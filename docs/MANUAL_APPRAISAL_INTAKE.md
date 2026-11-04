# Record supplied appraisals without generating judgements

`appraisal_intake.py` appends human-authored appraisal records through a separate
exact-input import review. It connects supplied methods and domain judgements to
existing extracted result IDs and preserves the original records, source context
and downstream review changes. It does not run an appraisal tool, select a method,
write a rubric, score quality, adjudicate disagreement or assess clinical use.

Each appraisal remains scoped to its explicitly listed result IDs within **one
supplied study ID**. That identifier is not verified study identity or proof of
independent evidence. An appraisal of one result does not automatically cover its
uncited sibling results, other reports or an entire study.

## Blank drafting and explicit candidate records

A reference document has exactly integer schema_version: 1 and a nonempty unique
list of evidence_ids. IDs follow the existing engine: an explicit raw evidence_id
is used when present; otherwise the exact legacy record_id is the normalized
result ID. Record/report/study IDs cannot substitute for a different explicit
result ID. The template exposes the supplied study ID but never materializes a
missing raw evidence ID.

The template copies only the selected IDs and blank record structure. Method,
version, method locator, reviewer, assessment date, limitations, appraisal ID and
all domain fields stay null. Even domain names and judgement choices are blank.
No blank is interpreted as low risk, poor quality, unknown quality or human review.

The candidate document has exactly schema_version and a nonempty appraisals list,
with at most 100 rows. Each new row has exactly:

- appraisal_id, method, method_version, method_locator, reviewer, assessed_at,
  limitations, evidence_ids and domains.
- All text is explicitly supplied and nonblank; assessed_at is a real YYYY-MM-DD.
- Existing normalized evidence_ids are nonempty and unique, and all belong to one
  supplied study ID. Separate rows in one batch can concern different study IDs.
- domains contains 1–100 objects, each with exactly name, judgement, rationale and
  source_locator. Domain names are unique within that record.

No judgement vocabulary, risk category, scoring formula or method suitability is
imposed or inferred. Domain and method locators are literal unverified strings.
New IDs must be unique across the existing ledger and the batch. Existing records
cannot be replaced or merged. Identical methods, reviewers or domain names across
different records do not establish duplicate assessments, consensus or independent
reviewers. Conflicting positions remain separately inspectable.

## Ten-command synthetic appraisal-to-review rehearsal

Use a new existing `OUTPUT` directory outside this repository. All fixture
judgements, methods, source locators and reviewer labels are fictional software
data, not actual assessments or a validated appraisal instrument.

```sh
python appraisal_intake.py template examples/synthesis-review.json examples/appraisal-references.json --candidate-output OUTPUT/appraisal-draft.json
python appraisal_intake.py target examples/synthesis-review.json examples/manual-appraisal-candidates.json --output OUTPUT/appraisal-target.json
```

Keep the unfinished draft separate. The completed fictional candidate supplies one
different position on result e1 and one unresolved position on e2. Copy the
target's review_document to `OUTPUT/appraisal-review.json`, retain schema and hash,
and explicitly fill receipt_id, reviewer, reviewed_at, rationale and
`decision: "import_appraisals"`. This separate review records the supplied rows and
links; it is not endorsement of their methods or judgements. Use fictional labels
only for this rehearsal. Real data requires the actual corresponding human review.

```sh
python appraisal_intake.py assemble examples/synthesis-review.json examples/manual-appraisal-candidates.json OUTPUT/appraisal-review.json --output OUTPUT/appraisal-application.json
python appraisal_intake.py verify examples/synthesis-review.json OUTPUT/appraisal-application.json --protocol-output OUTPUT/with-appraisals.json
python work_review.py OUTPUT/with-appraisals.json --work-package WP-MECHANISM --text
python synthesis_review.py OUTPUT/with-appraisals.json --text
python research_status.py OUTPUT/with-appraisals.json --text
python prisma_audit.py OUTPUT/with-appraisals.json --text
python research_bundle.py create OUTPUT/with-appraisals.json OUTPUT/research.zip
python research_bundle.py verify OUTPUT/research.zip
```

