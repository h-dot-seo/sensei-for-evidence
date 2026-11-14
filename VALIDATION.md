# Validation record

Current release: `0.107.0-passive-review-view` (2026-11-14). This file is the
current snapshot; every dated entry since the 2026-11-02 release preparation is kept
verbatim, in order, in [docs/VALIDATION_HISTORY.md](docs/VALIDATION_HISTORY.md).

## What CI runs

GitHub Actions (`.github/workflows/tests.yml`) runs on every push to `main` and on
every pull request, on a matrix of `ubuntu-latest` and `windows-latest` with Python
3.10 and 3.12:

1. `python -m unittest discover -v` on Python 3.10 and the same command with
   `--durations 25` on Python 3.12 — the synthetic test suite in the `tests/` package,
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

## 2026-11-14 One-file dispatcher selection (0.107.0-passive-review-view)

A separate real-user-path improvement, not a test harness conversion: sensei.py run
now validates the existing basename grammar and exact directory-entry spelling,
then reads/parses only the selected eligible file. It excludes itself, helpers and
nonfiles using the same entrypoint predicate. No cache. Existing list/check whole
checkout behavior remains. An unrelated syntax error no longer blocks a valid
selection, while full discovery and the selected file still expose their errors.
Existing symlink/trusted-checkout limits are documented, not silently strengthened
or presented as an isolation guarantee. ENGINE_FILES and other root Python unchanged.

Four-case before/after exact-result measurement: 388 source reads/AST parses become
2 (valid script plus helper). Three alternating runs: old0.660/0.674/0.678s versus
new0.00237/0.00230/0.00237s on Python3.12.14/Linux. Counts exclude directory metadata
calls. [Selection guide](docs/DISPATCHER_SELECTION.md) records reproduction and scope.
All existing subprocess dispatcher tests remain unchanged; new regression tests pin
exact case, zero/one source access, discovery differences, selected errors and no cache.

Full local suite: 2069 tests in 146.498s, OK (one platform skip). Focused and
independent dispatcher tests: 20 pass. Independent four-case benchmark: exact paths
and errors match, reads/AST388 to2, 0.644s to0.00246s locally. Unchanged real-process
rejected-name test measured4.880s before and0.466s after. No timing assertion.
Audit453 files, manifest, compileall, Python3.10 grammar, ENGINE/other root Python,
shared helper/CI/existing dispatcher tests and old executable blocks pass. Symlink
regression skips where the OS cannot create one. Final checkout/dispatcher checks
rerun after docs/manifest finalization. Independent review found no code blockers;
test-runtime documentation now explicitly scopes earlier production-byte-preservation
claims to the earlier test-only releases.

## 2026-11-14: passive local HTML review (0.107.0)

Added research_view.py and a literal synthetic guide. Full suite: 2081 tests in
160.104s, OK (one existing conditional skip). New12 tests, independent focused38
and direct supplied READY/challenge checks passed. Existing root modules,
ENGINE_FILES and all prior guide sh blocks are byte-identical. Python3.10 grammar
checked for231 files; audit456 and manifest455 passed before this record update.
CSP/allowlisted tags/escaping/fixed anchors, deterministic bytes, immutability,
work scope, output and input limits, exclusive paths, receipts and CLI errors tested.

Visual QA limitation: Chromium launch was attempted both normally and with execution
approval but failed at socket() with Operation not permitted. No screenshots or
responsive/print visual verification were completed. DOM and CSS contract tests
are not visual QA. Real user data, source verification and scientific validity
were not tested. Partial output after OS write failure and hostile path races
are not transactionally prevented; these limits are stated in REVIEW_VIEWS.md.
