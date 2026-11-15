# Validation record

Current release: `0.150.1-contract-coverage-reference` (2026-11-15). This file is the
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

Release: `0.150.1-contract-coverage-reference` (2026-11-15).

Documentation-only correction: AGENT_CONTRACT previously copied a stale count of 156 unknown-effect commands. The actual catalog and `python sensei.py contract` report 205 commands, 44 reviewed effects and 161 rows with NOT_REVIEWED/null effects. The sentence now points to the command's current coverage counts instead of maintaining a second fixed unknown count. The existing 44-entry scope description is unchanged. No effect is newly reviewed, no execution permission is inferred, and no product, test, example, schema, workflow or existing historical record is changed. This is not a new feature increment.

The prior round63 main matrix passed eight jobs on attempt2: one Windows3.10 job reached its unchanged ten-minute limit on attempt1 and the isolated retry passed without code or timeout changes. This record does not hide that incomplete first attempt. Full/independent checks of this documentation-only revision are pending.

Initial full verification: 2406 tests in 246.566s, one release-record failure and two platform skips. The new history heading incorrectly used Latest change instead of the required dated release heading. Only that new heading was corrected; the existing release-record assertion, products, examples and old historical prefix were not changed. The earlier focused independent14-test pass did not cover release_record. Corrected full validation is pending.

Corrected full verification: 2406 tests in 250.986s PASS (two platform skips), exit 0. Focused release/contract/manifest23 tests in 2.673s PASS (one platform skip); independent initial14 tests in 11.421s and the corrected release-record check1 in0.012s PASS. The independent corrected tree was bb9d064b590594eba5de714e109ced0ab2ecc9c6. Exact original four-file scope remains: one AGENT_CONTRACT sentence, current validation, append-only history and manifest. Final record-only updates do not change products, tests, examples, workflows or schema. Remote PR/main CI remains separately verified.
