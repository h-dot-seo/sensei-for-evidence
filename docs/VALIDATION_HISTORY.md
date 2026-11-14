# Validation history

This file holds every dated entry of the validation record in the order it was written,
from the 2026-11-02 release preparation to the latest change. On 2026-11-08 the root
[VALIDATION.md](../VALIDATION.md) became a short current snapshot (release, CI matrix, local
verification, what is not claimed), and its chronological entries moved here unchanged;
only the original `# Validation record` heading was replaced by this title. Each entry
records what was added, what was tested, the counts observed at that time and what was
not claimed. Test counts and platform notes describe the run they were written in; they
are not updated retroactively, and the public CI history remains the record of the
published heads.

Release preparation date: 2026-11-02 (Asia/Seoul).

- Python standard-library unittest: 4 synthetic tests passed.
- Limited public-file/type/secret-pattern scan: passed.
- Manual selected-content review: no actual conversation, researcher corpus, private
  configuration, credential, real experiment or article/book/figure asset selected.
- Examples: synthetic; no scientific validation claimed.
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

Fourth increment: CLI end-to-end scenarios and failure recovery added. Local tests: 15 passed. Remote CI status is recorded in the repository's GitHub Actions history.

Fifth increment: 18 local tests passed. New CLI paths, source boundaries, deterministic output and tamper/no-overwrite checks are covered. Remote matrix CI results are in the GitHub Actions history.

Consolidation (2026-11-03): the fifth-increment ZIP/CSV/summary exporter was
consolidated with implementation fingerprinting, strict JSON parsing and
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

Reviewed descriptive inventory intake increment (2026-11-04): 1,360 tests in the
suite; final Linux run: 1,359 passed and one native-Windows-only test skipped.
Thirty-six new tests cover this workflow: 28 general tests and eight separately
authored regression tests focused on review staleness and CSV provenance. The
final related inventory/reconciliation/full-text/navigation suite passes 177
tests. An independent reviewer inspected the actual new runtime, fixture, guide
and static discovery wiring. The reusable independent probe ran 54 passing tests:
11 new targeted probes plus 43 existing inventory regressions. Three supplemental
checks covered 100 candidates, sequential appends and inert source locators.
No blocking implementation defect was found. Documentation was clarified to
scope JSON output claims to this intake and distinguish new assertions from
already-stored rows. This is targeted code review and synthetic verification, not
a comprehensive security audit, scientific review, provider validation or proof
of source/reviewer identity. Runtime SHA-256 reviewed and tested:
6944a2bbeab09b9afc61a9c8374f4e06805ba439354c5297dfdfe4e119850057.

The new inventory_intake.py connects existing descriptive candidate study
inventory to template, target, assemble and verify commands. The unfinished draft
fills only explicitly selected report/study IDs and the current inventory source
basis. Description, assertion ID, recorder, date, location and source selection
remain null; no eligibility or scientific field is invented. Completed new rows
require retrieved reports, existing same-report descriptors, explicit source IDs
and the exact current source context. Pending, included and excluded retrieved
reports are supported without changing their decisions or memberships. Stale new
assertions, invalid source selections, duplicate IDs/recorder tuples and mock
adapter contexts are rejected rather than repaired or stripped.

Targets include the whole original protocol, ordered candidates, current
report/record/inventory source context, explicit selected descriptors and exact
implementation. Mapped CSV provenance is included. A separate explicit review is
required before append; blank human fields, changed unrelated context, changed
candidates, stale targets or implementation drift fail. Assembly preserves all
prior raw fields, including old inventory assertions, opaque metadata, version,
searches, CSV ledger, screening, memberships, results, sources and work. Exact
record/report flow equality is checked. The detached receipt records before/after
inventory counts, review assertions and source snapshots, and full replay checks
every field rather than trusting editable checksums.

All nine documented CLI commands pass using only supplied fictional review data
in an outside, space-named directory. The example adds one description: assertions
5 to 6 and described pairs 4 to 5; the original stale description remains stale.
Five reports, three included study labels, two result rows and existing accounting
remain unchanged. A separate regression proves that the described candidate is
still ineligible for an extraction worksheet until a separate explicit full-text
choice declares membership. Even then, scientific result fields remain blank and
the unfinished extraction is rejected by result intake.

Independent regression tests cover pending/included pairs and all supported
human eligibility positions. Adding a second recorder's description to the same
pair makes the old eligibility review stale while preserving its raw assertion,
canonical memberships and results. An unrelated pair does not stale that review.
Report-wide source catalog changes, including an unselected descriptor, remain
bound. Existing stale/orphan history is retained; a new stale assertion is refused.
No review winner, consensus, renewal, new task or downstream scientific reassessment
is inferred. Persistent inventory rows/source hashes are distinguished from the
detached import review and source snapshots.

Other tests cover strict JSON/container types, cycles/surrogates/nonfinite values,
real dates, exact schema/row/byte limits, literal preservation, whole-input invalidity,
reordered candidates, resealed replay attacks, source selection and file safety.
CLI coverage includes all commands, Unicode under ASCII streams, spaces/equals in
paths, exclusive output and observed dangling symlinks, inspection failure and
encoding/rendering-before-write. Source URLs/paths are inert; independent read
tracing observed only the expected implementation files. No document was acquired,
opened, interpreted or authenticated.

All 32 prior files in the combined relevant native/archive/intake replay dependency
sets remain byte-unchanged. Saved RIS, NBIB batch, typed native archive, ordinary
research, report registration and report-transition artifacts still verify.
Only read-only handoff navigation changes among existing runtime Python files;
its catalog now has twelve groups and 53 help-only entrypoints. Publication audit
checks 289 text files and exact manifest verification passes. Exact-head CI covers
Windows/Ubuntu with Python 3.10 and 3.12.

Unsupported scope stays explicit: no editing/replacing old inventory assertions,
review renewal, identity resolution, automatic study discovery or inclusion,
source-document authentication, verified chronology, complete extraction or
full-history packaging. Ordinary bundles do not retain/replay this application;
original input, application and recorded code must be retained separately. Output
size limits are not hard memory/CPU ceilings, and exclusive creation is not an
atomic defense against concurrent path replacement. Census and readiness remain
NOT_ESTABLISHED and NOT_READY. Real/private research stays outside the repository.

Portable extraction-transition archive increment (2026-11-04): the new standalone
extraction_transition_bundle.py retains exact initial/application/endpoint bytes
for an explicitly ordered contiguous segment of result intake, result-text
correction and descriptive condition intake. Every step uses its unchanged
existing verifier, and full canonical JSON equality binds each transition and
the endpoint. It does not mutate protocols, infer ordering, repair missing steps,
renew a review or claim a complete/authenticated research history.

Independent review found one direct-helper fingerprint omission during development:
nbib_intake.py and source_work_intake.py were used but not in the inherited verifier
engine maps. The new wrapper now fingerprints both helpers explicitly; no existing
runtime dependency was modified. Independent final-runtime review and 36 separately
executed synthetic acceptance/adversarial checks pass against SHA-256:
4f9c744ee8f34b095d0b1c794421b1e2a39f16b3726bf7a9ec61c5f31f554f66.
These are targeted code/probe checks, not a comprehensive security or scientific
audit, provider validation, source authentication or proof of execution.

The 27 general archive tests cover deterministic exact bytes, strict JSON,
canonical-versus-raw equality, literal Unicode, bool/int distinction, all supported
verifiers, valid prefix/suffix segments and repeated kinds, invalid missing/reordered
or repeated transitions, whole-input drift and resealed application tampering.
ZIP tests cover generated member allowlists, missing/duplicate/extra paths, embedded
code, symlink/type flags, compression, CRC, encryption flags, metadata, ordering,
comments and prefix/trailing bytes. Byte-identical canonical repacking is accepted.
Bounds cover exactly 20 versus 21 steps and inclusive archive-byte limits. API/CLI
checks cover relocation, spaces/equals in paths, ASCII process streams, exclusive
creation, observed dangling links, inspection failure and output preflight.

Eight independently authored context regressions retain exact source selections,
ordering, literal locations, supplied reviews and pre-correction result text.
A condition recorded before correction keeps its earlier evidence snapshot rather
than rebinding it to the endpoint. An archived intake remains replayable and can
be used with the separate source-context comparison against changed final wording
or later descriptor drift. Existing current/stale review assertions remain raw
and unchanged; correction can make completion context stale without changing its
supplied COMPLETE status or renewing its assertion. Existing bibliographic ledgers
and mapped raw-source context survive every supported extraction step.

All eleven CLI commands in the new synthetic guide passed using an outside,
space-named output directory and explicitly fictional reviews. The fixture appends
two result rows (2 to 4), corrects two existing text fields without adding results,
and appends two descriptive condition records. Extracted study labels increase
2 to 3 during result intake, while report-stage counts and membership stay fixed.
Independent documentation review caught and corrected an overly broad claim that
all PRISMA accounting was unchanged. Two additional documented commands archive
and verify the existing NBIB walkthrough's result/condition segment; its initial
canonical fingerprint equals the earlier report segment's endpoint. This is a
boundary match between supplied segments, not proof of complete research history.
The documentation also limits omitted/reordered-step rejection to changes that
break exact replay, rather than implying detection of unrecorded reversible history.

The related extraction/intake/correction/condition/source-comparison/navigation
suite passes 140 tests. A new discovery regression adds the separate extraction
archive route while preserving static, protocol-independent, help-only behavior.
The catalog now has thirteen groups and 55 parser-help entrypoints; no queue,
identity, clinical/scientific decision or execution recommendation is inferred.
All 41 prior files in the combined relevant extraction/native/report/inventory
replay dependency sets remain byte-unchanged. Saved typed native, NBIB batch,
report-transition, inventory application and ordinary research artifacts still
verify. Only read-only handoff navigation changes among existing runtime files.

Unsupported scope remains explicit: no collection/screening/report/inventory or
other mutations as extraction steps, no source documents/native citation files or
runtime embedded, no source updates, current endpoint source approval, automatic
review renewal, downstream scientific reassessment or complete-history claim.
Recorded source associations apply only to their recorded step context. Old
receipts remain unchanged; this separate archive preserves them rather than
rewriting their original snapshot-bundle caveats. No actual literature, private
research, experimental instructions or clinical inference is introduced. The
50 MB archive limit is not a hard CPU/memory ceiling, and exclusive creation is
not an atomic path-race/ancestor-alias defense. Census/extraction completeness
remain NOT_ESTABLISHED, and conclusions remain NOT_READY.

Final full Linux suite: 1,396 tests, 1,395 passed and one native-Windows-only test
skipped (265.508 seconds). The increment adds 36 tests: 27 archive tests, eight
independently authored context tests and one static discovery regression. Python
compilation, changed-guide links and whitespace checks pass. Publication audit
checks 293 text files and exact manifest verification passes with 292 listed files.
Exact-head CI uses the existing Ubuntu/Windows by Python 3.10/3.12 matrix.

