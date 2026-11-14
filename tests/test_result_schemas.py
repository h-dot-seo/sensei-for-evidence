"""Completed manual inputs, not extraction, source validation or review authority."""
import ast
import copy
import inspect
import json
from pathlib import Path
import unittest

import result_intake
import result_extraction
import schema_check

ROOT=Path(__file__).resolve().parents[1]
def load(path):return json.loads((ROOT/path).read_bytes())

class ResultSchemaTests(unittest.TestCase):
    def parts(self,kind):
        return (load('schemas/result-'+kind+'.schema.json'),
                load('examples/batch-to-evidence/results'+('-review' if kind=='review' else '')+'.json'),
                result_intake.validate_review_document if kind=='review' else result_intake.validate_candidate_document)

    def both_bad(self,s,d,validator):
        self.assertTrue(schema_check.check(s,d))
        with self.assertRaises(ValueError):validator(d)

    def test_fields_bounds_and_enums_track_existing_validator(self):
        s,d,v=self.parts('candidates');row=s['properties']['candidates']['items']
        for shape,fields in [(row,result_intake.CANDIDATE_FIELDS),(row['properties']['evidence'],result_intake.EVIDENCE_FIELDS),
                             (row['properties']['source_references']['items'],{'source_id','extraction_locator'})]:
            self.assertEqual(set(shape['properties']),fields);self.assertEqual(set(shape['required']),fields)
            self.assertFalse(shape['additionalProperties'])
        self.assertEqual(s['properties']['candidates']['maxItems'],result_intake.MAX_CANDIDATES)
        tree=ast.parse(inspect.getsource(result_intake.validate_candidate_document))
        enums=[ast.literal_eval(n.comparators[0]) for n in ast.walk(tree) if isinstance(n,ast.Compare)
               and isinstance(n.left,ast.Subscript) and isinstance(n.left.slice,ast.Constant)
               and n.left.slice.value=='mechanism_basis']
        self.assertEqual(row['properties']['evidence']['properties']['mechanism_basis']['enum'],list(enums[0]))
        s,d,v=self.parts('review');self.assertEqual(set(s['properties']),result_intake.REVIEW_FIELDS)
        self.assertEqual(set(s['required']),result_intake.REVIEW_FIELDS);self.assertFalse(s['additionalProperties'])
        tree=ast.parse(inspect.getsource(result_intake.validate_review_document))
        decisions=[ast.literal_eval(n.comparators[0]) for n in ast.walk(tree) if isinstance(n,ast.Compare)
                   and isinstance(n.left,ast.Subscript) and isinstance(n.left.slice,ast.Constant)
                   and n.left.slice.value=='decision']
        self.assertEqual(s['properties']['decision']['const'],decisions[0])

    def test_nested_required_unknown_and_wrong_types_rejected_by_both(self):
        for kind in ('candidates','review'):
            s,d,v=self.parts(kind);before=copy.deepcopy(d)
            paths=[()] if kind=='review' else [(),('candidates',0),('candidates',0,'evidence'),('candidates',0,'source_references',0)]
            for path in paths:
                def at(doc):
                    for k in path:doc=doc[k]
                    return doc
                for key in at(d):
                    for mode in ('missing','bool','empty'):
                        bad=copy.deepcopy(d);node=at(bad)
                        if mode=='missing':del node[key]
                        else:node[key]=False if mode=='bool' else ''
                        self.both_bad(s,bad,v)
                bad=copy.deepcopy(d);at(bad)['unexpected']=None;self.both_bad(s,bad,v)
            self.assertEqual(d,before)

    def test_allowed_variants_and_rejected_boundaries(self):
        s,d,v=self.parts('candidates')
        for count in (1,100):
            for label in ('association','intervention','unknown'):
                good=copy.deepcopy(d);good['candidates']=[copy.deepcopy(d['candidates'][0]) for _ in range(count)]
                for i,row in enumerate(good['candidates']):row['evidence'].update(evidence_id='synthetic-'+str(i),mechanism_basis=label)
                v(good);self.assertEqual(schema_check.check(s,good),[])
        for rows in ([],[d['candidates'][0]]*101):
            bad=copy.deepcopy(d);bad['candidates']=rows;self.both_bad(s,bad,v)
        for path,val in [(('source_references',),[]),(('evidence','mechanism_basis'),'inferred'),(('extracted_at',),'2026/11/14')]:
            bad=copy.deepcopy(d);node=bad['candidates'][0]
            for key in path[:-1]:node=node[key]
            node[path[-1]]=val;self.both_bad(s,bad,v)
        s,d,v=self.parts('review')
        for key,val in [('decision','approve'),('target_sha256','A'*64),('reviewed_at','today'),('schema_version',2)]:
            bad=copy.deepcopy(d);bad[key]=val;self.both_bad(s,bad,v)
        v(d);self.assertEqual(schema_check.check(s,d),[])

    def test_explicitly_looser_shape_rules_do_not_claim_python_equivalence(self):
        for kind in ('candidates','review'):
            s,d,v=self.parts(kind)
            bads=[]
            bad=copy.deepcopy(d);bad['schema_version']=1.0;bads.append(bad)
            if kind=='review':
                for key,val in [('reviewer',' '),('reviewed_at','2026-02-30'),('target_sha256','0'*64+'\n')]:
                    bad=copy.deepcopy(d);bad[key]=val;bads.append(bad)
            else:
                for key,val in [('extracted_by',' '),('extracted_at','2026-02-30'),('extracted_at','2026-11-14\n')]:
                    bad=copy.deepcopy(d);bad['candidates'][0][key]=val;bads.append(bad)
                bad=copy.deepcopy(d);bad['candidates'][1]['evidence']['evidence_id']=bad['candidates'][0]['evidence']['evidence_id'];bads.append(bad)
                bad=copy.deepcopy(d);ref=copy.deepcopy(bad['candidates'][0]['source_references'][0]);ref['extraction_locator']='Another location';bad['candidates'][0]['source_references'].append(ref);bads.append(bad)
                bad=copy.deepcopy(d);bad['candidates'][0]['source_references'][0]['source_id']=' ';bads.append(bad)
            for bad in bads:
                self.assertEqual(schema_check.check(s,bad),[])
                with self.assertRaises(ValueError):v(bad)
