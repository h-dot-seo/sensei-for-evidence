# Validation record

Current release: `0.88.0-implementation-check` (2026-11-10). This file is the
current snapshot; every dated entry since the 2026-11-02 release preparation is kept
verbatim, in order, in [docs/VALIDATION_HISTORY.md](docs/VALIDATION_HISTORY.md).

## What CI runs

GitHub Actions (`.github/workflows/tests.yml`) runs on every push to `main` and on
every pull request, on a matrix of `ubuntu-latest` and `windows-latest` with Python
3.10 and 3.12:

1. `python -m unittest discover -v` — the synthetic test suite in the `tests/` package,
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

## 2026-11-10 Implementation revision inspection (0.88.0-implementation-check)

Added the detached read-only `implementation_check.py inspect` diagnostic, outside
ENGINE_FILES, with nested engine/implementation/adapter hash declarations, escaped
JSON pointers, bounded strict JSON and ZIP-manifest input, safe bare source names,
shared cross-platform link-like rejection and independent supplied-manifest matching.
It prints complete per-file differences before exit 1 and candidate documented verify
usage without executing selected source code. Matching bytes are not verification,
authentication, provenance, input replay or scientific readiness. No engine module,
adapter, protected guide command block or bound walkthrough fixture changed.

The new executable guide uses fictional review-demo data. Sixteen focused synthetic
tests cover all hash shapes, malformed declarations/JSON, missing and changed sources,
conflicting declarations, byte/node/hash limits, ZIP duplicate/oversized manifests,
links/reparse rejection, independent manifest matching, safe text and exit status,
self-inclusion of current implementation sets and exact guide replay.

Local Python 3.12.14 validation: `python -m unittest discover -q` ran 1,854 tests
(1,838 existing + 16 new), OK with one platform skip and no failures or errors.
Focused inspector and dispatcher validation ran 28 tests, OK. `compileall`,
`verify_manifest.py` and `audit_publication.py` passed. The guide was also replayed
manually outside the checkout: all 28 recorded engine files and the supplied
publication manifest matched. UTF-8 without BOM and LF were checked for changed files.
No live service, scientific adequacy, source authenticity, complete census or release
provenance is claimed.


- 2026-11-08 Test package and dispatcher (`0.87.0-test-package-and-dispatcher`): the 106
  test modules moved from the repository root into the `tests/` package (79
  repository-root references and 28 cross-test imports adjusted; the CI command is
  unchanged), and the standard-library dispatcher `sensei.py` lists the root scripts
  and the operator-handoff routes or runs one root script exactly as `python <script>`
  does. Implementation modules stay flat at the root because fixtures bind
  `offline_adapter.py` and engine bytes; no fixture, guide command block or documented
  command changed. Local runs on native Windows with Python 3.15: before the move
  `Ran 1826 tests in 402.834s`, after `Ran 1838 tests in 450.444s` (1826 + 12 dispatcher tests),
  both `FAILED (errors=1, skipped=45)` with only the pre-existing Python 3.15
  junction-test TypeError in `tests.test_verify_manifest`, left as is.
  Full entry: [test package and dispatcher](docs/VALIDATION_HISTORY.md#2026-11-08-test-package-and-dispatcher-0870-test-package-and-dispatcher).