Reviewed source-declaration append increment (2026-11-04): the new
report_source_intake.py connects already retrieved reports to template, target,
assemble and verify commands for explicit new source descriptors. It fills the
practical gap between initial report registration/retrieval transitions and later
supplements or separately declared versions. This operation never fetches or
reads a document, computes a document digest, edits/replaces an old descriptor,
selects a preferred version, changes eligibility or renews a prior assertion.

The candidate document uses the existing five-field source schema with separate
supplied declarer/date/note metadata. Templates fill only an explicitly selected
report ID; human fields and source identity/locator/version remain null, with an
explicit null digest allowed for unbound bytes. Completed rows require real dates,
new globally unique IDs and a retrieved report, irrespective of pending/included/
excluded full-text choice. A valid-looking digest remains an unverified supplied
assertion. Distinct IDs with matching locator/digest remain distinct; no identity
merging or current-version selection occurs. New rows can be appended to absent,
empty or existing source stages without changing old catalog order.

An independent reviewer inspected actual runtime code and documentation and
independently authored 13 context regressions. All 13 pass in this POSIX environment;
the one actual safe local-byte observation is skipped on unsupported platforms,
while no-read template behavior remains tested. The combined new intake/context
suite passes 34 tests, and the related source/report/study/inventory/work/navigation
suite passes 215. Additional read-only probes rejected 14 malformed/collision
cases, stale targets and tampered receipts. No actionable runtime defect was found,
and local import fingerprint coverage was checked. This is targeted code review
and synthetic software testing, not a comprehensive security or scientific audit,
provider validation, or proof of source/people identity. Runtime SHA-256:
b17449bbe2eb1c04309b398d9e3a431dfa1eee7a25486f6c1cb8cf59a671218b.

The 21 general intake tests cover unfinished templates/reviews, exact append and
all-other-field preservation, retrieved eligibility variants, rejected unavailable/
unknown reports, source-ID collisions, strict document/row/review shapes and JSON
types, real dates, literal Unicode, explicit null/digest validation, whole-input/
candidate-order/implementation review binding, before/after catalogs and pointers,
resealed replay attacks, whole-input invalidity and mock-context refusal. Bounds
cover 100 versus 101 candidates, input sizes and serialized outputs. API/CLI tests
exercise inert locators, Unicode under ASCII process streams, spaces/equals in paths,
all commands, ordinary research snapshots, exclusive output, observed dangling
links, inspection failures and rendering/encoding preflight.

Independent context tests show that even an unselected new descriptor on the same
report can stale retained full-text/study/inventory positions and descriptive
inventory source bindings; unrelated report contexts stay unchanged. Document-bound
work and its direct dependents can become stale while supplied COMPLETE assertions
remain untouched. An indirect dependent or work without document-source opt-in is
not automatically rebound or invalidated. New IDs conflicting with retained stale
references on another report fail whole-protocol validation. CSV import ledgers,
search context and mapped raw-row provenance are preserved. Separate result-source
comparison distinguishes unchanged selected descriptors/results from changed whole
report catalogs; no result-source association is automatically repaired.

A retained null-digest descriptor stays unbound when a new descriptor has a supplied
digest. A separate explicit local byte comparison can match the new source while
leaving old declarations, review hashes and protocol verification claims unchanged.
The test uses only short fictional bytes. Actual byte access remains the existing
checker’s POSIX-only safe path; native Windows/unsupported access fails closed.
No source read, authentication or review completion is inferred by this intake.

All nine documented synthetic CLI commands passed in an outside, space-named
output directory with explicitly fictional review metadata. The fixture adds two
source declarations (four to six) while preserving every other raw field and
record/report flow. Before/after report views show stale context without renewal;
the separate byte-check template retains null path/size and performs no inspection.
Ordinary bundle creation/verification succeeds for the enriched protocol.

All 42 prior files in the combined relevant source/extraction/native/report/inventory
replay dependency sets remain byte-unchanged. Saved extraction-transition, typed
native, report-transition, inventory application, NBIB batch and ordinary research
artifacts all continue to verify. The only existing runtime change is read-only
handoff navigation. Its catalog now has fourteen groups and 61 help-only entrypoints,
including source-declaration and separate byte-check routes; no file is inspected
or operation recommended/executed merely by discovering the route.

Limits remain 100 candidates, 10 MB candidate/review inputs and 50 MB protocol/
application inputs/outputs, not hard CPU/memory ceilings. Exclusive output creation
is not an atomic path-race/ancestor-alias defense. Ordinary archives do not retain
this detached review/declaration history, and existing transition archive kinds
are deliberately not expanded. Old descriptors cannot be edited, removed, silently
filled or superseded here. No actual literature, private source data, experimental
procedure or clinical inference is introduced. Census stays NOT_ESTABLISHED and
conclusions NOT_READY.

Final full Linux suite: 1,431 tests, 1,430 passed and one native-Windows-only test
skipped (415.691 seconds). This increment adds 35 tests: 21 general intake tests,
13 independently authored context regressions and one static discovery test.
Compilation, changed-guide links and whitespace checks pass. Publication audit
checks 298 text files; exact manifest verification passes with 297 listed files.
The existing exact-head CI matrix covers Ubuntu/Windows and Python 3.10/3.12.

Reviewed evidence-work intake increment (2026-11-04): evidence_work_intake.py adds
a separate template/target/assemble/verify path from existing supplied results to
explicitly authored PLANNED evidence-review work. Source-work intake keeps its
narrower existing contract. No scientific question, deliverable, acceptance
criterion, dependency, priority, completion, clinical recommendation or experiment
is generated; these task fields require supplied human content and a separate
exact-target import review.

Independent code, fixture, documentation and discovery review found no actionable
runtime defect. The independent reviewer authored all 38 new intake regressions,
which pass, and ran 130 combined new/neighboring tests successfully. Those 130
include the new intake and existing source intake, navigation, document scope,
context and manual result intake checks; they are not 130 newly authored tests.
The independent test also executes all twelve documented CLI commands with
explicit fictional review metadata. These are targeted synthetic code/workflow
checks, not a comprehensive security or scientific audit or provider/source
validation. Reviewed runtime SHA-256:
3acbfaed060e19235f9fd2d16de15a3352e4c2893d83906622288af153a52fa4.

Templates copy only explicit existing normalized result IDs and fixed
PLANNED/evidence_review structure. Work ID, question, deliverable, acceptance
criterion, depends_on and proposer/date/note remain null; no missing dependency is
silently treated as independence. Existing raw evidence IDs are used exactly.
Legacy rows lacking evidence_id use the engine's established record_id identity,
exposed as LEGACY_RECORD_ID versus EXPLICIT_EVIDENCE_ID in target snapshots. Raw
rows are never rewritten to materialize defaults. An arbitrary record/report/
study label cannot substitute for a different explicit result ID.

New candidates must have nonempty unique known result IDs, explicit dependencies,
real dates and only permitted fields. Optional context/context_ids preserve the
existing evidence-scoped overlap rules without deciding guideline/development
applicability. Source refs and own document_source_ids are rejected. Explicit
source-work dependencies retain the existing direct document-context binding;
there is no automatic source-work conversion, transfer of selected documents,
transitive approval or evidence creation. Existing and same-batch prerequisites,
including forward references, are supported; unknown/self/duplicate/cyclic links
are rejected. Completed/in-progress work, artifact/acceptance/completion fields,
priority ranks, new planning assertions and unknown fields cannot enter here.

Targets retain the whole original input and ordered proposals, appended work
snapshots, original raw/normalized result snapshots and pointers, identity origins,
mapped record provenance, new planning targets and implementation fingerprints.
Appended-work pointers address the candidate; selected-result pointers address
the original. Assembly appends only supplied work objects and checks preservation
of every existing raw field and work prefix, normalized old work, research flows,
results and old planning/completion targets/assertions. CSV and mock provenance
remain under the existing integrity validators. Full replay compares the complete
record; changed input/result/candidate/implementation or resealed tampering fails.
Consistently rewritten unsigned assertions can still replay and are not proof of
identity, chronology, independent review or execution.

The independent tests cover legacy evidence/work IDs without materialization,
repeated result selection across different tasks, unfinished templates and blank
reviews, strict JSON/schema/type/date validation, all prohibited work fields,
context mismatch, explicit document-scoped source dependencies, existing current/
stale planning/completion assertions, CSV/mock provenance, exact snapshots,
whole-input validation, replay/engine binding, candidate/byte limits, mutability,
UTF-8/control escaping and no network/source opening. CLI tests cover all commands,
strict malformed inputs, exclusive outputs, actual available symlink behavior,
mocked dangling-entry/inspection failures and output rendering/encoding preflight.
Absence of reports remains distinct from an explicitly empty report catalog, which
cannot coexist with extracted evidence under existing report membership checks.

The twelve-command extraction-to-work guide was separately executed outside the
repository in a space-named directory. Result intake first grows result rows from
two to four. Work intake then grows work packages from two to four with all four
results and record/report accounting unchanged. One new task explicitly depends
on existing source-review work, and the second depends on the first. Both remain
PLANNED and blocked by their supplied unfinished prerequisite; no priority or
execution is inferred. Packet, status, PRISMA audit and ordinary research bundle
views retain the explicit links and limits. The compatible standalone fixture also
passes without deleting current extraction or fabricating evidence.

All 43 prior files in the combined relevant work/source/extraction/native/report/
inventory replay dependency sets remain byte-unchanged. Seven saved artifact kinds
continue to verify: source-declaration application, extraction-transition archive,
typed native archive, report-transition archive, inventory application, NBIB batch
archive and ordinary research bundle. Among existing runtime files only read-only
handoff discovery changes. The catalog now has fifteen groups and 65 help-only
entrypoints. The added route is static and does not infer task applicability,
execute commands or change existing source-work navigation.

Persisted work/result/context links and dependencies are distinguished from
separate proposal/review assertions and historical result snapshots. Ordinary
archives do not retain this application/original input; existing transition archive
kinds are not expanded. Existing work edits, progress/completion, project-wide
replanning, scientific/clinical decisions and current extraction-source approval
remain unsupported. Limits are 100 candidates, 10 MB reference/candidate/review
inputs and 50 MB protocols/applications, not hard CPU/memory ceilings. Exclusive
creation is not an atomic path-race/ancestor-alias defense. All fixtures are
synthetic; census remains NOT_ESTABLISHED and conclusions NOT_READY.

Final full Linux suite: 1,470 tests, 1,469 passed and one native-Windows-only test
skipped (278.490 seconds). The increment adds 39 tests: 38 independently authored
intake/workflow regressions and one static discovery regression. Compilation,
changed-guide links and whitespace checks pass. Publication audit checks 303 text
files; exact manifest verification passes with 302 listed files. The existing
exact-head CI matrix covers Ubuntu/Windows and Python 3.10/3.12.

## Reviewed work-completion increment (2026-11-04)

