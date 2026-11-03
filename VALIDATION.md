# Validation record

Release preparation date: 2026-11-02 (Asia/Seoul).

- Python standard-library unittest: 4 synthetic tests passed.
- Limited public-file/type/secret-pattern scan: passed.
- Manual selected-content review: no actual conversation, researcher corpus, private
  configuration, credential, real experiment or article/book/figure asset selected.
- Examples: synthetic; no scientific or persona-predictive validation claimed.
- Private history import: none; new public repository with a separate initial history.

The scanner is not a complete secret detector, anonymizer or legal clearance tool.
Framework-level code/tests and general methods were selected; private source DBs
and third-party source materials were excluded rather than redacted and republished.
Remote publication is verified separately after committing; this file does not
claim an upload has succeeded merely because local tests passed.

## 2026-11-03 increment

Run `python -m unittest discover -v` and `python audit_publication.py`.
New tests exercise the documented synthetic workflow and rejection boundaries.
On restricted Windows hosts, set TEMP and TMP to an authorized writable directory.
No real corpus, account data, or scientific fidelity evaluation was used.

Second increment: 10 tests passed; failure boundaries and deterministic repeated results covered.

Third increment: 13 tests passed, including supplied-evidence rejection and deterministic output. No external model/search integration tested.

Fourth increment: CLI end-to-end scenarios and failure recovery added. Local tests: 15 passed. Remote CI status is recorded separately in the private development log.

Fifth increment: 18 local tests passed. New CLI paths, source boundaries, deterministic output and tamper/no-overwrite checks are covered. See private development log for remote matrix CI.

Cloud reconciliation (2026-11-03): hdbio's fifth-increment ZIP/CSV/summary exporter
was consolidated with implementation fingerprinting, strict JSON parsing and
record-only support. All 26 tests passed, including the original 18 and eight
integration cases. The duplicate JSON-envelope prototype is not published.
Schema 2 intentionally rejects prototype schema 1 and changed implementation
bytes. No literature retrieval or scientific completeness validation was performed.

Supplied-context increment (2026-11-03): 35 tests passed. Nine new tests cover
provenance requirements, typed context domains, evidence/work-package joins,
review assertions, dates, dangling/duplicate references, record-only compatibility
and context preservation in portable bundles. Synthetic data only; no real
guideline currency, applicability or scientific adequacy evaluation was performed.

Search-plan accounting increment (2026-11-03): 44 tests passed. Nine additional
tests cover missing planned searches, asserted-only completion, count/paging/error
reasons, strict integer totals, source/query/window mismatch, duplicate/unplanned
search IDs, invalid shapes, legacy no-plan input and bundle/report propagation.
No source authentication, live retrieval or completeness assessment was performed.

Contradictory-completion correction (2026-11-03): 49 tests passed. Five regression
tests cover each truncation/pagination-limit flag, malformed values, legacy absent
flags, no-plan coverage and combined report/bundle propagation. This aligns the
workflow with the state validator's pre-existing truncation boundary.

Validator parity correction (2026-11-03): 52 tests passed. The standalone state
validator now reuses the workflow's completion checks, rejects Boolean/float totals
and Boolean screening counts, records malformed search shapes as validation errors
and refuses unresolved paging/error flags in completed search assertions. Three
regression tests cover these previously inconsistent input paths.

Report/work-package provenance correction (2026-11-03): 59 tests passed. Seven
new tests reject blank/nontext report provenance, malformed report containers,
empty/duplicate/malformed work evidence links, unsupported completed work after
full-text exclusion and blank completion artifacts. Pending reports remain valid.

CSV export consistency correction (2026-11-03): 63 tests passed. Four additional
tests cover formula/whitespace prefixes, plain Unicode text, multiline report CSV
round trips and work-package CSV inside verified bundles. Both exporters use one
escaping function, whose bytes are bound in bundle implementation fingerprints.
Original protocol JSON remains unchanged; no spreadsheet application was invoked.

Multi-result extraction increment (2026-11-03): 73 tests passed. Nine new extraction tests
cover multiple endpoint rows from one record, distinct record/study counts, legacy
ID defaults without mutation, duplicate/malformed IDs, extraction-level context
and work links, remaining unextracted records, full-text reconciliation of every
result and preservation of null findings in verified bundles. Extraction
completeness and scientific independence are not established.

The same increment includes one ZIP portability regression: a simulated Windows
creator previously changed archive bytes despite identical input/code. Fixed
creator metadata now makes those byte streams identical. Actual multi-platform
CI verifies runtime behavior separately.

