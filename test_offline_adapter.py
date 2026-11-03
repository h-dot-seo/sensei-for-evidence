"""Provider-neutral mock adapter regressions using entirely synthetic inputs."""
import copy
import io
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from offline_adapter import assemble
from adapter_integrity import digest
from evidence_workflow import run
from research_status import status
from research_bundle import build_bundle, verify


class OfflineAdapterTests(unittest.TestCase):
    def setUp(self):
        self.protocol = json.loads(Path('examples/adapter-protocol.json').read_text())
        self.fixture = json.loads(Path('examples/adapter-fixture.json').read_text())
        self.reviews = json.loads(Path('examples/adapter-reviews.json').read_text())

    def accept_all(self, protocol=None, fixture=None):
        pending = assemble(protocol or self.protocol, fixture or self.fixture)['review_pending']
        return [dict(row, decision='accept', reviewer='synthetic-reviewer',
                     reviewed_at='2026-11-03', rationale='Synthetic review assertion.') for row in pending]

    def test_unreviewed_candidates_never_become_evidence(self):
        before = copy.deepcopy((self.protocol, self.fixture))
        with patch('socket.create_connection', side_effect=AssertionError('network forbidden')):
            result = assemble(self.protocol, self.fixture)
        self.assertEqual((self.protocol, self.fixture), before)
        self.assertEqual(result['external_calls'], 0)
        self.assertEqual(result['adapter_mode'], 'mock')
        self.assertEqual(result['research']['flow']['extracted'], 0)
        self.assertEqual(len(result['review_pending']), 3)
        self.assertFalse(result['research']['coverage'][0]['complete'])
        self.assertEqual(result['reports']['extraction_pending_reports'], ['report-1'])
        self.assertEqual(result['research']['appraisal']['appraisal_ledger'], [])

    def test_reviewed_end_to_end_preserves_provenance_and_bounds(self):
        result = assemble(self.protocol, self.fixture, self.reviews)
        self.assertEqual(result, assemble(self.protocol, self.fixture, self.reviews))
        self.assertEqual(result['research']['flow']['extracted'], 2)
        self.assertEqual(result['reports']['report_flow']['included_studies'], 1)
        self.assertEqual(result['review_pending'], [])
        self.assertEqual(result['census_claim'], 'NOT_ESTABLISHED')
        self.assertEqual(result['conclusion_readiness'], 'NOT_READY')
        protocol = result['protocol']
        for row in protocol['evidence'] + protocol['searches']:
            provenance = row['adapter_provenance']
            self.assertEqual(provenance['provider']['mode'], 'mock')
            self.assertEqual(provenance['source_verification'], 'UNVERIFIED_PROVIDER_RESPONSE')
        protocol['gaps'] = [dict(work_package_id='WP-MOCK', question='Synthetic follow-up?',
                                deliverable='Synthetic evidence review', acceptance_criterion='Review assertions',
                                evidence_ids=[protocol['evidence'][0]['evidence_id']])]
        self.assertEqual(run(protocol)['work_packages'][0]['work_package_id'], 'WP-MOCK')
        self.assertEqual(status(protocol)['queues']['dependency_unblocked_planned_work'], ['WP-MOCK'])
        data = build_bundle(json.dumps(protocol).encode())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'mock.zip'; path.write_bytes(data)
            self.assertTrue(verify(path)['valid'])
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            self.assertIn('adapter_receipts', json.loads(archive.read('protocol.json')))
            self.assertEqual(json.loads(archive.read('research.json'))['evidence'][0]['adapter_provenance']['provider']['mode'], 'mock')

    def test_downstream_rejects_stale_reviewed_provenance(self):
        baseline = assemble(self.protocol, self.fixture, self.reviews)['protocol']
        for mutate in (lambda p: p['evidence'][0].update(result='unreviewed edit'),
                       lambda p: p['adapter_receipts']['receipts'][0]['exchange']['request'].update(query='changed'),
                       lambda p: p['adapter_receipts']['reviews'][0].update(target_sha256='0' * 64),
                       lambda p: p['screening'][0].update(reason='changed review context'),
                       lambda p: p.pop('adapter_receipts'),
                       lambda p: p.update(adapter_receipts=None)):
            protocol = copy.deepcopy(baseline); mutate(protocol)
            for operation in (run, status, lambda p: build_bundle(json.dumps(p).encode())):
                with self.assertRaises(ValueError):
                    operation(protocol)
        enriched = copy.deepcopy(baseline)
        enriched['version'] = '2'
        enriched['gaps'] = [dict(question='Synthetic new work?', deliverable='Review',
                                 acceptance_criterion='Synthetic acceptance', evidence_ids=['e1'])]
        self.assertEqual(run(enriched)['flow']['extracted'], 2)
        self.assertEqual(enriched['adapter_receipts']['base_protocol']['version'], self.protocol['version'])

    def test_bundle_rejects_stale_provenance_even_with_updated_file_hashes(self):
        protocol = assemble(self.protocol, self.fixture, self.reviews)['protocol']
        data = build_bundle(json.dumps(protocol).encode())
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = {name: archive.read(name) for name in archive.namelist()}
        protocol['evidence'][0]['result'] = 'Unreviewed synthetic edit'
        entries['protocol.json'] = json.dumps(protocol).encode()
        manifest = json.loads(entries['manifest.json'])
        manifest['input_sha256'] = hashlib.sha256(entries['protocol.json']).hexdigest()
        for row in manifest['files']:
            row.update(bytes=len(entries[row['path']]), sha256=hashlib.sha256(entries[row['path']]).hexdigest())
        entries['manifest.json'] = json.dumps(manifest).encode()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'tampered.zip'
            with zipfile.ZipFile(path, 'w') as archive:
                for name, content in entries.items():
                    archive.writestr(name, content)
            with self.assertRaisesRegex(ValueError, 'differs from reviewed receipts'):
                verify(path)

    def test_downstream_revalidates_candidate_schema_after_rehashing(self):
        baseline = assemble(self.protocol, self.fixture, self.reviews)['protocol']
        for mutate in (lambda c: c.update(source_locator='synthetic://absent'),
                       lambda c: c.update(supporting_quote='not in source'),
                       lambda c: c.update(candidate_id='different-candidate'),
                       lambda c: c.pop('extractor_version')):
            protocol = copy.deepcopy(baseline)
            receipt = protocol['adapter_receipts']['receipts'][1]
            mutate(receipt['candidate'])
            receipt['sha256'] = digest({k: v for k, v in receipt.items() if k != 'sha256'})
            review = protocol['adapter_receipts']['reviews'][1]
            review['target_sha256'] = receipt['sha256']
            protocol['evidence'][0]['adapter_provenance'].update(receipt_sha256=receipt['sha256'], review=copy.deepcopy(review))
            for operation in (run, status, lambda p: build_bundle(json.dumps(p).encode())):
                with self.assertRaises(ValueError): operation(protocol)

    def test_exact_bindings_distinguish_boolean_integer_and_float(self):
        self.protocol['screening'][0]['confidence'] = 1
        self.fixture['extraction_candidates'][0]['proposal']['sample_size'] = 1
        baseline = assemble(self.protocol, self.fixture, self.accept_all())['protocol']
        for value in (True, 1.0):
            for mutate in (lambda p: p['evidence'][0].update(sample_size=value),
                           lambda p: p['screening'][0].update(confidence=value)):
                protocol = copy.deepcopy(baseline); mutate(protocol)
                with self.assertRaises(ValueError): run(protocol)

    def test_rejected_candidates_stay_outside_evidence(self):
        self.reviews[1]['decision'] = 'reject'
        result = assemble(self.protocol, self.fixture, self.reviews)
        self.assertEqual(result['research']['flow']['extracted'], 1)
        self.assertEqual(result['rejected'], [dict(target_type='extraction', target_id='candidate-1')])
        self.reviews[0]['decision'] = 'reject'
        with self.assertRaisesRegex(ValueError, 'accepted search'):
            assemble(self.protocol, self.fixture, self.reviews)

    def test_hashes_bind_protocol_provider_pages_and_candidates(self):
        changes = [lambda p, f: p.update(question='Changed synthetic question'),
                   lambda p, f: f.update(provider_id='another synthetic provider'),
                   lambda p, f: f['search_responses'][0]['pages'][0].update(retrieved_at='changed'),
                   lambda p, f: f['extraction_candidates'][0]['proposal'].update(result='changed')]
        for change in changes:
            p, f = copy.deepcopy(self.protocol), copy.deepcopy(self.fixture)
            change(p, f)
            with self.assertRaisesRegex(ValueError, 'review hash'):
                assemble(p, f, self.reviews)
        changed = copy.deepcopy(self.fixture)
        changed['search_responses'][0]['pages'][0]['records'][0]['title'] = 'changed source metadata'
        old = assemble(self.protocol, self.fixture)['review_pending'][1]['target_sha256']
        new = assemble(self.protocol, changed)['review_pending'][1]['target_sha256']
        self.assertNotEqual(old, new)

    def test_unknown_duplicate_and_mutating_reviews_rejected(self):
        for mutate in (lambda r: r.append(copy.deepcopy(r[0])),
                       lambda r: r[0].update(target_id='unknown'),
                       lambda r: r[0].update(instruction='change the result'),
                       lambda r: r[0].update(decision='approve'),
                       lambda r: r[0].update(reviewed_at='not-a-date')):
            reviews = copy.deepcopy(self.reviews); mutate(reviews)
            with self.assertRaises(ValueError):
                assemble(self.protocol, self.fixture, reviews)

    def test_page_and_total_issues_cannot_be_reviewed_complete(self):
        for change in (lambda x: x['pages'][0].update(total_count=99),
                       lambda x: x['pages'][0].update(total_count=True),
                       lambda x: x['pages'][0].update(error='synthetic failure'),
                       lambda x: x['pages'][0].update(truncated=True),
                       lambda x: x['pages'][-1].update(has_more=True),
                       lambda x: x.update(total_count=99),
                       lambda x: x['pages'][1].update(page_number=3)):
            fixture = copy.deepcopy(self.fixture); change(fixture['search_responses'][0])
            reviews = self.accept_all(fixture=fixture)
            with self.assertRaisesRegex(ValueError, 'unresolved page/count'):
                assemble(self.protocol, fixture, reviews)

    def test_source_and_candidate_collisions_rejected(self):
        mutations = [lambda f: f['search_responses'][0]['pages'][1].update(request_id='wrong'),
                     lambda f: f['search_responses'][0]['pages'][1].update(response_id='mock-page-1'),
                     lambda f: f['extraction_candidates'][1].update(candidate_id='candidate-1'),
                     lambda f: f['extraction_candidates'][1]['proposal'].update(evidence_id=f['extraction_candidates'][0]['proposal']['evidence_id']),
                     lambda f: f['extraction_candidates'][0].update(source_locator='synthetic://unknown'),
                     lambda f: f['extraction_candidates'][0].update(supporting_quote='absent quote'),
                     lambda f: f['extraction_candidates'][0]['proposal'].update(record_id='r2')]
        for mutate in mutations:
            fixture = copy.deepcopy(self.fixture); mutate(fixture)
            with self.assertRaises(ValueError):
                assemble(self.protocol, fixture)
        fixture = copy.deepcopy(self.fixture)
        fixture['search_responses'][0]['pages'][1]['records'].append(dict(record_id='r1', source_locator='synthetic://conflict'))
        with self.assertRaisesRegex(ValueError, 'conflicting source'):
            assemble(self.protocol, fixture)

    def test_existing_eligibility_checks_remain_authoritative(self):
        for mutate in (lambda p: p['screening'][0].update(decision='exclude'),
                       lambda p: p['reports'][0].update(study_id='wrong-study'),
                       lambda p: p['reports'][0].update(retrieval='pending', decision='pending')):
            protocol = copy.deepcopy(self.protocol); mutate(protocol)
            # Compute reviews against the changed protocol without bypassing existing gates.
            try:
                reviews = self.accept_all(protocol=protocol)
            except ValueError:
                continue  # Screening/report contradiction is already rejected before promotion.
            with self.assertRaises(ValueError):
                assemble(protocol, self.fixture, reviews)

    def test_zero_result_receipt_requires_one_terminal_page(self):
        p, f = copy.deepcopy(self.protocol), copy.deepcopy(self.fixture)
        p.update(screening=[], reports=[]); f['extraction_candidates'] = []
        exchange = f['search_responses'][0]
        exchange.update(total_count=0, pages=[dict(response_id='empty-page', request_id='mock-search-request-1',
                        retrieved_at='synthetic', page_number=1, records=[], total_count=0, has_more=False)])
        result = assemble(p, f, self.accept_all(p, f))
        self.assertEqual(result['research']['flow']['identified'], 0)
        self.assertTrue(result['research']['coverage'][0]['complete'])
        exchange['pages'] = []
        with self.assertRaises(ValueError): assemble(p, f)

    def test_declared_plan_is_required_and_cross_request_identity_conflicts_rejected(self):
        for value in (None, []):
            protocol = copy.deepcopy(self.protocol)
            protocol['search_plan'] = value
            with self.assertRaisesRegex(ValueError, 'declared search plan'):
                assemble(protocol, self.fixture)
        protocol, fixture = copy.deepcopy(self.protocol), copy.deepcopy(self.fixture)
        second = copy.deepcopy(fixture['search_responses'][0])
        second['request'].update(request_id='second-request', search_id='search-secondary',
                                 source=protocol['search_plan'][1]['source'],
                                 query=protocol['search_plan'][1]['query'],
                                 window=protocol['search_plan'][1]['window'])
        for index, page in enumerate(second['pages']):
            page.update(request_id='second-request', response_id=f'second-response-{index}')
        second['pages'][0]['records'][0]['source_locator'] = 'synthetic://ambiguous-r1'
        fixture['search_responses'].append(second)
        with self.assertRaisesRegex(ValueError, 'reconcile global record IDs'):
            assemble(protocol, fixture)

    def test_non_mock_modes_and_existing_work_are_not_overwritten(self):
        self.fixture['mode'] = 'live'
        with self.assertRaisesRegex(ValueError, 'only mock'): assemble(self.protocol, self.fixture)
        self.fixture['mode'] = 'mock'
        for key in ('searches', 'evidence'):
            p = copy.deepcopy(self.protocol); p[key] = [dict(existing='work')]
            with self.assertRaisesRegex(ValueError, 'never silently overwrite'): assemble(p, self.fixture)

    def test_cli_uses_mock_contract_and_review_fixture(self):
        args = [sys.executable, 'offline_adapter.py', 'examples/adapter-protocol.json',
                'examples/adapter-fixture.json', '--reviews', 'examples/adapter-reviews.json']
        result = subprocess.run(args, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['research']['flow']['extracted'], 2)
        with tempfile.TemporaryDirectory() as directory:
            protocol = Path(directory) / 'assembled.json'
            archive = Path(directory) / 'reviewed.zip'
            exported = subprocess.run(args + ['--protocol-output', str(protocol)],
                                      capture_output=True, text=True, timeout=20)
            self.assertEqual(exported.returncode, 0, exported.stderr)
            before = protocol.read_bytes()
            repeated = subprocess.run(args + ['--protocol-output', str(protocol)],
                                      capture_output=True, text=True, timeout=20)
            self.assertEqual(repeated.returncode, 1)
            self.assertEqual(protocol.read_bytes(), before)
            for command in (['create', str(protocol), str(archive)], ['verify', str(archive)]):
                bundled = subprocess.run([sys.executable, 'research_bundle.py', *command],
                                         capture_output=True, text=True, timeout=20)
                self.assertEqual(bundled.returncode, 0, bundled.stderr)


if __name__ == '__main__':
    unittest.main()
