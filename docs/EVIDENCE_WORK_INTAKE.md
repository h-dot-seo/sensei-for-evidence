# Connect supplied results to reviewed work packages

`evidence_work_intake.py` appends explicitly authored result-linked review work
without editing the existing `gaps` ledger. It bridges supplied extraction to
research deliverables using the existing work engine, dependencies, context links
and planning/completion boundaries. It is not a second project-management system.

The tool does not generate a research question, experiment, deliverable, acceptance
criterion, dependency, priority or completion. It accepts only new **PLANNED
evidence_review** work after a separately supplied exact-target review. Existing
source-review work stays source-review work; result presence does not convert it
or establish complete extraction, independent support or clinical applicability.

## Select exact existing results

A reference document has exactly integer `schema_version: 1` and a nonempty list
of unique `evidence_ids`. Each must resolve to an existing normalized result ID:

```json
{"schema_version": 1, "evidence_ids": ["result-C-manual", "result-A-second"]}
```

The existing engine uses an explicit raw `evidence_id` when present. Legacy rows
without that field use their exact `record_id` as the normalized result ID. The
intake follows that established rule, retains the untouched raw row and records
`EXPLICIT_EVIDENCE_ID` or `LEGACY_RECORD_ID` in its selected snapshot. It never
fills a missing raw ID, guesses a publication identity or silently substitutes a
record/report/study ID for a different explicit result ID. Inspect the existing
workflow's normalized evidence list when selecting legacy IDs.

The template copies only explicit selected IDs and fixed evidence_review/PLANNED
structure. Work ID, question, deliverable, acceptance criterion, depends_on and
proposal metadata stay null. An empty dependency list must be supplied explicitly;
missing dependencies are not interpreted as independence. No human approval or
meaning is inferred from a source title or from the selected result text.

## Twelve-command synthetic extraction-to-work rehearsal

Use new output paths in an existing outside `OUTPUT` directory. All checked-in
inputs are fictional software examples, not real evidence or a research plan.
Begin with a separately reviewed result intake:

```sh
python result_intake.py target examples/report-study-inventory-reviews.json examples/manual-result-candidates.json --output OUTPUT/result-target.json
```

Copy its `review_document` to `OUTPUT/result-review.json`, retaining schema and
target hash. Explicitly complete receipt_id, reviewer, reviewed_at (YYYY-MM-DD),
rationale and `decision: "import_results"`. Use fictional human labels only for
this rehearsal. Real use requires the actual corresponding source/result review.

```sh
python result_intake.py assemble examples/report-study-inventory-reviews.json examples/manual-result-candidates.json OUTPUT/result-review.json --output OUTPUT/result-application.json
python result_intake.py verify examples/report-study-inventory-reviews.json OUTPUT/result-application.json --protocol-output OUTPUT/with-results.json
python evidence_work_intake.py template OUTPUT/with-results.json examples/evidence-work-references.json --candidate-output OUTPUT/work-draft.json
python evidence_work_intake.py target OUTPUT/with-results.json examples/evidence-work-candidates.json --output OUTPUT/work-target.json
```

The draft is deliberately unfinished. The separate completed fixture proposes a
traceability note and a limitations note. It does not run an experiment or invent
an evidence row. Copy only this new target's `review_document` into
`OUTPUT/work-review.json`, keep its new hash, and fill receipt_id, reviewer,
reviewed_at, rationale and `decision: "import_evidence_work"`. This is a separate
review of task meaning, result links and dependencies, not reuse of result approval.

```sh
python evidence_work_intake.py assemble OUTPUT/with-results.json examples/evidence-work-candidates.json OUTPUT/work-review.json --output OUTPUT/work-application.json
python evidence_work_intake.py verify OUTPUT/with-results.json OUTPUT/work-application.json --protocol-output OUTPUT/with-work.json
python work_review.py OUTPUT/with-work.json --work-package WP-RESULT-LIMITS-NOTE --include-prerequisites --brief
python research_status.py OUTPUT/with-work.json --text
python prisma_audit.py OUTPUT/with-work.json --text
python research_bundle.py create OUTPUT/with-work.json OUTPUT/research.zip
python research_bundle.py verify OUTPUT/research.zip
```

