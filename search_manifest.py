"""Freeze supplied query specifications and receipt accounting without executing searches."""
import argparse
import copy
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from evidence_workflow import run
from prisma_reports import report_flow
from research_bundle import engine_hashes
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display

CORE_FIELDS=('source','query','window')
SIGNALS=('complete','total_count','has_more','error','truncated','pagination_limited','field_pages_pending')
BOUNDARY=('Read-only query/receipt manifest, not a live search or provider-ready execution file. '
          'Exact source/query/window text is preserved, not translated or syntax-validated. '
          'Receipt accounting, same-core queries and exact-ID overlap do not prove semantic equivalence, '
          'publication identity, source coverage or a census. No retries, pagination cursors, searches, '
          'review decisions or protocol changes are generated or executed.')


def digest(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def manifest(protocol):
    research=run(protocol)
    if 'reports' in protocol: report_flow(protocol)
    plan=protocol.get('search_plan')
    planned=plan is not None
    planned_status={r['search_id']:r for r in research['search_plan_audit']['search_plan_ledger']}
    search_indices={row.get('search_id'):i for i,row in enumerate(protocol['searches'])} if planned else {}
    requests=None if not planned else []
    same_core=defaultdict(list)
    for index,row in enumerate(plan or []):
        core={key:row[key] for key in CORE_FIELDS}
        supported=dict(search_id=row['search_id'],**core)
        core_hash=digest(core)
        requests.append(dict(search_id=row['search_id'],input_pointer=f'/search_plan/{index}',
                             original_plan_entry=copy.deepcopy(row),request_fields=supported,
                             request_spec_sha256=digest(row),core_query_sha256=core_hash,
                             unsupported_plan_fields=sorted(set(row)-set(supported)),
                             receipt_status=planned_status[row['search_id']]['status'],
                             observed_search_index=search_indices.get(row['search_id']),
                             operator_required_fields=['request_id','searched_at'],
                             execution_readiness='NOT_ESTABLISHED',provider_translation='NOT_IMPLEMENTED',
                             query_syntax_verification='NOT_PERFORMED',index_snapshot_verification='NOT_PERFORMED'))
        same_core[core_hash].append(row['search_id'])
    sources=defaultdict(lambda:dict(planned_search_ids=[],missing_search_ids=[],observed_search_indices=[],
                                    asserted_complete_search_indices=[],unresolved_search_indices=[],record_ids=set(),record_occurrences=0))
    for row in requests or []:
        source=sources[row['request_fields']['source']]
        source['planned_search_ids'].append(row['search_id'])
        if row['receipt_status']=='MISSING':source['missing_search_ids'].append(row['search_id'])
    record_searches=defaultdict(list);record_sources=defaultdict(set)
    receipts=[]
    for index,row in enumerate(protocol['searches']):
        accounting=research['coverage'][index]
        source=sources[row['source']]
        source['observed_search_indices'].append(index)
        source['asserted_complete_search_indices' if accounting['complete'] else 'unresolved_search_indices'].append(index)
        source['record_occurrences']+=len(row['record_ids']);source['record_ids'].update(row['record_ids'])
        for rid in row['record_ids']:
            record_searches[rid].append(index);record_sources[rid].add(row['source'])
        pages=None if 'pages' not in row else []
        page_records=defaultdict(list)
        for pi,page in enumerate(row.get('pages',[])):
            pointer=f'/searches/{index}/pages/{pi}'
            pages.append(dict(input_pointer=pointer,page_number=page['page_number'],record_ids=copy.deepcopy(page['record_ids']),
                              recorded_signals={key:copy.deepcopy(page[key]) for key in SIGNALS if key in page},
                              page_sha256=digest(page),
                              uninterpreted_fields={key:copy.deepcopy(value) for key,value in page.items() if key not in {'page_number','record_ids',*SIGNALS}}))
            for rid in page['record_ids']:page_records[rid].append(pointer)
        receipts.append(dict(search_index=index,input_pointer=f'/searches/{index}',search_id=row.get('search_id'),
                             request_fields={key:row[key] for key in CORE_FIELDS},searched_at=row['searched_at'],
                             supplied_receipt_sha256=digest(row),record_ids=copy.deepcopy(row['record_ids']),
                             uninterpreted_fields={key:copy.deepcopy(value) for key,value in row.items() if key not in {'search_id',*CORE_FIELDS,'searched_at','record_ids','pages',*SIGNALS}},
                             recorded_signals={key:copy.deepcopy(row[key]) for key in SIGNALS if key in row},
                             accounting=copy.deepcopy(accounting),pages=pages,
                             page_overlap=[dict(record_id=rid,page_pointers=pointers) for rid,pointers in sorted(page_records.items()) if len(pointers)>1],
                             continuation='NOT_COMPUTED',source_authenticity='NOT_ESTABLISHED'))
    source_coverage=[]
    for name,source in sorted(sources.items()):
        source_coverage.append(dict(source=name,receipt_stage='SUPPLIED' if source['observed_search_indices'] else 'NOT_SUPPLIED',planned_search_ids=sorted(source['planned_search_ids']) if planned else None,
                                    missing_search_ids=sorted(source['missing_search_ids']) if planned else None,
                                    observed_search_indices=source['observed_search_indices'],
                                    asserted_complete_search_indices=source['asserted_complete_search_indices'],
                                    unresolved_search_indices=source['unresolved_search_indices'],
                                    supplied_record_occurrences=source['record_occurrences'] if source['observed_search_indices'] else None,
                                    unique_exact_record_ids=sorted(source['record_ids']) if source['observed_search_indices'] else None,
                                    unique_exact_record_count=len(source['record_ids']) if source['observed_search_indices'] else None,
                                    repeated_exact_id_occurrences=source['record_occurrences']-len(source['record_ids']) if source['observed_search_indices'] else None,
                                    cross_source_overlap_record_ids=sorted(rid for rid in source['record_ids'] if len(record_sources[rid])>1) if source['observed_search_indices'] else None,
                                    declared_plan_status='NOT_SUPPLIED' if not planned else 'INCOMPLETE' if source['missing_search_ids'] or source['unresolved_search_indices'] else 'ASSERTED_ACCOUNTED',
                                    source_completeness='NOT_ESTABLISHED'))
    implementation=dict(engine_hashes(),**{'search_manifest.py':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    return dict(schema_version=1,question=research['question'],protocol_version=research['protocol_version'],
                protocol_sha256=digest(protocol),hash_scope='Canonical supplied JSON, object key order ignored and list order retained; not authentication',
                engine_sha256=implementation,plan_stage='SUPPLIED' if planned else 'NOT_SUPPLIED',
                search_plan_audit=copy.deepcopy(research['search_plan_audit']),planned_requests=requests,
                same_core_request_groups=[dict(core_query_sha256=key,search_ids=sorted(ids),
                    scope='Equal literal source/query/window only; other plan fields and scientific equivalence not compared') for key,ids in sorted(same_core.items()) if len(ids)>1],
                observed_receipts=receipts,source_coverage=source_coverage,
                cross_search_overlap=[dict(record_id=rid,search_indices=indices,source_labels=sorted(record_sources[rid])) for rid,indices in sorted(record_searches.items()) if len(indices)>1],
                replay_limits=['No live adapter, provider translation or query syntax validation',
                               'No provider/index version or snapshot authenticity established',
                               'Required new request IDs and search timestamps must be supplied by the operator',
                               'Re-execution needs retained prior inputs and explicit protocol/plan reconciliation; existing receipts are never overwritten',
                               'Pages may be incomplete; no next cursor or restart point is inferred',
                               'Source labels and record IDs are exact supplied strings, not verified identities'],
                external_calls=0,census_claim='NOT_ESTABLISHED',conclusion_readiness='NOT_READY',boundary=BOUNDARY)


def render_text(result):
    show=quoted_display
    lines=['Supplied search query/receipt manifest','Question: '+show(result['question']),
           'Protocol SHA-256: '+result['protocol_sha256'],'Plan stage: '+result['plan_stage']]
    for row in result['planned_requests'] or []:
        lines.append('Request specification: '+show(row))
    if result['planned_requests'] is None:lines.append('No declared plan: observed queries are not promoted into executable requests.')
    for source in result['source_coverage']:lines.append('Source accounting: '+show(source))
    for row in result['observed_receipts']:
        lines.append('Observed receipt: '+show(row))
    lines.extend(['Same core request groups: '+show(result['same_core_request_groups']),
                  'Cross-search exact-ID overlap: '+show(result['cross_search_overlap']),
                  'Manual replay limits: '+show(result['replay_limits']),
                  'External calls: 0','Census: NOT_ESTABLISHED','Conclusion: NOT_READY',result['boundary']])
    return '\n'.join(lines)+'\n'


def main():
    configure_utf8_stdio();parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('protocol',type=Path);parser.add_argument('--text',action='store_true');args=parser.parse_args()
    try:result=manifest(parse_json(args.protocol.read_text(encoding='utf-8')))
    except (ValueError,OSError,KeyError,TypeError) as error:parser.exit(1,str(error)+'\n')
    print(render_text(result) if args.text else json.dumps(result,ensure_ascii=False,indent=2),end='' if args.text else '\n')

if __name__=='__main__':main()
