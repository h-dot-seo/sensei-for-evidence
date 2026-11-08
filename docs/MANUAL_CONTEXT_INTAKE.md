# Record supplied guideline and development context

`context_intake.py` appends explicitly authored context assertions through a
separate exact-input import review. It supports the existing clinical-guideline
and drug-development domains, both before extraction and for exact existing result
IDs. It neither retrieves guidance nor generates clinical/regulatory assertions.

This operation deliberately imports **unassigned** contexts. Existing work-package
and synthesis links are unchanged. Later, a person can explicitly reference these
IDs in newly authored [source-review work](SOURCE_WORK_INTAKE.md) or
[evidence-review work](EVIDENCE_WORK_INTAKE.md), subject to the existing exact-link
validators. Assignment to an existing work package is not part of this operation.

## Synthetic eight-command rehearsal

Use an existing new `OUTPUT` directory outside the repository. All examples are
fictional, not actual clinical or drug-development guidance.

```sh
python context_intake.py template examples/source-context-protocol.json examples/context-references.json --candidate-output OUTPUT/context-draft.json
python context_intake.py target examples/source-context-protocol.json examples/manual-context-candidates.json --output OUTPUT/context-target.json
```

The template copies only caller-selected domain, scope and links. In this example,
the selected search has not executed. Context ID, source attribution, dates,
applicability, clinical/development assertions and even review_status stay blank.
Do not treat a blank as pending, unknown, reviewed or clinically appropriate.

Keep that unfinished draft separate. The completed fictional candidate contains
two explicitly supplied contexts. Copy `review_document` from the target to
`OUTPUT/context-review.json`. Retain the schema and hash, then explicitly fill
receipt_id, reviewer, reviewed_at, rationale and `decision: "import_contexts"`.
This authorizes recording the supplied context, not endorsing its applicability.

```sh
python context_intake.py assemble examples/source-context-protocol.json examples/manual-context-candidates.json OUTPUT/context-review.json --output OUTPUT/context-application.json
python context_intake.py verify examples/source-context-protocol.json OUTPUT/context-application.json --protocol-output OUTPUT/with-contexts.json
python prisma_audit.py OUTPUT/with-contexts.json --text
python research_status.py OUTPUT/with-contexts.json --text
python research_bundle.py create OUTPUT/with-contexts.json OUTPUT/context-research.zip
python research_bundle.py verify OUTPUT/context-research.zip
```

Two new context IDs append after the two originals and remain unassigned. The
new guideline context stays pending, with no reviewer invented. The development
context keeps its own fictional reviewed assertion and supplied reviewer/date.
The import reviewer never replaces that attribution. The earlier pending record,
excluded record, incomplete search and missing planned search remain unresolved.
No evidence, study, work package or scientific conclusion is added.

Repeated source text under distinct supplied context IDs does not establish
independent sources or agreement. No identity merging or clinical adjudication
occurs. Retain original input and detached application separately; ordinary
research bundles preserve the resulting protocol, not this import history.

## Explicit input contract

The reference document has exactly schema_version 1, domain, context_scope and
evidence_ids, plus source_refs only for source_review. The candidate document has
exactly schema_version 1 and a nonempty contexts list, at most 100 rows.

Each new context explicitly supplies the existing common fields: context_id,
title, issuer, locator, version, accessed_at, population_or_setting,
relevance_statement, applicability and limitations. It also supplies:

- domain: clinical_guideline or drug_development.
- recommendation_strength and evidence_certainty for clinical_guideline, or
  development_stage and regulatory_status for drug_development.
- context_scope and review_status, with no missing-field defaults at this intake.
- evidence_ids; source_refs only for source_review.
- reviewer and reviewed_at when review_status is reviewed. Pending rows may carry
  explicit attribution, but that does not change pending status. Any supplied
  reviewer must be nonblank and any supplied date must be real YYYY-MM-DD.

Source_review requires empty evidence_ids and nonempty unique exact typed source
references. Planned searches may be unexecuted, and enumerated records may be
unscreened or excluded. Their eligibility does not change. A search ID and record
ID with identical text are different references. Search membership does not imply
source-to-record or source-to-evidence inheritance.

Extracted_evidence requires nonempty unique exact existing normalized result IDs.
The existing engine's legacy record-ID fallback is allowed and explicitly labelled
in snapshots; no raw evidence_id is invented. Multiple supplied studies may be
referenced without implying identity, independence or clinical applicability.
Source-reference fields cannot accompany this scope.

All common and domain-specific text must be nonblank. When a value is unassessed,
that wording must be explicitly supplied by the author, not filled by the tool.
Unknown fields, derived linked_study_ids, work-assignment requests, duplicate or
existing context IDs, malformed dates and unresolved references are rejected.
Existing opaque metadata and legacy defaults are preserved without retrofitting
these stricter new-row rules to old contexts.

## Review targets and preservation

The target binds the complete original protocol, exact ordered candidate rows,
implementation bytes, output pointers and selected raw/normalized result snapshots.
Typed planned searches and record provenance are retained, along with mapped
report/source-catalog context where present. Catalog membership is not a selection
of supporting documents or proof of reading. URLs and locators stay inert text.

Only new context rows append. Original contexts, source ledgers, PRISMA count
partitions, results, experiments, appraisals, work/dependency states, planning,
completion and synthesis bases/positions remain unchanged and are checked. The
context ledger, pending-context list, unassigned-context list and separate PRISMA
source-context ledger can grow. That is recorded scope, not better evidence quality
or expanded work coverage. No old hash is renewed and no status is repaired.

Exact replay must succeed against the actual original input and recorded
implementation before a new protocol file is exported. An unrelated original
change, edited candidate, altered snapshots or inconsistent resealed application
fails replay. Consistently rewritten unsigned assertions may replay: this is not
proof of identity, date chronology, source authenticity or research conduct.

## Bounds and exclusions

Candidate/reference/review JSON is limited to 10 MB; protocol/application JSON to
50 MB. These and the 100-row cap are not hard CPU/memory ceilings. JSON is strict;
output is encoded/rendered before exclusive creation. Existing entries and observed
dangling links are refused. Writes are not atomic path-race/ancestor-alias defenses
and a failed write may leave a partial new file.

No guideline currency, recommendation strength, evidence certainty, applicability,
development stage or regulatory status is independently assessed. No source/model
call, scientific judgement, clinical recommendation or experimental procedure is
performed. Existing transition archives do not support this application kind.
Private supplied text is retained without redaction; keep real inputs outside the
public repository. Census stays NOT_ESTABLISHED and conclusions NOT_READY.

After import, [existing-work context assignment](WORK_CONTEXT_INTAKE.md) is a
separate reviewed step for explicit links. It exposes changed selected/dependent
source bases while preserving all stored planning/completion assertions.
