# Validation record

Current release: `0.103.0-inventory-review-intake` (2026-11-14). This file is the
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

## 2026-11-14 Described candidate-position intake (0.103.0-inventory-review-intake)

The #33 follow-up closes the candidate-position manual-copy gap. A bounded wrapper
reuses existing separate import-review, exact replay and complete exclusive writer
helpers. New positions require a currently described exact pair, retrieved report,
source descriptors and current candidate-review basis, plus explicit same-pair
inventory and same-report source ID subsets. Neither subset is inferred. Current
review of stale descriptions does not renew them. Existing orphan/stale positions,
canonical reports, included memberships, inventory descriptions and evidence remain.

Tests cover full same-pair description binding, distinct membership/inventory hash
domains, pending/excluded eligibility, unavailable retrieval, explicit subsets/order,
unknown/other-pair IDs, no supersession, 100 rows and byte budgets, absent/empty first
ledger, exact whole replay, input immutability and exclusive outputs. The verbatim
synthetic guide uses separate fictional position and import-review fixtures.
No ENGINE_FILES, canonical schema or shared safety implementation changes. The
existing descriptive_inventory route now exposes these separate positions without
adding another route group: 27 groups, 129 help entrypoints.

Local Python 3.12 full suite: 2053 tests pass (one platform skip). Focused new/old
intake and navigation: 63 pass, plus the added hash-domain regression passes with
all 15 new tests. Independent review: 56 tests pass; no blocking findings. A cosmetic
CLI/docstring domain label was clarified after the first full run (153.759 seconds),
then the synthetic import-review fixture regenerated and the full suite rerun.
Audit: 444 files; manifest, compileall, Python 3.10 grammar, protected engine/adapter
and shared helper bytes, and old executable sh blocks pass. No test failures in the
completed implementation. Synthetic software checks are not scientific correctness,
authenticated review or source-reading validation.
