"""Compare validated supplied protocols without inferring scientific meaning from changes."""
import argparse
import hashlib
import json
from pathlib import Path
from evidence_workflow import run
from json_io import configure_utf8_stdio, parse_json, canonical_json_bytes as canonical
from prisma_reports import report_flow
from research_bundle import engine_hashes

BOUNDARY = ('Mechanical comparison of supplied inputs; both ledgers are recomputed with the current implementation, not replayed historical engines. '
            'Version labels do not authenticate amendment history or justify changes. '
            'No search, scientific reassessment or conclusion promotion is performed.')


def changed_fields(before, after):
    return sorted(field for field in set(before) | set(after)
                  if field not in before or field not in after
                  or canonical(before[field]) != canonical(after[field]))


def entity_changes(before, after, id_field):
    left = {row[id_field]: row for row in before}
    right = {row[id_field]: row for row in after}
    shared = set(left) & set(right)
    changed = [dict(id=identifier, fields=changed_fields(left[identifier], right[identifier]))
               for identifier in sorted(shared)
               if canonical(left[identifier]) != canonical(right[identifier])]
    return dict(added_ids=sorted(set(right) - set(left)),
                removed_ids=sorted(set(left) - set(right)), changed=changed,
                unchanged_count=len(shared) - len(changed))


def compare_protocols(before, after):
    left, right = run(before), run(after)
    left_reports = report_flow(before) if 'reports' in before else None
    right_reports = report_flow(after) if 'reports' in after else None
    left_bytes, right_bytes = canonical(before), canonical(after)
    changed = left_bytes != right_bytes
    version_changed = canonical(before['version']) != canonical(after['version'])
    old_records = {rid for row in before['searches'] for rid in row['record_ids']}
    new_records = {rid for row in after['searches'] for rid in row['record_ids']}
    positional_ids = {
        'before': [work['work_package_id'] for source, work in zip(before['gaps'], left['work_packages']) if 'work_package_id' not in source],
        'after': [work['work_package_id'] for source, work in zip(after['gaps'], right['work_packages']) if 'work_package_id' not in source],
    }
    identity_warnings = (['Work-package IDs were generated from list positions; insertion or reordering can change apparent identity. Use explicit stable IDs for longitudinal tracking.']
                         if positional_ids['before'] or positional_ids['after'] else [])
    entities = {
        'synthesis_statements': entity_changes(before.get('synthesis_statements', []), after.get('synthesis_statements', []), 'statement_id'),
        'planning_decisions': entity_changes(before.get('planning_decisions', []), after.get('planning_decisions', []), 'work_package_id'),
        'screening': entity_changes(left['screening_ledger'], right['screening_ledger'], 'record_id'),
        'evidence': entity_changes(left['evidence'], right['evidence'], 'evidence_id'),
        'work_packages': entity_changes(left['work_packages'], right['work_packages'], 'work_package_id'),
        'contexts': entity_changes(left['context']['context_ledger'], right['context']['context_ledger'], 'context_id'),
        'appraisals': entity_changes(left['appraisal']['appraisal_ledger'], right['appraisal']['appraisal_ledger'], 'appraisal_id'),
        'reports': entity_changes(left_reports['report_ledger'] if left_reports else [],
                                  right_reports['report_ledger'] if right_reports else [], 'report_id'),
        'search_plan': entity_changes(left['search_plan_audit']['search_plan_ledger'],
                                      right['search_plan_audit']['search_plan_ledger'], 'search_id'),
    }
    implementation = dict(engine_hashes(), **{'compare_runs.py': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    return dict(engine_sha256=implementation, before_protocol_sha256=hashlib.sha256(left_bytes).hexdigest(),
                after_protocol_sha256=hashlib.sha256(right_bytes).hexdigest(),
                hash_scope='sorted compact UTF-8 JSON inputs; object key order ignored, list order retained; not authentication',
                has_changes=changed, before_version=before['version'], after_version=after['version'],
                version_changed=version_changed, unversioned_change=changed and not version_changed,
                changed_protocol_fields=changed_fields(before, after),
                record_ids_added=sorted(new_records - old_records), record_ids_removed=sorted(old_records - new_records),
                entity_changes=entities, positional_work_package_ids=positional_ids,
                identity_warnings=identity_warnings,
                before_counts=left['flow'], after_counts=right['flow'],
                before_report_counts=left_reports['report_flow'] if left_reports else None,
                after_report_counts=right_reports['report_flow'] if right_reports else None,
                census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY', boundary=BOUNDARY)


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    args = parser.parse_args()
    try:
        result = compare_protocols(parse_json(args.before.read_text(encoding='utf-8')),
                                   parse_json(args.after.read_text(encoding='utf-8')))
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, str(error) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
