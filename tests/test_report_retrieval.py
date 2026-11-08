"""Self-authored synthetic retrieval-update tests, not independent validation."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import bibliographic_intake
import bibliographic_review
from evidence_workflow import run
from json_io import canonical_json_bytes
from prisma_audit import export_audit
import report_decision
import report_intake
from report_review_links import prepare_targets
import report_retrieval as retrieval
from report_study_inventory_links import prepare_candidate_target
import research_bundle

ROOT = Path(__file__).resolve().parents[1]


def fixture(name):
    return json.loads((ROOT / 'examples' / name).read_text(encoding='utf-8'))


def registered():
    base = fixture('report-intake-base.json')
    rows = fixture('manual-report-candidates.json')
    review = report_intake.prepare(base, rows)['review_document']
    review.update(receipt_id='synthetic-registration', decision='import_reports', reviewer='Fictional reviewer',
                  reviewed_at='2026-11-04', rationale='Synthetic supplied registration.')
    return report_intake.assemble(base, rows, review)['protocol_candidate']


class ReportRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.base = registered()
        self.candidates = fixture('manual-retrieval-candidates.json')

    def review(self, protocol=None, candidates=None):
        p = self.base if protocol is None else protocol
        c = self.candidates if candidates is None else candidates
        result = retrieval.prepare(p, c)['review_document']
        result.update(receipt_id='fictional-retrieval-update', decision='update_retrieval',
            reviewer='Fictional reviewer', reviewed_at='2026-11-04', rationale='Synthetic supplied retrieval review.')
        return result

    def assembled(self, protocol=None, candidates=None):
        p = self.base if protocol is None else protocol
        c = self.candidates if candidates is None else candidates
        return retrieval.assemble(p, c, self.review(p, c))

    def reject(self, candidates=None, protocol=None):
        with self.assertRaises((ValueError, TypeError)):
            retrieval.prepare(self.base if protocol is None else protocol,
                              self.candidates if candidates is None else candidates)

    def invoke(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'report_retrieval.py'), *map(str, args)],
            cwd=ROOT, capture_output=True, timeout=60,
            env=dict(os.environ, PYTHONIOENCODING='ascii', PYTHONUTF8='0'))

    def test_template_uses_only_explicit_ordered_reports_and_blank_assertions(self):
        refs = dict(schema_version=1, report_ids=['report-C', 'report-B'])
        before = copy.deepcopy((self.base, refs))
        draft = retrieval.template(self.base, refs)
        self.assertEqual([r['report_id'] for r in draft['candidate_document']['candidates']], refs['report_ids'])
        self.assertTrue(all(value is None for row in draft['candidate_document']['candidates']
                            for key, value in row.items() if key != 'report_id'))
        self.assertEqual((self.base, refs), before)
        self.reject(draft['candidate_document'])
        for ids in [[], ['report-B', 'report-B'], ['report-A'], ['unknown'], 'report-B']:
            with self.assertRaises(ValueError): retrieval.template(self.base, dict(schema_version=1, report_ids=ids))

    def test_preparation_is_deterministic_nonmutating_and_review_blank(self):
        before = copy.deepcopy((self.base, self.candidates))
        result = retrieval.prepare(self.base, self.candidates)
        self.assertEqual(result, retrieval.prepare(self.base, self.candidates))
        self.assertEqual((self.base, self.candidates), before)
        self.assertNotIn('protocol_candidate', result)
        self.assertFalse(result['protocol_changed'])
        self.assertTrue(all(value is None for key, value in result['review_document'].items()
                            if key not in ('schema_version', 'target_sha256')))
        with self.assertRaises(ValueError): retrieval.assemble(self.base, self.candidates, result['review_document'])
        target = result['target']
        self.assertEqual(target['prior_report_targets'][0]['recorded_report']['retrieval'], 'not_retrieved')
        self.assertEqual(target['proposed_report_targets'][0]['recorded_report']['retrieval'], 'retrieved')

    def test_updates_only_retrieval_partitions_and_keeps_full_text_pending(self):
        a = self.assembled(); p = a['protocol_candidate']
        self.assertTrue(retrieval.verify(self.base, a)['valid'])
        before = a['receipt']['before_report_flow']; after = a['receipt']['after_report_flow']
        self.assertEqual((before['retrieved'], before['not_retrieved'], before['retrieval_pending']), (1, 1, 1))
        self.assertEqual((after['retrieved'], after['not_retrieved'], after['retrieval_pending']), (2, 1, 0))
        self.assertEqual(after['assessment_pending'], 2)
        for key in ['assessed', 'included', 'excluded', 'included_studies', 'reports_with_extraction']:
            self.assertEqual(after[key], 0)
        self.assertEqual(a['receipt']['before_flow'], a['receipt']['after_flow'])
        self.assertEqual(p['reports'][0], self.base['reports'][0])
        self.assertTrue(all(r['decision'] == 'pending' for r in p['reports']))
        self.assertEqual(p['evidence'], [])
        audit = export_audit(p)
        self.assertTrue(all(row['status'] == 'RECORDED_MEMBERS_PARTITION' for row in audit['partition_checks']))
        self.assertEqual(audit['reasons']['reports_not_retrieved'][0]['member_ids'], ['report-C'])
        self.assertEqual(audit['census_claim'], 'NOT_ESTABLISHED')
        self.assertEqual(run(p)['search_plan_audit']['missing_search_ids'], ['followup'])

    def test_all_supported_transitions_and_same_state_or_reversal_refusal(self):
        for old, new in sorted(retrieval.TRANSITIONS):
            p = copy.deepcopy(self.base); p['reports'][2].update(retrieval=old, reason='Supplied prior note')
            c = dict(schema_version=1, candidates=[dict(self.candidates['candidates'][1], retrieval=new,
                     locator='synthetic://supplied' if new == 'retrieved' else None)])
            self.assertTrue(retrieval.verify(p, self.assembled(p, c))['valid'])
        for old, new in [('pending', 'pending'), ('not_retrieved', 'not_retrieved'),
                         ('not_retrieved', 'pending'), ('retrieved', 'not_retrieved'), ('retrieved', 'retrieved')]:
            p = copy.deepcopy(self.base); p['reports'][2].update(retrieval=old, reason='Prior', locator='synthetic://old')
            c = dict(schema_version=1, candidates=[dict(self.candidates['candidates'][1], retrieval=new)])
            self.reject(c, p)

    def test_raw_fields_mappings_absence_and_existing_source_prefix_preserved(self):
        p = copy.deepcopy(self.base)
        p['reports'][1].pop('decision'); p['reports'][1]['opaque'] = ['keep', None, '한글']
        p['opaque'] = dict(unrelated=['same'])
        before = canonical_json_bytes(p); a = self.assembled(p); result = a['protocol_candidate']
        self.assertNotIn('decision', result['reports'][1])
        self.assertEqual(result['reports'][1]['record_ids'], ['r3'])
        self.assertEqual(result['reports'][1]['opaque'], p['reports'][1]['opaque'])
        self.assertEqual(result['report_sources'][:1], p['report_sources'])
        restored = copy.deepcopy(result); restored['reports'] = copy.deepcopy(p['reports'])
        restored['report_sources'] = restored['report_sources'][:1]
        self.assertEqual(restored, p); self.assertEqual(canonical_json_bytes(p), before)
        prior = a['receipt']['target']['prior_report_targets'][0]['recorded_report']
        self.assertEqual(prior['reason'], 'Fictional document was not supplied.')
        self.assertIsNone(result['reports'][1]['reason'])
        self.assertTrue(retrieval.verify(p, a)['valid'])

    def test_absent_empty_sources_and_explicit_nulls_remain_distinct(self):
        c = copy.deepcopy(self.candidates); c['candidates'][0]['source_declarations'] = []
        for supplied in [False, True]:
            p = copy.deepcopy(self.base); p.pop('report_sources')
            if supplied: p['report_sources'] = []
            a = self.assembled(p, c)
            self.assertEqual('report_sources' in a['protocol_candidate'], supplied)
            self.assertEqual(a['receipt']['target']['before_source_stage'], 'SUPPLIED' if supplied else 'NOT_SUPPLIED')
            self.assertEqual(a['receipt']['added_source_declarations'], 0)
        p = copy.deepcopy(self.base); p['reports'][2].pop('locator'); p['reports'][2].pop('reason')
        a = self.assembled(p)
        self.assertNotIn('locator', a['receipt']['target']['prior_report_targets'][1]['recorded_report'])
        self.assertIsNone(a['protocol_candidate']['reports'][2]['locator'])

    def test_existing_review_assertions_become_stale_without_replacement(self):
        p = copy.deepcopy(self.base)
        targets = {row['report_id']:row for row in prepare_targets(p)['report_targets']}
        p['report_reviews'] = [dict(review_id='review-'+rid, report_id=rid, reviewer='Fictional reviewer',
            reviewed_at='2026-11-04', decision='unclear', rationale='Synthetic supplied position',
            reviewed_locator='synthetic://prior', source_basis_sha256=targets[rid]['source_basis_sha256'])
            for rid in ['report-A', 'report-B']]
        before = run(p)['report_review']; a = self.assembled(p); after = run(a['protocol_candidate'])['report_review']
        self.assertEqual(before['counts']['current_source_reviews'], 2)
        self.assertEqual(after['counts']['current_source_reviews'], 1)
        self.assertEqual(after['counts']['stale_source_reviews'], 1)
        self.assertEqual(a['protocol_candidate']['report_reviews'], p['report_reviews'])
        self.assertEqual(a['receipt']['target']['retained_review_assertions'], [p['report_reviews'][1]])
        self.assertFalse(a['receipt']['review_assertions_changed'])
        rows = {row['report_id']:row for row in after['report_review_ledger']}
        self.assertIn('STALE_REVIEW_ASSERTIONS', rows['report-B']['comparison_cues'])
        self.assertEqual(rows['report-A']['current_review_ids'], ['review-report-A'])

    def test_new_sources_are_not_retrieval_or_document_verification(self):
        c = copy.deepcopy(self.candidates); source = c['candidates'][0]['source_declarations'][0]
        source['document_sha256'] = '0'*64
        c['candidates'][0]['source_declarations'].append(dict(source, source_id='source-B-other'))
        c['candidates'][1]['source_declarations'] = [dict(source, report_id='report-C', source_id='source-C')]
        a = self.assembled(candidates=c)
        self.assertEqual(a['protocol_candidate']['reports'][2]['retrieval'], 'not_retrieved')
        self.assertEqual(a['receipt']['retrieval_verification'], 'NOT_PERFORMED')
        self.assertEqual(a['receipt']['document_bytes_verification'], 'NOT_PERFORMED')
        self.assertEqual(a['receipt']['added_source_declarations'], 3)
        self.assertEqual(a['protocol_candidate']['report_sources'][1]['document_sha256'],
                         a['protocol_candidate']['report_sources'][2]['document_sha256'])

    def test_inventory_and_orphan_study_positions_are_retained_not_promoted(self):
        p = copy.deepcopy(self.base)
        p['report_sources'].append(dict(source_id='prior-B', report_id='report-B', source_locator='synthetic://prior-B',
            document_version='Fictional prior descriptor', document_sha256=None))
        target = prepare_candidate_target(p, 'report-B', 'candidate-study-B')
        p['report_study_inventory'] = [dict(inventory_id='inventory-B', report_id='report-B', study_id='candidate-study-B',
            recorded_by='Fictional person', recorded_at='2026-11-04', description='Synthetic supplied description',
            source_locator='synthetic://prior-B', source_ids=['prior-B'], source_basis_sha256=target['source_basis_sha256'])]
        p['report_study_reviews'] = [dict(review_id='orphan-B', report_id='report-B', study_id='candidate-study-B',
            reviewer='Fictional person', reviewed_at='2026-11-04', decision='unclear', rationale='Synthetic retained position',
            reviewed_locator='synthetic://prior-B', reviewed_source_ids=['prior-B'], source_basis_sha256='0'*64)]
        self.assertEqual(run(p)['report_study_inventory']['counts']['current_source_assertions'], 1)
        a = self.assembled(p); result = run(a['protocol_candidate'])
        for key in ['report_study_inventory', 'report_study_reviews']:
            self.assertEqual(a['protocol_candidate'][key], p[key])
        self.assertEqual(result['report_study_inventory']['counts']['stale_source_assertions'], 1)
        self.assertEqual(result['report_study_review']['counts']['orphan_review_assertions'], 1)
        self.assertNotIn('study_id', a['protocol_candidate']['reports'][1])

    def test_new_source_that_conflicts_with_retained_orphan_reference_is_refused(self):
        p = copy.deepcopy(self.base)
        p['report_study_inventory'] = [dict(inventory_id='old-A', report_id='report-A', study_id='candidate-A',
            recorded_by='Fictional person', recorded_at='2026-11-04', description='Synthetic stale context',
            source_locator='synthetic://old-A', source_ids=['source-B'], source_basis_sha256='0'*64)]
        run(p); before = copy.deepcopy(p)
        with self.assertRaisesRegex(ValueError, 'another report'):
            retrieval.prepare(p, self.candidates)
        self.assertEqual(p, before)

    def test_bibliographic_import_association_and_source_snapshots_remain_bound(self):
        p = fixture('bibliographic-base.json')
        native = bibliographic_intake.prepare(p, b'record_id,source_locator\nx,synthetic:source\n', 'local-primary', 'synthetic time')
        choices = bibliographic_review.template(native)
        choices['resolutions'][0].update(disposition='new_record',record_id='r1',rationale='Synthetic supplied choice')
        reviewed = bibliographic_review.prepare_review(p,native,choices)['review_document']
        reviewed['review'].update(reviewer='Fictional reviewer',reviewed_at='2026-11-04',rationale='Synthetic',decision='import_for_screening')
        p = bibliographic_review.assemble(p,native,reviewed)['protocol_candidate']
        p['screening'] = [dict(record_id='r1',decision='include',reason='Supplied fictional choice')]
        p['reports'] = [dict(report_id='report-B',record_ids=['r1'],retrieval='pending',decision='pending')]
        c = dict(schema_version=1,candidates=[copy.deepcopy(self.candidates['candidates'][0])])
        a = self.assembled(p,c)
        self.assertEqual(a['protocol_candidate']['bibliographic_imports'],p['bibliographic_imports'])
        before = run(p); after = run(a['protocol_candidate'])
        self.assertEqual(before['bibliographic_collection'],after['bibliographic_collection'])
        prior = a['receipt']['target']['prior_report_targets'][0]['source_basis']['mapped_records']
        proposed = a['receipt']['target']['proposed_report_targets'][0]['source_basis']['mapped_records']
        self.assertEqual(prior,proposed)
        self.assertTrue(retrieval.verify(p,a)['valid'])

    def test_sources_must_be_new_unique_and_owned_by_updated_report(self):
        for field, value in [('source_id', 'source-A'), ('report_id', 'report-A'), ('source_locator', ''),
                             ('document_version', None), ('document_sha256', 'A'*64), ('document_sha256', True)]:
            c = copy.deepcopy(self.candidates); c['candidates'][0]['source_declarations'][0][field] = value; self.reject(c)
        c = copy.deepcopy(self.candidates); c['candidates'][0]['source_declarations'] *= 2; self.reject(c)
        c = copy.deepcopy(self.candidates); c['candidates'][0]['source_declarations'][0]['unknown'] = None; self.reject(c)
        for value in [None, {}, 'x']:
            c = copy.deepcopy(self.candidates); c['candidates'][0]['source_declarations'] = value; self.reject(c)

    def test_candidate_contract_does_not_accept_identity_eligibility_or_studies(self):
        for extra in ['record_ids', 'decision', 'study_id', 'study_ids', 'report', 'evidence']:
            c = copy.deepcopy(self.candidates); c['candidates'][0][extra] = 'invented'; self.reject(c)
        for field, value in [('report_id', 'unknown'), ('report_id', 'report-A'), ('retrieval', 'include'),
                             ('locator', None), ('reason', []), ('updated_by', ''), ('updated_at', '2026-02-29'),
                             ('updated_at', '2026-1-04'), ('update_note', None)]:
            c = copy.deepcopy(self.candidates); c['candidates'][0][field] = value; self.reject(c)
        c = copy.deepcopy(self.candidates); c['candidates'][1]['report_id'] = 'report-B'; self.reject(c)
        c = copy.deepcopy(self.candidates); c['candidates'][1]['reason'] = None; self.reject(c)
        for field in retrieval.CANDIDATE_FIELDS:
            c = copy.deepcopy(self.candidates); del c['candidates'][0][field]; self.reject(c)

    def test_strict_json_schemas_and_input_quotas(self):
        for value in [None, [], {}, dict(self.candidates, schema_version=True), dict(self.candidates, extra=1),
                      dict(self.candidates, candidates=[]), dict(self.candidates, candidates={})]:
            with self.assertRaises(ValueError): retrieval.prepare(self.base, value)
        cycle = []; cycle.append(cycle)
        for value in [float('nan'), float('inf'), ('tuple',), {1:'x'}, {'x'}, '\ud800', cycle]:
            p = copy.deepcopy(self.base); p['opaque'] = value; self.reject(protocol=p)
        class DictSubclass(dict): pass
        self.reject(DictSubclass(self.candidates))
        with patch.object(retrieval, 'MAX_CANDIDATES', 1): self.reject()
        with patch.object(retrieval, 'MAX_SOURCE_DECLARATIONS', 0): self.reject()
        with patch.object(retrieval, 'MAX_CANDIDATE_BYTES', 1): self.reject()
        with patch.object(retrieval, 'MAX_PROTOCOL_BYTES', 1): self.reject()
        with patch.object(retrieval, 'MAX_APPLICATION_BYTES', 1): self.reject()
        with patch.object(retrieval, 'MAX_CANDIDATES', 1):
            with self.assertRaises(ValueError): retrieval.template(self.base, fixture('retrieval-update-references.json'))

    def test_missing_malformed_or_mock_reports_are_not_repaired(self):
        p = copy.deepcopy(self.base); p.pop('reports'); p.pop('report_sources'); self.reject(protocol=p)
        for value in [None, {}, [None]]:
            p = copy.deepcopy(self.base); p['reports'] = value; self.reject(protocol=p)
        p = copy.deepcopy(self.base); p['reports'][1]['decision'] = 'exclude'; self.reject(protocol=p)
        p = fixture('source-work-protocol.json'); original = copy.deepcopy(p)
        with self.assertRaisesRegex(ValueError, 'mock adapter context locks'):
            retrieval.prepare(p, self.candidates)
        self.assertEqual(p, original)

    def test_review_is_bound_to_complete_original_candidate_and_code(self):
        review = self.review()
        for key, value in [('decision', 'include'), ('reviewer', ''), ('reviewed_at', '2026-02-30'),
                           ('rationale', None), ('target_sha256', '0'*64), ('receipt_id', True)]:
            r = copy.deepcopy(review); r[key] = value
            with self.assertRaises(ValueError): retrieval.assemble(self.base, self.candidates, r)
        p = copy.deepcopy(self.base); p['opaque'] = 'Changed'
        with self.assertRaises(ValueError): retrieval.assemble(p, self.candidates, review)
        for mutate in [lambda c:c['candidates'].reverse(), lambda c:c['candidates'][0].update(update_note='Changed'),
                       lambda c:c['candidates'][0]['source_declarations'][0].update(document_sha256='1'*64)]:
            c = copy.deepcopy(self.candidates); mutate(c)
            with self.assertRaises(ValueError): retrieval.assemble(self.base, c, review)
        with patch.object(retrieval, '_implementation_hashes', return_value={'changed':'code'}):
            with self.assertRaises(ValueError): retrieval.assemble(self.base, self.candidates, review)
        hashes = retrieval._implementation_hashes()
        self.assertEqual(hashes['report_retrieval.py'], hashlib.sha256((ROOT/'report_retrieval.py').read_bytes()).hexdigest())
        self.assertIn('source_work_intake.py', hashes); self.assertIn('report_review_links.py', hashes)

    def test_complete_replay_rejects_tamper_even_with_resealed_receipt(self):
        a = self.assembled()
        edits = [lambda v:v.update(extra=True), lambda v:v.update(schema_version=True),
                 lambda v:v['receipt'].update(updated_reports=100),
                 lambda v:v['receipt']['target']['prior_report_targets'][0]['recorded_report'].update(reason='Changed'),
                 lambda v:v['protocol_candidate']['reports'][1].update(record_ids=['r4']),
                 lambda v:v['protocol_candidate']['report_sources'][0].update(document_sha256='0'*64),
                 lambda v:v['receipt']['candidate_document']['candidates'][0].update(updated_by='Changed')]
        for edit in edits:
            for reseal in [False, True]:
                changed = copy.deepcopy(a); edit(changed)
                if reseal:
                    changed['receipt'].pop('receipt_sha256'); changed['receipt']['receipt_sha256'] = retrieval.digest(changed['receipt'])
                with self.assertRaises(ValueError): retrieval.verify(self.base, changed)
        with self.assertRaises(ValueError): retrieval.verify(a['protocol_candidate'], a)

    def test_later_full_text_decision_remains_separate_and_bundle_replays(self):
        p = self.assembled()['protocol_candidate']
        self.assertEqual(p['reports'][1]['decision'], 'pending')
        prepared = report_decision.prepare(p, 'report-B')
        d = prepared['decision_document']; d.update(receipt_id='synthetic-full-text', decision='include',
            reason='Fictional inclusion rationale', adjudicator='Fictional person', decided_at='2026-11-04',
            rationale='Synthetic separate choice', source_locator='synthetic://report-B/supplied',
            study_declaration={'study_id':'synthetic-study-B'})
        a = report_decision.assemble(p, d)
        self.assertTrue(report_decision.verify(p, a)['valid'])
        self.assertEqual(a['protocol_candidate']['reports'][1]['study_id'], 'synthetic-study-B')
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); source = root/'protocol.json'; bundle = root/'research.zip'
            source.write_bytes(canonical_json_bytes(a['protocol_candidate']))
            research_bundle.create(source, bundle)
            self.assertTrue(research_bundle.verify(bundle)['valid'])
        with self.assertRaises(ValueError): report_decision.prepare(p, 'report-C')

    def test_no_network_no_input_mutation_and_control_characters_are_quoted(self):
        p = copy.deepcopy(self.base); c = copy.deepcopy(self.candidates)
        c['candidates'][0]['update_note'] = 'literal\n\x1b[31m 한글'
        before = copy.deepcopy((p, c))
        with patch.object(socket, 'socket', side_effect=AssertionError('No network')):
            a = self.assembled(p, c); self.assertTrue(retrieval.verify(p, a)['valid'])
        self.assertEqual((p, c), before)
        text = retrieval.render_text(a)
        self.assertNotIn('\x1b', text); self.assertIn('\\u001b', text)
        self.assertIn('한글', text)
        with patch.object(retrieval, 'MAX_APPLICATION_BYTES', 1):
            with self.assertRaises(ValueError): retrieval.render_text(a)

    def test_cli_full_utf8_round_trip_and_output_guards(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); p = root/'protocol.json'; c = root/'candidates.json'; refs = root/'refs.json'
            p.write_bytes(canonical_json_bytes(self.base)); c.write_bytes(canonical_json_bytes(self.candidates))
            refs.write_bytes(canonical_json_bytes(fixture('retrieval-update-references.json')))
            draft = root/'draft.json'; target = root/'target.json'; review = root/'review.json'
            application = root/'application.json'; exported = root/'exported.json'
            for args in [('template', p, refs, '--output', draft, '--text'), ('target', p, c, '--output', target)]:
                result = self.invoke(*args); self.assertEqual(result.returncode, 0, result.stderr)
            r = json.loads(target.read_bytes())['review_document']
            r.update(self.review()); r['reviewer'] = '가상 검토자'; review.write_bytes(canonical_json_bytes(r))
            result = self.invoke('assemble', p, c, review, '--output', application, '--text')
            self.assertEqual(result.returncode, 0, result.stderr); self.assertIn('가상 검토자', result.stdout.decode())
            result = self.invoke('verify', p, application, '--protocol-output', exported)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)['valid'])
            original = exported.read_bytes()
            self.assertNotEqual(self.invoke('verify', p, application, '--protocol-output', exported).returncode, 0)
            self.assertEqual(exported.read_bytes(), original)
            dangling = root/'dangling'
            try: dangling.symlink_to(root/'missing')
            except OSError: pass
            else:
                self.assertNotEqual(self.invoke('target', p, c, '--output', dangling).returncode, 0)
                self.assertTrue(dangling.is_symlink()); self.assertFalse((root/'missing').exists())

    def test_cli_preflight_rejects_invalid_data_without_opening_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); p = root/'protocol.json'; c = root/'candidates.json'; out = root/'new.json'
            p.write_bytes(canonical_json_bytes(self.base))
            for raw in [b'{"schema_version":1,"schema_version":1}', b'NaN', b'\xff', b'{}']:
                c.write_bytes(raw)
                self.assertNotEqual(self.invoke('target', p, c, '--output', out).returncode, 0)
                self.assertFalse(out.exists())
            c.write_bytes(canonical_json_bytes(self.candidates))
            argv = ['report_retrieval.py', 'target', str(p), str(c), '--output', str(out)]
            with patch.object(sys, 'argv', argv), patch.object(retrieval.helpers, '_encode', side_effect=ValueError('serialization failure')):
                with self.assertRaises(SystemExit), patch('sys.stderr', new_callable=io.StringIO): retrieval.main()
            self.assertFalse(out.exists())
            with patch.object(Path, 'lstat', side_effect=PermissionError('inspection denied')):
                with self.assertRaises(PermissionError): retrieval._write_new(out, b'x')
            self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
