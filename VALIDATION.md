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

Outcome statistics-reporting increment (2026-11-03): 239 tests in the suite;
Linux run: 238 passed and one native-Windows-only test skipped. Twelve new tests
cover source-preserved arm summaries, contrasts and explicitly oriented direction,
strict string/reporting-state unions, missing/empty stages, exact outcome/arm
coverage, literal unit/statistic/dispersion-label cues, unchanged PRISMA counts,
fresh-to-stale source review bindings, unrelated condition stability, WP/CSV/
synthesis/bundle propagation, safe text and nonmutation. CLI status, work review,
synthesis and bundle creation/verification passed with fictional numerical data.
Independent review tested 146 malformed/reporting-state cases and 82 individual
source-leaf changes against current review bindings. The reported dispersion-unit
cue omission was fixed and covered by a targeted regression. Numerical consistency,
statistical significance, effect direction and causality remain unassessed.

Claim-position comparison increment (2026-11-03): 250 tests in the suite;
Linux run: 249 passed and one native-Windows-only test skipped. Eleven new tests
cover exact component/citation/aspect scope, strict provenance and author/date
fields, duplicate/partial coverage rejection, missing-versus-empty stages,
source-bound position changes/removal, fixed no-support/no-voting behavior,
WP-selected positions versus full-statement scope, condition/n/statistics joins,
CSV/bundle propagation, legacy hashes, unchanged PRISMA/work priorities and safe
text/nonmutation. Independent review identified a missing synthesis-stage label
in WP text; the label and absence/empty regression were added. CLI status,
work/synthesis review and reproducible bundle creation/verification passed on
fictional positions only. No direction, refutation or causal judgment is inferred.
Independent partial-overlap review was retained as an e1-only WP regression: only
its positions are selected while the other result and full statement stay visible.

Operator handoff CLI increment (2026-11-03): 265 tests in the suite;
Linux run: 264 passed and one native-Windows-only test skipped. Fifteen new tests
exercise all typed queue mappings, missing/empty states, selected-WP versus global
scope, protocol/implementation hashes, unchanged inputs, source-safe text, null
search plans, legacy effective IDs, namespace collisions, missing/duplicate search
IDs, leading-dash work IDs and nonzero/no-partial-output failures. The actual CLI
journey runs status, synthesis, selected work, handoff text/JSON and bundle
create/verify against a fictional input path with spaces. Independent review
identified null-plan, search-index, namespace and argument-array edge cases;
these were fixed with explicit regressions. No source retrieval, scientific
review, work execution or automatic review renewal is performed.

PRISMA-oriented accounting export increment (2026-11-03): 279 tests in the suite;
Linux run: 278 passed and one native-Windows-only test skipped. Fourteen new tests
cover occurrence/record/report/study/result units, nine same-unit disjoint member
partitions, exact-ID retention pointers, many-record/report/study links, missing
versus empty report stages, exact stage-specific reasons, incomplete-search
visibility, input-order retention, legacy source IDs, unchanged source data,
canonical/implementation hashes, handoff navigation and real JSON/text/error CLI
runs. Independent review additionally passed 150 randomized mixed accounting
fixtures, 47 malformed-input CLI cases and 27 existing report/handoff tests.
The fictional E2E CLI audit/handoff and existing bundle create/verify passed.
Matching partitions do not certify completeness, identity, PRISMA compliance or
scientific/clinical validity; no sources or models were called.

Search query/receipt manifest increment (2026-11-03): 294 tests in the suite;
Linux run: 293 passed and one native-Windows-only test skipped. Fifteen new tests
cover exact full/core query specifications, unsupported fields, missing runtime
metadata, source-wise missing/unresolved/asserted receipt states, null versus zero
counts, recorded interruption/page signals, page versus query overlap, same-source
versus cross-source IDs, no-plan behavior, full hashes/nonmutation, mock-receipt
compatibility, downstream validation, handoff fingerprints and safe real CLI
JSON/text/error paths. Uninterpreted receipt/page metadata is preserved but never
executed. Independent review passed 69 focused tests and probes on 17 valid
fixtures, including source/ID collisions and cross-process hash determinism.
The synthetic manifest/handoff/PRISMA CLI journey and existing bundle creation/
verification passed. No provider request, query translation, next cursor,
automatic retry, review renewal or census assertion is performed.

Synthetic manual receipt-intake increment (2026-11-03): 308 tests in the suite;
Linux run: 307 passed and one native-Windows-only test skipped. Fourteen new tests
cover deliberately unfilled templates, exact query copying, required-field pointer
hints, interrupted/overlapping unreviewed receipts, reuse of existing normalization,
separate-base guards, review/extraction rejection, unknown versus empty results,
canonical validation errors, hashes/nonmutation, escaped text, handoff separation
and real CLI exclusive export followed by PRISMA audit. Independent review passed
74 focused tests and 1,230 malformed-value mutations; existing/input/symlink files
could not be overwritten. The synthetic template/check/candidate → manifest →
PRISMA → handoff → bundle create/verify journey passed. Candidates retain no
accepted reviews or promoted evidence; missing facts and review gaps remain.
No source retrieval, API call, scientific judgment or acceptance is performed.

Source-review work increment (2026-11-03): 322 tests in the suite;
Linux run: 321 passed and one native-Windows-only test skipped. Fourteen new tests
cover empty-evidence source work with strict planned-search/record references,
legacy evidence requirements, pending source stages, mixed dependencies, unchanged
completion guards, no implicit receipt/extraction approval, structural result-ID
inventory staleness (including direct dependent evidence work), legacy hashes,
manual receipt → reviewed extraction → mixed WP workflow, CSV/handoff output and
real CLI execution. Independent review compared 17 valid legacy protocols to the
prior HEAD and confirmed identical run outputs/planning hashes. The discovered
source-inventory staleness gap was fixed with ID-only binding; result-content
assessment remains the evidence-work scope. Synthetic work/handoff and bundle
create/verify passed. No work is automatically completed, ranked or executed.

PRISMA work-traceability increment (2026-11-03): 332 tests in the suite;
Linux run: 331 passed and one native-Windows-only test skipped. Ten new tests
cover explicit planned-search and record-source work, separately linked result
work, missing receipt with a task, indirect multi-record report links, absent vs
empty stages, default IDs/input pointers, output copy isolation, hostile artifact
text, reproducible CLI output and completion without changing PRISMA accounting.
Independent review additionally probed namespace collisions and multi-result
record-level deduplication. A real CLI synthetic receipt intake → supplied source
work/fictional completion note → handoff → PRISMA export → seven-file bundle
create/verify passed. Artifacts remain unverified; work completion does not approve
receipts, create extracted evidence, assess task coverage or establish census.

Opt-in local artifact review increment (2026-11-03): 345 tests in the suite;
Linux run: 344 passed and one native-Windows-only test skipped. Thirteen new tests
exercise matching hashes without work completion, size/hash mismatch and missing
files, empty manifests, full manifest validation before access, traversal and
metadata paths, strict sizes/hashes/IDs, unsupported-platform fail-closed behavior,
symlink ancestors/root, hardlinks/FIFOs/directories, zero-byte nested files,
detected concurrent growth, bounded inputs, sanitized input errors and real CLI.
On unsupported platforms, POSIX artifact-access cases are skipped while explicit
fail-closed and portable validation tests still run. Independent review found no
blocking issue within the documented trusted/quiescent-directory boundary; its
metadata-cap, input-error leakage, root-spelling and access-time caveats were
addressed. The synthetic note hashes successfully while its WP remains IN_PROGRESS,
its dependent WP stays blocked, and source completeness is not established.

Context-amendment work comparison increment (2026-11-03): 358 tests in the
suite; Linux run: 357 passed and one native-Windows-only test skipped. Thirteen
new tests cover unchanged/added/removed contexts, distinct access/review dates,
retained review assertions after changed source/result inputs, changed review
metadata without reassessment claims, explicit-only WP linkage, old/new scope
partitions, unassigned contexts, validation failures, copy isolation, progress-only
changes, out-of-scope source changes and deterministic real CLI output. Independent
review found a mislabeled work-change cue caused by comparing context-derived link
overlap wrappers; comparison now uses the nested work assertions and a regression
locks the distinction. Synthetic work packet → amendment comparison → updated work
packet/handoff passes with clinical/regulatory significance and review validity
unassessed. No source retrieval, applicability inference or priority changes occur.

Prerequisite-packet review increment (2026-11-03): 369 tests in the suite;
Linux run: 368 passed and one native-Windows-only test skipped. Eleven new tests
cover mixed source/evidence dependency chains, exact packet reuse, default omitted
packet disclosure, strict flag/selector validation, diamonds, completed prerequisites,
no shared-evidence/downstream expansion, input isolation, a reversed 1,050-node
chain, cycle rejection, safe leading-dash handoff argv and real CLI/text boundaries.
Independent review also exercised 1,200 nodes, missing dependencies and packet
identity against individually selected work. The synthetic chain deliberately
retains stale planning assertions after dependency amendments; rank renewal and
scientific/clinical/acceptance decisions are not performed. CLI handoff → expanded
packets preserves source, condition/statistics, guideline and appraisal limits.

Planning rationale-statement increment (2026-11-03): 380 tests in the suite;
Linux run: 379 passed and one native-Windows-only test skipped. Eleven new tests
cover explicit shared-evidence references, strict unknown/duplicate/empty/type
rejection, source-only exclusion, linked statement/position/sibling-result
staleness, unlinked statement independence, validated-synthesis helper binding,
legacy omission behavior, unchanged work-progress semantics and packet/handoff/
bundle propagation with copy isolation. Independent review compared all 21 valid
legacy examples to the previous HEAD and found identical no-reference review
targets/hashes. CLI work-prerequisites → handoff → synthesis retains supplied
challenging/unknown positions without judging rationale support or making a
scientific, clinical, regulatory, proceed/stop/defer or priority decision.

