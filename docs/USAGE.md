# Detailed usage and compatibility

For a first complete rehearsal, use the [tested offline walkthrough](FIRST_RUN.md).
Run command examples from the repository root. See the [quick start](../README.md)
for the combined synthetic demonstration.

질문 정의부터 근거 수집·종합·반론 검토·결론 범위 판단까지 연결하는 연구 방법 프레임워크입니다.
A method-first framework for traceable evidence research and bounded conclusions.

Use `python PATH/TO/sensei-for-evidence/research_status.py ./my-protocol.json` or
`python PATH/TO/sensei-for-evidence/sensei.py run research_status.py ./my-protocol.json`
from your own working directory. Relative inputs and outputs remain relative to that
directory; guide examples still run from the repository root.

## Core principle

**Search completion is not evidence sufficiency.** A persuasive narrative does not
replace a reproducible search, claim-linked evidence or an explicit uncertainty bound.

## Included

- Workflow design for neutral discovery, protocol lock, search, screening, extraction,
  normalization, appraisal, synthesis, independent challenge and controlled reopening.
- A portable agent workflow (`SKILL.md`) with plan/run/status/method/audit intents.
- A deterministic research-state validator (`validate_run.py`) and synthetic tests/example.

No private research projects, experiment results, evidence databases, article/book
full text, extracted figures, paid databases or real patent-census datasets are included.
Apart from the separately invoked, preview-bound PubMed ESearch/EFetch clients, this
repository does not execute searches; it does not read papers, run an LLM, determine
scientific adequacy or deliver a legal freedom-to-operate opinion.

## Quick start

For your own supplied question, start with the [blank protocol template and check](PROTOCOL_SCAFFOLD.md).
For a complete fictional rehearsal, use [First run](FIRST_RUN.md). The separate
[checkout check](CHECKOUT_CHECK.md) inspects installation bytes, not research validity.
The legacy agent-state example below uses a different state schema, not this base.

## Research intents

| Intent | Output |
|---|---|
| Plan | Research map, scope, sources, criteria, extraction, appraisal and stop conditions |
| Run | Execution within a resolved question and versioned protocol |
| Status | Phase, coverage, contradiction, blocker and next action |
| Method | Established term, rationale, applicability, inputs, procedure, failures and references |
| Audit | Claim/evidence challenge, alternatives, surviving boundary and discriminating gaps |

Prefer established methods and current authoritative references appropriate to the
question. This framework does not reproduce or replace those standards.
See [architecture](ARCHITECTURE.md), [workflow](../SKILL.md),
[publication boundary](../PUBLICATION.md), [security](../SECURITY.md), and [rights](../RIGHTS.md).
No license has been selected by the owner yet.

## Search-to-work-package workflow

```sh
python evidence_workflow.py examples/protocol.json
```

Provide a versioned question, criteria, exact search source/query/time/window,
record IDs and paging assertions, reasoned screening decisions, extracted evidence
and gaps. IDs must be normalized by the caller across search sources. Output preserves
search/screening ledgers, reconciles record counts before and after deduplication,
reports pending screening/extraction and creates evidence-linked work packages with
deliverables and acceptance criteria. Model, intervention, comparator, endpoint,
result, limitation and mechanism basis are explicit. Intervention evidence alone
does not establish causality. Clinical/development context may be supplied in gap
records; no clinical guideline retrieval or recommendation is performed.

Record/report bookkeeping and dependency scheduling are implemented, but this
is not a complete PRISMA implementation. Actual report retrieval, scientific
appraisal and independent guideline/development evidence verification remain
future work. Coverage assertions are not independently authenticated; census and
conclusion readiness stay unestablished.

### Dependency-aware research work

