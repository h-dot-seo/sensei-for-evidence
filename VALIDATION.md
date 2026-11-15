# Validation record

Current release: `0.147.0-supplied-amendment-ledger` (2026-11-15). This file is the
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

Release: `0.147.0-supplied-amendment-ledger` (2026-11-15).

Roadmap #43 adjustments (a), (b), (d): persist a supplied amendment through exact BEFORE/human-edited AFTER target, separate supplied review, append-only application and replay. Optional engine observations distinguish CURRENT_VERSION/NOT_CURRENT_VERSION from NOT_VERIFIED_IN_PLACE historical hashes/references; paired comparison has its own before-and-scope label, never the external note's two-hash label. There is no embedded after hash, no DECLARED/ENACTED status and no automatic history renewal. Adjustment (c), gate-closing semantics, remains explicitly unimplemented. Existing challenge/readiness modules and rules are unchanged. Human BEFORE→AFTER changes may alter existing STALE/gate values; adding only the amendment row must preserve every other AFTER run value. See [amendment ledger](docs/AMENDMENT_LEDGER.md).

Exact product scope: eight existing root modules (four ENGINE: evidence_workflow/research_bundle/adapter_integrity/bibliographic_integrity; four non-engine: compare_runs/research_status/review_handoff/protocol_keys) plus amendment_links in ENGINE and separate amendment_intake. Optional allowlist keys do not authorize edits to immutable imported context. Source proof records exact prior59/current bytes; all historical baseline JSON is retained through named source/fictional-target reversal. New engine identities require original implementations for old bound records; no actual review, source data or automatic public resealer is changed.

Initial eight tests had one harness error: build_bundle requires bytes, not a dict. A subsequent twelve-test probe incorrectly expected compare text's explicit implementation-fingerprint line to be unchanged. Both tests were corrected, not product behavior. Core35/3.157s PASS, including18 actual prior/current CLI paths (default and existing external note), exact named fingerprint exceptions only, native newline bytes, two sequential modifications, reference checks, separate-review rejection, native CSV/NBIB/RIS continuation, STALE and gate preservation. New13/3.216s PASS includes the nine-command documented fictional walkthrough. The template never fills a human decision; only tests provide fictional review fields.

Independent core24/3.749s PASS, plus12 independently executed sequential records/replays, exact prior59 source comparison, unchanged challenge/readiness bytes and before/after validation boundaries. A subsequent inventory check corrected only the alphabetical position of the new protocol_keys name; exact source proof was refreshed. Metadata focus41/14.520s PASS. Existing seven guides/61commands regenerated the fixed15 fictional target fields only; final independent/full validation remains pending.

Historical compatibility focus82/74.768s initially had20 fingerprint mismatches and one generated-fixture replay setup error. Existing baseline JSON was not changed. Historical view tests now control only the eight named amendment revision fingerprints and explicit new ENGINE entry in addition to their original four-view controls; current public APIs and complete output bytes still execute and compare. The older CLI-error presentation test uses the current engine for its newly generated detached fixture, while exact older sources are proved independently and round60 tests execute actual prior59/current60 paths. The old fixture failure was expected implementation binding, not permission to accept a stale application. Named primary-CLI and map-view exceptions were extended only for the declared engine revision. Corrected affected27/14.163s PASS. Full validation pending.

First full2386/238.940s had three historical-proof failures (two platform skips), not product failures: AST extraction omitted the trailing newline expected by two preserved builder-source hashes, and the older15-CLI baseline lacked the explicit amendment ENGINE-map exceptions. The helper now restores the exact original trailing newline; the CLI test names the eight changed sources and inserts only amendment_links after the previous final ENGINE field. Existing baseline files and product/fixture bytes remain unchanged. Corrected full validation pending.

Corrected focus37/14.185s exposed one subsequent assertion that still enumerated only the three earlier added ENGINE leaves; added the explicitly declared amendment_links leaf to that inventory. This did not change the fixed-engine ZIP-byte comparison or its expected baseline. Product and fixture bytes remain unchanged.

Corrected full2386/238.062s PASS (two platform skips), corrected focus37/16.151s PASS. Independent final52/15.370s (one skip) and narrow historical correction33/13.684s PASS. Actual prior59 builder source including its terminal LF matches the reversal exactly (a9638c414943a98f0db053ce1ec418ff7cca1f2cfb3bd89f3aeb743cddbbd30f); the full historical chain retains baseline f1f95832e2f92c3af8476958f171dbc1ecefce54e462de627f7ffd7977adb1d6. Fixed-engine ZIP bytes, eighteen actual prior/current CLI paths, nine new guide commands, sixty-one existing guide commands and fifteen exact fictional target updates passed. Initial-to-corrected freeze changed only one test helper, two historical tests and these two validation records; products, examples and baseline JSON were unchanged. Independent corrected freeze4020a2095b5bb0c725cfd7b3c23698572e4c87ef matched. Audit631/manifest630/Python3.10 grammar309 passed. After full validation only these two final result records and their manifest rows change.
