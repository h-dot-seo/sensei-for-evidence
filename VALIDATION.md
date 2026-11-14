# Validation record

Current release: `0.131.0-supplied-patent-ledger` (2026-11-14). This file is the
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

Release: `0.131.0-supplied-patent-ledger` (2026-11-14).

Implemented roadmap #45 reader-adjusted path B as one standalone end-to-end
workflow: four supplied entity lists, explicit patent question/search basis, blank
templates, exact target, separately supplied import review, append-only candidate,
current-implementation replay and JSON/text observation view. No patent number
normalization, family inference, legal validity/currency determination, priority
claims, claim mapping or external service was added. Ordinary supplied protocols
only; adapter/bibliographic histories are refused, not stripped.

Existing109 root Python files and ENGINE_FILES remain byte-identical. Existing
run, allowlists, canonical decisions, bundle and readiness do not validate the new
ledger. Missing references in explicit queues and date comparisons are supplied
data observations, not legal findings or patent readiness. Candidate batch limit100
does not cap the whole ledger. Sources/records/reviewer labels remain unauthenticated.
New command effects stay NOT_REVIEWED:32 reviewed of184,152 unknown.

Focused15 tests include all four entities, exact review/stale/reject/tamper paths,
strict JSON/byte/depth limits, exclusive output, actual CLI error channels and the
seven-command documented synthetic ZZ rehearsal. Reviewer noted explicit null
question was treated as omission; a sentinel and API/real-CLI regressions now
reject explicit null while keeping omitted-question blank template behavior.
Initial full2252 run found three metadata regression failures: the current validation
release label was not updated and two tests still expected146 unknown command rows.
Those are corrected to the actual release and152; no implementation or effect review
was broadened. Corrected full2252 tests in183.145s passed (skip1). Independent final15 tests,
including the seven-command guide and explicit-null API/CLI probes, passed. Original
109 root modules remain byte-identical. Audit524/manifest523 and Python3.10 grammar268
passed. Final focused checks cover this record update. No unresolved review blockers.
Prior external compatibility, HTML visual QA and Korean-locale Windows limitations
remain; this fictional patent rehearsal does not verify live-provider interoperability
or legal utility. No license, gate/closure policy or tag decision was made.
