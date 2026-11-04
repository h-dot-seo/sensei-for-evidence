# Explicit intake of source-review work

`source_work_intake.py` lets a researcher append human-authored review tasks
without editing the existing `gaps` ledger by hand. Tasks can reference a declared
search before its receipt exists, an enumerated record before extraction, or
explicitly selected document/context metadata. They use the existing work engine,
source bindings and dependency checks, not a second project-management system.

The tool does not write research questions, deliverables, acceptance criteria,
dependencies or priorities. It admits only new **PLANNED source-review work**
after a separately supplied exact-target review. It cannot complete work, renew
old reviews, search a provider, read a paper or create scientific evidence.

## Start with explicitly selected references

The reference document has exactly `schema_version: 1` and a nonempty
`source_refs` list. Each reference uses the existing exact typed schema:
`{"kind":"planned_search","search_id":"..."}` or
`{"kind":"record","record_id":"..."}`. The first must name an existing
declared search; the second must name an enumerated record. Neither a report ID
nor an evidence ID can stand in for a record ID.

```sh
python source_work_intake.py template examples/source-work-protocol.json examples/source-work-references.json --candidate-output /outside/new-work-draft.json --text
```

The deliberately unfinished candidate copies only the supplied source references
and structural source-work fields. Task ID, question, deliverable, acceptance
criterion, dependencies and human proposal metadata remain null. The operator
must explicitly fill `depends_on`, including `[]` if no dependency is intended.
No absent dependency is silently interpreted as independence. The unfinished
candidate is not valid intake or a saved research protocol.

## Review and append a fictional example

The bundled candidate file contains two prewritten fictional proposals for
software testing: a missing-search receipt note and an excluded-record provenance
note. These are not a model-generated research plan or evidence that a real
person reviewed either source. Choose new output paths outside this checkout;
their parent directory must exist.

```sh
python source_work_intake.py target examples/source-work-protocol.json examples/source-work-candidates.json --output /outside/new-work-target.json --text
```

The target output contains a separate `review_document`. Copy that object into a
new local review JSON file. Its human fields remain null: supply a nonblank
`receipt_id`, `reviewer`, real `reviewed_at` date, `rationale`, and the explicit
decision `import_source_work` only after inspecting the exact proposals, source
references, dependencies and current protocol. Keep its target hash unchanged;
changed inputs require preparing and reviewing a new target.

```sh
python source_work_intake.py assemble examples/source-work-protocol.json examples/source-work-candidates.json /outside/filled-work-review.json --output /outside/new-work-application.json --text
python source_work_intake.py verify examples/source-work-protocol.json /outside/new-work-application.json --protocol-output /outside/new-work-protocol.json --text
python work_review.py /outside/new-work-protocol.json --work-package WP-EXCLUDED-RECORD-NOTE --include-prerequisites --brief
python research_status.py /outside/new-work-protocol.json --text
python prisma_audit.py /outside/new-work-protocol.json --text
python research_bundle.py create /outside/new-work-protocol.json /outside/new-work-bundle.zip
python research_bundle.py verify /outside/new-work-bundle.zip
```

The example grows two existing work packages to four. Both added tasks remain
PLANNED with their supplied dependencies. The missing secondary search remains
missing, r2 remains excluded, and no result row appears. A source-work task for an
excluded or unscreened record is permitted bookkeeping, not changed eligibility.
Search, record, report and evidence counts remain unchanged.

## Candidate contract

The candidate document has exactly integer `schema_version: 1` and `candidates`,
a nonempty list of at most 100 proposals. Each proposal has exactly:

- `work_package`: the full new source-review work object.
- `proposed_by`: nonblank supplied proposer label, not authenticated identity.
- `proposed_at`: real calendar date in YYYY-MM-DD form.
- `proposal_note`: nonblank human-supplied rationale or provenance note.

Each work object requires all of these fields:

- Explicit, nonblank `work_package_id`, unique across new and existing normalized
  work IDs. Existing legacy implicit IDs are not renamed or materialized.
- `work_type: "source_review"`, `evidence_ids: []`, `status: "PLANNED"`.
- Nonblank `question`, `deliverable` and `acceptance_criterion`, supplied by a human.
- Nonempty exact `source_refs` and an explicit `depends_on` list of unique IDs.

The only optional fields are nonblank `context`, nonempty unique `context_ids`
and nonempty unique `document_source_ids`. Existing engine rules validate exact
typed source-context overlap and document/report ownership. A planned-search
reference never inherits its records' contexts or documents. A record reference
does not certify a document version, reading, result applicability or scientific
support. See [source context links](SOURCE_CONTEXTS.md) and
[document-linked work](WORK_DOCUMENT_SOURCES.md).

Dependencies may refer to existing work or another explicit proposal in the same
batch, including one appearing later. Unknown IDs, duplicate dependencies, cycles
and self-dependencies fail. No prerequisite or priority is inferred from source
similarity, file order or a task title. Completed/in-progress tasks, result-linked
evidence work, completion fields, artifact locators, acceptance assertions and
extra work fields are not admitted through this intake.

## What is bound and preserved

The exact target binds the entire original protocol, complete ordered proposal
document, raw appended work objects and the new tasks' planning-source targets
derived by the unchanged engine. Selected source snapshots retain declared search
text or the existing record source context. Source hashes bind supplied metadata;
they do not prove a query ran, a file was read, a context applies or a reviewer is
qualified.

Assembly appends only the full supplied work objects to `gaps`, preserving the
existing raw prefix and every other protocol field, including version, search
receipts, screening, reports, evidence, conditions and old planning/completion
assertions. Valid CSV and mock-adapter provenance remain under their existing
integrity rules. The same full-protocol validation runs before and after append.
No prior status, acceptance assertion or human review is updated automatically.
The actual source/context/document references remain in the appended work object;
only the proposal metadata, separate human review and retained source snapshots
are detached. Existing engine bindings continue to use those persisted references.

The detached application retains the proposals, review assertion, target and
before/after accounting. Verification reconstructs the whole application from
the original protocol and retained assertions, rejecting unknown or inconsistent
fields even if a superficial hash is recomputed. These are unsigned editable
assertions, not authentication, chronology, globally unique receipt IDs or proof
of work execution. A consistently reauthored set of inputs can replay.

Keep the original protocol and detached application with the resulting protocol.
Ordinary research and collection bundles retain the enriched protocol but do not
automatically include this proposal/review record or original input. Use the
recorded implementation revision for replay after code changes. Existing work
source bindings still describe their established scope; a successful intake does
not broaden them to cover unrelated future edits.

## Local safety and privacy

Reference, candidate and review inputs are bounded at 10,000,000 bytes; protocols,
applications and serialized outputs at 50,000,000 bytes. Expansion can cause a
valid smaller input to exceed the output limit. All output files use exclusive
creation and are opened only after validation and serialization, including stdout
preflight. Existing files and symlinks are not overwritten; an operating-system
write failure can still leave a partial new file. Text output quotes supplied
values. No locator is opened and no external call occurs.
The final directory entry is inspected without following it before exclusive
creation, including on Windows. This is not protection against concurrent path
replacement or aliases in parent directories.

Real inputs may contain private project plans, source text and reviewer labels.
Nothing is redacted. Keep real files outside the public repository and review
access before sharing. This tool manages source-linked review work; it does not
generate biological execution procedures, clinical recommendations, causal
conclusions or a claim of exhaustive research.

For later tasks that explicitly cite existing results, use the separate
[evidence-work intake](EVIDENCE_WORK_INTAKE.md). This source-work contract remains
unchanged and does not accept evidence-review work or convert prior tasks.
