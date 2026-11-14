# Validation record

Current release: `0.100.0-reviewed-decision-batch` (2026-11-14). This file is the
current snapshot; every dated entry since the 2026-11-02 release preparation is kept
verbatim, in order, in [docs/VALIDATION_HISTORY.md](docs/VALIDATION_HISTORY.md).

## What CI runs

GitHub Actions (`.github/workflows/tests.yml`) runs on every push to `main` and on
every pull request, on a matrix of `ubuntu-latest` and `windows-latest` with Python
3.10 and 3.12:

1. `python -m unittest discover -v` — the synthetic test suite in the `tests/` package,
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

## 2026-11-14 Reviewed decision-batch application and replay (0.100.0-reviewed-decision-batch)

The #33 batch path now has a separate exact-human-review assemble/verify tool.
Preview and application share one internal simulation, preserving full existing
single-record operational guards and ordinary receipt schemas. The preview remains
read-only. A completed separate import review binds original protocol, raw sheet,
target and implementation before assembly creates a detached candidate. Full replay
must match the entire application before any new protocol export. No original file,
existing position or unrelated assertion is modified. Application code bytes are
part of the target, so older previews require fresh review rather than rebasing.

Local Python 3.12 full suite: `Ran 2013 tests in 153.165s`, `OK (skipped=1)`.
Focused application/preview/export/navigation: 56 pass. Independent review ran new
application9 + existing preview/single-decision48 tests (57 total), found no blockers
and confirmed unchanged ENGINE_FILES. Audit: 428 files, pass; manifest, compileall,
Python 3.10 grammar, adapter/engine bytes and existing executable sh blocks pass.
Catalog: 26 routes, 117 help entrypoints. No test failures occurred in this increment.

The application CLI has at most one new destination per command. Complete flushed
same-directory temporary files are published by exclusive hard links, never by
replacement. Tests cover write/link failures with no final output and cleanup,
existing/symlink destinations, unsupported hard links, absent parents, full replay
tampering, stale implementation/review/context, duplicate/partial rows, shared
limits/budgets, second-step guard failure, old history prefixes and the verbatim
synthetic guide. Post-publication cleanup/stdout failures can leave complete output;
that uncertainty and the absence of ancestor-race guarantees are documented.

All examples are synthetic. Import review authorizes recording supplied choices,
not adjudication correctness, reviewer identity, reading, chronology or scientific
validity. The detached application must be retained for batch provenance.

