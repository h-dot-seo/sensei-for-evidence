# Validation record

Current release: `0.96.0-blank-screening-sheet` (2026-11-14). This file is the
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

## 2026-11-14 Blank screening-position sheet export (0.96.0-blank-screening-sheet)

First bounded #33 increment: a new export-only spreadsheet scaffold reuses the
existing screening_review.template targets. Human assertion cells remain empty;
formula-safe display IDs stay distinct from literal JSON IDs and source hashes.
Optional retained-column selection is literal, ordered and separate from human
locator fields. No title inference, edited-sheet intake, screening decision,
review supersession or archive/schema change is introduced. Current source hashes
do not refresh old assertions. Documentation explicitly keeps the intake gap open.

Existing core ENGINE_FILES, all parsers/intake wrappers, native archive modules,
adapter, fixed fixtures and executable guide blocks remain unchanged. Discovery
adds one export help entrypoint (26 routes, 110 entrypoints). New guide commands
are tested with tokenization before host-path substitution, including Windows.

Local Python 3.12 full suite: `Ran 1971 tests in 138.846s`,
`OK (skipped=1)`, no failures/errors. The skip is the existing native-Windows
junction check on Linux. New export tests plus screening review, dispatcher and
navigation: 82/82 pass, also independently rerun. Independent review found no
blockers and additionally checked CR/LF/quote-bearing ID round trips and output
refusal. Publication audit (412 files), manifest, compileall, Python 3.10 grammar
and protected-byte checks passed. Synthetic cases cover escaped/literal ID
collisions, exact source targets, stale prior assertions, literal ordered display
values, no network use, row/byte bounds, blank manual displays, empty protocols,
invalid inputs, exclusive paths and the exact guide command.

No test failure occurred during this increment. These are local synthetic checks,
not researcher identity, source reading, eligibility assessment or live-provider
compatibility. Edited-sheet intake and reviewed append-only positions remain the
next separate increment; this release only exports a blank scaffold.
