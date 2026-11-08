"""Synthetic explicit report-study membership accounting, never identity inference."""
import copy
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from evidence_workflow import run
from prisma_reports import report_flow
from prisma_audit import export_audit
from research_status import status
from review_handoff import handoff
from synthesis_review import snapshot
from work_review import review_packets, navigation_summary, render_brief, render_text
from compare_runs import compare_protocols
from research_bundle import build_bundle, verify, engine_hashes
from report_links import validate_reports, report_study_ids
from offline_adapter import assemble

ROOT = Path(__file__).resolve().parents[1]
QUEUE = 'report_study_memberships_without_results'


def fixture(name='report-protocol.json'):
    return json.loads((ROOT / 'examples' / name).read_text(encoding='utf-8'))


def plural(p):
    for row in p['reports']:
        if row.get('decision') == 'include':
            row['study_ids'] = [row.pop('study_id')]
    return p


def multi():
    p = plural(fixture())
    p['reports'][0]['study_ids'].append('s2')
    p['evidence'][0]['evidence_id'] = 'e1'
    p['evidence'] += [dict(p['evidence'][0], evidence_id='e2', study_id='s2'),
                      dict(p['evidence'][0], evidence_id='e3', study_id='s2')]
    p['gaps'][0]['evidence_ids'] = ['e1', 'e2', 'e3']
    return p