The ledger grows from one to three supplied appraisals. The prior e1 assessment
and the different new e1 position both remain. Result e2 gains a recorded appraisal,
but e3 remains without one. All three result rows, report counts, work packages,
source data and stored synthesis assertions remain unchanged. Fewer rows without
recorded appraisal indicates only recorded coverage, not improved evidence quality
or sufficient assessment.

The existing reviewed statement citing e1 becomes STALE_SOURCE because its bound
appraisal context changed. Its stored reviewer and hash are not updated, and
support remains NOT_ASSESSED. The pending e2 statement stays pending. Existing
work planning/completion target hashes can also change; this fixture does not
invent ranks or completion. Census remains NOT_ESTABLISHED and conclusions NOT_READY.

## Exact targets and downstream changes

The import target binds the whole original protocol, ordered candidate records,
appended output pointers, selected raw and normalized result snapshots, exact
record provenance and mapped report/source-catalog context. Raw/normalized ID
origins are exposed. Mapped catalogs are context, **not a selected list of files
that were read or support an appraisal**. Domain locators are not resolved against
catalogs, fetched or validated. Selected snapshots remain in the detached record.

The target also shows before/after result IDs lacking recorded appraisal and
mechanical planning, completion and synthesis source-status changes. A changed
basis is shown even when both statuses remain pending, unfinished or already
stale. These are consistency cues, not new review judgements or priorities.

Assembly appends only supplied appraisal rows. Every old raw field and appraisal
prefix is preserved, including existing opaque appraisal metadata, search/native
provenance, screening/report decisions, results, contexts, experiments, work,
planning decisions, synthesis statements and completion hashes. Existing normalized
appraisal records and research flows remain unchanged. The existing engine derives
new links and source-status cues. CSV and mock provenance remain under their normal
integrity validation; no receipt is cleared or reconstructed to bypass it.

A previously current planning assertion can become stale without changing its
stored rank. A source-bound COMPLETE work assertion can become stale while staying
COMPLETE and continuing to satisfy the existing dependency rule. Unlinked work
keeps its previous basis. No source review, prior appraisal, statement, completion
or priority is renewed or silently corrected. Missing recorded appraisal is not a
judgement that a study is poor quality; present appraisal is not proof of adequacy.

## Replay, preservation and limits

Verification regenerates the entire application against its actual original and
recorded implementation before exporting a new candidate. Unrelated original
changes, candidate changes and inconsistent resealed output/snapshot/status-cue
changes fail replay. This is not authentication: consistently reauthored unsigned
reviewer assertions can replay. Dates are checked for calendar syntax, not actual
assessment chronology, and reviewer identity or independence is not verified.

Keep the original, detached application and recorded implementation. Persisted
appraisal rows retain their own method/domain/reviewer metadata, but the separate
import review and selected snapshots do not become a new current-approval ledger.
Later source/result changes do not automatically label these appraisal rows current
or stale. Their continued scientific applicability requires separate human review;
this intake does not establish current appraisal validity.
Ordinary research archives preserve the resulting rows, not this detached import
history. Existing report, extraction and work-transition archives do not support
this application kind. Appraisal edits, removals, consensus, scientific scoring
and method-specific validation remain outside this append operation.

Reference/candidate/review inputs are limited to 10 MB; protocols/applications to
50 MB. Limits of 100 appraisals and 100 domains per new row are enforced, not hard
CPU/memory ceilings. Strict JSON, exact new-row schemas and whole-protocol validation
apply. All output is prepared before exclusive creation; existing entries and
observed dangling links are refused. This is not an atomic path-race or ancestor
alias defense, and failed writes may leave a partial new file.

No external call, model call, source/artifact reading or experimental procedure is
performed. Supplied private text is retained without redaction. Keep real inputs
and generated records outside this public repository. Neither imported appraisals
nor matching hashes establish quality, complete research, clinical applicability,
scientific acceptance or development readiness.

For later snapshots, [detached appraisal context comparison](APPRAISAL_SOURCE_REVIEW.md)
shows literal appraisal/result/source changes after exact historical replay. It
adds no current-applicability label to stored appraisals and never renews review.
