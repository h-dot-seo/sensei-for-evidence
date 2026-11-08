"""Synthetic RIS byte provenance, explicit reconciliation and hostile-input tests."""
import copy
import csv
import hashlib
import io
import json
import os
import random
import re
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import bibliographic_review
from evidence_workflow import run
from json_io import canonical_json_bytes
from prisma_audit import export_audit
import research_bundle
import ris_export_parser as parser
import ris_intake as intake

ROOT = Path(__file__).resolve().parents[1]


def fixture(name):
    return json.loads((ROOT/'examples'/name).read_bytes())


class RisParserTests(unittest.TestCase):
    def test_four_occurrences_and_repeated_identifiers_remain_ordered(self):
        parsed=parser.parse_export((ROOT/'examples/ris-export.ris').read_bytes())
        self.assertEqual(len(parsed['records']),4)
        self.assertEqual([r['candidate_id'] for r in parsed['records']],
                         [f'ris-record-{i:06d}' for i in range(1,5)])
        self.assertEqual([f['value_lines'] for f in parsed['records'][1]['fields'] if f['tag']=='DO'],
                         [['10.0000/fictional-shared'],['10.0000/fictional-conflicting']])
        self.assertFalse(any(f['tag'] in ('ID','DO','UR','AN') for f in parsed['records'][2]['fields']))
        self.assertNotIn('record_id',parsed['records'][0])
        self.assertNotIn('duplicates',parsed)

    def test_exact_bom_unicode_mixed_line_and_field_spans_cover_all_bytes(self):
        raw='\ufeff\r\nTY  - JOUR\rTI  - 합성 α\n      folded\r\nAU  - A\rAU  - B\nER  - \r\n\nTY  - XTYPE\nZ9  - literal\nER  -'.encode()
        parsed=parser.parse_export(raw)
        self.assertTrue(parsed['initial_utf8_bom'])
        spans=parsed['ignored_blank_spans']+[r['source_span'] for r in parsed['records']]
        cursor=0
        for span in sorted(spans,key=lambda s:s['byte_start']):
            self.assertEqual(span['byte_start'],cursor)
            actual=raw[span['byte_start']:span['byte_end']]
            self.assertEqual(hashlib.sha256(actual).hexdigest(),span['sha256'])
            cursor=span['byte_end']
        self.assertEqual(cursor,len(raw))
        for record in parsed['records']:
            span=record['source_span']
            self.assertEqual(record['raw_text'].encode(),raw[span['byte_start']:span['byte_end']])
            self.assertEqual(''.join(f['raw_text'] for f in record['fields']),record['raw_text'])
            for field in record['fields']:
                span=field['source_span'];actual=raw[span['byte_start']:span['byte_end']]
                self.assertEqual(field['raw_text'].encode(),actual)
                self.assertEqual(hashlib.sha256(actual).hexdigest(),span['sha256'])
        self.assertEqual(parsed['records'][0]['fields'][1]['value_lines'],['합성 α','folded'])
        self.assertEqual(parsed['records'][1]['record_type'],'XTYPE')

    def test_adjacent_records_and_both_empty_er_spellings(self):
        for ending in ('ER  -','ER  - '):
            raw=('TY  - JOUR\n'+ending+'\nTY  - GEN\n'+ending).encode()
            result=parser.parse_export(raw)
            self.assertEqual(len(result['records']),2)
            self.assertEqual(result['ignored_blank_spans'],[])
            self.assertEqual(result['records'][1]['fields'][-1]['value_lines'],[''])

    def test_unknown_empty_and_literal_fields_are_not_normalized(self):
        raw=b'TY  - GEN\nZ9  -  literal  \nKW  -\nKW  - repeated\nER  -\n'
        fields=parser.parse_export(raw)['records'][0]['fields']
        self.assertEqual([r['tag'] for r in fields],['TY','Z9','KW','KW','ER'])
        self.assertEqual(fields[1]['value_lines'],[' literal  '])
        self.assertEqual(fields[2]['value_lines'],[''])

    def test_only_cr_lf_and_crlf_are_physical_line_boundaries(self):
        raw='TY  - JOUR\nTI  - one\u2028two\u0085three\nER  -'.encode()
        result=parser.parse_export(raw)
        self.assertEqual(result['physical_lines'],3)
        self.assertEqual(result['records'][0]['fields'][1]['value_lines'],['one\u2028two\u0085three'])

    def test_malformed_or_unsupported_structure_fails_closed(self):
        cases=[b'',b'\n',b'\xef\xbb\xbf',b'ER  -',b'TI  - private',b'TY  -',b'TY  - jour\nER  -',
               b'TY  - JOUR \nER  -',b'TY  - JOUR\n',b'TY  - JOUR\nTY  - BOOK\nER  -',
               b'TY  - JOUR\nER  - value',b'TY  - JOUR\nER  -  ',b'TY  - JOUR\n\nER  -',
               b'TY - JOUR\nER -',b'TY  - JOUR\nau  - A\nER  -',b'TY  - JOUR\nXYZ - A\nER  -',
               b'TY  - JOUR\nTI  - A\nunindented continuation\nER  -',
               b'TY  - JOUR\nTI  - A\n\tcontinuation\nER  -',
               b'TY  - JOUR\n      continuation\nER  -',b'      orphan\nTY  - JOUR\nER  -',
               b'TY  - JOUR\nER  -\n      orphan',b'TY  - JOUR\nER  -\nER  -',
               b'TY  - JOUR\nER  -\nTI  - stray',b'TY  - JOUR\n\xef\xbb\xbfTI  - middle BOM\nER  -']
        for raw in cases:
            with self.subTest(raw=raw),self.assertRaisesRegex(ValueError,'line '):parser.parse_export(raw)

    def test_nul_utf8_and_invalid_types_do_not_echo_source_text(self):
        for raw in (b'TY  - JOUR\nTI  - PRIVATESECRET\x00\nER  -',b'TY  - JOUR\nTI  - PRIVATESECRET\xff\nER  -'):
            with self.assertRaises(ValueError) as caught:parser.parse_export(raw)
            self.assertNotIn('PRIVATESECRET',str(caught.exception))
        class Bytes(bytes):pass
        for raw in (None,'TY  - JOUR',bytearray(b'TY  - JOUR\nER  -'),Bytes(b'TY  - JOUR\nER  -')):
            with self.subTest(kind=type(raw)),self.assertRaises(ValueError):parser.parse_export(raw)

    def test_inclusive_byte_line_and_record_limits(self):
        raw=b'TY  - GEN\nER  -\n'
        with patch.object(parser,'MAX_EXPORT_BYTES',len(raw)):
            self.assertEqual(len(parser.parse_export(raw)['records']),1)
            with self.assertRaises(ValueError):parser.parse_export(raw+b'\n')
        for raw in (b'TY  - GEN\nER  -',b'TY  - GEN\nER  -\n'):
            with patch.object(parser,'MAX_PHYSICAL_LINES',2):
                self.assertEqual(parser.parse_export(raw)['physical_lines'],2)
                with self.assertRaises(ValueError):parser.parse_export(raw+b'\n\n')
        with patch.object(parser,'MAX_RECORDS',2):
            self.assertEqual(len(parser.parse_export(raw+b'\n'+raw)['records']),2)
            with self.assertRaises(ValueError):parser.parse_export((raw+b'\n')*3)

    def test_seeded_supported_exports_reconstruct_every_original_byte(self):
        rng=random.Random(271)
        for sample in range(40):
            parts=['\ufeff'] if sample%2 else []
            def line(value):parts.extend([value,rng.choice(['\n','\r','\r\n'])])
            for _ in range(rng.randrange(1,5)):
                if rng.randrange(2):line('')
                line('TY  - '+rng.choice(['JOUR','RPRT','XTYPE']))
                for _ in range(rng.randrange(1,8)):
                    line(rng.choice(['TI','AU','Z9','DO'])+'  - '+rng.choice(['literal','합성 α',' value  ','=not executed','']))
                    if rng.randrange(3)==0:line('      '+rng.choice(['continuation','ER  -','  retained  ']))
                line(rng.choice(['ER  -','ER  - ']))
            raw=''.join(parts).encode()
            parsed=parser.parse_export(raw)
            spans=[r['source_span'] for r in parsed['records']]+parsed['ignored_blank_spans']
            self.assertEqual(b''.join(raw[s['byte_start']:s['byte_end']] for s in sorted(spans,key=lambda s:s['byte_start'])),raw)
            self.assertEqual(sum(s['byte_end']-s['byte_start'] for s in spans),len(raw))
            for record in parsed['records']:
                self.assertEqual(''.join(f['raw_text'] for f in record['fields']),record['raw_text'])

    def test_indented_tag_text_is_retained_not_interpreted_as_a_record_boundary(self):
        raw=b'TY  - JOUR\nN1  - note\n      TY  - BOOK\n      ER  -\nER  -'
        result=parser.parse_export(raw)
        self.assertEqual(len(result['records']),1)
        self.assertEqual(result['records'][0]['fields'][1]['value_lines'],['note','TY  - BOOK','ER  -'])


