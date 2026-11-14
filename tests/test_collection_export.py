"""Synthetic native occurrence selection and exact export replay."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import collection_export as export
import ris_intake
import nbib_intake
from tests import test_native_collection_bundle as fixtures
ROOT=Path(__file__).resolve().parents[1]
class ExportTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.NativeCollectionBundleTests();self.fixture.setUp()
        self.p=self.fixture.protocol;self.b=self.fixture.bindings
    def test_batch_exact_bodies_bom_separator_and_immutable(self):
        before=copy.deepcopy((self.p,self.b))
        with patch('socket.socket',side_effect=AssertionError('network')),patch('subprocess.run',side_effect=AssertionError('process')):
            raw,r=export.build(self.p,self.b,'pending')
        self.assertEqual(before,(self.p,self.b));self.assertEqual(raw,export.build(self.p,self.b,'pending')[0])
        self.assertEqual(r['exported_occurrences'],2);self.assertTrue(r['occurrences'][0]['bom_omitted'])
        self.assertEqual(r['occurrences'][0]['source_index'],0);self.assertEqual(r['occurrences'][1]['source_index'],1)
        self.assertTrue(export.verify(self.p,self.b,'pending',raw)['valid'])
        with self.assertRaisesRegex(ValueError,'differs'):export.verify(self.p,self.b,'pending',raw+b'\n')
    def test_include_exclude_and_pending_are_screening_not_report(self):
        p=copy.deepcopy(self.p);p['screening']=[dict(record_id='fictional-A',decision='include',reason='supplied'),dict(record_id='fictional-A1',decision='exclude',reason='supplied')]
        for decision in ('include','exclude'):
            raw,r=export.build(p,self.b,decision);self.assertEqual(len(r['occurrences']),1);self.assertEqual(r['occurrences'][0]['decision'],decision)
        self.assertEqual(export.build(p,self.b,'pending')[0],b'')
    def test_empty_no_output_and_cli(self):
        with tempfile.TemporaryDirectory(prefix='sensei export ') as td:
            p=Path(td)/'p.json';w=Path(td)/'w.json';out=Path(td)/'out.nbib'
            p.write_text(json.dumps(self.p));w.write_text(json.dumps(self.b[0]['artifact']))
            args=[sys.executable,str(ROOT/'collection_export.py'),'create',str(p),'--nbib-batch','0='+str(w),'--decision','include','--output',str(out)]
            r=subprocess.run(args,capture_output=True);self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(r.stdout)['status'],'NO_OUTPUT');self.assertFalse(out.exists())
            args[args.index('include')]='pending';r=subprocess.run(args,capture_output=True);self.assertEqual(r.returncode,0,r.stderr);self.assertTrue(out.exists())
            r=subprocess.run(args,capture_output=True);self.assertEqual(r.returncode,1)
            args[2]='verify';r=subprocess.run(args,capture_output=True);self.assertEqual(r.returncode,0,r.stderr)
    def test_exact_historical_binding_and_explicit_join(self):
        b=copy.deepcopy(self.b);b[0]['import_index']=1
        with self.assertRaisesRegex(ValueError,'unknown import'):export.build(self.p,b,'pending')
        b=copy.deepcopy(self.b);b[0]['artifact']['source_exports'].reverse()
        with self.assertRaises(ValueError):export.build(self.p,b,'pending')
    def test_ris_bom_no_final_terminator(self):
        raw=b'\xef\xbb\xbfTY  - JOUR\r\nTI  - Fictional\r\nER  -'
        wrapper=ris_intake.prepare(self.fixture.base,raw,'local-primary','synthetic')
        p=self.fixture.imported(self.fixture.base,wrapper['csv_intake'],'r')
        out,r=export.build(p,[dict(import_index=0,format='ris',artifact=wrapper)],'pending')
        self.assertEqual(out,b'TY  - JOUR\r\nTI  - Fictional\r\nER  -\r\n')
        self.assertEqual(r['occurrences'][0]['terminator_added'],'\r\n');self.assertTrue(r['occurrences'][0]['bom_omitted'])
    def test_single_nbib_and_missing_wrapper_coverage(self):
        w=nbib_intake.prepare(self.fixture.base,b'PMID- 12345\nTI  - Fictional','local-primary','synthetic')
        p=self.fixture.imported(self.fixture.base,w['csv_intake'],'extra')
        # This is not the same historical import, so it may not stand in for the batch.
        with self.assertRaisesRegex(ValueError,'historical import'):export.build(self.p,[dict(import_index=0,format='nbib',artifact=w)],'pending')
        out,r=export.build(p,[dict(import_index=0,format='nbib',artifact=w)],'pending');self.assertTrue(out.endswith(b'\n\n'));self.assertEqual(r['occurrences'][0]['terminator_added'],'\n')
    def test_duplicate_binding_mix_and_limits(self):
        with self.assertRaises(ValueError):export.build(self.p,self.b*2,'pending')
        b=copy.deepcopy(self.b);b.append(dict(import_index=1,format='ris',artifact={}))
        with self.assertRaisesRegex(ValueError,'cannot be mixed'):export.build(self.p,b,'pending')
        with patch.object(export,'MAX_BYTES',20):
            with self.assertRaises(ValueError):export.build(self.p,self.b,'pending')
    def test_withheld_not_exclude(self):
        import bibliographic_review
        f=self.fixture;w=f.wrapper;choices=bibliographic_review.template(w['csv_intake'])
        for row in choices['resolutions']:row.update(disposition='do_not_promote',record_id=None,rationale='synthetic triage')
        d=bibliographic_review.prepare_review(f.base,w['csv_intake'],choices)['review_document'];d['review'].update(reviewer='Fictional',reviewed_at='2026-11-14',rationale='synthetic',decision='import_for_screening')
        p=bibliographic_review.assemble(f.base,w['csv_intake'],d)['protocol_candidate']
        out,r=export.build(p,self.b,'withheld');self.assertEqual(len(r['occurrences']),2);self.assertEqual(export.build(p,self.b,'exclude')[0],b'')

    def test_nonbibliographic_occurrence_of_also_exported_record_reported(self):
        base=copy.deepcopy(self.fixture.base)
        base['searches'].append(dict(base['search_plan'][1],searched_at='2026',record_ids=['fictional-A'],total_count=1,complete=True,has_more=False))
        import nbib_batch_intake
        wrapper=nbib_batch_intake.prepare(base,self.fixture.sources,'local-primary','synthetic')
        # Import one occurrence as an explicit existing-record link.
        import bibliographic_review
        choices=bibliographic_review.template(wrapper['csv_intake'])
        choices['resolutions'][0].update(disposition='same_record',record_id='fictional-A',rationale='synthetic link')
        choices['resolutions'][1].update(disposition='new_record',record_id='fictional-A1',rationale='synthetic new')
        d=bibliographic_review.prepare_review(base,wrapper['csv_intake'],choices)['review_document']
        d['review'].update(reviewer='Fictional',reviewed_at='2026-11-14',rationale='synthetic',decision='import_for_screening')
        p=bibliographic_review.assemble(base,wrapper['csv_intake'],d)['protocol_candidate']
        raw,result=export.build(p,[dict(import_index=0,format='nbib_batch',artifact=wrapper)],'pending')
        self.assertEqual(result['exported_occurrences'],2)
        self.assertEqual(result['not_exported_count'],1)
        self.assertEqual(result['not_exported'][0]['cause'],'NON_BIBLIOGRAPHIC_SEARCH')
        self.assertEqual(result['not_exported'][0]['search_occurrences'][0]['search_index'],0)
