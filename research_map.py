"""Inspect separately supplied research-map records without changing protocol or gates."""
import argparse
import copy
import datetime
import hashlib
import json
from pathlib import Path
import re

from evidence_workflow import run
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json
from research_bundle import engine_hashes

MAX_PROTOCOL_BYTES = 50_000_000
MAX_DOCUMENT_BYTES = 10_000_000
MAX_REPORT_BYTES = 50_000_000
MAX_ROWS = 1000
CORE_FIELDS = ('question', 'inclusion_criteria', 'exclusion_criteria', 'search_plan')
MAP_FIELDS = ('decision_scope', 'boundaries', 'evidence_classes', 'planned_sources',
              'extraction_dimensions', 'appraisal_plan', 'challenge_plan', 'expected_outputs', 'stop_rules')
RECORD_FIELDS = ('record_id', 'recorder', 'recorded_at', 'statement', 'basis_sha256')
EVENT_FIELDS = ('event_id', 'record_id', 'search_id', 'stop_rule_id', 'recorded_by', 'recorded_at', 'note')
BOUNDARY = (
    'Standalone authored map and supplied records only, not integrated research-map validation. '
    'CURRENT_SOURCE means exact declared basis equality, not approval, preregistration, '
    'method adequacy, authenticity or proof that a map was recorded before research. '
    'Stop events are supplied statements, not search execution, exhaustion, completeness '
    'or evidence sufficiency. No protocol, engine, gate, adapter receipt, bundle or human '
    'judgement is changed. Existing run(), adapters and research bundles do not validate '
    'or retain this sidecar. Retain it separately with original inputs. No source locator '
    'is opened, no model or network is called. Real/private inputs and outputs belong '
    'outside the public repository; displayed text and digests are not anonymized.'
)
NEGATIVE = dict(assessment='NOT_PERFORMED', preregistration='NOT_ESTABLISHED',
    chronology='NOT_VERIFIABLE', authenticity='NOT_VERIFIED', search_execution='NOT_PERFORMED',
    protocol_changed=False, engine_integration='NOT_IMPLEMENTED', census_claim='NOT_ESTABLISHED',
    conclusion_readiness='NOT_READY', external_calls=0)


