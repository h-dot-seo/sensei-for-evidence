# Validation record

Current release: `0.104.0-test-cli-harness` (2026-11-14). This file is the
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

## 2026-11-14 Test-only CLI help harness (0.104.0-test-cli-harness)

One 129-entry help-catalog loop now uses a serial trusted-test runpy harness. All
production Python/ENGINE_FILES remain unchanged. All existing actual-process CLI,
JSON rejection, environment, dispatcher, guide and journey checks remain intact.
The harness restores argv/path/streams/cwd/environment; it does not simulate process
isolation, module cache isolation, startup, signals or timeouts. New contract tests
compare bytes/exit behavior against subprocess and verify exceptional restoration.

Opt-in full-catalog benchmark: all 129 entries match returncode/stdout/stderr across
three alternating-order runs. Subprocess 5.945/5.183/5.167 seconds, in-process
0.465/0.444/0.426 seconds on local Python 3.12.14/Linux. No timing assertions or
claims of proportional full-suite/Windows improvement. [Runtime guide](docs/TEST_RUNTIME.md)
records the reproducible command and retained coverage. Prior PR21 Windows3.10 job
452 seconds/test385; Windows3.12 job368/test354. Inspect slow tests when Windows
jobs exceed six minutes; class-fixture costs are absent from unittest durations.
CI adds --durations25 only on Python3.12; ten-minute timeout stays unchanged.

Full local Python3.12 suite: 2060 tests in 149.919 seconds, OK (one platform skip).
Prior local full run: 2053 tests in 155.178 seconds; new contract coverage adds seven
tests. These sequential observations are not a controlled whole-suite speed claim.
Focused and independent harness/navigation: 31 pass. Independent complete-catalog
benchmark also matched bytes/exit for all129 entries (5.099s vs0.440s). No blockers.
Audit448 files, manifest, compileall and Python3.10 grammar pass; every production
root Python file and existing executable sh block is byte-preserved. Final checkout
and focused regression checks rerun after validation-document/manifest update.
