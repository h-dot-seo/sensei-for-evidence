# sensei-for-evidence

질문 정의부터 근거 수집·종합·반론 검토·결론 범위 판단까지 연결하는 연구 방법 프레임워크입니다.
A method-first framework for traceable evidence research and bounded conclusions.

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
This repository does not itself execute searches, read papers, run an LLM, determine
scientific adequacy or deliver a legal freedom-to-operate opinion.

## Quick start

Python 3.10+, standard library only:

```sh
python3 validate_run.py examples/state.json
python3 -m unittest discover -v
```

The pending synthetic state passes consistency checks while its conclusion remains
`NOT_READY`. A valid file is not a completed study. `COMPLETE` additionally requires
explicit sufficiency, readiness, QA, storage and traceable citation/artifact fields;
these remain recorded assertions until independently checked against real evidence.

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
See [architecture](docs/ARCHITECTURE.md), [workflow](SKILL.md),
[publication boundary](PUBLICATION.md), [security](SECURITY.md), and [rights](RIGHTS.md).
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
or certify experiment quality. Evidence links remain mandatory.

## Report retrieval and full-text screening

```sh
python prisma_reports.py examples/report-protocol.json
```

Add `reports` with unique `report_id`, included `record_ids`, `retrieval`
(`retrieved`, `not_retrieved`, `pending`) and `decision` (`include`, `exclude`,
`pending`). Retrieved reports require a locator, failures/exclusions require a
reason, and included reports require `study_id`. The JSON output contains report
and study counts, pending work, exclusion counts, a deterministic report ledger and
CSV text. CSV cells beginning with formula characters are escaped. Multiple reports
may share a study ID; each input record maps to at most one report. Unmapped advanced
records remain visible. Extracted evidence must now map to a retrieved, included report with the same
study ID. Changed full-text decisions fail until the operator reconciles affected
extractions and work packages; evidence is never silently deleted. It is PRISMA-oriented bookkeeping,
not a complete compliance checker, search backend or scientific review.

## End-to-end and CI verification

`test_cli_e2e.py` runs the synthetic workflow through actual CLI subprocesses and
checks failed inputs and reproducible output. GitHub Actions runs standard-library
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

Bundle schema 2 additionally records the exact implementation bytes for
`evidence_workflow.py`, `prisma_reports.py`, `context_links.py`, `search_audit.py`,
`csv_safety.py`, `appraisal_links.py` and `research_bundle.py`. Retain that
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

Optional `contexts` link supplied `clinical_guideline` or `drug_development`
records to extracted evidence IDs. Each record requires a unique `context_id`,
title, issuer, locator, version, ISO access date, population/setting, relevance,
applicability, limitations and at least one known evidence ID. Guideline records
require recommendation strength and evidence certainty; development records
require development stage and regulatory status. Use `unknown` when unassessed,
not an invented positive claim. These strings are operator-supplied assertions.

Work packages may list `context_ids`; every referenced context must share an
evidence ID with that work package. Output shows linked study IDs, pending
context reviews and unassigned contexts. A context defaults to `pending`;
`reviewed` requires a reviewer and ISO review date but does not establish source
authenticity, guideline currency, applicability or scientific validity. Review
status is separate from work-package completion and never promotes conclusion
readiness. Dangling references fail rather than silently dropping context.

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
requires one supplied study ID per source record/report; conflicting study IDs
across result rows fail even when the optional report ledger is absent. Supporting
multiple studies in one report requires a future explicit model extension, not
silent reassignment of endpoint rows.

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
