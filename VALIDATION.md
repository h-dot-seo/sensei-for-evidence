# Validation record

Current release: `0.140.0-exclusive-output-guards` (2026-11-15). This file is the
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

Release: `0.140.0-exclusive-output-guards` (2026-11-15).

Roadmap #97: fifteen remaining unguarded non-engine consumers / sixteen output
sites share explicit existing-entry refusal followed by exclusive binary creation.
No atomic publication, race-proof paths, source-reader weakening or partial-file
cleanup is claimed. Global ENGINE and five engine/adapter-bound writers remain
byte unchanged; guarded writers, JSON/date parsing and scientific policy remain
unchanged. Consumers fingerprint the new helper; older artifacts require their
recorded implementation. See [output contract](docs/OUTPUT_CONTRACT.md).

Core consumer focus 431 / 17.850 s passed; historical compatibility focus 43 /
10.130 s passed. Independent core 198 / 7.151 s (one Windows junction skip), actual
five view byte comparisons, existing-file refusal and FIFO/race probes passed.
Fixed15 fictional targets were actually recreated: nine changed one hash and six
were already correct; no other example bytes changed. Independent final 36 / 8.270 s (one Windows-junction skip), output-contract
seven-command journey and prior 61-command/fixed15 replay passed. Final focus 51 /
10.964 s passed (two skips); audit 588 / manifest 587 / grammar 293 passed.
First full 2337 / 207.170 s found one missing helper row in the non-CLI command
inventory. Added that exact documentation row; product/tests unchanged.
Corrected full: 2337 tests / 210.407 s PASS (two native-platform skips).
Corrected metadata: 15 / 10.916 s PASS (one skip); independent correction 15 /
12.002 s, repeated 61-command/fixed15 replay and corrected tree matched.
Only validation records and their manifest entries changed after full verification.
