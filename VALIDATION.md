# Validation record

Current release: `0.124.0-forward-python-ci` (2026-11-14). This file is the
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

Release: `0.124.0-forward-python-ci` (2026-11-14).

Expanded the unchanged pinned/read-only CI workflow to Python3.10/3.12/3.14/3.15
on both Ubuntu and Windows (eight jobs), retaining both baseline versions. Manual
dispatch is available; only main has a push trigger. PR-only cancellation is grouped
by workflow/ref. Non-PR groups use unique run IDs so main/manual pending runs are not
replaced by another run in the same group. No branch is deleted. Existing duration reporting remains on versions other than3.10.

The native Windows junction test now captures cmd.exe output as bytes and uses a
safe tuple representation for diagnostics. Synthetic non-UTF8/None output regression
is not evidence of a live Korean-locale Windows run. Python3.15 enables UTF-8 mode by
default ([PEP686](https://peps.python.org/pep-0686/)); cmd.exe output need not be UTF-8.
Root modules and command-contract bindings remain unchanged. Actual new-version
setup, full tests, audit and manifest are gated by the published CI result, not assumed.
Local full2201 tests passed on Python3.12 in189.054s and Python3.13.5 in187.540s
(skip1 each). Independent14 tests passed (native Windows skip1); the pending-run
cancellation issue was corrected by unique non-PR groups. Audit504/manifest503 and
Python3.10 grammar257 passed. All107 root modules are byte-identical. No unresolved
local review blockers. New3.14/3.15 coverage requires actual remote8-job results;
Korean-locale Windows, external-export compatibility and HTML visual QA remain unverified.
