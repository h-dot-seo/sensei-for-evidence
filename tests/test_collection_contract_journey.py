"""Observed effects across supplied collection intake, separate review and archive replay."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import command_contract
from evidence_workflow import run

ROOT = Path(__file__).resolve().parents[1]
NEW = { (name+'.py', sub) for name in ('bibliographic_intake', 'ris_intake', 'nbib_batch_intake') for sub in ('preview','verify') }
NEW |= {(name+'.py',sub) for name in ('collection_bundle','native_collection_bundle','batch_collection_bundle') for sub in ('create','verify')}
EXISTING = {('nbib_intake.py',sub) for sub in ('preview','verify')} | {('bibliographic_review.py',sub) for sub in ('template','target','assemble')}


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode('utf-8')


class CollectionContractJourneyTests(unittest.TestCase):
    def invoke(self, script, *args):
        return subprocess.run([sys.executable, '-B', str(ROOT/script), *map(str,args)],
            cwd=self.root, capture_output=True, timeout=30,
            env=dict(os.environ, PYTHONIOENCODING='ascii', PYTHONUTF8='0'))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='supplied collection 계약 ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.rows = {(r['script'],r['subcommand']):r for r in command_contract.contract()['commands']}
        self.seen = set()

    def write(self,name,value):
        path=self.root/name
        path.write_bytes(value if isinstance(value,bytes) else encoded(value))
        return path

    def error(self,script,args,code=1):
        before={p.name:p.read_bytes() for p in self.root.iterdir() if p.is_file()}
        result=self.invoke(script,*args)
        self.assertEqual((result.returncode,result.stdout),(code,b''),result.stderr)
        self.assertTrue(result.stderr)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.root.iterdir() if p.is_file()})
        return result

    def success(self,script,args,outputs=()):
        """Observe raw process channels, logical files, text output and repeat-write refusal."""
        key=(script,args[0]);row=self.rows[key];self.seen.add(key)
        self.assertEqual(row['effects']['success'],{'exit_code':0,'stdout':'json_or_text'})
        self.assertIsNone(row['effects']['negative_report'])
        before={p.name:p.read_bytes() for p in self.root.iterdir() if p.is_file()}
        result=self.invoke(script,*args)
        self.assertEqual((result.returncode,result.stderr),(0,b''),result.stderr)
        parsed=json.loads(result.stdout)
        after={p.name:p.read_bytes() for p in self.root.iterdir() if p.is_file()}
        self.assertEqual(set(after)-set(before),{Path(p).name for p in outputs})
        for name,raw in before.items():self.assertEqual(after[name],raw)
        textargs=list(args)
        textoutputs=[]
        for path in outputs:
            new=Path(str(path)+'.text-mode')
            textargs=[new if str(a)==str(path) else a for a in textargs]
            textoutputs.append(new)
        text=self.invoke(script,*textargs,'--text')
        self.assertEqual((text.returncode,text.stderr),(0,b''),text.stderr)
        self.assertTrue(text.stdout)
        for source,dest in zip(outputs,textoutputs):self.assertEqual(Path(source).read_bytes(),dest.read_bytes())
        if outputs:self.error(script,args)
        return parsed

    def test_complete_supplied_csv_ris_nbib_batch_and_archive_effects(self):
        base=json.loads((ROOT/'examples/bibliographic-base.json').read_bytes())
        protocol=self.write('base.json',base)
        for kind in ('csv','ris','nbib','nbib_batch'):
            with self.subTest(kind=kind):
                script={'csv':'bibliographic_intake.py'}.get(kind,kind+'_intake.py')
                native={'csv':b'record_id,source_locator,title\r\nfictional,local:synthetic,fixture\r\n',
                        'ris':'TY  - JOUR\r\nTI  - 합성\r\nER  -\r\n'.encode(),
                        'nbib':'PMID- 999999999999991\nTI  - 합성\n'.encode(),
                        'nbib_batch':b'PMID- 999999999999992\nTI  - Fictional batch\n'}[kind]
                source=self.write(kind+'.source',native)
                source_args=['--export','first='+str(source),'--export','second='+str(source)] if kind=='nbib_batch' else [source]
                wrapper=self.root/(kind+'-wrapper.json')
                args=['preview',protocol,*source_args,'--search-id','local-primary','--searched-at','synthetic supplied time','--output',wrapper]
                artifact=self.success(script,args,[wrapper])
                self.success(script,['verify',wrapper])
                broken=copy.deepcopy(artifact);broken['review_target']['target_sha256']='0'*64
                bad=self.write(kind+'-tampered.json',broken)
                self.error(script,['verify',bad])
                intake=wrapper
                if kind!='csv':
                    intake=self.root/(kind+'-csv-intake.json')
                    self.success(script,['verify',wrapper,'--intake-output',intake],[intake])
                    csv=self.root/(kind+'-export.csv')
                    self.success(script,['verify',wrapper,'--csv-output',csv],[csv])
                    self.assertEqual(csv.read_bytes(),artifact['csv_intake']['source_export']['text'].encode('utf-8'))
                    self.assertEqual(json.loads(intake.read_bytes()),artifact['csv_intake'])
                    self.error(script,['verify',wrapper,'--intake-output',self.root/'never.json','--csv-output',self.root/'never.csv'],2)
                reviewscript='bibliographic_review.py'
                blank=self.root/(kind+'-blank.json')
                choices=self.success(reviewscript,['template',intake,'--review-output',blank],[blank])
                for index,row in enumerate(choices['resolutions']):
                    row.update(disposition='new_record',record_id='fictional-'+str(index),rationale='Synthetic test identity, not real review')
                choicespath=self.write(kind+'-choices.json',choices)
                target=self.root/(kind+'-target.json')
                self.success(reviewscript,['target',protocol,intake,choicespath,'--review-output',target],[target])
                self.error(reviewscript,['assemble',protocol,intake,target])
                supplied=json.loads(target.read_bytes())
                supplied['review'].update(reviewer='Fictional test reviewer',reviewed_at='2026-11-15',rationale='Synthetic software test only',decision='import_for_screening')
                approved=self.write(kind+'-supplied-review.json',supplied)
                imported=self.root/(kind+'-imported.json')
                assembled=self.success(reviewscript,['assemble',protocol,intake,approved,'--protocol-output',imported],[imported])
                self.assertEqual(json.loads(imported.read_bytes()),assembled['protocol_candidate'])
                before_run=run(json.loads(imported.read_bytes()))
                if kind!='csv':
                    archives=[('native_collection_bundle.py','--'+kind.replace('_','-'))]
                    if kind=='nbib':archives.append(('collection_bundle.py','--nbib'))
                    if kind=='nbib_batch':archives.append(('batch_collection_bundle.py','--batch'))
                    for archive_script,flag in archives:
                        zip_path=self.root/(kind+'-'+archive_script+'.zip')
                        self.success(archive_script,['create',imported,zip_path,flag,'0='+str(wrapper)],[zip_path])
                        self.success(archive_script,['verify',zip_path])
                        corrupted=self.write(zip_path.name+'.bad',zip_path.read_bytes()+b'not canonical')
                        self.error(archive_script,['verify',corrupted])
                        self.error(archive_script,['create',imported,self.root/'never.zip',flag,'missing-separator'])
                self.assertEqual(run(json.loads(imported.read_bytes())),before_run)
                self.assertEqual(source.read_bytes(),native)
        self.assertEqual(self.seen,NEW|EXISTING)
        self.assertEqual(json.loads(protocol.read_bytes()),base)

    def test_exact_new_inventory_and_source_unchanged_proof(self):
        proof=json.loads((ROOT/'tests/collection_contract_prior_bytes.json').read_bytes())
        from tests._json_depth_compat import prior_bytes, prior_fixture_bytes
        for rel,digest in proof.items():
            source=prior_fixture_bytes(rel) if rel.startswith('examples/') else prior_bytes(rel)
            self.assertEqual(hashlib.sha256(source).hexdigest(),digest,rel)
        self.assertEqual(set(proof),{p.relative_to(ROOT).as_posix() for p in ROOT.glob('*.py') if p.name not in ('cli_errors.py','retained_bundle_describe.py','amendment_links.py','amendment_intake.py','pubmed_partition.py','pubmed_partition_compare.py')}|{p.relative_to(ROOT).as_posix() for p in (ROOT/'examples').rglob('*') if p.is_file() and p.name not in ('amendment-before.json','amendment-after.json','manual-amendment.json')})
        prior=json.loads((ROOT/'tests/collection_contract_prior_registry.json').read_bytes())
        old={(r['script'],r['subcommand']):r for r in prior['commands']}
        current=command_contract.contract()
        observed=dict(current['implementation_sha256'])
        for name in ('amendment_links.py','amendment_intake.py','pubmed_partition.py','pubmed_partition_compare.py'):
            self.assertEqual(observed.pop(name),hashlib.sha256((ROOT/name).read_bytes()).hexdigest())
        self.assertEqual(observed.pop('retained_bundle_describe.py'),hashlib.sha256((ROOT/'retained_bundle_describe.py').read_bytes()).hexdigest())
        self.assertEqual(observed.pop('cli_errors.py'),hashlib.sha256((ROOT/'cli_errors.py').read_bytes()).hexdigest())
        changed=set(json.loads((ROOT/'tests/native_continuation_source_changes.json').read_bytes()))
        changed.update(json.loads((ROOT/'tests/amendment_source_changes.json').read_bytes()))
        changed.update(json.loads((ROOT/'tests/shared_analysis_source_changes.json').read_bytes()))
        changed.update(json.loads((ROOT/'tests/cli_error_source_changes.json').read_bytes()))
        changed.update(json.loads((ROOT/'tests/json_depth_source_changes.json').read_bytes()))
        changed.update(json.loads((ROOT/'tests/archive_preflight_source_changes.json').read_bytes()))
        changed.add('sensei.py')
        for name in changed:
            self.assertEqual(observed[name],hashlib.sha256((ROOT/name).read_bytes()).hexdigest())
            observed[name]=hashlib.sha256(prior_bytes(name)).hexdigest()
        self.assertEqual(observed,prior['implementation_sha256'])
        changed=set()
        for key,row in self.rows.items():
            if key==('retained_bundle_describe.py',None) or key[0] in ('amendment_intake.py','pubmed_partition.py','pubmed_partition_compare.py'):
                self.assertIsNone(row['effects']);continue
            original=old[key]
            if key == ('sensei.py', 'list'):
                self.assertEqual(row['usage'], original['usage'] + ' [--search TEXT]')
                self.assertEqual(row['purpose'],
                                 'List root script names and first docstring sentences, plus handoff route IDs, '
                                 'titles, scripts and guide paths. Search matches entries containing every term, '
                                 'ignoring case. Listing reads only the checkout and executes no listed command.')
                row = dict(row, usage=original['usage'], purpose=original['purpose'])
            if key==('native_collection_bundle.py','create'):
                self.assertEqual(row['usage'],original['usage'].replace('[--nbib-batch INDEX=PATH]','[--nbib-batch INDEX=PATH] [--ris-continuation INDEX=PATH]'))
                self.assertIn('--ris-continuation',row['effects']['inputs'])
                row=dict(row,usage=original['usage'])
            if key==('compare_runs.py',None):
                self.assertEqual(row['usage'], original['usage'].replace('[--amendment AMENDMENT]', '[--amendment AMENDMENT] [--amendment-id AMENDMENT_ID]'))
                row=dict(row,usage=original['usage'])
            self.assertEqual({k:row[k] for k in original if k!='effects'},{k:v for k,v in original.items() if k!='effects'})
            if row['effects']!=original['effects']:
                changed.add(key);self.assertIsNone(original['effects'])
        self.assertEqual(changed,NEW)
        self.assertEqual((current['coverage']['commands'],current['coverage']['reviewed_effects']),(209,44))
        self.assertEqual(sum(r['effects'] is None for r in current['commands']),165)

    def test_all_seventeen_handled_missing_inputs_and_usage_channels(self):
        for script,sub in sorted(NEW|EXISTING):
            with self.subTest(script=script,sub=sub):
                self.error(script,[],2)
                missing=self.root/'missing'
                if sub=='preview':
                    args=[sub,missing]
                    args+=['--export','synthetic='+str(missing)] if script=='nbib_batch_intake.py' else [missing]
                    args+=['--search-id','local-primary','--searched-at','synthetic']
                elif sub=='create':
                    flag={'collection_bundle.py':'--nbib','native_collection_bundle.py':'--ris','batch_collection_bundle.py':'--batch'}[script]
                    args=[sub,missing,self.root/'never.zip',flag,'0='+str(missing)]
                elif sub in ('target','assemble'):args=[sub,missing,missing,missing]
                else:args=[sub,missing]
                self.error(script,args)
                self.assertEqual(self.rows[(script,sub)]['effects']['caught_error']['stdout'],'empty')
                self.assertEqual(self.rows[(script,sub)]['effects']['network'],'none')


if __name__=='__main__':unittest.main()
