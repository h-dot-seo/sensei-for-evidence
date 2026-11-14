"""Synthetic starting-protocol scaffolds, never a generated research design."""
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

import protocol_scaffold as scaffold
from json_io import canonical_json_bytes
from receipt_intake import fresh_base, template as receipt_template
from tests._cli import run_cli

ROOT=Path(__file__).resolve().parents[1]


def supplied():
    draft=scaffold.template()['draft']
    draft.update(question='Fictional question, not a research recommendation?',version='fictional-v1',
                 inclusion_criteria=['Supplied fictional scope'],exclusion_criteria=['Outside fictional scope'],
                 search_plan=[dict(search_id='fictional-plan',source='fictional-source',
                                   query='literal query = "한국어"',window='operator-declared fictional window')])
    return draft


class ScaffoldTests(unittest.TestCase):
    def test_template_is_unfilled_separate_and_deterministic(self):
        first=scaffold.template();second=scaffold.template()
        self.assertEqual(first,second)
        d=first['draft'];self.assertIsNone(d['question']);self.assertIsNone(d['version'])
        self.assertEqual(d['inclusion_criteria'],[]);self.assertEqual(d['exclusion_criteria'],[])
        self.assertTrue(all(v is None for v in d['search_plan'][0].values()))
        self.assertTrue(all(d[k]==[] for k in scaffold.LEDGERS))
        d['search_plan'][0]['query']='changed'
        self.assertIsNone(second['draft']['search_plan'][0]['query'])
        self.assertEqual(first['plan_adequacy'],'NOT_ASSESSED')

    def test_supplied_values_unchanged_validated_and_intake_usable(self):
        d=supplied();before=copy.deepcopy(d)
        with patch('socket.socket',side_effect=AssertionError('network forbidden')):
            result=scaffold.check(d);fresh_base(d);receipts=receipt_template(d)
        self.assertTrue(result['valid']);self.assertEqual(d,before)
        self.assertEqual(result['draft_sha256'],hashlib.sha256(canonical_json_bytes(d)).hexdigest())
        self.assertEqual(receipts['search_responses'][0]['request']['query'],d['search_plan'][0]['query'])
        self.assertIsNone(receipts['search_responses'][0]['request']['searched_at'])
        self.assertEqual(result['conclusion_readiness'],'NOT_READY')

    def test_null_blank_wrong_typed_and_missing_fields_have_pointers(self):
        blank=scaffold.check(scaffold.template()['draft']);self.assertFalse(blank['valid'])
        self.assertIn('/question',{h['input_pointer'] for h in blank['missing_hints']})
        for field in scaffold.TEXT_FIELDS:
            for value in [None,' ','',True,123,[],{}]:
                d=supplied();d[field]=value
                self.assertFalse(scaffold.check(d)['valid'])
        for field in scaffold.CRITERIA_FIELDS:
            for value in [None,[],[''],[' '],[True],'text']:
                d=supplied();d[field]=value
                self.assertFalse(scaffold.check(d)['valid'])
        for field in scaffold.FIELDS:
            d=supplied();del d[field]
            result=scaffold.check(d);self.assertFalse(result['valid'])
            self.assertIn('/'+field,{h['input_pointer'] for h in result['missing_hints']})
        for value in [None,[],True,123]:self.assertFalse(scaffold.check(value)['valid'])

    def test_unknown_keys_and_existing_research_are_not_discarded(self):
        for field in ['$schema','adapter_receipts','bibliographic_imports','reports','unknown/~key']:
            d=supplied();d[field]=[];before=copy.deepcopy(d)
            result=scaffold.check(d);self.assertFalse(result['valid']);self.assertEqual(d,before)
        for field in scaffold.LEDGERS:
            for value in [None,{},[{'retain':'existing'}],False]:
                d=supplied();d[field]=value;before=copy.deepcopy(d)
                self.assertFalse(scaffold.check(d)['valid']);self.assertEqual(d,before)

    def test_exact_plan_keys_nonblank_and_unique_ids(self):
        for value in [None,[],{},[None],[{}]]:
            d=supplied();d['search_plan']=value;self.assertFalse(scaffold.check(d)['valid'])
        for field in scaffold.PLAN_FIELDS:
            for value in [None,'',1,True]:
                d=supplied();d['search_plan'][0][field]=value;self.assertFalse(scaffold.check(d)['valid'])
            d=supplied();del d['search_plan'][0][field];self.assertFalse(scaffold.check(d)['valid'])
        d=supplied();d['search_plan'][0]['searched_at']='2026-11-14';self.assertFalse(scaffold.check(d)['valid'])
        d=supplied();d['search_plan'].append(copy.deepcopy(d['search_plan'][0]))
        self.assertFalse(scaffold.check(d)['valid'])
        d['search_plan'][1]['search_id']='second-exact-id';self.assertTrue(scaffold.check(d)['valid'])

    def test_engine_rejection_is_reported_and_never_approval(self):
        with patch.object(scaffold,'run',side_effect=ValueError('synthetic engine rejection')):
            result=scaffold.check(supplied())
        self.assertFalse(result['valid']);self.assertEqual(result['validator_error'],'synthetic engine rejection')
        self.assertEqual(result['protocol_approval'],'NOT_ESTABLISHED')
        with patch.object(scaffold,'MAX_BYTES',4):
            with self.assertRaises(ValueError):scaffold.check(supplied())

    def test_cli_draft_export_and_check_export_preserve_input(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td);draft=td/'draft.json';out=td/'base.json'
            result=run_cli('protocol_scaffold.py','template','--draft-output',draft,cwd=td)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(draft.read_bytes()),json.loads(result.stdout)['draft'])
            result=run_cli('protocol_scaffold.py','check',draft,'--protocol-output',out,cwd=td)
            self.assertEqual(result.returncode,2);self.assertFalse(out.exists())
            self.assertFalse(json.loads(result.stdout)['valid'])
            draft.write_text(json.dumps(supplied(),ensure_ascii=False),encoding='utf-8');raw=draft.read_bytes()
            result=run_cli('protocol_scaffold.py','check',draft,'--protocol-output',out,cwd=td)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(out.read_bytes()),supplied());self.assertEqual(draft.read_bytes(),raw)
            self.assertNotIn('boundary',json.loads(out.read_bytes()))
            saved=out.read_bytes()
            result=run_cli('protocol_scaffold.py','check',draft,'--protocol-output',out,cwd=td)
            self.assertEqual(result.returncode,2);self.assertEqual(out.read_bytes(),saved)
            result=run_cli('protocol_scaffold.py','check',draft,'--protocol-output',draft,cwd=td)
            self.assertEqual(result.returncode,2);self.assertEqual(draft.read_bytes(),raw)

    def test_strict_cli_json_errors_have_no_output_or_traceback(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td);draft=td/'draft.json';out=td/'out.json'
            for raw in [b'{"question":1,"question":2}',b'{"question":NaN}',b'\xff',b'{']:
                draft.write_bytes(raw)
                result=run_cli('protocol_scaffold.py','check',draft,'--protocol-output',out,cwd=td)
                self.assertEqual(result.returncode,2);self.assertFalse(out.exists());self.assertNotIn(b'Traceback',result.stderr)

    def test_guide_two_block_rehearsal(self):
        blocks=re.findall(r'```sh\n(.*?)```',(ROOT/'docs/PROTOCOL_SCAFFOLD.md').read_text(),re.S)
        self.assertEqual(len(blocks),2)
        with tempfile.TemporaryDirectory(prefix='sensei starting protocol ') as td:
            for index,block in enumerate(blocks):
                for line in block.strip().splitlines():
                    args=shlex.split(line);self.assertEqual(args.pop(0),'python')
                    args=[a.replace('/outside',td) for a in args]
                    result=subprocess.run([sys.executable,*args],cwd=ROOT,capture_output=True)
                    self.assertEqual(result.returncode,0,result.stderr)
                if index==0:
                    draft=Path(td)/'starting-draft.json'
                    self.assertFalse(scaffold.check(json.loads(draft.read_bytes()))['valid'])
                    draft.write_text(json.dumps(supplied()),encoding='utf-8')
            base=json.loads((Path(td)/'starting-base.json').read_bytes())
            self.assertEqual(base,supplied())
            mock=json.loads(result.stdout)
            self.assertIsNone(mock['search_responses'][0]['request']['searched_at'])
            self.assertEqual(mock['extraction_candidates'],[])