Report extraction accounting increment (2026-11-03): 78 tests passed. Five new
tests distinguish report-level extraction from title/abstract record queues,
exclude unretrieved/excluded reports, prevent alias/result-row count inflation,
and run a combined plan + context + multi-result + full-text + bundle scenario
through CLI subprocesses while preserving pending reviews and readiness bounds.

Supplied appraisal provenance increment (2026-11-03): 87 tests passed. Nine new
tests cover provenance/domain requirements, missing appraisal coverage, duplicate
and dangling links, same-study scope, preservation of differing reviewer judgements,
legacy inputs, dates/shapes and report/bundle propagation. No appraisal method,
domain rubric, source authenticity or scientific adequacy was evaluated.

JSON entrypoint consistency increment (2026-11-03): 93 tests passed. Six new
tests cover duplicate/nested keys, nonfinite/overflow numbers, all four CLIs on
ambiguous/nonobject inputs, UTF-8 output under a forced ASCII stream environment,
unpaired-surrogate-safe diagnostics, and malformed bundle manifests without tracebacks. The shared parser is included
in implementation fingerprints; no external services were invoked.

Offline comparison increment (2026-11-03): 102 tests passed. Nine new tests cover
unchanged/key-reordered inputs, unversioned result changes, version-label bounds,
additional result rows without study inflation, reconciled full-text exclusions,
new source records, context/appraisal/plan changes, no-report input and strict
repeatable CLI output. Positional work-package IDs are explicitly warned about.

Comparator review also closed a shared workflow error path: malformed screening,
evidence and gap containers/rows now return validation errors instead of
AttributeError tracebacks. Regression cases run through the comparison CLI.

Supplied page-ledger increment (2026-11-03): 111 tests passed. Nine new tests
cover reconciled/absent/zero-result pages, ordering gaps, intermediate/final paging
flags, overlap, record-set mismatches, errors, malformed page fields, report/bundle
propagation and state-validator parity. No real search receipt was authenticated.

Combined demo/documentation increment (2026-11-03): 113 tests passed. Two new
tests verify the documented end-to-end synthetic counts, missing-source and review
gaps, work dependencies, unchanged-run comparison, verified bundle output and
README/usage relative links. Detailed compatibility notes were retained in
docs/USAGE.md while the README became a shorter practical entry point.

Status summary increment (2026-11-03): 122 tests passed. Nine new tests cover
combined queues, unknown-stage nulls, page issues, identifier-based screening,
separate report stages, unavailable/unmapped reports, dependency assertions, input
immutability/hash consistency and JSON/text CLI behavior. No priorities or
scientific readiness are inferred from queue counts.

Publication inventory correction (2026-11-03): 132 tests in the suite; local Linux run: 131 passed and one Windows-only
junction test skipped. Ten new temporary-fixture tests cover exact inventory, unlisted files, changed/missing
bytes, unsafe paths, duplicate/case-colliding names, malformed metadata and
symlink files/parents/manifests, unreadable directories and nonregular entries.
Symlink/FIFO tests skip only where creation is unavailable.
The scanner remains limited; inventory/hash validity is not authenticity or rights.

Release assertion correction (2026-11-03): 136 tests in the suite; local Linux run:
135 passed and one Windows-only test skipped. Four new regressions reject nonboolean
positive release assertions and require verification of actual cited IDs even when
the inclusion flag is absent/false, while allowing unverified uncited background
references. An independent synthetic relationship audit exercised 52 rejection
checks across report, bundle, comparison and status entrypoints without finding
another broken-link acceptance in those cases. This is not scientific validation.

Record occurrence provenance increment (2026-11-03): 142 tests in the suite;
local Linux run: 141 passed and one Windows-only test skipped. Six new synthetic
tests cover repeated source labels and absent search IDs, occurrence/count
reconciliation, preserved distinct similar IDs, report lookup back to search
positions, deterministic bundle propagation, page/search overlap separation and empty searches. No publication
identity matching or actual source authentication was performed.

State shape correction (2026-11-03): 147 tests in the suite; local Linux run:
146 passed and one Windows-only test skipped. Five new tests cover malformed
nested state containers, strict citation/reference numbers (including boolean,
float and null collisions), draft reference flags, individually supplied screening counts and machine-readable CLI errors
without tracebacks. Valid supplied COMPLETE assertions remain accepted without
independently certifying their factual truth.

Offline scale guards (2026-11-03): 152 tests in the suite; local Linux
run: 151 passed and one Windows-only test skipped. Three new tests cover a flat
1,500-work-package dependency chain, an equally deep cycle and branching shared
dependencies/completion checks. A separate seeded differential probe compared
100 small DAGs against the previous implementation and found identical output.
These synthetic graph checks do not validate research scale or scientific plans.

Two additional bundle regressions enforce the same inclusive uncompressed-byte
limit during creation and verification, and confirm rejected creation leaves no
output file. This fixes creation of a bundle that exceeded its own verifier limit.

