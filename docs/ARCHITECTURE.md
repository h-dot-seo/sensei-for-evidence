# SENSEI evidence workflow

## Checkout entry point

`sensei.py` provides discovery, transparent script dispatch and a bounded read-only
`check`. The check uses the unchanged strict publication verifier, compiles only
manifest-listed Python source in memory, then runs one synthetic status with bytecode
writes disabled. Unlisted ordinary files warn without relaxing publication verification;
changed/missing listed files and unsafe inventory entries fail before fixture execution.
This is not authentication, the full suite, CI or research validation. Engine and
adapter semantics are unchanged. See [checkout check](CHECKOUT_CHECK.md).

## Entry and neutral discovery

Resolve the research target, use context and decision-critical scope. Conduct neutral
discovery before fixing a favored mechanism or persona interpretation. Lock a research
map with question, boundaries, evidence classes, sources, search windows, eligibility,
extraction dimensions, appraisal, challenge and expected outputs.

## Protocol and search

Version the protocol before main execution. Record exact query, source, run time,
filters, search window, returned identifiers, expected count, paging/truncation and
failures. Preserve raw retrieval events before deduplication. Stop rules are controlled
and may be reopened through an amendment; never equate exhaustion with sufficiency.

## Screening and normalization

Maintain explicit inclusion/exclusion reasons and count reconciliation. Distinguish
records, reports, studies, results and claims. Link every normalized evidence row to
source ID, original source hash where available, locator, population/model, intervention,
comparator, endpoint, result, uncertainty and limitations. Abstract-only evidence must
remain abstract-only. Figures cannot be assigned exact values from visual estimates.

## Appraisal and synthesis

Separate observation, evidence appraisal, interpretation, inference and decision.
Distinguish association from causation, direct from indirect mechanisms, model from
human relevance, exposure plausibility from demonstrated target engagement, and
absence of evidence from evidence of absence. Retain null and contradictory findings.
Use question-appropriate established appraisal methods rather than invented authority.

## Challenge and gates

An independent challenge examines the strongest alternative explanation, missing
discriminating evidence, source/citation integrity and conclusion width. Track evidence
sufficiency, conclusion readiness and release readiness separately. A material gap
reopens targeted investigation under a new run/amendment. An unresolved answer is
a legitimate outcome. Do not broaden a conclusion because planned searching ended.

`challenge_intake.py` records such challenges as supplied assertions bound to the
challenged statements' current bases, after a separate import review. The engine
rejects a challenger label that matches a recorded reviewer, position-recorder or
appraiser label on the challenged statements, lists statements without a recorded
challenge and challenges with open material gaps, and marks challenges whose
statements changed afterwards as stale. It does not generate or adjudicate a
challenge, verify independence, or alter statements, reviews or work states.

`readiness_links.py` turns the same ledgers into twelve mechanical gates (plan,
searches, screening, reports, extraction, appraisal of cited results, statement
reviews, citations, challenges recorded and resolved, contexts, work), each with
exact open items, and hashes that gate ledger. `readiness_intake.py` records
supplied evidence-sufficiency and conclusion-readiness assertions bound to that
hash, with explicit reopening for a NOT_READY/INSUFFICIENT pair, and
`readiness_review.py` shows both. Closing every gate is necessary bookkeeping, not
sufficiency; the assertions are human, hash-bound and never promoted, so the
mechanical conclusion readiness stays NOT_READY.

## Four state layers

| State | Records |
|---|---|
| Research | Queries, search snapshots, screening, extraction, normalized evidence |
| Question | Open, narrowed, answered and unresolved questions/hypotheses |
| Decision | Sufficiency, confidence, relevance, assumptions and recommendation strength |
| Artifact | Research map, ledgers, evidence tables and release QA |

## Patent-information work

Define jurisdiction, date and intended question. Cross-check independent search
windows before deduplication/family grouping. Keep publications, applications,
families, priority chains and current legal status distinct. Map claim language to
the actual technical feature and inspect authoritative current records. A search
inventory, landscape, prior-art screen and legal FTO opinion are different outputs.
Do not assert a complete census when pagination, field coverage or count reconciliation
is unresolved. This release specifies the method but supplies no patent search backend.

