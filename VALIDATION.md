# Validation record

Current release: `0.144.0-scoped-cli-errors` (2026-11-15). This file is the
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

Release: `0.144.0-scoped-cli-errors` (2026-11-15).

Roadmap #51 completes the remaining twelve ordinary first-stage CLI error paths with a non-engine presentation leaf, explicit static labels/categories and nine downstream manual hash maps. Existing reads, bounds, strict parsing, validators, gates, usage exit2 and receipt-check negative stdout/exit1 are preserved. Existing stderr consumers must handle the changed presentation. Original implementations remain necessary for exact old bound records; no automatic resealer or real review update exists. See [contract](docs/CLI_ERROR_CONTRACT.md).

Exact root scope:21 existing modules plus cli_errors.py; global ENGINE files and accounting_flow/records_csv product bytes unchanged. An intermediate inspection mistakenly treated those two exporters' manual lists as missing propagation; full function inspection showed they already merge prisma_audit hashes. The unnecessary edits were reverted, and actual helper-map propagation is tested. This was an inspection mistake, not a product defect.

Initial test setup assumed appraisal text omitted its embedded engine map and used a nonempty base for the receipt template. Corrected named map-line handling and the existing empty-base fixture. A separate first test invocation named three nonexistent modules (not executed); corrected names yielded148 tests/7.425s PASS. New six tests/3.315s PASS; independent core six/3.341s plus27 exception/stage probes PASS. Historical compat initially had five failures from intentional helper/source-map and stderr changes; existing JSON baselines were preserved with exact named source reversals/map exceptions, and old error-position tests use the preserved previous main. Corrected combined38/15.696s PASS. Prior archive preflight tests exclude only the newly added helper from their old inventory. These corrections do not change the bounded readers or old assertions' data meaning.

Seven existing guides/61commands regenerated all15 fixed fictional targets: five changed and ten remained identical; other example bytes are preserved. Full/final independent validation pending.

First full run2356/215.516s had3 failures and11 errors (two platform skips): new helper missing from the command-contract root inventory; two historical inventories/registry comparison needed the explicit added-helper/source reversal; latest history heading used the wrong separator. Corrected metadata/test inventory bookkeeping only, preserving all prior baseline JSON and product bytes. Full revalidation pending.

Corrected full2356/222.346s PASS (two platform skips). Final focus49/27.014s PASS (one skip). Independent correction32/11.390s PASS (one skip), actual61guide commands/15targets and exact five metadata/test-record-only changes verified. Independent freeze tree02df0a87ca422248d29c85b95dcb22f7d3178ce8 matches. Audit611/manifest610 and Python3.10 grammar301 passed. After full verification only these result records and matching manifest rows change.
