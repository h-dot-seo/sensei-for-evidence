"""The current release record and last chronological history entry agree."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def validate_record(manifest, validation, history):
    current = re.search(r'Current release: `([^`]+)` \(([0-9-]+)\)', validation)
    latest = validation.split('## Latest change\n', 1)[1]
    heading = re.findall(r'^## ([^\n]+)', history, re.M)[-1]
    return (current is not None and current.groups() == (manifest['release'], manifest['date'])
            and f"Release: `{manifest['release']}` ({manifest['date']})." in latest
            and heading == f"{manifest['date']}: {manifest['release']}")


class ReleaseRecordTests(unittest.TestCase):
    def test_actual_and_mutated_records(self):
        m = json.loads((ROOT / 'PUBLICATION_MANIFEST.json').read_bytes())
        v = (ROOT / 'VALIDATION.md').read_text(encoding='utf-8')
        h = (ROOT / 'docs/VALIDATION_HISTORY.md').read_text(encoding='utf-8')
        self.assertTrue(validate_record(m, v, h))
        for key in ('release', 'date'):
            changed = dict(m, **{key: 'wrong'})
            self.assertFalse(validate_record(changed, v, h))
        self.assertFalse(validate_record(m, v, h + '\n## stale\n'))