## Persona consultation

Use a persona only as a labeled interpretive layer after neutral discovery and evidence
baseline construction. A persona's preferences are not search inclusion criteria.
New questions raised by consultation enter controlled reopening; consultation text
does not become an empirical evidence row.

## Validator boundary

The script checks selected required fields, search paging/count assertions, screening
arithmetic, duplicate reference IDs and release flags/citation/artifact linkage. It
does not authenticate a search receipt, inspect a paper, assess bias, establish legal
status, verify a storage location or certify scientific sufficiency. Its output must
not be represented as independent scientific validation.

## Optional identifier discovery transport

The separately invoked [bounded PubMed client](PUBMED_DISCOVERY.md) can transmit
an explicit preview-bound request to NCBI. Its native observations are detached
from protocol state. A later explicit conversion supplies unreviewed identifier
CSV to existing collection review; no search-plan amendment, identity resolution,
screening or evidence extraction is automatic. ESearch identifier counts are not
article-reading coverage or source/census authentication. Mock adapters keep their
existing offline semantics.

Selected metadata acquisition is separate again: `pubmed_metadata.py` consumes a
verified discovery plus explicit occurrence selection and retains EFetch MEDLINE
text. It reuses the strict native parser without changing its grammar. Exact-PMID
batch reconciliation is non-positional; CSV rows retain native record fields and
acquisition/discovery provenance. Unchanged collection review controls research
import. No metadata record automatically becomes screening, full text or evidence.

`result_passage_check.py` is a separate bounded local source reader. It validates
completed manual candidates and all explicit mappings before descriptor-relative
source access, compares declared hashes and exact UTF-8 byte quotations, and shows
selected text beside unchanged fields. It neither imports results nor claims
semantic support. The ordinary intake target/review remains separate; source-file
observations are not a new persistent protocol approval ledger.

`implementation_check.py` is a detached read-only diagnostic outside ENGINE_FILES.
It walks recorded hash declarations and compares selected local source bytes and
supplied publication manifests without executing that source or replaying artifacts.
Byte identity does not cover unhashed imports, authenticate provenance or verify inputs.

## Detached count crosswalk

`prisma_flow_template.py` calls the unchanged `prisma_audit.export_audit` and
serializes a native crosswalk, not an external template. Search classification is
supplied by input index; downstream counts retain whole-protocol scope. Unknown,
withheld and unsupported values stay blank; missing report data stays distinct
from an explicitly empty report ledger. It does not change engine state or bundle
verification. See [the crosswalk contract](PRISMA_FLOW_TEMPLATE.md).

## Detached status Markdown

`views_export.py status` renders only `research_status.status()` with fixed count
labels and quoted/fenced values, preserving every existing field, queue and pointer.
It derives no new joins or decisions, stays outside ENGINE_FILES and leaves existing
status/audit/handoff modules, adapter bindings and the bundle payload set unchanged.
The detached file and separate bounded receipt use exclusive output creation with
`lstat` rejection of existing entries. See [shareable status](SHAREABLE_VIEWS.md) for
Markdown escaping, unknown-versus-zero and partial-file boundaries.

## Detached accounting flow

`accounting_flow.py` serializes fixed vocabulary and counts from
`prisma_audit.export_audit()`. `views_export.py flow` uses the existing exclusive
writer and receipt preflight. Local aliases keep each partition in its own group;
two explicit unit bridges are dashed and detached study/result nodes stay detached.
This module is not an engine input; engine files and bundle payloads are unchanged.
See [accounting flow](ACCOUNTING_FLOW.md) for boundaries and rendering limitations.

## Detached records CSV

`records_csv.py` flattens only existing `export_audit()` ledgers and uses
`report_study_ids` for mapped report memberships. It stays outside ENGINE_FILES.
`views_export.py records` preflights the CSV and receipt before exclusive creation;
failed new writes are cleaned up on stable paths. Missing stages, display search
labels and separate report/result study lists remain explicit. See
[records CSV](RECORDS_CSV.md). No engine, adapter, fixture or bundle contract changes.