Compact work-navigation increment (2026-11-03): 390 tests in the suite;
Linux run: 389 passed and one native-Windows-only test skipped. Ten new tests
cover selected/prerequisite scope, unblocked vs blocked IN_PROGRESS work, COMPLETE
assertions retaining source gaps, absent vs empty cues, planning/acceptance text,
existing challenging positions, copy isolation, hostile-text quoting, empty work,
mutually exclusive CLI formats and a brief view under half the synthetic detailed
output size. Independent review confirmed status-only grouping and scope/copy
boundaries; supplied search-index wording and compact global-plan display were
refined. CLI prerequisite and rationale views retain unresolved source/scientific
work without generating next-task priorities, acceptance or clinical decisions.
The first navigation CI run exposed a Windows-only test comparison issue: native
CRLF stdout was compared to the renderer's LF string. The regression now normalizes
only CRLF line endings before comparing the complete UTF-8 text; production
behavior is unchanged. A fresh CI matrix run is required for the corrected commit.

First-run walkthrough increment (2026-11-03): 395 tests in the suite;
Linux run: 394 passed and one native-Windows-only test skipped. No runtime engine
or input schema was added. Five new tests execute all 11 shell-free documented
CLI commands in order using an external temporary directory with spaces, assert
exclusive output refusal, verify exact adapter lineage and restricted authored
enrichment fields, separate record/report/study/result counts, and check that the
fictional completed note only changes recorded work/dependency assertions. Missing
searches and scientific-readiness bounds persist. Local documentation links and
unchanged completion guards are checked. The sequence clearly separates mock
provider proposals, prewritten fictional reviews, hand-authored nonclinical/context
work metadata and unverified artifact/acceptance assertions.

External amendment-note increment (2026-11-03): 406 tests in the suite;
Linux run: 405 passed and one native-Windows-only test skipped. Eleven new tests
cover canonical input/version binding, exact top-level scope omissions/extras,
strict note fields/types/dates/hashes, missing vs null, identical inputs with empty
scope, observed work/planning transitions, typed-value hashing, mutation isolation,
unchanged non-note comparison fields and real CLI match/mismatch exit behavior.
Independent adversarial review found no blockers. The synthetic reason binds a
receipt-note completion snapshot while missing search and scientific-readiness
limits remain visible. Notes are external supplied assertions, not protocol
amendments performed by the tool, authenticated authorship or approved decisions.

Completion-source binding increment (2026-11-03): 419 tests in the suite;
Linux run: 418 passed and one native-Windows-only test skipped. Thirteen new tests
cover existing acceptance guards, strict optional hash/status rules, unbound legacy
completion, current/stale source classes, criteria/evidence/context/own-locator
changes, no self-binding, pre-completion targets, direct prerequisite scope,
unrelated context isolation, queue/handoff/brief/bundle propagation and immutable
outputs. Amendment transitions and matching artifact bytes with stale completion
are tested separately. Independent review compared legacy planning targets across
24 runnable historical examples and found them unchanged. Direct-dependency scope
limits and artifact-byte nonverification are explicit. Recorded COMPLETE and
mechanical dependency unblocking remain unchanged; no hash or acceptance is
renewed automatically and no scientific/clinical decision is made.

Direct prerequisite completion-cue increment (2026-11-04): 429 tests in the suite;
Linux run: 428 passed and one native-Windows-only test skipped. Ten new tests
cover current/stale/unbound/not-complete direct prerequisite labels, omitted
packet disclosure, unchanged unblocking, source-review work, exact handoff
projection, direct-only versus expanded scope, unrelated-work isolation, input
and cross-packet nested-copy isolation, multiple-prerequisite ordering, repeated
output determinism, and a real brief CLI invocation. Existing deep-chain,
diamond, hostile-text and compactness regressions also pass. The projection adds
no engine gate, automatic reopening, hash renewal or recursive acceptance claim.
Publication audit and complete inventory verification pass on the final files.
Independent read-only review found no blocking issues; its suggested ordering,
determinism and cross-packet isolation cases were added as executable regressions.

Completion-binding export increment (2026-11-04): 441 tests in the suite;
Linux run: 440 passed and one native-Windows-only test skipped. Twelve new tests
cover current/stale/unbound/unfinished completion CSV fields, unchanged supplied
status and hashes, explicit nonverification labels, direct prerequisite order,
unrelated-work isolation, formula-like artifact escaping with unaltered JSON,
deterministic bundle verification, rehashed fabricated-label rejection,
source-review work, explicit false versus missing acceptance fields, all direct
prerequisite labels, three-level link scope and empty-work readiness bounds.
The existing 31-column CSV prefix has an executable compatibility regression and is
preserved; summary counts do not infer acceptance. Public audit and inventory
verification pass. Independent review additionally compared the unchanged CSV
prefix and reproducible ZIP output across all 25 valid synthetic examples.
Independent review found no blockers; its four suggested edge cases are now
executable tests rather than manual checks alone.

Completion amendment-comparison increment (2026-11-04): 465 tests in the suite;
Linux run: 464 passed and one native-Windows-only test skipped. Twenty-four new
independently written tests cover current/unfinished/already-stale assertions,
own locator versus source scope, exact evidence/context/appraisal/experimental/
rationale changes, shared search context, prerequisite locator/status/order,
progress exclusions, retained hashes/statuses, positional-ID warnings, added and
removed work, detached snapshots and deterministic CLI comparison without a note.
The synthetic amendment fixture preserves an old COMPLETE hash after explicit
scope changes; comparison locates those changes without reopening work or
claiming historical acceptance reasons. Independent review found no blockers.
An additional unchanged-input/nonmutation check passed across all 26 valid
synthetic protocol examples. Publication audit and complete manifest checks pass.

Readable protocol-comparison increment (2026-11-04): 485 tests in the suite;
Linux run: 484 passed and one native-Windows-only test skipped. Twenty new
independently written tests cover text/API/default-JSON parity, CRLF inputs,
UTF-8 under forced ASCII stdout, deterministic repeated output, immutable input
files/objects, safe hostile control/format text, exact input/engine fingerprints,
field/scope differences, all context/work IDs, retained stale/unbound states,
missing stages, empty/add/remove scopes, prerequisite status versus order, and
matching/mismatching/invalid amendment notes with unchanged exit behavior.
Independent review found no implementation defects. All 26 valid synthetic
examples additionally rendered deterministically without mutation, preserving
input/implementation hashes and NOT_READY bounds. Publication audit and complete
manifest verification pass. The text view is a projection, not scientific prose
or automatic acceptance; full JSON remains the default structured record.

Native stdout portability correction (2026-11-04): the first readable-comparison
CI run passed Ubuntu but exposed nine Windows assertion failures because normal
CRLF stdout was compared directly with the API's LF string. Production rendering
was unchanged. Text parity tests now strictly decode UTF-8 and normalize only
CRLF; JSON parsing and repeated same-platform byte comparisons remain unchanged.
Two new regressions preserve literal escaped newlines, unexpected bare carriage
returns and invalid-UTF-8 failures, and exercise simulated Windows stdout on any
host. The suite now contains 487 tests; Linux run: 486 passed and one native-
Windows-only test skipped. Publication audit and manifest verification pass.

Local bibliographic intake increment (2026-11-04): 513 tests in the suite;
Linux run: 512 passed and one native-Windows-only test skipped. Twenty-six new
tests cover exact UTF-8/BOM/newline bytes and multiline row spans, original columns,
explicit search-plan mapping, duplicate occurrence and literal-locator conflicts,
canonical full-protocol binding, unchanged existing receipts/PRISMA counts,
header-only noncompletion, deterministic artifacts and safe text display.
Verification rejects 21 tampering classes even after a supplied review-target
hash is recomputed. CLI regressions cover exclusive output, invalid/null input,
forced-ASCII environments and portable native stdout. Byte, data-row, physical-line,
CSV-field and artifact-size limits bound parsing and retention. Independent test
and code review found no remaining substantive defect. The fixture is entirely
fictional; no source retrieval or real corpus was used. This is a detached,
unreviewed local export, not an accepted receipt or an integration into research
counts. Source authenticity, search completion and conclusions remain unverified.

Supplied bibliographic reconciliation increment (2026-11-04): 539 tests in the
suite; Linux run: 538 passed and one native-Windows-only test skipped. Twenty-six
new independently written tests cover explicit new/same/withheld row decisions,
forward references and canonical ordering, exact-context review targets, strict
review fields, empty/all-withheld exports, exclusive CLI writes and UTF-8/newline
portability. Sequential imports preserve intervening screening, version and
source-work enrichment while using one immutable common base. Compact artifacts
reconstruct exactly, and callbacks receive only ledger-free base snapshots.
Tests reject altered raw bytes/spans, choices, base context, historical bodies,
prefix order and attached completeness; dependent review targets remain stale
even after earlier receipt and search hashes are resealed. Output isolation,
resource bounds, separate raw-row versus PRISMA-membership accounting, row pointers
and deterministic bundle verification are exercised. The focused integration
suite passes 80 tests. Independent review found no remaining production defect.
All examples remain synthetic; supplied identity/review assertions do not prove
authenticity or complete searches, and no eligibility/extraction decision is made.

Pre-extraction context increment (2026-11-04): 560 tests in the suite; Linux run:
559 passed and one native-Windows-only test skipped. Twenty-one new independently
written tests cover both context domains with zero evidence, exact typed source
identity, partial reference intersections, missing planned sources, unscreened and
excluded records, unassigned contexts, scope/synthesis isolation, strict supplied
review metadata, immutable outputs, planning/completion staleness, and explicit
source linkage in packets, brief navigation, handoff, comparison, PRISMA and
bundles. Review identified and fixed acceptance of malformed optional review
dates on pending source contexts; legacy evidence-context behavior is unchanged.
The focused suite passes 116 tests. All 27 pre-edit valid examples retain exactly
equal normalized contexts, planning targets, completion ledgers and synthesis
outputs, avoiding implicit legacy hash renewal. Source links do not create
evidence/study IDs, eligibility decisions or clinical validity. Focused context
comparison explicitly leaves underlying search/receipt changes to the full
comparison and broader work-source binding. No real guidelines or development
records were retrieved or published; the new example is entirely fictional.