Gaps may include stable `work_package_id`, `depends_on` ID lists and `status`
(`PLANNED`, `IN_PROGRESS`, `COMPLETE`). Output includes a topological execution
order and unfinished dependencies. Unknown IDs, duplicate IDs and cycles fail.
`COMPLETE` requires `artifact_locator`, `acceptance_verified: true` and completed
dependencies. These are operator assertions; the tool does not fetch artifacts
or certify experiment quality. Evidence links remain mandatory for evidence-review
work. Explicit [source-review work](SOURCE_REVIEW_WORK.md) instead requires typed
source references and empty evidence IDs.

## Report retrieval and full-text screening

```sh
python prisma_reports.py examples/report-protocol.json
```

Add `reports` with unique `report_id`, included `record_ids`, `retrieval`
(`retrieved`, `not_retrieved`, `pending`) and `decision` (`include`, `exclude`,
`pending`). Retrieved reports require a locator, failures/exclusions require a
reason, and included reports require legacy `study_id` or explicit plural `study_ids`.
The two fields are mutually exclusive. See [multiple studies](MULTI_STUDY_REPORTS.md)
for opt-in validation and separate report-study membership accounting. The JSON output contains report
and study counts, pending work, exclusion counts, a deterministic report ledger and
CSV text. CSV cells beginning with formula characters are escaped. Multiple reports
may share a study ID; each input record maps to at most one report. Unmapped advanced
records remain visible. Extracted evidence must map to a retrieved, included report
that explicitly declares its study ID. Changed full-text decisions fail until the operator reconciles affected
extractions and work packages; evidence is never silently deleted. It is PRISMA-oriented bookkeeping,
not a complete compliance checker, search backend or scientific review.

## End-to-end and CI verification

`tests/test_cli_e2e.py` runs the synthetic workflow through actual CLI subprocesses and
checks failed inputs and reproducible output. The suite is the `tests/` package:
`python -m unittest discover -v` from the repository root recurses into it, and one
module runs as `python -m unittest tests.test_cli_e2e -v`. GitHub Actions runs standard-library
tests, publication scanning and manifest byte verification on Linux and Windows
with Python 3.10 and 3.12. Actions are commit-pinned; token permissions are read-only,
checkout does not persist credentials, no secrets or deployment steps are used.
The manifest describes LF-normalized published files, enforced by .gitattributes.
External model/search behavior and scientific meaning are not evaluated by CI.

## Portable offline research bundle

```sh
python research_bundle.py create examples/report-protocol.json ../synthetic-research.zip
python research_bundle.py verify ../synthetic-research.zip
```

The ZIP contains the exact input protocol, validated research/report JSON, report
and work-package CSV, a bounded summary and a SHA-256 manifest. Fixed ZIP metadata
and deterministic serialization reproduce identical bytes from identical input.
The output path must not exist. Validation occurs before creating it; an interrupted
filesystem write can leave an incomplete file, which verification rejects. Verify
checks a fixed entry set, a 50 MB uncompressed size bound, each payload hash, input
hash and regenerated derived outputs without extracting paths. It detects altered
derived results even if their manifest hashes were changed, but does not authenticate
the original protocol. CSV formula-leading cells are escaped. Store real bundles
outside this public repository; no uploads or external calls are made.

Bundle schema 2 additionally records the exact implementation bytes for all 28
modules listed in `ENGINE_FILES` in `research_bundle.py`, including the bundle
verifier itself and its recorded helpers. Retain that
source revision with each bundle; verification fails closed on implementation
drift. Duplicate JSON keys and nonstandard numeric constants are rejected. A
record-only protocol is supported: `reports.json` is null, report CSV contains
only its header, and report/study counts say `not supplied`, never zero.
The input protocol bytes are preserved exactly, so different whitespace or object
key order can yield different archive bytes despite equivalent results. Hashes
are not signatures. No source authenticity, completed census, scientific adequacy,
clinical recommendation or full PRISMA compliance is established.

The previously unpublished schema-1 prototype must be rebuilt from its retained
protocol to use schema 2. Only one bundle engine is shipped; a redundant JSON-only
prototype was consolidated into the portable ZIP workflow before publication.

## Supplied clinical and development context

```sh
python evidence_workflow.py examples/context-protocol.json
python research_bundle.py create examples/context-protocol.json ../synthetic-context.zip
```

