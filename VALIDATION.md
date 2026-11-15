# Validation record

Current release: `0.150.0-native-continuation-archive` (2026-11-15). This file is the
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

Release: `0.150.0-native-continuation-archive` (2026-11-15).

Roadmap #34 adjustment(6)/(d): explicitly retain a continuation RIS wrapper and original bytes with its exact reviewed CSV-ledger association in a typed native archive. The new --ris-continuation INDEX=PATH never guesses a format or changes review/gate decisions. Product changes are exactly native_collection_bundle.py, ris_continuation_intake.py (boundary only) and review_handoff.py (boundary only). Native-specific implementation hashes gain the existing continuation parser/wrapper; global ENGINE_FILES, strict RIS/NBIB/parser, ordinary research ZIP and every existing example remain unchanged. Old wrappers/native archives still require their recorded implementation; no migration, edited hash or renewed review is supplied.

New core5/1.124s PASS includes eight real guide commands with separate fictional human inputs, exact BOM/CRLF original preservation, actual prior62 old-wrapper/archive replay and current rejection, unverified retained descriptor, and prior/current handoff whole JSON/text comparison with only exact self-fingerprint and one native workflow boundary difference. Core independent review found no product blocker; its60-test run included one existing expected-hash inventory failure awaiting the declared two-name extension. Guide read_text now explicitly requests UTF-8.

Initial focused66/12.350s had four expected revision-oracle failures: added native-only fingerprints, two unused zero format-count expectations and one historical root proof. Product summary was refined so legacy selections retain their existing count-key shape rather than receiving an unused zero continuation key. An initial new-module run accidentally imported another TestCase into discovery (48tests, one existing fingerprint failure); importing the module instead left the intended new5 tests. Initial historical83/35.143s had22 source/display/registry proof failures. No old baseline JSON was edited. Exact three-source reversal and the one full native-workflow boundary reversal now make historical75/30.347s PASS; no whitespace/path normalization or gate changes are used. Current62/current63 behavior is separately tested rather than claimed through controlled historical fingerprints.

Metadata focus94/32.986s PASS. All original197 guide block bytes are retained, three new blocks explicitly registered with the new test (current200). Existing fixed15 examples are unchanged because global engine bytes are unchanged. Final independent/full validation pending.

First full2406/247.139s had three historical-oracle failures (two platform skips): the prior shared-preflight experiment still assumed the native-specific ENGINE/dispatch/boundary environment had never expanded, and the old collection-command catalog lacked the exact new source/flag exceptions. Corrected historical preflight controls only the declared native ENGINE_FILES, FORMATS and BOUNDARY in addition to its original eight source reads, restoring the earlier extraction experiment without normalizing input/output ZIP bytes. It separately asserts the exact two added native hash names and one explicit format. Actual current native behavior, old artifact refusal and old-source replay remain in the new uncontrolled tests. The old command catalog adds only the three declared source exceptions and the one --ris-continuation usage field. Existing baseline JSON/product/fixture bytes are unchanged. Earlier independent focused passes did not include these three full-suite assertions; corrected full validation remains pending.

Final corrected verification: 2406 tests in 241.378s PASS (two platform skips), exit 0. The first corrected run was interrupted by an execution-environment transport disconnect before a summary and is not counted as a pass; after verifying that no process remained, the identical freeze was rerun from the start. Corrected independent review passed 11 tests in 12.379s and confirmed exactly five listed corrections plus the manifest, with product/example/baseline bytes unchanged. The tested freeze tree is 7cd411d0f8dc67763c983f48d199b14d01acf889. Final audit/manifest checks apply after this result-only record update. Remote CI and publication are separate verification stages.