Explicit multi-study report increment (2026-11-04): 584 tests in the suite;
Linux run: 583 passed and one native-Windows-only test skipped. Twenty-four new
independent tests exercise plural declarations, exact report-study membership,
multiple results within one source record, partial/cross-report extraction gaps,
invalid or ambiguous declarations, literal identity preservation, nonmutation,
stale source bindings, unchanged appraisal/experimental same-study guards,
adapter integration, optional status/handoff queues, packet scope isolation,
PRISMA pair partitions, Unicode/CSV safety and deterministic bundles. Review found
and fixed a missing status-module import; CLI/status/snapshot/handoff regressions
pass. The focused 13-suite run passes 169 tests. All 28 prior valid fixtures retain
equal core/report/audit/status outputs and exact report CSV bytes, excluding only
changed implementation fingerprints. The new helper is included in bundle
fingerprints. Report/result-presence counters retain their legacy meaning, and
separate membership coverage does not assert per-study eligibility, independence
or exhaustive extraction. Only explicit included-report declarations enable this
migration; no real literature or scientific validation data is included.

Report-study comparison increment (2026-11-04): 608 tests in the suite; Linux
run: 607 passed and one native-Windows-only test skipped. Twenty-four independent
new tests cover scalar/singleton migration, report/study reordering, literal pair
identity and delimiter collisions, renamed IDs, partial result presence, result
reassignment between studies/reports, changed source record links and locators,
nonincluded metadata, included-to-excluded transitions, absent versus empty
ledgers, immutable deterministic snapshots, invalid declarations and portable
UTF-8/control-safe CLI output. The related comparison/membership suite passes
79 tests. Independent comparison against the prior comparator preserves legacy
JSON and text for 28 unchanged and 26 changed-input fixtures, excluding only the
comparator fingerprint. New pair projections are conditional on plural opt-in;
existing entity diffs and PRISMA counters are unchanged. Pair matching uses exact
two-field identities, never positional pointers, locators or inferred renames.
No source authenticity, study identity, eligibility, extraction completeness or
scientific/clinical significance is established by a retained or unchanged pair.
The comparison is read-only; its test inputs remain entirely fictional.

CSV-independent comparison correction (2026-11-04): the first membership-diff CI
run passed both Python 3.12 jobs but exposed a Python 3.10 CSV serialization
failure for an embedded NUL in an otherwise valid supplied JSON ID. The original
literal-identity regression remains intact. The comparator now requests validated
report projections without constructing unused CSV; default CSV exports and all
report/evidence validators are unchanged. Five new tests simulate an unavailable
CSV writer, cover every scalar/plural pairing, preserve NUL IDs, compare full
default/no-CSV projections and enforce strict keyword/Boolean options. The suite
now has 613 tests; Linux run: 612 passed and one native-Windows-only test skipped.
The related report/comparison suite passes 96 tests. All 26 report-bearing example
outputs retain exactly equal default report JSON and CSV; 29 unchanged and 27
changed-input comparison cases retain equal JSON/text with shared current engine
fingerprints. No identifier is removed or normalized to satisfy a serializer.

Supplied screening-review increment (2026-11-04): 649 tests in the suite; Linux
run: 648 passed and one native-Windows-only test skipped. Thirty-six independent
new tests cover strict assertions/dates/hashes, exact record/reviewer identities,
multiple current positions, unclear/stale separation, unchanged canonical counts,
linear source catalogs, conservative source/criteria binding, CSV mapped-row
provenance, source/canonical decision independence, detached output, optional
status/audit/handoff/snapshot/comparison projections, seven-file bundles and
portable UTF-8/control-safe exclusive-output CLI behavior. The fictional journey
checks four records, five assertions, one stale source match, no automatic
eligibility decision and unchanged input bytes. All 29 prior valid examples retain
equal core/report/audit/status/handoff/synthesis/comparison projections and report
CSV bytes, excluding implementation fingerprints. Informational assertions leave
existing planning/completion/synthesis bases unchanged. The initial model permits
one active assertion per exact record/reviewer label and performs no adjudication,
reviewer authentication, source retrieval, medical fact check or scientific review.
Publication audit and exact manifest verification pass; all new inputs are fictional.

Supplied screening-decision history increment (2026-11-04): 686 tests in the
suite; Linux run: 685 passed and one native-Windows-only test skipped. Thirty-seven
independent new tests cover strict completed decision documents, whole-input
staleness, explicit human choices without voting, before/after row preservation,
retained reviewer assertions, flat content-addressed source catalogs, historical
snapshot and receipt-chain integrity, canonical CSV source pointers, bounded
history, removed records, changed context and intervening manual edits. Before
and after assembly validate all supplied report/evidence structure, including
scalar and plural study links, without deleting downstream rows to accept a
conflicting exclusion. This is structural validation, not medical fact checking.
The focused eight-suite run passes 173 tests. All 30 prior valid examples retain
equal core/report/audit/status/handoff/synthesis/comparison projections and report
CSV bytes, excluding implementation fingerprints. A history-only recording leaves
the canonical projection and screening-review targets unchanged. Retrospective
comparison cues are not pending-work queues, and no receipt is selected as an
automatically authoritative or latest-by-date decision. Fictional CLI journeys
cover target, explicit assembly, inspection, comparison, audit and bundle checks,
including interleaved CSV imports without recursive decision-history copies.
Public APIs validate before and after mutation; strict JSON, UTF-8, control-safe
text and exclusive output creation remain enforced. Supplied identities, dates,
source locators and rationales are not authenticated, and historical whole-protocol
reconstruction, eligibility validity and scientific review are not claimed.
Publication audit and exact manifest verification pass; no private records or real
literature were used.

Supplied full-text report-review increment (2026-11-04): 729 tests in the suite;
Linux run: 728 passed and one native-Windows-only test skipped. Forty-three new
independent tests cover strict document/reviewer schemas, scalar/plural report
validation, exact source/reviewer identities, conservative document/provenance
binding, null versus supplied-but-unverified digests, removed-source/unretrieved
assertion retention, source-first scaffolds, no automatic opinion renewal and
canonical decision/study neutrality. The focused eight-suite run passes 187 tests.
All 31 prior valid examples retain equal core/report/audit/status/handoff/synthesis/
comparison projections and report CSV bytes, excluding implementation fingerprints.
A separate read-only review found no blocking correctness or overclaim issue and
reran all 43 new tests. Fictional CLI/audit/handoff/comparison/bundle journeys check
five reports, three source declarations and four positions, retaining unchanged
input bytes and canonical PRISMA counts. Multiple descriptors do not infer a
preferred version or exhaustive reading; reviewed coverage remains free text,
not a validated subset of document IDs. Every document digest is explicitly a
supplied assertion rather than a local byte measurement. Empty comparison cues
never imply source verification, agreement, complete reading or eligibility.
Whole-input validation occurs before selection; exclusive UTF-8/control-safe
output, duplicate-JSON rejection, import-cycle safety, linear source catalogs,
CSV-import enrichment and detached outputs are tested. Publication audit and
exact manifest verification pass. Only fictional inputs are included; no full
text, private records, external retrieval or medical facts were used or verified.

Exact report-study human-review increment (2026-11-04): 770 tests in the suite;
Linux run: 769 passed and one native-Windows-only test skipped. Forty-one new
regression tests independently exercise the supplied pair-position implementation:
strict schemas/dates/hashes and explicit source selections, exact tuple identity,
shared study IDs across reports, opposing sibling opinions, source-catalog versus
selected-subset binding, scalar/singleton migration and reordering, source removal,
retained orphan assertions, unknown/cross-report source rejection, fabricated
matching orphan-hash rejection, literal result-presence cues without filtering,
source-first blank scaffolds, whole-input validation and create-only UTF-8 CLI.
The focused seven-suite run passes 155 tests. All 32 prior valid examples retain
equal core/report/audit/status/handoff/synthesis/comparison outputs and exact CSV
bytes, excluding implementation fingerprints. The fictional CLI/audit/handoff/
comparison/bundle journey preserves three current memberships, two result rows,
five human assertions and one separately retained orphan pair view. Study opinions
never become canonical selection, report decisions, verified reading or independent
study identity. Orphans are not added to current-membership pending queues and
are not proof of historically valid membership. A current exclude-position with
result rows is only a literal navigation cue, never an invalid-result verdict or
a filtering instruction. Report-level source hashes remain unchanged by the new
ledger; the new pair presence flag intentionally changes when membership disappears.
Pre-inclusion study inventory remains outside this bounded increment. Publication
audit and exact manifest verification pass; no private records, real full text,
source retrieval, biological experiments or medical fact checks were used.

Descriptive pre-full-text-inclusion inventory increment (2026-11-04): 813 tests
in the suite; Linux run: 812 passed and one native-Windows-only test skipped.
Forty-three new independent tests cover exact descriptive schema/tuple identity,
multiple recorder assertions without a winner, explicit source selection, pending
and excluded reports, current/stale/unresolved source references, stable inventory
hashes across inclusion and membership changes, unchanged prior review hashes,
new-label proposals excluded from stored counts, whole-input validation, detached
linear catalogs and exclusive UTF-8/control-safe CLI output. The focused eight-suite
run passes 198 tests; all 33 prior valid examples retain equal core/report/audit/
status/handoff/synthesis/comparison projections and report CSV bytes, excluding
implementation fingerprints. A separate read-only review found no blocking issue.
An imported-CSV template omission was found before publication and repaired by
passing the validated mapped-row collection into candidate target preparation;
two regressions confirm source-first/completed scaffolds remain CURRENT_SOURCE.
The fictional CLI/audit/status/handoff/comparison/bundle journey retains five
assertions for four exact candidate pairs, four current and one stale, with no
new membership, extraction permission, queue or PRISMA node. Proposed targets are
not counted as stored inventory. Existing report constraints still require
title/abstract-included records: this is before full-text inclusion, not before
screening. Candidate eligibility-review migration remains deferred rather than
silently replacing the old membership-presence scope. Publication audit and exact
manifest verification pass. No real full text, private records, source retrieval,
scientific fact checking or biological experiment instructions were used.