Added a separate single-work completion intake without changing the research,
planning or completion engine. A blank template selects only an existing
unfinished normalized work ID. A supplied candidate names an artifact locator,
exact true acceptance assertion and literal completer/date/note. A separately
filled exact-target review is required before COMPLETE, locator, acceptance and
the reviewed current completion binding are recorded. No artifact is accessed and
no acceptance criterion is independently assessed. Existing COMPLETE work cannot
be refreshed, reopened or replaced, including stale/unbound assertions.

All other raw fields and rows remain unchanged, including implicit raw IDs,
source/evidence links, document catalogs, extraction, contexts, reviews and opaque
metadata. Every planning assertion and basis remains unchanged. Other work's
completion assertions and bases remain unchanged. Completing a prerequisite can
change dependent normalized blocked_by lists without editing dependent raw work;
the target and receipt expose these derived changes. Stale/unbound COMPLETE
prerequisites remain visible and satisfy the unchanged engine's dependency rule;
this is not a recursive acceptance certificate or a hidden new gate.

The fifteen documented commands were executed outside the repository in a
space-named directory and separately as a regression test. Existing reviewed work
intake first grows two work packages to four without changing four result rows.
Two separately reviewed fictional completion applications then mark the source
limitations note and the result-linked traceability note COMPLETE. The dependent
limitations task becomes unblocked but stays PLANNED. Both new completion bindings
match current metadata. Research flows, result rows and planning bases are
unchanged; census remains NOT_ESTABLISHED and conclusions NOT_READY. The generated
ordinary research archive verifies, but does not contain detached completion
history. Existing report/extraction archive kinds are deliberately not expanded.

Actual independent code/document review found no substantive defect. The worker
independently authored focused regression tests rather than merely reviewing the
parent's tests. This is a targeted software review, not a comprehensive security,
artifact-authenticity or scientific audit. The final validation counts are recorded
below. The parent-authored exact guide journey and static discovery test are
separate from the independent tests.

All 45 prior files in the combined work/source/inventory/extraction/native/report/
batch/research replay dependency sets remain byte-unchanged. Eight saved artifact
kinds still verify: evidence-work application, source-declaration application,
inventory application, extraction-transition archive, typed native archive,
report-transition archive, NBIB batch archive and ordinary research archive.
Among existing runtime files only read-only handoff discovery changes: sixteen
static groups and 69 help-only entrypoints. Discovery neither selects applicable
work nor runs the suggested commands.

The first standalone discovery run encountered a 30-second process timeout in
unchanged report_source_check.py check --help while the host was slow. Its unchanged
rerun passed all 16 tests and all 69 help entrypoints in 17.619 seconds; no timeout
was weakened. The combined neighboring regression suite passed 190 tests in
24.606 seconds before any later independent test additions.

Candidate/review limits remain 10 MB and protocol/application limits 50 MB, with
one selected completion per application, not hard CPU/memory ceilings. Output
preparation and exclusive creation do not guarantee atomic path-race or ancestor
alias protection. Completer/reviewer labels and dates are unsigned assertions,
not identity or chronology verification. Supplied completion notes, reviews and
snapshots remain detached from the persisted four fields. No work is executed,
source review renewed, clinical guideline approved or development stage advanced.

The independent final suite has 23 passing tests (3.997 seconds), including
current/stale planning-rank preservation, mock adapter integrity and CSV collection
provenance. Its actual code/docs review checked runtime SHA-256
`b8c8318b5914f2aabd5bb134d2a79db13bc19f22b22229d17cc23a5ab7952494`.
These checks are distinct from native-platform CI and do not claim adversarial
path-race testing or inspection of any real research deliverable.

Final full Linux suite: 1,495 tests, 1,494 passed and one native-Windows-only test
skipped (283.235 seconds), including all three late-added independent regressions.
This increment adds 25 tests: 23 independently authored intake regressions, one
parent-authored fifteen-command journey and one static discovery regression.
The final focused intake/journey suite also passed all 24 tests. Compilation,
98 changed-guide local links, whitespace and limited publication checks pass.
Publication audit checks 309 text files; exact manifest verification passes with
308 listed files. The existing exact-head remote matrix runs Ubuntu/Windows and
Python 3.10/3.12; its terminal status is verified separately after publication.

## Portable reviewed work-history increment (2026-11-04)

Added a separate work-transition archive, supporting only reviewed source-work
intake, evidence-work intake and single-work completion applications. It retains
exact initial/application/endpoint bytes and replays explicitly ordered steps
through the unchanged existing verifiers. Whole-protocol canonical equality
connects steps, including opaque metadata and JSON scalar types. No automatic
rebase, review renewal, completion renewal, status editing or work execution occurs.

The closed stored ZIP keeps generated regular-file paths, fixed metadata, raw and
canonical hashes, receipt identifiers, explicit selected work IDs and recorded
implementation fingerprints. Exact regeneration compares the entire archive byte
sequence rather than trusting editable manifest checksums. Directly used JSON,
file-reading and exclusive-output helpers are fingerprinted. No embedded code,
source document, artifact bytes, native citation file or credential is added or
executed. A byte-identical canonical repack is accepted; changed metadata or
archive bytes fail the canonical byte receipt.

The tests adapt the existing archive regression matrix and add work-specific
context cases. They cover deterministic/raw-byte retention, exact prefix/suffix
segments, ordering and omitted/duplicate/stale applications, strict schema/JSON,
unsupported kinds, full protocol equality, resealed tampering, helper changes,
malformed paths/ZIP types/CRC/sizes/encryption, 20-step and inclusive-byte bounds,
relocation, no network/extraction, explicit output refusal and rendering preflight.
The contextual cases check retained proposal/completer/reviewer snapshots,
explicit targets versus derived dependency effects, preserved stale completion
and planning assertions, later source amendment versus historical replay,
unrecorded inter-step changes, source-only zero-result work, control-quoted work
IDs and the actual documented thirteen-command journey.

The thirteen CLI commands were also executed outside the repository in a
space-named directory. Source-work intake grows two tasks to three; evidence-work
intake grows three to four; one separately reviewed completion keeps four tasks
and completes only the document-trace note. The result-delivery note becomes
mechanically unblocked but remains PLANNED. Four result rows, report accounting,
old tasks and research remain unchanged. The three-step archive has eight members
and 170,641 bytes for this particular generated rehearsal. It verifies after
relocation. An additional earlier evidence-work/two-completion segment also
packages and verifies without rewriting its saved application records.

All 46 prior files in the combined work/source/inventory/extraction/native/report/
batch/research replay dependency sets remain byte-unchanged. Nine saved artifact
kinds still verify: work-completion, evidence-work, source-declaration and inventory
applications; extraction-transition, native, report-transition and NBIB-batch
archives; and an ordinary research archive. Among existing runtime files only
read-only handoff discovery changes, to seventeen static groups and 71 help-only
entrypoints. Its 17-test discovery suite passed in 16.378 seconds. The combined
related regression suite passed 178 tests in 146.290 seconds.

Actual independent review was not performed for this increment. All new runtime,
adapted tests, work-context tests and documentation received implementation-author
review only. The previous intake and extraction-archive independent reviews are
not an independent audit of this new wrapper. No comprehensive security audit,
real artifact inspection, source authentication or scientific validation is
claimed. Native cross-platform checks remain a separate CI result.

Historical snapshots and completion bindings apply only to their recorded step
context. A later document amendment can stale a persisted completion while the
older archive still verifies; it does not renew approval for the changed input.
Existing stale/unbound COMPLETE prerequisites remain unchanged and can satisfy the
original engine's dependency rule. Explicit selected work IDs are not a complete
list of derived blocking effects. Unsigned assertions cannot authenticate people,
chronology, actual work or complete project history. Collection, screening,
report/source/inventory and extraction transitions are not supported steps here.

Limits remain 1–20 steps and 50 MB stored/retained bytes, not hard memory/CPU
ceilings. Exclusive outputs do not provide an atomic path-race or ancestor-alias
defense. Supplied text is not redacted. Synthetic fixtures only; no source/artifact
locator is followed, no criteria are assessed, and census/conclusion labels remain
NOT_ESTABLISHED/NOT_READY. The exact full-suite and publication counts follow.

Final full Linux suite: 1,532 tests, 1,531 passed and one native-Windows-only test
skipped (357.814 seconds). This increment adds 37 tests: 27 adapted archive
regressions, eight new work-context checks, one documented CLI journey and one
static discovery regression, all implementation-author written/reviewed.
Compilation, 99 changed-guide local links, whitespace and limited publication
checks pass. Publication audit checks 316 text files; exact manifest verification
passes with 315 listed files. Ubuntu/Windows × Python 3.10/3.12 exact-head CI is
checked separately after publication and is not an independent code audit.

## Reviewed supplied-appraisal increment (2026-11-04)

Added a standalone appraisal intake for explicitly authored method/domain records
linked to existing normalized result IDs. Blank drafts copy only selections and
structure: even domain names and judgement choices remain unset. Each new appraisal
stays within one supplied study ID; separate rows may concern different studies.
This is identifier scoping, not verified study identity or independent evidence.
New record/domain schemas, calendar dates, unique IDs and bounded list sizes are
validated without choosing a method, validating a rubric, assigning scores or
judging scientific quality.

A separate exact-target import review permits appending the supplied records.
Every prior raw field and appraisal prefix is preserved. Contradictory positions
remain separate records, and appraisal coverage does not extend to uncited sibling
results. The detached target binds whole input, ordered records, raw/normalized
result snapshots with identity origins, record provenance, mapped report/source
catalog context and derived planning/synthesis/completion source-status changes.
Mapped catalogs are not selected or read documents; literal locators are not
resolved. Existing review hashes, ranks, completion statuses and dependency
semantics are unchanged even when their derived basis becomes stale.

The implementation-author tests cover strict input/review schemas, blank meaning
fields, exact result selection and legacy identity, study scoping, preserved
conflicts and coverage, append-only invariants, source catalogs, current/stale/
pending downstream cues, completed and unlinked work, opaque old appraisal data,
whole-original/candidate/helper changes, resealed inconsistent tampering, unsigned
consistent reauthoring, size/count bounds, UTF-8 and control quoting, mock/CSV
provenance, absent reports, no network, archive scope, exclusive outputs, duplicate
JSON and preflight refusal. The initial test expectation that consistently
reauthored unsigned reviewer text must fail was corrected: this is replay, not
identity authentication. A regression explicitly preserves that limitation.

The documented ten CLI commands also ran in a space-named directory outside the
repository. Three results remain three; supplied appraisals grow from one to three.
The old e1 appraisal and a differing e1 position both remain; e2 gains a recorded
appraisal and uncited e3 remains without one. A previously current e1 synthesis
assertion becomes STALE_SOURCE without changing its stored review or creating
support; the e2 statement stays pending. Ordinary archive creation and verification
succeed. An additional saved two-search NBIB protocol accepts one supplied appraisal
while retaining both import receipts; its three-original native archive rebuilds
and verifies. No appraisal, document or source is actually assessed in these runs.

