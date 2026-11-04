"""Synthetic report registration tests; not independent scientific validation."""
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
import condition_intake
from evidence_workflow import run
from json_io import canonical_json_bytes
from prisma_audit import export_audit
from prisma_reports import report_flow
import report_decision
import report_intake as intake
import research_bundle
import result_intake
from test_condition_intake import unit

ROOT = Path(__file__).resolve().parent


def fixture(name):
    return json.loads((ROOT / 'examples' / name).read_text(encoding='utf-8'))


class ReportIntakeTests(unittest.TestCase):
    def setUp(self):
        self.base = fixture('report-intake-base.json')
        self.candidates = fixture('manual-report-candidates.json')

    def review(self, protocol=None, candidates=None):
        p = self.base if protocol is None else protocol
        c = self.candidates if candidates is None else candidates
        result = intake.prepare(p, c)['review_document']
        result.update(receipt_id='fictional-report-registration', decision='import_reports',
            reviewer='Fictional reviewer', reviewed_at='2026-11-04', rationale='Synthetic explicit registration review.')
        return result

    def assembled(self, protocol=None, candidates=None):
        p = self.base if protocol is None else protocol
        c = self.candidates if candidates is None else candidates
        return intake.assemble(p, c, self.review(p, c))

    def reject(self, candidates=None, protocol=None):
        with self.assertRaises((ValueError, TypeError)):
            intake.prepare(self.base if protocol is None else protocol,
                           self.candidates if candidates is None else candidates)

    def invoke(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'report_intake.py'), *map(str, args)],
            cwd=ROOT, capture_output=True, timeout=60,
            env=dict(os.environ, PYTHONIOENCODING='ascii', PYTHONUTF8='0'))

    def test_template_keeps_explicit_group_without_identity_or_sources(self):
        refs = dict(schema_version=1, record_ids=['r2', 'r1'])
        before = copy.deepcopy((self.base, refs))
        draft = intake.template(self.base, refs)
        row = draft['candidate_document']['candidates'][0]
        self.assertEqual(row['report']['record_ids'], ['r2', 'r1'])
        self.assertEqual(row['report']['decision'], 'pending')
        self.assertTrue(all(row['report'][key] is None for key in ('report_id', 'retrieval', 'locator', 'reason')))
        self.assertTrue(all(row[key] is None for key in ('source_declarations', 'registered_by', 'registered_at', 'registration_note')))
        self.reject(draft['candidate_document'])
        self.assertEqual((self.base, refs), before)
        for ids in [[], ['r1', 'r1'], ['r5'], ['r6'], ['unknown'], 'r1']:
            with self.assertRaises(ValueError): intake.template(self.base, dict(schema_version=1, record_ids=ids))

    def test_target_is_deterministic_detached_and_review_blank(self):
        before = copy.deepcopy((self.base, self.candidates))
        result = intake.prepare(self.base, self.candidates)
        self.assertEqual(result, intake.prepare(self.base, self.candidates))
        self.assertEqual((self.base, self.candidates), before)
        self.assertNotIn('protocol_candidate', result)
        self.assertFalse(result['protocol_changed'])
        self.assertTrue(all(value is None for key, value in result['review_document'].items()
                            if key not in ('schema_version', 'target_sha256')))
        with self.assertRaises(ValueError): intake.assemble(self.base, self.candidates, result['review_document'])
        target = result['target']
        self.assertEqual(target['before_report_stage'], 'NOT_SUPPLIED')
        self.assertEqual(target['before_source_stage'], 'NOT_SUPPLIED')
        self.assertEqual(len(target['selected_record_targets']), 4)
        self.assertEqual(len(target['proposed_report_targets']), 3)
        self.assertEqual(target['proposed_source_declarations'][0]['input_pointer'], '/report_sources/0')

    def test_registration_changes_report_units_not_record_or_scientific_decisions(self):
        application = self.assembled(); protocol = application['protocol_candidate']
        self.assertTrue(intake.verify(self.base, application)['valid'])
        self.assertEqual(application['receipt']['before_flow'], application['receipt']['after_flow'])
        self.assertIsNone(application['receipt']['before_report_flow'])
        counts = application['receipt']['after_report_flow']
        self.assertEqual(counts, dict(sought=3, retrieved=1, not_retrieved=1, retrieval_pending=1,
            assessed=0, assessment_pending=1, excluded=0, included=0, included_studies=0, reports_with_extraction=0))
        self.assertEqual(protocol['reports'], [row['report'] for row in self.candidates['candidates']])
        self.assertEqual(protocol['screening'], self.base['screening'])
        self.assertEqual(protocol['evidence'], [])
        self.assertFalse(any('study_id' in row or 'study_ids' in row for row in protocol['reports']))
        audit = export_audit(protocol); nodes = {row['node_id']: row for row in audit['nodes']}
        self.assertEqual(nodes['unique_records']['count'], 6)
        self.assertEqual(nodes['included_records']['count'], 4)
        self.assertEqual(nodes['mapped_included_records']['count'], 4)
        self.assertEqual(nodes['reports_sought']['count'], 3)
        self.assertEqual(nodes['reports_excluded']['count'], 0)
        self.assertEqual(audit['reasons']['reports_not_retrieved'][0]['member_ids'], ['report-B'])
        self.assertTrue(all(row['status'] == 'RECORDED_MEMBERS_PARTITION' for row in audit['partition_checks']))
        self.assertEqual(run(protocol)['search_plan_audit']['missing_search_ids'], ['followup'])
        self.assertEqual(audit['census_claim'], 'NOT_ESTABLISHED')
        self.assertEqual(audit['conclusion_readiness'], 'NOT_READY')

    def test_absent_empty_source_and_report_stages_remain_distinct(self):
        c = copy.deepcopy(self.candidates); c['candidates'][0]['source_declarations'] = []
        for present in [False, True]:
            p = copy.deepcopy(self.base)
            if present: p.update(reports=[], report_sources=[])
            a = self.assembled(p, c)
            self.assertEqual('report_sources' in a['protocol_candidate'], present)
            self.assertEqual(a['receipt']['target']['before_report_stage'], 'SUPPLIED' if present else 'NOT_SUPPLIED')
            self.assertEqual(a['receipt']['target']['before_source_stage'], 'SUPPLIED' if present else 'NOT_SUPPLIED')
            if present: self.assertEqual(a['receipt']['before_report_flow']['sought'], 0)
            else: self.assertIsNone(a['receipt']['before_report_flow'])
            self.assertEqual(a['receipt']['added_source_declarations'], 0)

    def test_raw_prefixes_and_opaque_fields_are_retained(self):
        first = dict(schema_version=1, candidates=[copy.deepcopy(self.candidates['candidates'][0])])
        p = self.assembled(candidates=first)['protocol_candidate']
        p['reports'][0]['opaque_annotation'] = dict(order=['β', None, 0])
        p['opaque'] = {'text': '  preserve\nspacing  '}
        remaining = dict(schema_version=1, candidates=copy.deepcopy(self.candidates['candidates'][1:]))
        before = canonical_json_bytes(p)
        a = self.assembled(p, remaining)
        self.assertEqual(a['protocol_candidate']['reports'][:1], p['reports'])
        self.assertEqual(a['protocol_candidate']['report_sources'], p['report_sources'])
        restored = copy.deepcopy(a['protocol_candidate']); restored['reports'] = restored['reports'][:1]
        self.assertEqual(restored, p); self.assertEqual(canonical_json_bytes(p), before)
        self.assertTrue(intake.verify(p, a)['valid'])

    def test_record_report_and_source_collisions_fail_without_repair(self):
        for ids in [['r5'], ['r6'], ['unknown'], [], ['r1', 'r1']]:
            c = copy.deepcopy(self.candidates); c['candidates'][0]['report']['record_ids'] = ids; self.reject(c)
        c = copy.deepcopy(self.candidates); c['candidates'][1]['report']['record_ids'] = ['r2']; self.reject(c)
        c = copy.deepcopy(self.candidates); c['candidates'][1]['report']['report_id'] = 'report-A'; self.reject(c)
        p = self.assembled(candidates=dict(schema_version=1, candidates=[self.candidates['candidates'][0]]))['protocol_candidate']
        self.reject(protocol=p)
        c = dict(schema_version=1, candidates=[copy.deepcopy(self.candidates['candidates'][1])])
        c['candidates'][0]['source_declarations'] = [dict(self.candidates['candidates'][0]['source_declarations'][0], report_id='report-B')]
        self.reject(c, p)
        c['candidates'][0]['source_declarations'][0]['source_id'] = 'new-source'
        self.assertTrue(intake.verify(p, self.assembled(p, c))['valid'])

    def test_pending_only_report_contract_and_all_retrieval_states(self):
        for field, bad in [('decision', 'include'), ('decision', 'exclude'), ('retrieval', 'complete'),
                           ('locator', ''), ('reason', []), ('record_ids', 'r1')]:
            c = copy.deepcopy(self.candidates); c['candidates'][0]['report'][field] = bad; self.reject(c)
        for field in ['study_id', 'study_ids', 'invented']:
            c = copy.deepcopy(self.candidates); c['candidates'][0]['report'][field] = 'x'; self.reject(c)
        c = copy.deepcopy(self.candidates); c['candidates'][0]['report']['locator'] = None; self.reject(c)
        c = copy.deepcopy(self.candidates); c['candidates'][1]['report']['reason'] = None; self.reject(c)
        c = copy.deepcopy(self.candidates); c['candidates'][2]['report'].update(locator='synthetic:pending', reason='Supplied pending note')
        self.assertTrue(intake.verify(self.base, self.assembled(candidates=c))['valid'])

    def test_document_declarations_are_supplied_and_never_prove_retrieval(self):
        c = copy.deepcopy(self.candidates)
        source = c['candidates'][0]['source_declarations'][0]
        source['document_sha256'] = '1' * 64
        c['candidates'][0]['source_declarations'].append(dict(source, source_id='same-bytes-other-declaration'))
        c['candidates'][2]['source_declarations'] = [dict(source, source_id='pending-source', report_id='report-C')]
        a = self.assembled(candidates=c)
        self.assertEqual(a['protocol_candidate']['reports'][2]['retrieval'], 'pending')
        self.assertEqual(a['receipt']['document_bytes_verification'], 'NOT_PERFORMED')
        self.assertEqual(a['receipt']['retrieval_verification'], 'NOT_PERFORMED')
        self.assertEqual(len(a['protocol_candidate']['report_sources']), 3)
        self.assertEqual(a['protocol_candidate']['report_sources'][0]['document_sha256'],
                         a['protocol_candidate']['report_sources'][1]['document_sha256'])
        for field, values in {'source_declarations': [None, {}, 'x']}.items():
            for value in values:
                bad = copy.deepcopy(c); bad['candidates'][0][field] = value; self.reject(bad)
        for field, values in {'document_sha256': ['A'*64, 'short', True, 1], 'report_id': ['report-B', 'unknown'],
                              'source_id': ['', None], 'source_locator': [''], 'document_version': [None]}.items():
            for value in values:
                bad = copy.deepcopy(c); bad['candidates'][0]['source_declarations'][0][field] = value; self.reject(bad)
        bad = copy.deepcopy(c); bad['candidates'][2]['source_declarations'][0]['source_id'] = source['source_id']; self.reject(bad)
        bad = copy.deepcopy(c); bad['candidates'][0]['source_declarations'][0]['extra'] = True; self.reject(bad)

    def test_strict_json_schemas_human_metadata_and_dates(self):
        for value in [None, [], {}, dict(self.candidates, schema_version=True), dict(self.candidates, extra=True),
                      dict(self.candidates, candidates=[]), dict(self.candidates, candidates={})]:
            with self.assertRaises(ValueError): intake.prepare(self.base, value)
        for field in intake.CANDIDATE_FIELDS:
            c = copy.deepcopy(self.candidates); del c['candidates'][0][field]; self.reject(c)
        for field in ['registered_by', 'registered_at', 'registration_note']:
            for value in [None, True, 1, [], {}, '', ' \n']:
                c = copy.deepcopy(self.candidates); c['candidates'][0][field] = value; self.reject(c)
        for date in ['2026-02-29', '2026-2-04', '0000-01-01', '2026-11-04T00:00:00Z']:
            c = copy.deepcopy(self.candidates); c['candidates'][0]['registered_at'] = date; self.reject(c)
        c = copy.deepcopy(self.candidates); c['candidates'][0]['registered_at'] = '2024-02-29'; intake.prepare(self.base, c)
        cycle = []; cycle.append(cycle)
        for value in [float('nan'), float('inf'), ('tuple',), {1: 'key'}, {'set'}, '\ud800', cycle]:
            p = copy.deepcopy(self.base); p['opaque'] = value; self.reject(protocol=p)
        class DictSubclass(dict): pass
        self.reject(DictSubclass(self.candidates))

    def test_invalid_old_reports_and_legacy_evidence_cannot_be_silently_migrated(self):
        for value in [None, {}, [None], [dict(report_id='old', record_ids=['r6'], retrieval='pending')]]:
            p = copy.deepcopy(self.base); p['reports'] = value; self.reject(protocol=p)
        p = fixture('report-protocol.json'); p.pop('reports')
        with self.assertRaisesRegex(ValueError, 'legacy evidence'): intake.prepare(p, self.candidates)
        p = fixture('report-protocol.json'); p['reports'][0].pop('study_id')
        self.reject(protocol=p)
        p = copy.deepcopy(self.base); p['report_sources'] = [self.candidates['candidates'][0]['source_declarations'][0]]
        self.reject(protocol=p)

    def test_review_fields_staleness_and_implementation_binding(self):
        review = self.review()
        for field, values in {'decision': ['include', None], 'reviewer': ['', None], 'reviewed_at': ['2026-02-30'],
                              'rationale': [None], 'target_sha256': ['0'*64], 'receipt_id': [True]}.items():
            for value in values:
                changed = copy.deepcopy(review); changed[field] = value
                with self.assertRaises(ValueError): intake.assemble(self.base, self.candidates, changed)
        changed = copy.deepcopy(review); changed['extra'] = True
        with self.assertRaises(ValueError): intake.assemble(self.base, self.candidates, changed)
        p = copy.deepcopy(self.base); p['opaque'] = 'changed'
        with self.assertRaises(ValueError): intake.assemble(p, self.candidates, review)
        for mutate in [lambda c: c['candidates'].reverse(),
                       lambda c: c['candidates'][0]['report']['record_ids'].reverse(),
                       lambda c: c['candidates'][0].update(registration_note='Changed'),
                       lambda c: c['candidates'][0]['source_declarations'][0].update(document_sha256='0'*64)]:
            c = copy.deepcopy(self.candidates); mutate(c)
            with self.assertRaises(ValueError): intake.assemble(self.base, c, review)
        with patch.object(intake, '_implementation_hashes', return_value={'changed':'code'}):
            with self.assertRaises(ValueError): intake.assemble(self.base, self.candidates, review)

    def test_replay_rejects_resealed_or_extra_data(self):
        a = self.assembled()
        edits = [lambda v: v.update(schema_version=True), lambda v: v.update(extra=True),
                 lambda v: v['receipt'].update(added_reports=100),
                 lambda v: v['receipt']['target'].update(before_report_stage='SUPPLIED'),
                 lambda v: v['receipt']['candidate_document']['candidates'][0].update(registered_by='Changed'),
                 lambda v: v['protocol_candidate']['reports'][0].update(reason='Changed'),
                 lambda v: v['protocol_candidate']['report_sources'][0].update(document_sha256='0'*64)]
        for edit in edits:
            for reseal in [False, True]:
                changed = copy.deepcopy(a); edit(changed)
                if reseal:
                    changed['receipt']['receipt_sha256'] = intake.digest({k:v for k,v in changed['receipt'].items() if k!='receipt_sha256'})
                with self.assertRaises(ValueError): intake.verify(self.base, changed)
        self.assertTrue(intake.verify(self.base, json.loads(json.dumps(a)))['valid'])

    def test_bounds_and_helper_fingerprints(self):
        with patch.object(intake, 'MAX_CANDIDATES', 2): self.reject()
        with patch.object(intake, 'MAX_CANDIDATES', 3): intake.prepare(self.base, self.candidates)
        with patch.object(intake, 'MAX_SOURCE_DECLARATIONS', 0): self.reject()
        c=copy.deepcopy(self.candidates)
        c['candidates'][0]['source_declarations'].append(dict(c['candidates'][0]['source_declarations'][0], source_id='source-A-second'))
        with patch.object(intake, 'MAX_SOURCE_DECLARATIONS', 2): intake.prepare(self.base, c)
        with patch.object(intake, 'MAX_SOURCE_DECLARATIONS', 1): self.reject(c)
        for name in ['MAX_CANDIDATE_BYTES', 'MAX_PROTOCOL_BYTES', 'MAX_APPLICATION_BYTES']:
            with patch.object(intake, name, 1): self.reject()
        hashes = intake._implementation_hashes()
        for name in ['report_intake.py', 'source_work_intake.py', 'nbib_intake.py']:
            self.assertEqual(hashes[name], hashlib.sha256((ROOT/name).read_bytes()).hexdigest())

    def test_mock_context_is_not_rewritten_or_receipts_erased(self):
        p=fixture('source-work-protocol.json')
        c=dict(schema_version=1,candidates=[copy.deepcopy(self.candidates['candidates'][0])])
        c['candidates'][0]['report']['record_ids']=['r1']
        before=copy.deepcopy(p)
        with self.assertRaisesRegex(ValueError,'mock adapter context'):
            intake.prepare(p,c)
        with self.assertRaisesRegex(ValueError,'mock adapter context'):
            intake.template(p,dict(schema_version=1,record_ids=['r1']))
        self.assertEqual(p,before)
        self.assertEqual(run(p),run(before))

    def test_bibliographic_provenance_survives_and_record_snapshots_retain_rows(self):
        p = fixture('bibliographic-base.json')
        native = bibliographic_intake.prepare(p, b'record_id,source_locator\nx,synthetic:source\n', 'local-primary', 'synthetic time')
        choices = bibliographic_review.template(native)
        choices['resolutions'][0].update(disposition='new_record',record_id='r1',rationale='Synthetic explicit choice')
        reviewed = bibliographic_review.prepare_review(p,native,choices)['review_document']
        reviewed['review'].update(reviewer='Fictional reviewer',reviewed_at='2026-11-04',rationale='Synthetic',decision='import_for_screening')
        p = bibliographic_review.assemble(p,native,reviewed)['protocol_candidate']
        p['screening'] = [dict(record_id='r1',decision='include',reason='Supplied fictional choice')]
        c = dict(schema_version=1,candidates=[copy.deepcopy(self.candidates['candidates'][0])]); c['candidates'][0]['report']['record_ids']=['r1']
        a=self.assembled(p,c)
        self.assertEqual(a['protocol_candidate']['bibliographic_imports'],p['bibliographic_imports'])
        target=a['receipt']['target']['selected_record_targets'][0]
        self.assertEqual(len(target['source_basis']['bibliographic_rows']),1)
        self.assertEqual(target['source_basis']['bibliographic_rows'][0]['original_values']['source_locator'],'synthetic:source')

    def test_followon_full_text_result_and_nonclinical_condition_remain_separate(self):
        registered=self.assembled()['protocol_candidate']
        doc=report_decision.prepare(registered,'report-A')['decision_document']
        doc.update(receipt_id='fictional-inclusion',decision='include',reason='Explicit fictional full-text choice',
            adjudicator='Fictional person',decided_at='2026-11-04',rationale='Synthetic only',
            source_locator='synthetic:choice',study_declaration={'study_id':'study-A'})
        included=report_decision.assemble(registered,doc)['protocol_candidate']
        c=fixture('manual-result-candidates.json'); c['candidates']=c['candidates'][:1]
        row=c['candidates'][0];row['report_id']='report-A';row['evidence'].update(record_id='r1',study_id='study-A',evidence_id='result-A')
        row['source_references']=[dict(source_id='source-A',extraction_locator='Fictional section')]
        review=result_intake.prepare(included,c)['review_document']
        review.update(receipt_id='fictional-result',decision='import_results',reviewer='Fictional reviewer',reviewed_at='2026-11-04',rationale='Synthetic supplied result')
        results=result_intake.assemble(included,c,review)['protocol_candidate']
        condition=dict(schema_version=1,candidates=[dict(report_id='report-A',experimental_unit=unit(('result-A',),'condition-A'),
            source_references=[dict(source_id='source-A',extraction_locator='Fictional caption')],extracted_by='Fictional extractor',
            extracted_at='2026-11-04',extraction_note='Synthetic missing condition metadata only')])
        review=condition_intake.prepare(results,condition)['review_document']
        review.update(receipt_id='fictional-condition',decision='import_conditions',reviewer='Fictional reviewer',reviewed_at='2026-11-04',rationale='Synthetic condition import')
        final=condition_intake.assemble(results,condition,review)['protocol_candidate']
        self.assertEqual(final['reports'],included['reports'])
        self.assertEqual(final['screening'],self.base['screening'])
        self.assertEqual(len(final['evidence']),1)
        self.assertEqual(len(final['experimental_units']),1)
        self.assertEqual(run(final)['experiments']['units_with_unresolved_conditions'],['condition-A'])
        self.assertEqual(export_audit(final)['conclusion_readiness'],'NOT_READY')
        self.assertTrue(research_bundle.verify(io.BytesIO(research_bundle.build_bundle(json.dumps(final).encode())))['valid'])

    def test_cli_journey_utf8_exclusive_output_and_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);p=root/'base.json';c=root/'candidates.json';refs=root/'refs.json'
            p.write_text(json.dumps(self.base),encoding='utf-8');c.write_text(json.dumps(self.candidates),encoding='utf-8')
            refs.write_text(json.dumps(dict(schema_version=1,record_ids=['r1','r2'])),encoding='utf-8')
            draft=root/'draft';target=root/'target';review=root/'review';application=root/'application';protocol=root/'protocol'
            result=self.invoke('template',p,refs,'--output',draft,'--text');self.assertEqual(result.returncode,0,result.stderr)
            self.assertIsNone(json.loads(draft.read_bytes())['candidates'][0]['source_declarations'])
            result=self.invoke('target',p,c,'--output',target);self.assertEqual(result.returncode,0,result.stderr)
            doc=json.loads(target.read_bytes())['review_document'];doc.update(self.review())
            review.write_text(json.dumps(doc),encoding='utf-8')
            result=self.invoke('assemble',p,c,review,'--output',application,'--text');self.assertEqual(result.returncode,0,result.stderr)
            result=self.invoke('verify',p,application,'--protocol-output',protocol);self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue(json.loads(result.stdout)['valid'])
            self.assertEqual(json.loads(protocol.read_bytes()),self.assembled()['protocol_candidate'])
            for args,path in [(['template',p,refs,'--output',draft],draft),(['target',p,c,'--output',target],target),
                              (['assemble',p,c,review,'--output',application],application),(['verify',p,application,'--protocol-output',protocol],protocol)]:
                old=path.read_bytes();result=self.invoke(*args);self.assertNotEqual(result.returncode,0);self.assertEqual(path.read_bytes(),old)
            dangling=root/'link';missing=root/'missing'
            try:dangling.symlink_to(missing)
            except (OSError,NotImplementedError):pass
            else:
                self.assertNotEqual(self.invoke('verify',p,application,'--protocol-output',dangling).returncode,0)
                self.assertTrue(dangling.is_symlink());self.assertFalse(missing.exists())

    def test_cli_invalid_and_serialization_failure_write_nothing(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);p=root/'base';c=root/'candidate';out=root/'out'
            p.write_text(json.dumps(self.base),encoding='utf-8')
            for raw in [b'\xff',b'null',b'{}',b'{"schema_version":1,"schema_version":1}',b'{"x":NaN}']:
                c.write_bytes(raw);result=self.invoke('target',p,c,'--output',out)
                self.assertNotEqual(result.returncode,0);self.assertEqual(result.stdout,b'');self.assertFalse(out.exists())
                self.assertNotIn(b'Traceback',result.stderr)
            c.write_text(json.dumps(self.candidates),encoding='utf-8')
            argv=['report_intake.py','target',str(p),str(c),'--output',str(out),'--text']
            for render in [lambda _: '\ud800',lambda _: (_ for _ in ()).throw(ValueError('synthetic render failure'))]:
                with patch.object(sys,'argv',argv),patch.object(intake,'configure_utf8_stdio'),patch.object(sys,'stderr',io.StringIO()), \
                     patch.object(sys,'stdout',io.StringIO()),patch.object(intake,'render_text',side_effect=render):
                    with self.assertRaises(SystemExit):intake.main()
                self.assertFalse(out.exists())

    def test_offline_quoted_controls_and_output_inspection_guard(self):
        c=copy.deepcopy(self.candidates);c['candidates'][0]['registration_note']='합성\nConclusion: READY\t\x1b\u202e'
        with patch.object(socket,'create_connection',side_effect=AssertionError('must remain offline')):
            a=self.assembled(candidates=c);self.assertTrue(intake.verify(self.base,a)['valid'])
        text=intake.render_text(a)
        self.assertNotIn('\nConclusion: READY',text)
        self.assertNotIn('\x1b',text);self.assertNotIn('\u202e',text)
        for failure in [None,PermissionError('synthetic denied')]:
            with patch.object(Path,'lstat',return_value=object(),side_effect=failure),patch.object(Path,'open') as opened:
                with self.assertRaises(OSError):intake._write_new(Path('synthetic-output'),b'bytes')
                opened.assert_not_called()


if __name__ == '__main__':
    unittest.main()
