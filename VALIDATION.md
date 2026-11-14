# Validation record

Current release: `0.123.0-decision-document-shapes` (2026-11-14). This file is the
current snapshot; every dated entry since the 2026-11-02 release preparation is kept
verbatim, in order, in [docs/VALIDATION_HISTORY.md](docs/VALIDATION_HISTORY.md).

## What CI runs

GitHub Actions (`.github/workflows/tests.yml`) runs on every push to `main` and on
every pull request, on a matrix of `ubuntu-latest` and `windows-latest` with Python
3.10 and 3.12:

1. `python -m unittest discover -v` on Python 3.10 and the same command with
   `--durations 25` on Python 3.12 — the synthetic test suite in the `tests/` package,
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

Release: `0.123.0-decision-document-shapes` (2026-11-14).

Added descriptive completed screening/report decision schemas. Report include
requires exactly scalar study_id or nonempty unique study_ids; exclude requires null.
Existing authoritative validators retain real-date, nonblank, exact-version, target
and protocol checks. No values, approvals or scientific judgments are generated.
Existing screening/report journeys now perform shape inspection before assembly;
all19 commands are replayed. Explicit fixture mapping covers7 documents, with106
outside these five shapes. Root modules, contract source bindings and ENGINE_FILES
remain byte-identical. Numeric1.0, whitespace, calendar and regex differences are
explicitly tested rather than hidden. Full protocol and output schemas remain absent.
Full2197 tests in185.657s passed (skip1). Independent17 tests plus90 decision/study
combinations passed; only the explicitly documented whitespace shape differences
remained. Audit503/manifest502 and Python3.10 grammar256 passed. All107 root modules
remain byte-identical. No unresolved review blockers; external-export compatibility
and prior HTML visual QA remain unverified.
