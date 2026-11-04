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