All 47 prior replay dependency files remain byte-unchanged. Ten saved artifact
kinds still verify: work-transition, work-completion, evidence-work, source,
inventory, extraction-transition, typed native, report-transition, NBIB-batch and
ordinary research artifacts. Existing runtime changes are limited to static
read-only handoff discovery, now eighteen groups and 75 help-only entrypoints.
The focused intake/discovery suite passed 49 tests in 14.050 seconds; the combined
intake/journey/appraisal/planning/synthesis/completion/work suite passed 128 tests
in 12.287 seconds.

A separate read-only reviewer inspected the final new runtime and guide and ran
all 32 intake/journey tests successfully, finding no blocking correctness or
provenance issue. The inspected appraisal_intake.py SHA-256 is
10ddbb9b2daf465d69aa5635b9483f80e9cd9d410911823e3f090f064d08ca97;
the guide SHA-256 is
96d6d7d49e2beb4e1dbd2a569bfb0ef6bddb82fa2f39c2d1e2d506c1d94554f9.
This review did not independently author the new tests and is not a comprehensive
security audit, real-world scientific review or method validation. The earlier
search-plan assessment concerned a different proposed change, not this code.

The operation adds no live current/stale validity label to persisted appraisal
rows after later result/source changes. Import review and selected snapshots remain
detached, not a current-approval ledger. Ordinary archives retain rows, not this
application history; existing specialized transition archives do not support this
new kind. Edits/removals, consensus, method-specific checks, source authentication,
reading, clinical applicability and appraisal adequacy remain unsupported.
Unsigned assertions do not establish identities, chronology or independent review.
Limits are 100 appraisals, 100 domains per new row, 10 MB reference/candidate/review
and 50 MB protocol/application, not hard resource ceilings. Exclusive output is not
an atomic path-race or ancestor-alias defense. Synthetic data only, with unchanged
NOT_ESTABLISHED census and NOT_READY conclusion boundaries.

Final full Linux suite: 1,565 tests, 1,564 passed and one native-Windows-only test
skipped (251.687 seconds). This increment adds 33 implementation-author tests:
31 intake regressions, one documented CLI journey and one discovery regression.
Compilation, 99 changed-guide local links and whitespace checks pass. Limited
publication audit checks 322 text files; exact manifest verification passes with
321 listed files. Ubuntu/Windows × Python 3.10/3.12 exact-head CI is verified
separately after publication and is not a scientific or independent security audit.

## 2026-11-04 detached appraisal context comparison

Added read-only replay-first comparison of imported appraisal assertions and their
historical raw/normalized result, record-source and mapped report-source context.
Literal changes remain separate from appraisal validity and never renew stored
reviews, work completion or planning. Added operator discovery and a dedicated
guide; no live retrieval, model call, source reading or scientific assessment.

The full Linux regression run passed 1,587 tests with one Windows-only skip
(1,586 passed). Three additional focused regressions were then added for moved
result provenance, legacy-versus-explicit ID origin and added mapped source
catalogs; the complete new 25-test focused suite passed. Synthetic data only.
An independent read-only code reviewer found no blocking issue after running the
initial 18 tests and additional identity/reorder/oversized-input probes. This is
code-behavior review, not scientific validation or a comprehensive security audit.
Compilation, changed-guide local links, whitespace and limited publication audit
passed. Exact final-head cross-platform CI is checked separately after push.

Inputs and canonical/rendered outputs are capped at 50 MB each, not hard memory or
CPU ceilings. Only historical appraisal/result pairs are expanded; added links and
unrelated current evidence are not reviewed. Exact replay remains unsigned and
does not establish lineage, authorship, reading or appraisal applicability.

The published appraisal-comparison head was also rerun locally in full: 1,590
tests in 279.800 seconds, 1,589 passed and one native-Windows-only skip. Exact
remote-head matrix run remained queued at the next increment's local validation;
no remote success is inferred from the local result.

## 2026-11-04 portable appraisal transition segment

Added a separate deterministic appraisal-transition archive without changing
existing archive formats. Exact original/application/endpoint bytes are retained;
only explicitly ordered detached appraisal intake records are dispatched through
the existing verifier. Historical reviewer/result/source snapshots and downstream
status cues remain in their recorded step context, without renewal or scientific
validity claims. Read-only comparisons are not accepted as transition steps.

Full Linux regression run: 1,620 tests in 259.884 seconds, 1,619 passed and one
native-Windows-only skip. Three further reviewer-requested wrapper regressions
cover legacy no-report input, resealed mapped-source snapshot tampering and retained
completion assertions with changed derived bindings. All 32 final new wrapper and
CLI-journey tests passed. One operator discovery regression brings this increment
to 33 new tests and 19 static routes with 78 parser-help entrypoints.

An independent read-only reviewer found no blocking issue, ran the initial 27
wrapper tests and probed nine protocol fixtures, including source catalogs,
planning/completion, document bindings, legacy IDs and inventory reviews. Their
minor docstring correction and branch-regression suggestions were incorporated.
This is implementation testing, not scientific validation, source authentication,
reviewer independence verification or a complete security audit.

Compile, changed-guide link and whitespace checks passed; limited publication
scanner and complete-byte manifest validation are rerun before publication.
The archive caps exact bytes at 50 MB and steps at 20, rejects unknown/duplicate
members, unsafe file types, compression, altered metadata and inconsistent replay.
No extraction, locator resolution, source reading or external/model call occurs.
Unsigned assertions, partial selected history and no atomic path-race defense
remain explicit limitations. Exact-head remote CI is verified separately.

The published appraisal-archive head was rerun locally in full: 1,623 tests in
275.873 seconds, 1,622 passed and one native-Windows-only skip. Its exact-head
Ubuntu/Windows × Python 3.10/3.12 matrix subsequently passed all four jobs (run
41865544255, commit 27545526be9e6eab5c05c7d8fcbabf78954cd529). The prior
appraisal-comparison head also passed all four matrix jobs (run 41861815662,
commit 4b9bcc8bd0bf0f3c1047ccae1c2f8840a6e00dbf).

## 2026-11-04 reviewed unassigned context intake

Added standalone append-only input for supplied clinical-guideline/development
contexts, using explicit source_review or extracted_evidence scope and separate
exact-input import review. Newly imported contexts remain unassigned. Their own
pending/reviewed status and attribution are retained, never supplied by import
approval. Existing engine and archive formats are unchanged.

Full Linux suite: 1,654 tests in 331.582 seconds, 1,653 passed and one
native-Windows-only skip. Thirty-one new tests include 29 intake regressions, an
eight-command documented synthetic journey and static operator discovery. Focused
intake/journey/discovery passed 50 tests in 11.640 seconds. The catalog now has
20 routes and 82 parser-help entrypoints, without execution or scope selection.

A separate read-only reviewer exercised prepare/assemble/replay and raw-prefix
preservation across 12 valid protocol fixtures, evidence snapshot identity/index
handling, ten malformed inputs and exclusive file/symlink output behavior, finding
no correctness blocker. The reviewer-reported wording typo was corrected before
the final full test run. This was code-behavior review, not clinical or regulatory
validation, source authentication or a comprehensive security audit.

Explicit preservation checks cover original raw fields/context prefix, count
partitions, work/dependency state, all existing planning/completion bases and
synthesis assertions. New context, unassigned, pending and PRISMA source-context
ledgers may grow. Source records may be excluded/unscreened and planned searches
unexecuted without eligibility or evidence promotion. Existing-work assignment,
review renewal, context replacement and removal are intentionally unsupported.

Compilation, changed-guide links, whitespace and limited publication audit passed;
exact publication inventory is regenerated and verified before push. Bounds are
100 contexts, 10 MB candidate/reference/review JSON and 50 MB protocol/application,
not hard resource ceilings. No external/model calls, source reading, guideline
currency assessment, clinical judgement or regulatory determination is performed.
Unsigned assertions and non-atomic path-race/ancestor-alias limits remain explicit.
Final exact-head remote CI is checked separately after publication.

The exact published unassigned-context head passed all four Ubuntu/Windows ×
Python 3.10/3.12 jobs: run 41869085129, commit
6f73dae815b4b11a8fa8fb11fbd569488ab85e18.

## 2026-11-04 reviewed existing-work context assignment

Added a separate append-only context-ID assignment operation for explicitly named
existing raw work IDs. It neither imports contexts nor infers their applicability.
Before/after targets expose selected and direct-dependent source-basis changes,
while preserving old context-ID ordering, all other raw fields, supplied planning
ranks, completion states/artifacts/acceptance and original hashes. Stale completion
still satisfies the existing dependency rule; work is not reopened or reassessed.

Full Linux regression: 1,683 tests in 625.897 seconds, 1,682 passed and one
native-Windows-only skip. Twenty-nine new tests comprise 27 intake regressions,
one eight-command context-to-work continuation and one discovery test. The focused
intake/discovery run passed 48 tests in 19.120 seconds; the documented continuation
passed separately. Operator discovery now has 21 static routes and 86 parser-help
entrypoints. Existing workflow/engine and archive formats are unchanged.

Independent read-only review found no blocking defects, probing completion/source
fixtures, selected/direct-dependent basis changes, preserved ranks and COMPLETE
assertions, positional versus explicit IDs, 26 malformed/no-op inputs, exact replay,
CLI duplicate keys, no-overwrite and dangling-link refusal. Additional persistent
tests cover explicit default-looking IDs, nonrecursive change propagation and stale
completed direct dependents without reopening. This is code-behavior review, not
clinical validation, source authentication or a full security audit.

Compile, local guide links, whitespace and limited publication audit pass. The
exact inventory is regenerated and checked before publication. Bounds are 100
assignments, 100 context IDs per assignment, 10 MB candidate/reference/review and
50 MB protocol/application; these are not hard CPU/memory limits. Templates select
no contexts and expose an unfiltered catalog, not a compatibility recommendation.
Unknown/repeated/already-assigned links, no-ops and positional work-ID targets are
rejected. Context rows and own reviewer/status stay unchanged. Source/evidence
scope compatibility uses the existing engine and does not establish applicability.

Snapshots remain detached unsigned assertions. No source/artifact is opened and no
external/model call is made. Private text is not redacted; output creation does
not claim atomic path-race or ancestor-alias protection. Existing work-transition
archives do not support this new application kind. Exact-head matrix CI is checked
separately after push; local success is not a substitute for remote verification.

The exact published work-context head passed all four Ubuntu/Windows × Python
3.10/3.12 jobs: run 41872850838, commit
5c8ee356a5312d58b2830eba6cf88c45b64dcd0b.

## 2026-11-04 bounded optional PubMed identifier discovery

Added an optional, explicit ESearch client rather than another mock receipt path.
Only its preview-hash-bound fetch contacts the fixed HTTPS NCBI endpoint. Preview,
supplied-response replay, verification and conversion stay offline. It preserves
bounded raw response bytes, exact parameters, ordered PMID occurrences, failures,
query translation and count/paging diagnostics without certifying a database census.
Separate conversion requires an exact existing plan and enters ordinary unreviewed
CSV collection; it never changes a search plan, resolves identities, screens records
or extracts evidence. Zero-hit observations retain native provenance and cannot be
converted into a provenance-free header-only intake.