class RisIntakeTests(unittest.TestCase):
    def setUp(self):
        self.base=fixture('bibliographic-base.json')
        self.raw=(ROOT/'examples/ris-export.ris').read_bytes()
        self.choices=fixture('ris-resolutions.json')

    def prepare(self,raw=None,base=None,search='local-primary',time='fictional supplied time'):
        return intake.prepare(self.base if base is None else base,self.raw if raw is None else raw,search,time)

    def reviewed(self,artifact,current=None):
        document=bibliographic_review.prepare_review(self.base if current is None else current,
                                                    artifact['csv_intake'],self.choices)['review_document']
        document['review'].update(reviewer='Fictional RIS reviewer',reviewed_at='2026-11-04',
                                 rationale='Synthetic explicit collection review only.',decision='import_for_screening')
        return document

    def cli(self,*args,cwd=ROOT,env=None):
        return subprocess.run([sys.executable,str(ROOT/'ris_intake.py'),*map(str,args)],
                              cwd=cwd,capture_output=True,env=env,timeout=30)

    def test_deterministic_replay_no_mutation_and_closed_claims(self):
        before=copy.deepcopy(self.base);artifact=self.prepare();again=self.prepare()
        self.assertEqual(artifact,again);self.assertEqual(self.base,before)
        self.assertTrue(intake.verify(artifact)['valid'])
        self.assertEqual(artifact['source_export']['text'].encode(),self.raw)
        self.assertEqual(artifact['review_status'],'NOT_PERFORMED')
        self.assertEqual(artifact['census_claim'],'NOT_ESTABLISHED')
        self.assertEqual(artifact['conclusion_readiness'],'NOT_READY')
        self.assertFalse(artifact['effects']['protocol_changed'])
        artifact['protocol_snapshot']['question']='changed'
        self.assertEqual(self.base,before);self.assertEqual(self.prepare(),again)

    def test_occurrence_ids_locators_do_not_resolve_doi_id_or_url(self):
        artifact=self.prepare();rows=artifact['csv_intake']['parsed_export']['record_rows']
        digest=hashlib.sha256(self.raw).hexdigest()
        self.assertEqual(len({r['record_id'] for r in rows}),4)
        for i,row in enumerate(rows,1):
            cid=f'ris-record-{i:06d}'
            self.assertEqual(row['record_id'],f'ris-occurrence:{digest}:{cid}')
            self.assertEqual(row['source_locator'],f'supplied-ris-sha256:{digest}#{cid}')
            self.assertEqual(row['original_values']['ris_occurrence_id'],cid)
            self.assertEqual(json.loads(row['original_values']['ris_fields_json']),artifact['parsed_export']['records'][i-1]['fields'])
            self.assertEqual(json.loads(row['original_values']['ris_record_span_json']),artifact['parsed_export']['records'][i-1]['source_span'])
        self.assertEqual(artifact['csv_intake']['parsed_export']['duplicate_record_ids'],[])
        self.assertEqual(artifact['derivation']['identity_status'],'FILE_OCCURRENCE_ONLY_NOT_PUBLICATION_IDENTITY')

    def test_file_edits_change_occurrence_labels_not_publication_identity(self):
        left=self.prepare();right=self.prepare(self.raw+b'\n')
        self.assertEqual(len(left['parsed_export']['records']),len(right['parsed_export']['records']))
        self.assertNotEqual(left['csv_intake']['parsed_export']['record_rows'][0]['record_id'],
                            right['csv_intake']['parsed_export']['record_rows'][0]['record_id'])
        self.assertNotEqual(left['review_target'],right['review_target'])

    def test_explicit_review_preserves_raw_rows_and_only_appends_incomplete_search(self):
        artifact=self.prepare()
        blank=bibliographic_review.template(artifact['csv_intake'])
        self.assertIsNone(blank['review']);self.assertTrue(all(r['disposition'] is None for r in blank['resolutions']))
        pending=bibliographic_review.prepare_review(self.base,artifact['csv_intake'],self.choices)['review_document']
        with self.assertRaises(ValueError):bibliographic_review.assemble(self.base,artifact['csv_intake'],pending)
        protocol=bibliographic_review.assemble(self.base,artifact['csv_intake'],self.reviewed(artifact))['protocol_candidate']
        self.assertEqual(protocol['searches'][0]['record_ids'],['fictional-ris-A','fictional-ris-B'])
        self.assertIs(protocol['searches'][0]['complete'],False);self.assertIsNone(protocol['searches'][0]['total_count'])
        self.assertEqual(protocol['screening'],[]);self.assertEqual(protocol['evidence'],[])
        audit=export_audit(protocol)
        self.assertEqual(audit['bibliographic_collection']['counts'],dict(raw_rows=4,promoted_row_occurrences=3,withheld_rows=1,canonical_search_memberships=2))
        self.assertEqual(run(protocol)['flow']['identified'],2)
        self.assertEqual(protocol['bibliographic_imports']['imports'][0]['intake']['source_export'],artifact['csv_intake']['source_export'])
        raw=research_bundle.build_bundle(json.dumps(protocol).encode())
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'research.zip';path.write_bytes(raw)
            self.assertTrue(research_bundle.verify(path)['valid'])
        with zipfile.ZipFile(io.BytesIO(raw)) as z:self.assertNotIn('ris-wrapper.json',z.namelist())

    def test_second_planned_ris_import_preserves_prior_screening(self):
        first=self.prepare();p=bibliographic_review.assemble(self.base,first['csv_intake'],self.reviewed(first))['protocol_candidate']
        p['screening']=[dict(record_id='fictional-ris-A',decision='include',reason='Fictional supplied choice.')]
        second=self.prepare(b'TY  - RPRT\nTI  - Fictional later source\nER  -',search='local-secondary')
        choices=bibliographic_review.template(second['csv_intake'])
        choices['resolutions'][0].update(disposition='same_record',record_id='fictional-ris-A',rationale='Explicit fictional association.')
        review=bibliographic_review.prepare_review(p,second['csv_intake'],choices)['review_document']
        review['review'].update(reviewer='Fictional',reviewed_at='2026-11-04',rationale='Synthetic only.',decision='import_for_screening')
        next_p=bibliographic_review.assemble(p,second['csv_intake'],review)['protocol_candidate']
        self.assertEqual(next_p['screening'],p['screening']);self.assertEqual(next_p['searches'][:-1],p['searches'])
        self.assertEqual(len(next_p['bibliographic_imports']['imports']),2)
        self.assertTrue(intake.verify(second)['valid'])

    def test_no_network_or_declared_attachment_access(self):
        with patch.object(socket,'create_connection',side_effect=AssertionError('No network')), \
             patch('urllib.request.urlopen',side_effect=AssertionError('No URL access')):
            artifact=self.prepare();self.assertTrue(intake.verify(artifact)['valid'])
        self.assertIn('/unopened/fictional-attachment.pdf',artifact['source_export']['text'])
        self.assertEqual(artifact['external_calls'],0)

    def test_whole_protocol_and_explicit_search_metadata_are_validated(self):
        for base in (None,[],{},dict(self.base,screening=[dict(record_id='missing',decision='include',reason='fictional')])):
            with self.subTest(base=base),self.assertRaises((ValueError,KeyError,TypeError)):
                intake.prepare(base,self.raw,'local-primary','time')
        for search,time in (('missing','time'),('','time'),('local-primary',''),(True,'time'),('local-primary',4)):
            with self.subTest(search=search,time=time),self.assertRaises(ValueError):intake.prepare(self.base,self.raw,search,time)

    def test_full_wrapper_tampering_rejected_even_with_resealed_outer_target(self):
        original=self.prepare()
        cases=[lambda a:a['source_export'].update(bytes=True),lambda a:a['source_export'].update(sha256='0'*64),
               lambda a:a['parsed_export']['records'][0].update(record_type='BOOK'),
               lambda a:a['parsed_export']['records'].reverse(),lambda a:a['parsed_export']['records'][0]['fields'].reverse(),
               lambda a:a['csv_intake']['parsed_export']['record_rows'][0].update(record_id='forged'),
               lambda a:a['derivation'].update(identity_status='VERIFIED'),lambda a:a['effects'].update(protocol_changed=True),
               lambda a:a.update(extra='unknown'),lambda a:a.update(schema_version=True),
               lambda a:a['search_request'].update(searched_at='different time'),
               lambda a:a['source_export'].update(text=a['source_export']['text']+'\n')]
        for change in cases:
            a=copy.deepcopy(original);change(a)
            if a.get('review_target'):
                a['review_target']['target_sha256']=intake.digest({k:v for k,v in a.items() if k!='review_target'})
            with self.subTest(change=change),self.assertRaises((ValueError,TypeError,KeyError)):intake.verify(a)

    def test_unknown_fields_literal_types_and_engine_drift_are_bound(self):
        artifact=self.prepare()
        for change in (lambda a:a['source_export'].update(extra='x'),lambda a:a['effects'].update(new_searches=False),
                       lambda a:a['engine_sha256'].update(**{'ris_export_parser.py':'0'*64}),
                       lambda a:a['review_target'].update(scope='approval')):
            a=copy.deepcopy(artifact);change(a)
            with self.assertRaises(ValueError):intake.verify(a)
        self.assertIn('ris_export_parser.py',artifact['engine_sha256']);self.assertIn('ris_intake.py',artifact['engine_sha256'])
        self.assertNotIn('ris_intake.py',research_bundle.ENGINE_FILES)
        self.assertEqual(intake.verify(dict(reversed(list(artifact.items())))),intake.verify(artifact))

    def test_native_formats_are_not_guessed_or_interchanged(self):
        import nbib_intake,nbib_batch_intake
        artifact=self.prepare()
        for verifier in (nbib_intake.verify,nbib_batch_intake.verify):
            with self.assertRaises(ValueError):verifier(artifact)
        raw=(ROOT/'examples/pubmed-export.nbib').read_bytes()
        native=nbib_intake.prepare(self.base,raw,'local-primary','fictional supplied time')
        with self.assertRaises(ValueError):intake.verify(native)
        with self.assertRaises(ValueError):self.prepare(raw)

    def test_strict_json_api_rejects_nonfinite_subclasses_cycles_and_surrogates(self):
        class Dict(dict):pass
        class Int(int):pass
        for value in ({'not-json'},('tuple',),float('nan'),float('inf'),'\ud800',Dict(x=1),Int(1)):
            p=copy.deepcopy(self.base);p['opaque']=value
            with self.subTest(value=repr(value)),self.assertRaises((ValueError,TypeError,UnicodeError)):self.prepare(base=p)
        p=copy.deepcopy(self.base);p['cycle']=p
        with self.assertRaises(ValueError):self.prepare(base=p)
        a=self.prepare();a['cycle']=a
        with self.assertRaises(ValueError):intake.verify(a)

    def test_derivative_csv_and_artifact_bounds_are_not_bypassed(self):
        artifact=self.prepare();n=len(intake.artifact_bytes(artifact))
        with patch.object(intake,'MAX_ARTIFACT_BYTES',n):self.assertEqual(len(intake.artifact_bytes(artifact)),n)
        with patch.object(intake,'MAX_ARTIFACT_BYTES',n-1):
            with self.assertRaises(ValueError):intake.artifact_bytes(artifact)
            with self.assertRaises(ValueError):self.prepare()
        prior=csv.field_size_limit()
        with patch('csv_export_parser.MAX_EXPORT_BYTES',100):
            with self.assertRaises(ValueError):self.prepare()
        self.assertEqual(csv.field_size_limit(),prior)

    def test_original_byte_variants_roundtrip_through_csv_without_loss(self):
        for newline in ('\n','\r','\r\n'):
            raw=('\ufeff'+newline+'TY  - JOUR'+newline+'TI  - "합성", literal'+newline+
                 'AU  - A'+newline+'AU  - B'+newline+'ER  -'+newline+newline).encode()
            a=self.prepare(raw)
            self.assertTrue(intake.verify(a)['valid'])
            self.assertEqual(a['source_export']['text'].encode(),raw)
            row=a['csv_intake']['parsed_export']['record_rows'][0]
            self.assertEqual(row['original_values']['ris_record_text'],a['parsed_export']['records'][0]['raw_text'])

    def test_completely_identical_records_remain_distinct_occurrences(self):
        row=b'TY  - JOUR\nTI  - Fictional repeated\nDO  - 10.0000/fictional\nER  -\n'
        a=self.prepare(row+row)
        self.assertEqual(len(a['parsed_export']['records']),2)
        self.assertEqual(a['parsed_export']['records'][0]['raw_text'],a['parsed_export']['records'][1]['raw_text'])
        ids=[r['record_id'] for r in a['csv_intake']['parsed_export']['record_rows']]
        self.assertNotEqual(ids[0],ids[1])
        self.assertEqual(a['effects']['new_searches'],0)

    def test_prior_review_is_not_refreshed_for_changed_native_bytes(self):
        a=self.prepare();review=self.reviewed(a);changed=self.prepare(self.raw+b'\n')
        with self.assertRaises(ValueError):bibliographic_review.assemble(self.base,changed['csv_intake'],review)
        rebuilt=self.prepare(self.raw.replace(b'Fictional citation',b'Different fictional citation'))
        self.assertTrue(intake.verify(rebuilt)['valid'])
        self.assertEqual(rebuilt['source_authenticity'],'NOT_VERIFIED')
        self.assertEqual(rebuilt['human_authenticity'],'NOT_VERIFIED')

    def test_output_inspection_failures_are_not_bypassed(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'out.json'
            with patch.object(Path,'lstat',side_effect=PermissionError('Synthetic inspection refusal')):
                with self.assertRaises(PermissionError):intake._write_new(path,b'no')
            self.assertFalse(path.exists())

    def test_native_input_can_exceed_existing_csv_field_bound_without_raising_it(self):
        limit=csv.field_size_limit()
        raw=b'TY  - JOUR\nTI  - '+b'x'*(limit+1)+b'\nER  -'
        self.assertEqual(len(parser.parse_export(raw)['records']),1)
        with self.assertRaisesRegex(ValueError,'field-size limit'):self.prepare(raw)
        self.assertEqual(csv.field_size_limit(),limit)

    def test_document_links_and_public_inputs_are_explicit(self):
        path=ROOT/'docs/RIS_INTAKE.md';doc=path.read_text(encoding='utf-8')
        for link in re.findall(r'\]\(([^)]+)\)',doc):
            if not link.startswith('https://'):self.assertTrue((path.parent/link.split('#')[0]).is_file(),link)
        self.assertIn('unindented multiline abstracts are outside this initial subset',doc)
        self.assertIn('NATIVE_COLLECTION_BUNDLES.md',doc)
        self.assertIn('not a complete research-history archive',doc)
        self.assertIn('NBIB** collection archives do not accept RIS wrappers',doc)
        self.assertIn('not universal RIS compatibility',doc)
        self.assertIn('ris_intake.py', (ROOT/'README.md').read_text(encoding='utf-8'))

    def test_text_quotes_controls_and_never_claims_acceptance(self):
        p=copy.deepcopy(self.base);p['search_plan'][0]['query']='fake\nConclusion: READY\x1b\u202e'
        text=intake.render_text(self.prepare(base=p))
        self.assertNotIn('\nConclusion: READY',text);self.assertNotIn('\x1b',text);self.assertNotIn('\u202e',text)
        self.assertIn('Conclusion: NOT_READY',text)
        self.assertIn('file occurrences only',text)
        self.assertIn('not universal RIS compatibility',text)

    def test_cli_roundtrip_utf8_space_paths_and_new_output_only(self):
        with tempfile.TemporaryDirectory(prefix='sensei ris cli ') as td:
            root=Path(td);p=root/'protocol space.json';native=root/'source space.ris';artifact=root/'wrapper.json'
            native_raw=self.raw.replace(b'Fictional citation','Fictional 합성 citation'.encode('utf-8'))
            expected=self.prepare(native_raw)
            p.write_text(json.dumps(self.base),encoding='utf-8');native.write_bytes(native_raw)
            before=(p.read_bytes(),native.read_bytes())
            env=dict(os.environ,PYTHONIOENCODING='ascii',PYTHONUTF8='0')
            args=['preview',p,native,'--search-id','local-primary','--searched-at','fictional supplied time','--output',artifact]
            result=self.cli(*args,cwd=root,env=env);self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout),expected)
            self.assertIn('합성',result.stdout.decode('utf-8'))
            checked=self.cli('verify',artifact,'--text',cwd=root,env=env);self.assertEqual(checked.returncode,0,checked.stderr)
            self.assertIn(b'consistency: true',checked.stdout)
            derivative=root/'derived.csv';nested=root/'intake.json'
            self.assertEqual(self.cli('verify',artifact,'--csv-output',derivative).returncode,0)
            self.assertEqual(self.cli('verify',artifact,'--intake-output',nested).returncode,0)
            self.assertEqual(derivative.read_bytes(),expected['csv_intake']['source_export']['text'].encode())
            self.assertEqual(json.loads(nested.read_bytes()),expected['csv_intake'])
            saved=artifact.read_bytes()
            self.assertNotEqual(self.cli(*args).returncode,0);self.assertEqual(artifact.read_bytes(),saved)
            self.assertNotEqual(self.cli('verify',artifact,'--csv-output',derivative,'--intake-output',nested).returncode,0)
            self.assertEqual((p.read_bytes(),native.read_bytes()),before)
            self.assertNotEqual(self.cli('verify',artifact,'--intake-output',p).returncode,0)
            self.assertEqual(p.read_bytes(),before[0])

    def test_cli_invalid_inputs_fail_before_output_and_do_not_echo_raw_content(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);p=root/'p.json';native=root/'bad.ris';out=root/'out.json'
            p.write_text(json.dumps(self.base));native.write_bytes(b'TY  - JOUR\nPRIVATESECRET unsupported\nER  -')
            result=self.cli('preview',p,native,'--search-id','local-primary','--searched-at','fictional','--output',out)
            self.assertNotEqual(result.returncode,0);self.assertEqual(result.stdout,b'');self.assertFalse(out.exists())
            self.assertNotIn(b'PRIVATESECRET',result.stderr);self.assertNotIn(b'Traceback',result.stderr)
            bad=self.prepare();bad['parsed_export']['records'][0]['record_type']='forged'
            artifact=root/'tampered.json';artifact.write_text(json.dumps(bad),encoding='utf-8')
            result=self.cli('verify',artifact,'--intake-output',out)
            self.assertNotEqual(result.returncode,0);self.assertEqual(result.stdout,b'');self.assertFalse(out.exists())
            p.write_text('{"question":1,"question":2}')
            result=self.cli('preview',p,ROOT/'examples/ris-export.ris','--search-id','local-primary','--searched-at','fictional','--output',out)
            self.assertNotEqual(result.returncode,0);self.assertFalse(out.exists())

    def test_observed_dangling_output_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);target=root/'missing';link=root/'output'
            try:link.symlink_to(target)
            except (OSError,NotImplementedError):self.skipTest('symlink creation unavailable')
            with self.assertRaises(FileExistsError):intake._write_new(link,b'no')
            self.assertTrue(link.is_symlink());self.assertFalse(target.exists())

    def test_cli_serialization_preflight_prevents_output(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'output.json'
            argv=['ris_intake.py','preview',str(ROOT/'examples/bibliographic-base.json'),str(ROOT/'examples/ris-export.ris'),
                  '--search-id','local-primary','--searched-at','fictional','--output',str(out),'--text']
            with patch.object(sys,'argv',argv),patch.object(intake,'render_text',return_value='\ud800'), \
                 patch('sys.stderr',new=io.StringIO()),self.assertRaises(SystemExit):intake.main()
            self.assertFalse(out.exists())


if __name__=='__main__':
    unittest.main()
