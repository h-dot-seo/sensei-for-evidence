# Validation record

Current release: `0.143.0-shared-archive-preflight` (2026-11-15). This file is the
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

Release: `0.143.0-shared-archive-preflight` (2026-11-15).

Roadmap #54: consolidate seven existing ZIP metadata preflights in archive_safety without new acceptance, safety or format claims. Exact root8: existing ENGINE leaf plus seven collection/transition wrappers. Existing research check/read_bounded, build/verify function bodies and ENGINE filename sets remain unchanged. Wrapper body lines fall from102 to34 plus19 shared-helper lines (53 total, excluding seven imports). No runtime performance claim. See [shared preflight](docs/SHARED_ARCHIVE_PREFLIGHT.md).

Initial three new tests had seven failures because a controlled old-source read was erroneously reversed twice, and one error assuming every transition module exposed an ENGINE_FILES constant. Fixed test setup only: load previous modules before controlling the eight implementation-byte reads, and compare actual implementation key sets where no constant exists. Corrected core3 /2.429s PASS. Old/new metadata comparison covers15 variants under two size-callback conditions across seven functions (210 pairs); an earlier progress estimate said14 variants and is corrected here.

Existing bundle and history focus266 /70.271s PASS (one platform skip). Independent core217 /52.545s PASS plus2100 randomized metadata comparisons against actual previous55 sources, including exception classes/messages, callback ordering and no payload reads. Seven actual old/current archives have identical bytes and cross-replay under controlled prior implementation reads; actual new-release hashes still change. All15 fixed fictional target hashes were actually regenerated with seven guides/61commands; other example bytes unchanged. Historical baselines are retained with exact named source/hash reversals. Full/final independent validation pending.

Full2350 /219.585s PASS (two platform skips). Final focused39 /25.847s PASS (one skip). Independent final29 /10.200s, actual seven guides/61commands and15 fixed target recreations passed; hash-only/other example bytes and historical baseline JSON preservation verified. Audit604/manifest603 and Python3.10 grammar298 passed. Independent frozen tree6e3a8fc09f7490cb7808283f13a47b38558db520 matched exactly. Only these validation results and corresponding manifest entries change after full verification.
