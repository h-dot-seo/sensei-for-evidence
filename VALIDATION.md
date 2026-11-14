# Validation record

Current release: `0.101.0-report-review-intake` (2026-11-14). This file is the
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

## 2026-11-14 Append-only full-text reviewer-position intake (0.101.0-report-review-intake)

The #33 report_reviews follow-up closes the documented manual protocol-copy gap.
Existing report_review templates remain the first stage; a separate JSON intake
provides exact target, human import-review assembly and full replay. New positions
require a retrieved report, supplied source descriptors and the current source basis.
Null document digests remain explicitly unbound and non-null digests unverified.
Existing stale positions, report/source/canonical fields, memberships and old review
prefixes stay unchanged. Duplicate IDs/pairs are rejected without supersession.
CSV intake and report-study/inventory position ledgers are separate future work.

Local Python 3.12 full suite: `Ran 2026 tests in 151.610s`, `OK (skipped=1)`.
Initial focused intake/report-review/navigation suite: 79 pass. Final new intake
module: 13 pass, including a subsequently added absent/empty-ledger first-append
regression. Independent review ran 64 intake/report-review/shared-writer tests and
also independently exercised first-ledger append/replay; no remaining blockers.
Audit: 433 files, pass; manifest, compileall, Python 3.10 grammar, unchanged engine/
adapter bytes and existing executable sh blocks pass. Catalog: 26 routes, 121 help
entrypoints. No failures occurred in this increment.

Synthetic cases cover exact append/replay and unchanged record/report counts,
missing/pending/unavailable source contexts, explicitly unbound document digests,
source drift, preserved stale positions, no supersession, schema/partial/date/choice
validation, 100-row and byte budgets, unrelated-input/implementation review drift,
full-validator failure, replay tampering, exclusive single-output CLI and the
verbatim guide. Complete-file exclusive publication reuses the reviewed batch
writer without changing it. Selected source copies are budgeted before retention.

These checks do not establish actual full-text reading, reviewer identity, source
authenticity, comparable coverage, adjudication, scientific validity or readiness.
The detached application carries import-review provenance and must be retained.

