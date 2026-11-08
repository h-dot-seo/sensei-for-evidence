"""Fictional explicit full-text decisions: detached exact replay and no inferred votes."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import report_decision as decision
from evidence_workflow import run
from json_io import canonical_json_bytes
from prisma_reports import report_flow
from test_report_reviews import protocol, source, assertion

ROOT = Path(__file__).resolve().parent


def fixture():
    return json.loads((ROOT / 'examples/report-study-inventory.json').read_text(encoding='utf-8'))


class ReportDecisionTests(unittest.TestCase):
    def setUp(self):
        self.p = protocol()

    def document(self, p=None, report_id='report-1', **fields):
        p = self.p if p is None else p
        doc = decision.prepare(p, report_id)['decision_document']
        doc.update(receipt_id='fictional-choice-1', decision='include', reason='Fictional explicit reason',
                   adjudicator='Fictional human', decided_at='2026-11-04',
                   rationale='Fictional choice, not a vote', source_locator='fictional://human-choice',
                   study_declaration={'study_id': 'study-1'})
        doc.update(fields)
        return doc

    def apply(self, p=None, report_id='report-1', **fields):
        p = self.p if p is None else p
        return decision.assemble(p, self.document(p, report_id, **fields))

    def test_target_human_fields_blank_and_detached(self):
        original = copy.deepcopy(self.p)
        prepared = decision.prepare(self.p, 'report-1')
        doc = prepared['decision_document']
        self.assertEqual(set(doc), decision.DOCUMENT_FIELDS)
        for key in decision.DOCUMENT_FIELDS - {'schema_version', 'report_id', 'target_sha256'}:
            self.assertIsNone(doc[key], key)
        self.assertEqual(prepared['target']['prior_report'], self.p['reports'][0])
        self.assertEqual(prepared['protocol_sha256'], hashlib.sha256(canonical_json_bytes(self.p)).hexdigest())
        target = prepared['target']
        self.assertEqual(target['target_sha256'], decision.digest({k:v for k,v in target.items() if k != 'target_sha256'}))
        self.assertEqual(target['report_review_stage'], 'NOT_SUPPLIED')
        self.assertEqual(target['study_review_stage'], 'NOT_SUPPLIED')
        self.assertEqual(target['inventory_stage'], 'NOT_SUPPLIED')
        with self.assertRaises(ValueError): decision.assemble(self.p, doc)
        target['prior_report']['record_ids'].append('mutation')
        target['report_source_target']['recorded_report']['locator'] = 'mutation'
        self.assertEqual(self.p, original)

    def test_exact_literal_existing_retrieved_report_only(self):
        for rid in ('missing', 'report-1 ', 'REPORT-1', '', ' ', None, 1, True, 'report-2'):
            with self.subTest(rid=rid), self.assertRaises(ValueError): decision.prepare(self.p, rid)
        for retrieval in ('pending', 'not_retrieved'):
            p = copy.deepcopy(self.p)
            p['reports'][1].update(retrieval=retrieval, reason='Fictional unavailable')
            with self.assertRaises(ValueError): decision.prepare(p, 'report-2')
        p = copy.deepcopy(self.p); p.pop('reports')
        with self.assertRaises(ValueError): decision.prepare(p, 'report-1')

    def test_literal_nonblank_ids_are_not_trimmed(self):
        self.p['reports'][0]['report_id'] = ' report-1 '
        record = self.apply(report_id=' report-1 ', study_declaration={'study_ids':['study-A','study-A ', 'STUDY-A']})
        self.assertEqual(record['receipt']['assertion']['report_id'], ' report-1 ')
        self.assertEqual(record['protocol_candidate']['reports'][0]['study_ids'], ['study-A','study-A ', 'STUDY-A'])
        self.assertTrue(decision.verify(self.p, record)['valid'])

    def test_preserves_metadata_all_other_rows_and_no_embedded_history(self):
        self.p['reports'][0]['supplied_metadata'] = {'fictional':['retained']}
        original = copy.deepcopy(self.p)
        record = self.apply()
        candidate = record['protocol_candidate']
        expected = copy.deepcopy(original)
        expected['reports'][0]['reason'] = 'Fictional explicit reason'
        self.assertEqual(candidate, expected)
        self.assertEqual(set(record), decision.APPLICATION_FIELDS)
        self.assertEqual(set(candidate), set(original))
        self.assertEqual(self.p, original)
        record['receipt']['result_report']['supplied_metadata']['fictional'].append('mutation')
        self.assertEqual(candidate, expected)
        candidate['reports'][0]['record_ids'].append('mutation')
        self.assertEqual(self.p, original)

    def test_exclude_removes_scalar_and_plural_and_preserves_other_metadata(self):
        for plural in (False, True):
            p = copy.deepcopy(self.p)
            if plural: p['reports'][0]['study_ids'] = [p['reports'][0].pop('study_id')]
            record = self.apply(p, decision='exclude', study_declaration=None)
            row = record['protocol_candidate']['reports'][0]
            self.assertNotIn('study_id', row); self.assertNotIn('study_ids', row)
            self.assertEqual(row['decision'], 'exclude')
            self.assertEqual(row['locator'], p['reports'][0]['locator'])
            self.assertTrue(decision.verify(p, record)['valid'])

    def test_scalar_plural_replacement_and_reason_only_are_explicit(self):
        for old in ({'study_id':'study-1'}, {'study_ids':['study-1','unextracted']}):
            for new in ({'study_id':'new-study'}, {'study_ids':['new-study','other-study']}):
                p = copy.deepcopy(self.p)
                p['reports'][0].pop('study_id'); p['reports'][0].update(old)
                result = self.apply(p, study_declaration=new)['protocol_candidate']['reports'][0]
                for key in ('study_id','study_ids'):
                    self.assertEqual(result.get(key), new.get(key))
        record = self.apply(reason='  Fictional literal reason\n')
        row = record['protocol_candidate']['reports'][0]
        self.assertEqual(row['study_id'], self.p['reports'][0]['study_id'])
        self.assertEqual(row['reason'], '  Fictional literal reason\n')

    def test_retrieved_excluded_and_pending_legacy_scalar_are_explicitly_replaced(self):
        for old_decision in ('exclude','pending'):
            p=copy.deepcopy(self.p)
            p['reports'][0].update(decision=old_decision,reason='Fictional earlier state',study_id='legacy-label')
            included=self.apply(p,study_declaration={'study_ids':['explicit-new']})
            row=included['protocol_candidate']['reports'][0]
            self.assertEqual(row['study_ids'],['explicit-new']);self.assertNotIn('study_id',row)
            self.assertEqual(included['receipt']['target']['prior_report']['study_id'],'legacy-label')
            self.assertTrue(decision.verify(p,included)['valid'])
            excluded=self.apply(p,decision='exclude',study_declaration=None)
            self.assertNotIn('study_id',excluded['protocol_candidate']['reports'][0])
            self.assertEqual(excluded['receipt']['target']['prior_report']['study_id'],'legacy-label')
            self.assertTrue(decision.verify(p,excluded)['valid'])

    def test_strict_document_fields_types_dates_and_hashes(self):
        valid = self.document()
        cases = []
        for field in decision.DOCUMENT_FIELDS:
            missing = copy.deepcopy(valid); del missing[field]; cases.append(missing)
        cases.append(dict(valid, unexpected=True))
        wrong = [('schema_version',v) for v in (True, 1.0, 2, '1', None)]
        wrong += [('decision',v) for v in ('pending','unclear','Include',' include')]
        wrong += [('decided_at',v) for v in ('2026-02-30','0000-01-01','20261104','2026-1-04','2026-11-04\n','2026-11-04T00:00:00Z')]
        wrong += [('target_sha256',v) for v in ('A'*64,'z'*64,'0'*63,'0'*65,'0'*64+'\n','0'*64)]
        wrong += [('report_id','report-1 ')]
        for key in decision.DOCUMENT_FIELDS - {'schema_version','study_declaration'}:
            wrong.extend((key,v) for v in (None,'',' \t',1,True,[],{}))
        cases.extend(dict(valid, **{key:value}) for key,value in wrong)
        for doc in cases:
            with self.subTest(doc=doc), self.assertRaises(ValueError): decision.assemble(self.p, doc)
        self.assertTrue(self.apply(decided_at='2024-02-29'))

    def test_strict_explicit_declaration_shapes(self):
        bad = [None, {}, True, [], 'study-1', {'study_id':''}, {'study_id':1},
               {'study_id':'study-1','study_ids':['study-1']}, {'study_id':'study-1','extra':True}]
        bad += [{'study_ids':v} for v in (None, [], 'study-1', {}, [None], [True], [1], [' '], [[]], [{}], ['same','same'])]
        for declaration in bad:
            with self.subTest(declaration=declaration), self.assertRaises(ValueError): self.apply(study_declaration=declaration)
        for declaration in ({}, {'study_id':'study-1'}, [], False):
            with self.subTest(declaration=declaration), self.assertRaises(ValueError): self.apply(decision='exclude', study_declaration=declaration)

    def test_whole_input_any_change_stales_document_without_mutating(self):
        doc = self.document()
        changes = [lambda p:p.update(version='fictional-v2'),
                   lambda p:p.update(extra_metadata={'fictional':True}),
                   lambda p:p['reports'][1].update(reason='Unrelated supplied reason'),
                   lambda p:p['searches'][0].update(query='Other supplied query'),
                   lambda p:p['inclusion_criteria'].append('Other criterion'),
                   lambda p:p.update(report_reviews=[]),
                   lambda p:p['reports'][0].update(locator='fictional://new')]
        for change in changes:
            p = copy.deepcopy(self.p); change(p); original = copy.deepcopy(p)
            with self.subTest(change=change), self.assertRaises(ValueError): decision.assemble(p, doc)
            self.assertEqual(p, original)

    def test_dictionary_order_semantics_and_array_order_binding(self):
        def reverse(value):
            if isinstance(value, dict): return {k:reverse(v) for k,v in reversed(list(value.items()))}
            if isinstance(value, list): return [reverse(v) for v in value]
            return value
        record = self.apply()
        self.assertEqual(decision.prepare(reverse(self.p), 'report-1'), decision.prepare(self.p, 'report-1'))
        self.assertTrue(decision.verify(reverse(self.p), reverse(record))['valid'])
        p = copy.deepcopy(self.p); p['reports'].reverse()
        with self.assertRaises(ValueError): decision.verify(p, record)

    def test_conflicting_unclear_stale_and_absent_reviews_cannot_vote(self):
        self.p['report_sources'] = [source()]
        rows = [assertion(self.p, decision='exclude'),
                assertion(self.p, reviewer='Fictional B', decision='unclear', review_id='b'),
                dict(assertion(self.p, reviewer='Fictional C', decision='exclude', review_id='c'), source_basis_sha256='0'*64)]
        for supplied in (None, [], rows):
            p = copy.deepcopy(self.p)
            if supplied is not None: p['report_reviews'] = supplied
            record = self.apply(p)
            self.assertEqual(record['protocol_candidate']['reports'][0]['decision'], 'include')
            self.assertEqual(record['receipt']['target']['report_review_snapshots'], supplied or [])
            self.assertEqual(record['protocol_candidate'].get('report_reviews'), supplied)
            self.assertFalse(record['receipt']['review_assertions_changed'])

    def test_inventory_never_chooses_or_promotes_membership_and_source_hash_unchanged(self):
        p = fixture()
        before = run(p)['report_study_inventory']
        record = self.apply(p, 'report-three', study_declaration={'study_id':'explicit-other'})
        candidate = record['protocol_candidate']
        self.assertEqual(candidate['reports'][2]['study_id'], 'explicit-other')
        self.assertEqual(candidate['report_study_inventory'], p['report_study_inventory'])
        self.assertEqual(record['receipt']['target']['inventory_snapshots'], p['report_study_inventory'][:2])
        after = run(candidate)['report_study_inventory']
        self.assertEqual([r['source_basis_sha256'] for r in before['candidate_targets']],
                         [r['source_basis_sha256'] for r in after['candidate_targets']])

    def test_membership_shrink_only_when_no_result_is_removed(self):
        p = fixture()
        record = self.apply(p, 'report-one', study_declaration={'study_ids':['study-A','study-B']})
        self.assertEqual(record['protocol_candidate']['evidence'], p['evidence'])
        for declaration in ({'study_ids':['study-A','study-C']}, {'study_id':'study-A'}):
            with self.assertRaises(ValueError): self.apply(p, 'report-one', study_declaration=declaration)
        with self.assertRaises(ValueError): self.apply(p, 'report-one', decision='exclude', study_declaration=None)

    def test_scalar_only_no_optional_ledgers_still_checks_downstream_evidence(self):
        p = copy.deepcopy(self.p)
        p['evidence'] = [dict(evidence_id='fictional-result',record_id='r1',study_id='study-1',
                             locator='fictional://result', model='Fictional system',intervention='Fictional label',
                             comparator='Fictional reference',endpoint='Fictional endpoint',result='Fictional observation',
                             limitations='Software testing only',mechanism_basis='unknown')]
        self.assertFalse(any(k in p for k in ('report_reviews','report_sources','report_study_reviews','report_study_inventory')))
        self.assertTrue(self.apply(p))
        original = copy.deepcopy(p)
        for fields in (dict(decision='exclude', study_declaration=None),dict(study_declaration={'study_id':'other'})):
            with self.subTest(fields=fields), self.assertRaises(ValueError): self.apply(p, **fields)
            self.assertEqual(p, original)

    def test_invalid_unselected_scalar_report_blocks_before_assembly(self):
        self.p['reports'][1].update(retrieval='retrieved',decision='include',study_id='other',locator='')
        with self.assertRaises(ValueError): decision.prepare(self.p, 'report-1')

    def test_study_review_orphans_retained_and_stale_not_repaired(self):
        from test_report_study_reviews import protocol as study_protocol, assertion as study_assertion
        p = study_protocol()
        p['report_study_reviews'] = [study_assertion(p, study='study-C')]
        record = self.apply(p, 'report-one', study_declaration={'study_ids':['study-A','study-B']})
        candidate = record['protocol_candidate']
        self.assertEqual(candidate['report_study_reviews'], p['report_study_reviews'])
        ledger = run(candidate)['report_study_review']
        self.assertEqual(ledger['counts']['orphan_review_assertions'], 1)
        self.assertEqual(ledger['review_ledger'][0]['source_match_status'], 'STALE_SOURCE')
        self.assertEqual(record['receipt']['target']['study_review_snapshots'], p['report_study_reviews'])

    def test_before_after_flows_hashes_engine_and_boundaries(self):
        record = self.apply(decision='exclude', study_declaration=None)
        receipt, candidate = record['receipt'], record['protocol_candidate']
        self.assertEqual(receipt['before_flow'], run(self.p)['flow'])
        self.assertEqual(receipt['after_flow'], run(candidate)['flow'])
        self.assertEqual(receipt['before_report_flow'], report_flow(self.p)['report_flow'])
        self.assertEqual(receipt['after_report_flow'], report_flow(candidate)['report_flow'])
        self.assertEqual(receipt['input_protocol_sha256'], decision.digest(self.p))
        self.assertEqual(receipt['protocol_candidate_sha256'], decision.digest(candidate))
        self.assertEqual(receipt['receipt_sha256'], decision.digest({k:v for k,v in receipt.items() if k != 'receipt_sha256'}))
        self.assertEqual(receipt['engine_sha256']['report_decision.py'], hashlib.sha256((ROOT/'report_decision.py').read_bytes()).hexdigest())
        for key, expected in [('source_authenticity','NOT_VERIFIED'),('reading','NOT_ESTABLISHED'),
                              ('document_bytes_verification','NOT_PERFORMED'),('eligibility_correctness','NOT_ASSESSED')]:
            self.assertEqual(receipt[key], expected)
        self.assertEqual(receipt['external_calls'], 0)
        self.assertIn('not an immutable history', receipt['boundary'])
        self.assertIn('globally unique', receipt['boundary'])

    def test_exact_record_tampering_rejected_even_resealed(self):
        base = self.apply()
        mutations = [lambda r:r['receipt']['target']['prior_report'].update(locator='tampered'),
                     lambda r:r['receipt']['target'].update(target_sha256='0'*64),
                     lambda r:r['receipt']['assertion'].update(rationale='tampered'),
                     lambda r:r['receipt']['result_report'].update(reason='tampered'),
                     lambda r:r['protocol_candidate'].update(version='tampered'),
                     lambda r:r['receipt']['before_flow'].update(included=999),
                     lambda r:r['receipt']['after_flow'].update(included=999),
                     lambda r:r['receipt']['before_report_flow'].update(included_reports=999),
                     lambda r:r['receipt']['after_report_flow'].update(included_reports=999),
                     lambda r:r['receipt']['engine_sha256'].update(**{'report_decision.py':'0'*64}),
                     lambda r:r['receipt'].update(input_protocol_sha256='0'*64),
                     lambda r:r['receipt'].update(protocol_candidate_sha256='0'*64),
                     lambda r:r['receipt'].update(receipt_sha256='0'*64),
                     lambda r:r['receipt'].update(reading='VERIFIED'),
                     lambda r:r['receipt'].update(extra=True)]
        for index, mutate in enumerate(mutations):
            for reseal in ((False,) if index in (2, 12) else (False, True)):
                record = copy.deepcopy(base); mutate(record)
                if reseal:
                    receipt = record['receipt']
                    receipt['receipt_sha256'] = decision.digest({k:v for k,v in receipt.items() if k != 'receipt_sha256'})
                with self.subTest(index=index, reseal=reseal), self.assertRaises(ValueError): decision.verify(self.p, record)

    def test_resealed_human_assertion_is_editable_not_authenticated_history(self):
        record = self.apply()
        record['receipt']['assertion']['rationale'] = 'Different supplied fictional rationale'
        receipt = record['receipt']
        receipt['receipt_sha256'] = decision.digest({k:v for k,v in receipt.items() if k != 'receipt_sha256'})
        self.assertTrue(decision.verify(self.p, record)['valid'])
        self.assertIn('editable detached application record', receipt['boundary'])
        self.assertIn('not an immutable history', receipt['boundary'])

    def test_strict_outer_schema_original_and_current_engine_binding(self):
        base = self.apply()
        for record in (None, [], {}, dict(base, schema_version=True), dict(base, schema_version=1.0),
                       dict(base, kind='other'),dict(base, extra=True), dict(base, receipt=[]),dict(base, receipt={})):
            with self.subTest(record=record), self.assertRaises(ValueError): decision.verify(self.p, record)
        p = copy.deepcopy(self.p); p['version'] += '-changed'
        with self.assertRaises(ValueError): decision.verify(p, base)
        altered = dict(base['receipt']['engine_sha256'], **{'report_decision.py':'0'*64})
        with patch.object(decision, '_implementation_hashes', return_value=altered):
            with self.assertRaises(ValueError): decision.verify(self.p, base)

    def test_reused_receipt_id_is_not_a_global_uniqueness_or_history_claim(self):
        first = self.apply()
        second = self.apply(first['protocol_candidate'], decision='exclude', study_declaration=None)
        self.assertEqual(first['receipt']['receipt_id'], second['receipt']['receipt_id'])
        self.assertTrue(decision.verify(first['protocol_candidate'], second)['valid'])
        self.assertEqual(set(second['protocol_candidate']), set(self.p))
        with self.assertRaises(ValueError): decision.verify(self.p, second)

    def test_validated_csv_mapping_source_context_preserved(self):
        from test_bibliographic_review import BibliographicReviewTests
        helper = BibliographicReviewTests(); helper.setUp(); p = helper.imported()
        rid = p['searches'][0]['record_ids'][0]
        p['screening'] = [dict(record_id=rid, decision='include', reason='Fictional scope')]
        p['reports'] = [dict(report_id='report-1',record_ids=[rid],retrieval='retrieved',locator='fictional',decision='pending')]
        p['report_sources'] = [source()]
        collection = run(p)['bibliographic_collection']
        p['report_reviews'] = [assertion(p, collection=collection)]
        result = self.apply(p)
        self.assertEqual(result['protocol_candidate']['bibliographic_imports'], p['bibliographic_imports'])
        self.assertEqual(run(result['protocol_candidate'])['bibliographic_collection'], collection)
        self.assertTrue(decision.verify(p, result)['valid'])
        target = result['receipt']['target']['report_source_target']
        from report_review_links import prepare_targets
        expected = prepare_targets(p, collection)['report_targets'][0]
        self.assertEqual(target, expected)

    def test_full_run_and_report_flow_validate_before_and_after(self):
        doc = self.document()
        with patch.object(decision, 'run', wraps=run) as core, patch.object(decision, 'report_flow', wraps=report_flow) as reports:
            result = decision.assemble(self.p, doc)
        self.assertEqual(core.call_count, 2)
        self.assertEqual(reports.call_count, 2)
        self.assertEqual(core.call_args_list[0].args[0], self.p)
        self.assertEqual(core.call_args_list[1].args[0], result['protocol_candidate'])
        self.assertEqual(reports.call_args_list[0].args[0], self.p)
        self.assertEqual(reports.call_args_list[1].args[0], result['protocol_candidate'])

    def test_replay_nested_schema_types_and_nonlocal_engine_change_reject(self):
        base = self.apply()
        for container in ('receipt', 'target', 'assertion'):
            for value in (True, 1.0):
                record = copy.deepcopy(base)
                target = record['receipt'] if container == 'receipt' else record['receipt'][container]
                target['schema_version'] = value
                with self.subTest(container=container, value=value), self.assertRaises(ValueError):
                    decision.verify(self.p, record)
        engines = dict(base['receipt']['engine_sha256'])
        other = next(name for name in engines if name != 'report_decision.py')
        engines[other] = '0' * 64
        with patch.object(decision, '_implementation_hashes', return_value=engines):
            with self.assertRaises(ValueError): decision.verify(self.p, base)

    def test_checked_in_fictional_example_replays(self):
        p = fixture()
        doc = json.loads((ROOT/'examples/report-decision-document.json').read_text(encoding='utf-8'))
        record = decision.assemble(p, doc)
        self.assertTrue(decision.verify(p, record)['valid'])
        self.assertEqual(record['protocol_candidate']['reports'][2]['study_ids'], ['candidate-X'])


class ReportDecisionCLITests(unittest.TestCase):
    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT/'report_decision.py'), *map(str,args)],
                              cwd=ROOT, capture_output=True, env=dict(os.environ,PYTHONIOENCODING='ascii'))

    def write(self, path, value):
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')

    def test_cli_detached_roundtrip_verify_then_protocol_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); p = protocol(); original = root/'original.json'
            docpath, recordpath, candidate = root/'document.json', root/'record.json', root/'candidate.json'
            self.write(original,p)
            result = self.cli('target',original,'--report-id','report-1','--output',root/'target.json')
            self.assertEqual(result.returncode,0,result.stderr)
            doc = json.loads(result.stdout)['decision_document']
            doc.update(receipt_id='fictional', decision='include', reason='허구의 이유',adjudicator='Fictional human',
                       decided_at='2026-11-04',rationale='Fictional',source_locator='fictional://choice',study_declaration={'study_id':'study-1'})
            self.write(docpath,doc)
            result = self.cli('assemble',original,docpath,'--output',recordpath)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['kind'],'detached_report_decision')
            self.assertFalse(candidate.exists())
            result = self.cli('verify',original,recordpath,'--protocol-output',candidate)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue(json.loads(result.stdout)['valid'])
            self.assertEqual(json.loads(candidate.read_text(encoding='utf-8'))['reports'][0]['reason'],'허구의 이유')
            self.assertEqual(json.loads(original.read_text(encoding='utf-8')),p)
            for args, output in [(('target',original,'--report-id','report-1','--output',root/'target.json'),root/'target.json'),
                                 (('assemble',original,docpath,'--output',recordpath),recordpath),
                                 (('verify',original,recordpath,'--protocol-output',candidate),candidate)]:
                before = output.read_bytes(); result = self.cli(*args)
                self.assertNotEqual(result.returncode,0); self.assertEqual(output.read_bytes(),before)

    def test_failed_verification_creates_no_output_and_original_is_required(self):
        helper = ReportDecisionTests(); helper.setUp()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); original, recordpath, output = root/'original.json',root/'record.json',root/'out.json'
            record = helper.apply(); self.write(original,helper.p)
            record['protocol_candidate']['version']='tampered'; self.write(recordpath,record)
            result = self.cli('verify',original,recordpath,'--protocol-output',output)
            self.assertNotEqual(result.returncode,0); self.assertFalse(output.exists()); self.assertFalse(result.stdout)
            record = helper.apply(); self.write(recordpath,record); self.write(original,record['protocol_candidate'])
            result = self.cli('verify',original,recordpath,'--protocol-output',output)
            self.assertNotEqual(result.returncode,0); self.assertFalse(output.exists())

    def test_cli_create_only_paths_with_unicode_spaces_and_original_collision(self):
        helper = ReportDecisionTests(); helper.setUp()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original, docpath, recordpath = root/'원본 protocol.json', root/'decision document.json', root/'application record.json'
            self.write(original, helper.p); self.write(docpath, helper.document())
            before = original.read_bytes()
            result = self.cli('assemble', original, docpath, '--output', original)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(original.read_bytes(), before)
            result = self.cli('assemble', original, docpath, '--output', recordpath)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = self.cli('verify', original, recordpath, '--protocol-output', original)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(original.read_bytes(), before)

    def test_cli_strict_json_utf8_control_safe_errors_and_text(self):
        helper = ReportDecisionTests(); helper.setUp()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); original, docpath, output = root/'original.json',root/'document.json',root/'out.json'
            self.write(original, helper.p)
            bads = [b'{"schema_version":1,"schema_version":1}', b'{"x":NaN}', b'\xff', b'{"x":"\\ud800"}']
            for raw in bads:
                docpath.write_bytes(raw)
                result = self.cli('assemble',original,docpath,'--output',output)
                self.assertNotEqual(result.returncode,0); self.assertFalse(output.exists())
            result = self.cli('target',original,'--report-id','unknown\x1b[31m\nforged','--text')
            self.assertNotEqual(result.returncode,0); self.assertNotIn(b'\x1b', result.stderr)
            self.write(docpath,helper.document(reason='Fictional\x1b[31m\nline 한국어'))
            result = self.cli('assemble',original,docpath,'--text')
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertNotIn(b'\x1b',result.stdout)
            self.assertIn('한국어', result.stdout.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
