# Validation record

Current release: `0.98.0-blank-decision-sheet` (2026-11-14). This file is the
current snapshot; every dated entry since the 2026-11-02 release preparation is kept
verbatim, in order, in [docs/VALIDATION_HISTORY.md](docs/VALIDATION_HISTORY.md).

## What CI runs

GitHub Actions (`.github/workflows/tests.yml`) runs on every push to `main` and on
every pull request, on a matrix of `ubuntu-latest` and `windows-latest` with Python
3.10 and 3.12:

1. `python -m unittest discover -v` — the synthetic test suite in the `tests/` package,
   including the tests that execute the documented walkthrough command blocks exactly
   as written.
2. `python audit_publication.py` — the limited public-file/type/secret-pattern scan.
3. `python verify_manifest.py` — the complete published inventory against exact
   checkout bytes.

Actions are commit-pinned, token permissions are read-only, checkout does not persist
credentials, and no secrets or deployment steps are used. The published head's matrix
result is the public Actions history of this repository; this file does not restate it.

## How to verify locally

From the repository root, with Python 3.10 or later and the standard library only:

Start with `python sensei.py check` for the read-only smoke check. It is not the
full suite, CI matrix or research validation. Full verification (several minutes):

```sh
python -m unittest discover -v
python audit_publication.py
python verify_manifest.py
```

Expected: every test passes or is skipped (skips cover POSIX-only source access and
symlink privileges on native Windows), `audit_publication.py` prints `"pass": true`,
and `verify_manifest.py` prints `{"valid": true, "errors": []}`. On restricted Windows
hosts set `TEMP` and `TMP` to an authorized writable directory first. Walkthrough tests
replay the documented command blocks of the guides in a temporary directory; nothing is
written inside the checkout. `python -m compileall -q .` must stay clean. One test
module runs as `python -m unittest tests.test_<module> -v`.

## What this record does not claim

The tests exercise generic code on entirely fictional fixtures. They do not evaluate
scientific fidelity, literature coverage, source authenticity, reviewer independence,
guideline currency or clinical applicability, and no live PubMed request is part of the
suite. The publication scanner is not a complete secret detector, anonymizer or legal
clearance tool, and a passing manifest proves byte identity, not authorship or
redistribution rights. Local test results do not establish that a remote publication
succeeded; the public CI history is the record of published heads.

## Latest change

## 2026-11-14 Blank human-decision sheets (0.98.0-blank-decision-sheet)

A small export-only #33 increment reuses the existing source-sheet and screening
review views. At most 100 explicitly ordered or all enumerated records are shown;
all seven human decision fields remain empty. Exact prior canonical rows and
supplied review ledgers/cues are read-only JSON with export-time protocol, source
and review-context hashes. No vote, recommended choice, sequential decision target,
receipt, canonical mutation or batch edited-sheet intake is introduced. The guide
keeps the positions/decisions distinction and pending batch application explicit.

Local Python 3.12 full suite: `Ran 1993 tests in 140.367s`, `OK (skipped=1)`.
Focused decision/source-sheet/intake/navigation: 56 tests pass (12 new decision
sheet tests). Independent review ran 58 decision/source/review tests successfully,
compared ENGINE_FILES against the prior release and found no blockers. Publication
audit: 420 files, pass; manifest, compileall, Python 3.10 grammar, ENGINE_FILES and
offline_adapter byte preservation pass. Existing executable sh blocks are unchanged;
the new guide runs verbatim with tokenization before Windows path substitution.
Catalog: 26 routes, 114 help entrypoints. No test failures occurred.

Cases cover conflict/stale context without a winner, all human fields blank,
literal/escaped ID collisions, ordered selection and unknown/duplicate rejection,
100-record bound, whole-protocol validation, drift hashes, incompatible positions
intake headers, empty catalog, byte bounds, exclusive output and synthetic CLI
walkthrough. These are offline bookkeeping checks, not source reading, identity,
scientific assessment or real spreadsheet interoperability certification.

