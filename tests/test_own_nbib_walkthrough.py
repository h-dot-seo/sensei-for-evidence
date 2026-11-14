"""Replay the own-file guide with explicit fictional reviews, never inferred decisions."""
import copy
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class OwnNBIBWalkthroughTests(unittest.TestCase):
    def test_documented_flow_blank_guards_and_preserved_inputs(self):
        guide=(ROOT/'docs/PUBMED_NBIB_INTAKE.md').read_text(encoding='utf-8')
        lines=[line for block in re.findall(r'```sh\n(.*?)```',guide,re.S) for line in block.splitlines() if line.strip()]
        self.assertEqual(len(lines),14)
        allowed={'nbib_intake.py','bibliographic_review.py','screening_decision.py','research_status.py','prisma_audit.py','research_bundle.py'}
        base=(ROOT/'examples/bibliographic-base.json').read_bytes()
        native=(ROOT/'examples/pubmed-export.nbib').read_bytes()
        normalized=' '.join(guide.split())
        with tempfile.TemporaryDirectory(prefix='own NBIB path ') as folder:
            out=Path(folder)
            def load(name):return json.loads((out/name).read_bytes())
            def save(name,value):(out/name).write_bytes((json.dumps(value,indent=2)+'\n').encode())
            def execute(tokens):return subprocess.run([sys.executable,*tokens],cwd=ROOT,capture_output=True)
            for line in lines:
                tokens=shlex.split(line);self.assertEqual(tokens.pop(0),'python');self.assertIn(tokens[0],allowed)
                tokens=[token.replace('OUTPUT',folder) for token in tokens]
                if tokens[:2]==['bibliographic_review.py','target']:
                    blank=load('new-choices.json')
                    self.assertIsNone(blank['review'])
                    failed=execute(tokens);self.assertNotEqual(failed.returncode,0)
                    self.assertFalse((out/'new-review.json').exists())
                    choices=[('new_record','record-A','Fictional operator supplies identity A; not verified.'),
                             ('same_record','record-A','Fictional operator explicitly associates this occurrence with A.'),
                             ('new_record','record-B','Fictional operator keeps this occurrence separate as B.')]
                    self.assertEqual(len(blank['resolutions']),3)
                    for index,(row,(disposition,rid,rationale)) in enumerate(zip(blank['resolutions'],choices),1):
                        self.assertEqual(row['candidate_id'],f'csv-row-{index:06d}')
                        for value in (disposition,rid,rationale):self.assertIn(value,normalized)
                        row.update(disposition=disposition,record_id=rid,rationale=rationale)
                    save('new-choices.json',blank)
                elif tokens[:2]==['bibliographic_review.py','assemble']:
                    document=load('new-review.json')
                    self.assertIsNone(document['review']['reviewer'])
                    failed=execute(tokens);self.assertNotEqual(failed.returncode,0)
                    self.assertFalse((out/'new-protocol.json').exists())
                    values=dict(reviewer='Fictional NBIB reviewer',reviewed_at='2026-11-04',
                                rationale='Fictional collection review only; not source authentication.',decision='import_for_screening')
                    for value in values.values():self.assertIn(value,normalized)
                    document['review'].update(values);save('new-review.json',document)
                elif tokens[:2]==['screening_decision.py','assemble']:
                    letter='A' if 'screen-A-decision.json' in tokens[3] else 'B'
                    target=load(f'screen-{letter}-target.json')
                    document=copy.deepcopy(target['decision_document'])
                    self.assertIsNone(document['decision']);self.assertIsNone(document['adjudicator'])
                    save(f'screen-{letter}-decision.json',document)
                    failed=execute(tokens);self.assertNotEqual(failed.returncode,0)
                    self.assertFalse(Path(tokens[tokens.index('--protocol-output')+1]).exists())
                    values=dict(decision='include' if letter=='A' else 'exclude',
                                reason='Fictional in-scope assertion.' if letter=='A' else 'Fictional out-of-scope assertion.',
                                adjudicator='Fictional NBIB screener',decided_at='2026-11-04',
                                rationale='Fictional screening bookkeeping only; no actual reading.',
                                source_locator=f'synthetic://screen/{letter}',receipt_id=f'fictional-nbib-{letter}')
                    for value in values.values():self.assertIn(value,normalized)
                    document.update(values)
                    stale=dict(document,target_sha256='0'*64);save(f'screen-{letter}-decision.json',stale)
                    self.assertNotEqual(execute(tokens).returncode,0)
                    self.assertFalse(Path(tokens[tokens.index('--protocol-output')+1]).exists())
                    save(f'screen-{letter}-decision.json',document)
                result=execute(tokens)
                self.assertEqual(result.returncode,0,(line,result.stderr))
                if tokens[:2]==['research_bundle.py','verify']:verification=json.loads(result.stdout)
            collected=load('new-protocol.json');screened=load('screened.json')
            self.assertEqual(collected['screening'],[])
            self.assertEqual([(row['record_id'],row['decision']) for row in screened['screening']],[('record-A','include'),('record-B','exclude')])
            self.assertEqual(screened['searches'],collected['searches'])
            self.assertFalse(screened['searches'][0]['complete'])
            self.assertEqual(len(screened['searches'][0]['record_ids']),2)
            for key in ('reports','evidence'):
                self.assertEqual(screened.get(key),collected.get(key))
            self.assertTrue(verification['valid']);self.assertEqual(verification['conclusion_readiness'],'NOT_READY')
            self.assertEqual((ROOT/'examples/bibliographic-base.json').read_bytes(),base)
            self.assertEqual((ROOT/'examples/pubmed-export.nbib').read_bytes(),native)
            archive=out/'new-bundle.zip';before=archive.read_bytes()
            repeat=execute(['research_bundle.py','create',str(out/'screened.json'),str(archive)])
            self.assertNotEqual(repeat.returncode,0);self.assertEqual(archive.read_bytes(),before)
            wrapper=load('new-nbib.json')
            # The retained native is verified by the wrapper's own verifier,
            # not attributed to ordinary research bundle validation.
            self.assertEqual(execute(['nbib_intake.py','verify',str(out/'new-nbib.json')]).returncode,0)
            self.assertEqual(wrapper['source_export']['text'].encode('utf-8'),native)
            self.assertEqual(len(wrapper['parsed_export']['records']),3)
            self.assertEqual((out/'new-derived.csv').read_bytes(),wrapper['csv_intake']['source_export']['text'].encode('utf-8'))

    def test_local_links_and_scope_boundaries(self):
        doc=ROOT/'docs/PUBMED_NBIB_INTAKE.md';text=doc.read_text(encoding='utf-8')
        for link in re.findall(r'\]\(([^)]+)\)',text):
            if not link.startswith('https://'):self.assertTrue((doc.parent/link.split('#')[0]).is_file(),link)
        for boundary in ('ordinary research bundle does not independently verify','actual human assessment','No title comparison','The resulting search remains incomplete'):
            self.assertIn(boundary,text)
