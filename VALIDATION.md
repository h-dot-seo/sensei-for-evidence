# Validation record

Current release: `0.112.0-protocol-scaffold` (2026-11-14). This file is the
current snapshot; every dated entry since the 2026-11-02 release preparation is kept
verbatim, in order, in [docs/VALIDATION_HISTORY.md](docs/VALIDATION_HISTORY.md).

## What CI runs

GitHub Actions (`.github/workflows/tests.yml`) runs on every push to `main` and on
every pull request, on a matrix of `ubuntu-latest` and `windows-latest` with Python
3.10 and 3.12:

1. `python -m unittest discover -v` on Python 3.10 and the same command with
   `--durations 25` on Python 3.12 — the synthetic test suite in the `tests/` package,
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

## 2026-11-14 One-file dispatcher selection (0.107.0-passive-review-view)

A separate real-user-path improvement, not a test harness conversion: sensei.py run
now validates the existing basename grammar and exact directory-entry spelling,
then reads/parses only the selected eligible file. It excludes itself, helpers and
nonfiles using the same entrypoint predicate. No cache. Existing list/check whole
checkout behavior remains. An unrelated syntax error no longer blocks a valid
selection, while full discovery and the selected file still expose their errors.
Existing symlink/trusted-checkout limits are documented, not silently strengthened
or presented as an isolation guarantee. ENGINE_FILES and other root Python unchanged.

Four-case before/after exact-result measurement: 388 source reads/AST parses become
2 (valid script plus helper). Three alternating runs: old0.660/0.674/0.678s versus
new0.00237/0.00230/0.00237s on Python3.12.14/Linux. Counts exclude directory metadata
calls. [Selection guide](docs/DISPATCHER_SELECTION.md) records reproduction and scope.
All existing subprocess dispatcher tests remain unchanged; new regression tests pin
exact case, zero/one source access, discovery differences, selected errors and no cache.

Full local suite: 2069 tests in 146.498s, OK (one platform skip). Focused and
independent dispatcher tests: 20 pass. Independent four-case benchmark: exact paths
and errors match, reads/AST388 to2, 0.644s to0.00246s locally. Unchanged real-process
rejected-name test measured4.880s before and0.466s after. No timing assertion.
Audit453 files, manifest, compileall, Python3.10 grammar, ENGINE/other root Python,
shared helper/CI/existing dispatcher tests and old executable blocks pass. Symlink
regression skips where the OS cannot create one. Final checkout/dispatcher checks
rerun after docs/manifest finalization. Independent review found no code blockers;
test-runtime documentation now explicitly scopes earlier production-byte-preservation
claims to the earlier test-only releases.

## 2026-11-14: passive local HTML review (0.107.0)

Added research_view.py and a literal synthetic guide. Full suite: 2081 tests in
160.104s, OK (one existing conditional skip). New12 tests, independent focused38
and direct supplied READY/challenge checks passed. Existing root modules,
ENGINE_FILES and all prior guide sh blocks are byte-identical. Python3.10 grammar
checked for231 files; audit456 and manifest455 passed before this record update.
CSP/allowlisted tags/escaping/fixed anchors, deterministic bytes, immutability,
work scope, output and input limits, exclusive paths, receipts and CLI errors tested.

Visual QA limitation: Chromium launch was attempted both normally and with execution
approval but failed at socket() with Operation not permitted. No screenshots or
responsive/print visual verification were completed. DOM and CSS contract tests
are not visual QA. Real user data, source verification and scientific validity
were not tested. Partial output after OS write failure and hostile path races
are not transactionally prevented; these limits are stated in REVIEW_VIEWS.md.

## 2026-11-14: referenced search receipts (0.108.0)

Synthesis/work snapshots schema2 replace repeated full search rows with index/hash
references and retain top-level ledger/coverage. HTML composed snapshot also bumps
to2 and identifies nested synthesis schema2; receipt schema1 remains unchanged.
Full final suite2086 tests155.321s OK(skip1), focused41 before final nested test,
independent56 plus direct11 nested reference resolutions. Final nested-statement
regression and wrapper schema markers were added following review.
N200/400 one-search, independent-result/work shape: synthesis213439/417039 bytes,
work748028/1491828 bytes. No statements or wide cross-links in that scale generator;
not general linearity or timing guarantees. Canonical/ENGINE_FILES unchanged.
Prior HTML visual QA remains unverified because browser startup is restricted.

## 2026-11-14: supplied native occurrence export (0.109.0)

Added collection_export.py create/verify and a guide chained to the existing
batch/continuation walkthrough (no duplicate43-command replay). Full final suite
2095 tests154.578s OK(skip1). New9 edge tests, combined guide26 tests, independent
initial52 plus guide17 and final26 review passed. Exact historical wrapper binding,
explicit occurrence joins, include/exclude/pending/withheld, repeated IDs, BOM and
CRLF/no-final-newline handling, missing wrappers and non-bibliographic occurrences
including a shared native record were checked. Original module/ENGINE_FILES
bytes unchanged; new parser self-check keeps its10MB cap under50MB aggregate cap.
A new regression fixture initially violated base-search and review-date contracts;
these test setup errors were corrected before final full run. No released failure.
No reference-manager interoperability or scientific validity was tested.
OS write failure can leave a partial new output; hostile path races are not guarded.