class ReportStudyMembershipTests(unittest.TestCase):
    def test_two_studies_one_report_record_multiple_results(self):
        p = multi(); r = run(p); reports = report_flow(p)
        self.assertEqual((r['flow']['extracted'], r['flow']['extracted_records'], r['flow']['extracted_studies']), (3, 1, 2))
        self.assertEqual(reports['report_flow']['included_studies'], 2)
        self.assertEqual(reports['report_flow']['reports_with_extraction'], 1)
        rows = r['report_study_coverage']['membership_ledger']
        self.assertEqual([x['evidence_ids'] for x in rows], [['e1'], ['e2', 'e3']])
        self.assertEqual([x['membership_id'] for x in rows], ['/reports/0/study_ids/0', '/reports/0/study_ids/1'])
        self.assertEqual(r['report_study_coverage']['counts'], dict(included_memberships=2, memberships_with_result_rows=2, memberships_without_result_rows=0))
        self.assertEqual(reports['report_study_coverage'], r['report_study_coverage'])
        self.assertEqual(r['report_study_coverage']['study_eligibility_assessment'], 'NOT_PERFORMED')
        self.assertEqual(r['report_study_coverage']['study_identity_verification'], 'NOT_ESTABLISHED')
        self.assertEqual(r['report_study_coverage']['extraction_completeness'], 'NOT_ESTABLISHED')
        self.assertEqual(r['extraction_completeness'], 'NOT_ESTABLISHED')
        self.assertEqual(r['record_identity_verification'], 'NOT_ESTABLISHED')

    def test_partial_pair_does_not_become_report_without_results(self):
        p = multi(); p['evidence'] = p['evidence'][:1]; p['gaps'] = []
        r = report_flow(p)
        self.assertEqual(r['extraction_pending_reports'], [])
        self.assertEqual(r['report_flow']['reports_with_extraction'], 1)
        missing = r['report_study_coverage']['missing_report_study_memberships']
        self.assertEqual(missing, [dict(report_id='report-1', study_id='s2', membership_id='/reports/0/study_ids/1', input_pointer='/reports/0/study_ids/1')])
        self.assertEqual(status(p)['queues'][QUEUE], missing)
        self.assertEqual(snapshot(p)['review_queues'][QUEUE], missing)
        step = next(s for s in handoff(p)['manual_review_steps'] if s['queue'] == QUEUE)
        self.assertEqual(step['items'], missing)
        self.assertEqual(step['matching_input_rows'], ['/reports/0'])

    def test_same_study_in_another_report_cannot_fill_missing_pair(self):
        p = multi(); p['screening'][1]['decision'] = 'include'
        p['reports'].append(dict(report_id='report-2', record_ids=['r2'], retrieval='retrieved', decision='include', study_id='s1', locator='synthetic section'))
        r = report_flow(p)
        self.assertEqual(r['report_flow']['included_studies'], 2)
        self.assertEqual(r['extraction_pending_reports'], ['report-2'])
        last = r['report_study_coverage']['membership_ledger'][-1]
        self.assertEqual((last['study_id'], last['evidence_ids'], last['membership_id']), ('s1', [], '/reports/1/study_id'))
        links = {r['study_id']: r for r in export_audit(p)['study_links']}
        self.assertEqual(links['s1']['included_report_ids'], ['report-1', 'report-2'])

    def test_multiple_records_per_report_keep_pair_specific_evidence(self):
        p = multi(); p['screening'][1]['decision'] = 'include'
        p['reports'][0]['record_ids'].append('r2'); p['evidence'][2]['record_id'] = 'r2'
        r = report_flow(p)
        self.assertEqual(r['record_flow']['extracted_records'], 2)
        self.assertEqual(r['report_flow']['reports_with_extraction'], 1)
        self.assertEqual(r['report_study_coverage']['membership_ledger'][1]['evidence_ids'], ['e2', 'e3'])

    def test_invalid_plural_shapes_and_values(self):
        for value in (None, True, 1, 's1', {}, [], [''], [' '], ['\t\n'], [None], [False], [1], [{}], [[]], ['s1', 's1']):
            p = multi(); p['reports'][0]['study_ids'] = value
            for operation in (run, report_flow):
                with self.subTest(value=value, operation=operation.__name__), self.assertRaises(ValueError): operation(p)

    def test_both_keys_rejected_even_null_legacy_key(self):
        for value in (None, '', 's1'):
            p = multi(); p['reports'][0]['study_id'] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'mutually exclusive'): run(p)

    def test_plural_requires_included_retrieved_report(self):
        for change in (dict(decision='exclude', reason='scope'), dict(decision='pending'), dict(decision='pending', retrieval='pending'), dict(decision='pending', retrieval='not_retrieved', reason='missing')):
            p = multi(); p['evidence'] = []; p['gaps'] = []; p['reports'][0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError): run(p)

    def test_nonincluded_legacy_scalar_is_retained_not_membership(self):
        p = multi(); p['screening'][1]['decision'] = 'include'
        p['reports'].append(dict(report_id='excluded', record_ids=['r2'], retrieval='retrieved', decision='exclude', reason='scope', study_id='legacy-nonincluded', locator='synthetic'))
        r = report_flow(p)
        self.assertEqual(r['report_ledger'][0]['study_id'], 'legacy-nonincluded')
        self.assertEqual(len(r['report_study_coverage']['membership_ledger']), 2)
        self.assertNotIn('legacy-nonincluded', [x['study_id'] for x in export_audit(p)['study_links']])

    def test_multiple_studies_require_explicit_plural_authorization(self):
        for state in ('absent', 'scalar', 'unmapped', 'excluded', 'unretrieved', 'undeclared'):
            p = multi()
            if state == 'absent': p.pop('reports')
            elif state == 'scalar': p['reports'][0].pop('study_ids'); p['reports'][0]['study_id'] = 's1'
            elif state == 'undeclared': p['reports'][0]['study_ids'] = ['s1']
            else:
                p['screening'][1]['decision'] = 'include'
                p['reports'][0]['record_ids'] = ['r2']
                if state != 'unmapped':
                    row = dict(report_id='other', record_ids=['r1'], retrieval='retrieved', decision='exclude', reason='scope', locator='synthetic')
                    if state == 'unretrieved': row.update(retrieval='pending', decision='pending')
                    p['reports'].append(row)
            with self.subTest(state=state), self.assertRaises(ValueError): run(p)

    def test_optin_validates_all_report_rows_in_core(self):
        p = multi(); p['reports'].append(dict(p['reports'][0], report_id='duplicate-mapping'))
        with self.assertRaisesRegex(ValueError, 'multiple reports'): run(p)
        p = fixture(); p['reports'][0]['locator'] = ''
        run(p)  # Legacy core does not newly enforce report rendering rules.
        with self.assertRaises(ValueError): report_flow(p)

    def test_literal_ids_no_title_locator_or_near_id_inference(self):
        p = multi(); p['reports'][0]['study_ids'] = ['s1', 's1 ', 'S1']
        p['evidence'][1]['study_id'] = 's1 '; p['evidence'][2]['study_id'] = 'S1'
        for row in p['evidence']: row.update(title='same supplied title', locator='same supplied locator')
        self.assertEqual(run(p)['flow']['extracted_studies'], 3)
        self.assertEqual(report_flow(p)['report_flow']['included_studies'], 3)
        p['evidence'][1]['study_id'] = 's1-near'
        with self.assertRaisesRegex(ValueError, 'conflicts'): run(p)

    def test_prisma_additive_partition_and_boundaries(self):
        p = multi(); r = export_audit(p)
        nodes = {n['node_id']: n for n in r['nodes']}
        self.assertEqual(nodes['included_report_study_memberships']['count'], 2)
        self.assertEqual(nodes['reports_included']['count'], 1)
        checks = r['partition_checks']
        self.assertEqual(len(checks), len(export_audit(fixture())['partition_checks']) + 1)
        self.assertTrue(all(c['status'] == 'RECORDED_MEMBERS_PARTITION' for c in checks))
        self.assertEqual(r['conclusion_readiness'], 'NOT_READY')
        self.assertIn('not verified study identity', r['report_study_coverage']['boundary'])

    def test_new_outputs_and_helper_inputs_are_detached(self):
        p = multi(); original = copy.deepcopy(p)
        reports, by_record = validate_reports(p['reports'], ['r1'])
        ids = report_study_ids(reports['report-1']); ids.append('mutated')
        reports['report-1']['record_ids'].append('mutation')
        self.assertEqual(p, original)
        for operation in (run, report_flow, export_audit, snapshot):
            result = operation(p); result['report_study_coverage']['membership_ledger'][0]['evidence_ids'].append('mutated')
            self.assertEqual(p, original)
            self.assertEqual(operation(p)['report_study_coverage']['membership_ledger'][0]['evidence_ids'], ['e1'])
        result = status(p); result['queues'][QUEUE].append({'mutated': True}); self.assertEqual(p, original)

    def test_legacy_csv_exact_bytes_and_optin_append_only(self):
        p = fixture(); old = report_flow(p)['report_csv']
        self.assertEqual(old, 'report_id,record_ids,retrieval,decision,reason,study_id,locator\nreport-1,r1,retrieved,include,,s1,synthetic section\n')
        r = report_flow(multi())['report_csv']; rows = list(csv.reader(io.StringIO(r)))
        self.assertEqual(rows[0][:-1], list(csv.reader(io.StringIO(old)))[0])
        self.assertEqual(rows[0][-1], 'declared_study_ids'); self.assertEqual(rows[1][5], '')
        self.assertEqual(json.loads(rows[1][-1]), ['s1', 's2'])

    def test_hostile_multiline_csv_remains_parseable_and_safe(self):
        p = multi(); p['reports'][0].update(report_id='=formula', locator='@source\r\n한글,"quoted"')
        p['reports'][0]['study_ids'].append('=unextracted\n한글')
        rows = list(csv.reader(io.StringIO(report_flow(p)['report_csv'], newline='')))
        self.assertEqual(len(rows), 2); self.assertEqual(len(rows[1]), 8)
        self.assertEqual(rows[1][0], "'=formula"); self.assertTrue(rows[1][6].startswith("'@source"))
        self.assertEqual(json.loads(rows[1][7]), p['reports'][0]['study_ids'])

    def test_legacy_optional_outputs_absent(self):
        p = fixture()
        for operation in (run, report_flow, export_audit, snapshot): self.assertNotIn('report_study_coverage', operation(p))
        self.assertNotIn(QUEUE, status(p)['queues'])
        self.assertNotIn(QUEUE, [s['queue'] for s in handoff(p)['manual_review_steps']])

    def test_appraisal_cross_study_guard_preserved(self):
        p = plural(fixture('appraised-protocol.json'))
        p['reports'][0]['study_ids'].append('s2'); p['evidence'][1]['study_id'] = 's2'
        p['appraisals'][0]['evidence_ids'] = ['e1', 'e2']
        with self.assertRaisesRegex(ValueError, 'study'): run(p)

    def test_experimental_unit_cross_study_guard_preserved(self):
        p = plural(fixture('experiment-review.json'))
        p['reports'][0]['study_ids'].append('s2'); p['evidence'][1]['study_id'] = 's2'
        with self.assertRaisesRegex(ValueError, 'study'): run(p)

    def test_source_metadata_changes_stale_bound_reviews(self):
        p = plural(fixture('completion-binding.json'))
        p['planning_decisions'] = fixture('planning-review.json')['planning_decisions']
        r = run(p)
        targets = {x['work_package_id']: x['basis_sha256'] for x in r['planning']['review_targets']}
        for row in p.get('planning_decisions', []): row['basis_sha256'] = targets[row['work_package_id']]
        for row in p['gaps']:
            if row.get('status') == 'COMPLETE': row['completion_basis_sha256'] = next(x['current_basis_sha256'] for x in r['planning']['completion_ledger'] if x['work_package_id'] == row['work_package_id'])
        p['synthesis_statements'] = [dict(statement_id='synthetic', text='Supplied synthetic statement', limitations='No verification', evidence_ids=['e1'])]
        target = run(p)['synthesis']['review_targets'][0]['basis_sha256']
        p['synthesis_statements'][0].update(review_status='reviewed', reviewer='synthetic', reviewed_at='2026-11-03', basis_sha256=target)
        self.assertEqual(run(p)['synthesis']['statement_ledger'][0]['source_match_status'], 'CURRENT_SOURCE')
        p['reports'][0]['locator'] += ' changed supplied metadata'
        r = run(p)
        self.assertEqual(r['synthesis']['statement_ledger'][0]['source_match_status'], 'STALE_SOURCE')
        self.assertTrue(status(p)['queues']['completed_work_with_stale_source_binding'])
        self.assertTrue(status(p)['queues']['work_with_stale_planning_assertion'])

    def test_bundle_roundtrip_and_report_helper_fingerprint(self):
        p = multi(); data = build_bundle(json.dumps(p, ensure_ascii=False).encode('utf-8'))
        self.assertEqual(data, build_bundle(json.dumps(p, ensure_ascii=False).encode('utf-8')))
        self.assertEqual(engine_hashes()['report_links.py'], hashlib.sha256((ROOT / 'report_links.py').read_bytes()).hexdigest())
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            self.assertEqual(json.loads(z.read('protocol.json')), p)
            self.assertEqual(json.loads(z.read('research.json'))['report_study_coverage'], run(p)['report_study_coverage'])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'run.zip'; path.write_bytes(data); self.assertTrue(verify(path)['valid'])

    def test_cli_utf8_native_newline(self):
        p = multi(); p['question'] = '한글 synthetic question'
        p['reports'][0]['locator'] = '한글 synthetic locator'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'protocol.json'; path.write_text(json.dumps(p, ensure_ascii=False), encoding='utf-8')
            for script in ('evidence_workflow.py', 'prisma_reports.py', 'prisma_audit.py', 'research_status.py', 'review_handoff.py', 'synthesis_review.py'):
                result = subprocess.run([sys.executable, str(ROOT / script), str(path)], capture_output=True, timeout=30, cwd=ROOT, env=dict(os.environ, PYTHONIOENCODING='ascii'))
                with self.subTest(script=script):
                    self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8'))
                    self.assertIn('한글', result.stdout.decode('utf-8'))
                    self.assertTrue(result.stdout.endswith(os.linesep.encode()))

    def test_work_membership_coverage_is_navigation_not_inherited_scope(self):
        p = multi(); p['evidence'] = p['evidence'][:1]; p['gaps'][0]['evidence_ids'] = ['e1']
        packet = review_packets(p)['packets'][0]
        coverage = packet['report_study_coverage']
        self.assertEqual(coverage['missing_report_study_memberships'][0]['study_id'], 's2')
        self.assertEqual(coverage['scope'], 'full_explicitly_linked_reports_not_inferred_work_requirements')
        self.assertEqual(packet['work_package']['evidence_ids'], ['e1'])
        self.assertEqual(packet['work_package']['blocked_by'], [])
        self.assertEqual(packet['scope_counts']['result_rows'], 1)
        self.assertIn('s2', render_brief(review_packets(p)))
        self.assertIn('s2', render_text(review_packets(p)))
        self.assertIn('report_study_coverage', json.dumps(navigation_summary(review_packets(p))))
        self.assertIn('report_study_coverage', json.dumps(handoff(p)))
        self.assertEqual(packet['appraisals'], [])
        self.assertEqual(packet['experimental_units'], [])

    def test_planned_search_work_does_not_expand_report_memberships(self):
        p = plural(fixture('source-work-protocol.json'))
        p.pop('adapter_receipts')
        for row in p['searches']: row.pop('adapter_provenance', None)
        p['reports'][0]['study_ids'].append('s2')
        packets = {r['work_package']['work_package_id']: r for r in review_packets(p)['packets']}
        planned = packets['WP-RECEIPT-REVIEW']['report_study_coverage']
        direct = packets['WP-EXTRACTION-REVIEW']['report_study_coverage']
        self.assertEqual(planned['membership_ledger'], [])
        self.assertEqual(planned['missing_report_study_memberships'], [])
        self.assertEqual(len(direct['missing_report_study_memberships']), 2)
        p['gaps'][1]['source_refs'] = [dict(kind='record', record_id='r2')]
        unrelated = review_packets(p, 'WP-EXTRACTION-REVIEW')['packets'][0]
        self.assertEqual(unrelated['report_study_coverage']['membership_ledger'], [])

    def test_work_snapshot_compare_and_adapter_smoke(self):
        p = multi(); self.assertEqual(len(review_packets(p)['packets']), 1)
        self.assertEqual(len(snapshot(p)['evidence_citation_index']), 3)
        self.assertFalse(compare_protocols(p, copy.deepcopy(p))['has_changes'])
        q = copy.deepcopy(p); q['reports'][0]['study_ids'].append('missing-study')
        self.assertEqual(compare_protocols(p, q)['after_report_counts']['included_studies'], 3)
        adapter = plural(fixture('adapter-protocol.json'))
        adapter['reports'][0]['study_ids'].append('not-extracted')
        pending = assemble(adapter, fixture('adapter-fixture.json'))['review_pending']
        reviews = [dict(row, decision='accept', reviewer='synthetic', reviewed_at='2026-11-03', rationale='Synthetic test assertion only') for row in pending]
        result = assemble(adapter, fixture('adapter-fixture.json'), reviews)
        self.assertEqual(result['research']['flow']['extracted'], 2)
        self.assertEqual(result['reports']['report_study_coverage']['missing_report_study_memberships'][0]['study_id'], 'not-extracted')


if __name__ == '__main__':
    unittest.main()
