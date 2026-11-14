"""Output-preserving joins, with deterministic work counts rather than timing promises."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import synthesis_review
import work_review
from evidence_workflow import run
from tests.test_view_scale import generated

ROOT = Path(__file__).resolve().parents[1]


class CountedRows(list):
    def __init__(self, rows):
        super().__init__(rows)
        self.visits = 0

    def __iter__(self):
        for row in super().__iter__():
            self.visits += 1
            yield row


def scan_index(rows):
    return rows


def scan_rows(rows, evidence_ids):
    return [row for row in rows if evidence_ids.intersection(row['evidence_ids'])]


class JoinIndexTests(unittest.TestCase):
    def test_positions_preserve_duplicates_order_empty_and_unknown_links(self):
        rows = [dict(evidence_ids=['z', 'a', 'a'], value=2),
                dict(evidence_ids=['b'], value=0),
                dict(evidence_ids=['a', 'z'], value=2),
                dict(evidence_ids=[], value=9)]
        before = copy.deepcopy(rows)
        index = work_review._evidence_row_index(rows)
        for ids in (set(), {'missing'}, {'z', 'a'}, {'b', 'z'}):
            actual = work_review._linked_rows(index, ids)
            expected = scan_rows(rows, ids)
            self.assertEqual(actual, expected)
            self.assertEqual([id(row) for row in actual], [id(row) for row in expected])
        self.assertEqual(rows, before)

    def test_sparse_row_visit_cost_is_not_packets_times_ledger(self):
        for n in (100, 200):
            rows = CountedRows([dict(evidence_ids=['e'+str(i)]) for i in range(n)])
            index = work_review._evidence_row_index(rows)
            for i in range(n):
                self.assertEqual(work_review._linked_rows(index, {'e'+str(i)}), [rows[i]])
            self.assertEqual(rows.visits, n)
            rows.visits = 0
            for i in range(n):
                scan_rows(rows, {'e'+str(i)})
            self.assertEqual(rows.visits, n*n)

    def test_actual_work_views_equal_scan_oracle_and_leave_inputs_unchanged(self):
        count = 0
        for path in sorted((ROOT/'examples').glob('*.json')):
            protocol = json.loads(path.read_bytes())
            if not isinstance(protocol, dict) or not {'question', 'searches', 'evidence'} <= protocol.keys():
                continue
            try:
                run(protocol)
            except ValueError:
                continue  # Examples also contain intentionally invalid research protocols.
            before = copy.deepcopy(protocol)
            with self.subTest(example=path.name):
                actual = work_review.review_packets(protocol)
                with patch.object(work_review, '_evidence_row_index', scan_index), patch.object(work_review, '_linked_rows', scan_rows):
                    expected = work_review.review_packets(protocol)
                self.assertEqual(actual, expected)
                self.assertEqual(protocol, before)
                for packet in actual['packets'][:2]:
                    wid = packet['work_package']['work_package_id']
                    for expand in (False, True):
                        selected = work_review.review_packets(protocol, wid, expand)
                        with patch.object(work_review, '_evidence_row_index', scan_index), patch.object(work_review, '_linked_rows', scan_rows):
                            self.assertEqual(selected, work_review.review_packets(protocol, wid, expand))
                count += 1
        self.assertGreaterEqual(count, 40)

    def test_actual_packet_build_consumes_unit_and_statement_ledgers_once(self):
        protocol = json.loads((ROOT/'examples/experiment-review.json').read_bytes())
        research = run(protocol)
        units = CountedRows(research['experiments']['experimental_unit_ledger'])
        statements = CountedRows(research['synthesis']['statement_ledger'])
        research['experiments']['experimental_unit_ledger'] = units
        research['synthesis']['statement_ledger'] = statements
        with patch.object(work_review, 'run', return_value=research):
            actual = work_review.review_packets(protocol)
        self.assertEqual(actual, work_review.review_packets(protocol))
        self.assertGreater(len(units), 0)
        self.assertEqual(units.visits, len(units))
        self.assertEqual(statements.visits, len(statements))

    def test_actual_synthesis_work_membership_is_single_pass_and_exact(self):
        protocol = generated(100)
        protocol['gaps'][0]['evidence_ids'] = ['e2', 'e0', 'e1']
        research = run(protocol)
        work = CountedRows(research['work_packages'])
        research['work_packages'] = work
        with patch.object(synthesis_review, 'run', return_value=research):
            actual = synthesis_review.snapshot(protocol)
        self.assertEqual(work.visits, len(work))
        for citation in actual['evidence_citation_index']:
            eid = citation['evidence']['evidence_id']
            self.assertEqual(citation['work_package_ids'], sorted(row['work_package_id'] for row in list.__iter__(work) if eid in row['evidence_ids']))
        self.assertEqual(actual, synthesis_review.snapshot(protocol))

    def test_packet_copies_remain_independent_and_unknown_selection_fails(self):
        protocol = generated(2)
        protocol['gaps'][1]['evidence_ids'] = ['e0']
        before = copy.deepcopy(protocol)
        result = work_review.review_packets(protocol)
        result['packets'][0]['results'][0]['evidence']['record_id'] = 'changed'
        self.assertEqual(result['packets'][1]['results'][0]['evidence']['record_id'], 'r0')
        self.assertEqual(protocol, before)
        with self.assertRaisesRegex(ValueError, 'unknown work package ID'):
            work_review.review_packets(protocol, 'missing')
