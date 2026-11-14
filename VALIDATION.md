# Validation record

Current release: `0.105.0-json-rejection-harness` (2026-11-14). This file is the
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

## 2026-11-14 Bounded JSON rejection test harness (0.105.0-json-rejection-harness)

Only the 24-case JSON rejection loop uses the existing trusted serial harness.
Original duplicate/nonfinite/nonobject/surrogate cases and all rejection assertions
are preserved, with source-byte preservation added. Four real subprocess error
smokes compare exact output/exit to the harness. Existing ASCII environment/Unicode,
normal CLI roundtrips, bundle errors and documented walkthroughs stay subprocess.
All production Python, ENGINE_FILES, shared harness and CI workflow bytes unchanged.

Before: JSON loop0.840s, sampled batch bundle invalid-input0.493s. Reproducible
24-case byte/exit/source/output/state equivalence passed three alternating runs:
subprocess0.762/0.734/0.741s versus in-process0.063/0.056/0.056s. Retained four-process
smoke costs0.176s locally. These small local savings are not a claim of proportional
suite/CI acceleration; larger batch/dispatcher bottlenecks remain out of scope.
See [runtime guide](docs/TEST_RUNTIME.md) for commands and process-isolation limits.

Full local suite: 2061 tests in 149.247s, OK (one platform skip). Focused and
independent JSON/harness tests: 14 pass. Independent 24-case benchmark also passes
all equivalence and preservation checks (subprocess0.7594s vs in-process0.0639s).
No blockers. Audit450 files, manifest, compileall, Python3.10 grammar and unchanged
production/helper/workflow/old executable blocks pass. Final checkout, JSON/harness
and navigation checks rerun after documentation/manifest finalization.
