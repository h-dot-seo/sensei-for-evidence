"""Brief work navigation reflects supplied states, never automatic decisions."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from work_review import review_packets,navigation_summary,render_brief
ROOT=Path(__file__).resolve().parent

class WorkNavigationTests(unittest.TestCase):
    def setUp(self):self.p=json.loads((ROOT/'examples/prerequisite-review.json').read_text())
    def report(self,expanded=True):return review_packets(self.p,'WP-TRANSLATION',expanded)
    def test_groups_reflect_only_selected_packets_and_dependencies(self):
        s=navigation_summary(self.report());g=s['work_state_groups']
        self.assertEqual(g['unblocked_planned'],['WP-RECEIPT-REVIEW'])
        self.assertEqual(g['blocked_unfinished'],['WP-EXTRACTION-REVIEW','WP-MECHANISM','WP-TRANSLATION'])
        selected=navigation_summary(self.report(False))
        self.assertEqual(selected['work_state_groups']['unblocked_planned'],[])
        self.assertEqual(selected['dependency_review']['omitted_direct_prerequisite_ids'],['WP-MECHANISM'])
    def test_in_progress_can_be_blocked_not_reclassified_as_actionable(self):
        self.p['gaps'][0]['status']='IN_PROGRESS';self.p['gaps'][1]['status']='IN_PROGRESS'
        g=navigation_summary(self.report())['work_state_groups']
        self.assertEqual(g['unblocked_in_progress'],['WP-RECEIPT-REVIEW'])
        self.assertIn('WP-EXTRACTION-REVIEW',g['blocked_unfinished'])
    def test_completed_note_retains_missing_search_and_no_acceptance_check(self):
        self.p['gaps'][0].update(status='COMPLETE',artifact_locator='synthetic://note',acceptance_verified=True)
        s=navigation_summary(self.report());self.assertEqual(s['work_state_groups']['completed_assertions'],['WP-RECEIPT-REVIEW'])
        self.assertEqual(s['work'][0]['recorded_review_gaps']['source_review_missing_searches'],['search-secondary'])
        text=render_brief(self.report());self.assertIn('artifact/acceptance (not checked)',text)
        self.assertIn('NOT_READY',text)
    def test_null_empty_and_nonempty_cues_are_not_conflated(self):
        p=json.loads((ROOT/'examples/source-work-protocol.json').read_text());r=review_packets(p)
        s=navigation_summary(r);self.assertIsNone(s['work'][0]['recorded_review_gaps']['units_without_outcome_statistics'])
        text=render_brief(r);self.assertIn('Review cue stages not supplied:',text)
        self.assertIn('source_review_missing_searches',text);self.assertIn('Empty cues are omitted',text)
    def test_planning_assertion_and_acceptance_criterion_preserved(self):
        s=navigation_summary(self.report());work=s['work'][-1]
        self.assertEqual(work['acceptance_criterion'],self.p['gaps'][-1]['acceptance_criterion'])
        self.assertEqual(work['planning']['source_match_status'],'STALE_SOURCE')
        self.assertIn(self.p['planning_decisions'][0]['rationale'],render_brief(self.report()))
    def test_existing_position_labels_remain_supplied_not_inferred(self):
        p=json.loads((ROOT/'examples/rationale-links.json').read_text());r=review_packets(p,'WP-TRANSLATION')
        statements=navigation_summary(r)['work'][0]['statement_review_statuses']
        self.assertTrue(any(pos['relation']=='challenges' for row in statements for pos in row['work_positions']))
        self.assertTrue(all(row['support_status']=='NOT_ASSESSED' for row in statements))
        self.assertIn('not support',render_brief(r))
    def test_input_output_copy_isolation(self):
        r=self.report();before=copy.deepcopy(r);s=navigation_summary(r)
        s['work'][0]['source_review_inputs'].clear();s['dependency_review']['edges'].clear()
        self.assertEqual(r,before)
    def test_hostile_supplied_text_escaped(self):
        self.p['gaps'][-1]['deliverable']='fictional\x1b[31m\u202e\ntext'
        text=render_brief(self.report());self.assertNotIn('\x1b',text);self.assertNotIn('\u202e',text)
        self.assertIn('\\u001b',text.lower())
    def test_cli_format_flags_and_compactness(self):
        cmd=[sys.executable,str(ROOT/'work_review.py'),str(ROOT/'examples/prerequisite-review.json'),'--work-package=WP-TRANSLATION','--include-prerequisites']
        brief=subprocess.run(cmd+['--brief'],capture_output=True,check=True).stdout
        full=subprocess.run(cmd+['--text'],capture_output=True,check=True).stdout
        self.assertLess(len(brief),len(full)//2);self.assertEqual(brief.decode(),render_brief(self.report()))
        invalid=subprocess.run(cmd+['--brief','--text'],capture_output=True);self.assertNotEqual(invalid.returncode,0)
    def test_empty_work_is_not_readiness(self):
        self.p['gaps']=[];self.p.pop('planning_decisions');r=review_packets(self.p)
        self.assertTrue(all(not ids for ids in navigation_summary(r)['work_state_groups'].values()))
        self.assertIn('Conclusion: NOT_READY',render_brief(r))

if __name__=='__main__':unittest.main()
