# Validation record

Current release: `0.97.0-screening-sheet-intake` (2026-11-14). This file is the
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

## 2026-11-14 Reviewed screening-sheet positions intake (0.97.0-screening-sheet-intake)

Second bounded #33 increment: a separate wrapper appends human-supplied CSV
positions after exact-target import review. Export-time protocol/source hashes
and every read-only cell are checked against the existing export. Blank human
rows are explicitly skipped; partial rows, formula/escape ambiguity, duplicate
review IDs and record/reviewer pairs fail closed. Original CSV bytes, spans,
review cues and implementation hashes remain in a detached replayable application.
Canonical screening and old positions are never overwritten or renewed.

Local Python 3.12 full suite: `Ran 1981 tests in 140.201s`, `OK (skipped=1)`.
Focused intake/export/navigation: 44 tests pass, including 10 new intake tests.
The synthetic guide commands execute verbatim with tokenization before host-path
substitution. Publication audit: 417 files, pass; manifest, compileall, Python 3.10
grammar and unchanged ENGINE_FILES/offline_adapter checks pass. Existing executable
sh blocks remain byte-identical. Catalog: 26 routes, 113 help entrypoints.

Independent review identified a multi-output preflight gap: an already-existing
report path could be discovered after a candidate was written. Both destinations,
parent directories, alias equality and serialized sizes are now checked before
writing; regression tests cover existing destinations, identical paths and absent
parents with no candidate creation. Exclusive creation remains the final guard.
I/O failures and races are not atomic transactions and may leave partial output;
the guide states that boundary. No local test failures occurred. These are synthetic
offline checks, not source reading, reviewer identity or eligibility validation.

