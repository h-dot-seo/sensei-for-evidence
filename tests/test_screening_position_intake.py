"""Synthetic long-form supplied-position transcription, not product interoperability."""
import base64
import copy
import csv
import hashlib
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

import screening_position_intake as intake
import screening_review
from tests.test_screening_reviews import protocol
from tests._cli import run_cli

ROOT = Path(__file__).resolve().parents[1]
COLUMNS = dict(record_id='Record', decision='Position', reviewer='Reader', reviewed_at='Date',
               rationale='Why', source_locator='Locator')
LABELS = dict(include='Included', exclude='Excluded', unclear='Maybe')


def export(rows=None, newline='\n'):
    if rows is None:
        rows = [['r1','Included','Fictional CSV A','2026-11-14','Synthetic only','synthetic:one'],
                ['r1','Excluded','Fictional CSV B','2026-11-14','Opposite supplied position','synthetic:one']]
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator=newline)
    writer.writerow(list(COLUMNS.values()));writer.writerows(rows)
    return output.getvalue().encode('utf-8')


def assertion(prepared):
    return dict(prepared['review_document'], receipt_id='fictional-import', reviewer='Fictional importer',
                reviewed_at='2026-11-14', rationale='Retain supplied fictional positions only.')


class PositionIntakeTests(unittest.TestCase):
    def setUp(self):
        self.p = protocol();self.raw = export();self.basis = screening_review.template(self.p)

    def preview(self, **kwargs):
        args = dict(protocol=self.p, raw=self.raw, basis_template=self.basis, columns=COLUMNS, labels=LABELS)
        args.update(kwargs)
        return intake.preview(**args)

    def test_multiple_positions_exact_bytes_and_append_only_replay(self):
        original = copy.deepcopy(self.p)
        with patch('socket.socket', side_effect=AssertionError('no network')):
            doc = self.preview(raw=b'\xef\xbb\xbf'+export(newline='\r\n'))
            target = intake.prepare(self.p, doc)
            self.assertIsNone(target['review_document']['reviewer'])
            app = intake.assemble(self.p, doc, assertion(target))
            self.assertTrue(intake.verify(self.p, app)['valid'])
        self.assertEqual(self.p, original)
        candidate = copy.deepcopy(app['protocol_candidate']);reviews = candidate.pop('screening_reviews')
        self.assertEqual(candidate, original)
        self.assertEqual([r['decision'] for r in reviews], ['include','exclude'])
        self.assertEqual([r['record_id'] for r in reviews], ['r1','r1'])
        raw = base64.b64decode(doc['provenance']['export_base64'])
        self.assertEqual(raw, b'\xef\xbb\xbf'+export(newline='\r\n'))
        for row in doc['provenance']['parsed_rows']:
            span=row['source_span']
            self.assertEqual(hashlib.sha256(raw[span['byte_start']:span['byte_end']]).hexdigest(),span['sha256'])
        self.assertEqual(target['target']['stale_rows'],0)
        self.assertFalse(target['canonical_screening_changed'])

    def test_unmapped_unknown_empty_bad_date_and_duplicate_rows_are_blocked(self):
        good=['r1','Included','Reader','2026-11-14','Synthetic','synthetic:x']
        for index,value in [(0,'missing'),(1,'include'),(2,''),(3,'2026-02-30'),(3,'2026-11-14T00:00'),(4,' ')]:
            row=list(good);row[index]=value
            with self.subTest(index=index,value=value):
                doc=self.preview(raw=export([row]));self.assertTrue(doc['blocked_rows'])
                with self.assertRaises(ValueError):intake.prepare(self.p,doc)
        doc=self.preview(raw=export([good,good]));self.assertTrue(doc['blocked_rows'])
        with self.assertRaises(ValueError):intake.prepare(self.p,doc)
        for index in [0,5]:
            row=list(good);row[index]=''
            with self.assertRaises(ValueError):self.preview(raw=export([row]))

    def test_no_current_hash_refresh_and_historical_implementation_not_required(self):
        self.basis['engine_sha256']={'historical.py':'a'*64}
        doc=self.preview()
        self.assertTrue(intake.prepare(self.p,doc))
        changed=copy.deepcopy(self.p);changed['inclusion_criteria'].append('Changed scope')
        stale=self.preview(protocol=changed)
        self.assertEqual(stale['screening_reviews'][0]['source_basis_sha256'],doc['screening_reviews'][0]['source_basis_sha256'])
        with self.assertRaisesRegex(ValueError,'re-examine'):intake.prepare(changed,stale)
        # Unrelated version metadata may change while exact reviewed source remains equal.
        changed=copy.deepcopy(self.p);changed['version']='new-metadata'
        self.assertTrue(intake.prepare(changed,self.preview(protocol=changed)))

    def test_template_hash_identity_duplicates_and_missing_target(self):
        for mutate in [lambda b:b['record_targets'][0].update(source_basis_sha256='a'*64),
                       lambda b:b['record_targets'].append(copy.deepcopy(b['record_targets'][0])),
                       lambda b:b['record_targets'][0]['source_basis'].update(record_id='wrong')]:
            b=copy.deepcopy(self.basis);mutate(b)
            with self.assertRaises(ValueError):self.preview(basis_template=b)
        b=copy.deepcopy(self.basis);b['record_targets']=[r for r in b['record_targets'] if r['record_id']!='r1']
        self.assertTrue(self.preview(basis_template=b)['blocked_rows'])

    def test_literal_mapping_no_normalization_and_generated_or_supplied_ids(self):
        row=['r1','Maybe','Consensus','2026-11-14',"'=literal, 한국어\nsecond line",'https://invalid.example/inert']
        doc=self.preview(raw=export([row]))
        self.assertEqual(doc['screening_reviews'][0]['rationale'],row[4])
        self.assertTrue(doc['screening_reviews'][0]['review_id'].startswith('csv-row-000001@'))
        raw=export([row]).decode().replace('Locator\n','Locator,ID\n').rstrip('\n')+',own-id\n'
        doc=self.preview(raw=raw.encode(),columns=dict(COLUMNS,review_id='ID'))
        self.assertEqual(doc['screening_reviews'][0]['review_id'],'own-id')
        for labels in [dict(include='Same',exclude='Same'),{'accept':'Included'},{}]:
            with self.assertRaises(ValueError):self.preview(labels=labels)
        with self.assertRaises(ValueError):self.preview(columns=dict(COLUMNS,decision='Record'))
        with self.assertRaises(ValueError):self.preview(columns=dict(COLUMNS,decision='absent'))

    def test_existing_positions_collisions_and_unchanged_history(self):
        doc=self.preview();app=intake.assemble(self.p,doc,assertion(intake.prepare(self.p,doc)))
        p=app['protocol_candidate']
        blocked=self.preview(protocol=p)
        self.assertTrue(blocked['blocked_rows'])
        with self.assertRaises(ValueError):intake.prepare(p,blocked)
        raw=export([['r1','Maybe','New reader','2026-11-14','Another position','synthetic:two']])
        nextdoc=self.preview(protocol=p,raw=raw)
        nextapp=intake.assemble(p,nextdoc,assertion(intake.prepare(p,nextdoc)))
        self.assertEqual(nextapp['protocol_candidate']['screening_reviews'][:2],p['screening_reviews'])

    def test_tampered_candidate_application_and_review_fail_closed(self):
        doc=self.preview();target=intake.prepare(self.p,doc);review=assertion(target)
        app=intake.assemble(self.p,doc,review)
        for key in ['screening_reviews','blocked_rows','provenance']:
            d=copy.deepcopy(doc);d[key]=None
            with self.assertRaises((ValueError,TypeError)):intake.prepare(self.p,d)
        for key in app:
            damaged=copy.deepcopy(app);damaged[key]=None
            with self.assertRaises((ValueError,TypeError)):intake.verify(self.p,damaged)
        for key,value in [('target_sha256','0'*64),('decision','accept'),('reviewer',''),('reviewed_at','2026-99-99')]:
            with self.assertRaises(ValueError):intake.assemble(self.p,doc,dict(review,**{key:value}))
        with patch.object(intake,'_hashes',return_value={'drift.py':'b'*64}):
            with self.assertRaises(ValueError):intake.verify(self.p,app)

    def test_bounds_no_rows_and_excessive_rows(self):
        with self.assertRaises(ValueError):self.preview(raw=export([]))
        with patch.object(intake,'MAX_POSITIONS',1):
            with self.assertRaises(ValueError):self.preview()
        with patch.object(intake,'MAX_INPUT_BYTES',4):
            with self.assertRaises(ValueError):self.preview()
        with patch.object(intake,'MAX_APPLICATION_BYTES',4):
            with self.assertRaises(ValueError):self.preview()

    def test_actual_hundred_row_limit_and_manual_id_collision(self):
        rows=[['r1','Maybe','Reader '+str(i),'2026-11-14','Synthetic only','synthetic:'+str(i)] for i in range(100)]
        doc=self.preview(raw=export(rows))
        self.assertEqual(len(doc['screening_reviews']),100)
        self.assertTrue(intake.prepare(self.p,doc))
        with self.assertRaises(ValueError):self.preview(raw=export(rows+[rows[0]]))
        stream=io.StringIO(newline='')
        writer=csv.writer(stream,lineterminator='\n')
        writer.writerow(list(COLUMNS.values())+['ID'])
        writer.writerows([rows[0]+['same'],rows[1]+['same']])
        blocked=self.preview(raw=stream.getvalue().encode(),columns=dict(COLUMNS,review_id='ID'))
        self.assertTrue(blocked['blocked_rows'])
        with self.assertRaises(ValueError):intake.prepare(self.p,blocked)
        empty=copy.deepcopy(self.p);empty['screening_reviews']=[]
        blankdoc=self.preview(protocol=empty)
        app=intake.assemble(empty,blankdoc,assertion(intake.prepare(empty,blankdoc)))
        self.assertEqual(empty['screening_reviews'],[])
        self.assertEqual(len(app['protocol_candidate']['screening_reviews']),2)

    def test_cli_failure_and_exclusive_output(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td);(td/'p.json').write_text(json.dumps(self.p));(td/'d.json').write_text(json.dumps(self.preview()))
            out=td/'target.json'
            args=['target',str(td/'p.json'),str(td/'d.json'),'--output',str(out)]
            result=run_cli('screening_position_intake.py',*args,cwd=td)
            self.assertEqual(result.returncode,0,result.stderr)
            saved=out.read_bytes()
            result=run_cli('screening_position_intake.py',*args,cwd=td)
            self.assertEqual(result.returncode,2);self.assertEqual(out.read_bytes(),saved)
            self.assertNotIn(b'Traceback',result.stderr)
            (td/'d.json').write_text('{}')
            result=run_cli('screening_position_intake.py','target',td/'p.json',td/'d.json',cwd=td)
            self.assertEqual(result.returncode,2);self.assertNotIn(b'Traceback',result.stderr)

    def test_documented_two_block_rehearsal(self):
        guide=(ROOT/'docs/SCREENING_POSITION_INTAKE.md').read_text()
        blocks=re.findall(r'```sh\n(.*?)```',guide,re.S)
        self.assertEqual(len(blocks),2)
        with tempfile.TemporaryDirectory(prefix='sensei positions ') as td:
            for index,block in enumerate(blocks):
                for line in block.strip().splitlines():
                    args=shlex.split(line)
                    self.assertEqual(args.pop(0),'python')
                    args=[a.replace('/outside',td) for a in args]
                    result=subprocess.run([sys.executable,*args],cwd=ROOT,capture_output=True)
                    self.assertEqual(result.returncode,0,result.stderr)
                if index==0:
                    target=json.loads((Path(td)/'positions-target.json').read_bytes())
                    (Path(td)/'positions-review.json').write_text(json.dumps(assertion(target)))
            original=json.loads((ROOT/'examples/screening-reviews.json').read_bytes())
            candidate=json.loads((Path(td)/'positions-protocol.json').read_bytes())
            self.assertEqual(candidate['screening'],original['screening'])
            self.assertEqual(candidate['screening_reviews'][:-2],original['screening_reviews'])
            self.assertEqual([r['decision'] for r in candidate['screening_reviews'][-2:]],['include','exclude'])
