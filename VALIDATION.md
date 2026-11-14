# Validation record

Current release: `0.134.0-bibliographic-assertion-continuation` (2026-11-14). This file is the
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

Release: `0.134.0-bibliographic-assertion-continuation` (2026-11-14).

Fixed roadmap #42 reader obstacle (4): existing challenges/readiness_assertions
were omitted from bibliographic enrichment, so even empty ledgers after a valid
CSV/NBIB/RIS import failed immutable-context validation. The only product change
adds exactly those two names to ENRICHMENT_FIELDS in bibliographic_integrity.py.
No validator, source-basis function, gate/closure policy, engine inventory or
canonical-data code changes. Existing immutable fields and unknown root additions
remain rejected; original bibliographic history and separate review requirements
are preserved. Old artifacts require their recorded trusted implementation.

Synthetic tests prepare all three real parser/import paths, then execute twelve
existing CLI commands per format (36 commands): challenge template/target/separate
review/assemble/verify, readiness template/target/separate review/assemble/verify,
status/readiness views and research bundle create/verify. Additional tests cover
empty/invalid ledgers, immutable/unknown context, declared origin/label coexistence,
stale targets and tampered records. The separate plain comparison control explicitly
binds its fictional challenge to its own changed source after provenance removal;
no actual imported protocol or retained review is renewed. All prior core validator
bytes are pinned by regression.

Exactly 15 existing fictional target-hash fields are maintained from actual guides,
with all other bytes/reviewer/date/decision values preserved. No actual human review,
user data, network access or automatic refresh tool is involved. Full 2,281 tests passed in 197.782 s (one platform skip). Independent 118 tests
and the 36-command three-format journey passed; seven existing guides/61 commands
independently regenerated all 15 synthetic targets exactly. Audit 541/manifest
540 passed; final source-bound focused checks cover this record update. Existing
external interoperability/visual QA limits remain unverified; no license or tag.
