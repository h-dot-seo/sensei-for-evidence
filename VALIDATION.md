# Validation record

Current release: `0.99.0-decision-batch-preview` (2026-11-14). This file is the
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

## 2026-11-14 Read-only decision-batch target preview (0.99.0-decision-batch-preview)

A separate #33 target-only increment parses exact edited decision-sheet bytes,
rejects changed read-only/export context and simulates completed supplied rows in
sheet order using the existing full single-record prepare/assemble guards. It
outputs hypothetical steps and a blank import review, not a candidate protocol,
applied receipt, approval or application. Batch assemble/verify remains absent.
Canonical screening, existing positions and stored history are untouched. The
100-row cap, lifetime receipt cap and cumulative/final target byte budgets bound
this convenience without claiming high-volume performance or scientific validity.

Final local Python 3.12 suite on fixed inputs: `Ran 2004 tests in 151.029s`,
`OK (skipped=1)`. Focused preview/export/intake/navigation: 57 tests pass; new preview
module: 11 tests pass after final byte-budget hardening. Independent review ran
60 preview/export/single-decision tests, reran two later-step guard/CLI regressions
and reviewed the final cumulative-byte guard; no remaining blockers. Actual 100
completed decisions were simulated successfully (local standalone 8.208s).

Audit: 424 files, pass. Manifest, compileall, Python 3.10 grammar, unchanged engine/
adapter bytes and preserved existing executable sh blocks pass. Catalog: 26 routes,
115 help entrypoints. The new synthetic guide executes verbatim. Tests cover exact
chain/order reproducibility, original/context drift, partial/blank/duplicate rows,
formula ambiguity, source spans, limits and second-step workflow failures that
preserve original input and produce no CLI output.

Validation correction: an interim final rerun had 10 checkout smoke failures
because the guide was edited while that run was active, leaving its manifest
outdated. No source-function failure occurred. The guide was frozen, the manifest
regenerated and the full 2004-test suite rerun successfully as recorded above.
This bookkeeping error occurred before publication; no failing revision was pushed.
All fixtures remain synthetic. Hashes and previews do not establish reviewer
identity, source reading, adjudication, chronological authenticity or readiness.

