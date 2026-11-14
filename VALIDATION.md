# Validation record

Current release: `0.102.0-report-study-review-intake` (2026-11-14). This file is the
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

## 2026-11-14 Exact report-study reviewer-position intake (0.102.0-report-study-review-intake)

The #33 pair-position follow-up closes another documented manual-copy gap using
existing blank templates plus reviewed append/replay. New assertions require an
exact currently declared membership on a retrieved/source-declared report, current
pair basis and explicitly supplied same-report source IDs. No subset is selected
for a human. Old orphan/stale assertions, canonical reports, memberships, results,
counts and every prior position remain unchanged. Exclude positions only expose
existing cues; no canonical study selection or result deletion is introduced.

A small reviewed_intake_safety helper now shares only import-review validation
and complete application replay with report-review intake. Domain source/member
rules remain specific and engine schemas unchanged. Both targets bind helper bytes;
the prior report-intake fixture was regenerated and its regression suite rerun.
Whole report source snapshots are retained once per selected report and byte-budgeted.

Local Python 3.12 full suite: `Ran 2038 tests in 154.400s`, `OK (skipped=1)`.
Focused new/old intake, pair review and navigation: 90 pass. Independent review ran
66 new/old intake and pair-validator tests, confirmed unchanged ENGINE_FILES and
found no blockers. A nonblocking CLI error-prefix naming suggestion was corrected
before the final full run. Audit: 439 files, pass; manifest, compileall, Python 3.10
grammar, engine/adapter preservation and old executable sh blocks pass. New route
catalog: 27 groups, 125 help entrypoints. No test failures occurred.

Synthetic tests cover explicit source subsets/order, wrong-report/unknown/empty
source rejection, current/orphan pairs, null unbound digests, whole-catalog drift,
no supersession, 100-row/byte limits, first absent/empty ledger, exact import review,
whole replay tampering, candidate-validator failure without input changes, single
exclusive outputs and the verbatim guide. Shared complete-file writer unchanged.
No identity, independence, equivalent reading coverage, source authenticity,
adjudication, chronology or scientific readiness is established.

