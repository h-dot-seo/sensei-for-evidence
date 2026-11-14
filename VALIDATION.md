# Validation record

Current release: `0.129.0-standalone-research-map` (2026-11-14). This file is the
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

Release: `0.129.0-standalone-research-map` (2026-11-14).

Added a standalone authored research-map sidecar workflow, not full research-map
integration. Template leaves every human field and record/event basis blank. Review
compares supplied recording bases to exact question/criteria/search-plan plus map
content and preserves every CURRENT_SOURCE/STALE_SOURCE record. Stop events link to
supplied records and inherit stale status, never completion or sufficiency. Current
input counts are not historical recording-time observations. Verify compares the full
stored review against exact current-input/current-implementation replay.

The original107 root Python files and ENGINE_FILES remain byte-identical. Protocol,
gates, adapter receipts, research bundles, status/handoff/compare and human decisions
are unchanged. They do not consume or validate this sidecar. This is the ENGINE-external
first increment of the roadmap standalone alternative, not its full implementation.
Sidecar values and dates are supplied, unauthenticated and not scientific judgement.
Structural references, all-empty recording stage, changed map/core, mismatched replay,
unchanged engine/bundle output, strict JSON/limits, exclusive output and the fictional
three-command real CLI journey are covered. Contract coverage remains32 reviewed of178;
146 including the three new commands are explicitly NOT_REVIEWED.
Full2229 tests in192.852s passed (skip1). Independent33 focused tests and nine
map-field mutations passed, including record/event stale status and replay mismatch.
The protocol-key inventory required explicit literal core keys; after that equivalent
expression change, focused19 and the full suite passed. Audit513/manifest512 and
Python3.10 grammar262 passed; final focused checks cover the record update.
External reference-manager compatibility, prior HTML visual QA and Korean-locale
Windows remain unverified. No unresolved review blockers.