Explicit local report-source byte-check increment (2026-11-04): 845 tests in the
suite; Linux run: 844 passed and one native-Windows-only test skipped. Thirty-two
new tests cover exact source/report/descriptor binding, null-digest source-first
scaffolds, whole-input validation before access, strict bounded manifests,
case-folded duplicate paths, unlisted sources, descriptor-versus-criteria context,
CSV mapped provenance, detached outputs and unchanged canonical/bundle bytes.
The focused seven-suite run passes 212 tests. All 34 prior valid examples retain
equal core/report/audit/status/handoff/synthesis/comparison projections and report
CSV bytes. The existing canonical engine files are unchanged by this standalone
command; its separate result fingerprints both itself and the reused artifact
checker. Independent read-only review found no blocking issue, ran the initial
26 new tests plus 56 artifact/inventory tests, and probed resource-limit and race
boundaries. Those probes became permanent tests for entry/aggregate limits,
same-size rewrite, stat/open replacement and unchanged unavailable retrieval.
The final 32-test suite passes locally. Native-Windows byte access is deliberately
unsupported and fails closed; cross-platform tests exercise that boundary rather
than claim source bytes were checked there. A fictional 225-byte file matches its
supplied descriptor while two other source IDs remain uninspected. Symlinked
roots/parents/files, hardlinks, FIFOs, missing files and changed reads do not become
successful observations. A match does not prove authenticity, reading, eligibility
or durable file state, and never changes protocol assertions or review hashes.
Only an explicit local manifest is inspected; locators remain inert. Source text
and discovered absolute filesystem paths are omitted, while supplied metadata and
relative mappings remain in the detached result and may still be sensitive.
Publication audit and exact manifest verification pass. No real document, private
record, source retrieval, scientific fact check or biological execution guidance
was used or added.

Detached full-text report-decision increment (2026-11-04): 875 tests in the suite;
Linux run: 874 passed and one native-Windows-only test skipped. Thirty new tests
cover blank human targets, strict dates/hash/schema types, literal scalar/plural
membership choices, retrieved pending/excluded transitions, controlled legacy
scalar removal, whole-input staleness, unchanged metadata and reviewer assertions,
source-linked inventory independence, preserved orphan study-review context, and
complete pre/post report reconciliation. Scalar-only inputs without optional
ledgers reject exclusions or membership changes that invalidate retained results.
The focused seven-suite run passes 234 tests. All 35 prior valid examples retain
equal core/report/audit/status/handoff/synthesis/comparison projections and report
CSV bytes. Canonical engine files remain unchanged; the separate application
record additionally fingerprints its decision implementation. An independent test
writer supplied 29 regressions and passed a 192-test report-family run; a separate
read-only code/document review found no implementation defect. A final transition
regression and explicit UTF-8 file reads were added before the final full run.
Replay rejects modified original inputs, candidate rows, target/context snapshots,
counts, hashes, unknown fields and changed implementation bindings. The tests
also deliberately allow a newly consistent, resealed rationale assertion: these
editable records are not authenticated or immutable historical evidence. CLI
round trips save one detached record first and export a new protocol only after
replay, reject collisions and malformed JSON, preserve original files, and escape
supplied controls. The documented fictional target/application/replay/comparison/
audit/seven-file-bundle journey succeeds. It includes report three only because
the human fixture expressly names candidate X, retaining all five descriptive
assertions and both prior result rows. No embedded history, review consensus,
source authenticity, reading, per-study scientific eligibility or chronological
authority is inferred. Publication audit and exact manifest verification pass.
No private inputs, real paper, medical fact checking or biological execution
instructions were used or added.

Opt-in document-linked source-work increment (2026-11-04): 896 tests in the suite;
Linux run: 895 passed and one native-Windows-only test skipped. Twenty-one new
regressions cover exact source/report/record linkage, strict opt-in lists and work
types, partial record intersection, null digests and unavailable retrieval,
selected-source deletion, whole same-report catalog changes, pointer-independent
bindings, supplied review/inventory exclusions, CSV-import provenance, direct-only
dependency propagation, completion guards and detached packet/export projections.
The focused nine-suite run passes 138 tests. All 35 prior valid example views
remain equal except implementation fingerprints. An isolated checkout of the
previous commit also confirms exact reports.csv and work-packages.csv bytes for
all 35 prior valid examples. Legacy source scopes and semantic planning/completion
hashes remain unchanged when document_source_ids is absent.
An independent test writer supplied 19 passing regressions. Separate read-only
review identified a direct-helper trust gap in an initial caller-supplied derived
binding map; the CLI/run path was not exposed. The final planning helper now
computes document bindings internally from source declarations and validated CSV
provenance and does not accept that external map. Two additional regressions cover
rejection and one-time opt-in preparation. Independent recheck passes 156 related
tests and confirms the route is closed, with no remaining findings.
The fictional four-work-package CLI/brief/handoff/comparison/bundle journey shows
that a selected document version edit stales own and direct-dependent completion
bindings, while recorded COMPLETE status and blocking stay unchanged. Transitive
and legacy bases retain their prior semantics; direct stale-prerequisite labels
remain visible. Conditional CSV columns preserve selected descriptors and context,
not document bytes or verification. Same-report unselected catalog changes can
stale the opted scope by design; unrelated report-source edits do not. No source
or work is selected automatically, and a matching hash never establishes reading,
acceptance, source authenticity or scientific readiness. Publication audit and
exact manifest verification pass. Only fictional sources and management records
were used; no real corpus, medical fact checking or biological execution guidance
was added.

Inventory-candidate eligibility-review increment (2026-11-04): 926 tests in the
suite; Linux run: 925 passed and one native-Windows-only test skipped. Thirty new
independent regressions cover exact schemas/identities, dates/hashes/selections,
whole ordered same-pair description bindings, source/criteria changes, eligibility
and membership independence, differing positions, stale description preservation,
known crossed-reference rejection, missing-reference retention only when stale,
and removed-description orphan views without fresh templates or queue entries.
The focused ten-suite run passes 260 tests. All 36 prior valid examples retain
equal core/report/audit/status/handoff/synthesis/comparison views except engine
fingerprints. An isolated checkout of the prior commit confirms exact reports.csv
and work-packages.csv bytes for all 36 examples. Existing membership-review,
planning and completion source semantics are not migrated or auto-renewed.
CLI tests cover full-input validation, exact selection, blank human fields and
source/description choices, create-only outputs, UTF-8 and escaped controls.
Mapped CSV-provenance enrichment produces current targets without dropping raw
collection context. Optional full-text decision snapshots retain exact same-report
candidate positions; explicit inclusion preserves those assertions and their
source labels, and exact-input replay rejects altered snapshots. No vote or
canonical study selection is inferred from any position.
The documented fictional inspection/template/status/handoff/audit/seven-file
bundle journey succeeds. Five review assertions retain four current-context
positions and one stale orphan; three described candidates have review cues.
The existing five descriptions and two result rows remain unchanged. A current
review of a stale description never upgrades the description or verifies reading.
No real source, private corpus, medical fact check or biological execution guidance
was used or added.
Independent read-only review found no blocking issue and confirmed relocation,
unrelated-description and review-metadata boundaries, full-removal orphan behavior,
removed-source retention, detached outputs and crossed-ID reuse rejection. Two
documentation qualifications were clarified: inherited search ordering can stale
source context, and only removed selected descriptions produce unresolved selected
IDs. Publication audit checks 200 text files and exact manifest verification passes.

Detached manual-result intake increment (2026-11-04): 944 tests in the suite;
Linux run: 943 passed and one native-Windows-only test skipped. Eighteen new
independent regressions cover completed candidate batches, strict schemas and
literal IDs, actual scalar/plural report memberships, same-report document
selections, explicit and implicit evidence-ID collisions, null findings, and
unchanged prior rows and unrelated protocol fields. The focused five-suite run
passes 118 tests. All 37 prior valid example projections remain exactly equal,
including implementation fingerprints. Every existing canonical engine file is
byte-for-byte unchanged; only the standalone intake fingerprints its new module.
CSV collection followed by supplied screening/report/source declarations, manual
result intake, exact replay and seven-file bundle verification succeeds without
mock extraction or modifying retained bibliographic history. Both original and
appended protocols undergo core and complete report reconciliation, covering the
legacy scalar-report validation path. Mock-adapter ledgers are explicitly refused.
Tests reject changed original inputs, candidate/source metadata, review targets,
implementation bytes, result rows, counts, receipt fields, unknown fields and
merely resealed derived data. A fully consistent alternate human assertion still
replays by design: these unsigned records are not authenticated history. Resource
bounds, strict JSON numbers, UTF-8/control-safe output, source-inert execution and
exclusive file creation are exercised. Independent read-only review found no
blocking issue and also probed source-location tampering, JSON schema number types,
symlink/input overwrite refusal and oversized file rejection before output.
The documented fictional target/explicit review/application/replay/audit/bundle
journey succeeds. Two explicit result rows are appended to the two existing rows;
all report counts and included study labels stay unchanged. The null-finding row
is retained as supplied text. Document associations and human extraction/review
metadata remain only in the detached application record, not a new persistent
protocol binding. Later ordinary views or bundle verification do not check those
associations; original inputs, detached records and code must be retained separately.
Publication audit checks 204 text files and exact manifest verification passes.
No private corpus, real source retrieval, medical fact checking or biological
execution guidance was used or added.

Detached result-source comparison increment (2026-11-04): 969 tests in the suite;
Linux run: 968 passed and one native-Windows-only test skipped. Twenty-five new
independent tests cover replay-first failure, engine drift, full-current-input
validation, exact explicit evidence IDs without implicit legacy fallback, raw-row
changes, and original record/report/study mapping separately from a moved current
result. They also cover scalar/plural declaration changes, eligibility versus
retrieval/source context, missing/moved/unsupplied descriptors, whole same-report
catalog and criteria/search drift, pointer relocation, unrelated inputs, shared
report counts, JSON type distinctions, validated CSV provenance and detached
nested outputs. The focused five-suite run passes 135 tests.
All 37 prior valid example projections, including implementation fingerprints,
remain exactly equal. Canonical engine files and result_intake.py remain byte-for-
byte unchanged, and the previously saved manual intake application still replays.
The new tool adds its own fingerprint without changing the earlier receipt's
implementation inputs. CLI tests exercise strict UTF-8/JSON, quoted controls,
exclusive output creation, input preservation and the 50 MB input/output bounds.
Independent read-only review found no blocking issue and confirmed additional
whitespace-sensitive identity, absent-report, number-type and duplicate-ID probes.
A documentation sentence was qualified to distinguish explicit pointer scope
fields from nested current-mapping pointer names.
The fictional CLI comparison matches its documented independent counts: one
changed and one unchanged result, two unchanged original mappings and current
row links, one unchanged report assertion, one changed shared report-source
context, and two changed versus one unchanged selected-source references. Repeated
source selections are counted per candidate; shared contexts count original report
IDs. No combined current/approved verdict hides those units. Source locations
remain historical assertions, not verified or renewed reading; exact matches do
not establish lineage, source authenticity, clinical validity or extraction
completeness. No protocol state or persistent provenance ledger is written.
Publication audit checks 208 text files and exact manifest verification passes.
No private corpus, real document access, medical fact check or biological execution
guidance was used or added.