Full local regression passed 1,696 tests in 235.965 seconds (1,695 passed and one
native-Windows-only skip). Two additional actual-urllib/buffered-read regression
tests, added after that full run started, passed separately in 0.022 seconds. These
exercise a real synthetic 302 handler chain and a slow one-byte buffered source.
The full run includes 11 discovery tests, one six-command documented offline journey
with separate explicit fictional collection review, and one navigation regression.
Operator discovery now has 22 static routes and 91 parser-help entrypoints. No real
ESearch query, abstract/full-text retrieval, private input or model call was used.

Independent review identified and verified fixes for zero-hit provenance loss,
slow-body read aggregation, a rate-sleep deadline overshoot and impossible successful
replay durations. No remaining release blocker was found. This is implementation
review, not source authentication or a full security audit. Socket/checkpoint budgets
are best effort: DNS, TLS, response/chunk headers, an individual blocking read or OS
scheduling can still delay control. Pacing is process-local, not shared-IP enforcement.

Strict run caps are 100 requested IDs/page, 1,000 requested occurrences, 10 requests,
65,536 native bytes/attempt and 20 MB discovery JSON. Unexpected returned occurrences
remain retained even when a diagnostic stops the run; caps do not erase provenance.
TLS validation is enabled; redirects, retries, authentication, cookies, proxies and
provider fallback are not used. Error messages do not expose raw exception strings.
Unsigned replay proves consistency only, not retrieval, authentic timing or index
stability. Real queries and returned data belong outside the public repository.

Compile, seven changed-guide local links, whitespace, limited publication audit and
regenerated inventory checks pass. Official parameters and limits were checked via
public documentation; modern JSON behavior remains conservatively mocked, not live
service validated. Exact published-head Ubuntu/Windows × Python 3.10/3.12 CI is checked
separately after push, including the two added transport tests.

## 2026-11-04 selected PubMed metadata and HTTP framing hardening

Added explicit bounded EFetch MEDLINE-text acquisition for selected discovery
occurrences. This retrieves title/abstract candidate fields only. It reuses the
strict fixed-column parser, preserves raw response bytes/ordered fields/spans,
reconciles returned PMIDs by literal identifier rather than position, and keeps
repeated discovery occurrences mapped to their selected native record. Only fully
reconciled successful batches enter a separate unreviewed CSV derivative with
acquisition/discovery/native provenance. No source identity, screening, full text,
extraction, search-plan amendment or scientific conclusion is inferred.

Independent review found an HTTP framing defect shared by both clients: a duplicate
Content-Length could be collapsed to its last value and falsely mark a truncated
body complete. Both clients now preserve comma-joined bounded observations and
fail closed on repeated Content-Length, simultaneous Transfer-Encoding and length,
and repeated/unsupported transfer coding. Replay rejects contradictory complete-body
claims too. Actual synthetic HTTPResponse tests cover these cases for both clients,
while retaining real-handler redirect and slow-buffered-read regressions.

Additional review verified nonpositional/repeated occurrence mappings, BOM/CRLF and
field span hashes, missing/duplicate/unexpected PMID stops, malformed native bodies,
partial-batch retention, tamper rejection and unchanged scientific gates. A native
JSON-expansion cap preserves raw observations without candidate promotion when
control characters or repeated field structures expand excessively. Fetch snapshots
the approved discovery and selection before an injected callback can mutate them.
No remaining review blocker was found; this is not a full security or live-service
audit. All data/transports are synthetic, with no NCBI query, model, private corpus,
credential or expenditure used.

Limits: 100 selected occurrences, 20 distinct literal IDs per request, 10 requests,
262,144 raw bytes per response, 1,000 physical lines/500 fields/40 native records,
1 MB serialized parsed response and 50 MB acquisition JSON. Separate CSV intake has
its existing size bound. Repeated IDs are grouped only for transport while original
selection provenance remains explicit. Timing is best effort and pacing process-local;
DNS/TLS/headers/reads/scheduling can exceed wall-clock expectations. Unsigned replay
cannot prove retrieval, freshness, authentic timing or source identity. Current
implementation bytes are required for replay; use the recorded version for earlier
artifacts after the shared transport change.

Final frozen-byte Linux regression: 1,721 tests in 287.177 seconds, with 1,720
passed and one native-Windows-only skip. All Python source/test hashes were unchanged
across the run. Eighteen metadata tests, one six-command offline journey, one new
operator route and three added HTTP framing tests are included. The catalog has
23 static routes and 96 parser-help entrypoints. Eight changed-guide local link
checks, compilation, whitespace, limited publication audit and regenerated inventory
checks pass.

The prior d211f8aca1e912ea15139b76f847427905066b3d workflow run 41877285628 was
reported completed/success at 17:48 UTC on 2026-11-04. All matrix step results were
successful; two per-job summary states still lagged at in_progress at that read.
New exact-head CI is checked separately after publication.

The exact published metadata head baef66823ac1d924d7af073f88276541e01fa5a8
passed all four Ubuntu/Windows × Python 3.10/3.12 jobs in run 41881573568.

## 2026-11-04 local source passages beside manual extraction fields

Added a read-only local reading-to-extraction bridge, not an approval wrapper.
A source catalog exposes explicitly mapped, byte-matched UTF-8 physical lines and
positions. A separate check compares selected verbatim quotes and byte ranges
beside unchanged completed candidate fields. Manifest protocol/candidate/descriptor
hashes, source-reference/report membership, nonnull declared document hashes and
all later selections are validated before opening any source directory. Source
locators remain inert. No source selection, scientific field, mechanism label,
reviewer or intake decision is inferred.

One descriptor-relative, no-follow, nonblocking regular-file read both collects
and hashes each bounded source. Hard-linked/nonregular/unsafe paths, changed reads,
size/hash mismatches and unsupported text prevent quote exposure for that source.
Native Windows local source checks fail closed; template and metadata validation
remain available. Rerun with original files and the recorded implementation for
reproducibility. The detached observation is unsigned, not a persistent ledger or
proof of execution, source authenticity, semantic support or complete reading.

Independent review exercised metadata-before-read, bindings, symlink/hardlink/FIFO
and directory refusals, changed-read observations, mismatch non-disclosure, UTF-8
boundaries/BOM/CRLF/CR and Unicode line separators, output preflight and safe error
rendering. It identified excessive span/catalog/repeated-field expansion, raw-root
normalization and cyclic Python-input issues; all were fixed and independently
rechecked. Forty-two focused/journey tests passed, as did 105 related source/intake
regressions. No remaining review blocker was found. This is not a full security
audit; a privileged concurrent filesystem attacker is outside the stated boundary.

Limits: 20 sources, 1 MB/source, 5 MB total, 200 passages, 32,768 bytes for both quote
and selected span, 10 MB manifest, 50 MB output, 5,000 catalog lines/source and
20,000 total. Metadata/output expansion is streamed and preflighted before source
reads; catalog lines are counted before object construction. Human text rendering
uses incremental budgets and control-safe quoting. These bounds are not hard CPU
or memory isolation. Root spellings are retained by the CLI for validation; an API
Path object may already have normalized its spelling before entry.

The six-command fictional journey runs template, catalog, check, separate result
review target, explicitly supplied import review and application verification. It
checks unchanged identification/screening PRISMA counts, unchanged supplied fields,
separate source-check scope in the intake receipt, and NOT_READY conclusions.
No real source, network/API/model call, credential, private corpus or expenditure
was used. The checked-in source is LF UTF-8 and contains no experimental procedure.

Final frozen-byte Linux regression: 1,764 tests in 320.029 seconds, with 1,763
passed and one native-Windows-only skip. All Python source/test hashes remained
unchanged across the run. Forty-one checker tests, one six-command source-to-intake
journey and one navigation regression are new. The catalog now has 24 static routes
and 99 parser-help entrypoints. Nine changed-guide local link checks, compilation,
whitespace, limited publication audit and regenerated inventory checks pass.
Exact published-head Ubuntu/Windows × Python 3.10/3.12 CI is checked after push;
local POSIX results do not substitute for the native-Windows fail-closed checks.

## 2026-11-06 PubMed validation without Windows symlink privileges

The discovery and metadata output-preflight tests now separate existing-file
protection from dangling-link protection. Ordinary output and no-network checks
always run. Only the link case is skipped when symlink creation is explicitly
unsupported or Windows requires an unavailable privilege; unrelated filesystem
errors still fail. Supported platforms still check that the link is retained and
its absent target is not created. Runtime acquisition behavior is unchanged.

On Windows with Python 3.12.10, the focused command
`python -m unittest test_pubmed_discovery test_pubmed_metadata test_pubmed_transport_regressions -v`
ran 36 tests: 34 passed and two link cases skipped for missing Windows privileges.
An independent rerun returned the same result. Temporary files were kept in a
dedicated workspace directory. These were synthetic/offline checks; no live
PubMed search or retrieval was performed. Full cross-platform CI is recorded
separately after publication and is not implied by this focused result.

The first cross-platform run for `69843997` exposed an existing passage-check
test mismatch on Windows: its native temporary-directory spelling was rejected
for backslashes before the mocked unsupported-platform check. The test now uses
a portable inert root spelling for that gate and separately checks rejection of
Windows backslashes, with source opening forbidden in both cases. The original
failure was reproduced locally before editing. The passage checker and journey
modules then ran 42 tests: 19 passed and 23 skipped for unsupported POSIX source
access on native Windows. This changes test setup, not source-access behavior.

## 2026-11-08 Public boundary cleanup (0.84.1-public-boundary-cleanup)

Removed an internal host name and references to a private development log from
this record; remote CI results are the public GitHub Actions history. Reworded the
shared boundary boilerplate to this project's scope and aligned `docs/USAGE.md`
with the opt-in PubMed wording of the README. The owner approved the separately
invoked PubMed ESearch/EFetch clients as part of the public release boundary; this
decision is recorded in PUBLICATION.md. The test workflow now also runs on `main`,
and this cleanup precedes merging the workflow branch into `main`. No code path,
test or fixture changed; the manifest was regenerated for the edited text files.
## 2026-11-08 Independent challenge records (0.85.0-independent-challenge)

`challenge_intake.py` and the engine module `challenge_links.py` implement the
workflow's step 8 as supplied records. A challenge names existing synthesis
statements, a challenger label, the strongest alternative explanation, missing
discriminating evidence, citation-integrity findings on cited results, a
conclusion-width label and one of three outcomes. The engine rejects a challenger
label that matches a recorded reviewer, position-recorder or appraiser label on the
challenged statements, binds each challenge to the challenged statements' current
review bases, requires a MATERIAL_GAP outcome to name existing reopening work or an
amendment note, and derives statements without a recorded challenge, open material
gaps, unresolved challenges and stale bindings. Status, handoff, synthesis snapshot,
bundle summary and version comparison expose the new section; the operator catalog
gained one route with four parser-help entry points (103 in total). The mock
adapter context allows the new section as an enrichment that does not change what
was searched, screened or extracted. Nothing adjudicates, generates or verifies a
challenge; a distinct label is labeled LABEL_DISTINCT_ONLY, not independence.

