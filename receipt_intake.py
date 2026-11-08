"""Guide synthetic manual search receipt entry using the existing mock adapter."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from adapter_integrity import digest
from search_audit import audit_search_plan
from offline_adapter import assemble
from search_manifest import manifest
from prisma_audit import export_audit
from json_io import configure_utf8_stdio, parse_json, quoted_display

BOUNDARY=('Synthetic manual-entry rehearsal using the existing mock adapter, not actual literature '
          'retrieval or source verification. Template nulls are deliberate missing input, not empty '
          'search results. Checking never accepts a receipt or extraction, supplies missing facts, '
          'renews a review, or certifies complete search. Saved protocols are unreviewed candidates.')


def fresh_base(protocol):
    if not isinstance(protocol,dict):raise ValueError('protocol must be an object')
    if protocol.get('searches') != [] or protocol.get('evidence') != [] or 'adapter_receipts' in protocol:
        raise ValueError('intake requires a separate base with empty searches/evidence and no adapter_receipts; never clear or overwrite existing research to import receipts')
    if not isinstance(protocol.get('search_plan'),list) or not protocol['search_plan']:
        raise ValueError('intake requires a nonempty declared search plan')
    audit_search_plan(protocol)


def template(protocol):
    fresh_base(protocol)
    return dict(schema_version=1,mode='mock',provider_id=None,adapter_version=None,
                search_responses=[dict(request=dict(**{key:row[key] for key in ('search_id','source','query','window')},
                                                    request_id=None,searched_at=None),
                                       total_count=None,
                                       pages=[dict(response_id=None,request_id=None,retrieved_at=None,page_number=None,
                                                   has_more=None,total_count=None,records=None)]) for row in protocol['search_plan']],
                extraction_candidates=[])


def missing_hints(fixture):
    """Locate unfilled required entry fields; the adapter remains the schema authority."""
    hints=[]
    def text_fields(row,pointer,fields):
        if not isinstance(row,dict):return
        for field in fields:
            value=row.get(field)
            if value is None or isinstance(value,str) and not value.strip():
                hints.append(dict(input_pointer=pointer+'/'+field,kind='required_text_unfilled'))
    if not isinstance(fixture,dict):return hints
    text_fields(fixture,'',('provider_id','adapter_version'))
    responses=fixture.get('search_responses')
    if not isinstance(responses,list):return hints
    for ei,exchange in enumerate(responses):
        prefix=f'/search_responses/{ei}'
        if not isinstance(exchange,dict):continue
        text_fields(exchange.get('request'),prefix+'/request',('search_id','source','query','window','request_id','searched_at'))
        pages=exchange.get('pages')
        if not isinstance(pages,list):continue
        for pi,page in enumerate(pages):
            path=prefix+f'/pages/{pi}'
            if not isinstance(page,dict):continue
            text_fields(page,path,('response_id','request_id','retrieved_at'))
            if page.get('page_number') is None:hints.append(dict(input_pointer=path+'/page_number',kind='required_page_number_unfilled'))
            records=page.get('records')
            if records is None:hints.append(dict(input_pointer=path+'/records',kind='required_record_list_unfilled_not_an_empty_result'))
            if isinstance(records,list):
                for ri,record in enumerate(records):text_fields(record,path+f'/records/{ri}',('record_id','source_locator'))
    return hints


def check(protocol,fixture):
    hints=missing_hints(fixture)
    try:
        fresh_base(protocol)
        if not isinstance(fixture,dict) or fixture.get('extraction_candidates') != []:
            raise ValueError('search receipt intake requires extraction_candidates=[]; use the existing adapter separately for extraction review')
        if any(key in fixture for key in ('reviews','review_decisions')):
            raise ValueError('intake does not accept review payloads; review receipts separately through the existing adapter workflow')
        assembled=assemble(protocol,fixture)  # No reviews accepted or fabricated.
        candidate=assembled['protocol']
        search=manifest(candidate);prisma=export_audit(candidate)
    except (ValueError,KeyError,TypeError) as error:
        return dict(schema_version=1,valid_input=False,status='INVALID_INPUT',missing_field_hints=hints,
                    validation_error=str(error),external_calls=0,boundary=BOUNDARY)
    hashes=dict(search['engine_sha256'],**prisma['engine_sha256'])
    hashes['receipt_intake.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return dict(schema_version=1,valid_input=True,status='UNREVIEWED_SUPPLIED_CANDIDATES',
                base_protocol_sha256=digest(protocol),fixture_sha256=digest(fixture),engine_sha256=hashes,
                missing_field_hints=hints,review_pending=copy.deepcopy(assembled['review_pending']),
                search_manifest=search,prisma_audit=prisma,protocol_candidate=candidate,
                external_calls=0,census_claim='NOT_ESTABLISHED',conclusion_readiness='NOT_READY',boundary=BOUNDARY)


def render_text(result):
    show=quoted_display
    lines=['Synthetic manual receipt intake','Status: '+result['status'],
           'Unfilled required-field hints: '+show(result['missing_field_hints'])]
    if not result['valid_input']:
        lines.append('Validation error: '+show(result['validation_error']))
    else:
        lines.extend(['Supplied receipts awaiting operator review: '+show(result['review_pending']),
                      'Declared search accounting: '+show(result['search_manifest']['search_plan_audit']),
                      'Source receipt accounting: '+show(result['search_manifest']['source_coverage']),
                      'PRISMA-oriented accounting nodes: '+show(result['prisma_audit']['nodes']),
                      'Full page/interruption/overlap diagnostics and candidate protocol are in JSON output.',
                      'Census: NOT_ESTABLISHED','Conclusion: NOT_READY'])
    lines.extend(['External calls: 0',result['boundary']])
    return '\n'.join(lines)+'\n'


def main():
    configure_utf8_stdio();parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    t=sub.add_parser('template');t.add_argument('protocol',type=Path)
    c=sub.add_parser('check');c.add_argument('protocol',type=Path);c.add_argument('fixture',type=Path)
    c.add_argument('--text',action='store_true');c.add_argument('--protocol-output',type=Path,help='save an unreviewed candidate exclusively; never overwrite')
    args=parser.parse_args()
    try:
        protocol=parse_json(args.protocol.read_bytes())
        result=template(protocol) if args.command=='template' else check(protocol,parse_json(args.fixture.read_bytes()))
        if args.command=='check' and result['valid_input'] and args.protocol_output is not None:
            serialized=json.dumps(result['protocol_candidate'],ensure_ascii=False,indent=2)+'\n'
            with args.protocol_output.open('x',encoding='utf-8',newline='\n') as output:output.write(serialized)
    except (OSError,ValueError,KeyError,TypeError) as error:parser.exit(1,str(error)+'\n')
    print(render_text(result) if args.command=='check' and args.text else json.dumps(result,ensure_ascii=False,indent=2),end='' if args.command=='check' and args.text else '\n')
    if args.command=='check' and not result['valid_input']:parser.exit(1)

if __name__=='__main__':main()