Explicit result-text correction increment (2026-11-04): 994 tests in the suite;
Linux run: 993 passed and one native-Windows-only test skipped. Twenty-five new
tests cover exact in-place result/limitations corrections, preserved IDs/order/
opaque fields/counts, multiple corrections in supplied order, a 100-row batch,
strict schemas/dates, no-op and prohibited-field rejection, explicit raw IDs
without implicit fallback, same-report source selections and null digests.
They also cover complete original/candidate validation including scalar report
guards, CSV provenance preservation, mock-adapter rejection, blank human review,
input/proposal/implementation drift, exact replay and resealed tampering, and
the distinction between reproducibility and authenticated reviewer identity.
The focused six-suite run passes 121 tests. The independent read-only audit ran
the full suite and found no blocking issue; additional literal whitespace,
Unicode/control-character ID and opaque numeric-type probes passed.
All 38 prior valid example projections, including implementation fingerprints,
remain exactly equal. Every pre-existing tracked Python file is byte-unchanged,
including manual intake and source comparison, and a previously saved intake
application still replays. An earlier intake's source comparison reports a
corrected imported row as CHANGED without renewing its historical associations.
Existing appraisals/condition/work assertions remain literally unchanged; an
affected source-bound completion becomes stale under the existing engine rule,
while its recorded COMPLETE status remains unchanged. This is not a claim that
all downstream assertions have bindings or are automatically reassessed.
The documented fictional CLI target/review/assembly/replay/comparison/bundle
journey succeeds: one result wording and one limitation change, while four result
rows, one included report and three included study labels remain unchanged.
Strict JSON/UTF-8, quoted controls, exclusive output creation, input preservation
and byte bounds (including encoded text/JSON before file creation) are exercised.
The separate unsigned correction record retains before/after rows and supplied
source selections. Ordinary protocol bundles do not retain or verify that record.
Publication audit checks 212 text files and exact manifest verification passes.
No source reading, actual research corpus, medical verification, biological
execution guidance, automatic scientific approval or downstream review renewal
was performed or added.

Manual extraction worksheet increment (2026-11-04): 1,018 tests in the suite;
Linux run: 1,017 passed and one native-Windows-only test skipped. Twenty-four new
independently written tests cover mandatory exact report/study/record selections,
scalar/plural membership, whole-protocol validation, multiple mapped records,
same-label studies in different reports, original raw rows and implicit ID origins,
missing-result pairs, available-but-unselected sources, null/non-null digests,
and source-less eligible reports with deliberately unfinished candidates.
Tests preserve full context assertions while selecting only exact typed record or
existing pair-result intersections. Search membership and shared report labels do
not infer context applicability. Human assertions remain unchanged, and all new
scientific fields, extraction IDs, dates and source choices remain unfilled.
Further tests cover deep output detachment, opaque numeric types, validated CSV
provenance, fingerprints, no external actions, strict JSON/UTF-8, quoted controls,
exclusive output files and final encoded output bounds. The focused six-suite
run passes 142 tests. Independent read-only implementation/documentation review
found no blocking issue; existing and dangling output-symlink probes fail safely.
All 38 prior valid example projections, including implementation fingerprints,
remain exactly equal. Every pre-existing Python file remains byte-unchanged.
Previously saved manual intake and correction application records still replay.
The new fictional worksheet reports one existing pair-result, one selected-record
result and two available source descriptors. It shows the exact selected-record
context and existing-result context without inheriting the search-only context or
another study's context. Full context assertions retain their other references,
while matched subsets are separately visible. No new candidate applicability is
asserted. The blank candidate fails intake as intended; after explicit fictional
manual filling, the existing target/review/assembly/replay/bundle journey succeeds.
Publication audit checks 216 text files and exact manifest verification passes.
No actual source reading, private corpus, medical fact checking, biological
execution guidance, inferred findings or automated scientific approval was added.

Supplied-condition intake increment (2026-11-04): 1,042 tests in the suite;
Linux run: 1,041 passed and one native-Windows-only test skipped. Twenty-four new
independently written tests cover append-only preservation, absent/empty stages,
existing-condition prefixes, ordered raw evidence snapshots, raw explicit IDs,
report/study/source ownership, condition-ID collisions and outcome reassignment,
cross-record/study rejection, existing nested reporting-state rules, optional
sampling/statistics coverage, textual values, and the 100-candidate boundary.
The focused eight-suite run passes 144 tests. Blank or stale human reviews fail;
full replay rejects altered/resealed counts, snapshots, targets and candidates,
while consistently reauthored unsigned assertions remain explicitly unauthenticated.
Tests cover deep detachment, exact schema/date checks, implementation fingerprints,
strict UTF-8/JSON, quoted controls, exclusive output and encoded size bounds before
file creation. Independent read-only implementation/documentation review found no
production issue, with additional mock/source-mutation, output-symlink, surrogate,
BOM and overflowing-number probes. The final full suite passes after corrections
to test-only fixture/helper assumptions; no production defect was found.
Valid CSV and mock-adapter condition enrichment preserve earlier provenance.
The mock test establishes reports and source descriptors in the original base;
later descriptor/report/result changes still fail existing integrity checks.
CSV import through result intake/correction and condition enrichment retains both
earlier replay records. Existing planning/synthesis/completion assertions remain
literally unchanged while established source-binding checks expose affected
staleness; no completion status or human review is automatically renewed.
All 39 prior valid example projections, including implementation fingerprints,
remain exactly equal. Every pre-existing Python file, including condition schema,
intake and correction implementations, remains byte-unchanged. Previously saved
intake/correction records still replay. The fictional CLI target/review/assembly/
replay/status/comparison/bundle journey succeeds: two comparison descriptions
cover three of four result rows, leaving result B unlinked, with record/report
flows unchanged. The absent stage's null unlinked queue remains distinct from a
supplied empty ledger. Counts concern stored condition pairs, never independent
experimental units, biological replicates or sample size.
Publication audit checks 220 text files and exact manifest verification passes.
Whole-condition document associations and human metadata remain detached from
the enriched protocol and ordinary bundle. No real source reading, scientific or
clinical fact verification, generated experimental parameter, biological execution
instruction, numerical calculation or causal acceptance was performed or added.

Local PubMed NBIB preparation increment (2026-11-04): 1,060 tests in the suite;
Linux run: 1,059 passed and one native-Windows-only test skipped. Eighteen new
independently written tests cover strict fixed-column parsing, initial BOM,
UTF-8 and mixed physical line endings, exact record/field spans, repeated authors,
folded values, unknown tags, repeated PMID occurrences, literal leading zeros,
malformed/orphan fields, ambiguous record boundaries and zero/invalid identifiers.
The focused six-suite run passes 145 tests. Independent read-only review found
no blocking issue; an additional 80-case synthetic probe verifies complete byte
partition, mixed line endings, controls, repeated identifiers, CSV preservation
and full conversion replay. During implementation review, a bare-CR CSV quoting
edge was found and fixed by quoting every derived cell; the regression passes.
Tampered/resealed and unknown fields, boolean/integer substitutions, altered
implementation hashes, non-JSON values, cycles, overflowing bounds and invalid
protocols fail closed. CLI tests cover strict JSON/UTF-8, unfilled required inputs,
safe text, exclusive output and serialization preflight before file creation.
Symlink probes run where the host permits creating symlinks.
The entirely fictional CLI preview/native verification/CSV extraction/review/
assembly/status/audit/bundle journey succeeds. Three native occurrences remain
three collection rows; explicit fictional choices map them to two canonical
search memberships. The search remains incomplete with two pending records and
no screening, report or evidence decisions. Independent tests also cover an
explicit withheld occurrence and retained native columns in screening targets.
The unchanged CSV ledger retains each record's original text, ordered field JSON,
native spans and full-file hash. The separate native wrapper must accompany the
protocol for full-file separator/BOM provenance and conversion replay; ordinary
bundle verification does not independently verify or embed that wrapper.
All 39 prior valid example projections, including implementation fingerprints,
remain exactly equal. Every pre-existing Python file is byte-unchanged, and
previously saved result-intake, result-correction and condition-intake records
still replay. Publication audit checks 225 text files and exact manifest
verification passes. This supports a documented strict subset, not every NBIB
variant. No provider connection, real citation/paper corpus, source authentication,
automatic identity resolution, completeness or medical-validity assertion,
biological execution instruction or generated scientific finding was added.

Portable native collection bundle increment (2026-11-04): 1,080 tests in the suite;
Linux run: 1,079 passed and one native-Windows-only test skipped. Twenty new
independently authored tests cover exact native-wrapper-to-historical-intake
association, receipt/intake/wrapper/source hashes, deterministic selection order,
mixed CSV/NBIB imports, partial attachment, duplicate/missing/unmatched selections,
same native bytes under different searches, later legitimate protocol enrichment,
and preservation of exact protocol/native bytes without input mutation. The
focused five-suite run passes 115 tests. Unknown or changed derived payloads,
resealed native fields and summaries, altered base/receipt/engine metadata,
boolean/integer substitutions and invalid JSON fail closed.
Archive tests reject outer and nested duplicate, traversal, unexpected, symlink
and compressed entries; direct encrypted-header, CRC and oversized-entry probes
also fail. Prefix/trailing bytes and changed ZIP metadata fail canonical replay.
Verification never extracts files. Bounds include the stored ZIP overhead, and
inclusive-limit tests pass. CLI tests cover strict local input, filenames with
equals signs, exclusive output, available-host symlink probes and rendering
preflight failures before file creation. Independent read-only implementation
and documentation review found no issue requiring changes and separately probed
nested hostile entries and metadata changes, including resealed outer hashes.
The fictional CLI packages the previously reviewed three-occurrence/two-record
NBIB collection, verifies its native association and unchanged ordinary research
bundle, and preserves its one incomplete search with no new research decisions.
Other tests show uncovered imports explicitly without inferring whether their
origin was CSV or an unsupplied native wrapper. No archive is uploaded or shared.
All 39 prior valid example projections, including implementation fingerprints,
remain exactly equal. Every pre-existing Python file is byte-unchanged; saved
NBIB preparation, result-intake, result-correction and condition-intake artifacts
still replay. Publication audit checks 228 text files and exact manifest
verification passes. Consistency remains distinct from source or reviewer
authentication, publication identity, search completeness and scientific validity.
No real corpus, live retrieval, biological execution guidance or automated review
renewal was added.

