# Validation record

Current release: `0.125.0-bundle-cli-test-budget` (2026-11-14). This file is the
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

Release: `0.125.0-bundle-cli-test-budget` (2026-11-14).

Moved only repeated create-side invalid-input cases in seven bundle test methods
to the existing serial trusted-test harness. All original assertions and test method
inventories remain; this is not a product change or a process-isolation guarantee.
The49 in-process calls replace repeated startup while17 real subprocess calls remain
in those tests (previously56). Ten representative create errors compare exact return
code/stdout/stderr between both paths, and seven malformed-ZIP verifies remain real.

Every other test method, the harness, root modules and ENGINE_FILES are byte-identical.
In particular, real roundtrip, non-ASCII stdio, PYTHONIOENCODING=ascii/PYTHONUTF8=0,
exclusive output and documented journey tests retain their actual subprocess behavior.
The harness's ascii stream option does not simulate Python startup or UTF-8 mode.
No wall-clock speedup is promised; fixture and in-process bundle costs remain.
Full2201 tests in176.463s passed (skip1), retaining the prior total. Independent212
bundle/harness tests passed in48.732s; separate seven-method replay confirmed49
harness calls and interpreter-surface restoration. Independent AST checks retained
205 methods and846 original assertions across the seven files. Audit504/manifest503
and Python3.10 grammar257 passed. No unresolved review blockers; Korean-locale
Windows, external-export compatibility and prior HTML visual QA remain unverified.
