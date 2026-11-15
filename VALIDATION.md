# Validation record

Current release: `0.146.0-retained-bundle-descriptors` (2026-11-15). This file is the
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

Release: `0.146.0-retained-bundle-descriptors` (2026-11-15).

Roadmap #62 adjustment1 separate M: a new non-engine reader describes the unverified manifest of seven explicit schema1 collection/transition ZIP families. It reads only manifest.json, reports exact received ZIP SHA-256 and current implementation differences, and never performs payload hashing, replay, canonical verification, extraction or network access. Existing eight builders/verifiers, research descriptor, root products, ENGINE and all examples remain byte-identical. Supplied claims never become readiness or authentication. See [retained-bundle reader](docs/RETAINED_BUNDLE_DESCRIBE.md).

Initial eight reader tests/1.478s passed. Expanded first focus19/4.152s failed two test assumptions: a byte-pattern search selected an inner ZIP central directory instead of the outer one, and a historical root inventory needed the explicitly added reader excluded. The next20/4.301s had one test expectation error: truncating an outer EOCD may expose an inner directory, which the existing preflight refuses with ValueError rather than BadZipFile. Tests now address the outer directory and accept either refusal channel for truncated ZIPs; no product relaxation. Corrected focus20/4.591s PASS. Full and independent final results pending.

First full2373/233.775s completed with two failures (two platform skips): the new tagged descriptor was absent from the static record registry, and an older state-boundary test retained the previous156 unknown-command count. Added only the descriptor registry/table row and updated the explicit count to157; existing command effects remain unchanged. Independent review also corrected documentation to describe aggregate entry ceilings, not individual binding/source cardinality verification. Product code remains frozen and unchanged. Corrected full validation pending.

Corrected full2373/229.678s PASS (two platform skips). Corrected focus34/4.186s PASS (one skip). Independent final45/6.477s PASS (one skip), seven actual retained-family manifest-only reads plus35 malformed probes and21 new guide CLI calls; seven existing guides/61commands reproduced all15 targets unchanged. All prior root/ENGINE/examples/schemas and baseline JSON bytes remain unchanged. Independent freeze edb71ce60951560bbd39b38d2020c6a62ffb1591 matched. Registry preserves all200 previous command rows and adds one effects-null entry (44 reviewed/157 not reviewed); record registry adds only the unverified descriptor. Audit620/manifest619/Python3.10 grammar305 passed. Only these two final result records and their manifest rows change after full validation.
