# Validation record

Current release: `0.130.0-map-context-views` (2026-11-14). This file is the
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

Release: `0.130.0-map-context-views` (2026-11-14).

Added explicit optional research-map sidecar context to status/handoff and paired
before/after map comparison. A separate section displays existing supplied record/event
statuses and literal changes, never changes readiness, queues, canonical decisions,
protocol has_changes or amendment exit decisions. Missing options leave no new fields.
This completes the explicit optional-view route of the standalone increment, not full
research-map or engine/bundle integration. Existing research_map.py and ENGINE_FILES
are unchanged; their standalone replay is not modified.

Twelve recorded default views over four synthetic fixtures retain complete JSON/text
apart from exact named top-level implementation digest entries: status self, handoff
status+self, compare self. Compare text displays that same digest, and only that value
is substituted for baseline comparison. No other field/text is excluded or normalized.
Optional views have explicit10MB sidecar and50MB joined output bounds. Tests cover
paired arguments, strict failures, stale records/events, supplied field changes,
added/removed/reordered IDs, actual three-CLI text/JSON journeys and normal amendment
mismatch JSON exit1. Contract coverage remains32 reviewed of178;146 remain unknown.
Full2237 tests in186.563s passed (skip1). Independent24 focused tests passed; the
12 default baselines were independently regenerated from the preceding release and
matched. A selected-work handoff also retains its entire original result outside the
explicit protocol-wide map context. Audit517/manifest516 and Python3.10 grammar264
passed. Final focused checks cover this record update. No unresolved review blockers.
External reference-manager compatibility, prior HTML visual QA and Korean-locale
Windows remain unverified.
