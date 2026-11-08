"""Explicit typed pre-extraction context assertions never manufacture evidence."""
import copy
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from context_links import COMMON_FIELDS, DOMAIN_FIELDS
from evidence_workflow import run
from compare_runs import compare_protocols
from prisma_audit import export_audit
from research_bundle import build_bundle, verify
from review_handoff import handoff
from work_review import review_packets, navigation_summary, render_text, render_brief

ROOT = Path(__file__).resolve().parents[1]
SEARCH = dict(kind='planned_search', search_id='search-secondary')
RECORD = dict(kind='record', record_id='r1')
OTHER = dict(kind='record', record_id='r2')


class SourceContextTests(unittest.TestCase):
    def setUp(self):
        self.p = json.loads((ROOT / 'examples/source-work-protocol.json').read_text())
        contexts = json.loads((ROOT / 'examples/context-protocol.json').read_text())['contexts']
        for row in contexts:
            row.update(context_scope='source_review', evidence_ids=[], source_refs=[copy.deepcopy(SEARCH), copy.deepcopy(RECORD), copy.deepcopy(OTHER)])
        self.p['contexts'] = contexts
        self.p['gaps'][0]['context_ids'] = ['ctx-guideline']
        self.p['gaps'][1]['context_ids'] = ['ctx-development']

    def detach_receipts(self, p):
        p.pop('adapter_receipts', None)
        for row in p['searches'] + p['evidence']:
            row.pop('adapter_provenance', None)

    def test_both_domains_before_extraction_preserve_metadata_and_accounting(self):
        baseline = copy.deepcopy(self.p)
        baseline['contexts'] = []
        for w in baseline['gaps']:
            w.pop('context_ids')
        before, after = run(baseline), run(self.p)
        self.assertEqual(after['evidence'], [])
        for row in after['context']['context_ledger']:
            self.assertEqual(row['linked_study_ids'], [])
            original = next(c for c in self.p['contexts'] if c['context_id'] == row['context_id'])
            for key, value in original.items():
                self.assertEqual(row[key], value)
        for key in ('census_claim', 'conclusion_readiness', 'search_plan_audit', 'evidence'):
            self.assertEqual(before[key], after[key])
        a, b = export_audit(baseline), export_audit(self.p)
        for key in a:
            if key not in ('protocol_sha256', 'engine_sha256', 'work_traceability'):
                self.assertEqual(a[key], b[key], key)

    def test_missing_search_and_excluded_pending_records_do_not_change_eligibility(self):
        self.detach_receipts(self.p)
        self.p['screening'] = self.p['screening'][1:]
        self.p.pop('reports')
        original = copy.deepcopy(self.p)
        result = run(self.p)
        self.assertEqual(result['search_plan_audit']['missing_search_ids'], ['search-secondary'])
        self.assertEqual(result['evidence'], [])
        packets = review_packets(self.p)['packets']
        record = next(p for p in packets if p['work_package']['work_package_id'] == 'WP-EXTRACTION-REVIEW')
        self.assertIsNone(record['source_review_inputs'][0]['screening'])
        self.assertEqual(self.p, original)
        self.assertEqual(self.p['screening'][0]['decision'], 'exclude')

    def test_partial_intersections_visible_in_packets_handoff_and_comparison(self):
        packet = review_packets(self.p, 'WP-RECEIPT-REVIEW')['packets'][0]
        link = packet['contexts'][0]
        self.assertEqual(link['shared_source_refs'], [SEARCH])
        self.assertEqual(link['other_context_source_refs'], [RECORD, OTHER])
        self.assertEqual(link['other_work_source_refs'], [dict(kind='planned_search', search_id='search-primary')])
        self.assertEqual(link['work_evidence_ids'], [])
        self.assertEqual(packet['results'], [])
        brief = navigation_summary(review_packets(self.p))
        self.assertTrue(all(w['source_context_links'] for w in brief['work']))
        sheet = handoff(self.p)
        self.assertTrue(all(w['source_context_links'] for w in sheet['selected_work']))
        impact = compare_protocols(self.p, self.p)['context_work_impact']['contexts']
        for row in impact:
            self.assertEqual(row['before']['linked_evidence'], [])
            self.assertTrue(row['before']['work_links'][0]['shared_source_refs'])
            self.assertEqual(row['comparison_cues'], [])

    def test_unassigned_contexts_do_not_infer_work_or_result_coverage(self):
        for w in self.p['gaps']:
            w.pop('context_ids')
        self.assertEqual(run(self.p)['context']['unassigned_context_ids'], ['ctx-development', 'ctx-guideline'])
        audit = export_audit(self.p)
        self.assertEqual(len(audit['source_context_ledger']), 2)
        self.assertTrue(all(not r['explicit_work_ids'] for r in audit['source_context_ledger']))
        self.assertEqual(audit['evidence_links'], [])

    def test_strict_scopes_and_evidence_ids(self):
        for value in (None, True, 1, [], {}, '', 'source', 'SOURCE_REVIEW'):
            p = copy.deepcopy(self.p); p['contexts'][0]['context_scope'] = value
            with self.subTest(scope=value), self.assertRaises(ValueError):
                run(p)
        for value in (None, 'r1', ['r1'], ['missing'], ['r1', 'r1']):
            p = copy.deepcopy(self.p); p['contexts'][0]['evidence_ids'] = value
            with self.subTest(evidence=value), self.assertRaises(ValueError):
                run(p)
        for scope in ('extracted_evidence', None):
            p = copy.deepcopy(self.p)
            if scope is None: p['contexts'][0].pop('context_scope')
            else: p['contexts'][0]['context_scope'] = scope
            with self.assertRaisesRegex(ValueError, 'source_refs'):
                run(p)

    def test_exact_nonempty_known_unique_typed_references(self):
        bad = [None, {}, [], 'r1', [None], [True], [dict(kind='evidence', evidence_id='r1')],
               [dict(kind='record', record_id='unknown')], [dict(kind='planned_search', search_id='unknown')],
               [dict(kind='record', search_id='r1')], [dict(kind='record', record_id='r1', extra=True)],
               [RECORD, RECORD], [dict(kind='record', record_id=[])], [dict(kind='record', record_id=' ')]]
        for refs in bad:
            p = copy.deepcopy(self.p); p['contexts'][0]['source_refs'] = copy.deepcopy(refs)
            with self.subTest(refs=refs), self.assertRaises(ValueError): run(p)
        p = copy.deepcopy(self.p); p['contexts'][0].pop('source_refs')
        with self.assertRaises(ValueError): run(p)

    def test_no_search_record_inheritance_or_same_string_cross_kind_matching(self):
        p = copy.deepcopy(self.p)
        p['contexts'][0]['source_refs'] = [RECORD]
        with self.assertRaisesRegex(ValueError, 'exact typed'): run(p)
        self.detach_receipts(p)
        p['search_plan'].append(dict(search_id='r1', source='synthetic', query='synthetic', window='2020-2026'))
        p['gaps'][0]['source_refs'] = [dict(kind='planned_search', search_id='r1')]
        with self.assertRaisesRegex(ValueError, 'exact typed'): run(p)
        p['contexts'][0]['source_refs'].append(dict(kind='planned_search', search_id='r1'))
        self.assertEqual(len(run(p)['context']['context_ledger']), 2)

    def test_search_refs_require_declared_plan_but_record_refs_only_enumeration(self):
        self.detach_receipts(self.p)
        self.p.pop('search_plan')
        self.p['gaps'] = []
        self.p['contexts'][0]['source_refs'] = [dict(kind='planned_search', search_id='search-primary')]
        with self.assertRaisesRegex(ValueError, 'declared search'): run(self.p)
        for row in self.p['contexts']: row['source_refs'] = [RECORD]
        self.assertEqual(len(run(self.p)['context']['context_ledger']), 2)

    def test_omitted_scope_still_requires_extracted_evidence(self):
        self.p['gaps'] = []
        for row in self.p['contexts']:
            row.pop('context_scope'); row.pop('source_refs')
        with self.assertRaisesRegex(ValueError, 'known extracted evidence'): run(self.p)

    def test_ref_change_is_visible_without_implicit_review_reassessment(self):
        before = copy.deepcopy(self.p)
        self.p['contexts'][1]['source_refs'] = [RECORD]
        row = next(r for r in compare_protocols(before, self.p)['context_work_impact']['contexts'] if r['context_id'] == 'ctx-development')
        self.assertEqual(row['changed_context_assertion_fields'], ['source_refs'])
        self.assertIn('REVIEW_LABEL_RETAINED_AFTER_INPUT_CHANGE', row['comparison_cues'])
        self.assertEqual(row['review_validity'], 'NOT_VERIFIED')
        self.assertEqual(row['after']['work_links'][0]['shared_source_refs'], [RECORD])
        self.assertEqual(row['before']['work_links'][0]['other_context_source_refs'], [SEARCH, OTHER])
        self.assertEqual(row['after']['work_links'][0]['other_context_source_refs'], [])

    def test_common_and_domain_metadata_and_review_provenance_remain_required(self):
        for index in (0, 1):
            for field in COMMON_FIELDS + DOMAIN_FIELDS[self.p['contexts'][index]['domain']]:
                p = copy.deepcopy(self.p); p['contexts'][index].pop(field)
                with self.subTest(index=index, field=field), self.assertRaises(ValueError): run(p)
        for field in ('reviewer', 'reviewed_at'):
            p = copy.deepcopy(self.p); p['contexts'][1].pop(field)
            with self.subTest(field=field), self.assertRaises(ValueError): run(p)
        for value in ('20261103', '2026-W45-2', '2026-02-30', '2026-11-03T00:00:00Z', None, True):
            for field in ('accessed_at', 'reviewed_at'):
                p = copy.deepcopy(self.p); p['contexts'][1][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError): run(p)

    def test_pending_supplied_review_dates_are_strict(self):
        for value in ('20261103', '2026-02-30', None, True):
            p = copy.deepcopy(self.p); p['contexts'][0]['reviewed_at'] = value
            with self.subTest(value=value), self.assertRaises(ValueError): run(p)

    def test_pending_supplied_review_metadata_does_not_imply_review(self):
        for value in (None, True, '', '   ', []):
            p = copy.deepcopy(self.p); p['contexts'][0]['reviewer'] = value
            with self.subTest(value=value), self.assertRaises(ValueError): run(p)
        self.p['contexts'][0].update(reviewer='synthetic', reviewed_at='2026-11-03')
        context = next(c for c in run(self.p)['context']['context_ledger'] if c['context_id'] == 'ctx-guideline')
        self.assertEqual(context['review_status'], 'pending')
        self.assertEqual(context['reviewed_at'], '2026-11-03')
        self.assertIn('ctx-guideline', run(self.p)['context']['review_pending'])

    def test_source_context_cannot_link_evidence_work_or_synthesis(self):
        p = json.loads((ROOT / 'examples/context-protocol.json').read_text())
        p['contexts'] = copy.deepcopy(self.p['contexts'])
        for row in p['contexts']: row['source_refs'] = [RECORD]
        with self.assertRaisesRegex(ValueError, 'only to source_review'): run(p)
        p['gaps'] = []
        p['synthesis_statements'] = [dict(statement_id='s', text='Supplied synthetic statement', limitations='Synthetic only', evidence_ids=['r1'], context_ids=['ctx-guideline'])]
        with self.assertRaisesRegex(ValueError, 'share cited evidence'): run(p)

    def test_later_evidence_does_not_automatically_link_source_context_to_study(self):
        p = json.loads((ROOT / 'examples/context-protocol.json').read_text())
        p['contexts'] = copy.deepcopy(self.p['contexts'])
        for row in p['contexts']: row['source_refs'] = [RECORD]
        p['gaps'] = [copy.deepcopy(self.p['gaps'][1])]
        p['gaps'][0].pop('depends_on')
        result = run(p)
        self.assertTrue(result['evidence'])
        self.assertTrue(all(c['linked_study_ids'] == [] for c in result['context']['context_ledger']))
        packet = review_packets(p)['packets'][0]
        self.assertEqual(packet['results'], [])
        self.assertEqual(packet['source_review_inputs'][0]['existing_result_ids'], ['r1'])

    def test_planning_and_completion_bind_context_metadata_refs_and_reviews(self):
        w = self.p['gaps'][0]
        w.update(status='COMPLETE', artifact_locator='synthetic://note', acceptance_verified=True)
        r = run(self.p)
        target = next(t for t in r['planning']['review_targets'] if t['work_package_id'] == w['work_package_id'])
        completion = next(t for t in r['planning']['completion_ledger'] if t['work_package_id'] == w['work_package_id'])
        w['completion_basis_sha256'] = completion['current_basis_sha256']
        self.p['planning_decisions'] = [dict(work_package_id=w['work_package_id'], priority_rank=1, rationale='Synthetic rank', uncertainty='Unassessed', planner='synthetic', planned_at='2026-11-03', basis_sha256=target['basis_sha256'])]
        self.assertEqual(run(self.p)['planning']['work_with_stale_planning_assertion'], [])
        for field, value in [('title', 'Changed synthetic title'), ('source_refs', [SEARCH]), ('review_status', 'reviewed')]:
            p = copy.deepcopy(self.p); c = p['contexts'][0]; c[field] = copy.deepcopy(value)
            if field == 'review_status': c.update(reviewer='synthetic', reviewed_at='2026-11-03')
            result = run(p)
            with self.subTest(field=field):
                self.assertEqual(result['planning']['work_with_stale_planning_assertion'], [w['work_package_id']])
                row = next(t for t in result['planning']['completion_ledger'] if t['work_package_id'] == w['work_package_id'])
                self.assertEqual(row['source_match_status'], 'STALE_SOURCE')
                self.assertEqual(result['work_packages'][0]['status'], 'COMPLETE')

    def test_focused_context_comparison_does_not_infer_search_freshness(self):
        self.detach_receipts(self.p)
        other = copy.deepcopy(self.p); other['searches'][0]['query'] += ' changed'; other['search_plan'][0]['query'] += ' changed'
        rows = compare_protocols(self.p, other)['context_work_impact']['contexts']
        self.assertTrue(all(not row['comparison_cues'] for row in rows))
        before = run(self.p)['planning']['review_targets']
        after = run(other)['planning']['review_targets']
        self.assertNotEqual(before, after)

    def test_inputs_and_nested_outputs_are_isolated(self):
        original = copy.deepcopy(self.p)
        outputs = [run(self.p), review_packets(self.p), handoff(self.p), export_audit(self.p), compare_protocols(self.p, self.p)]
        self.assertEqual(self.p, original)
        outputs[0]['context']['context_ledger'][0]['source_refs'][0]['search_id'] = 'mutated'
        outputs[1]['packets'][0]['contexts'][0]['shared_source_refs'][0]['search_id'] = 'mutated'
        outputs[2]['selected_work'][0]['source_context_links'][0]['shared_source_refs'][0]['search_id'] = 'mutated'
        outputs[3]['source_context_ledger'][0]['context']['source_refs'][0]['search_id'] = 'mutated'
        outputs[4]['context_work_impact']['contexts'][0]['before']['context']['source_refs'][0]['search_id'] = 'mutated'
        self.assertEqual(self.p, original)
        self.assertEqual(run(self.p), run(original))

    def test_bundle_verification_json_and_csv_preserve_explicit_scope(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'source-contexts.zip'; path.write_bytes(build_bundle(json.dumps(self.p).encode()))
            self.assertTrue(verify(path)['valid'])
            with zipfile.ZipFile(path) as archive:
                result = json.loads(archive.read('research.json'))
                self.assertTrue(all(c['context_scope'] == 'source_review' for c in result['context']['context_ledger']))
                rows = list(csv.DictReader(io.StringIO(archive.read('work-packages.csv').decode())))
                self.assertTrue(all(json.loads(r['context_ids']) for r in rows))
                self.assertTrue(all(json.loads(r['evidence_ids']) == [] for r in rows))

    def test_hostile_text_and_unicode_real_cli(self):
        self.p['contexts'][0]['title'] = '합성 안내\nFORGED\x1b[31m'
        for render in (render_text, render_brief):
            text = render(review_packets(self.p))
            self.assertNotIn('\x1b', text)
            self.assertNotIn('\nFORGED', text)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / '합성.json'; path.write_text(json.dumps(self.p, ensure_ascii=False), encoding='utf-8')
            for script, options in [('work_review.py', ['--text']), ('work_review.py', ['--brief']), ('review_handoff.py', ['--text']), ('prisma_audit.py', ['--text'])]:
                proc = subprocess.run([sys.executable, str(ROOT / script), str(path)] + options, cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
                with self.subTest(script=script, options=options):
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    self.assertNotIn('\x1b', proc.stdout)
                    self.assertNotIn('\nFORGED', proc.stdout)
                    self.assertIn('ctx-guideline', proc.stdout)

    def test_explicit_legacy_scope_allowed_and_omitted_not_injected(self):
        p = json.loads((ROOT / 'examples/context-protocol.json').read_text())
        self.assertTrue(all('context_scope' not in r for r in run(p)['context']['context_ledger']))
        p['contexts'][0]['context_scope'] = 'extracted_evidence'
        self.assertEqual(next(c for c in run(p)['context']['context_ledger'] if c['context_id'] == 'ctx-guideline')['linked_study_ids'], ['s1'])


if __name__ == '__main__':
    unittest.main()
