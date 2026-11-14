# Validation record

Current release: `0.136.0-supplied-question-ledger` (2026-11-14). This file is the
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

Release: `0.136.0-supplied-question-ledger` (2026-11-14).

Roadmap #42 reader adjustment (a): optional supplied question records and separate
exact-target append/transition review. OPEN and NARROWED have an explicit transition
table; terminal labels and same-state renewal are rejected. Question labels are not
assessed answers. Root question, existing work/statements, readiness gates and all
prior judgments are unchanged. Optional views and bundle context expose labels and
STALE bindings without updating old records. External references are opaque labels/hashes.

Twelve actual previous48 CLI raw outputs are preserved without question records;
all 44 pre-label run baselines remain unchanged. Native Windows CRLF expectations
are explicitly recorded separately, with no runtime newline normalization. Historical
baseline files stay byte-identical; exact named new engine hashes/source additions
and optional bundle-summary block are isolated in regression tests.

Core independent review passed 33 tests plus actual previous48 CLI comparison and
empty-stage/review/input-preservation probes. The new twelve-command guide executes
for CSV/NBIB/RIS imports (36 commands). Full 2,302 tests passed in 202.213 s (one platform skip). Final independent
checks passed 35 and 26 focused tests, regenerated all fixed 15 target hashes
through seven existing guides / 61 CLI commands, and confirmed all other old
example bytes preserved. Audit 556 and manifest validation passed.
