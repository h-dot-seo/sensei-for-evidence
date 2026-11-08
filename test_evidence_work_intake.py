"""Independent synthetic evidence-work intake, preservation and exact-replay tests."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import evidence_work_intake as intake
from evidence_workflow import run
from json_io import canonical_json_bytes
from prisma_reports import report_flow

ROOT = Path(__file__).resolve().parent
UNSET = object()


def fixture(name):
    return json.loads((ROOT / 'examples' / name).read_text(encoding='utf-8'))


def candidates(wid='WP-FICTIONAL-EVIDENCE', evidence_ids=None, dependencies=None):
    return dict(schema_version=1, candidates=[dict(work_package=dict(
        work_package_id=wid, work_type='evidence_review',
        question='Supplied fictional review question?', deliverable='Supplied fictional metadata note.',
        acceptance_criterion='A human checks the supplied fictional note; no scientific conclusion.',
        evidence_ids=list(['result-C-manual', 'result-A-second'] if evidence_ids is None else evidence_ids),
        depends_on=list([] if dependencies is None else dependencies), status='PLANNED'),
        proposed_by='Fictional proposer', proposed_at='2026-11-04',
        proposal_note='Explicit fictional human-authored bookkeeping work.')])


class EvidenceWorkIntakeTests(unittest.TestCase):
    def setUp(self):
        self.p = fixture('result-source-current.json')
        self.c = candidates()

    def review(self, p=None, c=None):
        result = intake.prepare(self.p if p is None else p, self.c if c is None else c)
        review = result['review_document']
        review.update(receipt_id='fictional-evidence-work-receipt', decision='import_evidence_work',
                      reviewer='Fictional reviewer', reviewed_at='2026-11-04',
                      rationale='Explicit fictional work import, not scientific approval.')
        return review

    def assembled(self, p=None, c=None):
        p = self.p if p is None else p
        c = self.c if c is None else c
        return intake.assemble(p, c, self.review(p, c))

    def reject(self, c=UNSET, p=None):
        with self.assertRaises((ValueError, TypeError)):
            intake.prepare(self.p if p is None else p, self.c if c is UNSET else c)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'evidence_work_intake.py'), *map(str, args)],
                              cwd=ROOT, capture_output=True,
                              env=dict(os.environ, PYTHONIOENCODING='ascii', PYTHONUTF8='0', PYTHONDONTWRITEBYTECODE='1'))

    def test_template_only_copies_selection_and_structural_constants(self):
        refs = dict(schema_version=1, evidence_ids=['result-A-second', 'result-C-manual'])
        old = copy.deepcopy((self.p, refs))
        result = intake.template(self.p, refs)
        self.assertEqual(result, intake.template(self.p, refs))
        self.assertEqual((self.p, refs), old)
        work = result['candidate_document']['candidates'][0]['work_package']
        self.assertEqual(set(work), intake.WORK_FIELDS)
        self.assertEqual(work['evidence_ids'], refs['evidence_ids'])
        self.assertEqual(work['work_type'], 'evidence_review')
        self.assertEqual(work['status'], 'PLANNED')
        for key in ('work_package_id', 'question', 'deliverable', 'acceptance_criterion', 'depends_on'):
            self.assertIsNone(work[key])
        for key in ('proposed_by', 'proposed_at', 'proposal_note'):
            self.assertIsNone(result['candidate_document']['candidates'][0][key])
        self.assertFalse(result['protocol_changed'])
        self.reject(result['candidate_document'])

    def test_template_exact_schema_and_known_normalized_result_selection(self):
        refs = dict(schema_version=1, evidence_ids=['result-C-manual'])
        for bad in (None, [], True, {}, dict(refs, extra=1), dict(refs, schema_version=True),
                    dict(refs, schema_version=2), dict(schema_version=1, source_refs=[])):
            with self.subTest(bad=bad), self.assertRaises((ValueError, TypeError)):
                intake.template(self.p, bad)
        for ids in (None, [], {}, True, 'result-C-manual', [''], [' '], [True], [1], [None], [[]],
                    ['result-C-manual'] * 2, ['result-c-manual'], ['result-C-manual '],
                    ['record-one'], ['report-one'], ['study-C'], ['source-main'], ['missing']):
            with self.subTest(ids=ids), self.assertRaises((ValueError, TypeError)):
                intake.template(self.p, dict(refs, evidence_ids=ids))

    def test_exact_selected_raw_normalized_snapshots_and_planning_targets(self):
        self.c['candidates'][0]['work_package']['evidence_ids'].reverse()
        result = self.assembled()
        target = result['receipt']['target']
        wid = self.c['candidates'][0]['work_package']['work_package_id']
        self.assertEqual(target['target_type'], 'manual_evidence_work_intake')
        self.assertEqual(target['candidate_work_packages'], [dict(candidate_index=0, input_pointer='/gaps/2',
                         work_package=self.c['candidates'][0]['work_package'])])
        expected = []
        for index in (3, 2):
            row = self.p['evidence'][index]
            expected.append(dict(candidate_index=0, work_package_id=wid, evidence_id=row['evidence_id'],
                input_pointer=f'/evidence/{index}', identity_origin='EXPLICIT_EVIDENCE_ID',
                raw_evidence=row, normalized_evidence=row))
        self.assertEqual(target['selected_evidence'], expected)
        from screening_links import prepare_targets
        expected_records = [row for row in prepare_targets(self.p)['record_targets'] if row['record_id'] == 'record-one']
        self.assertEqual(target['selected_record_targets'], expected_records)
        after = run(result['protocol_candidate'])
        self.assertEqual(target['selected_planning_targets'],
                         [row for row in after['planning']['review_targets'] if row['work_package_id'] == wid])
        self.assertEqual(target['target_sha256'], intake.digest({k: v for k, v in target.items() if k != 'target_sha256'}))

    def test_selection_repeated_across_tasks_is_not_collapsed(self):
        second = candidates('WP-SECOND', ['result-C-manual'])['candidates'][0]
        self.c['candidates'].append(second)
        rows = self.assembled()['receipt']['target']['selected_evidence']
        self.assertEqual([r['candidate_index'] for r in rows], [0, 0, 1])
        self.assertEqual([r['evidence_id'] for r in rows], ['result-C-manual', 'result-A-second', 'result-C-manual'])

    def test_legacy_evidence_identity_exposed_without_rewriting_raw_row(self):
        p = fixture('context-protocol.json')
        self.assertNotIn('evidence_id', p['evidence'][0])
        c = candidates(evidence_ids=['r1'])
        record = self.assembled(p, c)
        snapshot = record['receipt']['target']['selected_evidence'][0]
        self.assertEqual(snapshot['identity_origin'], 'LEGACY_RECORD_ID')
        self.assertEqual(snapshot['input_pointer'], '/evidence/0')
        self.assertEqual(snapshot['raw_evidence'], p['evidence'][0])
        self.assertEqual(snapshot['normalized_evidence'], dict(p['evidence'][0], evidence_id='r1'))
        self.assertNotIn('evidence_id', record['protocol_candidate']['evidence'][0])
        self.assertTrue(intake.verify(p, record)['valid'])
        p['evidence'][0]['evidence_id'] = 'explicit-result'
        p['gaps'] = []
        p['contexts'] = []
        self.reject(c, p)
        self.assertTrue(intake.verify(p, self.assembled(p, candidates(evidence_ids=['explicit-result'])))['valid'])

    def test_prepare_is_immutable_deterministic_and_review_is_blank(self):
        old = copy.deepcopy((self.p, self.c))
        prepared = intake.prepare(self.p, self.c)
        self.assertEqual(prepared, intake.prepare(self.p, self.c))
        self.assertEqual((self.p, self.c), old)
        review = prepared['review_document']
        self.assertEqual(set(review), intake.REVIEW_FIELDS)
        self.assertEqual(review['target_sha256'], prepared['target']['target_sha256'])
        self.assertTrue(all(v is None for k, v in review.items() if k not in ('schema_version', 'target_sha256')))
        with self.assertRaises(ValueError):
            intake.assemble(self.p, self.c, review)

    def test_append_only_preserves_every_raw_field_and_implicit_work_defaults(self):
        self.p['opaque_metadata'] = {'ordered': ['β', None, {'verbatim': '  keep\nthis  '}], 'number': 0}
        original = canonical_json_bytes(self.p)
        record = self.assembled()
        new = record['protocol_candidate']
        self.assertEqual(set(record), {'schema_version', 'kind', 'receipt', 'protocol_candidate'})
        self.assertEqual(record['kind'], 'detached_evidence_work_intake')
        self.assertEqual(new['gaps'], self.p['gaps'] + [r['work_package'] for r in self.c['candidates']])
        self.assertEqual({k: v for k, v in new.items() if k != 'gaps'}, {k: v for k, v in self.p.items() if k != 'gaps'})
        self.assertNotIn('status', new['gaps'][0])
        self.assertNotIn('depends_on', new['gaps'][0])
        self.assertEqual(canonical_json_bytes(self.p), original)
        self.assertTrue(intake.verify(self.p, record)['valid'])
        self.assertEqual(record, self.assembled())
        self.reject(p=new)

    def test_no_eligibility_accounting_review_or_readiness_changes(self):
        record = self.assembled()
        before, after = run(self.p), run(record['protocol_candidate'])
        for key in ('flow', 'evidence', 'coverage', 'search_plan_audit', 'record_provenance',
                    'screening_ledger', 'conclusion_readiness', 'census_claim', 'extraction_completeness',
                    'report_review', 'report_study_inventory', 'report_study_inventory_review', 'report_study_coverage'):
            self.assertEqual(before[key], after[key], key)
        self.assertEqual(record['receipt']['before_flow'], record['receipt']['after_flow'])
        self.assertEqual(record['receipt']['before_report_flow'], record['receipt']['after_report_flow'])
        self.assertNotIn('planning_decisions', record['protocol_candidate'])
        self.assertEqual(after['planning']['completion_ledger'][-1]['acceptance_assessment'], 'NOT_PERFORMED')

    def test_strict_document_candidate_and_work_shapes(self):
        for bad in (None, [], True, {}, dict(self.c, schema_version=True), dict(self.c, schema_version=2),
                    dict(self.c, extra=1), dict(self.c, candidates=[]), dict(self.c, candidates={}),
                    dict(self.c, candidates=[None]), dict(self.c, candidates=self.c['candidates'] * 101)):
            with self.subTest(bad=repr(bad)[:60]):
                self.reject(bad)
        for scope in ('candidate', 'work'):
            original = self.c['candidates'][0] if scope == 'candidate' else self.c['candidates'][0]['work_package']
            for field in original:
                c = copy.deepcopy(self.c)
                target = c['candidates'][0] if scope == 'candidate' else c['candidates'][0]['work_package']
                del target[field]
                with self.subTest(scope=scope, missing=field):
                    self.reject(c)
            c = copy.deepcopy(self.c)
            (c['candidates'][0] if scope == 'candidate' else c['candidates'][0]['work_package'])['extra'] = 1
            self.reject(c)

    def test_human_meaning_and_real_calendar_dates_are_required(self):
        fields = [('candidate', 'proposed_by'), ('candidate', 'proposed_at'), ('candidate', 'proposal_note')]
        fields += [('work', x) for x in ('work_package_id', 'question', 'deliverable', 'acceptance_criterion')]
        for scope, field in fields:
            for value in (None, True, 0, [], {}, '', ' \t\n'):
                c = copy.deepcopy(self.c)
                (c['candidates'][0] if scope == 'candidate' else c['candidates'][0]['work_package'])[field] = value
                with self.subTest(field=field, value=value):
                    self.reject(c)
        for value in ('2026-02-29', '2026-2-04', '2026-11-04\n', '0000-01-01', '2026-11-04T00:00:00Z'):
            c = copy.deepcopy(self.c)
            c['candidates'][0]['proposed_at'] = value
            self.reject(c)
        self.c['candidates'][0]['proposed_at'] = '2024-02-29'
        intake.prepare(self.p, self.c)

    def test_no_source_scope_completion_artifact_priority_or_execution_fields(self):
        for field, value in [('work_type', 'source_review'), ('work_type', None), ('status', 'COMPLETE'),
                            ('status', 'IN_PROGRESS'), ('status', None), ('status', True), ('evidence_ids', []),
                            ('evidence_ids', None), ('evidence_ids', ['record-one']), ('evidence_ids', ['result-A'] * 2),
                            ('source_refs', []), ('document_source_ids', ['source-main']), ('priority_rank', 1),
                            ('artifact_locator', 'synthetic:note'), ('acceptance_verified', True),
                            ('completion_basis_sha256', '0' * 64), ('completion_review', {}),
                            ('scientific_task', 'Synthetic prohibited field'), ('procedure', 'Synthetic prohibited field')]:
            c = copy.deepcopy(self.c)
            c['candidates'][0]['work_package'][field] = value
            with self.subTest(field=field, value=value):
                self.reject(c)

    def test_explicit_existing_and_forward_same_batch_dependencies(self):
        self.c = candidates(dependencies=['WP-MEMBERSHIP-SOURCES'])
        second = candidates('WP-SECOND', dependencies=['WP-FICTIONAL-EVIDENCE'])['candidates'][0]
        self.c['candidates'].insert(0, second)
        new = self.assembled()['protocol_candidate']
        self.assertEqual(new['gaps'][-2:], [r['work_package'] for r in self.c['candidates']])
        order = run(new)['execution_order']
        self.assertLess(order.index('WP-MEMBERSHIP-SOURCES'), order.index('WP-FICTIONAL-EVIDENCE'))
        self.assertLess(order.index('WP-FICTIONAL-EVIDENCE'), order.index('WP-SECOND'))
        self.assertEqual(new['gaps'][-2]['depends_on'], ['WP-FICTIONAL-EVIDENCE'])

    def test_dependency_missing_duplicate_cycle_and_self_rejected(self):
        for deps in (None, 'WP-RESULT-LINKS', ['missing'], ['WP-FICTIONAL-EVIDENCE'],
                     ['WP-RESULT-LINKS'] * 2, [True], [[]], [' ']):
            c = copy.deepcopy(self.c)
            c['candidates'][0]['work_package']['depends_on'] = deps
            with self.subTest(deps=deps):
                self.reject(c)
        c = candidates(dependencies=['WP-SECOND'])
        c['candidates'].append(candidates('WP-SECOND', dependencies=['WP-FICTIONAL-EVIDENCE'])['candidates'][0])
        self.reject(c)
        c = copy.deepcopy(self.c)
        c['candidates'].append(copy.deepcopy(c['candidates'][0]))
        self.reject(c)
        self.reject(candidates('WP-RESULT-LINKS'))

    def test_normalized_legacy_work_id_collision_and_raw_prefix_preserved(self):
        self.p['gaps'][0].pop('work_package_id')
        self.reject(candidates('WP-001'))
        record = self.assembled(c=candidates(dependencies=['WP-001']))
        self.assertNotIn('work_package_id', record['protocol_candidate']['gaps'][0])
        self.assertEqual(record['protocol_candidate']['gaps'][:2], self.p['gaps'])

    def test_evidence_context_requires_exact_shared_result_and_stays_supplied(self):
        contexts = fixture('context-protocol.json')['contexts']
        for row in contexts:
            row['evidence_ids'] = ['result-C-manual']
        self.p['contexts'] = contexts
        work = self.c['candidates'][0]['work_package']
        work.update(context='Human-authored fictional context.', context_ids=['ctx-guideline'])
        record = self.assembled()
        self.assertEqual(record['protocol_candidate']['gaps'][-1], work)
        basis = record['receipt']['target']['selected_planning_targets'][0]['basis']
        self.assertEqual([c['context_id'] for c in basis['contexts']], ['ctx-guideline'])
        for field, values in [('context', (None, '', ' ', True, [])),
                              ('context_ids', (None, [], ['missing'], ['ctx-guideline'] * 2, True))]:
            for value in values:
                c = copy.deepcopy(self.c)
                c['candidates'][0]['work_package'][field] = value
                self.reject(c)
        c = copy.deepcopy(self.c)
        c['candidates'][0]['work_package']['evidence_ids'] = ['result-A']
        self.reject(c)
        self.p['contexts'][0].update(context_scope='source_review', evidence_ids=[],
                                    source_refs=[dict(kind='record', record_id='record-one')])
        self.reject()

    def test_direct_source_document_dependency_binds_without_own_document_scope(self):
        self.p['gaps'][1]['document_source_ids'] = ['source-main']
        self.c = candidates(dependencies=['WP-MEMBERSHIP-SOURCES'])
        record = self.assembled()
        basis = record['receipt']['target']['selected_planning_targets'][0]['basis']
        self.assertNotIn('document_source_context', basis)
        self.assertEqual([r['work_package_id'] for r in basis['direct_dependency_document_sources']], ['WP-MEMBERSHIP-SOURCES'])
        self.assertEqual(basis['direct_dependency_document_sources'][0]['document_source_context']['sources'][0]['source']['source_id'], 'source-main')
        self.assertNotIn('document_source_ids', record['protocol_candidate']['gaps'][-1])
        new = record['protocol_candidate']
        expected = next(t for t in run(new)['planning']['review_targets'] if t['work_package_id'] == 'WP-FICTIONAL-EVIDENCE')
        new['report_sources'][0]['document_version'] += ' changed synthetic metadata'
        changed = next(t for t in run(new)['planning']['review_targets'] if t['work_package_id'] == 'WP-FICTIONAL-EVIDENCE')
        self.assertNotEqual(expected['basis_sha256'], changed['basis_sha256'])

    def test_existing_planning_completion_and_stale_assertions_remain_unchanged(self):
        work = self.p['gaps'][0]
        work.update(status='COMPLETE', artifact_locator='synthetic:old-note', acceptance_verified=True)
        before = run(self.p)
        binding = next(r for r in before['planning']['completion_ledger'] if r['work_package_id'] == work['work_package_id'])
        work['completion_basis_sha256'] = binding['current_basis_sha256']
        target = next(r for r in before['planning']['review_targets'] if r['work_package_id'] == work['work_package_id'])
        self.p['planning_decisions'] = [dict(work_package_id=work['work_package_id'], priority_rank=1,
            rationale='Fictional supplied rank', uncertainty='No scientific priority established',
            planner='Fictional planner', planned_at='2026-11-04', basis_sha256=target['basis_sha256'])]
        for stale in (False, True):
            if stale:
                self.p['evidence'][0]['result'] += ' Changed synthetic text.'
            before = run(self.p)
            new = self.assembled()['protocol_candidate']
            after = run(new)
            self.assertEqual(new['planning_decisions'], self.p['planning_decisions'])
            self.assertEqual(new['gaps'][:2], self.p['gaps'])
            old_ids = {w['work_package_id'] for w in before['work_packages']}
            for key in ('review_targets', 'planning_ledger', 'completion_ledger'):
                self.assertEqual(before['planning'][key], [r for r in after['planning'][key] if r['work_package_id'] in old_ids])

    def test_mock_adapter_provenance_remains_valid_and_unmodified(self):
        import offline_adapter
        p = offline_adapter.assemble(fixture('adapter-protocol.json'), fixture('adapter-fixture.json'),
                                     fixture('adapter-reviews.json'))['protocol']
        record = self.assembled(p, candidates(evidence_ids=['e1', 'e2']))
        self.assertEqual({k: v for k, v in record['protocol_candidate'].items() if k != 'gaps'},
                         {k: v for k, v in p.items() if k != 'gaps'})
        self.assertEqual(run(record['protocol_candidate'])['evidence'], run(p)['evidence'])
        self.assertTrue(intake.verify(p, record)['valid'])

    def test_csv_provenance_remains_valid_and_unmodified(self):
        import bibliographic_intake
        import bibliographic_review
        p = fixture('bibliographic-base.json')
        artifact = bibliographic_intake.prepare(p, b'record_id,source_locator\nfictional-input,synthetic:export\n',
                                                'local-primary', '2026-11-04T00:00:00Z')
        choices = bibliographic_review.template(artifact)
        choices['resolutions'][0].update(disposition='new_record', record_id='record-one', rationale='Synthetic identity assertion')
        review = bibliographic_review.prepare_review(p, artifact, choices)['review_document']
        review['review'].update(reviewer='Fictional reviewer', reviewed_at='2026-11-04',
                               rationale='Fictional collection', decision='import_for_screening')
        p = bibliographic_review.assemble(p, artifact, review)['protocol_candidate']
        p['screening'] = [dict(record_id='record-one', decision='include', reason='Fictional scope')]
        evidence = copy.deepcopy(self.p['evidence'][0])
        evidence.update(evidence_id='csv-result', record_id='record-one')
        p['evidence'] = [evidence]
        record = self.assembled(p, candidates(evidence_ids=['csv-result']))
        new = record['protocol_candidate']
        self.assertEqual({k: v for k, v in new.items() if k != 'gaps'}, {k: v for k, v in p.items() if k != 'gaps'})
        self.assertEqual(run(new)['bibliographic_collection'], run(p)['bibliographic_collection'])
        self.assertTrue(intake.verify(p, record)['valid'])

    def test_absent_reports_preserved_and_empty_report_catalog_cannot_hide_evidence(self):
        p = fixture('context-protocol.json')
        p.pop('reports', None)
        c = candidates(evidence_ids=['r1'])
        record = self.assembled(p, c)
        self.assertNotIn('reports', record['protocol_candidate'])
        self.assertIsNone(record['receipt']['before_report_flow'])
        self.assertIsNone(record['receipt']['after_report_flow'])
        # Unlike source-only work, real result links cannot coexist with an empty
        # supplied report catalog: the existing report flow requires membership.
        for value in ([], None, {}, [None]):
            p['reports'] = value
            self.reject(c, p)

    def test_full_protocol_and_report_validation_happen_before_and_after(self):
        with patch.object(intake, 'run', wraps=run) as runs, patch.object(intake, 'report_flow', wraps=report_flow) as flows:
            intake.prepare(self.p, self.c)
        self.assertEqual(runs.call_count, 2)
        self.assertEqual(flows.call_count, 2)
        for call in flows.call_args_list:
            self.assertIs(call.kwargs['include_csv'], False)
        p = copy.deepcopy(self.p)
        p['reports'][0]['retrieval'] = 'invalid'
        self.reject(p=p)
        p = copy.deepcopy(self.p)
        p['evidence'] = [None]
        self.reject(p=p)

    def test_review_exact_schema_decision_identity_date_and_hash(self):
        review = self.review()
        for field in review:
            r = copy.deepcopy(review)
            del r[field]
            with self.subTest(missing=field), self.assertRaises(ValueError):
                intake.assemble(self.p, self.c, r)
        for field in ('receipt_id', 'reviewer', 'reviewed_at', 'rationale'):
            for value in (None, ' ', True, [], {}):
                r = dict(review, **{field: value})
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    intake.assemble(self.p, self.c, r)
        for changes in ({'schema_version': True}, {'extra': 1}, {'decision': 'import_source_work'},
                        {'decision': 'approve'}, {'target_sha256': '0' * 64}, {'target_sha256': 'A' * 64},
                        {'reviewed_at': '2026-02-29'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                intake.assemble(self.p, self.c, dict(review, **changes))

    def test_stale_protocol_result_candidate_and_engine_review_never_rebased(self):
        review = self.review()
        for mutate in (lambda p: p.update(opaque='changed'),
                       lambda p: p['evidence'][2].update(result='Changed synthetic result'),
                       lambda p: p['evidence'].reverse()):
            p = copy.deepcopy(self.p)
            mutate(p)
            with self.assertRaisesRegex(ValueError, 'no automatic rebase'):
                intake.assemble(p, self.c, review)
        c = copy.deepcopy(self.c)
        c['candidates'][0]['proposal_note'] = 'Changed synthetic note'
        with self.assertRaisesRegex(ValueError, 'no automatic rebase'):
            intake.assemble(self.p, c, review)
        hashes = intake._implementation_hashes()
        hashes['evidence_work_intake.py'] = '0' * 64
        with patch.object(intake, '_implementation_hashes', return_value=hashes), self.assertRaisesRegex(ValueError, 'no automatic rebase'):
            intake.assemble(self.p, self.c, review)

    def test_exact_replay_rejects_resealed_extra_and_typed_tampering(self):
        record = self.assembled()
        for mutate in (lambda r: r.update(extra=True), lambda r: r.update(schema_version=True),
                       lambda r: r.update(kind='detached_source_work_intake'),
                       lambda r: r['receipt'].update(extra=True), lambda r: r['receipt'].update(external_calls=False),
                       lambda r: r['protocol_candidate'].update(version='forged'),
                       lambda r: r['receipt']['target'].update(extra=True),
                       lambda r: r['receipt']['target']['selected_evidence'][0].update(identity_origin='LEGACY_RECORD_ID'),
                       lambda r: r['receipt']['target']['selected_evidence'][0]['raw_evidence'].update(result='Forged'),
                       lambda r: r['receipt']['candidate_document']['candidates'][0].update(proposal_note='Forged')):
            bad = copy.deepcopy(record)
            mutate(bad)
            bad['receipt']['receipt_sha256'] = intake.digest({k: v for k, v in bad['receipt'].items() if k != 'receipt_sha256'})
            with self.assertRaises(ValueError):
                intake.verify(self.p, bad)
        changed = self.review()
        changed.update(reviewer='Another fictional person', receipt_id='rewritten')
        rewritten = intake.assemble(self.p, self.c, changed)
        self.assertTrue(intake.verify(self.p, rewritten)['valid'])
        self.assertIn('unsigned', rewritten['receipt']['boundary'])

    def test_negative_claims_are_explicit_and_not_scientific_approval(self):
        record = self.assembled()
        verify = intake.verify(self.p, record)
        template = intake.template(self.p, dict(schema_version=1, evidence_ids=['result-C-manual']))
        for result in (record['receipt'], record['receipt']['target']['negative_claims'], verify, template,
                       intake.prepare(self.p, self.c)):
            for key, value in intake.NEGATIVE_CLAIMS.items():
                self.assertEqual(result[key], value)
        self.assertEqual(record['receipt']['retained_evidence_snapshot_scope'], 'DETACHED_RECORD_ONLY')
        self.assertEqual(record['receipt']['proposal_review_scope'], 'DETACHED_RECORD_ONLY')
        self.assertEqual(record['receipt']['execution'], 'NOT_PERFORMED')
        self.assertEqual(record['receipt']['scientific_task_generation'], 'NOT_PERFORMED')
        self.assertEqual(record['receipt']['conclusion_readiness'], 'NOT_READY')

    def test_runtime_fingerprints_cover_direct_helpers_and_engine(self):
        from research_bundle import engine_hashes
        actual = intake._implementation_hashes()
        self.assertEqual(set(actual), set(engine_hashes()) | {'nbib_intake.py', 'evidence_work_intake.py'})
        for name, digest in actual.items():
            self.assertEqual(digest, hashlib.sha256((ROOT / name).read_bytes()).hexdigest())

    def test_strict_json_input_and_byte_limits(self):
        for name, value in [('MAX_CANDIDATE_BYTES', 10_000_000), ('MAX_PROTOCOL_BYTES', 50_000_000),
                            ('MAX_APPLICATION_BYTES', 50_000_000), ('MAX_CANDIDATES', 100)]:
            self.assertEqual(getattr(intake, name), value)
        record = self.assembled()
        for name, action in [('MAX_CANDIDATE_BYTES', lambda: intake.prepare(self.p, self.c)),
                             ('MAX_PROTOCOL_BYTES', lambda: intake.prepare(self.p, self.c)),
                             ('MAX_APPLICATION_BYTES', lambda: intake.verify(self.p, record))]:
            with patch.object(intake, name, 10), self.assertRaises(ValueError):
                action()
        for value in (float('nan'), float('inf'), {1: 'non-string key'}, ('tuple',), {1, 2}, '\ud800'):
            p = copy.deepcopy(self.p)
            p['opaque'] = value
            with self.assertRaises((ValueError, TypeError, UnicodeError)):
                intake.prepare(p, self.c)
        p = copy.deepcopy(self.p)
        p['cycle'] = p
        with self.assertRaises((ValueError, TypeError, RecursionError)):
            intake.prepare(p, self.c)

    def test_candidate_count_limit_and_no_mutable_aliases(self):
        with patch.object(intake, 'MAX_CANDIDATES', 2):
            c = copy.deepcopy(self.c)
            c['candidates'].append(candidates('WP-SECOND')['candidates'][0])
            prepared = intake.prepare(self.p, c)
            c['candidates'].append(candidates('WP-THIRD')['candidates'][0])
            self.reject(c)
        original = copy.deepcopy((self.p, self.c))
        record = self.assembled()
        record['receipt']['target']['selected_evidence'][0]['raw_evidence']['result'] = 'Mutated output'
        self.assertEqual((self.p, self.c), original)
        self.assertNotEqual(record['protocol_candidate']['evidence'][2]['result'], 'Mutated output')

    def test_no_network_external_process_or_source_opening(self):
        with patch('urllib.request.urlopen', side_effect=AssertionError('no network')), \
             patch('socket.socket', side_effect=AssertionError('no network')), \
             patch('subprocess.run', side_effect=AssertionError('no external process')):
            record = self.assembled()
            self.assertTrue(intake.verify(self.p, record)['valid'])
        self.assertIsInstance(intake.render_text(record), str)

    def test_manual_result_intake_to_work_packets_audit_status_bundle(self):
        import result_intake
        import research_bundle
        from prisma_audit import export_audit
        from research_status import status
        from work_review import review_packets
        p = fixture('report-study-inventory-reviews.json')
        results = fixture('manual-result-candidates.json')
        review = result_intake.prepare(p, results)['review_document']
        review.update(receipt_id='fictional-result-receipt', reviewer='Fictional reviewer', reviewed_at='2026-11-04',
                      rationale='Explicit fictional extraction import.', decision='import_results')
        imported = result_intake.assemble(p, results, review)
        self.assertTrue(result_intake.verify(p, imported)['valid'])
        current = imported['protocol_candidate']
        ids = [r['evidence']['evidence_id'] for r in results['candidates']]
        c = candidates(evidence_ids=ids, dependencies=['WP-MEMBERSHIP-SOURCES'])
        record = self.assembled(current, c)
        self.assertTrue(intake.verify(current, record)['valid'])
        new = record['protocol_candidate']
        packet = review_packets(new, work_package_id='WP-FICTIONAL-EVIDENCE')['packets'][0]
        self.assertEqual(packet['work_package']['status'], 'PLANNED')
        self.assertEqual(packet['work_package']['blocked_by'], ['WP-MEMBERSHIP-SOURCES'])
        self.assertEqual({r['evidence']['evidence_id'] for r in packet['results']}, set(ids))
        self.assertEqual(run(current)['flow'], run(new)['flow'])
        self.assertEqual(status(new)['conclusion_readiness'], 'NOT_READY')
        self.assertIsInstance(export_audit(new), dict)
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / 'fictional.zip'
            archive.write_bytes(research_bundle.build_bundle(canonical_json_bytes(new)))
            self.assertTrue(research_bundle.verify(archive)['valid'])

    def test_cli_template_stdout_and_exclusive_candidate_export(self):
        refs = dict(schema_version=1, evidence_ids=['result-C-manual'])
        with tempfile.TemporaryDirectory() as temp:
            d = Path(temp)
            p, r, out = d / 'p.json', d / 'refs.json', d / 'draft.json'
            p.write_bytes(canonical_json_bytes(self.p))
            r.write_bytes(canonical_json_bytes(refs))
            result = self.cli('template', p, r)
            self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8'))
            self.assertEqual(json.loads(result.stdout), intake.template(self.p, refs))
            result = self.cli('template', p, r, '--candidate-output', out, '--text')
            self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8'))
            self.assertEqual(json.loads(out.read_bytes()), intake.template(self.p, refs)['candidate_document'])
            old = out.read_bytes()
            self.assertNotEqual(self.cli('template', p, r, '--candidate-output', out).returncode, 0)
            self.assertEqual(out.read_bytes(), old)

    def test_cli_roundtrip_utf8_controls_and_exclusive_outputs(self):
        self.c['candidates'][0]['work_package']['question'] = 'Fictional 합성\n\x1b[31m question'
        with tempfile.TemporaryDirectory() as temp:
            d = Path(temp)
            p, c, r = d / 'p.json', d / 'c.json', d / 'r.json'
            target, out, derived = d / 'target.json', d / 'out.json', d / 'derived.json'
            p.write_bytes(canonical_json_bytes(self.p))
            c.write_bytes(canonical_json_bytes(self.c))
            r.write_bytes(canonical_json_bytes(self.review()))
            calls = [(('target', p, c, '--output', target, '--text'), target),
                     (('assemble', p, c, r, '--output', out, '--text'), out),
                     (('verify', p, out, '--protocol-output', derived, '--text'), derived)]
            for args, path in calls:
                result = self.cli(*args)
                self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8'))
                self.assertNotIn(b'\x1b', result.stdout)
            self.assertEqual(json.loads(derived.read_bytes()), json.loads(out.read_bytes())['protocol_candidate'])
            for args, path in calls:
                old = path.read_bytes()
                self.assertNotEqual(self.cli(*args).returncode, 0)
                self.assertEqual(path.read_bytes(), old)
            old = p.read_bytes()
            self.assertNotEqual(self.cli('target', p, c, '--output', p).returncode, 0)
            self.assertEqual(p.read_bytes(), old)

    def test_cli_strict_json_rejected_before_output_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            d = Path(temp)
            p, c, out = d / 'p.json', d / 'c.json', d / 'out.json'
            p.write_bytes(canonical_json_bytes(self.p))
            for raw in (b'{"schema_version":1,"schema_version":1,"candidates":[]}', b'\xff',
                        b'{"x":NaN}', b'{} trailing', br'{"bad":"\ud800"}'):
                c.write_bytes(raw)
                self.assertNotEqual(self.cli('target', p, c, '--output', out).returncode, 0)
                self.assertFalse(out.exists())

    def test_existing_dangling_symlinks_and_directory_entries_never_opened(self):
        destination = Mock(spec=Path)
        destination.lstat.return_value = os.stat_result((stat.S_IFLNK | 0o777, 0, 0, 1, 0, 0, 0, 0, 0, 0))
        destination.exists.return_value = False
        with self.assertRaises(FileExistsError):
            intake._write_new(destination, b'fictional output')
        destination.lstat.assert_called_once_with()
        destination.exists.assert_not_called()
        destination.open.assert_not_called()
        for error in (PermissionError('fictional denial'), NotADirectoryError('fictional parent'), OSError('fictional failure')):
            destination = Mock(spec=Path)
            destination.lstat.side_effect = error
            with self.assertRaises(type(error)):
                intake._write_new(destination, b'fictional output')
            destination.open.assert_not_called()
        with tempfile.TemporaryDirectory() as temp:
            d = Path(temp)
            p, c, out, victim = d / 'p.json', d / 'c.json', d / 'link.json', d / 'victim.json'
            p.write_bytes(canonical_json_bytes(self.p))
            c.write_bytes(canonical_json_bytes(self.c))
            try:
                out.symlink_to(victim)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable on this platform')
            self.assertNotEqual(self.cli('target', p, c, '--output', out).returncode, 0)
            self.assertFalse(victim.exists())
            victim.write_text('unchanged', encoding='utf-8')
            self.assertNotEqual(self.cli('target', p, c, '--output', out).returncode, 0)
            self.assertEqual(victim.read_text(), 'unchanged')

    def test_cli_input_and_stdout_preflight_before_output_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            d = Path(temp)
            p, c, out = d / 'p.json', d / 'c.json', d / 'out.json'
            p.write_bytes(canonical_json_bytes(self.p))
            c.write_bytes(canonical_json_bytes(self.c))
            argv = ['evidence_work_intake.py', 'target', str(p), str(c), '--output', str(out), '--text']
            with patch.object(sys, 'argv', argv), patch.object(intake, 'configure_utf8_stdio'), \
                 patch.object(intake, 'MAX_CANDIDATE_BYTES', 10), patch('sys.stderr', new_callable=io.StringIO), \
                 self.assertRaises(SystemExit):
                intake.main()
            self.assertFalse(out.exists())
            for rendered in ('x' * (intake.MAX_APPLICATION_BYTES + 1), '\ud800'):
                with patch.object(sys, 'argv', argv), patch.object(intake, 'configure_utf8_stdio'), \
                     patch.object(intake, 'render_text', return_value=rendered), \
                     patch('sys.stderr', new_callable=io.StringIO), self.assertRaises(SystemExit):
                    intake.main()
                self.assertFalse(out.exists())


    def test_checked_in_work_fixtures_preserve_four_results_and_grow_two_to_four(self):
        c = fixture('evidence-work-candidates.json')
        refs = fixture('evidence-work-references.json')
        template = intake.template(self.p, refs)
        self.assertEqual(template['candidate_document']['candidates'][0]['work_package']['evidence_ids'],
                         c['candidates'][0]['work_package']['evidence_ids'])
        record = self.assembled(c=c)
        self.assertTrue(intake.verify(self.p, record)['valid'])
        before, after = run(self.p), run(record['protocol_candidate'])
        self.assertEqual((len(before['work_packages']), len(after['work_packages'])), (2, 4))
        self.assertEqual(before['flow'], after['flow'])
        self.assertEqual(len(after['evidence']), 4)
        self.assertEqual(after['evidence'], before['evidence'])
        self.assertEqual([w['status'] for w in after['work_packages'][-2:]], ['PLANNED', 'PLANNED'])
        self.assertEqual(after['work_packages'][-2]['blocked_by'], ['WP-MEMBERSHIP-SOURCES'])
        self.assertEqual(after['work_packages'][-1]['blocked_by'], ['WP-RESULT-TRACE-NOTE'])

    def test_documented_twelve_command_rehearsal_with_only_explicit_synthetic_reviews(self):
        import result_intake
        doc = (ROOT / 'docs/EVIDENCE_WORK_INTAKE.md').read_text(encoding='utf-8')
        commands = [line for block in re.findall(r'```sh\n(.*?)```', doc, re.S)
                    for line in block.splitlines() if line.strip()]
        self.assertEqual(len(commands), 12)
        allowed = {'result_intake.py', 'evidence_work_intake.py', 'work_review.py',
                   'research_status.py', 'prisma_audit.py', 'research_bundle.py'}
        with tempfile.TemporaryDirectory(prefix='fictional evidence work ') as temp:
            out = Path(temp)
            for line in commands:
                tokens = shlex.split(line)
                self.assertEqual(tokens[0], 'python')
                self.assertIn(tokens[1], allowed)
                command = [sys.executable] + [token.replace('OUTPUT', str(out)) for token in tokens[1:]]
                result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=60,
                    env=dict(os.environ, PYTHONIOENCODING='ascii', PYTHONUTF8='0', PYTHONDONTWRITEBYTECODE='1'))
                self.assertEqual(result.returncode, 0, (line, result.stderr.decode('utf-8')))
                if tokens[1] in ('result_intake.py', 'evidence_work_intake.py') and tokens[2] == 'target':
                    prefix = 'result' if tokens[1] == 'result_intake.py' else 'work'
                    target = json.loads((out / (prefix + '-target.json')).read_bytes())
                    review = target['review_document']
                    self.assertTrue(all(v is None for k, v in review.items() if k not in ('schema_version', 'target_sha256')))
                    review.update(receipt_id='fictional-' + prefix + '-review', reviewer='Fictional test operator',
                                  reviewed_at='2026-11-04', rationale='Explicit synthetic software-test review.',
                                  decision='import_results' if prefix == 'result' else 'import_evidence_work')
                    (out / (prefix + '-review.json')).write_bytes(canonical_json_bytes(review))
            original = fixture('report-study-inventory-reviews.json')
            extracted = json.loads((out / 'with-results.json').read_bytes())
            final = json.loads((out / 'with-work.json').read_bytes())
            self.assertEqual((len(original['evidence']), len(extracted['evidence']), len(final['evidence'])), (2, 4, 4))
            self.assertEqual((len(extracted['gaps']), len(final['gaps'])), (2, 4))
            self.assertEqual({k: v for k, v in extracted.items() if k != 'gaps'},
                             {k: v for k, v in final.items() if k != 'gaps'})
            self.assertTrue(result_intake.verify(original, json.loads((out / 'result-application.json').read_bytes()))['valid'])
            self.assertTrue(intake.verify(extracted, json.loads((out / 'work-application.json').read_bytes()))['valid'])
            self.assertTrue(json.loads(result.stdout)['valid'])
            self.reject(json.loads((out / 'work-draft.json').read_bytes()), extracted)

    def test_empty_evidence_protocol_cannot_synthesize_a_selected_result(self):
        p = fixture('bibliographic-base.json')
        with self.assertRaisesRegex(ValueError, 'exact existing normalized result IDs'):
            intake.template(p, dict(schema_version=1, evidence_ids=['fictional-invented']))
        self.reject(candidates(evidence_ids=['fictional-invented']), p)


if __name__ == '__main__':
    unittest.main()
