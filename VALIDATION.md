# Validation record

Current release: `0.151.0-offline-pubmed-partition` (2026-11-16). This file is the
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

Release: `0.151.0-offline-pubmed-partition` (2026-11-16).

New standalone offline PubMed window reconciliation: explicit unchanged discovery specs, inclusive calendar gaps/overlaps/outside windows, exact separately supplied artifact replay and preserved occurrence positions across windows. Counts, translation differences and calendar coverage never establish completeness, source authenticity, human review or fetch approval. Local discovery caps remain unchanged; no fetch, automatic subdivision, deduplication or merged intake is added. Existing root modules, ENGINE_FILES, all examples/schema/workflows and historical baseline JSON are unchanged. Two new command rows remain NOT_REVIEWED/null effects; existing 44 reviewed rows are not expanded.

Focused new/existing PubMed checks: 25 tests in 1.088s PASS. Documentation/contract checks: 23 tests in 25.781s PASS. Initial focused bound test had one incorrect expectation: a report-sized limit was used to assert whole review success even though the supplied input was larger. Corrected the test to isolate the exact inclusive serialization boundary; the product behavior was not weakened. Independent core and full-suite results remain pending. No live API calls or real research inputs were used.

Initial full verification: 2413 tests in 324.575s, 11 failures and two platform skips. Eight historical inventory assertions did not yet explicitly exclude the newly added standalone pubmed_partition.py, one record-shape inventory lacked its new report mode, and two current unknown-effect counts still expected 161 rather than 163. Corrected these exact declarations: one new module name only in historical root sets (and its verified current hash in the historical catalog comparison), one new navigation record, and 207 total/44 reviewed/163 unknown command counts. Existing source-change proofs, baseline JSON and every old byte/hash assertion remain unchanged. Six documented-block source pins track only these exact test-source edits; existing shell blocks are unchanged. New proof/test independently checks all 279 prior root/example/schema/workflow files byte-for-byte and global ENGINE exclusion. Corrected focused83 tests in44.334s PASS. Core independent7 tests plus 200 randomized day-set comparisons and blocked socket/SQLite checks passed; core review did not cover these later inventory changes. Corrected full and final independent review are pending.

Corrected full verification: 2414 tests in 330.443s PASS (two platform skips). Final independent review passed 43 focused tests, confirmed manifest648/audit649 and exact freeze1441604f8298dc34cd1926262087893b6b3ef1d0, all 279 protected files, all prior baseline JSON and all 200 existing shell blocks unchanged. Existing 205 command rows are unchanged plus two null-effect rows; one descriptive record row is added. Additional socket-blocked boundary probe accepted 100 explicit windows (4950 pairwise overlaps, 466184 canonical report bytes) and refused 101; this is not a performance guarantee. After this full run only current validation/history result text and corresponding manifest entries are updated. Remote draft/PR matrix/main verification remains a separate stage; no live API calls or real research data were used.

Approved CI operating-budget correction after draft PR70: the first exact-head matrix had seven successful jobs and Windows3.10 cancelled at the unchanged ten-minute job boundary. Its log nevertheless completed all2414 tests in539.684s (48 Windows platform skips), audit649 and manifest verification before cleanup. One isolated retry was also cancelled at ten minutes, during the final existing work_transition_context journey; it has no full summary and did not run audit/manifest. These two outcomes are not called an eight-job pass. The eight new partition tests passed in both attempts. Local two skips and Windows48 platform skips are different configurations.

Both Windows3.10 attempts used Python3.10.11/image20261103.298.1; setup-python took46/45seconds. First-attempt unit-step durations across eight jobs averaged366.5seconds (Windows514seconds); Windows3.10 consumed46seconds setup +541seconds unit step +17seconds other work =604seconds total. The recorded 539.684seconds is the unittest summary, not the whole job. This evidence supports a job-wide budget issue, not a demonstrated assertion failure; it does not explain all host timing variability or promise future duration.

With explicit owner-delegated approval, change only the job timeout from10 to20minutes. No matrix row, runner label, trigger, cancellation scope, action pin, permission, credential persistence, network/secret/billing setting, test command, skip or failure handling is changed. This is an operating-budget correction, not a test relaxation or product optimization. Existing product/ENGINE/example/schema bytes remain unchanged. The workflow is the sole explicit exception to the earlier workflow-byte-preservation scope: a test-only helper asserts its exact new SHA, reverses only that one timeout line, and verifies the exact prior SHA against unchanged historical JSON. The CI oracle requires20minutes and a new full-workflow delta assertion protects all other bytes. Focused27 tests in8.005s passed; new-head full, independent difference review and complete remote CI remain pending. No additional retry of the old cancelled head is performed.

CI-budget correction validation: new full2415 tests in329.681s PASS (two local platform skips), exit0. Independent28 tests in8.740s PASS verified exact workflow-only timeout delta, all prior baseline JSON/product/example/schema bytes, and fail-closed historical reversal for unrelated workflow changes. Independent tree370b1f30d76cf6de02b039849d30a850fe3fba13 matched manifest649/audit650. After that freeze only these two result records and manifest rows change. This local result does not replace exact new-head eight-job remote CI, which is required before merge; prior cancelled attempts remain explicitly incomplete as recorded above.
