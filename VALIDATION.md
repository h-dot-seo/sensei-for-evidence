# Validation record

Current release: `0.145.0-same-call-view-analysis` (2026-11-15). This file is the
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

Release: `0.145.0-same-call-view-analysis` (2026-11-15).

Roadmap #52 adjustment8: four non-engine views separate private same-call projections to avoid repeated engine analysis in handoff and synthesis. Public signatures/validation and CLI options, ENGINE/prisma_reports, validators, schema2, gates, queues and source bindings retain their meaning. There is no cache, external prevalidated input or persisted analysis. Actual old/current engine-call counts: handoff4→1 without reports/8→2 with reports; synthesis2→1/4→2. Standalone status/work remain1/2. No wall-time or general complexity guarantee. See [shared view analysis](docs/SHARED_VIEW_ANALYSIS.md).

Initial related45/1.393s PASS. New six tests/7.439s PASS including40 actual prior/current CLI paths with only four exact implementation-byte reads controlled, current unmodified fingerprints checked separately; actual old/new run counts, public validation, optional selections/map/negative paths, input/intermediate and repeated-result-mutation isolation. Historical compat37/22.303s PASS before the sixth counter test was added. Historical baseline JSON is preserved via exact four-file source reversal. Full/final independent checks pending.

Final focus68/43.817s PASS (one platform skip). Independent core54/8.806s PASS plus60 actual old/new malformed public-API comparisons with identical exception type/message. Actual seven guides/61commands regenerated all15 targets identically; every existing example byte is unchanged. Full/final independent validation pending.

First full2362/229.119s had one failure (two platform skips): the older synthesis index test counted500 visits rather than100 because the newly shared analysis exposed four pre-existing status traversals to its CountedRows. Product code was unchanged. The test now supplies an actually computed status result separately to isolate the original membership-index measurement, keeps the exact100-visit assertion and compares the full result with the unpatched snapshot. This is not a claim that the entire composed view traverses work once. Corrected full validation pending.

Corrected full2362/229.369s PASS (two platform skips). Corrected focus60/10.056s PASS; independent final49/22.912s (one skip) plus correction12/8.497s PASS. Independent actual old57/new58 counters cover every run-returned work list:100-work status400→400 visits, snapshot500→500 (old100+400 separate objects versus one shared500), handoff1000→600; report fixture with two work rows gives8→8,10→10,20→12. Counted outputs equal unpatched outputs. Thus index isolation does not hide increased whole-snapshot traversal; no general wall-time claim follows. Independent freeze31afc3d0820cb620e73417659d640e0d5033489f matched;61 guide commands/15targets and all example bytes unchanged. Audit616/manifest615/Python3.10 grammar303 passed. Only these final result records and their manifest rows change after full validation.