def digest(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _normalize(value, limit):
    raw=canonical_json_bytes(value)
    if len(raw)>limit:raise ValueError('input size limit')
    value=parse_json(raw)
    pending=[(value,0)]
    while pending:
        item,depth=pending.pop()
        if depth>128:raise ValueError('input nesting limit')
        if isinstance(item,dict):pending.extend((x,depth+1) for x in item.values())
        elif isinstance(item,list):pending.extend((x,depth+1) for x in item)
    return value


def _object(value,fields):
    if not isinstance(value,dict) or set(value)!=set(fields):raise ValueError('exact object fields required')


def _text(value):
    if not isinstance(value,str) or not value.strip():raise ValueError('supplied nonblank text required')


def _rows(value,nonempty=False):
    if not isinstance(value,list) or len(value)>MAX_ROWS or (nonempty and not value):raise ValueError('bounded list required')


def _texts(value,nonempty=False):
    _rows(value,nonempty)
    for item in value:_text(item)


def _hash(value):
    if not isinstance(value,str) or re.fullmatch('[0-9a-f]{64}',value) is None:raise ValueError('basis digest required')


def _date(value):
    _text(value)
    if re.fullmatch('[0-9]{4}-[0-9]{2}-[0-9]{2}',value) is None:raise ValueError('date shape required')
    datetime.date.fromisoformat(value)


def _context(protocol):
    protocol=_normalize(protocol,MAX_PROTOCOL_BYTES)
    research=run(protocol)
    plan=protocol.get('search_plan')
    _rows(plan,True)
    ids=set()
    for row in plan:
        if not isinstance(row,dict):raise ValueError('search plan object required')
        _text(row.get('search_id'))
        if row['search_id'] in ids:raise ValueError('unique planned search IDs required')
        ids.add(row['search_id'])
    core={key:copy.deepcopy(protocol[key]) for key in ('question', 'inclusion_criteria', 'exclusion_criteria', 'search_plan')}
    return protocol,core,ids,research


def validate_document(document,search_ids):
    _object(document,('schema_version','research_map','records','stop_events'))
    if type(document['schema_version']) is not int or document['schema_version']!=1:raise ValueError('schema version must be integer 1')
    body=document['research_map'];_object(body,MAP_FIELDS)
    for key in ('decision_scope','boundaries','challenge_plan'):_text(body[key])
    for key in ('planned_sources','extraction_dimensions','expected_outputs'):_texts(body[key])
    _rows(body['evidence_classes']);classes=set()
    for row in body['evidence_classes']:
        _object(row,('label','description'));_text(row['label']);_text(row['description'])
        if row['label'] in classes:raise ValueError('duplicate evidence class label')
        classes.add(row['label'])
    _rows(body['appraisal_plan'])
    for row in body['appraisal_plan']:
        _object(row,('evidence_class','method','method_locator'))
        for value in row.values():_text(value)
        if row['evidence_class'] not in classes:raise ValueError('unknown declared evidence class')
    _rows(body['stop_rules']);rules={}
    for row in body['stop_rules']:
        _object(row,('stop_rule_id','applies_to','rule'))
        for value in row.values():_text(value)
        if row['stop_rule_id'] in rules:raise ValueError('duplicate stop rule')
        if row['applies_to']!='ALL' and row['applies_to'] not in search_ids:raise ValueError('unknown planned search')
        rules[row['stop_rule_id']]=row
    _rows(document['records']);records={}
    for row in document['records']:
        _object(row,RECORD_FIELDS)
        for key in ('record_id','recorder','statement'):_text(row[key])
        _date(row['recorded_at']);_hash(row['basis_sha256'])
        if row['record_id'] in records:raise ValueError('duplicate record ID')
        records[row['record_id']]=row
    _rows(document['stop_events']);events=set()
    for row in document['stop_events']:
        _object(row,EVENT_FIELDS)
        for value in row.values():_text(value)
        _date(row['recorded_at'])
        if row['event_id'] in events:raise ValueError('duplicate event ID')
        events.add(row['event_id'])
        if row['record_id'] not in records:raise ValueError('unknown map record')
        if row['search_id'] not in search_ids or row['stop_rule_id'] not in rules:raise ValueError('unknown event reference')
        if rules[row['stop_rule_id']]['applies_to'] not in ('ALL',row['search_id']):raise ValueError('event outside supplied rule scope')
    return body,records,rules


def _hashes():
    return dict(engine_hashes(),**{'research_map.py':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})


def template(protocol):
    protocol,core,_,_=_context(protocol)
    body={key:None for key in MAP_FIELDS}
    document=dict(schema_version=1,research_map=body,records=[],stop_events=[])
    return dict(schema_version=1,kind='research_map_template',draft=document,
        record_template={key:None for key in RECORD_FIELDS},event_template={key:None for key in EVENT_FIELDS},
        source_context=core,protocol_sha256=digest(protocol),implementation_sha256=_hashes(),
        template_warning='Every map field and every record/event assertion must be supplied separately. '
        'No map basis exists until the map is authored. Review an authored document with empty records '
        'to inspect its current basis; copying that digest alone is not a recording decision.',boundary=BOUNDARY,**NEGATIVE)


def review(protocol,document):
    protocol,core,ids,research=_context(protocol)
    document=_normalize(document,MAX_DOCUMENT_BYTES)
    body,records,rules=validate_document(document,ids)
    basis=digest(dict(protocol_core=core,research_map=body))
    statuses={key:'CURRENT_SOURCE' if row['basis_sha256']==basis else 'STALE_SOURCE' for key,row in records.items()}
    rows=[dict(record=copy.deepcopy(row),source_match_status=statuses[key]) for key,row in records.items()]
    events=[dict(event=copy.deepcopy(row),source_match_status=statuses[row['record_id']],
                 observation='SUPPLIED_STOP_STATEMENT_NOT_EXECUTION') for row in document['stop_events']]
    return _normalize(dict(schema_version=1,kind='research_map_review',
        protocol_sha256=digest(protocol),document_sha256=digest(document),
        current_basis_sha256=basis,basis_scope=list(CORE_FIELDS)+['research_map'],
        research_map=copy.deepcopy(body),records=rows,stop_events=events,
        record_stage='SUPPLIED' if rows else 'NOT_SUPPLIED',
        current_record_ids=[key for key in records if statuses[key]=='CURRENT_SOURCE'],
        stale_record_ids=[key for key in records if statuses[key]=='STALE_SOURCE'],
        planned_search_ids=sorted(ids),
        planned_searches_without_stop_rule=sorted(sid for sid in ids if not any(r['applies_to'] in ('ALL',sid) for r in rules.values())),
        input_observation=dict(identified_occurrences=research['flow']['identified'],
                               evidence_rows=len(protocol['evidence']),
                               scope='CURRENT_SUPPLIED_INPUT_NOT_AUTHENTICATED_RECORDING_TIME'),
        implementation_sha256=_hashes(),boundary=BOUNDARY,**NEGATIVE),MAX_REPORT_BYTES)


def verify(protocol,document,recorded_review):
    recorded_review=_normalize(recorded_review,MAX_REPORT_BYTES)
    expected=review(protocol,document)
    valid=canonical_json_bytes(expected)==canonical_json_bytes(recorded_review)
    return dict(schema_version=1,kind='research_map_replay_check',valid=valid,
        verification='EXACT_CURRENT_IMPLEMENTATION_REPLAY' if valid else 'REPLAY_MISMATCH',
        expected_report_sha256=digest(expected),recorded_report_sha256=digest(recorded_review),
        boundary='Exact current-input/current-implementation report comparison only. '+BOUNDARY,**NEGATIVE)


def _read(path,limit):
    with path.open('rb') as stream:raw=stream.read(limit+1)
    if len(raw)>limit:raise ValueError('byte limit')
    return _normalize(parse_json(raw),limit)


def main():
    configure_utf8_stdio();parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    for command in ('template','review','verify'):
        p=sub.add_parser(command);p.add_argument('protocol',type=Path)
        if command!='template':p.add_argument('document',type=Path)
        if command=='verify':p.add_argument('recorded_review',type=Path)
        else:p.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:
        protocol=_read(args.protocol,MAX_PROTOCOL_BYTES)
        if args.command=='template':result=template(protocol)
        else:
            document=_read(args.document,MAX_DOCUMENT_BYTES)
            result=review(protocol,document) if args.command=='review' else verify(protocol,document,_read(args.recorded_review,MAX_REPORT_BYTES))
        encoded=(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
        if len(encoded)>MAX_REPORT_BYTES:raise ValueError('output byte limit')
        if getattr(args,'output',None) is not None:
            with args.output.open('xb') as stream:stream.write(encoded)
        print(encoded.decode('utf-8'),end='')
        return int(args.command=='verify' and not result['valid'])
    except (OSError,ValueError,TypeError,KeyError,IndexError,AttributeError,RecursionError,OverflowError):
        parser.exit(1,'research map error: invalid, oversized or unreadable input, or unavailable new output; details withheld\n')


if __name__=='__main__':
    raise SystemExit(main())