By default, optional `contexts` link supplied `clinical_guideline` or `drug_development`
records to extracted evidence IDs. Each record requires a unique `context_id`,
title, issuer, locator, version, ISO access date, population/setting, relevance,
applicability, limitations and at least one known evidence ID. Guideline records
require recommendation strength and evidence certainty; development records
require development stage and regulatory status. Use `unknown` when unassessed,
not an invented positive claim. These strings are operator-supplied assertions.

Work packages may list `context_ids`; each default evidence context must share an
evidence ID with that work package. Output shows linked study IDs, pending
context reviews and unassigned contexts. A context defaults to `pending`;
`reviewed` requires a reviewer and ISO review date but does not establish source
authenticity, guideline currency, applicability or scientific validity. Review
status is separate from work-package completion and never promotes conclusion
readiness. Dangling references fail rather than silently dropping context.

Alternatively, explicit `context_scope: "source_review"` uses empty `evidence_ids`
and nonempty typed `source_refs` for a declared search or enumerated record. It
can attach only to source-review work sharing an exact typed reference. It never
creates linked study IDs or inherits extracted results. Source references outside
this explicit scope are rejected. See [pre-extraction context links](SOURCE_CONTEXTS.md)
for provenance rules, supplied review metadata, comparison limits and the
fictional source-context example.

The same links survive report output and bundle JSON/CSV; summary reports pending
context reviews. Existing protocols without contexts remain supported. All
examples are synthetic. No guideline retrieval, regulatory assessment or clinical
recommendation is performed, and clinical context does not turn a cell-model
finding into evidence of patient benefit.

## Declared search-plan accounting

```sh
python evidence_workflow.py examples/planned-protocol.json
```

Optional `search_plan` is a nonempty list of stable `search_id`, exact `source`,
`query` and `window` entries. When supplied, each executed search must reference
one unique planned ID and exactly match that scope. Scope changes must be
reconciled explicitly under a revised protocol rather than silently accepted.
Repeated attempts are not merged automatically; preserve them in separately
versioned inputs. Existing protocols without a plan remain supported and show
`NOT_SUPPLIED`, not complete planned coverage.

The audit exposes missing planned searches, incomplete paging/count assertions,
recorded errors and per-item reasons. Missing searches have null enumerated
counts, distinct from an executed zero-result search. Count assertions must be
nonnegative integers; booleans and floats never establish completion. The same
audit survives report output and bundles.

`ASSERTED_ACCOUNTED` means only that every declared search has a supplied matching
ledger with internally consistent completion assertions. It does not establish
that the plan was comprehensive, the query adequate, receipts authentic or all
relevant literature found. No searches are performed, and census/conclusion gates
remain unestablished/not ready. The synthetic example deliberately omits one
planned source so that the remaining work stays visible.

Optional search flags `truncated`, `pagination_limited` and
`field_pages_pending` also block asserted completion. Omission remains compatible
with older inputs; a supplied flag is resolved only when explicitly `false`. True,
null and malformed values remain unresolved, even if returned counts match and
`has_more` is false. This prevents a capped result set from being marked complete
solely because its reported count matches the enumerated IDs.

The standalone state validator uses the same search-completion rules as the
workflow. Its `enumerated_ids` map to the workflow's `record_ids`; completed
searches require explicit `has_more: false`, strict integer totals and resolved
optional blockers. Malformed search containers and identifier lists return
validation errors, and Boolean screening counts are not accepted as integers.

Report IDs and required retrieval locators, included study IDs, exclusion/failure
reasons and work-package deliverables must be nonblank strings, not merely truthy
values. Every work package requires a nonempty list of unique known evidence IDs,
including completed packages. Full-text exclusions therefore cannot be reconciled
by clearing a work package's evidence links and retaining a completed claim.
Completed packages also require a nonblank artifact locator. Pending report
retrieval does not require a locator or study ID that is not yet available.

