# Validation record

Current release: `0.142.0-bounded-json-depth` (2026-11-15). This file is the
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

Release: `0.142.0-bounded-json-depth` (2026-11-15).

Roadmap #95: the shared strict decoder explicitly accepts at most128 containers (root depth0 through127; scalar leaves are not containers). JsonNestingError distinguishes explicit count from interpreter decoder capacity. Four bounded view/state CLIs retain input-too-complex classification; all other root sources, canonical encoding, numeric/duplicate/surrogate policies and scientific gates are unchanged. Deeper previously accepted inputs now reject intentionally. Existing artifacts need their old recorded implementation. See [strict JSON depth](docs/STRICT_JSON.md).

Core seven tests / 1.444 s passed. Initial synthetic success comparison incorrectly used a protocol without reports for every reporting command; replaced the new test input with the existing report protocol. Actual prior/current audit and search-manifest outputs expose the changed json_io digest; allowed only that named field, not arbitrary output differences. Initial compatibility focus65 /19.794s found one historical synthesis-review output also exposes a changed CLI-reader hash. Extended the named exception list to the exact five source fields; historical baseline JSON data remain untouched. Corrected compatibility65 /19.686s PASS (one native-platform skip).

Independent core21 /2.870s PASS plus705 separate depth-oracle cases, a200,000 bracket-character string and100,000-level rejection. The independent probe initially assumed lowering Python recursionlimit controlled the C decoder identically; that assumption did not hold and was discarded, not treated as a product failure. Fixed15 fictional targets were actually recreated by seven guides/61commands and changed one target hash each; all other old example bytes unchanged. Full and final independent validation pending.

Full 2347 tests / 213.763 s PASS (two platform skips). Final focus47 /16.677 s PASS (one skip); audit598/manifest597 and Python3.10 grammar296 passed. Independent final55 /14.761 s, actual seven guides/61commands and15 regenerated targets passed: exactly one hash field per fixed fictional example, all other bytes retained. All prior baseline JSON files are preserved; independent tree045dd0297af5ad7fd8ac5ade48e69632bc21a525 matched exactly. Product/test/metadata frozen; only validation results and manifest entries are updated after the full run.
