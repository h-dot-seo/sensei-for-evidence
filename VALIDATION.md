# Validation record

Current release: `0.86.1-documentation-restructure` (2026-11-08). This file is the
current snapshot; every dated entry since the 2026-11-02 release preparation is kept
verbatim, in order, in [docs/VALIDATION_HISTORY.md](docs/VALIDATION_HISTORY.md).

## What CI runs

GitHub Actions (`.github/workflows/tests.yml`) runs on every push to `main` and on
every pull request, on a matrix of `ubuntu-latest` and `windows-latest` with Python
3.10 and 3.12:

1. `python -m unittest discover -v` — the synthetic test suite, including the tests
   that execute the documented walkthrough command blocks exactly as written.
2. `python audit_publication.py` — the limited public-file/type/secret-pattern scan.
3. `python verify_manifest.py` — the complete published inventory against exact
   checkout bytes.

Actions are commit-pinned, token permissions are read-only, checkout does not persist
credentials, and no secrets or deployment steps are used. The published head's matrix
result is the public Actions history of this repository; this file does not restate it.

## How to verify locally

From the repository root, with Python 3.10 or later and the standard library only:

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
written inside the checkout. `python -m compileall -q .` must stay clean.

## What this record does not claim

The tests exercise generic code on entirely fictional fixtures. They do not evaluate
scientific fidelity, literature coverage, source authenticity, reviewer independence,
guideline currency or clinical applicability, and no live PubMed request is part of the
suite. The publication scanner is not a complete secret detector, anonymizer or legal
clearance tool, and a passing manifest proves byte identity, not authorship or
redistribution rights. Local test results do not establish that a remote publication
succeeded; the public CI history is the record of published heads.

## Latest change

- 2026-11-08 Documentation restructure (`0.86.1-documentation-restructure`): README
  reduced to one screen with a command table and documentation index; the full command
  reference, workflow narratives and a Korean guide moved to `docs/COMMANDS.md`,
  `docs/WORKFLOWS.md` and `docs/README.ko.md`; this record became a snapshot and its
  history moved to `docs/VALIDATION_HISTORY.md`. No code path, test or fixture changed.
  Local run on native Windows with Python 3.15: `Ran 1826 tests in 463.922s`,
  `FAILED (errors=1, skipped=45)`; the one error is the pre-existing Python 3.15
  junction-test TypeError in `test_verify_manifest`, left as is.
  Full entry: [documentation restructure](docs/VALIDATION_HISTORY.md#2026-11-08-documentation-restructure-0861-documentation-restructure).
