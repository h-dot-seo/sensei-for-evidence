"""Synthetic exact-ID occurrence accounting; no bibliographic entity resolution."""
import copy
import io
import json
from pathlib import Path
import unittest
import zipfile

from evidence_workflow import run
from prisma_reports import report_flow
from research_bundle import build_bundle
from research_status import status, render_text


class RecordProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.p = json.loads(Path('examples/review-demo.json').read_text())
        self.p.pop('search_plan', None)

    def test_repeated_source_labels_keep_distinct_search_positions(self):
        search = copy.deepcopy(self.p['searches'][0])
        search.pop('search_id', None)
        self.p['searches'] = [copy.deepcopy(search), copy.deepcopy(search)]
        original = copy.deepcopy(self.p)
        result = run(self.p)
        self.assertEqual(self.p, original)
        for row in result['record_provenance']:
            self.assertEqual([o['search_index'] for o in row['occurrences']], [0, 1])
            self.assertEqual([o['search_id'] for o in row['occurrences']], [None, None])
        counts = result['flow']
        self.assertEqual(sum(len(row['occurrences']) for row in result['record_provenance']), counts['identified'])
        self.assertEqual(sum(len(row['occurrences']) - 1 for row in result['record_provenance']), counts['duplicates'])
        self.assertEqual(result['deduplication_scope'], 'exact_supplied_record_id_only')
        self.assertEqual(result['record_identity_verification'], 'NOT_ESTABLISHED')
        compact = status(self.p)
        self.assertEqual(compact['deduplication_scope'], result['deduplication_scope'])
        self.assertEqual(compact['record_identity_verification'], 'NOT_ESTABLISHED')
        self.assertNotIn('record_provenance', compact)
        self.assertIn('exact supplied IDs only', render_text(compact))

    def test_similar_ids_are_not_merged_or_normalized(self):
        self.p.update(searches=[dict(source='synthetic', query='synthetic', searched_at='synthetic',
                                    window='synthetic', record_ids=['r1', 'R1', ' r1'],
                                    complete=True, total_count=3, has_more=False)],
                      screening=[], evidence=[], gaps=[])
        self.p.pop('contexts', None)
        self.p.pop('appraisals', None)
        result = run(self.p)
        self.assertEqual([r['record_id'] for r in result['record_provenance']], [' r1', 'R1', 'r1'])
        self.assertEqual(result['flow']['duplicates'], 0)
        self.assertEqual(result['flow']['unique_records'], 3)

    def test_reports_keep_occurrence_lookup_and_source_ledger(self):
        research, reports = run(self.p), report_flow(self.p)
        self.assertEqual(reports['record_provenance'], research['record_provenance'])
        self.assertEqual(reports['search_ledger'], self.p['searches'])
        for record in reports['record_provenance']:
            for occurrence in record['occurrences']:
                search = reports['search_ledger'][occurrence['search_index']]
                self.assertIn(record['record_id'], search['record_ids'])
                self.assertEqual(search.get('search_id'), occurrence['search_id'])

    def test_bundle_preserves_ledger_and_scopes_duplicate_language(self):
        raw = json.dumps(self.p).encode()
        bundle = build_bundle(raw)
        self.assertEqual(bundle, build_bundle(raw))
        with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
            research = json.loads(archive.read('research.json'))
            reports = json.loads(archive.read('reports.json'))
            summary = archive.read('summary.md').decode()
        self.assertEqual(research['record_provenance'], reports['record_provenance'])
        self.assertIn('Identified record occurrences:', summary)
        self.assertIn('Repeated exact-ID occurrences:', summary)
        self.assertIn('identities not independently verified', summary)

    def test_page_overlap_does_not_inflate_search_occurrences(self):
        protocol = json.loads(Path('examples/paged-protocol.json').read_text())
        protocol['searches'][0]['pages'][1]['record_ids'].append('r1')
        result = run(protocol)
        self.assertFalse(result['coverage'][0]['complete'])
        self.assertEqual(result['coverage'][0]['page_audit']['record_occurrences'], 3)
        self.assertEqual(result['flow']['identified'], 2)
        self.assertEqual(result['flow']['duplicates'], 0)
        self.assertTrue(all(len(row['occurrences']) == 1 for row in result['record_provenance']))

    def test_empty_searches_have_empty_provenance(self):
        self.p.update(searches=[], screening=[], evidence=[], gaps=[])
        self.p.pop('contexts', None)
        self.p.pop('appraisals', None)
        result = run(self.p)
        self.assertEqual(result['record_provenance'], [])
        self.assertEqual(result['flow']['identified'], 0)


if __name__ == '__main__':
    unittest.main()