## 2026-11-14: checked command reference (0.110.0)

The command reference now has one exact parser-usage row per documented entry.
Added omitted continuation preview/verify and screening-sheet export, expanded the
compressed screening intake row, corrected22 usage rows and listed3 missing helpers.
162 command rows cover all root CLI scripts/subcommands; non-CLI modules are checked
separately. Every argparse help runs in a real subprocess from an empty temporary
working directory, with fixed width/color and no bytecode writes. Two publication
scripts without argparse are checked statically and not executed as help. Unittest
examples are excluded. The129 handoff routes must occur in the tested command set,
replacing duplicate in-process help runs. Existing guide link checking includes
COMMANDS.md. Parser tests reject duplicate/compressed/malformed rows and distinguish
subparser lists from argument choice lists. No root Python or ENGINE_FILES changed;
existing schema2 consumers, rights and human-decision boundaries are unchanged.

Focused30 and independent30 tests passed. Independent review identified a future
global-option/subparser help shape; suffix extraction and its regression now cover it.
The initial full run was stopped to include that correction; only the final full run
is counted below. Final full suite2099 tests165.462s OK(skip1); final independent4
passed with no blockers. Audit461, manifest460 and Python3.10 grammar235 passed.
These checks concern parser help and documentation only, not live
research actions, external tool compatibility or the previously unverified HTML UI.

## 2026-11-14: explicit long-form CSV positions (0.111.0)

Added screening_position_intake.py preview/target/assemble/verify for operator-prepared
long-form UTF-8 CSV positions with explicit columns/labels and a supplied pre-review
basis template. This fills the multiple-reviewer/mapped-column gap beyond the existing
own-sheet intake. The template's exact source hashes are retained, never refreshed;
target rejects stale sources. Raw CSV, compact basis, mappings and byte-span provenance
are replayed from the detached application after separate supplied import review.
Only screening_reviews is appended; canonical screening and all prior assertions stay
unchanged. No external product compatibility, reviewer chronology/identity, authenticity,
scientific correctness or rights is established. First scope is CSV-only (not manual
candidate JSON or ID-remapping files),1..100 rows,10MB/50MB bounds,exclusive single output.
OS write failure can leave a partial new file; hostile path races are not guarded.

New10 tests and combined focused38 passed, including the independent two-block6-command
synthetic guide, opposing reviewers, stale basis, literal mapping, collision and replay
checks. Initial tamper test mistakenly replaced an already empty list with another empty
list; that no-op test was corrected before the final runs. Catalog now133 routes and
command reference166 rows. ENGINE_FILES and schema2 contracts unchanged; review_handoff
is the only pre-existing root module modified. External manager compatibility and the
previous HTML visual QA remain unverified. Independent56 tests and direct stale CLI/action checks passed with no blockers.
Added actual100-success/101-rejection, manual-ID collision and empty-ledger regression
after review. Final full2110 tests168.825s OK(skip1); final independent11 passed.
Audit465/manifest464 and Python3.10 grammar237 passed.

## 2026-11-14: supplied starting-protocol scaffold (0.112.0)

Added protocol_scaffold.py template/check, the independent first slice of roadmap36.
A new null/empty draft never fills questions, criteria, plan IDs/source/query/window or
search facts. The strict recommended starting shape rejects missing/unknown fields,
nontext/blank values, empty criteria, malformed/duplicate plan rows and nonempty ledgers.
Only a fresh_base+run validated supplied draft can be exported to an exclusive new
protocol. Invalid checks report JSON-pointer hints and exit2 without a new file.
No JSON Schema/explain collection, provider-specific PubMed matching or automatic
plan creation is shipped. Schema2 and all existing root Python/ENGINE_FILES unchanged.

A two-block3-command synthetic guide supplies fictional draft values between blocks,
then checks the new base and obtains blank mock receipts on stdout. First rehearsal
caught an unsupported receipt template --output option, corrected to the actual stdout
contract before final tests. New9 and focused15 tests passed. Existing USAGE quick-start
shell block is preserved intact under a separate legacy agent-state heading; own-protocol
onboarding now leads to the new guide. Final full2119 tests172.826s OK(skip1); independent23 tests and direct dangling-link
CLI refusal passed with no blockers. Audit468/manifest467 and grammar239 passed.
10MB memory-bound inputs/outputs; exclusive writes may leave partial files on OS failure
and do not guard hostile ancestor/path races. A valid shape is not plan/query adequacy,
source authenticity, approval, search execution or scientific readiness. Previously
unverified external-tool compatibility and HTML visual QA remain unverified.
