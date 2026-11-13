# Validation record

Current release: `0.95.0-ris-continuation` (2026-11-14). This file is the
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

## 2026-11-14 Declared RIS continuation intake (0.95.0-ris-continuation)

Roadmap #34(b) adds an independent parser/wrapper pair with an explicit versioned
dialect, untagged continuation and empty-paragraph rules. Byte provenance and
reconstruction verification preserve all fields, repetitions, framing and inert
values. Malformed tag-like lines, tabs, TY continuation and orphans fail closed.
Existing strict RIS modules, core ENGINE_FILES, native archive implementations,
adapter and all old walkthrough command blocks are byte-identical. Native archive
admission is explicitly deferred. Discovery exposes two new help entrypoints.

New synthetic tests cover grammar boundaries, BOM/CRLF/CR spans, resource limits,
tampering, cross-format rejection and four exact documented commands stopping at
the unfilled review template. No real data, provider claim, network request,
identity matching or scientific inference is introduced.

Local Python 3.12 full suite: `Ran 1960 tests in 137.817s`,
`OK (skipped=1)`, no failures/errors. The skip is the existing native-Windows
junction check on Linux. New focused suite: 10/10 pass. Combined strict RIS and
navigation regression before the final additional test: 66/66 pass. Independent
review found no blockers and independently reran the new tests plus dispatcher
regression (22/22). Publication audit (409 files), manifest, compileall, Python
3.10 grammar, UTF-8/LF and protected-byte checks passed.

The first full run (1959 tests) found one stale dispatcher catalog expectation:
the new wrapper had been added to discovery but not that exact expected list.
Updating the list, without weakening its equality check, resolved it. An early
focused run also exposed an overbroad tag-like pattern that rejected ordinary
hyphenated narrative; the grammar was narrowed to documented tag-shaped separators
and focused cases rerun. Neither correction changes the strict RIS parser.
All results are synthetic and local, not exporter compatibility, research validity,
source authenticity or a claim about remote CI. Native archive admission and
additional identity hints remain separate future work.
