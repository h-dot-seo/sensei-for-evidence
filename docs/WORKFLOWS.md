# Workflows

The feature narratives that used to fill the README, grouped by workflow stage. Each
paragraph links the topic guide that documents the behavior in full, together with its
tested command block. The [command reference](COMMANDS.md) lists every script and
subcommand; [detailed usage](USAGE.md) explains field requirements, strict JSON rules,
ID migration, stage definitions and compatibility.

The framework supports plan, run, status, method and audit intents. Choose
question-appropriate established methods, preserve contradictions and uncertainty,
and distinguish supplied observations from interpretation and decisions.

Only explicit PubMed ESearch discovery and EFetch selected metadata acquisition
make live requests. No full-text retrieval, guideline currency verification,
scientific appraisal, meta-analysis, clinical recommendation or legal opinion is performed. Search pages, source locators and reviewer claims are not authenticated.
Census and conclusion readiness remain `NOT_ESTABLISHED` and `NOT_READY`.

## Implemented capabilities in detail

The README condenses this list into grouped bullets; the full statements are kept here.
Standard-library Python tools reconcile **supplied data**. The optional, explicitly
invoked PubMed clients can fetch bounded PMID lists and selected metadata; the core
never calls models:

- Optional preview-bound, keyless PubMed identifier discovery with retained native
  response observations, explicit caps/failures and separate unreviewed CSV intake.
- Explicit selected-PMID EFetch MEDLINE acquisition with title/abstract candidates,
  literal identifier reconciliation, retained native fields and separate intake.
- Declared search plans and optional page ledgers, including missing sources,
  count mismatches, overlap, truncation and incomplete pagination.
- Provider-neutral mock search/extraction receipts with hash-bound operator review
  gates; unreviewed proposals never enter accepted evidence. Mock adapters stay offline.
- Local UTF-8 CSV export provenance, strict-subset NBIB/RIS native wrappers,
  and explicit supplied identity reconciliation with raw-row retention and
  incomplete-search promotion into screening queues.
- Per-record search-occurrence provenance with exact-ID-only deduplication.
  Similar IDs are not merged; repeated IDs are not verified duplicate publications.
- Record screening, report retrieval/full-text decisions, study IDs and reasoned
  exclusions, with separate record/result/report counts.
- Explicit local UTF-8 passage checks beside supplied extraction fields, with
  source hashes, byte ranges and quotes kept separate from scientific acceptance.
- Supplied nonclinical comparison conditions with model, concentration/exposure,
  observation-time anchors, comparator and causal limitations; no procedure or inference.
- Multiple result rows per source, including null findings, with extraction-level
  IDs and traceable locators. Included reports may explicitly declare multiple
  study IDs, with separate report-study result-presence accounting.
- Supplied clinical-guideline and drug-development context, applicability limits,
  reviewer status and evidence/work-package links.
- Explicit pre-extraction source context linked to declared searches or enumerated
  records and source-review work, without inventing evidence or study IDs.
- Supplied appraisal methods and domain judgements, with reviewer provenance and
  missing-appraisal coverage. No appraisal score or consensus is inferred.
- Dependency-aware work packages, deliverables and explicit completion assertions,
  including source-review work before any result has been extracted.
- PRISMA-oriented synthesis review snapshots with exact result citations, visible
  uncited evidence and source-bound supplied reviews; no generated conclusions.
- Supplied planning ranks with rationale/uncertainty and source-staleness checks;
  ranks never override dependencies or become automated recommendations.
- Per-work-package review packets joining source lineage, guideline/development
  applicability limits, appraisal provenance and local review gaps without decisions.
- Deterministic offline ZIP bundles, SHA-256 checks, regeneration verification and
  CSV exports, plus version-to-version mechanical comparison.
- Supplied independent challenges to synthesis statements: a challenger label
  distinct from every recorded reviewer/appraiser label, the strongest alternative
  explanation, missing discriminating evidence, citation-integrity findings,
  conclusion width and outcome, bound to the challenged statements' current bases.
  A material gap must name existing reopening work or an amendment; nothing is
  generated, adjudicated, upheld or refuted.