Two new test modules cover engine validation, binding staleness, reopening rules,
label collisions, intake replay/tampering, CLI exclusive outputs, adapter
preservation and the documented ten-command rehearsal in `docs/INDEPENDENT_CHALLENGE.md`.
The full suite passed on Ubuntu with Python 3.12: 1795 tests in 167.973s.
A native Windows run with Python 3.15 before the fixture refresh ran 1778 tests: the
batch walkthrough class failed in setUpClass on the fixture hash mismatch that this
change resolves, and the pre-existing Python 3.15 junction-test error remained. The
published head is checked on the Ubuntu/Windows × Python 3.10/3.12 matrix after push.
Publication audit and the regenerated manifest pass. All fixtures are fictional;
no real statement, source, model call or network request was involved.

## 2026-11-08 Conclusion readiness gates (0.86.0-conclusion-readiness)

`readiness_links.py` (added to the bundle engine files), `readiness_review.py` and
`readiness_intake.py` implement the workflow's step 9 as mechanical bookkeeping plus
supplied records. The engine derives twelve gates from the existing ledgers (declared
plan, supplied searches, screening, reports, record-level extraction, appraisal of
cited results, statement reviews, result citations, challenges recorded, challenges
resolved, contexts, work), each CLOSED, OPEN or NOT_APPLICABLE with exact open items
and one basis sentence, and hashes the canonical gate ledger. Only three cases are
NOT_APPLICABLE (no declared plan, no report ledger, record-level extraction when a
report ledger exists); gates whose stage is not supplied stay OPEN with empty items.
`reports_resolved` also lists included records that map to no report, and legacy
scalar report rows are read as supplied, so what `run` accepts is unchanged.
A supplied `readiness_assertions` row names an assessor, date, scope statement,
rationale, limitations, separate evidence_sufficiency and conclusion_readiness labels
and the examined `gates_sha256`; reopening work or an amendment note is required for a
NOT_READY/INSUFFICIENT pair. A READY assertion is permitted while gates are open and
is recorded with the open gates at the asserted snapshot. Assertions are labeled
CURRENT_GATES or STALE_GATES against the current hash. The intake mirrors the
challenge intake: template bound to the current hash, target rejecting a stale hash,
separate `import_readiness_assertions` review, exact replay, and preservation checks
that include record flow, report counts, synthesis, challenge and the gate ledger.
Status adds a `readiness` summary and two text lines without new queues; the handoff
gains a detailed view and one catalog route with four parser-help entry points (26
routes, 107 entry points); the synthesis snapshot, bundle summary, version comparison
and amendment transitions expose the section; the mock adapter context allows it as
an enrichment. Every hard-coded `conclusion_readiness: NOT_READY` and `census_claim`
is unchanged, and the engine adds `mechanical_conclusion_readiness: NOT_READY`.

Two new test modules cover gate derivation on `examples/synthesis-review.json` with
and without challenges, the fixture hash equality, staleness after statement,
appraisal and screening changes, missing-stage rules, index pointers for searches,
READY-with-open-gates recording, reopening rules, enum/date/field strictness, status/
handoff/snapshot/bundle/comparison surfaces, text-control quoting, the adapter
context, intake replay and tampering, exclusive CLI outputs and the documented
eight-command rehearsal in `docs/CONCLUSION_READINESS.md`. Because the engine file
set changed, the walkthrough fixture refresh rewrote ten `target_sha256` values
(nine under `examples/batch-to-evidence/` and `examples/second-search/review.json`).
The full suite ran on native Windows with Python 3.15 in a dedicated temporary
directory: Ran 1826 tests in 410.592s; FAILED (errors=1, skipped=45). The one error
is the pre-existing `test_verify_manifest...test_native_windows_junction_rejected`
TypeError under Python 3.15, unrelated to this change and left as is.
The two new modules also pass under the locally installed Python 3.13, and every
changed module parses with Python 3.10 syntax rules. Compilation, the CRLF scan, the
limited publication audit and the regenerated manifest pass. Exact published-head
Ubuntu/Windows × Python 3.10/3.12 CI is checked after push.

Not claimed: a closed gate is not evidence sufficiency, census or conclusion
readiness; a READY assertion is a supplied human label bound to a gate snapshot, not
a mechanical conclusion, and no assertion is assessed, adjudicated or promoted. The
gate hash binds the gate snapshot only, not every protocol byte. All fixtures are
fictional; no real statement, source, model call or network request was involved.

## 2026-11-08 Documentation restructure (0.86.1-documentation-restructure)

The README was reduced from 38 KB to 12.9 KB: title, the Korean and English taglines, a
link to the new Korean guide, a purpose/scope table, grouped "What is implemented" bullets
that keep every capability named, "Start here" links, the unchanged Quick start command
block with the synthetic demo bounds, a twelve-row "Commands at a glance" table, a
documentation index with one line for every file under `docs/`, the design/boundary links
and the rights paragraph. The 47-row command table and the per-feature narratives moved out of
the README: `docs/COMMANDS.md` lists every command-line script and subcommand with the
usage line its parser prints for `--help`, a one-line purpose and its guide, plus the 23
engine modules without an entry point; `docs/WORKFLOWS.md` keeps the moved narratives
verbatim, grouped by workflow stage, together with the full capability list and the
boundary paragraphs that were only in the README; `docs/README.ko.md` is a Korean guide
(purpose, public scope, installation and quick start, main commands, boundaries,
documentation index). This validation record became a short current snapshot, and every
earlier dated entry moved verbatim, in order, to `docs/VALIDATION_HISTORY.md`. SKILL.md
now points at the command reference and the workflow document instead of the removed
README section. No existing file under `docs/` was renamed or moved, no fenced command
block of any guide changed, and no Python module, test or fixture changed, so the
walkthrough fixtures were not refreshed.

Verification on native Windows with Python 3.15 in a dedicated temporary directory:
`python -m unittest discover -q` ran 1826 tests in 463.922s; FAILED (errors=1, skipped=45).
The one error is the pre-existing `test_verify_manifest...test_native_windows_junction_rejected`
TypeError under Python 3.15, unrelated to this change and left as is; the two tests that
read the README were rerun after its final edit. A local link checker resolved every
relative link target in the 79 Markdown files of the root, `docs/` and `examples/`
(642 local links, none broken, every heading anchor present), confirmed that all 48
guide paths of the `review_handoff.py` catalog and every guide named in SKILL.md exist
at their paths, and that the README links every `docs/*.md`. The README Quick start
block is byte-identical to the previous release and still names `ris_intake.py`.
Compilation, the CRLF scan, the limited publication audit and the regenerated manifest
(380 files) pass; the Quick start commands were run by hand once and the generated bundle
removed. Exact published-head Ubuntu/Windows x Python 3.10/3.12 CI is checked after push.

Not claimed: no behavior, boundary text or test changed; the restructure only moves and
condenses documentation. The command reference records parser usage lines, not validated
workflows, and the Korean guide translates the documented scope without adding a
capability. Documentation size and link resolution say nothing about scientific adequacy;
census remains `NOT_ESTABLISHED` and the mechanical conclusion readiness `NOT_READY`.

## 2026-11-08 Test package and dispatcher (0.87.0-test-package-and-dispatcher)

The 106 `test_*.py` modules moved from the repository root into the new `tests/` package
(`tests/__init__.py` is one docstring line), so the root now shows the command-line scripts
and the engine modules only. `python -m unittest discover -v` from the repository root
recurses into the package and loads the modules as `tests.test_<name>`; the CI command in
`.github/workflows/tests.yml` is unchanged. Inside the moved modules the 79 repository-root
definitions `ROOT = Path(__file__).resolve().parent` became `Path(__file__).resolve().parents[1]`,
each use checked individually: every use of `ROOT` is a repository-root use (fixtures under
`examples/`, guides under `docs/`, script paths and `cwd` for subprocesses, the README read by
the RIS intake test, and the implementation-byte reads that the extraction worksheet test
guards); none used the directory as a scratch base. The 28 cross-test imports in 16 modules
became `from tests.test_<name> import ...`. The 27 modules that locate `examples/` and scripts
relative to the current directory are unchanged, because discovery neither changes the
working directory nor removes the start directory from `sys.path`. The walkthrough tests still
build command paths from `ROOT` and read the guides under `docs/`; the catalog navigation and
operator journey tests still run the parser-help entry points with a temporary current
directory. No fenced command block of any guide changed, and no implementation module changed.

The new `sensei.py` is a standard-library dispatcher that makes the root scripts discoverable
without changing them. `python sensei.py list` prints every root script that has a top-level
`main()` or `__main__` block (58 scripts, found by parsing the files rather than importing
them) with the first sentence of its docstring, then the 26 supplied-input routes of
`review_handoff.SUPPLIED_INPUT_WORKFLOWS` with their scripts and their 52 guide paths;
`review_handoff` is imported only inside `list`, and the dispatcher imports no repository module
at startup. `python sensei.py run <script> [arguments...]` accepts exactly the listed file names
(anything else, including engine modules, paths, the dispatcher itself and case variants, exits 2
with a one-line message before anything runs) and executes the script with
`runpy.run_path(..., run_name='__main__')` after setting `sys.argv`, so output, parser name, exit
status and boundary text are those of the script; no shell is involved, and the dispatcher works
from any current directory because it resolves scripts next to its own file. The twelve tests in
`tests/test_dispatcher.py` check the listing against an independent scan of the root, the
first-sentence rendering, every catalog route with its scripts and guides, control-character
escaping, byte-identical output versus direct invocation from a temporary directory, `--help` and
exit-status pass-through, the rejection list, that nothing is created in the current directory,
and that neither importing the dispatcher nor `run` loads the catalog modules. README "Commands at
a glance", `docs/COMMANDS.md`, `docs/USAGE.md`, `SKILL.md` and the Korean guide describe the
layout and the dispatcher; the documented `python <script>` commands remain the primary form.

Deliberately not moved: the implementation modules stay flat at the root. Fixtures bind
`offline_adapter.py` bytes and review targets bind engine bytes through `ENGINE_FILES` and the
`implementation_hashes` tuples, so packaging them would change those bytes and bindings.
`offline_adapter.py`, every `ENGINE_FILES` module and the walkthrough fixture `target_sha256`
values are byte-identical to the previous release, and the fixture refresh script was therefore
not run. The 2026-11-06 entry above quotes the focused command
`python -m unittest test_pubmed_discovery ...` as it was run that day; it is kept verbatim as a
record and is not a current instruction (the modules are now `tests.test_pubmed_discovery` and
so on).

