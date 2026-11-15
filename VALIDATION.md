# Validation record

Current release: `0.149.0-documentation-conformance` (2026-11-15). This file is the
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

Release: `0.149.0-documentation-conformance` (2026-11-15).

Roadmap common #102, Sensei-only local link/heading checks and exact classification of197 existing sh blocks, all block bytes preserved. Sixteen approved synthetic blocks execute77 actual argv commands without shell; one block parses two commands without product execution;19 blocks bind ten existing bespoke guide tests;161 are explicit generic-run exclusions, not claims of no other tests. Existing usage/help conformance stays separate. No product/ENGINE/example/schema/workflow changes.

Local new7/5.533s PASS, compact historical-proof7/5.376s PASS. The first exploratory runner expected amendment comparison exit1 but its supplied note correctly returns0; only the new expectation changed. Five historical relative-link targets lost one erroneous docs/ prefix with exact-offset and original/corrected-prefix proof; historical prose and all other bytes remain intact. Full/final independent validation pending.

Independent initial core7/5.506s PASS with actual prior61 protected279-file and197-block byte comparison. The reviewer identified unsupported Markdown dialects; an independent current-document search found none except initial SKILL.md YAML delimiters. New unsupported reference/HTML-comment-link/nested-destination/setext guards now fail rather than imply coverage; corrected8/5.837s PASS. Final focus23/18.230s PASS (one platform skip), audit640/manifest639. Full and final independent review pending.

Full2401/247.483s PASS (two platform skips). Final independent8/5.668s PASS, actual prior61 protected279 files/197 sh blocks and existing baseline JSON unchanged, exact five historical targets only, updated dialect counterexamples rejected. Current supported-syntax link observations1114 with zero failures; the earlier1112 count predates the two new documentation links. Independent tree84267596827b93575760d5980691e3e9063c4df9 matched; audit640/manifest639/Python3.10 grammar313 PASS. After this full run only these two final validation records and their manifest rows change. All other frozen bytes remain unchanged.