- Mechanical conclusion-readiness gates (search plan, searches, screening, reports,
  extraction, appraisal of cited results, statement reviews, citations, challenges,
  contexts, work) with exact open items and a gate-ledger hash, plus supplied
  evidence-sufficiency and conclusion-readiness assertions bound to that hash.
  Closing every gate is bookkeeping, not sufficiency; the mechanical label stays NOT_READY.

## Start here: rehearsals on fictional fixtures

New to the tools? Follow the [first offline run](FIRST_RUN.md): 11 tested
commands from a declared question and mock receipt through explicit supplied
reviews, PRISMA accounting, nonclinical/context work and a verified bundle.
Human-authored inputs and automatic bookkeeping are separated at each step.
The [operator handoff](OPERATOR_HANDOFF.md) also lists supplied-input routes
and parser-help entry points without selecting or executing any operation.

For supplied citation files rather than mock provider receipts, follow the
[NBIB-to-evidence rehearsal](BATCH_TO_EVIDENCE.md): two native files through
explicit reconciliation, screening, reports, retrieval, results, missing
nonclinical context and a verified original-source bundle. Every decision is a
prewritten fictional assertion, not a review performed by the tools.
Then use the [second-search continuation](SECOND_SEARCH_CONTINUATION.md) to
append another originally planned search while retaining prior results and
checking changed source context.

For supported RIS exports, use [source-preserving RIS intake](RIS_INTAKE.md)
with separate explicit identity choices. Its scope is a documented subset, not
universal database-format compatibility. Preserve supported RIS and NBIB wrappers
together with exact historical imports using the separate
[typed native collection archive](NATIVE_COLLECTION_BUNDLES.md).

Start with the [operator handoff journey](OPERATOR_HANDOFF.md) to see which
steps remain human work and reproduce evidence → claim/guideline → WP → bundle
review using real CLI commands on the fictional fixture.