Mock adapter contract increment (2026-11-03): 168 tests in the suite; local Linux
run: 167 passed and one Windows-only test skipped. Sixteen adapter tests cover
pending/rejected proposals, hash-bound supplied review promotion, exact plan and
source links, request/response/candidate collisions, page/count failures, zero
results, existing screening/report eligibility, immutable inputs, downstream
stale-provenance rejection and CLI protocol export/bundle verification. A forged
bundle with updated file hashes still fails when extraction content no longer
matches its reviewed receipt. Enrichment tests retain original review context
while allowing version/work-package additions. All examples and review assertions
are synthetic; no external service/model or actual reviewer was invoked.

Adapter regressions also reject consistently rehashed but structurally invalid
candidate ledgers and integer/Boolean/float substitutions in frozen review content.
Assembly and downstream validation share the same fixture/candidate contract.

Work-package review packet increment (2026-11-03): 180 tests in the suite; local
Linux run: 179 passed and one Windows-only test skipped. Twelve new synthetic
tests cover source/report/screening lineage, guideline/development assertions,
extraction-level context/appraisal scope, narrowed work selection, multiple reports
and reviewers, optional stages, positional search joins, full-protocol validation,
completion bounds, input/hash determinism, adapter-to-management enrichment and
UTF-8/strict-JSON CLI behavior. Text rendering escapes control, format and Unicode
line-separator characters. Extraction completeness and source identity remain
unestablished even when recorded review gaps are empty. No clinical, regulatory,
scientific-quality, prioritization or go/no-go decision is generated.

Supplied planning assertion increment (2026-11-03): 191 tests in the suite; local
Linux run: 190 passed and one Windows-only test skipped. Eleven new tests cover
strict ranks/targets, ties and missing assertions, stale evidence/context/appraisal/
search/screening/report/scope bindings, progress/version exclusions, unrelated work,
canonical type distinctions, immutable inputs, comparison, CSV safety and the
adapter → context/WP → supplied rank → prerequisite completion → packet/bundle
journey. Independent review also probed dependency-scope and context-review changes.
Current-source matching is not planning quality; stale ranks are not used in current
rank groups, and neither ranks nor completion assertions alter readiness bounds.

Synthesis review snapshot increment (2026-11-03): 204 tests in the suite; local
Linux run: 203 passed and one Windows-only test skipped. Thirteen new synthetic
tests cover distinct record/report/study/result accounting, unfinished search and
full-text stages, missing versus empty stages, extraction-scoped citation/context/
appraisal links, malformed citations, source-bound statement reviews, stale prose
and source inputs, canonical type changes, conflicting appraisal assertions,
empty-queue readiness limits, adapter-to-synthesis/bundle propagation and strict
UTF-8/control-safe CLI rendering. Independent review also checked conservation,
source-hash scope, tampering and latest ledger/diagnostic visibility fixes.
No statement support, literature completeness or clinical validity was assessed.

Nonclinical condition-record increment (2026-11-03): 217 tests in the suite; local
Linux run: 216 passed and one Windows-only test skipped. Thirteen new synthetic
tests cover strict reporting-state unions, anchored per-result observation times,
condition/outcome scope, missing versus empty stages, duplicate/cross-record/study
and overlapping assignments, causal-label consistency, planning/synthesis staleness,
unrelated/legacy basis compatibility, direct-helper safeguards, adapter enrichment,
bundle/CSV scope, deterministic nonmutation and control-safe text. Independent
review confirmed anchor handling, full-unit unresolved-field scope, shared null
queues and enforced condition binding. Fixtures use fictional models and units;
no protocol, dosing advice, causal assessment or operational biology is generated.

Outcome sample-reporting increment (2026-11-03): 227 tests in the suite; local
Linux run: 226 passed and one native-Windows-only test skipped. Ten new tests
cover exact per-outcome coverage, fixed arm scope, strict source-backed reporting
states, numeric/coercion rejection, missing versus empty metadata, explicit n
semantics, absence of inferred independence/readiness, unchanged PRISMA counts,
planning/synthesis staleness, source-preserving WP/CSV/bundle propagation and
nonmutation. CLI status, work review, synthesis snapshot and reproducible bundle
creation/verification were also exercised with fictional metadata. Counts and
independence explanations are unverified supplied text; no real biology,
numerical/statistical consistency assessment or effect estimation was performed.
Independent review additionally rejected 265 malformed sampling inputs, checked
all four reporting states, affected-only review staleness (including removal),
sibling-outcome scope, unrelated-condition stability, deterministic verification,
source-change diffs and legacy bindings. No feature blockers were found.