Report and work-package CSV use one conservative escaping rule: cells beginning
with formula characters or whitespace receive an apostrophe before their original
text. This includes newline/control/Unicode whitespace prefixes, avoiding divergent
export behavior when a spreadsheet consumer trims leading whitespace. Original
protocol and JSON evidence remain unchanged. The rule is defensive text handling,
not certification of every spreadsheet application's import behavior.

## Multiple results from one source record

```sh
python evidence_workflow.py examples/multi-result-protocol.json
```

Evidence rows may carry a unique `evidence_id`; omitted IDs default to `record_id`
for existing one-result-per-record inputs. Multiple rows can share a source
`record_id` when their evidence IDs differ. Each row still requires its own
locator, model, intervention, comparator, endpoint, result, limitations and
mechanism basis. The synthetic example keeps both a changed readout and a null
result from one report without inventing another source record.

Work-package and context `evidence_ids` refer to extraction IDs. If explicit IDs
replace legacy record IDs, update those references together; record IDs are not
automatically treated as aliases. Duplicate implicit IDs fail, and the original
input is not mutated. Full-text report/study reconciliation checks every result.

`flow.extracted` counts result rows, while `extracted_records` and
`extracted_studies` count distinct supplied source-record and study IDs. More rows
do not create more independent studies. `extraction_pending` lists included
records with no extracted row; an empty list does not prove all results in a paper
were extracted. `extraction_completeness` stays `NOT_ESTABLISHED`. Statistical
dependence, endpoint comparability, study identity and scientific adequacy remain
operator-review responsibilities, not automated findings.

Standalone report JSON includes the normalized evidence ledger, so extraction IDs
can be traced back to source record IDs even without a bundle. The current model
requires one supplied study ID per source record/report unless an included report
explicitly declares plural `study_ids`. Without that opt-in, conflicting study IDs
across result rows fail even when the optional report ledger is absent. Use the
explicit [report-study membership model](MULTI_STUDY_REPORTS.md), never silent
reassignment of endpoint rows or inferred study independence.

Bundle ZIP creator metadata is explicitly fixed across Unix and Windows instead
of inheriting the host default. Reproducible archive bytes still require identical
input bytes and implementation files; source line endings are enforced by this
repository's attributes.

Report-level extraction accounting is separate from title/abstract screening.
`extraction_pending_reports` lists only full-text-included reports with no linked
result row; excluded or unretrieved reports do not enter that queue.
`report_flow.reports_with_extraction` counts distinct reports, not source aliases
or endpoint rows. The older record-level `extraction_pending` is explicitly
scoped by `extraction_pending_scope` to title/abstract-included source records
without any row. An empty queue at either stage never certifies exhaustive
extraction; the extraction-completeness flag remains unestablished.

## Supplied appraisal provenance

```sh
python evidence_workflow.py examples/appraised-protocol.json
```

Optional `appraisals` preserve a declared method, version and method locator,
reviewer/date, limitations and domain-level judgement, rationale and source
locator. Each unique `appraisal_id` links a nonempty set of known extraction IDs
within one supplied study ID. A record applies only to its listed extraction IDs;
it does not silently appraise other results from the study. Domain names must be
unique within an appraisal. Judgement labels are retained as supplied because
different methods use different rubrics.

The output links appraisal IDs to result rows and work packages and exposes
`evidence_without_recorded_appraisal`. Multiple reviewers' records, including
different judgements, remain separate; no score or consensus is calculated.
Reports and portable bundles retain the same provenance and missing coverage.
Existing inputs without appraisals show absent recorded appraisal, not poor
quality or a completed appraisal.

No tool or rubric is executed or validated. Method suitability, source authenticity,
domain completeness, assessor independence and scientific adequacy require review.
The example uses an explicitly synthetic placeholder method, not a recommended
appraisal standard. Recording all rows never promotes conclusion readiness.

Work-package CSV also includes linked appraisal IDs, result IDs without recorded
appraisal and pending context-review IDs. These are transparent review queues,
not inferred blockers or completion certifications. JSON retains the complete
domain judgements and provenance.

