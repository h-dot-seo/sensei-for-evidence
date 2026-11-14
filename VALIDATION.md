# Validation record

Current release: `0.127.0-result-document-shapes` (2026-11-14). This file is the
current snapshot; every dated entry since the 2026-11-02 release preparation is kept
verbatim, in order, in [docs/VALIDATION_HISTORY.md](docs/VALIDATION_HISTORY.md).

## What CI runs

GitHub Actions (`.github/workflows/tests.yml`) runs on every push to `main` and on
every pull request, and on manual dispatch, on a matrix of `ubuntu-latest` and `windows-latest` with Python
3.10, 3.12, 3.14 and 3.15 (eight jobs):

1. `python -m unittest discover -v` on Python 3.10 and the same command with
   `--durations 25` on Python 3.12/3.14/3.15 — the synthetic test suite in the `tests/` package,
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

Release: `0.127.0-result-document-shapes` (2026-11-14).

Added descriptive completed manual result candidates and separate import-review
schemas. Exact nested fields, candidate bounds, mechanism labels and required source
reference structure track the existing Python validator. The original extraction
worksheet and blank target review intentionally fail these completed-input shapes.
No values, review, source authenticity or scientific judgement are generated.

Python remains authoritative for nonblank text, duplicate evidence/source identities,
real dates, exact integer versions, report/study/record/source context and exact target
binding. Tests retain accepted and rejected structural variants and explicitly looser
shape examples rather than claiming equivalence. The existing complete NBIB-to-evidence
rehearsal still assembles and replays the unchanged supplied inputs, and rejects stale
review hashes and unknown sources despite passing shape checks. The explicit example
inventory now maps9 of113 files;104 remain outside these seven authored shapes.
All107 root Python files and ENGINE_FILES are unchanged. Full2212 tests in181.299s
passed (skip1). Independent33 focused tests plus32 leaf mutations passed; no blockers.
Audit508/manifest507 and Python3.10 grammar259 passed. Final focused validation covers
this record update. External reference-manager compatibility, prior HTML visual QA
and Korean-locale Windows remain unverified.
