# Validation record

Current release: `0.133.0-supplied-evidence-basis` (2026-11-14). This file is the
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

Release: `0.133.0-supplied-evidence-basis` (2026-11-14).

Roadmap #41: optional supplied evidence-basis labels and same-report document
selections, with status-shaped uncertainty and a separately reviewed append-only
intake. Canonical result rows, actual human assertions, gate policy and scientific
assessment boundaries are unchanged. Related label/source changes are bound to
existing statement/work bases and can make old reviews stale without renewal.
Labels are not inferred from source-file observations. Figure/statistics coexistence
is only a cue. Template human fields are null; empty ledger presence is an explicit
stage transition, and legacy absence retains old behavior.

Six existing ENGINE modules change and evidence_basis_links.py is added. The
bibliographic enrichment allowance adds exactly evidence_bases. Old applications
need their recorded trusted implementation. Only 15 fixed fictional example target
hashes were maintained; all other bytes/reviewer/date/decision values remain intact.
No public or automatic refresh tool was added.

Actual previous45 execution reproduces all 44 valid legacy example input/run hashes
exactly without labels. Original43 default-view baseline bytes are retained, with
only explicit named implementation changes and one static route accounted for.
Core independent verification checked 72 label combinations. Final independent
verification passed 43 tests, the new 11-command guide, and 61 existing guide commands
that independently regenerate all 15 synthetic targets.

First full run: 2,274 tests / 190.690 s, six metadata/inventory failures (one platform
skip), corrected without changing the engine or intake. A subsequent 38-test metadata
check exposed the matching protocol-key inventory count (26 to 27), also corrected.
Corrected full suite: 2,274 tests passed in 187.613 s (one platform skip). Existing external interoperability,
HTML visual QA and Korean-locale Windows limits remain unverified. No license, tag,
new acceptance rule or actual human review is selected.