## Consistent JSON entrypoints

All workflow, report, state-validation, bundle, comparison and status CLIs use
one strict JSON reader.
Duplicate object keys, unpaired Unicode surrogates, NaN/Infinity and numbers outside finite float range fail
instead of being silently reinterpreted. Protocol roots must be objects. CLI input
files and output streams use UTF-8, including redirected Windows output.
Bundle verification also rejects malformed manifest containers, noninteger schema
versions and invalid file metadata with ordinary validation errors. These checks
establish input consistency, not authenticity or scientific correctness.

## Supplied screening reviewer positions

For separate human title/abstract positions before canonical screening, use
`python screening_review.py PROTOCOL.json --text`. Add `--template` to prepare
unfilled assertions and `--output NEW_PATH` to save a separate JSON report without
overwrite. See [screening reviewer positions](SCREENING_REVIEWS.md) for exact source
binding, disagreement, source-change and non-adjudication behavior.

When a human explicitly supplies the canonical choice, the separate
`screening_decision.py target/assemble/inspect` workflow can retain its context
and produce a new protocol candidate. It does not fill a verdict automatically.
See [supplied decision receipts](SCREENING_DECISIONS.md) for concurrency hashes,
before/after validation, immutable inputs and retrospective history limits.

## Offline run-to-run comparison

```sh
python compare_runs.py before-protocol.json after-protocol.json
python compare_runs.py before-protocol.json after-protocol.json --text
```

Both inputs must pass current workflow and optional report reconciliation. The
comparison reports canonical input hashes, changed top-level fields, record-ID
additions/removals, stable-ID ledger additions/removals/changed fields and before/
after counts. Screening, extraction rows, work packages, contexts, appraisals,
reports and declared-plan status are covered. It reports field names and IDs,
not an automatically interpreted scientific narrative.

`unversioned_change` flags differing inputs that retain the same version label.
A changed version label does not authenticate history, justify an amendment or
mean that findings improved. Object key order is ignored for these comparison
hashes; list order is retained. They are not the exact-byte receipt hashes used
by portable bundles. Compare hashes are not signatures.

Use explicit stable work-package IDs across versions. Legacy generated IDs are
positional; the comparison exposes them and warns that insertion/reordering can
change apparent identity. Explicit extraction-ID changes are additions/removals,
not guessed matches. Missing report ledgers stay null rather than becoming zero
counts. No inputs are edited, source searches performed or readiness promoted.

Comparison ledgers are recomputed with the current implementation, not replayed
with each historical run's engine. Output records implementation SHA-256 values,
including the comparator, for reproducibility; retain those source bytes when
archiving a comparison. The hashes do not authenticate amendment history.

If either input explicitly declares report `study_ids`, an additional
`report_study_comparison` matches exact `(report_id, study_id)` pairs, including
scalar declarations on the other side. Reordering or scalar-to-singleton migration
retains pairs but shows changed pointers/form; pointers are not longitudinal IDs.
Changed literal IDs are removals/additions, never inferred renames. Separate
report/result changes and pair counts expose partial result coverage without
changing existing report-level accounting. Absent report ledgers retain null
counts rather than becoming empty ledgers. Legacy-only comparison shapes are
unchanged. See [multiple studies within a report](MULTI_STUDY_REPORTS.md) for the
snapshot fields, verification limits and migration examples.

## Optional supplied search-page ledgers

```sh
python evidence_workflow.py examples/paged-protocol.json
```

A search may include `pages`, each with a unique positive `page_number`, a list
of unique nonblank `record_ids`, explicit Boolean `has_more` and optional error.
Page numbers start at one and appear in order without gaps; all intermediate
pages indicate more pages and the final page indicates none. Page record IDs
use the same caller-normalized identity convention as the search-level list.
Optional page-level `truncated`, `pagination_limited` and `field_pages_pending`
flags use the same explicit-false resolution rule as their search-level counterparts.