Human-authored source-work intake increment (2026-11-04): 1,107 tests in the suite;
Linux run: 1,106 passed and one native-Windows-only test skipped. Twenty-seven new
independently written tests cover intentionally incomplete templates, explicit
task IDs/meaning/dependencies, strict proposal/review schemas and calendar dates,
existing and same-batch dependency chains, cycles, legacy implicit-ID collisions,
append-only raw preservation and exact existing planning/completion bases.
The focused eight-suite run passes 151 tests. Missing planned-search receipts,
unscreened/excluded records and absent/empty report stages are handled without
inventing eligibility, reports or evidence. Present malformed legacy reports
still fail the full report validator even where core run alone permits them.
Source contexts and selected documents retain existing exact-reference rules;
valid mock, CSV and NBIB-derived import provenance survives work enrichment.
Entire replay rejects stale reviews, altered/resealed snapshots or candidates,
extra fields, typed substitutions and implementation drift. Strict JSON, cycles,
UTF-8, quoted controls, byte limits, exclusive output, available-host symlink
refusal and serialization preflight are covered. No source URL or external
process is invoked. Independent read-only implementation/documentation review
found no blocking issue and separately checked helper-fingerprint and proposal
changes invalidate review, example replay and documentation links.
Implementation review removed an inappropriate report-presence requirement so
pre-search and pre-screening protocols remain supported. It also clarified that
actual source/context/document references persist in the appended work, while
proposal metadata, human review and retained source snapshots remain detached.
The fictional CLI draft/target/review/assembly/replay/work-packet/status/audit/
bundle journey succeeds: work grows from two to four, both additions PLANNED;
the secondary search stays missing, r2 stays excluded, and no evidence is added.
The deliberately unfinished draft fails intake. Existing record/report flows,
statuses, receipts, planning ranks and completion assertions remain unchanged.
All 39 prior valid example projections, including implementation fingerprints,
remain exactly equal. Every pre-existing Python file is byte-unchanged; saved
NBIB preparation, native collection bundle, result-intake, result-correction and
condition-intake records still verify. Publication audit checks 233 text files
and exact manifest verification passes. No task meaning, priority, dependency,
completion, experimental procedure or scientific/clinical judgment is generated.

Source-work Windows output correction (2026-11-04): exact-head CI for 4d983ad
passed both Ubuntu environments but failed both Windows environments on the
existing dangling-symlink CLI regression. Windows exclusive open followed that
dangling final entry and created its target. The source-work output helper now
checks the final entry with lstat, rejects every observed existing entry, catches
only FileNotFoundError and retains exclusive creation. Other inspection errors
propagate without opening the output. Two additional focused regressions check
this preflight independently of host behavior; the original native symlink test
remains. This is not atomic protection against concurrent path replacement or
parent-directory aliases, as stated in the helper and guide.
The revised suite contains 1,109 tests: Linux 1,108 passed, one native-Windows-only
test skipped. The focused eight-suite run passes 153 tests. Independent review
confirmed the scoped fix and error propagation. The revised fictional target/
review/assembly/replay journey passes, and all 39 earlier example projections
remain unchanged. Source-work implementation fingerprints change intentionally;
artifacts made with the earlier implementation require that recorded revision,
not an automatically renewed review. No underlying research engine or other
intake implementation changed. Publication audit and exact manifest validation
pass; native Windows confirmation is performed on the corrective commit's CI.

Multiple-file NBIB preparation increment (2026-11-04): 1,122 tests in the suite;
Linux run: 1,121 passed and one native-Windows-only test skipped. Thirteen new
batch tests cover exact separate native files, BOM/line endings/separators,
repeated fields, identical bytes and within/across-file repeated PMID strings,
source-local byte spans, explicit ordered labels and one deterministic CSV intake.
The focused five-suite run passes 91 tests. Independent implementation review
also ran the original 10 batch tests and 78 existing intake/review/collection tests,
found no blocking defect, and independently challenged stale review reuse after
file additions, reordering, relabeling, separator changes and timestamp changes.
Those stale-review cases are now committed regressions. Formula/whitespace-leading
labels remain literal, with an explicit warning that raw derivative CSV is not
spreadsheet-safe; output quoting does not neutralize formulas. The README now
clearly limits existing native collection bundles to single-file wrappers.
Strict source schemas and labels, aggregate/per-file limits, strict JSON, full
canonical replay, altered/resealed fields, implementation drift, serialization
preflight, exclusive creation, dangling symlinks and inspection-error propagation
are covered. Final-entry protection retains the documented race/ancestor-alias
limitation; actual Windows behavior is checked on this commit's CI matrix.
The documented fictional CLI preparation/verification/template/target/review/
assembly/status/audit/ordinary-bundle journey succeeds with two source files and
five raw occurrences. Explicit fixture choices promote four occurrences to two
canonical memberships and withhold one row, retaining every original value.
Exactly one incomplete search is appended; its total is unknown, the secondary
planned search remains missing, and screening/evidence stay empty. The separate
batch wrapper retains native files and verifies independently; an ordinary bundle
retains the CSV provenance but does not independently verify native batch parsing.
Existing Python implementation files are byte-unchanged, preserving previous
engine fingerprints and replay behavior. New documentation links resolve;
publication audit checks 237 text files, and exact manifest verification passes.
No live acquisition, automatic deduplication, query/page association validation,
review renewal, scientific conclusion or completeness claim is introduced.

Portable native batch collection increment (2026-11-04): 1,153 tests in the suite;
Linux run: 1,152 passed and one native-Windows-only test skipped. Thirty-one
independently written batch-archive tests pass, with 108 passing tests in the
focused five-suite intake/review/collection run. A separate independent code
audit could not be started because the worker limit was reached; implementation
self-review and independently authored regression tests are not represented as
that additional audit or as scientific validation.
The new opt-in format retains exact original native members alongside their
batch wrappers and the unchanged ordinary research bundle. Tests cover exact
BOM/line-ending/source-span bytes, repeated identifiers and identical files,
generated import/source paths, partial attachment, exact historical common-base
binding after later enrichment, stale/mismatched wrappers, canonical ordering,
strict types, per-wrapper/aggregate quotas and implementation fingerprints.
Hostile ZIP, duplicate/extra/missing/traversal/symlink/compression/encryption/CRC/
size attacks and resealed wrapper/source/binding/summary changes are rejected.
All verification is in memory without extraction or network connections. CLI
JSON/text paths and create API preflight serialization before exclusive output;
dangling final entries are rejected through the existing batch output guard.
The documented synthetic CLI packaging/replay succeeds for the prior increment's
unchanged two-file/five-occurrence batch and explicitly reviewed protocol. Both
standalone native members equal their retained originals and SHA-256 values.
Copying only the archive into a separate temporary working directory and running
the verifier there succeeds without the original input locations. Replay still
requires a separate checkout of the recorded implementation; source code is not
embedded. Earlier saved batch preparation and ordinary research ZIP also verify.
All 122 previously committed Python files remain byte-unchanged, so existing
single-file collection and intake implementation fingerprints are preserved.
Documentation links resolve, publication audit checks 240 text files, and exact
manifest verification passes. Packaging does not import records, renew review,
infer native formats for unselected imports, deduplicate source occurrences or
establish complete retrieval, source authenticity, human authenticity or research
readiness. Windows and both supported Python versions are checked in exact-head CI.

Explicit supplied report registration increment (2026-11-04): 1,172 tests in the
suite; final Linux run: 1,171 passed and one native-Windows-only test skipped.
Nineteen new self-authored regression tests pass; the focused eight-suite report,
PRISMA, full-text decision, result, condition and bibliographic run passes 186.
Neither an independent test author nor a separate independent code auditor could
be started for this increment because the worker limit was reached. These tests
and implementation self-review are not represented as independent review or as
scientific validation.
The new detached intake registers explicitly grouped included records as new
reports and optionally appends supplied document declarations. Full-text choices
remain pending. Tests cover record/report unit differences, all three supplied
retrieval states, unavailable versus excluded reports, absent versus supplied
empty stages, duplicate/collision/mapped-record refusal, no study-ID inference,
exact raw-prefix preservation, source targets and unverified document hashes.
Stale review, altered/resealed application, implementation drift, strict JSON,
quotas, invalid dates, UTF-8/quoted display, serialization preflight, exclusive
output, dangling final entries and inspection errors are checked. Existing mock
adapter receipts lock report declarations; this intake explicitly refuses those
contexts rather than rebasing or deleting their provenance. The supported manual
and bibliographic-import paths preserve their original collection associations.
The fictional CLI draft/target/review/assembly/replay/export/status/PRISMA/review-
template/ordinary-bundle journey succeeds. Six records and four included records
remain unchanged while registration adds three sought reports: one retrieved,
one not retrieved, one retrieval-pending, zero assessed or included reports,
zero studies and zero extracted results. Unknown search totals and a missing
planned search remain visible. A separate synthetic test continues from one
registered report through an explicit full-text choice, supplied result, explicit
missing nonclinical metadata and verified ordinary bundle without deriving an
experimental parameter. Existing report retrieval or document versions are not
updated by this registration-only operation.
All 124 previously committed Python files remain byte-unchanged, preserving
existing engine fingerprints. Previously saved native batch collection and
ordinary research archives still verify. Documentation links resolve, publication
audit checks 246 text files, and exact manifest verification passes. No external
acquisition, source authenticity, reading, human authenticity, inferred identity,
review renewal, complete searching or scientific conclusion is established.
The exact-head CI matrix checks Windows and both supported Python versions.

