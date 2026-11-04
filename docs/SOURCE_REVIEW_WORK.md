# Work packages before extraction

A manual receipt candidate has no accepted extracted result rows. Previously,
every work package required an evidence ID, so an operator could not record
receipt, screening or extraction-review deliverables without inventing evidence.
Explicit `work_type: source_review` closes this gap **inside the existing work
package model**. There is no second task engine and no generated research design.

```sh
python work_review.py examples/source-work-protocol.json --work-package WP-RECEIPT-REVIEW --text
python work_review.py examples/source-work-protocol.json --work-package WP-EXTRACTION-REVIEW --text
python review_handoff.py examples/source-work-protocol.json --text
python research_status.py examples/source-work-protocol.json --text
python research_bundle.py create examples/source-work-protocol.json ../fictional-source-work.zip
python research_bundle.py verify ../fictional-source-work.zip
```

Use a new output path outside the repository. The fixture is the synthetic manual
receipt candidate plus two supplied work packages. It has no extracted evidence,
no accepted receipt reviews, an interrupted/overlapping primary receipt and a
missing secondary search. The extraction-review WP depends on the receipt-review
WP. Both deliverables and acceptance criteria are fictional human-supplied text.

## Input contract

All work still lives under `gaps` with question, deliverable, acceptance_criterion,
evidence_ids, optional explicit work_package_id, depends_on and status.

- Omitted work_type means the legacy evidence_review behavior. Explicit
  evidence_review is also accepted. It requires at least one known extracted
  result ID and cannot contain source_refs.
- Explicit source_review requires evidence_ids: [] and nonempty source_refs.
  It cannot also claim linked extracted evidence. Each ref has exactly either
  `{ "kind": "planned_search", "search_id": "search-primary" }` or
  `{ "kind": "record", "record_id": "r1" }`.
- A planned_search ref must name a declared search-plan entry, even if no receipt
  has been supplied. An optional observed search ID without a declared plan is
  not sufficient because it can be absent or ambiguous.
- A record ref must name an enumerated search record. It can still be unscreened
  or excluded; referencing it never changes its eligibility. Evidence IDs, report
  IDs and arbitrary strings cannot stand in for record IDs.
- Duplicate refs, unknown kinds/IDs, extra ref fields and mixed evidence/source
  work are rejected. Questions and completion criteria still must be supplied;
  this feature does not write them or infer scientific work from a record.

Source-only work can attach an explicitly source-scoped guideline/development
context through `context_ids` when both share an exact typed source reference.
See [pre-extraction context links](SOURCE_CONTEXTS.md). Legacy evidence contexts
still require shared extracted evidence and cannot attach to source-only work.
Use a subsequent evidence-review WP for evidence-level scientific/applicability
review. Multiple source refs are not evidence rows or studies.

## A concrete manual journey

1. Use receipt_intake to check a filled synthetic fixture and save a new unreviewed
   candidate, preserving the base and original inputs.
2. Add a source-review WP for named planned searches. Its deliverable might be a
   source-linked receipt review note that explicitly retains unresolved overlap,
   interruption or missing-source limitations. This is bookkeeping, not approval.
3. Add a dependent source-review WP for an enumerated record. A human supplies its
   extraction-review worksheet or an explicit unresolved-source note. Do not add
   invented evidence just to satisfy a task field.
4. Independently use the existing receipt/extraction review workflow when a human
   actually reviews supplied candidates. Source-work completion does not call or
   substitute for that workflow. An interrupted receipt cannot be accepted merely
   because its review-note task is complete.
5. Once genuine supplied result IDs exist in the synthetic workflow, an ordinary
   evidence-review WP can cite those IDs and depend on the source-review work.
   Source-review packets display existing result IDs as an inventory only; they
   do not silently convert those results into their linked evidence.

The E2E regression exercises manual receipt with no evidence, existing explicit
mock receipt/extraction review, then mixed source/evidence work dependencies. No
actual document is read, result extracted or scientific question decided by it.

## Packet, planning and output scope

`work_review.py` shows work_type, source_review_inputs and separate
source_input_counts. A planned source includes its declared-plan status and
observed search indices; a missing receipt stays explicit. A record includes all
supplied search occurrences, optional screening/report data and existing result
IDs. Missing screening or reports stay null. Related search accounting retains
page/interruption warnings. Result scope counts remain zero for source-only work.
The handoff exposes the same source inputs. Bundle work CSV includes work_type and
source_refs; the research JSON preserves the explicit work entries.

Existing planning hashes bind source refs and the shared question/criteria/search/
screening/report scope. For a record-source WP, a structural inventory of
record_id plus sorted existing result IDs is additionally bound. Adding/removing
those IDs stales affected source-work ranks and their direct dependents. This is
inventory consistency, not scientific evidence linkage. Changing only result
content, appraisal or experimental detail is not part of this source-only inventory
binding; use evidence-review work for that scope. Planned-search-only work does
not bind a result inventory. Progress fields remain excluded as before. Legacy
work without new fields keeps its original planning hashes.

The same dependency-cycle and completion guards apply to both work types. COMPLETE
requires a supplied artifact_locator, acceptance_verified: true and completed
prerequisites. These are human assertions; the tool does not open artifacts,
evaluate acceptance criteria or perform the work. Completing a source review can
unblock another recorded WP while search receipts remain unreviewed, planned
sources remain missing, and scientific readiness remains NOT_READY. It must never
be read as an accepted search, exhaustive extraction, guideline approval or census.
No review flags, source facts, evidence rows or priorities are changed automatically.

For the reverse path from a planned search, record, result or indirectly linked
report to its supplied work and artifact, use `prisma_audit.py` on the same
protocol. See [work and deliverable traceability](PRISMA_AUDIT.md#work-and-deliverable-traceability).
It lists explicit links without propagating source-work completion to records or
results, and never opens or verifies artifact locators.

For explicitly authorized local byte checks, [local artifact review](LOCAL_ARTIFACT_REVIEW.md)
accepts a separate manifest/root and checks bounded regular-file size and SHA-256.
This POSIX-only opt-in never fetches locators or changes work/acceptance assertions.

## Explicit document-version scope

Source-review work may optionally select `document_source_ids` that share an
exact record reference with their report. See [document-linked work](WORK_DOCUMENT_SOURCES.md)
for source-catalog binding, direct-dependent staleness and portable review views.
Omitting the field retains the original record/search scope and semantic hashes;
no document version, reading or acceptance is implicitly bound or verified.
