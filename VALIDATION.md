# Validation record

Current release: `0.93.0-checkout-smoke-check` (2026-11-10). This file is the
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

## 2026-11-10 Bounded checkout smoke check (0.93.0-checkout-smoke-check)

Added `sensei.py check` for a read-only first-hour checkout check. The strict
publication verifier is unchanged: listed-byte drift, missing files, malformed
metadata and unsafe entries fail. Ordinary unlisted additions warn only in this
smoke command; strict publication verification still rejects them. Only listed
Python sources are compiled in memory, then one synthetic status fixture must
retain NOT_ESTABLISHED and NOT_READY. Bytecode writes are disabled, the status
subprocess has a 30-second timeout, and inventory/syntax failure skips later steps.
This checks consistency with the local manifest, not publisher authentication.

English/Korean quick starts now begin with the smoke command; full tests and
maintainer audit/manifest checks remain separate and required. Direct scripts
remain the primary form. Caller-relative input/output paths and repository-relative
guide examples are distinguished explicitly. The new guide and English README
quick-start block are replayed by tests, with Korean command-block parity asserted.
The release header is advanced from the stale 0.91 label through the actual 0.92
base to 0.93. No packaging, license, Python floor, engine, adapter, existing fixture
or protected executable guide-block changes are included.

Local Python 3.12.14: focused dispatcher/smoke tests reported `Ran 20 tests in
13.185s`, `OK`, no skips or failures. The full suite reported `Ran 1943 tests in
156.945s`, `OK (skipped=1)`, no failures/errors; the skip is the existing native
Windows junction test on Linux. Coverage includes untouched checkout/caller files,
no new bytecode, tracked drift/missing files, invalid manifests and verifier imports,
unlisted invalid Python, unsafe links, listed syntax failure, bad status JSON/labels,
nonzero exit, timeout, caller-relative input and executable documentation replay.

A separate smoke demonstration passed in 0.602s over 201 manifest-listed Python
files. This is an observation, not a universal runtime guarantee; inventory cost
scales with the checkout and additions. Compileall, Python 3.10 grammar parsing,
UTF-8/LF, exact engine/adapter and protected guide-block comparisons, manifest and
publication audit passed. These are local synthetic results, not remote CI results,
research validation, scientific sufficiency or evidence of Windows execution.

## 2026-11-10 Status ZIP-error integration (0.90.0-status-markdown)

Integrated the upstream detached implementation-inspector correction before the
first publication of the status-Markdown increment. DEFLATE and LZMA ZIP-manifest
decoder failures now produce the existing sanitized INVALID report and exit 1 in
JSON and quoted text, without a traceback; existing BZIP2 error handling remains.
Four additional synthetic tests cover actual corrupt compressed bytes with valid
ZIP directories, input nonmutation and valid stored/DEFLATE/BZIP2/LZMA archives.
The status renderer, count crosswalk, engine, adapter and bound fixtures are unchanged.

Local Python 3.12.14 integration validation: `python -m unittest discover -q`
reported `Ran 1905 tests in 157.292s`, `OK (skipped=1)`, with no failures/errors.
The only skip is the existing native-Windows junction test. Focused inspector,
dispatcher and status validation ran 56 tests in 10.628s, OK without skips.
Compileall, regenerated manifest and publication audit passed. Integrated inspector
code/tests exactly match the upstream correction. Status-renderer code/tests/guide,
crosswalk, engine, adapter, fixtures and existing guide command bytes are unchanged.
The release remains 0.90.0-status-markdown. This fix does not establish artifact
verification, source authentication or scientific adequacy. Census remains
NOT_ESTABLISHED and readiness remains NOT_READY.

## 2026-11-10 Supplied-data status Markdown (0.90.0-status-markdown)

Added `views_export.py status` as a detached read-only rendering of the unchanged
`research_status.status()` result. Fixed-label integer/null count tables accompany
all status fields, optional retrospective records and complete queues. Supplied
values use quoted JSON lines inside backtick fences longer than their contents;
control/format and Unicode line separators cannot escape those blocks. Missing
stages remain distinct from empty lists and zero. No join, pointer or decision is
invented. No engine, adapter, protected guide block or bound fixture changed.

Twenty-four synthetic tests cover complete status preservation across protocol
examples, unknown/empty stages, nested pointers, hostile Markdown/control strings,
long fences, deterministic bytes/key permutations, no mutation/network/clock,
implementation/output hashes, compact receipts, schema/count rejection, strict
JSON, all three size bounds, existing paths, Windows dangling links and exact guide
replay. The guide was also run separately with ASCII-configured stdout.

Local Python 3.12.14: focused status tests ran 24 tests in 2.221s, OK with no skips.
`python -m unittest discover -q` ran 1,901 tests in 153.369s, OK (skipped=1),
with no failures/errors; the skip is the existing native-Windows junction test.
Compileall, regenerated publication manifest and publication audit passed. All 305
existing Python/example files and all existing guide sh blocks stayed byte-identical.
No Markdown renderer compatibility, source authentication, scientific sufficiency,
PRISMA figure, completed review or authorized sharing is established. Census stays
NOT_ESTABLISHED and conclusion stays NOT_READY. Real files and receipts are private.