The audit reports page count, record occurrences and distinct records. Gaps,
reordering, unresolved paging, overlap, recorded errors or a page/search record-set
mismatch prevent asserted search completion. Overlap is retained as an unresolved
reconciliation issue, not silently discarded. Malformed page structures fail.
An omitted ledger is `NOT_SUPPLIED` with null counts, distinct from one explicit
empty final page representing a supplied zero-result search.

Workflow, declared-plan, report and bundle outputs preserve the accounting.
Report output retains search coverage even without a declared plan. The state
validator always checks page structure and applies completion rules only when
completion is asserted. `RECONCILED`
only means page-level assertions agree internally; neither pages nor search
receipts are authenticated, queries assessed or sources searched by this code.
Legacy inputs without pages remain supported, and census readiness stays
`NOT_ESTABLISHED`.

## Concise research status

```sh
python research_status.py examples/review-demo.json --text
python research_status.py examples/review-demo.json
```

The status command summarizes existing validated ledgers rather than executing
research. JSON preserves IDs and reasons for missing planned searches, incomplete
searches, unscreened records, report mapping/retrieval/full-text/extraction queues,
context review, absent recorded appraisal and dependency-blocked work. `--text`
prints a shorter count summary. No total is summed across these overlapping stages.

Missing plan/report stages use null counts and `not supplied`, not zero pending
work. The record-level extraction queue retains its title/abstract scope; report
queues use full-text eligibility. `dependency_unblocked_planned_work` describes
only declared dependencies, not scientific permission or suitability to begin.
Completed work remains an operator assertion, and readiness is never promoted.

Status and comparison use the same sorted compact UTF-8 JSON representation for
semantic input hashes. Both record implementation hashes; these hashes are neither
exact-byte receipt hashes nor signatures.

## Publication inventory checks

```sh
python audit_publication.py
python verify_manifest.py
```

The publication manifest now covers the complete checkout inventory, excluding
Git metadata, generated Python caches and the manifest itself. Extra unlisted
files fail verification instead of silently falling outside its hash coverage.
Unreadable directories and nonregular filesystem entries also fail closed.
File metadata, canonical relative paths, portable case uniqueness, missing files
and exact bytes are checked. Use a canonical root path when calling the verifier API. Symlink roots or their
ancestors, manifests, file entries and parent
components, including Windows reparse points/junctions, are rejected without
recursing through them. Do not place private inputs or generated bundles inside
the public checkout. These checks do not authenticate authorship, detect every
secret or establish redistribution rights.

### Release assertion checks

The legacy research-state validator requires literal JSON `true` for a COMPLETE
release's QA, storage, reference verification and artifact-existence assertions.
Strings such as `"false"` and numeric `1` are not accepted as positive assertions.
Every explicitly cited reference, as well as every reference flagged as included
in the report, must be verified. These are checks of supplied assertions, not
independent verification of references, artifacts, evidence sufficiency or science.

### Record occurrence provenance

`record_provenance` in research and report JSON lists each distinct supplied
`record_id` in sorted order, with an `occurrences` array retaining every search
position (`search_index`, zero-based), optional `search_id` (null if absent), and
`source`. The research/report `search_ledger` provides the query and other supplied
metadata at that position. Repeated source labels remain distinct occurrences.
Positions apply only to this protocol, not stable IDs across edited protocols.

Existing `flow.identified` counts search-record occurrences, `flow.unique_records`
counts exact distinct IDs, and `flow.duplicates` counts repeated exact-ID
occurrences. These names remain for compatibility. No case folding, trimming,
bibliographic matching or cross-source entity resolution occurs. Use consistent,
unambiguous IDs upstream; different IDs for one publication stay separate, and an
accidental shared ID can collapse different publications. The tool cannot detect
those identity errors. `deduplication_scope` is `exact_supplied_record_id_only` and
`record_identity_verification` remains `NOT_ESTABLISHED`. Compact status exposes
these bounds rather than repeating the full source ledger. Bundles preserve the
ledger in existing JSON payloads without changing the archive file set.

