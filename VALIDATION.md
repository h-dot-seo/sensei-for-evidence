# Validation record

Current release: `0.126.0-source-observation-contract` (2026-11-14). This file is the
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

Release: `0.126.0-source-observation-contract` (2026-11-14).

Extended the partial command-effects registry with exactly six local artifact/source/
passage observation operations. Reviewed coverage is32 of175;143 remain NOT_REVIEWED.
Negative reports may coexist with exit1 and an optional newly created JSON output;
text stdout does not change that stored JSON. Caught input/access errors remain a
separate stderr path. Unsupported secure source access, including native Windows,
still fails closed before opening the source root. No fallback, remote lookup,
permission inference, human approval or canonical state update is added.

Actual checkers and ENGINE_FILES are unchanged. The declaration reader accepts the
existing json_or_text negative channel and all root source bindings are refreshed.
Source drift still rejects the contract. Synthetic CLI tests cover successful/negative
source observations, output files, templates, malformed inputs and unavailable secure
access; scientific fidelity and human acceptance remain outside the observations.
Full2207 tests in184.505s passed (skip1). Independent17 tests plus seven negative
stdout-only JSON/text paths passed, with input/source files unchanged. Template-only
output wording was clarified afterward; final focused checks cover that metadata edit.
Audit505/manifest504 and Python3.10 grammar258 passed. All actual checker and28
ENGINE_FILES bytes are unchanged. No unresolved review blockers; Korean-locale
Windows, external-export compatibility and prior HTML visual QA remain unverified.