## 2026-11-10 Native count crosswalk (0.89.0-prisma-count-crosswalk)

Added `prisma_flow_template.py` as a separate read-only derivation of the unchanged
PRISMA audit. It writes one exclusively created native CSV, not an official or
import-compatible external template. Search arms are supplied by input index;
unknown arms and unsupported rows stay blank. Exact-ID repeats and screened counts
are blank without an explicit opt-in. Missing report stages remain distinct from
supplied empty ledgers. Receipt JSON/text retain every mapping, plan/page issue,
pending node, mechanical count difference and implementation/CSV fingerprint.
No engine, adapter, protected walkthrough or bound fixture changed.

Twenty-two synthetic tests cover expected cells, nonaggregation, optional IDs,
blank-versus-zero, pending states, incomplete/page issues, formula escaping,
control-safe text, deterministic hashes/nonmutation, invalid assignments, strict
JSON, input/CSV/stdout limits, exclusive output, dangling links and the documented
rehearsal. The guide was also executed separately with ASCII-configured stdout.

Local Python 3.12.14: final `python -m unittest discover -q` ran 1,876 tests,
OK (skipped=1), with no failures/errors. Focused crosswalk tests: 22 passed.
`compileall`, publication manifest verification and publication audit passed.
No external template compatibility, source authentication, completed review,
scientific validity or independent deduplication is claimed. No third-party template
text or external tool is included. Census stays NOT_ESTABLISHED; conclusion stays
NOT_READY. Keep real source labels, reasons, CSVs and receipts private.


## 2026-11-10 Implementation revision inspection (0.88.0-implementation-check)

Added the detached read-only `implementation_check.py inspect` diagnostic, outside
ENGINE_FILES, with nested engine/implementation/adapter hash declarations, escaped
JSON pointers, bounded strict JSON and ZIP-manifest input, safe bare source names,
shared cross-platform link-like rejection and independent supplied-manifest matching.
It prints complete per-file differences before exit 1 and candidate documented verify
usage without executing selected source code. Matching bytes are not verification,
authentication, provenance, input replay or scientific readiness. No engine module,
adapter, protected guide command block or bound walkthrough fixture changed.

The new executable guide uses fictional review-demo data. Sixteen focused synthetic
tests cover all hash shapes, malformed declarations/JSON, missing and changed sources,
conflicting declarations, byte/node/hash limits, ZIP duplicate/oversized manifests,
links/reparse rejection, independent manifest matching, safe text and exit status,
self-inclusion of current implementation sets and exact guide replay.

Local Python 3.12.14 validation: `python -m unittest discover -q` ran 1,854 tests
(1,838 existing + 16 new), OK with one platform skip and no failures or errors.
Focused inspector and dispatcher validation ran 28 tests, OK. `compileall`,
`verify_manifest.py` and `audit_publication.py` passed. The guide was also replayed
manually outside the checkout: all 28 recorded engine files and the supplied
publication manifest matched. UTF-8 without BOM and LF were checked for changed files.
No live service, scientific adequacy, source authenticity, complete census or release
provenance is claimed.


