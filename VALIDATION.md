# Validation record

Current release: `0.139.0-authored-assertion-shapes` (2026-11-14). This file is the
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

Release: `0.139.0-authored-assertion-shapes` (2026-11-14).

Roadmap #36/#59: four descriptive completed challenge/readiness candidate and
separate review shapes, integrated with two existing exact-input CLI journeys.
All root product modules, checker, ENGINE, existing schemas and examples are byte
unchanged. Human authorship/readiness labels remain supplied, not authenticated
or scientifically assessed. Python remains authoritative for documented structural
looseness, real context and exact bindings. No license or external contract change.

Initial guide execution caught a missing schema_check `check` subcommand in the
new documentation. Corrected guide and test argument positions only; no product
changes. Six initial focused tests / 0.780 s passed. Final focused 44 tests / 3.713 s PASS (one native-Windows skip).
Full suite 2328 tests / 212.055 s PASS (one native-Windows skip).
Independent 54 tests / 4.941 s, actual 12-command journeys, and 792 mutations
compared with an independent Draft202012 validator passed. This is limited tested
agreement, not full JSON Schema compliance. All prior root/example/seven-schema
bytes and frozen tree were independently checked unchanged. Publication audit 581,
manifest 580, and Python 3.10 grammar 290 passed. No target resealing occurred.