Explicit supplied retrieval update increment (2026-11-04): 1,193 tests in the
suite; final Linux run: 1,192 passed and one native-Windows-only test skipped.
Twenty-one new self-authored tests pass, and the focused nine-suite report,
retrieval, PRISMA, decision, source-review, study-inventory/study-review and
bibliographic run passes 249. Worker limits still prevent independent test
authorship and a separate independent code audit; this increment has self-review
and regression coverage, not independent or scientific validation.
Only pending-to-unavailable/retrieved and unavailable-to-retrieved transitions
are accepted for existing unassessed reports. Tests cover exact record/report
identity preservation, retrieval partitions without new eligibility decisions,
prior raw retrieval/locator/reason snapshots, absent/empty source stages, explicit
nulls, source-prefix retention and supplied but unverified document hashes.
Existing report reviews and descriptive study inventories become stale when the
source context changes; their original assertions remain unchanged and orphan
study positions are not promoted into memberships. New source declarations that
conflict with retained orphan references are rejected without erasing history.
Mock adapter contexts stay locked. The bibliographic path retains exact imports
and mapped record source hashes. Same-state changes, reversals, existing retrieved
report changes, unknown reports, source replacement and unsupported identity/
eligibility/study fields are refused. Strict JSON and quotas, stale review/code,
resealed tamper, UTF-8/control display, no network, serialization preflight,
exclusive output and dangling final entries are checked.
The documented synthetic CLI sequence continues from the unchanged prior report
registration application. Six records, four included records and three sought
reports remain fixed; the new supplied state has two retrieved reports, one not
retrieved, none retrieval-pending, two awaiting assessment, and no included or
excluded reports, studies or results. A separate explicit full-text choice and
ordinary bundle also replay in the regression journey. Unknown search totals,
missing planned sources and completeness/readiness limits remain visible.
All 126 previously committed Python files remain byte-unchanged. The saved report
registration application, prior native batch collection archive and earlier
ordinary research bundle still verify. Changed documentation links resolve;
publication audit checks 251 text files and exact manifest verification passes.
No actual retrieval, document reading, source/identity authentication, automatic
review renewal, nonclinical parameter generation or completeness claim is made.
Historical retrieval values are retained only with the detached receipt and
original, not as a new protocol event ledger. Windows and both supported Python
versions are checked by exact-head CI.

Native batch-to-evidence rehearsal increment (2026-11-04): 1,201 tests in the
suite; final Linux run: 1,200 passed and one native-Windows-only test skipped.
Eight new self-authored walkthrough tests execute all 30 documentation commands
in order in an external temporary directory whose name contains spaces, with
ASCII environment defaults to exercise explicit UTF-8 CLI behavior. The focused
eight-suite batch/archive/report/retrieval/result/condition/PRISMA run passes 148.
The worker limit still prevents a separate independent author/auditor; this is
self-review and regression testing, not independent review or scientific review.
Fourteen prewritten fictional JSON inputs provide every explicit choice. Blank
collection, screening, registration, retrieval, full-text, result and condition
targets remain blank and match the separately supplied fixture hashes. No runtime
module changes or automatic review helper is introduced; all 128 previously
committed Python files remain byte-unchanged.
The same five raw NBIB occurrences are preserved through one explicit same-record
choice, one non-promotion and three new record declarations. Four promoted raw
occurrences become three search memberships; the search-ledger identified count
is three, not five, and its repeated-exact-ID count is zero. The guide explicitly
distinguishes these scopes from raw-row reconciliation, publication identity and
PRISMA duplicate-removal claims. Separate supplied screening, report grouping,
retrieval, full-text and result steps lead to three included records, two retrieved
reports, one assessed/included report, one pending assessment, one declared study
and two result rows. One record anchors both results; the other mapped record is
not given a fabricated extraction. Nonclinical concentration, exposure, comparator,
observation timing/reference event and causal basis remain explicitly unknown.
Tests verify unchanged source/import and screening history, exact per-stage target
bindings, rejection of stale fixture reuse, no output overwrites, raw native member
bytes, and archive verification after copying only the archive into another
working directory. The archive retains the historical native import binding after
later evidence additions, but not the detached applications or all intermediate
originals. The guide requires retaining the complete output directory and recorded
implementation and does not call the ZIP a complete review-history archive.
Unknown search totals, an absent planned secondary search and unassessed report
remain visible; census and conclusion readiness stay closed. Documentation links
resolve, publication audit checks 267 text files and exact manifest verification
passes. No real-source acquisition, reading, review, scientific conclusion or
experimental parameter generation is represented. Exact-head CI covers Windows
and both supported Python versions.

Portable report-transition segment increment (2026-11-04): 1,226 tests in the
suite; final Linux run: 1,225 passed and one native-Windows-only test skipped.
Twenty-five independently authored tests pass, with 134 passing tests in the
focused six-suite transition/registration/retrieval/decision/walkthrough/native-
archive run. An independent read-only gap assessment informed the narrow segment
scope. A separate independent code audit could not be performed; implementation
self-review and independent regression tests are not represented as that audit.
The optional stored ZIP retains exact initial-protocol, ordered application and
endpoint-protocol bytes, including Unicode and whitespace, while canonical JSON
binds each next original to the preceding candidate. Only existing registration,
retrieval-update and full-text application verifiers can dispatch. Their original
validation and implementation bindings remain authoritative. All 129 previously
committed Python files are byte-unchanged, including existing bundle engines.
Tests cover valid contiguous prefixes/suffixes, three distinct step kinds,
20-step inclusive bounds, omitted/reordered/duplicate/stale steps, full endpoint
comparison including Boolean/integer distinctions, altered/resealed applications,
strict JSON/schema/types, wrapper/verifier fingerprints and aggregate byte limits.
Hostile paths, extra/missing/duplicate/code members, symlink/compressed/encrypted
entries, CRC/size attacks, archive comments/order/metadata/trailing bytes and
resealed chain/summary/manifest tampering are refused. Verification uses in-memory
reads only; no source locator, extraction or embedded-code execution occurs.
Exclusive output, final dangling entries, inspection failures and API/CLI
serialization preflight are covered; the documented race/parent-alias limitations
remain. Explicit negative claims keep earlier/later history unassessed, complete
history unestablished, human/source authenticity unverified and execution/review
renewal unperformed.
The existing 30-command NBIB-to-evidence recipe and the new two-command segment
recipe execute successfully against the same synthetic outputs. Registration,
retrieval and full-text replay end exactly at included.json, before results and
conditions. Supplying the later final.json as this segment's endpoint is rejected
without creating an archive. The eight-member segment preserves all five exact
input/application files and verifies after copying only the ZIP into a separate
working directory with the recorded implementation available. It contains no
native source files, document files, ordinary research ZIP or implementation code,
and is not called a complete review-history archive.
Saved prior registration, batch-native collection and ordinary research artifacts
still verify. Documentation links resolve, publication audit checks 270 text files
and exact manifest verification passes. No actual reading, source acquisition,
human authentication, eligibility validity, complete searching or scientific
readiness is established. Exact-head CI checks both supported Python versions on
Windows and Ubuntu.

Supplied-workflow handoff discovery increment (2026-11-04): 1,237 tests in the
suite; final Linux run: 1,236 passed and one native-Windows-only test skipped.
Eleven new self-authored navigation tests pass; the focused seven-suite handoff,
receipt, archive and walkthrough run passes 124 tests. Independent read-only code
review examined implementation, focused tests and documentation, ran 99 existing
handoff/archive/walkthrough tests plus all 11 new tests, and found no blockers.
Its two suggested improvements were incorporated: expose native verification as
the CSV-intake export route, and distinguish execution of existing verifiers from
loading/executing embedded code.
The additive handoff catalog has ten static workflow groups and 41 valid parser-
help entry points. Every --help array was executed independently and by tests;
all return usage without creating output files. Linked guides cover native
collection, explicit screening, report registration/retrieval/full-text choices,
result/condition intake, optional source-review work and distinct archive scopes.
The catalog is identical across manual, bibliographic and mock contexts and WP
selections. It is discovery, not applicability, queue-based eligibility, automatic
selection or a recommended task order. No protocol ID/path is interpolated into
these arrays and the handoff never executes them. Unsupported mock contexts and
missing human inputs remain explicit rather than inferred away.
The original mock manual_input_workflow object, queues, matching-row navigation,
selected-work scope, protocol hash and closed scientific bounds are preserved.
Independent old/new comparison confirms equality after excluding the two additive
catalog fields and the expected handoff implementation fingerprint. Tests cover
deep-copy isolation, deterministic output, malicious/control display strings,
unchanged protocol bytes, malformed-input refusal, no network/execution and JSON/
text CLI use with paths containing spaces and a leading-dash work ID.
Only review_handoff.py changed among 131 previously committed Python files. It is
outside the research-bundle engine and intake/segment verifier fingerprint sets;
all prior replay engines and receipt targets remain unchanged. Saved registration,
report-transition, native batch collection and ordinary research artifacts still
verify. Documentation links resolve, publication audit checks 271 text files and
exact manifest verification passes. Native archives remain selected-source
association checks; report-transition archives remain report-only segments, not
complete research history. No new research operation, scientific assessment,
source retrieval, task generation, parameter inference or readiness claim occurs.
Exact-head CI checks Windows and Ubuntu with both supported Python versions.

Result-review continuation discovery increment (2026-11-04): 1,238 tests in the
suite; final Linux run: 1,237 passed and one native-Windows-only test skipped.
The focused handoff/intake/source-comparison/correction run passes 95 tests.
Independent read-only assessment identified the missing existing continuation;
independent code review found no issues and passed 77 handoff/source-comparison/
correction tests, including all 45 parser-help commands in empty temporary
working directories. The navigation tests are self-authored, independently reviewed
and executed, not independently authored scientific tests.
One static result_review_continuation group now connects the existing original
manual-result input/application/current comparison to the separate exact-target
result-text correction workflow. It does not select a correction because source
context changed. Guidance keeps literal drift separate from historical lineage,
source approval and scientific correctness; a corrected copy must not be imported
under a new ID merely to avoid collisions. Only result/limitations wording is
correctable by the existing operation; result IDs, order and counts stay intact.
Prior reviews and detached source associations are not renewed, and downstream
assertions are not all reassessed. Required original inputs and recorded code
remain explicit. The catalog now has eleven groups and 45 help-only entry points.
Tests retain static output across empty/manual/mock and populated result contexts,
no command execution, source access or input mutation, deep-copy isolation, safe
rendering, unchanged queues and closed readiness bounds. Independent old/new
comparison across five contexts confirms equality after excluding the new group
and the expected handoff self-fingerprint scope. Existing research-bundle, intake,
source-comparison and correction implementation hashes exactly match the previous
commit; only handoff runtime and its navigation test changed among prior Python
files. A saved report-transition archive still verifies. Guide links resolve,
publication audit checks 271 text files and exact manifest verification passes.
No new module, schema, protocol mutation operation or source-retrieval capability
is introduced. Exact-head CI covers Windows/Ubuntu with Python 3.10 and 3.12.

