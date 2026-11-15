# Validation record

Current release: `0.141.0-collection-effects-contract` (2026-11-15). This file is the
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

Release: `0.141.0-collection-effects-contract` (2026-11-15).

Roadmap #57: twelve newly reviewed effect profiles complete a 17-profile supplied collection intake/review/native-archive journey with five unchanged existing profiles. Coverage is 44/200 reviewed, 156 unknown. Declarations are not execution permission, acceptance guarantees or human authentication. All root product/ENGINE and existing example bytes remain unchanged; no synthetic target refresh was needed. See [collection effects](docs/COLLECTION_EFFECTS.md).

New actual-process journey tests: three / 7.737 s PASS across CSV, RIS, single NBIB and ordered NBIB batch, separate fictional review, three archive families, JSON/text output-file equivalence and errors. Initial contract focus 18 / 20.748 s had six failures because the pre-existing generic missing-input test omitted newly covered preview/create required options, reaching usage exit2 instead of handled exit1. Added only those required test arguments; corrected 18 / 20.872 s PASS. Independent/final/full verification pending.

Full 2340 tests / 210.887 s PASS (two native-platform skips). Final focus 42 / 23.843 s PASS (one skip); audit592/manifest591 and Python3.10 grammar294 passed. Independent review noted that the RIS-only preview profile repeated a batch-specific option sentence. After the full run, removed only that sentence from RIS notes (batch profile unchanged); focused contract and inventory checks are rerun on the corrected prose. No product, test or example bytes changed in this correction. Final independent validation pending.

Final independent correction review passed: 25 tests / 10.040 s (one platform skip), audit592 and manifest validation. Exact corrected tree c88ef1ccebc11f2a0095fe25741e3f727f0406c1 matched independently. Prior root and example bytes are unchanged. Corrected focused verification: 42 / 23.717 s PASS (one skip). Only these result records and corresponding manifest entries change after that verification.
