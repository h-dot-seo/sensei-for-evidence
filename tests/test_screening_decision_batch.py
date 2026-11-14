"""Synthetic exact decision-sheet preview; never an application or approval."""
import copy
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from json_io import canonical_json_bytes
import screening_decision
import screening_decision_batch as batch
import screening_decision_sheet as sheet
from tests.test_screening_sheet_intake import rewrite
from tests.test_screening_reviews import protocol, assertion

ROOT = Path(__file__).resolve().parents[1]


def fill(rows):
    for i, row in enumerate(rows):
        row.update(receipt_id='synthetic-'+str(i), decision='include', reason='Synthetic reason',
                   adjudicator='Synthetic human', decided_at='2026-11-14',
                   rationale='Supplied synthetic choice, not consensus', source_locator='synthetic:decision')


class DecisionBatchPreviewTests(unittest.TestCase):
    def setUp(self):
        self.p = protocol()
        self.blank = sheet.export_sheet(self.p, ['r2', 'pending'])[0]
        self.raw = rewrite(self.blank, fill)

    def test_exact_reproducible_hypothetical_chain_and_blank_review(self):
        original = copy.deepcopy(self.p)
        with patch('socket.socket', side_effect=AssertionError('no network')):
            result = batch.prepare(self.p, self.raw)
        self.assertEqual(self.p, original)
        self.assertEqual(result, batch.prepare(self.p, self.raw))
        self.assertNotIn('protocol_candidate', result)
        self.assertNotIn('application', result)
        self.assertFalse(result['approval_granted'])
        self.assertFalse(result['canonical_screening_changed'])
        self.assertEqual(result['status'], 'READ_ONLY_TARGET_PREVIEW')
        for key in ('receipt_id','reviewer','reviewed_at','rationale'):
            self.assertIsNone(result['review_document'][key])
        self.assertEqual(result['review_document']['decision'], 'apply_screening_decisions')
        t = result['target']; candidate = copy.deepcopy(self.p)
        self.assertEqual(t['sheet_sha256'], hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(t['sheet_bytes'], len(self.raw))
        self.assertEqual([x['record_id'] for x in t['hypothetical_steps']], ['r2','pending'])
        for step in t['hypothetical_steps']:
            doc = screening_decision.prepare(candidate, step['record_id'])['decision_document']
            doc.update({key: step['supplied_decision'][key] for key in sheet.HUMAN_COLUMNS})
            applied = screening_decision.assemble(candidate, doc)
            self.assertEqual(step['hypothetical_target'], applied['appended_receipt']['target'])
            self.assertEqual(step['hypothetical_receipt_sha256'], applied['appended_receipt']['receipt_sha256'])
            self.assertFalse(step['applied'])
            candidate = applied['protocol_candidate']
        steps = t['hypothetical_steps']
        self.assertEqual(steps[1]['hypothetical_target']['previous_receipt_sha256'], steps[0]['hypothetical_receipt_sha256'])
        self.assertEqual(t['projected_protocol_sha256'], hashlib.sha256(canonical_json_bytes(candidate)).hexdigest())
        self.assertNotEqual(steps[0]['hypothetical_target']['target_sha256'], t['target_sha256'])
        for row in t['parsed_human_rows']:
            span=row['source_span']; self.assertEqual(hashlib.sha256(self.raw[span['byte_start']:span['byte_end']]).hexdigest(),span['sha256'])

    def test_blank_skip_partial_and_invalid_choices(self):
        with self.assertRaises(ValueError):batch.prepare(self.p,self.blank)
        one = rewrite(self.raw, lambda rows: rows[1].update({key:'' for key in sheet.HUMAN_COLUMNS}))
        result=batch.prepare(self.p,one)
        self.assertEqual(len(result['target']['hypothetical_steps']),1)
        self.assertEqual(len(result['target']['skipped_blank_human_rows']),1)
        for key,value in [('reason',''),('rationale',' '),('decision','unclear'),('decided_at','11/14/2026'),('decided_at','2026-02-30')]:
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                batch.prepare(self.p,rewrite(self.raw,lambda rows:rows[0].update({key:value})))

    def test_formula_prefixes_are_not_unescaped_or_guessed(self):
        for value in ["'=formula",'=formula','+formula','-formula','@formula',' text','\ttext',"'literal"]:
            with self.subTest(value=value),self.assertRaises(ValueError):
                batch.prepare(self.p,rewrite(self.raw,lambda rows:rows[0].update(reason=value)))

    def test_every_readonly_cell_exact_and_original_drift_fails(self):
        import csv,io
        headers=next(csv.reader(io.StringIO(self.raw.decode('utf-8'))))
        for key in [k for k in headers if k not in sheet.HUMAN_COLUMNS]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                batch.prepare(self.p,rewrite(self.raw,lambda rows:rows[0].update({key:rows[0][key]+'x'})))
        for mutate in [lambda p:p.update(version='changed'),lambda p:p['screening'][0].update(reason='changed'),
                       lambda p:p['inclusion_criteria'].append('changed'),lambda p:p.update(screening_reviews=[assertion(p)])]:
            p=copy.deepcopy(self.p);mutate(p)
            with self.assertRaises(ValueError):batch.prepare(p,self.raw)

    def test_duplicate_row_receipt_and_existing_receipt_fail(self):
        with self.assertRaises(ValueError):batch.prepare(self.p,rewrite(self.raw,lambda rows:rows.append(copy.deepcopy(rows[0]))))
        with self.assertRaises(ValueError):batch.prepare(self.p,rewrite(self.raw,lambda rows:rows[1].update(receipt_id=rows[0]['receipt_id'])))
        doc=screening_decision.prepare(self.p,'r1')['decision_document']
        fill([doc]);p=screening_decision.assemble(self.p,doc)['protocol_candidate']
        raw=rewrite(sheet.export_sheet(p,['r2'])[0],fill)
        with self.assertRaises(ValueError):batch.prepare(p,raw)

    def test_max100_sheet_and_lifetime_preflight(self):
        p=protocol();ids=['id-'+str(i) for i in range(101)]
        p['searches'][0].update(record_ids=ids,total_count=len(ids));p['screening']=[]
        raw=sheet.export_sheet(p,ids[:100])[0]
        raw=rewrite(raw,lambda rows:fill(rows[:1]))
        self.assertEqual(len(batch.prepare(p,raw)['target']['parsed_human_rows']),100)
        completed=rewrite(sheet.export_sheet(p,ids[:100])[0],fill)
        self.assertEqual(len(batch.prepare(p,completed)['target']['hypothetical_steps']),100)
        with self.assertRaises(ValueError):batch.prepare(p,rewrite(raw,lambda rows:rows.append(copy.deepcopy(rows[0]))))
        with patch.object(batch.screening_decision_links,'MAX_RECEIPTS',1),self.assertRaises(ValueError):
            batch.prepare(self.p,self.raw)
        with patch.object(batch,'MAX_DECISIONS',1),self.assertRaises(ValueError):batch.prepare(self.p,self.raw)
        self.assertEqual(batch.MAX_DECISIONS,100)

    def test_whole_operational_gate_failure_leaves_input_unchanged(self):
        p=json.loads((ROOT/'examples/report-protocol.json').read_bytes());original=copy.deepcopy(p)
        raw=rewrite(sheet.export_sheet(p,['r1'])[0],fill)
        raw=rewrite(raw,lambda rows:rows[0].update(decision='exclude'))
        with self.assertRaises(ValueError):batch.prepare(p,raw)
        self.assertEqual(p,original)
        later=rewrite(sheet.export_sheet(p,['r2','r1'])[0],fill)
        later=rewrite(later,lambda rows:rows[1].update(decision='exclude'))
        with patch.object(batch.screening_decision,'assemble',wraps=screening_decision.assemble) as gate:
            with self.assertRaises(ValueError):batch.prepare(p,later)
            self.assertEqual(gate.call_count,2)
        self.assertEqual(p,original)
        p['evidence']=[];p['gaps']=[]
        raw=rewrite(sheet.export_sheet(p,['r1'])[0],fill)
        raw=rewrite(raw,lambda rows:rows[0].update(decision='exclude'))
        with self.assertRaises(ValueError):batch.prepare(p,raw)
        with patch.object(batch.screening_decision,'assemble',side_effect=ValueError('synthetic gate failure')),self.assertRaises(ValueError):
            batch.prepare(self.p,self.raw)

    def test_positions_unchanged_and_conflict_does_not_select_choice(self):
        self.p['screening_reviews']=[assertion(self.p,'r2',decision='exclude'),assertion(self.p,'r2',reviewer='Fictional B',review_id='b',decision='unclear')]
        original=copy.deepcopy(self.p)
        raw=rewrite(sheet.export_sheet(self.p,['r2'])[0],fill)
        result=batch.prepare(self.p,raw)
        self.assertEqual(self.p,original)
        step=result['target']['hypothetical_steps'][0]
        self.assertEqual(step['projected_screening_row']['decision'],'include')
        self.assertEqual(step['hypothetical_target']['review_snapshots'],self.p['screening_reviews'])

    def test_raw_bytes_order_and_implementation_bound_to_target(self):
        original=batch.prepare(self.p,self.raw)['target']['target_sha256']
        raw=b'\xef\xbb\xbf'+self.raw.replace(b'\n',b'\r\n')
        self.assertNotEqual(batch.prepare(self.p,raw)['target']['target_sha256'],original)
        reverse=rewrite(self.raw,lambda rows:rows.reverse())
        self.assertNotEqual(batch.prepare(self.p,reverse)['target']['target_sha256'],original)
        with patch.object(batch,'_hashes',return_value={'changed':'implementation'}):
            self.assertNotEqual(batch.prepare(self.p,self.raw)['target']['target_sha256'],original)
        for raw in [b'\xff',self.raw+b'\x00',b'']:
            with self.assertRaises(ValueError):batch.prepare(self.p,raw)
        with patch.object(batch,'MAX_TARGET_BYTES',10),self.assertRaises(ValueError):batch.prepare(self.p,self.raw)

    def test_cli_failures_write_nothing_and_existing_output_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);p=d/'p.json';p.write_text(json.dumps(self.p),encoding='utf-8');s=d/'s.csv';s.write_bytes(self.raw);out=d/'target.json'
            args=[sys.executable,str(ROOT/'screening_decision_batch.py'),'target',str(p),str(s),'--output',str(out)]
            result=subprocess.run(args,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(out.read_bytes())['status'],'READ_ONLY_TARGET_PREVIEW')
            prior=out.read_bytes();self.assertNotEqual(subprocess.run(args,capture_output=True).returncode,0);self.assertEqual(out.read_bytes(),prior)
            s.write_bytes(rewrite(self.raw,lambda rows:rows[0].update(reason='')))
            other=d/'not-written.json';self.assertNotEqual(subprocess.run(args[:-1]+[str(other)],capture_output=True).returncode,0);self.assertFalse(other.exists())
            invalid=json.loads((ROOT/'examples/report-protocol.json').read_bytes());p.write_text(json.dumps(invalid),encoding='utf-8')
            raw=rewrite(sheet.export_sheet(invalid,['r2','r1'])[0],fill);s.write_bytes(rewrite(raw,lambda rows:rows[1].update(decision='exclude')))
            self.assertNotEqual(subprocess.run(args[:-1]+[str(other)],capture_output=True).returncode,0);self.assertFalse(other.exists())
            for mode in ('assemble','verify'):
                self.assertNotEqual(subprocess.run([sys.executable,str(ROOT/'screening_decision_batch.py'),mode],capture_output=True).returncode,0)
            self.assertEqual(sorted(x.name for x in d.iterdir()),['p.json','s.csv','target.json'])

    def test_documented_preview_command_verbatim(self):
        guide=(ROOT/'docs/SCREENING_DECISION_BATCH_PREVIEW.md').read_text(encoding='utf-8')
        blocks=re.findall(r'```sh\n(.*?)```',guide,re.S);self.assertEqual(len(blocks),1)
        with tempfile.TemporaryDirectory() as tmp:
            for line in blocks[0].splitlines():
                args=shlex.split(line);self.assertEqual(args[:2],['python','screening_decision_batch.py'])
                args=[str(Path(tmp)/x[7:]) if x.startswith('OUTPUT/') else x for x in args]
                result=subprocess.run([sys.executable,*args[1:]],cwd=ROOT,capture_output=True)
                self.assertEqual(result.returncode,0,result.stderr)
            result=json.loads((Path(tmp)/'target.json').read_bytes())
            self.assertEqual(result['status'],'READ_ONLY_TARGET_PREVIEW');self.assertFalse(result['approval_granted'])
            self.assertEqual([p.name for p in Path(tmp).iterdir()],['target.json'])
        tokens=shlex.split('python tool.py OUTPUT/target.json');replaced=[str(Path(r'C:\synthetic space')/x[7:]) if x.startswith('OUTPUT/') else x for x in tokens];self.assertIn(r'C:\synthetic space',replaced[-1])


if __name__ == '__main__':unittest.main()
