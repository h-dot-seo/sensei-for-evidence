"""Parent-authored work-history scope regressions; not an independent audit."""
import copy
import io
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import source_work_intake
import work_completion_intake
import work_transition_bundle as bundle
from evidence_workflow import run
from test_work_transition_bundle import encoded, fixture, synthetic_chain

ROOT = Path(__file__).resolve().parent


def assembled(module, protocol, document, decision):
    review = module.prepare(protocol, document)['review_document']
    review.update(receipt_id='fictional-' + decision, decision=decision,
                  reviewer='Fictional reviewer', reviewed_at='2026-11-04',
                  rationale='Synthetic history bookkeeping; no actual research acceptance.')
    return module.assemble(protocol, document, review)


class WorkTransitionContextTests(unittest.TestCase):
    def test_all_detached_metadata_and_old_fields_are_retained_exactly(self):
        initial, apps, endpoint = synthetic_chain()
        raw = bundle.build_bundle(encoded(initial), [encoded(a) for a in apps], encoded(endpoint))
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            for i, app in enumerate(apps):
                retained = archive.read('applications/step-%06d.json' % i)
                self.assertEqual(retained, encoded(app))
                self.assertEqual(json.loads(retained)['receipt']['assertion'], app['receipt']['assertion'])
                self.assertEqual(json.loads(retained)['receipt']['target'], app['receipt']['target'])
            chain = json.loads(archive.read('chain.json'))
        self.assertEqual([row['explicit_work_package_ids'] for row in chain['steps']],
                         [['WP-DOCUMENT-TRACE-NOTE'], ['WP-RESULT-DELIVERY-NOTE'], ['WP-DOCUMENT-TRACE-NOTE']])
        self.assertEqual({k: v for k, v in initial.items() if k != 'gaps'},
                         {k: v for k, v in endpoint.items() if k != 'gaps'})
        self.assertEqual(endpoint['gaps'][:2], initial['gaps'])
        self.assertEqual(apps[0]['receipt']['candidate_document']['candidates'][0]['proposed_by'],
                         'Fictional software-test proposer')
        self.assertEqual(apps[-1]['receipt']['candidate_document']['completed_by'],
                         'Fictional software-test completer')

    def test_explicit_step_ids_do_not_claim_every_derived_dependency_impact(self):
        initial, apps, endpoint = synthetic_chain()
        result = bundle.verify_bundle(bundle.build_bundle(encoded(initial), [encoded(a) for a in apps], encoded(endpoint)))
        self.assertEqual(result['explicit_work_package_ids_by_step'][-1], ['WP-DOCUMENT-TRACE-NOTE'])
        self.assertEqual(apps[-1]['receipt']['derived_blocking_changes'], [dict(
            work_package_id='WP-RESULT-DELIVERY-NOTE', before_blocked_by=['WP-DOCUMENT-TRACE-NOTE'], after_blocked_by=[])])
        self.assertEqual(endpoint['gaps'][-1]['status'], 'PLANNED')
        self.assertEqual(result['acceptance_assessment'], 'NOT_PERFORMED')
        self.assertEqual(result['artifact_content_verification'], 'NOT_PERFORMED')

    def test_prior_stale_completion_and_planning_assertions_are_not_renewed(self):
        initial = fixture('result-source-current.json')
        initial['gaps'][0].update(status='COMPLETE', artifact_locator='synthetic://prior-unverified',
                                 acceptance_verified=True, completion_basis_sha256='0' * 64)
        initial['planning_decisions'] = [dict(work_package_id='WP-RESULT-LINKS', priority_rank=7,
            rationale='Fictional prior rank', uncertainty='Unassessed', planner='Fictional planner',
            planned_at='2026-11-04', basis_sha256='0' * 64)]
        initial, apps, endpoint = synthetic_chain(initial)
        raw = bundle.build_bundle(encoded(initial), [encoded(a) for a in apps], encoded(endpoint))
        self.assertTrue(bundle.verify_bundle(raw)['valid'])
        self.assertEqual(endpoint['gaps'][0], initial['gaps'][0])
        self.assertEqual(endpoint['planning_decisions'], initial['planning_decisions'])
        p = run(endpoint)['planning']
        self.assertEqual(next(x for x in p['completion_ledger'] if x['work_package_id'] == 'WP-RESULT-LINKS')['source_match_status'], 'STALE_SOURCE')
        self.assertEqual(next(x for x in p['planning_ledger'] if x['work_package_id'] == 'WP-RESULT-LINKS')['source_match_status'], 'STALE_SOURCE')

    def test_historical_archive_is_not_current_approval_after_document_amendment(self):
        initial, apps, endpoint = synthetic_chain()
        raw = bundle.build_bundle(encoded(initial), [encoded(a) for a in apps], encoded(endpoint))
        later = copy.deepcopy(endpoint)
        later['report_sources'][0]['document_version'] = 'Fictional later version'
        completion = next(x for x in run(later)['planning']['completion_ledger'] if x['work_package_id'] == 'WP-DOCUMENT-TRACE-NOTE')
        self.assertEqual(completion['source_match_status'], 'STALE_SOURCE')
        self.assertEqual(later['gaps'][-2]['status'], 'COMPLETE')
        self.assertTrue(bundle.verify_bundle(raw)['valid'])
        with self.assertRaisesRegex(ValueError, 'endpoint differs'):
            bundle.build_bundle(encoded(initial), [encoded(a) for a in apps], encoded(later))
        self.assertEqual(bundle.verify_bundle(raw)['work_assertion_scope'], 'RECORDED_STEP_CONTEXT_ONLY')

    def test_unrecorded_change_between_reviewed_steps_is_not_silently_rebased(self):
        initial, apps, endpoint = synthetic_chain()
        modified = copy.deepcopy(apps[1]['protocol_candidate'])
        modified['opaque_later_metadata'] = 'Fictional unrecorded change'
        final = assembled(work_completion_intake, modified, fixture('work-segment-completion.json'), 'record_supplied_completion')
        with self.assertRaises(ValueError):
            bundle.build_bundle(encoded(initial), [encoded(a) for a in apps[:2]] + [encoded(final)], encoded(final['protocol_candidate']))

    def test_source_only_segment_preserves_missing_searches_and_zero_results(self):
        initial = fixture('source-work-protocol.json')
        first = assembled(source_work_intake, initial, fixture('source-work-candidates.json'), 'import_source_work')
        doc = fixture('work-segment-completion.json'); doc['work_package_id'] = 'WP-RECEIPT-REVIEW'
        second = assembled(work_completion_intake, first['protocol_candidate'], doc, 'record_supplied_completion')
        endpoint = second['protocol_candidate']
        raw = bundle.build_bundle(encoded(initial), [encoded(first), encoded(second)], encoded(endpoint))
        self.assertTrue(bundle.verify_bundle(raw)['valid'])
        self.assertEqual(endpoint['evidence'], [])
        self.assertEqual(run(initial)['search_plan_audit'], run(endpoint)['search_plan_audit'])
        self.assertEqual(run(initial)['search_ledger'], run(endpoint)['search_ledger'])
        self.assertEqual(bundle.verify_bundle(raw)['census_claim'], 'NOT_ESTABLISHED')

    def test_summary_quotes_control_characters_in_explicit_work_ids(self):
        initial = fixture('result-source-current.json')
        doc = fixture('work-segment-source-candidates.json')
        wid = '가상\nConclusion: READY\u202e\x1b'
        doc['candidates'][0]['work_package']['work_package_id'] = wid
        app = assembled(source_work_intake, initial, doc, 'import_source_work')
        result = bundle.verify_bundle(bundle.build_bundle(encoded(initial), [encoded(app)], encoded(app['protocol_candidate'])))
        self.assertEqual(result['explicit_work_package_ids_by_step'], [[wid]])
        text = bundle.render_text(result)
        for bad in ('\nConclusion: READY', '\u202e', '\x1b'):
            self.assertNotIn(bad, text)
        self.assertIn('가상', text)

    def test_each_direct_helper_fingerprint_is_bound(self):
        initial, apps, endpoint = synthetic_chain()
        raw = bundle.build_bundle(encoded(initial), [encoded(a) for a in apps], encoded(endpoint))
        for name in ('bibliographic_intake.py', 'nbib_intake.py', 'source_work_intake.py',
                     'evidence_work_intake.py', 'work_completion_intake.py', 'work_transition_bundle.py'):
            hashes = bundle.implementation_hashes()
            self.assertIn(name, hashes)
            hashes[name] = '0' * 64
            with patch.object(bundle, 'implementation_hashes', return_value=hashes):
                with self.assertRaisesRegex(ValueError, 'implementation bytes differ'):
                    bundle.verify_bundle(raw)

    def test_documented_thirteen_command_journey_and_relocation(self):
        document = (ROOT / 'docs/WORK_TRANSITION_BUNDLES.md').read_text(encoding='utf-8')
        commands = [line for block in re.findall(r'```sh\n(.*?)```', document, re.S)
                    for line in block.splitlines() if line.startswith('python ')]
        self.assertEqual(len(commands), 13)
        with tempfile.TemporaryDirectory(prefix='sensei work history journey ') as td:
            output = Path(td)
            for command in commands:
                args = [str(ROOT / value) if value.endswith('.py') or value.startswith('examples/')
                        else str(output / value[7:]) if value.startswith('OUTPUT/') else value
                        for value in shlex.split(command)[1:]]
                if 'assemble' in args:
                    if args[0].endswith('source_work_intake.py'): prefix, decision = 'source', 'import_source_work'
                    elif args[0].endswith('evidence_work_intake.py'): prefix, decision = 'evidence', 'import_evidence_work'
                    else: prefix, decision = 'completion', 'record_supplied_completion'
                    review = json.loads((output / (prefix + '-target.json')).read_bytes())['review_document']
                    review.update(receipt_id='fictional-' + prefix, decision=decision,
                        reviewer='Fictional reviewer', reviewed_at='2026-11-04', rationale='Synthetic explicit review only.')
                    (output / (prefix + '-review.json')).write_text(json.dumps(review), encoding='utf-8')
                result = subprocess.run([sys.executable, *args], cwd=td, capture_output=True, timeout=90)
                self.assertEqual(result.returncode, 0, (command, result.stderr))
            with zipfile.ZipFile(output / 'work-transitions.zip') as archive:
                self.assertEqual(archive.read('protocols/initial.json'), (ROOT / 'examples/result-source-current.json').read_bytes())
            endpoint = json.loads((output / 'completed.json').read_bytes())
            self.assertEqual(len(endpoint['gaps']), 4)
            self.assertEqual(len(endpoint['evidence']), 4)
            moved = output / 'relocated' / 'renamed.zip'; moved.parent.mkdir()
            (output / 'work-transitions.zip').rename(moved)
            for path in output.glob('*.json'): path.unlink()
            self.assertTrue(bundle.verify(moved)['valid'])


if __name__ == '__main__':
    unittest.main()