Verification on native Windows with Python 3.15 in a dedicated temporary directory: before the
move, `python -m unittest discover -q` on a byte-identical copy of the tree ran
`Ran 1826 tests in 402.834s`; `FAILED (errors=1, skipped=45)`. After the move and the new module:
`Ran 1838 tests in 450.444s`; `FAILED (errors=1, skipped=45)`, exactly 1826 + 12 dispatcher tests. The one error
is the pre-existing `tests.test_verify_manifest...test_native_windows_junction_rejected`
TypeError under Python 3.15, unrelated to this change and left as is. The dispatcher module
also passes under the locally installed Python 3.13. Compilation, the CRLF scan, a local link
checker (every relative link target and heading anchor in the Markdown files of the root,
`docs/` and `examples/`, all catalog guide paths and every file named in SKILL.md), the limited
publication audit and the regenerated manifest (383 files) pass. `python sensei.py list` and
`python sensei.py run` were executed by hand from the repository root and from a temporary
directory. Exact published-head Ubuntu/Windows x Python 3.10/3.12 CI is checked after push.

Not claimed: no behavior, boundary text, fixture or documented command changed; the dispatcher
adds no capability beyond discovery and pass-through, and its listing is neither a recommended
execution order nor a workflow validation nor evidence that any step was done. Matching test
counts show that the same tests were collected, not scientific adequacy; census remains
`NOT_ESTABLISHED` and the mechanical conclusion readiness `NOT_READY`.

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

## 2026-11-10 Corrupt ZIP manifest diagnostics (0.88.1-implementation-zip-errors)

The detached implementation inspector now normalizes DEFLATE and LZMA decoder
failures at the ZIP-manifest read boundary. Corrupt manifests produce the existing
complete INVALID report and exit 1 without a traceback in JSON and quoted text.
BZIP2 rejection remains covered by the existing OSError handling. No engine,
adapter, bound walkthrough fixture or existing guide command block changed.

Four new synthetic tests generate actual ZIP files, corrupt compressed manifest
data while retaining readable central directories, confirm the native decoder
failures, and check sanitized reports and unchanged input bytes. Valid stored,
DEFLATE, BZIP2 and LZMA archives still match. The pre-fix DEFLATE and LZMA cases
both reproduced uncaught decoder errors.

Local Python 3.12.14 validation: `python -m unittest discover -q` reported
`Ran 1858 tests in 140.230s`, `OK (skipped=1)`, with no failures or errors.
Focused inspector and dispatcher validation ran 32 tests, OK. The documented guide
was replayed separately: all 28 engine files and the supplied publication manifest
matched. `compileall`, manifest verification and the limited publication audit
passed; changed files are UTF-8 without BOM and LF. This is malformed-input
handling, not artifact verification, source authentication, scientific adequacy or
release provenance. Census stays NOT_ESTABLISHED and readiness stays NOT_READY.

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

## 2026-11-10 Crosswalk ZIP-error integration (0.89.1-crosswalk-zip-errors)

Integrated the upstream detached implementation-inspector correction into the native
count-crosswalk release. DEFLATE and LZMA failures while reading a ZIP manifest now
produce the existing sanitized INVALID report with exit 1, in JSON and quoted text,
without a traceback. BZIP2 errors retain the existing OSError handling. Four added
synthetic tests exercise actual corrupted compressed bytes with readable ZIP central
directories and valid stored/DEFLATE/BZIP2/LZMA archives. Input bytes stay unchanged.
The count-crosswalk implementation, engine, adapter and bound fixtures are unchanged.

Local Python 3.12.14 integration validation: `python -m unittest discover -q`
reported `Ran 1881 tests in 155.429s`, `OK (skipped=1)`, with no failures/errors.
The only skip is the existing native-Windows junction test. Focused inspector,
dispatcher and crosswalk validation ran 55 tests in 8.657s, OK without skips.
Compileall, regenerated manifest and publication audit passed. Integrated inspector
code/tests exactly match the upstream correction; no other existing Python, engine,
adapter, fixture or guide command bytes changed.
This is malformed-input handling, not artifact verification, scientific adequacy or
source authentication. Census stays NOT_ESTABLISHED; readiness stays NOT_READY.

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

## 2026-11-14 Explicit keyed CSV journey (0.94.0-keyed-csv-journey)

Documented roadmap #34(a): the existing importer can use one explicitly selected,
nonblank key column for both record ID and inert locator. A three-command guide
previews, verifies and creates an unfilled review template without rewriting the
native CSV or changing protocol state. A fictional fixture retains empty URL/DOI
cells, multiline text, repeated keys and different literal URL values under one
key. No locator fallback, dialect guessing, publication matching or review approval
is introduced. Runtime modules, ENGINE_FILES, strict RIS parsers/wrappers, adapter,
existing fixtures and existing executable guide blocks remain byte-identical.

Seven new tests cover exact same-column mapping, separate occurrences, original
blank/nonblank values, no invented locator conflicts, BOM/CRLF physical spans,
missing/blank keys, wrong mappings, malformed input, tamper rejection even after
resealing, unfilled review state, protocol nonmutation and exact guide replay with
exclusive-output retries. Independent review found no blockers; its suggested
same-key/different-URL case was added and independently rerun (7/7 passed).

Local Python 3.12.14 full suite: `Ran 1950 tests in 137.708s`,
`OK (skipped=1)`, no failures/errors. The skip is the existing native-Windows
junction test on Linux. Existing parser/intake/review regression: 52 tests in
2.043s, OK. New focused suite: 7 tests in 0.254s, OK. Publication audit, manifest,
compileall, Python 3.10 grammar and UTF-8/LF checks passed.

An initial focused assertion expected the template renderer to print NOT_READY;
the existing renderer instead prints an explicit unfilled-review boundary. The
test was corrected to assert that unchanged boundary and null draft values.
The first full run preceded manifest regeneration and failed ten checkout-smoke
assertions on expected inventory drift. After regenerating the manifest, the full
suite passed without relaxing the verifier or changing production code.
These are synthetic/local results, not provider compatibility, source authenticity,
complete search, scientific validity or remote Windows CI results. RIS continuation
wrappers and native archive expansion remain separate future increments.

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

Post-publication CI correction: Ubuntu matrix jobs passed, while both Windows
jobs exposed a test-harness path-tokenization error in the new guide replay.
The test had inserted a host-native path before POSIX shell tokenization, stripping
Windows backslashes. It now tokenizes the documented command first and substitutes
the path in individual arguments. A Windows-backslash/space-path regression was
added; no parser, wrapper or published guide command was changed. The corrected
head requires a new full local run and all four CI jobs before merge.

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

## 2026-11-14 Reviewed screening-sheet positions intake (0.97.0-screening-sheet-intake)

Second bounded #33 increment: a separate wrapper appends human-supplied CSV
positions after exact-target import review. Export-time protocol/source hashes
and every read-only cell are checked against the existing export. Blank human
rows are explicitly skipped; partial rows, formula/escape ambiguity, duplicate
review IDs and record/reviewer pairs fail closed. Original CSV bytes, spans,
review cues and implementation hashes remain in a detached replayable application.
Canonical screening and old positions are never overwritten or renewed.

Local Python 3.12 full suite: `Ran 1981 tests in 140.201s`, `OK (skipped=1)`.
Focused intake/export/navigation: 44 tests pass, including 10 new intake tests.
The synthetic guide commands execute verbatim with tokenization before host-path
substitution. Publication audit: 417 files, pass; manifest, compileall, Python 3.10
grammar and unchanged ENGINE_FILES/offline_adapter checks pass. Existing executable
sh blocks remain byte-identical. Catalog: 26 routes, 113 help entrypoints.

Independent review identified a multi-output preflight gap: an already-existing
report path could be discovered after a candidate was written. Both destinations,
parent directories, alias equality and serialized sizes are now checked before
writing; regression tests cover existing destinations, identical paths and absent
parents with no candidate creation. Exclusive creation remains the final guard.
I/O failures and races are not atomic transactions and may leave partial output;
the guide states that boundary. No local test failures occurred. These are synthetic
offline checks, not source reading, reviewer identity or eligibility validation.


## 2026-11-14 Blank human-decision sheets (0.98.0-blank-decision-sheet)

A small export-only #33 increment reuses the existing source-sheet and screening
review views. At most 100 explicitly ordered or all enumerated records are shown;
all seven human decision fields remain empty. Exact prior canonical rows and
supplied review ledgers/cues are read-only JSON with export-time protocol, source
and review-context hashes. No vote, recommended choice, sequential decision target,
receipt, canonical mutation or batch edited-sheet intake is introduced. The guide
keeps the positions/decisions distinction and pending batch application explicit.

Local Python 3.12 full suite: `Ran 1993 tests in 140.367s`, `OK (skipped=1)`.
Focused decision/source-sheet/intake/navigation: 56 tests pass (12 new decision
sheet tests). Independent review ran 58 decision/source/review tests successfully,
compared ENGINE_FILES against the prior release and found no blockers. Publication
audit: 420 files, pass; manifest, compileall, Python 3.10 grammar, ENGINE_FILES and
offline_adapter byte preservation pass. Existing executable sh blocks are unchanged;
the new guide runs verbatim with tokenization before Windows path substitution.
Catalog: 26 routes, 114 help entrypoints. No test failures occurred.

Cases cover conflict/stale context without a winner, all human fields blank,
literal/escaped ID collisions, ordered selection and unknown/duplicate rejection,
100-record bound, whole-protocol validation, drift hashes, incompatible positions
intake headers, empty catalog, byte bounds, exclusive output and synthetic CLI
walkthrough. These are offline bookkeeping checks, not source reading, identity,
scientific assessment or real spreadsheet interoperability certification.


## 2026-11-14 Read-only decision-batch target preview (0.99.0-decision-batch-preview)

A separate #33 target-only increment parses exact edited decision-sheet bytes,
rejects changed read-only/export context and simulates completed supplied rows in
sheet order using the existing full single-record prepare/assemble guards. It
outputs hypothetical steps and a blank import review, not a candidate protocol,
applied receipt, approval or application. Batch assemble/verify remains absent.
Canonical screening, existing positions and stored history are untouched. The
100-row cap, lifetime receipt cap and cumulative/final target byte budgets bound
this convenience without claiming high-volume performance or scientific validity.

Final local Python 3.12 suite on fixed inputs: `Ran 2004 tests in 151.029s`,
`OK (skipped=1)`. Focused preview/export/intake/navigation: 57 tests pass; new preview
module: 11 tests pass after final byte-budget hardening. Independent review ran
60 preview/export/single-decision tests, reran two later-step guard/CLI regressions
and reviewed the final cumulative-byte guard; no remaining blockers. Actual 100
completed decisions were simulated successfully (local standalone 8.208s).

Audit: 424 files, pass. Manifest, compileall, Python 3.10 grammar, unchanged engine/
adapter bytes and preserved existing executable sh blocks pass. Catalog: 26 routes,
115 help entrypoints. The new synthetic guide executes verbatim. Tests cover exact
chain/order reproducibility, original/context drift, partial/blank/duplicate rows,
formula ambiguity, source spans, limits and second-step workflow failures that
preserve original input and produce no CLI output.

