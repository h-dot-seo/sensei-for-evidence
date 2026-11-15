# Validation record

Current release: `0.148.0-opt-in-scale-observation` (2026-11-15). This file is the
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

Release: `0.148.0-opt-in-scale-observation` (2026-11-15).

Roadmap #52 adjustments (4), (5), (9): opt-in local synthetic scale probe under tests, fixed bounded shapes, eight actual product computations and separate generation/input/output timings. No new workflow or automatic large run. Existing root product sources, ENGINE, examples, schemas and CI bytes are unchanged. Complete outputs alone have full hashes; failed calls, skipped prerequisites and over-budget observations are explicit. Output budgets do not prevent product allocation or guarantee CPU/memory safety.

Core7/0.655s PASS; independent core7/0.633s PASS plus protected279-file direct comparison and injected failures. Explicit moderate and large runs completed all eight paths; the narrow large shape produced 48,809,916-byte synthesis and 47,917,494-byte ZIP, near the existing limit. docs/SCALE_ENVELOPE.md records dated environment, separate timings and limitations. Full/final validation pending.

Full2393/240.540s PASS (two platform skips). Final independent7/0.616s PASS with direct protected279-file comparison, both retained moderate/large receipts matched to current probe/source hashes, and all16 measurement table rows verified; large runs were not repeated by the reviewer. Independent freeze93e7d6ef51054502b1976c9450e5a3ea77388a93 matched. Audit635/manifest634/Python3.10 grammar311 PASS. Existing products, ENGINE, schemas, examples, workflows and baseline JSON remain byte-identical; no fictional targets needed updating. After full validation only these two final result records and their manifest rows change.
