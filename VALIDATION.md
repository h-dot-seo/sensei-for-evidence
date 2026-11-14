# Validation record

Current release: `0.132.0-interpretive-challenge-origin` (2026-11-14). This file is the
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

Release: `0.132.0-interpretive-challenge-origin` (2026-11-14).

Implemented roadmap #100's optional schema 1 origin declaration, not a gate rule.
HUMAN_AUTHORED is self-declared, INTERPRETIVE_SIMULATION is not a scholar's view or
empirical evidence, and missing origin derives UNDECLARED without rewriting raw rows.
Exact optional shape, nullable declared hashes and the five-field bounded Persona
provenance contract are validated without opening sources or invoking a producer.
Human-origin declarations cannot carry package/consultation/model metadata.

Only challenge_links.py and research_bundle.py change inside ENGINE_FILES. Outside
the engine, challenge_intake.py/status/handoff expose supplied origin and optional
statement queues; synthesis/compare already preserve full rows. readiness_links.py,
its basis sentences, offline_adapter.py, allowlists, canonical decisions and closure
policy are unchanged. Old archives and applications require their recorded trusted
implementation; their hashes must not be rewritten to claim current verification.

The original43rd-increment twelve-view baseline file is byte-preserved. Its original
self-hash exclusions remain; exactly two top-level engine digest paths are substituted
with recorded prior values for whole JSON/text comparison. Four actual44th-increment
run/input/gate baselines recover the entire old result after removing only the newly
derived UNDECLARED per-row origin_kind. Explicit-origin comparisons preserve all
non-challenge engine fields and readiness rows/digests and old queue/count decisions.
Independent actual old-code recomputation confirmed the four baselines and prior
engine digests; nine mixed origin combinations preserved all non-challenge results.

Fifteen fixed public fictional walkthrough target_sha256 fields were updated from actual
target outputs after replay in a temporary copy. All other bytes/JSON values, including
reviewer, date, rationale and supplied decisions, remain identical. No real/user data
or review was changed and no public/automatic refresh tool was added. Existing challenge
guide's two blocks/ten commands and its test remain byte-identical. New origin guide
has its own ten-command actual CLI rehearsal. Initial full2263 tests in194.923s found five stale-target failures in later synthetic
import-review walkthroughs absent from the original ten-field inventory. Work paused
until the maintenance scope explicitly expanded to fifteen. Only the five additional
target_sha256 fields changed, preserving all other bytes and supplied assertions.
Corrected full2263 tests in196.398s passed (skip1). Independent final origin11
tests and five-journey-related61 tests passed; the full15-file raw-byte and remaining
JSON preservation checks passed. Earlier independent48+19 focused tests and actual
old-code/nine-origin-combination comparisons also passed. Audit529/manifest528 and
Python3.10 grammar269 passed. Final focused checks cover this record update.
No unresolved review blockers; existing external compatibility, HTML visual QA and Korean-locale Windows
limitations remain unverified. No new license, tag, gate or human judgment is selected.
