# Validation record

Current release: `0.128.0-state-cli-failure-boundary` (2026-11-14). This file is the
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

Release: `0.128.0-state-cli-failure-boundary` (2026-11-14).

Separated legacy state CLI operational failures from normal mechanical findings.
Read/strict JSON/non-object/limit failures now produce one fixed category-and-state
stderr line, empty stdout and exit1; argparse remains exit2. This changes the older
error-JSON stdout path, so automation must not assume every exit1 carries findings.
Normal successful and negative findings retain their JSON output and exit0/1.
The validate() function is unchanged, and the legacy schema gains no scientific
or protocol-readiness authority. Normal reports are not anonymized.

The CLI reads at most50,000,001 bytes, accepts at most50,000,000, and checks nesting
at128 levels. Error paths omit input/path/exception content. Strict JSON, UTF-8,
byte/depth boundaries, actual/harness equivalence and original findings are covered.
Only validate_run.py changes among107 root Python files; ENGINE_FILES are unchanged.
The partial command registry source binding is refreshed without extending the32
reviewed commands;143 including validate_run remain NOT_REVIEWED.
Full2219 tests in182.974s passed (skip1). Independent34 focused tests plus28
old/new real-CLI shape variants passed with identical findings bytes/codes.
Audit509/manifest508 and Python3.10 grammar260 passed; final focused checks cover
this record update. No unresolved blockers. External reference-manager compatibility,
prior HTML visual QA and Korean-locale Windows remain unverified.

The first PR CI exposed a Windows-only test comparison mismatch: subprocess text
mode normalized CRLF while the harness retained it. The tests now capture bytes on
both paths, decode without newline conversion and expect the native line separator.
Runtime code is unchanged by this correction; the corrected matrix is rechecked.