The result intake first increases result rows from two to four. The later work
intake grows two work packages to four while keeping all four results, declared
memberships and record/report flow unchanged. Both new tasks remain PLANNED.
WP-RESULT-TRACE-NOTE explicitly depends on the existing source-review task
WP-MEMBERSHIP-SOURCES; WP-RESULT-LIMITS-NOTE explicitly depends on that new note.
Their blocked state follows supplied prerequisites; nothing is marked complete or
executed. Multiple selected results can belong to one study and are not counted
as independent evidence. The audit lists explicit work/result/source links, not
proof the proposed deliverables exist or satisfy acceptance criteria.

Already-extracted inputs can start directly with the work template/target steps;
`examples/result-source-current.json` is a compatible standalone fictional base.
Do not erase actual extraction or provenance to imitate a fixture.

## Candidate and dependency contract

Candidates use exactly schema_version and a nonempty ordered candidates list,
at most 100 entries. Each entry has work_package, proposed_by, proposed_at and
proposal_note. All proposal text is nonblank; dates are real YYYY-MM-DD dates.
Each work object requires:

- Explicit work_package_id, unique across candidates and existing normalized IDs.
- work_type `evidence_review` and status `PLANNED`.
- Nonblank human question, deliverable and acceptance_criterion.
- Nonempty unique existing evidence_ids, and an explicit unique depends_on list.

Optional fields are nonblank context and nonempty unique context_ids. Context IDs
must satisfy the existing evidence-scoped overlap rules. A linked clinical
guideline or development context is a supplied assertion, not a recommendation,
verified applicability or clinical acceptance. No context is invented or selected.

Dependencies can reference existing source/evidence work or another supplied
proposal, including a later row in the same batch. Unknown IDs, self-dependencies,
duplicates and cycles are rejected. Candidate order is retained; it does not
choose dependency order, priority or scientific independence. Existing implicit
work IDs are recognized for collision checks but never materialized into old rows.

Source_refs and document_source_ids are rejected on evidence work, as the existing
engine requires. Use separate [source-review work](SOURCE_WORK_INTAKE.md) for those
inputs. A human can explicitly depend on a document-scoped source-review task;
its existing direct-dependency document binding remains visible. This is not an
automatic transfer of document selection or a recursive source-approval chain.
Completion/artifact fields, acceptance assertions, priority ranks, new planning
assertions, non-PLANNED statuses and unknown fields are not admitted here.

## Preservation and replay

The exact target binds the whole original protocol, ordered candidate document,
appended raw work snapshots/pointers, selected raw and normalized result snapshots,
identity origins, mapped record provenance and new planning targets. Appended-work
pointers refer to the candidate protocol; selected-result pointers refer to the
original protocol. Even an unrelated input change invalidates the review. There is no automatic rebase.

Assembly appends only full supplied work objects to gaps. Every prior raw field
and old work prefix stays unchanged, including source catalogs, reviews, results,
conditions, CSV/mock provenance, version and opaque metadata. Existing normalized
work and planning/completion targets/assertions are checked for equality. New
work uses the existing validation and dependency logic, not a weaker path.

Work/result/context links and dependencies persist in the candidate protocol.
Proposal metadata, separate import review and selected snapshots remain detached.
The receipt records before/after work counts, execution order and research flows;
execution order is a dependency ordering, not proof tasks ran. Full replay rebuilds
the entire application rather than trusting a recalculated checksum. Unsigned,
consistently reauthored assertions may replay; identity and chronology are not
verified. Source associations from older extraction receipts are not automatically
imported or treated as current approval by this work intake.

Keep the actual original, detached application and recorded implementation.
Ordinary research/native archives retain the resulting protocol, not this review
history. Existing report/extraction transition archives do not support this kind.
Editing existing work, progress updates, completion, project-wide replanning and
clinical/scientific decisions remain outside this append operation.

## Local safety and limits

Reference/candidate/review inputs are limited to 10 MB; protocols/applications to
50 MB, with at most 100 proposals. Output expansion can exceed limits even when an
input fits. These are not hard CPU/memory ceilings. Strict JSON, whole-protocol
validation and exact schema checks reject coercion, malformed values and stale
inputs. All output is serialized before exclusive creation. Existing entries,
including observed dangling links, are refused; this is not an atomic path-race
or parent-alias defense, and a failed write can leave a partial new file.

No source/artifact is opened, fetched or executed. Supplied text is not redacted
or transmitted; keep actual private work and generated files outside this public
repository. Hashes do not establish source truth, reading, causal inference,
independent studies, exhaustive research or satisfaction of acceptance criteria.
Census remains NOT_ESTABLISHED and conclusions NOT_READY.