The combined synthetic demonstration in the [README quick start](../README.md#quick-start)
runs `examples/review-demo.json` through the handoff, status, workflow, report, bundle
and comparison commands; its deliberately unfinished bounds are listed there. Comparing
the demo with itself reports no input changes; use two supplied protocol versions for a
real mechanical comparison.

## Search plans, receipts and the mock adapter

See [the mock adapter contract](ADAPTER_CONTRACT.md) for the synthetic
search → receipt review → extraction review → report/status/bundle example.

Before connecting provider output to research, use the [search query/receipt manifest](SEARCH_MANIFEST.md)
with `examples/search-manifest.json` to inspect exact requests, missing runtime
fields and source-wise unresolved receipts. No query translation or execution occurs.

For manual-entry rehearsal, start with [receipt intake](RECEIPT_INTAKE.md).
It generates deliberately unfilled request/page fields and checks a filled mock
fixture without accepting reviews or overwriting existing research.

[Declared search-plan accounting](USAGE.md#declared-search-plan-accounting) and
[optional supplied search-page ledgers](USAGE.md#optional-supplied-search-page-ledgers)
explain how missing planned searches, count mismatches, overlap, truncation and
incomplete pagination block asserted completion; `ASSERTED_ACCOUNTED` and `RECONCILED`
mean internal consistency of supplied assertions, never an authenticated or complete search.

[Source-review work packages](SOURCE_REVIEW_WORK.md) connect unreviewed manual
receipts to search/screening/extraction deliverables without fabricating evidence
IDs. Try `examples/source-work-protocol.json` with the existing work/handoff CLIs.

[Explicit source-work intake](SOURCE_WORK_INTAKE.md) connects selected
planned searches or records to human-authored review tasks through blank drafts,
exact-context review and append-only replay. Dependencies and task meaning must
be supplied; no priority, completion or scientific work is invented.

[Pre-extraction context links](SOURCE_CONTEXTS.md) connect supplied guideline
and development questions to exact typed source references and source-review work.
They preserve applicability uncertainty and remain separate from extracted evidence.

[Document-linked source work](WORK_DOCUMENT_SOURCES.md) optionally binds named
report-source versions to a source-review task and its direct dependents. Changed
document context can stale planning/completion assertions without reopening work,
automatically accepting it, or changing legacy task hashes when omitted.

## Supplied citation files and collection review

[Local bibliographic CSV intake](BIBLIOGRAPHIC_INTAKE.md) preserves exact export
bytes, original rows and an explicit search-plan association in a detached,
unreviewed artifact. Duplicate occurrences and locator conflicts remain visible;
byte-consistency verification does not authenticate the source or promote rows
into screening, PRISMA counts, guideline links or development evidence.

For a nonblank key column with empty URL/DOI cells, the tested
[same-column mapping](CSV_KEY_MAPPING.md) declares the key as both ID and inert
locator on every row. Native values are preserved and the journey stops at an
unfilled review template; no fallback locator or publication identity is guessed.

[Native PubMed NBIB preparation](PUBMED_NBIB_INTAKE.md) retains original file
bytes, repeated fields and exact native spans while producing a verified CSV
derivative for the same human reconciliation path. No PMID, title or URL is
resolved or used for automatic identity decisions. Keep the detached native
artifact with the resulting protocol; ordinary bundles retain the CSV provenance
but do not independently verify the native conversion.

[Multiple-file NBIB preparation](PUBMED_NBIB_BATCH.md) groups explicitly
selected downloads before one human collection review, retaining per-file native
bytes and row provenance. Repeated identifiers and identical files are not
automatically removed; grouping is not verified pagination or search completeness.
Keep the detached batch wrapper alongside the protocol and ordinary bundle.

For supported RIS exports, [source-preserving RIS intake](RIS_INTAKE.md) retains
strict-subset native bytes and field occurrences without DOI/ID resolution; its
scope is a documented subset, not universal database-format compatibility.

[Explicit CSV reconciliation](BIBLIOGRAPHIC_REVIEW.md) connects those artifacts
to screening through supplied per-row identity/withholding choices and a separate
exact-context review. Repeated imports retain flat source provenance and raw-row
accounting while appending only incomplete searches, with no eligibility decisions.

[Portable collection bundles](COLLECTION_BUNDLES.md) optionally preserve
single-file native wrappers, not batch wrappers, with the ordinary research bundle. Each attachment is
checked against its exact historical import, while imports without supplied
native wrappers remain visible. Packaging never changes collection or research
decisions and does not establish search completeness.

[Batch-native collection bundles](BATCH_COLLECTION_BUNDLES.md) extend portable
delivery through a separate format that retains every original file alongside
its batch wrapper and ordinary research bundle. Exact historical import links
and all native member bytes are replayed; partial attachment stays explicit.

The [typed native collection archive](NATIVE_COLLECTION_BUNDLES.md) carries
supported RIS and NBIB wrappers together with exact historical imports in one
portable snapshot; existing NBIB archive formats do not accept RIS wrappers.

## Optional live PubMed discovery and metadata

[Bounded optional PubMed discovery](PUBMED_DISCOVERY.md) closes the gap between
manual export collection and live identifier discovery. Preview is offline; only a
matching explicitly invoked fetch contacts NCBI. Raw observations and stop reasons
remain separate from search completeness, identity decisions and extracted evidence.

After identifier discovery, [selected PubMed metadata acquisition](PUBMED_METADATA.md)
can obtain bounded EFetch MEDLINE title/abstract candidates. It preserves literal
PMID links and native source fields without silently screening or extracting evidence.

Only these two explicit fetch paths make live requests; see the
[security boundary](../SECURITY.md) for what they transmit and never do.

## Screening and PRISMA-oriented accounting

[Supplied screening reviewer positions](SCREENING_REVIEWS.md) preserve
separate title/abstract judgments, source/criteria hashes and differing or stale
assertions after collection. They never vote, adjudicate eligibility, authenticate
reviewers or replace canonical screening and PRISMA counts.

[Explicit supplied screening decisions](SCREENING_DECISIONS.md) connect those
positions to a separately authored human choice. Target-bound assembly retains
before/after rows and source/reviewer snapshots, refuses structural conflicts,
and never votes, authenticates chronology or verifies medical correctness.

The [PRISMA-oriented accounting export](PRISMA_AUDIT.md) exposes exact member
IDs and record/report/study/result links for audit, without certifying a complete
search or PRISMA compliance. Try `examples/prisma-audit.json`.

PRISMA audit JSON also exposes [work/deliverable traceability](PRISMA_AUDIT.md#work-and-deliverable-traceability):
explicit source/result work references, indirect report links and unverified
artifact assertions, without treating task completion as source approval.

[Record occurrence provenance](USAGE.md#record-occurrence-provenance) explains the
exact-ID-only deduplication scope: similar IDs are not merged, repeated IDs are not
verified duplicate publications, and record identity verification stays `NOT_ESTABLISHED`.

## Reports, retrieval and full text

[Multiple studies in one report](MULTI_STUDY_REPORTS.md) supports explicit
plural study declarations while keeping legacy record/report counts unchanged.
Missing report-study result memberships stay visible without inferring identity,
independence, study-level eligibility or exhaustive extraction.

[Supplied full-text reviewer positions](REPORT_REVIEWS.md) bind separate human
positions to declared document versions and mapped record context. Read-only
scaffolds preserve missing/unverified digests, source coverage and disagreement;
no document reading, consensus or per-study eligibility is inferred.

[Manual report registration](MANUAL_REPORT_INTAKE.md) connects explicitly
included screening records to new report rows and supplied document declarations
before full-text assessment. Retrieval and identity remain supplied assertions;
no report eligibility, study membership, result or nonclinical parameter is inferred.
[Supplied retrieval updates](REPORT_RETRIEVAL_UPDATES.md) then record a later
retrieval outcome for pending/unavailable reports without duplicate registration.
Changed source contexts expose stale retained reviews rather than refreshing them.
[Reviewed source declarations](MANUAL_SOURCE_DECLARATIONS.md) append later
supplements or separately declared versions to already retrieved reports. Existing
descriptors remain untouched, and local byte comparison stays a separate check.
The optional [report-transition archive](REPORT_TRANSITION_BUNDLES.md) retains
exact initial/application/endpoint files for a supplied contiguous segment without
changing the existing research or native-source archive formats.
The separate [extraction-transition archive](EXTRACTION_TRANSITION_BUNDLES.md)
retains ordered result intake, text correction and descriptive condition records.
Earlier wording and source selections remain bound to their recorded step context;
no prior review or downstream assertion is renewed.

[Exact report-study reviewer positions](REPORT_STUDY_REVIEWS.md) distinguish
human opinions on individual studies from report inclusion. Explicit source-ID
selections and unresolved orphan assertions remain visible without choosing a
canonical study outcome, changing PRISMA counts or filtering extracted results.

[Reviewed inventory intake](MANUAL_INVENTORY_INTAKE.md) appends completed
descriptions without manually editing the protocol. It preserves old assertions
and research counts; it does not infer study membership or renew prior reviews.

[Descriptive candidate inventory](REPORT_STUDY_INVENTORY.md) permits source-linked
human descriptions on retrieved reports before their full-text inclusion decision.
Novel-label scaffolds do not count as stored assertions or change included study
memberships, prior review targets, results or pending-work queues.

[Explicit local source-byte checks](REPORT_SOURCE_CHECK.md) compare a selected
local document with its supplied source digest through a bounded no-follow file
checker. Detached observations never certify reading, authenticity or eligibility,
change canonical state, or follow locators. Unsupported platforms fail closed.

[Explicit full-text decision records](REPORT_DECISIONS.md) apply a separately
supplied human include/exclude choice and exact study declaration to a detached
candidate. Replay against the original input precedes protocol export; conflicting
result links are rejected rather than deleted, and reviewer positions never vote.

[Inventory-candidate eligibility positions](INVENTORY_CANDIDATE_REVIEWS.md)
keep human opinions on described candidates separate from report inclusion and
included-membership reviews. Try `examples/report-study-inventory-reviews.json`.

## Results, source passages and conditions

[Manual extraction worksheets](EXTRACTION_WORKSHEETS.md) gather available
document declarations, existing pair-results and explicitly linked contexts before
new result entry. Only caller-selected report/study/record IDs are prefilled;
source selection, scientific fields and human metadata remain blank.

For the reading-to-extraction step, [selected source passage checks](RESULT_PASSAGE_CHECK.md)
show exact UTF-8 quotes beside unchanged manual result values. Source and quote
matching never replaces human interpretation or the separate result intake review.

[Manual result intake](MANUAL_RESULT_INTAKE.md) connects a collected, screened
and included report to explicit supplied results without using mock extraction
or changing prior evidence. Document associations stay in a separate replay record.

[Detached result-source comparison](RESULT_SOURCE_REVIEW.md) checks later
result/source drift against a replayed manual intake record. Differences stay
separate from approval, source authenticity and scientific interpretation.

[Explicit result text corrections](RESULT_CORRECTIONS.md) preserve an existing
finding's ID and count while applying separately reviewed wording changes. Before/
after rows and supplied sources stay in a detached replay record; earlier reviews
and downstream assertions are not renewed or scientifically reassessed.

[Multiple results from one source record](USAGE.md#multiple-results-from-one-source-record)
explains extraction-level IDs, null findings, record/study counts and why an empty
extraction queue never proves that all results in a paper were extracted.

See [nonclinical condition records](EXPERIMENT_CONDITIONS.md) for the fictional
model/condition → result → WP/synthesis review journey.

[Supplied condition intake](MANUAL_CONDITION_INTAKE.md) appends completed
comparison descriptions through explicit human review and exact replay. It binds
existing result rows and chosen document declarations without generating experimental
parameters, changing observations or validating scientific claims.

Outcome- and arm-specific sample reporting is available in the fictional
[`sampling-review.json`](../examples/sampling-review.json) workflow. It exposes
missing n semantics and independence explanations without inferring sample size
or assessing statistics. See [condition metadata](EXPERIMENT_CONDITIONS.md#outcome-specific-sample-reporting).

[`statistics-review.json`](../examples/statistics-review.json) demonstrates supplied
arm summaries, statistical metadata and explicitly oriented effect-direction
text. [Outcome statistics review](OUTCOME_STATISTICS.md) explains missing
fields and literal-label cues without numerical or scientific inference.

[`claim-comparison.json`](../examples/claim-comparison.json) adds human-supplied
observation/causal claim positions alongside source-linked results, n and statistics.
[Claim-position comparison](CLAIM_COMPARISON.md) explains exact scope,
stale review and why positions are not independent votes or inferred conclusions.

## Guideline/development context and appraisal

See [work review packets](WORK_REVIEW.md) for the synthetic guideline,
development and research-management handoff example.

[Supplied clinical and development context](USAGE.md#supplied-clinical-and-development-context)
describes the context record fields, review status and why clinical context does
not turn a cell-model finding into evidence of patient benefit.

[Reviewed guideline/development context intake](MANUAL_CONTEXT_INTAKE.md)
appends complete human-authored source/evidence contexts without inventing clinical
or regulatory judgements. New contexts stay unassigned, and existing work links,
planning/completion bases and each context's own review status remain unchanged.

[Reviewed existing-work context assignment](WORK_CONTEXT_INTAKE.md) appends
only explicitly selected context links to named work. Before/after targets expose
selected and direct-dependent source-basis changes while preserving stored ranks,
completion assertions and hashes, without automatic applicability or review renewal.

[Guideline/development amendment comparison](CONTEXT_AMENDMENTS.md) extends
compare_runs with explicit context→result→work snapshots and retained-review-label
cues. Version/access/review dates, applicability and uncertainty stay separate;
no clinical significance, regulatory decision or new priority is inferred.

[Supplied appraisal provenance](USAGE.md#supplied-appraisal-provenance) describes the
appraisal record fields; no tool or rubric is executed, and recording all rows never
promotes conclusion readiness.

[Reviewed appraisal intake](MANUAL_APPRAISAL_INTAKE.md) records human-authored
method/domain assertions against exact result IDs. Existing conflicting positions
remain separate; changed work/synthesis/completion source cues do not renew reviews.

[Detached appraisal context comparison](APPRAISAL_SOURCE_REVIEW.md) follows
exactly replayed imported appraisal IDs and their original result/source snapshots
through later supplied edits. Literal drift is separate from scientific validity;
no appraisal, work completion or prior reviewer assertion is renewed.

[Appraisal-transition archives](APPRAISAL_TRANSITION_BUNDLES.md) preserve exact
original/import/endpoint bytes for an explicitly selected contiguous appraisal
segment. Existing archives stay unchanged; source snapshots and supplied reviews
retain their historical scope without asserting complete history or current validity.

## Synthesis, independent challenge and conclusion readiness

See [synthesis review snapshots](SYNTHESIS_REVIEW.md) for the record/report/
study/result accounting and supplied statement review journey.

See [independent challenge records](INDEPENDENT_CHALLENGE.md) for the fictional
statement → challenge → reopening journey and the distinct-label rule.

See [conclusion readiness gates](CONCLUSION_READINESS.md) for the fictional
gate ledger → supplied sufficiency/readiness assertion → reopening journey and why
closed gates are not evidence sufficiency.

Together these three guides are the executable form of the workflow's steps 7 to 9
in [SKILL.md](../SKILL.md): synthesize only within evidence bounds, challenge the
strongest alternative explanation independently, and assess evidence sufficiency and
conclusion readiness separately. A recorded SURVIVES outcome is not proof, an
UNRESOLVED outcome is not a defect, a READY assertion is a supplied label bound to a
gate snapshot, and the mechanical conclusion readiness of every tool stays `NOT_READY`.

## Planning, work packages and completion

See [supplied planning assertions](PLANNING_ASSERTIONS.md) for recording a
rank, checking changed source context and keeping priority separate from dependencies.

[Prerequisite review packets](PREREQUISITE_REVIEW.md) open a selected WP and
its explicit transitive prerequisites together, preserving source/experimental/
guideline gaps and supplied planning rationale beside deliverables and completion
criteria. Dependency-first display is not an automated research decision.

[Planning rationale citations](PLANNING_RATIONALE_LINKS.md) connect existing
human planning assertions to supplied hypotheses and challenging/unresolved
positions. They add source-change tracking, not automated rationale validation,
refutation, clinical decisions or new priorities.

[Compact work navigation](WORK_NAVIGATION.md) adds `work_review.py --brief`
for packet-scoped status groups, deliverables, completion criteria and existing
review cues. It shortens the review view without choosing the next task.

[Supplied amendment notes](AMENDMENT_NOTES.md) optionally bind a human change
reason, scope and version labels to the exact inputs of compare_runs, with observed
review/work-state transitions. Matching notes are not change approval or legal,
scientific or regulatory validation.

[Completion source binding](COMPLETION_BINDING.md) flags unbound/stale COMPLETE
assertions after work/source/locator changes, reusing planning source scope. It
never verifies acceptance, renews a hash or automatically reopens work.

Selected work views also expose [direct prerequisite completion cues](PREREQUISITE_REVIEW.md#completion-source-cues-without-expanding-packets):
CURRENT/STALE/UNBOUND source labels remain visible even when full prerequisite
packets are omitted. Recorded unblocking stays separate from acceptance review.

[Portable work-package CSV exports](COMPLETION_BINDING.md#portable-csv-and-bundle-summary)
also preserve supplied completion assertions, source-binding hashes, direct
prerequisite labels and explicit nonverification states without changing work status.

[Completion amendment comparison](COMPLETION_COMPARISON.md) identifies changed
work/source sections and direct prerequisite labels across two supplied snapshots.
It separates own artifact-locator changes from source-basis changes without
reconstructing historical acceptance reasons or reopening completed work.

Add `--text` to [protocol comparison](COMPLETION_COMPARISON.md#readable-comparison-output)
for a read-only summary with exact input hashes, changed field names, all work
source states and amendment-binding results. Full JSON remains the default.

[Opt-in local artifact review](LOCAL_ARTIFACT_REVIEW.md) checks explicitly
listed synthetic local files against supplied size/SHA-256 expectations using
safe POSIX directory descriptors. Unsupported platforms fail closed; matching
bytes are never acceptance of a work package or scientific conclusion.

[Reviewed evidence-work intake](EVIDENCE_WORK_INTAKE.md) connects existing
result IDs to human-authored review deliverables and explicit prerequisites. It
adds only PLANNED tasks and preserves prior source work, evidence and assertions.

[Reviewed work completion](WORK_COMPLETION_INTAKE.md) links an explicitly supplied
artifact/acceptance assertion to the reviewed work/source basis without editing
other research or renewing existing COMPLETE assertions. Dependency changes are
shown separately from scientific readiness; artifact content is not inspected.

[Work-transition archives](WORK_TRANSITION_BUNDLES.md) preserve selected proposal
and completion records with their actual initial/endpoint protocols. Replaying
a historical segment does not renew acceptance or establish complete project history.

## Bundles, comparison and publication checks

The [portable offline research bundle](USAGE.md#portable-offline-research-bundle),
[run-to-run comparison](USAGE.md#offline-run-to-run-comparison), [concise research
status](USAGE.md#concise-research-status) and [publication inventory checks](USAGE.md#publication-inventory-checks)
are documented in detailed usage. Existing bundles require their recorded
implementation bytes for verification. Comparison hashes ignore object key order but
retain list order; exact-input bundle hashes preserve original bytes. Neither kind of
hash is a signature. Keep real research inputs and generated bundles outside this
public repository: bundles preserve all supplied data without redaction, and no
upload or external request is made by these commands.

## Export a native count crosswalk

The [native crosswalk](PRISMA_FLOW_TEMPLATE.md) derives a local CSV from supplied
PRISMA accounting, with explicit per-search method choices and a full pending-state
receipt. It never supplies missing counts or certifies diagram compatibility.

## Save a supplied-data status view

The [shareable status guide](SHAREABLE_VIEWS.md) saves existing mechanical status
counts and complete queues as detached Markdown. Supplied strings stay quoted and
fenced; absent stages remain distinct from zero, and historical records do not become
pending work. The receipt fingerprints the file without duplicating it on stdout.
No protocol, engine judgement or bundle payload changes; sharing remains a separate
authorized action.

## Save supplied-accounting flow text

The [accounting flow guide](ACCOUNTING_FLOW.md) saves Mermaid text from existing
audit nodes and partitions. Every partition is a separate group; repeated labels
are the same quantity, never additive counts. Dashed bridges change units.
Missing stages remain unknown, and study/result nodes stay detached. No renderer,
source transmission or readiness judgement is included. Keep counts private.

## Share a supplied-record worksheet

Use `views_export.py records PROTOCOL --output NEW.csv` for a detached record-level
view of existing audit joins, with a separate bounded receipt. Preserve authoritative
search indices, distinct report/result study lists and absent-stage markers.
[Records CSV](RECORDS_CSV.md) includes the tested rehearsal and privacy limits.
No cue is adjudicated; no bundle payload or engine state changes.

## Explicit continuation RIS intake

The separate [declared continuation dialect](RIS_CONTINUATION_INTAKE.md) preserves native bytes
through `ris_continuation_intake.py preview --dialect
ris-untagged-continuation-empty-paragraphs-v1` and `verify`. The four-command
synthetic walkthrough stops at an unfilled review template. Strict RIS and native
archive formats remain unchanged; retain continuation wrappers separately.

## Blank screening-position spreadsheet

[Export a blank transcription sheet](SCREENING_SHEETS.md) with
`screening_sheet.py export PROTOCOL --output NEW.csv`. Optional repeated
`--display-column NAME` selects literal retained values, never guessed titles.
Human assertion columns remain empty; this is export only, not edited-sheet
intake, screening performed or a canonical decision. Preserve export-time source
hashes and keep real sheets outside the public repository.

## Reviewed screening-sheet positions

[Append edited screening positions](SCREENING_SHEET_INTAKE.md) through the separate
`screening_sheet_intake.py target`, `assemble`, and `verify` workflow.
A separate human import review binds exact CSV bytes, protocol and implementation.
Read-only cells and source hashes must remain unchanged; blank rows are skipped,
partial/stale rows and duplicate reviewer pairs fail. No canonical decision or
reviewer supersession is inferred. Real sheets remain outside the public repository.

## Blank human-decision sheets

[Export a separate blank decisions sheet](SCREENING_DECISION_SHEETS.md) with
`screening_decision_sheet.py export PROTOCOL --output NEW.csv`. At most 100
records; optional repeated `--record-id` keeps explicit selection order. Read-only
prior screening and review snapshots never prefill human choices. This export does
not implement batch target/assemble/verify, modify canonical decisions or import
reviewer positions. Preserve source/protocol hashes; real sheets stay private.

## Read-only decision-batch target preview

[Preview an exact supplied decision sheet](SCREENING_DECISION_BATCH_PREVIEW.md) with
`screening_decision_batch.py target PROTOCOL SHEET --output NEW.json`.
The preview checks all read-only context, simulates at most 100 supplied decisions
through existing full workflow guards and drafts a blank import review. Hypothetical
steps are not applied receipts or approval; no candidate protocol/application is
exported, and batch assemble/verify remains unimplemented.