Validation correction: an interim final rerun had 10 checkout smoke failures
because the guide was edited while that run was active, leaving its manifest
outdated. No source-function failure occurred. The guide was frozen, the manifest
regenerated and the full 2004-test suite rerun successfully as recorded above.
This bookkeeping error occurred before publication; no failing revision was pushed.
All fixtures remain synthetic. Hashes and previews do not establish reviewer
identity, source reading, adjudication, chronological authenticity or readiness.


## 2026-11-14 Reviewed decision-batch application and replay (0.100.0-reviewed-decision-batch)

The #33 batch path now has a separate exact-human-review assemble/verify tool.
Preview and application share one internal simulation, preserving full existing
single-record operational guards and ordinary receipt schemas. The preview remains
read-only. A completed separate import review binds original protocol, raw sheet,
target and implementation before assembly creates a detached candidate. Full replay
must match the entire application before any new protocol export. No original file,
existing position or unrelated assertion is modified. Application code bytes are
part of the target, so older previews require fresh review rather than rebasing.

Local Python 3.12 full suite: `Ran 2013 tests in 153.165s`, `OK (skipped=1)`.
Focused application/preview/export/navigation: 56 pass. Independent review ran new
application9 + existing preview/single-decision48 tests (57 total), found no blockers
and confirmed unchanged ENGINE_FILES. Audit: 428 files, pass; manifest, compileall,
Python 3.10 grammar, adapter/engine bytes and existing executable sh blocks pass.
Catalog: 26 routes, 117 help entrypoints. No test failures occurred in this increment.

The application CLI has at most one new destination per command. Complete flushed
same-directory temporary files are published by exclusive hard links, never by
replacement. Tests cover write/link failures with no final output and cleanup,
existing/symlink destinations, unsupported hard links, absent parents, full replay
tampering, stale implementation/review/context, duplicate/partial rows, shared
limits/budgets, second-step guard failure, old history prefixes and the verbatim
synthetic guide. Post-publication cleanup/stdout failures can leave complete output;
that uncertainty and the absence of ancestor-race guarantees are documented.

All examples are synthetic. Import review authorizes recording supplied choices,
not adjudication correctness, reviewer identity, reading, chronology or scientific
validity. The detached application must be retained for batch provenance.


## 2026-11-14 Append-only full-text reviewer-position intake (0.101.0-report-review-intake)

The #33 report_reviews follow-up closes the documented manual protocol-copy gap.
Existing report_review templates remain the first stage; a separate JSON intake
provides exact target, human import-review assembly and full replay. New positions
require a retrieved report, supplied source descriptors and the current source basis.
Null document digests remain explicitly unbound and non-null digests unverified.
Existing stale positions, report/source/canonical fields, memberships and old review
prefixes stay unchanged. Duplicate IDs/pairs are rejected without supersession.
CSV intake and report-study/inventory position ledgers are separate future work.

Local Python 3.12 full suite: `Ran 2026 tests in 151.610s`, `OK (skipped=1)`.
Initial focused intake/report-review/navigation suite: 79 pass. Final new intake
module: 13 pass, including a subsequently added absent/empty-ledger first-append
regression. Independent review ran 64 intake/report-review/shared-writer tests and
also independently exercised first-ledger append/replay; no remaining blockers.
Audit: 433 files, pass; manifest, compileall, Python 3.10 grammar, unchanged engine/
adapter bytes and existing executable sh blocks pass. Catalog: 26 routes, 121 help
entrypoints. No failures occurred in this increment.

Synthetic cases cover exact append/replay and unchanged record/report counts,
missing/pending/unavailable source contexts, explicitly unbound document digests,
source drift, preserved stale positions, no supersession, schema/partial/date/choice
validation, 100-row and byte budgets, unrelated-input/implementation review drift,
full-validator failure, replay tampering, exclusive single-output CLI and the
verbatim guide. Complete-file exclusive publication reuses the reviewed batch
writer without changing it. Selected source copies are budgeted before retention.

These checks do not establish actual full-text reading, reviewer identity, source
authenticity, comparable coverage, adjudication, scientific validity or readiness.
The detached application carries import-review provenance and must be retained.


## 2026-11-14 Exact report-study reviewer-position intake (0.102.0-report-study-review-intake)

The #33 pair-position follow-up closes another documented manual-copy gap using
existing blank templates plus reviewed append/replay. New assertions require an
exact currently declared membership on a retrieved/source-declared report, current
pair basis and explicitly supplied same-report source IDs. No subset is selected
for a human. Old orphan/stale assertions, canonical reports, memberships, results,
counts and every prior position remain unchanged. Exclude positions only expose
existing cues; no canonical study selection or result deletion is introduced.

A small reviewed_intake_safety helper now shares only import-review validation
and complete application replay with report-review intake. Domain source/member
rules remain specific and engine schemas unchanged. Both targets bind helper bytes;
the prior report-intake fixture was regenerated and its regression suite rerun.
Whole report source snapshots are retained once per selected report and byte-budgeted.

Local Python 3.12 full suite: `Ran 2038 tests in 154.400s`, `OK (skipped=1)`.
Focused new/old intake, pair review and navigation: 90 pass. Independent review ran
66 new/old intake and pair-validator tests, confirmed unchanged ENGINE_FILES and
found no blockers. A nonblocking CLI error-prefix naming suggestion was corrected
before the final full run. Audit: 439 files, pass; manifest, compileall, Python 3.10
grammar, engine/adapter preservation and old executable sh blocks pass. New route
catalog: 27 groups, 125 help entrypoints. No test failures occurred.

Synthetic tests cover explicit source subsets/order, wrong-report/unknown/empty
source rejection, current/orphan pairs, null unbound digests, whole-catalog drift,
no supersession, 100-row/byte limits, first absent/empty ledger, exact import review,
whole replay tampering, candidate-validator failure without input changes, single
exclusive outputs and the verbatim guide. Shared complete-file writer unchanged.
No identity, independence, equivalent reading coverage, source authenticity,
adjudication, chronology or scientific readiness is established.


## 2026-11-14 Described candidate-position intake (0.103.0-inventory-review-intake)

The #33 follow-up closes the candidate-position manual-copy gap. A bounded wrapper
reuses existing separate import-review, exact replay and complete exclusive writer
helpers. New positions require a currently described exact pair, retrieved report,
source descriptors and current candidate-review basis, plus explicit same-pair
inventory and same-report source ID subsets. Neither subset is inferred. Current
review of stale descriptions does not renew them. Existing orphan/stale positions,
canonical reports, included memberships, inventory descriptions and evidence remain.

Tests cover full same-pair description binding, distinct membership/inventory hash
domains, pending/excluded eligibility, unavailable retrieval, explicit subsets/order,
unknown/other-pair IDs, no supersession, 100 rows and byte budgets, absent/empty first
ledger, exact whole replay, input immutability and exclusive outputs. The verbatim
synthetic guide uses separate fictional position and import-review fixtures.
No ENGINE_FILES, canonical schema or shared safety implementation changes. The
existing descriptive_inventory route now exposes these separate positions without
adding another route group: 27 groups, 129 help entrypoints.

Local Python 3.12 full suite: 2053 tests pass (one platform skip). Focused new/old
intake and navigation: 63 pass, plus the added hash-domain regression passes with
all 15 new tests. Independent review: 56 tests pass; no blocking findings. A cosmetic
CLI/docstring domain label was clarified after the first full run (153.759 seconds),
then the synthetic import-review fixture regenerated and the full suite rerun.
Audit: 444 files; manifest, compileall, Python 3.10 grammar, protected engine/adapter
and shared helper bytes, and old executable sh blocks pass. No test failures in the
completed implementation. Synthetic software checks are not scientific correctness,
authenticated review or source-reading validation.

## 2026-11-14 Test-only CLI help harness (0.104.0-test-cli-harness)

One 129-entry help-catalog loop now uses a serial trusted-test runpy harness. All
production Python/ENGINE_FILES remain unchanged. All existing actual-process CLI,
JSON rejection, environment, dispatcher, guide and journey checks remain intact.
The harness restores argv/path/streams/cwd/environment; it does not simulate process
isolation, module cache isolation, startup, signals or timeouts. New contract tests
compare bytes/exit behavior against subprocess and verify exceptional restoration.

Opt-in full-catalog benchmark: all 129 entries match returncode/stdout/stderr across
three alternating-order runs. Subprocess 5.945/5.183/5.167 seconds, in-process
0.465/0.444/0.426 seconds on local Python 3.12.14/Linux. No timing assertions or
claims of proportional full-suite/Windows improvement. [Runtime guide](docs/TEST_RUNTIME.md)
records the reproducible command and retained coverage. Prior PR21 Windows3.10 job
452 seconds/test385; Windows3.12 job368/test354. Inspect slow tests when Windows
jobs exceed six minutes; class-fixture costs are absent from unittest durations.
CI adds --durations25 only on Python3.12; ten-minute timeout stays unchanged.

Full local Python3.12 suite: 2060 tests in 149.919 seconds, OK (one platform skip).
Prior local full run: 2053 tests in 155.178 seconds; new contract coverage adds seven
tests. These sequential observations are not a controlled whole-suite speed claim.
Focused and independent harness/navigation: 31 pass. Independent complete-catalog
benchmark also matched bytes/exit for all129 entries (5.099s vs0.440s). No blockers.
Audit448 files, manifest, compileall and Python3.10 grammar pass; every production
root Python file and existing executable sh block is byte-preserved. Final checkout
and focused regression checks rerun after validation-document/manifest update.

## 2026-11-14 Bounded JSON rejection test harness (0.105.0-json-rejection-harness)

Only the 24-case JSON rejection loop uses the existing trusted serial harness.
Original duplicate/nonfinite/nonobject/surrogate cases and all rejection assertions
are preserved, with source-byte preservation added. Four real subprocess error
smokes compare exact output/exit to the harness. Existing ASCII environment/Unicode,
normal CLI roundtrips, bundle errors and documented walkthroughs stay subprocess.
All production Python, ENGINE_FILES, shared harness and CI workflow bytes unchanged.

Before: JSON loop0.840s, sampled batch bundle invalid-input0.493s. Reproducible
24-case byte/exit/source/output/state equivalence passed three alternating runs:
subprocess0.762/0.734/0.741s versus in-process0.063/0.056/0.056s. Retained four-process
smoke costs0.176s locally. These small local savings are not a claim of proportional
suite/CI acceleration; larger batch/dispatcher bottlenecks remain out of scope.
See [runtime guide](docs/TEST_RUNTIME.md) for commands and process-isolation limits.

Full local suite: 2061 tests in 149.247s, OK (one platform skip). Focused and
independent JSON/harness tests: 14 pass. Independent 24-case benchmark also passes
all equivalence and preservation checks (subprocess0.7594s vs in-process0.0639s).
No blockers. Audit450 files, manifest, compileall, Python3.10 grammar and unchanged
production/helper/workflow/old executable blocks pass. Final checkout, JSON/harness
and navigation checks rerun after documentation/manifest finalization.

## 2026-11-14 One-file dispatcher selection (0.106.0-dispatcher-selection)

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
