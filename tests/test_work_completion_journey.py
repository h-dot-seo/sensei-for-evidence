"""Execute the documented synthetic work-to-deliverable path, not actual research."""
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
from prisma_reports import report_flow
from work_review import review_packets

ROOT = Path(__file__).resolve().parents[1]


class WorkCompletionJourneyTests(unittest.TestCase):
    def test_fifteen_documented_commands_preserve_research_and_show_two_unblockings(self):
        document = (ROOT / 'docs/WORK_COMPLETION_INTAKE.md').read_text(encoding='utf-8')
        commands = [line for block in re.findall(r'```sh\n(.*?)```', document, re.S)
                    for line in block.splitlines() if line.startswith('python ')]
        self.assertEqual(len(commands), 15)
        base = json.loads((ROOT / 'examples/result-source-current.json').read_bytes())
        with tempfile.TemporaryDirectory(prefix='sensei completion journey ') as td:
            output = Path(td)
            for command in commands:
                args = [str(ROOT / value) if value.endswith('.py') or value.startswith('examples/')
                        else str(output / value[7:]) if value.startswith('OUTPUT/') else value
                        for value in shlex.split(command)[1:]]
                if 'assemble' in args:
                    prefix = 'work' if args[0].endswith('evidence_work_intake.py') else (
                        'source' if 'source-work-completion.json' in args[3] else 'evidence')
                    target = json.loads((output / (prefix + '-target.json')).read_bytes())
                    review = copy.deepcopy(target['review_document'])
                    self.assertIsNone(review['decision'])
                    review.update(receipt_id='fictional-' + prefix, reviewer='Fictional reviewer',
                        reviewed_at='2026-11-04', rationale='Explicit synthetic software rehearsal only.',
                        decision='import_evidence_work' if prefix == 'work' else 'record_supplied_completion')
                    (output / (prefix + '-review.json')).write_text(json.dumps(review), encoding='utf-8')
                result = subprocess.run([sys.executable, *args], cwd=td, capture_output=True, timeout=60)
                self.assertEqual(result.returncode, 0, (command, result.stderr.decode('utf-8')))
                self.assertTrue(result.stdout)
            with_work = json.loads((output / 'with-work.json').read_bytes())
            source_done = json.loads((output / 'source-complete.json').read_bytes())
            done = json.loads((output / 'evidence-complete.json').read_bytes())
            self.assertEqual(len(base['gaps']), 2)
            self.assertEqual(len(done['gaps']), 4)
            self.assertEqual(len(done['evidence']), 4)
            for p in (source_done, done):
                self.assertEqual({k: v for k, v in with_work.items() if k != 'gaps'},
                                 {k: v for k, v in p.items() if k != 'gaps'})
                self.assertEqual(run(p)['planning']['review_targets'], run(with_work)['planning']['review_targets'])
                self.assertEqual(report_flow(p)['report_flow'], report_flow(with_work)['report_flow'])
            before = {w['work_package_id']: w for w in run(with_work)['work_packages']}
            middle = {w['work_package_id']: w for w in run(source_done)['work_packages']}
            after = {w['work_package_id']: w for w in run(done)['work_packages']}
            self.assertEqual(before['WP-RESULT-TRACE-NOTE']['blocked_by'], ['WP-MEMBERSHIP-SOURCES'])
            self.assertEqual(middle['WP-RESULT-TRACE-NOTE']['blocked_by'], [])
            self.assertEqual(middle['WP-RESULT-LIMITS-NOTE']['blocked_by'], ['WP-RESULT-TRACE-NOTE'])
            self.assertEqual(after['WP-RESULT-LIMITS-NOTE']['blocked_by'], [])
            self.assertEqual(after['WP-RESULT-LIMITS-NOTE']['status'], 'PLANNED')
            self.assertEqual(after['WP-RESULT-LINKS']['status'], 'PLANNED')
            completions = {w['work_package_id']: w for w in run(done)['planning']['completion_ledger']}
            for wid in ('WP-MEMBERSHIP-SOURCES', 'WP-RESULT-TRACE-NOTE'):
                self.assertEqual(completions[wid]['source_match_status'], 'CURRENT_SOURCE')
                self.assertEqual(completions[wid]['acceptance_assessment'], 'NOT_PERFORMED')
            draft = json.loads((output / 'completion-draft.json').read_bytes())
            self.assertIsNone(draft['acceptance_verified'])
            packets = review_packets(done, 'WP-RESULT-LIMITS-NOTE', include_prerequisites=True)
            self.assertEqual(packets['conclusion_readiness'], 'NOT_READY')
            self.assertEqual(packets['census_claim'], 'NOT_ESTABLISHED')


if __name__ == '__main__':
    unittest.main()
