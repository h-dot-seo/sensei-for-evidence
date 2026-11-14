# Validation record

Current release: `0.138.0-bounded-cli-inputs` (2026-11-14). This file is the
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

Release: `0.138.0-bounded-cli-inputs` (2026-11-14).

Roadmap #54: fifteen remaining CLI readers, nineteen supplied JSON input sites,
now enforce 50,000,000 bytes inclusive before parsing. Four old text readers retain
universal-newline/error-position semantics. Existing helper/ZIP and excluded CLI
bytes are unchanged. No gate, scientific decision, original record or permission
changes. See [CLI input boundaries](docs/CLI_INPUT_BOUNDS.md).

Core focused 36 / 9.647 s and final focused 44 / 9.107 s (one native-Windows
skip) passed. Independent core 57 tests, actual 60 old/new malformed-input byte
comparisons, seven guides / 61 commands and all fixed15 synthetic target checks
passed. Initial full 2321 / 208.583 s found one examples-only metadata inventory
error; that file was restored to previous bytes. Corrected full run: 2321 tests / 206.779 s PASS (one native-Windows skip).
Metadata correction focus: 21 / 0.454 s PASS (one skip); independent correction
review and repeated 61 guide commands / 15 target checks passed.
Publication audit 574 files and Python 3.10 grammar 289 files passed.