Optional search IDs need not be unique without a declared plan, so use the search
position for this ledger lookup. Page occurrences are separate: overlap across
pages remains an unresolved search audit issue and does not inflate search-level
record occurrence counts.

The state validator rejects malformed screening/reference/release containers and
artifact entries with ordinary validation errors, including machine-readable CLI
JSON. Reference numbers and cited numbers must be positive JSON integers, excluding
booleans, floating-point values and null; cited numbers must be unique. Previously
accepted loosely typed reference IDs must be converted explicitly upstream.
Reference flags, when supplied, must be booleans. Required artifact names and
artifact types must be nonempty strings. These selected structural checks do not
constitute a complete state schema or establish that an artifact actually exists.

Each supplied screening count must be a nonnegative integer even if the rest of
its reconciliation equation is omitted. Arithmetic reconciliation is applied only
when all three counts in that equation are supplied.

### Long work-package dependency chains

Dependency ordering uses iterative traversal, so a valid long chain does not
consume Python call-stack depth. Existing dependency-order ties, unfinished-work
checks, cycle rejection and supplied completion assertions are unchanged. This is
not a claim of unlimited scale: available memory, input size and bundle limits
still apply. Dependency-unblocked work is not approval to perform an experiment.

Bundle creation and verification share a 50,000,000-byte limit on the sum of all
uncompressed ZIP entry bytes, including the manifest. Creation rejects oversized
outputs before writing the destination, rather than creating a bundle that its own
verifier cannot accept. ZIP container overhead is not part of this threshold.
This is an output-size safeguard, not a streaming/input-memory limit; protocol
processing and derived payload construction still occur in memory.

## Mock provider adapter

See [the versioned adapter contract](ADAPTER_CONTRACT.md) for the provider-neutral
fixture schema, review hash boundaries, CLI export and end-to-end synthetic demo.
This is an offline mock runner, not a live literature or model API integration.

## Work-package review packets

See [the work-review contract](WORK_REVIEW.md) for source-linked guideline and
development context, explicit extraction-level appraisal scope and pending review
items beside each supplied deliverable. No scientific or medical decision is made.

## Supplied planning assertions

See [planning ranks and source staleness](PLANNING_ASSERTIONS.md). The workflow
exposes source/hash review targets but never chooses a rank or renews a stale
assertion. Missing/stale planning queues remain separate from dependency status.

## Synthesis review snapshot

See [PRISMA-oriented accounting and supplied synthesis review](SYNTHESIS_REVIEW.md)
for exact result citations, all stage ledgers, uncited evidence and pending/stale
reviews. This is not generated scientific synthesis or a completed systematic review.

## Supplied nonclinical conditions

See [comparison condition records](EXPERIMENT_CONDITIONS.md) for explicit model,
treatment/comparator, concentration, exposure and anchored observation-time metadata.
Reporting states and causal limitations are preserved without scientific inference.

Explicit `work_type: source_review` can use empty evidence_ids only with validated
source_refs to declared searches or enumerated records. Legacy evidence work still
requires extracted result IDs. See [source-review work](SOURCE_REVIEW_WORK.md).


### Completion assertions in work-package exports

