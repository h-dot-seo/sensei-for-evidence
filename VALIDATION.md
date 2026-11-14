# Validation record

Current release: `0.135.0-canonical-research-zip` (2026-11-14). This file is the
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

Release: `0.135.0-canonical-research-zip` (2026-11-14).

Roadmap #54 standalone research ZIP core: bounded path/seekable-stream input,
fixed-name STORED regular-entry preflight, then existing manifest/engine/hash/
derivation validation and exact canonical archive-byte comparison. Noncanonical
recompression, metadata, comments and trailing bytes formerly accepted are now
rejected. This is consistency hardening, not a known-vulnerability claim. The
other seven archive modules and broad CLI sweep remain unchanged.

The existing inclusive uncompressed 50,000,000-byte total is preserved, with exact
derived 732-byte ZIP-header allowance for raw input. Create protocol input is bounded
to the same payload budget. Caller-owned streams support partial reads and retain
position/ownership. The builder function is byte-identical at source level; actual
previous47 generation for four protocols with the same recorded engine dictionary
produces identical ZIP bytes. Real release fingerprints still change, requiring
old archives' recorded implementation. No existing archive/review is rewritten.

Only research_bundle.py changes among old root modules; archive_safety.py is a new
ENGINE leaf. The original view baseline bytes are retained with one explicitly named
new helper fingerprint excluded alongside prior named changes. The prior47 protected
builder check is refined only for this intentional verifier change. Five existing
semantic-tamper helper sites use canonical ZIP metadata so original assertions still
reach payload/engine/derivation checks. New tests exercise preflight-before-read,
CRC, EOCD, exact repack, metadata/trailing rejection, bounded partial streams and
create/verify boundary symmetry. No extraction or authenticity/readiness promotion.

Core independent review passed 45 tests plus actual previous-module reconstruction
and five local-only header mutations. Fixed 15 synthetic target-hash maintenance
preserves all other bytes. Full 2,290 tests passed in 198.677 s (one platform
skip). Final independent review regenerated all 15 targets through seven existing
guides / 61 CLI commands and verified all other example bytes unchanged; audit
546 and manifest validation passed. No license/tag, network call or automatic
refresh tool is added.