- 2026-11-08 Test package and dispatcher (`0.87.0-test-package-and-dispatcher`): the 106
  test modules moved from the repository root into the `tests/` package (79
  repository-root references and 28 cross-test imports adjusted; the CI command is
  unchanged), and the standard-library dispatcher `sensei.py` lists the root scripts
  and the operator-handoff routes or runs one root script exactly as `python <script>`
  does. Implementation modules stay flat at the root because fixtures bind
  `offline_adapter.py` and engine bytes; no fixture, guide command block or documented
  command changed. Local runs on native Windows with Python 3.15: before the move
  `Ran 1826 tests in 402.834s`, after `Ran 1838 tests in 450.444s` (1826 + 12 dispatcher tests),
  both `FAILED (errors=1, skipped=45)` with only the pre-existing Python 3.15
  junction-test TypeError in `tests.test_verify_manifest`, left as is.
  Full entry: [test package and dispatcher](docs/VALIDATION_HISTORY.md#2026-11-08-test-package-and-dispatcher-0870-test-package-and-dispatcher).

## 2026-11-10 Windows crosswalk output correction (0.89.0-prisma-count-crosswalk)

The first PR CI run exposed a real Windows difference: opening a dangling symlink
with `xb` can create its missing target. The new writer now uses the existing
intake convention of `lstat` rejection before exclusive creation. A platform-neutral
regression also verifies that existing entries and inspection errors prevent any
open. The original Windows symlink test remains enabled, not skipped or weakened.
Stable output paths are required; concurrent replacement and ancestor aliases are
not a supported security boundary. No existing engine or intake module changed.

Focused crosswalk tests: 23 passed. Final local full suite: 1,877 tests, OK
(skipped=1), no failures/errors. Compileall, publication audit and regenerated
manifest passed. The failed first CI run is retained as evidence; the corrected
published head requires a separate four-platform CI result.

## 2026-11-10 Supplied-accounting flow text (0.91.0-accounting-flow)

Added `views_export.py flow --format mermaid` with a detached, bounded Mermaid
text serialization of existing audit nodes and partition checks. Each partition
uses local aliases in a separate labelled group; repeated quantities are not
additive. Two dashed unit bridges explicitly reject count conservation, while
study/result nodes outside partitions stay detached. Optional report-study
membership partitions follow the supplied audit. Missing stages and plans remain
not supplied rather than zero. Labels contain only fixed vocabulary and counts,
not supplied questions, identifiers, reasons or locators. The visible boundary
retains NOT_ESTABLISHED/NOT_READY; validated fingerprints appear in comments.

The new serializer does not enter ENGINE_FILES. Engine, adapter, fixture bytes,
existing guide sh blocks and the seven-file bundle contract are unchanged. The
existing status Markdown document remained byte-identical (10,777 bytes) in the
synthetic fixture comparison. Its receipt intentionally fingerprints the updated
view module. The same lstat/xb writer, input/document/receipt bounds and explicit
partial-write limitation apply. No renderer, network, source authentication,
scientific judgement, official PRISMA diagram or exhaustive privacy audit is claimed.

Synthetic tests cover all valid protocol examples, partition aliases, detached
nodes, optional memberships, unknown stages, key-order determinism, input
preservation, hostile supplied strings, invalid vocabulary/counts/fingerprints,
size rejection, exclusive creation, JSON/text receipts and executable documentation.
The fixed Mermaid grammar is checked locally without an external renderer; this
is not a promise of acceptance or identical display in every rendering application.

Final local complete suite: `Ran 1918 tests in 142.589s`; `OK (skipped=1)` with only the
native-Windows junction test skipped on Linux. Focused flow/status/dispatcher:
49 tests in 10.291s, OK. The new guide was also executed manually (two equal
files). Python 3.10 syntax parsing, compileall, manifest verification, publication
audit and UTF-8/LF checks passed. The first focused run exposed a mock receipt
without a schema key; receipt-label selection now preserves that compatibility
and all tests pass. External renderer acceptance and remote CI are not asserted
by these local results.

## 2026-11-10 Detached records CSV (0.92.0-records-csv)

Added `views_export.py records PROTOCOL --output NEW_CSV`, rendering only existing
record, occurrence, report and evidence audit ledgers. Authoritative search indices
are occurrence-aligned; optional/duplicated display search IDs retain their positions.
Report memberships and result study IDs stay separate. Stage columns distinguish
not-supplied reports/reviews from available empty data. Bibliographic pointers and
existing screening-review cues are optional, never new adjudications.

The standard-library serializer is outside ENGINE_FILES. Every cell string uses
CSV safety escaping, list cells use JSON, and all cells are quoted to retain CR/LF.
Scalar NUL is rejected consistently across CSV runtimes. Input, CSV and stdout
receipt are bounded before exclusive output creation. A failed new CSV write is
removed on stable paths; OS cleanup failure can still leave an incomplete file.
Existing files/links are refused. The data-only CSV requires its separate boundary
receipt; real outputs remain unredacted and private. No model, network, clock,
source authentication, scientific judgement or PRISMA interchange claim is added.
Census remains NOT_ESTABLISHED and conclusion readiness remains NOT_READY.

Engine, adapter, all fixture bytes and the seven-file bundle contract are unchanged.
The existing status Markdown is byte-identical to the base (10,777 bytes). Existing
flow serialization code is unchanged; its view implementation fingerprint changes
honestly. Existing status/flow receipt formats and writer semantics are preserved.
English/Korean documentation and a tested two-command CSV rehearsal were added.

Local Python 3.12.14 complete suite: `Ran 1935 tests in 150.304s`,
`OK (skipped=1)`, no failures/errors. The skip is the existing native-Windows
junction test on Linux. Focused records/status/flow/dispatcher: `Ran 66 tests in
13.320s`, `OK`. Records-only: `Ran 17 tests in 1.253s`, `OK`. Tests cover original
ledger values, optional columns, missing versus empty stages, hostile formulas,
quotes/CR/LF/NUL, deterministic key permutation, no input mutation, CSV errors,
size/receipt preflight, exclusive destinations, failed-write cleanup and guide replay.
The initial focused run exposed a test assumption that top-level example protocols
include bibliographic collection data; a separate synthetic audit fixture now tests
that column explicitly. No production failure or test weakening resulted.

The guide was also replayed manually with byte-identical files. Python 3.10 grammar
parsing, compileall, manifest verification, publication audit and UTF-8/LF checks
passed. Local results do not assert Windows behavior, remote CI completion, universal
spreadsheet safety or scientific adequacy.