Bundles append [completion-source columns](COMPLETION_BINDING.md#portable-csv-and-bundle-summary)
to `work-packages.csv` while preserving the previous column order. Supplied
artifact/acceptance fields, current versus supplied basis hashes, nonverification
labels and direct prerequisite source labels stay separate from recorded work
status. The bounded summary includes unbound and stale completion counts. Matching
hashes or a valid ZIP never certify scientific or deliverable acceptance.

Full-text report review has a separate [source/version and human-position
workflow](REPORT_REVIEWS.md). `report_review.py` offers read-only targets and blank
scaffolds, preserving unbound document digests and unavailable reports without
changing canonical full-text decisions or claiming actual document verification.

For distinct human opinions on individual studies, use the [report-study review
workflow](REPORT_STUDY_REVIEWS.md). Pair-specific scaffolds leave source selections
and every human field blank. This does not infer per-study eligibility from report
inclusion or change existing extracted results.

For candidate descriptions before a full-text inclusion decision, use the
[study inventory workflow](REPORT_STUDY_INVENTORY.md). Supply a report ID and an
explicit human study label to generate a blank source-linked scaffold without
creating an included membership or eligibility judgment.

For opt-in local file comparison, see [explicit source-byte checks](REPORT_SOURCE_CHECK.md).
The separate manifest maps exact source IDs to local relative files; no document
is fetched or interpreted. Only supported secure POSIX access is used, and an
observation never upgrades the ordinary protocol's source or human-review status.

To record a human full-text include/exclude choice, use [detached report decision
records](REPORT_DECISIONS.md). Save the application record first, then replay it
against the original protocol before exporting the candidate. Existing results
must remain structurally compatible; no reviewer consensus or study identity is
inferred.

## Optional bounded PubMed identifier discovery

See [PubMed discovery](PUBMED_DISCOVERY.md) for the separate preview/fetch/native
observation/verification/conversion route. Only explicit, preview-bound fetch is
networked; ordinary tools and the mock adapter remain offline. The API returns
identifiers, not abstracts or extracted findings. No real network query is part of
this repository's synthetic tests or documented offline rehearsal.

For explicitly selected PMID metadata, follow [PubMed metadata](PUBMED_METADATA.md).
Its rehearsal is offline; only its preview-bound fetch retrieves EFetch MEDLINE
text. Inspect native title/abstract candidates and exact-ID mappings, then make
separate collection identity choices. Existing research is never silently enriched.

For completed manual result candidates, [source passage checks](RESULT_PASSAGE_CHECK.md)
provide a local UTF-8 line catalog and exact quote comparisons. All source choices,
field associations and byte ranges remain explicit human input. Native Windows
source access is unsupported and fails closed; no PDF/OCR or semantic inference is
performed. Preserve the original sources and separate intake review.

## Tested search-reference scale shape

The default regression uses one search with N unique records, N independent
results and N work packets each citing one result, no reports, statements,
contexts, units or appraisal cross-links. At N=200 and400, synthesis and work
JSON output must grow by less than3x when N doubles. Time is not asserted. This
is a shape-specific size regression, not a general linear complexity guarantee
or scientific validation. Broad statements and `other_*_evidence_ids` can still
produce quadratic output. The bundle50 MB limit is unchanged. Read-only existing
synthesis/work CLI inputs are not bounded; the HTML view separately limits input
and output. Start with research_status for large projects.

## Legacy agent-state validator

Python 3.10+, standard library only:

```sh
python3 sensei.py check
python3 validate_run.py examples/state.json
```

Full verification (several minutes): `python3 -m unittest discover -v`,
`python3 audit_publication.py`, and `python3 verify_manifest.py`. The
[checkout smoke check](CHECKOUT_CHECK.md) is not the full suite, CI or research validation.

The pending synthetic state passes consistency checks while its conclusion remains
`NOT_READY`. A valid file is not a completed study. `COMPLETE` additionally requires
explicit sufficiency, readiness, QA, storage and traceable citation/artifact fields;
these remain recorded assertions until independently checked against real evidence.


[Inspect protocol root field names](PROTOCOL_KEYS.md): read-only known/unknown names,
not value validation, typo correction or a research gate.

[Authored document schemas and explain](SCHEMAS.md) cover the starting-base and
collection-choice/review path. Shape checks do not replace exact workflow validation.

Publication maintainers: [manifest regeneration](MANIFEST_BUILD.md), for non-engine changes without automatic replacement.

Retained artifact navigation: [record kinds, object versions and verification guides](RECORD_SCHEMAS.md). This index is not validation or migration.

For status, handoff and comparison CLI input limits and classified, non-echoing
errors, see [view input failures](VIEW_INPUT_ERRORS.md). Successful and negative
report contracts are unchanged; this is not a repository-wide error policy.