Second planned-search continuation rehearsal (2026-11-04): 1,247 tests in the
suite; final Linux run: 1,246 passed and one native-Windows-only test skipped.
The focused collection/native-archive/source-comparison/walkthrough run passes
99 tests. Seventeen walkthrough tests now exercise the original 30 commands plus
13 continuation commands; nine new assertions cover the added path. A separate
manual execution of all 43 documented commands also passes. All inputs and
review/identity decisions are prewritten fictional software-test assertions.
A new independent assessment/review worker could not be created because of the
agent limit. This increment received self-review and regression execution, not a
separate independent code audit; earlier independent handoff reviews do not cover
this new walkthrough.
The continuation uses the original ledger-free common base for a native wrapper
and the later result/condition-enriched protocol for exact collection review.
The already declared, unused secondary search explicitly links one row to record A
and introduces record D awaiting screening. No new engine is added: existing
reconciliation already supports this operation. Tests retain every earlier output
file byte, the original import prefix, screening history, reports/sources, results,
conditions and version label. Only a second incomplete search and flat historical
import receipt are appended. Wrong current review targets, intermediate-base reuse,
immutable-plan edits and repeated executed search IDs are rejected.
Accounting remains unit-specific: seven raw rows, six promoted row occurrences,
one withheld row, five search memberships, four exact record IDs and one repeated
exact-ID membership across searches. There are still two retrieved reports, one
included study and two result rows; new record D is pending and report B remains
unassessed. Zero missing planned searches does not clear incomplete searches,
unknown totals, missing conditions or scientific-readiness bounds.
The prior result application still replays against its actual original. Current
result rows, mappings and selected document descriptors are unchanged, while one
shared report-source context changes because record A gains a search occurrence.
Both result rows reference that context, not two changed documents. The retained
screening receipt reports STALE_SOURCE while matches_current_screening remains
true; no eligibility decision, review renewal, correction or re-import is inferred.
A verified two-wrapper native archive preserves three exact original NBIB files
and both historical import bindings, and verifies after relocation with the
recorded implementation available. Wrong-index wrapper substitution is rejected.
Detached applications and the entire intermediate history remain outside this
archive's coverage. All runtime Python files and old review targets are unchanged;
only the existing walkthrough test file changes among prior Python files.
Guide links resolve, publication audit checks 275 text files and exact manifest
verification passes. No actual retrieval, reading, source authentication, identity
resolution, scientific review or completeness claim is performed. Exact-head CI
checks Windows and Ubuntu with both supported Python versions.

Source-preserving RIS intake increment (2026-11-04): 1,280 tests in the suite;
final Linux run: 1,279 passed and one native-Windows-only test skipped. Thirty-three
new self-authored tests pass; the focused RIS/NBIB/reconciliation/navigation run
passes 89 tests. All eleven documented CLI commands also run against an outside,
space-named directory using an explicitly fictional supplied review. Independent
code review could not be performed for this increment. Self-review, these tests
and the manual software rehearsal are not represented as an independent audit,
provider-format conformance testing or actual literature review.
The new standalone parser and wrapper preserve an explicit fixed-column UTF-8 RIS
subset: TY/empty-ER framing, ordered repeated/unknown fields, optional initial BOM,
CR/LF/CRLF endings, six-space continuations and exact full-file/record/field spans.
Malformed framing, absent ER, orphan content, NUL/invalid UTF-8, unsupported
padding/continuations, blank lines inside records and legacy encodings fail closed.
Unindented multiline abstracts remain outside this initial subset; the tool does
not silently repair originals or claim universal RIS compatibility. Primary format
context references are linked in the guide, without copying translator code or
using actual publication data.
File-hash plus positional occurrence labels supply the CSV's required ID/locator
fields. They are not DOI, URL, publication identity or stable cross-file IDs.
DO/ID/AN/UR/attachment fields are neither selected nor resolved. Identical records,
repeated identifiers and conflicting fields remain distinct ordered occurrences;
identifier-free records are retained. CSV duplicate-ID/overlap hints therefore
compare only these occurrence labels and cannot establish absence of publication
duplicates. Existing explicit reconciliation still requires complete human row
choices and a separate exact-current-input review, then appends only an incomplete
search. Fictional four-row reconciliation retains three promoted raw occurrences,
one withheld occurrence and two canonical memberships, without screening/results.
Tests cover literal/Unicode/BOM/mixed-line byte reconstruction, forty seeded
supported exports, exact inclusive byte/line/record bounds, derivative expansion
and unchanged interpreter CSV field limits, entire-input validation, strict JSON
and type handling, tampering/resealed targets, unknown fields and implementation
drift. Cross-format wrappers are not guessed or interchanged. CLI tests cover
Unicode under ASCII locale settings, spaces, mutual output exclusion, read-only
inputs, exclusive output, observed dangling entries, inspection refusal and
serialization-before-write. Native source URLs and attachment locators remain
inert; no external call or source-document access occurs.
A second unused planned RIS search retains prior screening and the flat common-
base import history. Ordinary research bundles verify the resulting CSV ledger,
not the native RIS wrapper; existing NBIB collection archives do not accept it.
The exact wrapper and recorded implementation must be retained separately. No
RIS archive, mixed-format archive, automatic deduplication, source authentication,
completeness assertion, scientific decision or review renewal is added.
Only the existing read-only handoff and its navigation test changed among prior
Python files; the catalog now exposes 47 parser-help entrypoints. All prior intake,
review and bundle engines remain byte-unchanged. Saved registration, report-
transition, two-search native collection and ordinary research artifacts still
verify, as does the newly retained RIS wrapper. Guide links resolve, publication
audit checks 281 text files and exact manifest verification passes. Exact-head CI
covers Windows/Ubuntu with Python 3.10 and 3.12. Census and readiness stay closed.

Explicitly typed native archive increment (2026-11-04): 1,324 tests in the suite;
final Linux run: 1,323 passed and one native-Windows-only test skipped. Forty-four
new archive tests pass, and the final related native/reconciliation/archive/
navigation run passes 197 tests. An independent reviewer inspected the actual new
archive module, static discovery wiring and guide, and ran 51 separate named
synthetic checks against the final runtime SHA-256
5487359956a56b3fd89fd60a89ba92e7e283efc51cdcb0642cfd52d13cc9f046.
No concrete implementation defect was found within that targeted review. A wording
overstatement about re-zipping was corrected: identical canonical bytes remain
valid; changed bytes do not. These checks are not a comprehensive security audit,
resource-exhaustion proof, provider-format conformance test or scientific review.
The independent checks are separate from, not added to, the unittest suite count.

The new opt-in native_collection_bundle.py accepts only explicit ris, nbib and
nbib_batch selections. Each selected wrapper is validated by its format-specific
existing verifier and must match the entire historical CSV intake reconstructed
with the ledger's original common base. No file/format/index/identity association
is inferred. Unique zero-based import indices, exact types, closed format dispatch,
strict wrapper validation and full canonical archive regeneration reject alternate
formats, wrong historical imports and resealed derived-output changes. Existing
intake, review and archive formats remain unchanged and are not reinterpreted.

A mixed synthetic project carries three wrappers, four original native files and
one uncovered CSV import in one archive. Each import has explicit covered/uncovered
status; uncovered formats are not guessed and coverage is not search completeness.
Original RIS BOM/newlines/separators, repeated native fields, identical NBIB files
and source occurrence order are retained. Single-file sources receive no invented
source labels; batch labels remain inert metadata and never determine paths.
The new ZIP preserves the exact protocol inside unchanged research.zip, normalized
wrapper JSON, separately retained source bytes and exact historical bindings.
Four documented create/verify CLI commands and a separate relocated verification
pass outside the repository. The original four-row RIS rehearsal is also bound
without changing its three promoted/one withheld rows or two pending memberships.
A separately retained enriched two-search workflow also binds both batch wrappers
and three original files while preserving its exact protocol and two result rows.

Tests cover all six wrong-format pairings, same source bytes under different
searches/times, mixed and partial selections, cross-format duplicate indices,
source/path/type/count/hash/coverage tampering, implementation drift, exact size
boundaries, strict JSON and noncanonical ZIPs. Existing archive adversarial cases
are applied to the new format, including traversal, duplicate names, symlinks,
compression/encryption, CRC and exaggerated-size headers, nested archives,
prefix/trailer bytes and metadata changes. Byte-identical canonical re-packing is
explicitly accepted. Exclusive output, observed dangling links, Unicode/ASCII
streams, equals/space paths and preflight failures are covered. Independent read
spying observed only local implementation-file reads, not supplied locators;
network and archive-extraction guards were not called.

All 31 prior files in the new archive's replay-engine dependency set remain
byte-unchanged. Previously saved RIS, batch-native, ordinary research, report-
registration and report-transition artifacts still verify. Only read-only handoff
navigation changes among existing runtime Python files; its catalog now exposes
49 help-only entrypoints in the same eleven groups. Tests and guide links are
updated to distinguish the separate new archive from the unchanged RIS wrapper
and older NBIB-only formats. Publication audit checks 284 text files and the exact
manifest verifies. Exact-head CI covers Windows/Ubuntu with Python 3.10 and 3.12.

Unsupported scope remains explicit: no additional RIS dialects, multi-file RIS
intake, mixed-format search intake, embedded runtime, detached application history,
full research-history archive, downloaded source documents, source/reviewer
identity authentication or review renewal. File-size limits are not hard memory/
CPU limits; exclusive creation is not an atomic path-race defense. No actual
literature, private research data, source retrieval, automated deduplication,
scientific decision or completeness assertion is introduced. Census and readiness
remain NOT_ESTABLISHED and NOT_READY respectively.
