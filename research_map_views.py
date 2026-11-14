"""Optional standalone map context; never alter research gates, queues or decisions."""
import copy
import hashlib
from pathlib import Path

import research_map as maps
from json_io import canonical_json_bytes, quoted_display

BOUNDARY = ('Optional standalone map context only. Not part of protocol/gate/queue validation, '
    'research bundle verification or an execution permission. Supplied map records and stopping '
    'statements do not establish approval, scientific adequacy, chronology or completeness. '
    'No record is renewed or selected as authoritative. Map differences do not change protocol '
    'has_changes, amendment binding or command exit decisions. Inputs and hashes are not anonymized.')


def read_document(path):
    return maps._read(path,maps.MAX_DOCUMENT_BYTES)


def _context(report):
    return dict(scope='STANDALONE_SIDECAR_NOT_ENGINE_INTEGRATED',
        protocol_sha256=report['protocol_sha256'],document_sha256=report['document_sha256'],
        current_basis_sha256=report['current_basis_sha256'],record_stage=report['record_stage'],
        current_record_ids=copy.deepcopy(report['current_record_ids']),stale_record_ids=copy.deepcopy(report['stale_record_ids']),
        records=[dict(record_id=x['record']['record_id'],source_match_status=x['source_match_status']) for x in report['records']],
        stop_events=[dict(event_id=x['event']['event_id'],record_id=x['event']['record_id'],search_id=x['event']['search_id'],
                         stop_rule_id=x['event']['stop_rule_id'],source_match_status=x['source_match_status']) for x in report['stop_events']],
        planned_searches_without_stop_rule=copy.deepcopy(report['planned_searches_without_stop_rule']),
        input_observation=copy.deepcopy(report['input_observation']),
        implementation_sha256=dict(report['implementation_sha256'],**{'research_map_views.py':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}),
        assessment='NOT_PERFORMED',census_claim='NOT_ESTABLISHED',conclusion_readiness='NOT_READY',boundary=BOUNDARY)


def context(protocol,document):
    return _context(maps.review(protocol,document))


def _different(left,right):
    return canonical_json_bytes(left)!=canonical_json_bytes(right)


def _changes(left,right,key):
    a={row[key]:row for row in left};b={row[key]:row for row in right}
    return dict(added_ids=sorted(set(b)-set(a)),removed_ids=sorted(set(a)-set(b)),
        modified=[dict(id=i,changed_fields=sorted(k for k in set(a[i])|set(b[i]) if k not in a[i] or k not in b[i] or _different(a[i][k],b[i][k])))
                  for i in sorted(set(a)&set(b)) if _different(a[i],b[i])],
        order_changed=[row[key] for row in left]!=[row[key] for row in right])


def comparison(before,after,before_map,after_map):
    left=maps.review(before,before_map);right=maps.review(after,after_map)
    changes=dict(map_fields=sorted(k for k in left['research_map'] if _different(left['research_map'][k],right['research_map'][k])),
        records=_changes([x['record'] for x in left['records']],[x['record'] for x in right['records']],'record_id'),
        stop_events=_changes([x['event'] for x in left['stop_events']],[x['event'] for x in right['stop_events']],'event_id'))
    return dict(before=_context(left),after=_context(right),
        map_document_changed=left['document_sha256']!=right['document_sha256'],
        basis_changed=left['current_basis_sha256']!=right['current_basis_sha256'],
        supplied_changes=changes,boundary=BOUNDARY)


def attach(result,value):
    result['research_map_context']=value
    # Bound optional joined views without changing any default call's output budget.
    return maps._normalize(result,maps.MAX_REPORT_BYTES)


def text(context):
    if 'before' in context:
        return ('Standalone map comparison (not protocol changes or gates)\n'
            +'Map document changed: '+str(context['map_document_changed'])+'\n'
            +'Basis changed: '+str(context['basis_changed'])+'\n'
            +'Supplied changes: '+quoted_display(context['supplied_changes'])+'\n'
            +'Before: '+text(context['before'])+'After: '+text(context['after']))
    return ('Standalone map context (not a readiness gate)\n'
        +'Record stage: '+quoted_display(context['record_stage'])+'\n'
        +'Current record IDs: '+quoted_display(context['current_record_ids'])+'\n'
        +'Stale record IDs: '+quoted_display(context['stale_record_ids'])+'\n'
        +'Supplied stop event contexts: '+quoted_display(context['stop_events'])+'\n'
        +'Planned searches without supplied stop rule: '+quoted_display(context['planned_searches_without_stop_rule'])+'\n'
        +BOUNDARY+'\n')
