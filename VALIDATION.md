# Validation record

Current release: `0.137.0-supplied-output-disclosures` (2026-11-14). This file is the
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

Release: `0.137.0-supplied-output-disclosures` (2026-11-14).

Roadmap #44: optional supplied research-output disclosure records, current gate/item
context, and separate exact-input append/replay with explicit optional saved observations
and pre-disclosure bundles. RELEASED labels are not actual publication, permission or
scientific closure; NOT_READY coexistence is exposed without a new gate or rejection.
Existing gate logic, old records and source/Windows security boundaries are unchanged.

Prior49 actual CLI raw-byte baselines remain identical without disclosure records;
current native newline expectations are explicit. Exact named ENGINE additions and
optional summary blocks preserve historical baseline data. Saved artifact observations
are not live checks or authenticated engines; original attachment re-supply is required
for replay. Real previous artifact output was accepted after its synthetic file was
removed, while live_bytes_checked remains false. No source path is opened by intake.

Core independent review passed 35 tests / 5.370 s plus actual twelve old/new CLI byte
comparisons and binding/prefix probes. The eleven-command guide uses fictional saved
observations and an actual pre-disclosure ZIP. Full 2,313 tests passed in 198.435 s (one platform skip). Final independent
review passed 36 tests / 5.566 s and independently regenerated fixed15 targets
through seven prior guides / 61 CLI commands; all other old example bytes are
preserved. Audit 567 and manifest validation passed.
