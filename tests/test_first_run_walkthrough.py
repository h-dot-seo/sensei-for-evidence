"""Execute the first-run documentation itself, with synthetic local outputs only."""
import copy
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from evidence_workflow import run
from offline_adapter import assemble
from compare_runs import compare_protocols
from prisma_audit import export_audit
ROOT=Path(__file__).resolve().parents[1]

def load(name):return json.loads((ROOT/'examples'/name).read_text(encoding='utf-8'))

class FirstRunWalkthroughTests(unittest.TestCase):
    def test_documented_commands_execute_in_order_with_space_in_output_path(self):
        doc=(ROOT/'docs/FIRST_RUN.md').read_text(encoding='utf-8')
        lines=[line for block in re.findall(r'```sh\n(.*?)```',doc,re.S) for line in block.splitlines() if line.strip()]
        self.assertEqual(len(lines),11)
        allowed={'receipt_intake.py','offline_adapter.py','prisma_audit.py','compare_runs.py','work_review.py','research_bundle.py'}
        with tempfile.TemporaryDirectory(prefix='sensei first run ') as folder:
            outputs=[]
            for line in lines:
                tokens=shlex.split(line);self.assertEqual(tokens[0],'python');self.assertIn(tokens[1],allowed)
                cmd=[sys.executable]+[token.replace('OUTPUT',folder) for token in tokens[1:]]
                result=subprocess.run(cmd,cwd=ROOT,capture_output=True,encoding='utf-8',check=False)
                self.assertEqual(result.returncode,0,(line,result.stderr));outputs.append(result.stdout)
            unreviewed=json.loads((Path(folder)/'unreviewed.json').read_text())
            reviewed=json.loads((Path(folder)/'reviewed.json').read_text())
            self.assertEqual(unreviewed['evidence'],[]);self.assertEqual(unreviewed['adapter_receipts']['reviews'],[])
            self.assertFalse(unreviewed['searches'][0]['complete']);self.assertEqual(len(reviewed['evidence']),2)
            last=json.loads(outputs[-1]);self.assertTrue(last['valid']);self.assertEqual(last['conclusion_readiness'],'NOT_READY')
            self.assertEqual(last['census_claim'],'NOT_ESTABLISHED')
            archive=Path(folder)/'first-run.zip';original_archive=archive.read_bytes()
            repeated=subprocess.run([sys.executable,'research_bundle.py','create','examples/first-run-note-complete.json',str(archive)],cwd=ROOT,capture_output=True)
            self.assertNotEqual(repeated.returncode,0);self.assertEqual(archive.read_bytes(),original_archive)
            target=Path(folder)/'reviewed.json';before=target.read_bytes()
            cmd=[sys.executable,'offline_adapter.py','examples/adapter-protocol.json','examples/adapter-fixture.json','--reviews','examples/adapter-reviews.json','--protocol-output',str(target)]
            again=subprocess.run(cmd,cwd=ROOT,capture_output=True);self.assertNotEqual(again.returncode,0);self.assertEqual(target.read_bytes(),before)
    def test_enrichment_only_adds_explicit_supplied_fields(self):
        reviewed=assemble(load('adapter-protocol.json'),load('adapter-fixture.json'),load('adapter-reviews.json'))['protocol']
        enriched=load('first-run-enriched.json');comparison=compare_protocols(reviewed,enriched)
        self.assertEqual(set(comparison['changed_protocol_fields']),{'version','contexts','appraisals','experimental_units','gaps'})
        for field in ('searches','screening','reports','evidence','adapter_receipts'):
            self.assertEqual(reviewed[field],enriched[field])
        nodes={n['node_id']:n['count'] for n in export_audit(enriched)['nodes']}
        self.assertEqual(nodes['unique_records'],2);self.assertEqual(nodes['extracted_result_rows'],2)
        self.assertEqual(nodes['included_studies'],1);self.assertEqual(nodes['reports_included'],1)
    def test_completion_changes_only_note_assertions_and_dependency_block(self):
        a=load('first-run-enriched.json');b=load('first-run-note-complete.json')
        self.assertEqual(set(compare_protocols(a,b)['changed_protocol_fields']),{'version','gaps'})
        clean=copy.deepcopy(b);clean['version']=a['version'];clean['gaps'][0]=copy.deepcopy(a['gaps'][0]);self.assertEqual(clean,a)
        before=run(a);after=run(b)
        self.assertEqual(before['work_packages'][1]['blocked_by'],['WP-RECEIPT-REVIEW'])
        self.assertEqual(after['work_packages'][1]['blocked_by'],[])
        self.assertTrue(after['work_packages'][2]['blocked_by']);self.assertTrue(after['work_packages'][3]['blocked_by'])
        self.assertEqual(after['search_plan_audit']['missing_search_ids'],['search-secondary'])
        self.assertEqual(after['evidence'],before['evidence']);self.assertEqual(after['conclusion_readiness'],'NOT_READY')
        self.assertEqual(export_audit(a)['nodes'],export_audit(b)['nodes'])
    def test_completion_guard_remains_required(self):
        b=load('first-run-note-complete.json')
        for field in ('artifact_locator','acceptance_verified'):
            p=copy.deepcopy(b);p['gaps'][0].pop(field)
            with self.assertRaises(ValueError):run(p)
        b['gaps'][0]['acceptance_verified']=1
        with self.assertRaises(ValueError):run(b)
    def test_document_local_links_resolve(self):
        doc=ROOT/'docs/FIRST_RUN.md'
        for link in re.findall(r'\]\(([^)]+)\)',doc.read_text(encoding='utf-8')):
            self.assertTrue((doc.parent/link.split('#')[0]).is_file())

if __name__=='__main__':unittest.main()
