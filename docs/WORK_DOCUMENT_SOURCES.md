# Explicit document sources for source-review work

A record-linked work package does not automatically track every document version
associated with that record. Optional `document_source_ids` makes a person's
selected report-source declarations part of the work's planning/completion basis.
Changing that context can mark supplied assertions stale without changing the
recorded task status or accepting/rejecting its work.

This is source and observation bookkeeping, not document reading, scientific
assessment or experimental design. Only fictional inputs are checked in. Keep
actual/private source material and generated artifacts outside this repository.

## Reproduce the fictional work packet

```sh
python work_review.py examples/work-document-sources.json --work-package WP-DOCUMENTS --text
python work_review.py examples/work-document-sources.json --work-package WP-DIRECT --include-prerequisites --brief
python review_handoff.py examples/work-document-sources.json --text
python research_bundle.py create examples/work-document-sources.json /outside/new-document-work-bundle.zip
python research_bundle.py verify /outside/new-document-work-bundle.zip
```

Use a new output path in an existing directory. The example has four supplied
COMPLETE assertions with matching completion context:

- WP-DOCUMENTS explicitly selects `source-main` for record one.
- WP-DIRECT directly depends on WP-DOCUMENTS and binds that document context.
- WP-TRANSITIVE depends on WP-DIRECT, not directly on WP-DOCUMENTS.
- WP-LEGACY has no selected document sources and retains the older record scope.

Copy the protocol to a separate working file and change only source-main's
`document_version`. Then compare the original and changed file with
`python compare_runs.py ORIGINAL.json CHANGED.json --text`.
WP-DOCUMENTS and WP-DIRECT receive stale planning/completion source labels.
WP-TRANSITIVE and WP-LEGACY retain their original basis hashes. All four recorded
statuses stay COMPLETE and dependencies stay as supplied. WP-TRANSITIVE still
shows its direct prerequisite's stale completion label; its own matching hash
is not a recursive acceptance certificate.

The example's COMPLETE and acceptance fields are fictional human assertions,
not claims this tool read the documents, inspected an artifact or verified a
completion criterion. A null digest in the surrounding catalog remains unbound.

## Optional input contract

Add the field only to an explicit source-review work package under `gaps`:

```json
{
  "work_package_id": "WP-DOCUMENTS",
  "work_type": "source_review",
  "evidence_ids": [],
  "source_refs": [{"kind": "record", "record_id": "record-one"}],
  "document_source_ids": ["source-main"],
  "question": "Which supplied document version was used for this source note?",
  "deliverable": "A source-linked human review note.",
  "acceptance_criterion": "A person records the supplied context and unresolved limitations."
}
```

The field must be a nonempty list of unique, nonblank literal IDs. Each ID must
name a `report_sources` descriptor, and that descriptor's report must contain at
least one exact record reference explicitly listed in this work's `source_refs`.
One shared record is sufficient; no search-to-record or similar-title inheritance
is inferred. Matching record IDs are retained in the report's declared order.

Planned-search-only work cannot select a report document through an inferred
relationship. Evidence-review work cannot use this field. Unknown IDs, wrong-report
links, extra reference fields, empty/null lists and duplicates fail validation.
Source IDs and record IDs are not trimmed or case-folded. Equal digests do not
merge descriptors or establish one study. Existing requirements for question,
deliverable, acceptance criterion, empty evidence IDs and valid source refs remain.

A report's pending/unavailable retrieval or a null document digest does not prevent
recording a source-review task; those supplied states remain visible and unverified.
The command never marks a report retrieved or included. Removing a selected source
makes its explicit current link invalid rather than silently deleting the work
input. Preserve prior snapshots and deliberately revise the working protocol.

## What changes the binding

Each opted-in work basis has a separate `document_source_context` containing:

- Versioned scope, the selected descriptors and exact matched record IDs.
- Each descriptor's report ID and existing report source-basis hash.
- No positional navigation pointers and no invented document-byte observations.

The existing report source hash binds **the complete ordered same-report source
catalog**, retrieval, report locator, criteria and mapped search/CSV provenance.
Thus a same-report unselected descriptor's addition, removal, version/digest edit
or catalog reordering can stale the opted-in work, even if its selected descriptor
is unchanged. Selected IDs identify requested work inputs; the surrounding catalog
is context, not a claim that every document was read or a preferred version chosen.

A source-catalog change on an unrelated report does not affect this new document
binding. Existing broader planning scope still binds shared search/screening/report
rows, so changes to those may already affect more work under legacy rules. The new
feature does not narrow or silently replace that older scope.

Report/reviewer opinions, inventory descriptions and local byte-check results are
not imported into this document binding as approvals. Changing human opinions
alone does not renew or stale the report-source hash. Existing work source-result
inventory and evidence/appraisal/condition scopes keep their previous semantics.

Direct dependencies that explicitly select documents are retained in a separate
`direct_dependency_document_sources` basis field. Only direct dependencies are
included. No new dependency is inferred and no transitive document cascade is
introduced. The additional fields do not overwrite arbitrary metadata in the
existing `work_scope`.

Completion already reuses the planning work/source basis plus artifact locator,
so it inherits these source changes. A changed source label does not reopen work,
change blocked state, renew hashes, validate acceptance criteria, authenticate a
reviewer or establish scientific readiness. Missing/stale planning groups continue
to follow the existing source-match rules, not newly generated priorities.

## Review views, comparison and portable exports

Detailed packets, compact navigation and handoff retain optional own/direct
prerequisite document contexts with the nonverification boundary. They expose
exact supplied descriptors and links, not a new pending-work queue. Existing
source/evidence counts and PRISMA accounting are unchanged.

Completion comparison adds conditional before/after document contexts and a
literal changed flag. It retains added/removed work's available contexts too.
Changes are not causal attribution or historical acceptance reasons. A report
source hash can change when only an unselected catalog entry changes; inspect
the existing report-source comparison for those catalog details.

If any work opts in, bundle `work-packages.csv` appends `document_source_ids`,
`document_source_context` and `direct_dependency_document_sources`. Structured
values are JSON in CSV cells with the shared spreadsheet escaping rules. An empty
own-context cell means that work has no own document selection; dependency context
can still be present. Existing seven-file bundles remain unchanged in structure
and do not include source document bytes.

If no work opts in, no document-binding packet/basis fields or CSV columns are
added. Legacy semantic planning/completion hashes, ordinary projections and CSV
payloads remain identical, even where `report_sources` already exists. The new
helper and edited implementation files do change engine fingerprints. Older
engine-bound artifacts require their recorded code, including detached report
decision records and previous research bundles.

`document_source_ids` is a new reserved field, not an automatic migration of
legacy work. Deliberately adding it changes scope and requires honest new planning
or completion assertions when appropriate. Never copy a new hash just to remove
a stale label. A matching source binding is not evidence of reading, verified
bytes, source authenticity, eligibility, independent studies or completed research.
