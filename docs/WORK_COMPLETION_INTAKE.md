# Record reviewed work completion without editing the research ledger

`work_completion_intake.py` records one explicitly supplied completion assertion
for an existing unfinished work package. It connects a supplied deliverable
locator and acceptance assertion to the exact work/source scope reviewed. It does
not perform the work, inspect the artifact, assess the criterion or approve the
science. A task can be recorded COMPLETE while census remains NOT_ESTABLISHED
and conclusions NOT_READY.

This narrow path handles source-review and evidence-review work already present
in `gaps`, including work created by the separate reviewed intake tools. It does
not create work, change questions or dependencies, rank tasks, start work,
reopen completed work or renew a stale/unbound completion. Only PLANNED and
IN_PROGRESS work can be selected; an omitted raw status follows the existing
engine's PLANNED default.

## Explicit completion and a separate review

The candidate has exactly these fields:

- Integer schema_version: 1 and one exact existing normalized work_package_id.
- A nonblank literal artifact_locator. It is not followed, read or executed.
- Exact boolean acceptance_verified: true, explicitly supplied by the human.
- Nonblank completed_by and completion_note; completed_at is a real YYYY-MM-DD.

The template fills only schema_version and the selected ID. Locator, acceptance,
completer, date and note remain null. A template is not a completion claim and
cannot be assembled. Selecting work never infers that its deliverable exists or
that its criterion was met. Existing unfinished locator/acceptance assertions are
shown in the target beside their proposed replacements.

The target preview binds the whole original protocol, candidate and recorded
implementation. It shows the selected raw and normalized before/after work,
raw input/output pointers, planning source basis, intended completion basis,
direct prerequisite completion-source cues and derived blocking changes. The
review document has schema_version and target_sha256 filled; receipt_id, decision,
reviewer, reviewed_at and rationale remain null. A human must supply all fields
and explicitly choose `record_supplied_completion`. Preparing a target does not
mutate the original protocol or record completion.

After this exact-target review, assembly records only four selected raw fields:
status COMPLETE, supplied artifact_locator, supplied true acceptance_verified and
the reviewed current completion_basis_sha256. The hash mechanically combines the
existing planning work/source basis and literal locator, using the same engine as
[completion binding](COMPLETION_BINDING.md). Recording the hash does not independently
verify acceptance. A stale review cannot be rebased silently onto changed input.

## Fifteen-command synthetic work-to-deliverable rehearsal

Use a new existing `OUTPUT` directory outside this repository. All checked-in
inputs and completer labels are fictional software examples, not actual finished
research. First add the existing supplied result-linked review tasks:

```sh
python evidence_work_intake.py target examples/result-source-current.json examples/evidence-work-candidates.json --output OUTPUT/work-target.json
```

Copy that target's review_document to `OUTPUT/work-review.json`, retain its schema
and hash, and explicitly fill receipt_id, reviewer, reviewed_at, rationale and
`decision: "import_evidence_work"`. Fictional reviewer labels are only for this
rehearsal; real work requires the actual corresponding review.

```sh
python evidence_work_intake.py assemble examples/result-source-current.json examples/evidence-work-candidates.json OUTPUT/work-review.json --output OUTPUT/work-application.json
python evidence_work_intake.py verify examples/result-source-current.json OUTPUT/work-application.json --protocol-output OUTPUT/with-work.json
python work_completion_intake.py template OUTPUT/with-work.json --work-package WP-MEMBERSHIP-SOURCES --candidate-output OUTPUT/completion-draft.json
python work_completion_intake.py target OUTPUT/with-work.json examples/source-work-completion.json --output OUTPUT/source-target.json
```

The unfinished draft remains separate from the completed fictional candidate.
Copy the new source target's review_document to `OUTPUT/source-review.json`, keep
its own hash and fill all human fields with `decision: "record_supplied_completion"`.
This reviews the note's recorded completion, not search/extraction completeness.

```sh
python work_completion_intake.py assemble OUTPUT/with-work.json examples/source-work-completion.json OUTPUT/source-review.json --output OUTPUT/source-application.json
python work_completion_intake.py verify OUTPUT/with-work.json OUTPUT/source-application.json --protocol-output OUTPUT/source-complete.json
python work_completion_intake.py target OUTPUT/source-complete.json examples/evidence-work-completion.json --output OUTPUT/evidence-target.json
```

Copy this third target's review_document to `OUTPUT/evidence-review.json`, retain
its own hash and again supply all fields with `record_supplied_completion`. Do not
reuse either earlier review. This is a separate recorded acceptance of the
result-linked traceability note.

```sh
python work_completion_intake.py assemble OUTPUT/source-complete.json examples/evidence-work-completion.json OUTPUT/evidence-review.json --output OUTPUT/evidence-application.json
python work_completion_intake.py verify OUTPUT/source-complete.json OUTPUT/evidence-application.json --protocol-output OUTPUT/evidence-complete.json
python work_review.py OUTPUT/evidence-complete.json --work-package WP-RESULT-LIMITS-NOTE --include-prerequisites --brief
python research_status.py OUTPUT/evidence-complete.json --text
python prisma_audit.py OUTPUT/evidence-complete.json --text
python research_bundle.py create OUTPUT/evidence-complete.json OUTPUT/research.zip
python research_bundle.py verify OUTPUT/research.zip
```

The work intake grows two tasks to four with four existing result rows unchanged.
The first completion marks only WP-MEMBERSHIP-SOURCES COMPLETE and mechanically
unblocks WP-RESULT-TRACE-NOTE. The second completes that note and unblocks
WP-RESULT-LIMITS-NOTE, which remains PLANNED. WP-RESULT-LINKS also remains PLANNED.
Two newly recorded completion bindings match current metadata, but no artifact
bytes are checked. All research flows, extracted results, source descriptors,
review records and planning bases remain unchanged throughout the two completion
steps. Work status does not accept a source, eliminate a missing membership,
certify extraction, resolve a clinical guideline or establish independent support.

Trying to complete the traceability note before its prerequisite is COMPLETE
fails. The original engine's dependency rule is retained: an already COMPLETE
prerequisite may still have a stale or unbound completion assertion. Such cues
remain visible; this tool neither renews them nor invents a stricter hidden gate.
Inspect them before making a human decision. Dependency completion cues are direct
links, not recursive acceptance certificates.

## Preservation, replay and later changes

Only the selected four progress fields may change. All other raw fields and rows,
including opaque metadata, provenance, source catalogs, review assertions, result
links, work meanings and explicit/implicit IDs are preserved. An implicit legacy
ID such as WP-001 resolves positionally through the existing engine but is not
inserted into the raw row. The target labels this LEGACY_POSITIONAL_ID separately
from EXPLICIT_WORK_PACKAGE_ID. Planning assertions and bases remain unchanged;
other work's completion assertions and bases remain unchanged. Derived blocked_by
lists can change when the selected prerequisite becomes COMPLETE; the target and
receipt show each such change without editing dependent raw rows.

`verify` recomputes the entire application against the exact original and recorded
implementation before exporting a new candidate protocol. Editing a checksum does
not bypass replay. Unsigned assertions can nevertheless be consistently reauthored;
reviewer/completer identity, chronology and truthful completion are not verified.
Dates are checked for calendar syntax only. They are not evidence of the order in
which work happened.

Later changes to bound work/source/locator metadata can stale the persisted
completion hash. This tool never repairs that hash or reopens the work. Work
completion is a supplied assertion, not an immutable approval or execution record.
A current binding is not evidence of artifact existence, authorship or content.
Use the separate [local artifact review](LOCAL_ARTIFACT_REVIEW.md) only when an
explicit local byte check is intended; even matching bytes do not assess acceptance.

Keep the actual original protocol, detached application and recorded implementation.
The candidate retains completion fields; completer/reviewer metadata, notes and
snapshots are detached. Ordinary research/native archives preserve the candidate,
not this transition history. Report/extraction transition archives do not accept
this application kind. There is no project-wide completion, batch completion,
status-edit, reopen or historical-completion renewal path in this increment.

## Local limits and safety

Candidate/review inputs are limited to 10 MB and protocol/application inputs to
50 MB. There is exactly one selected completion per application. These are not
hard CPU/memory ceilings. Strict JSON, exact schemas, whole-protocol validation
and canonical replay apply. All output is prepared before exclusive creation;
existing directory entries, including observed dangling links, are refused. This
is not an atomic path-race or parent-alias defense, and failed writes may leave a
partial new file. Input and output files are supplied explicitly by the operator.

No source/artifact locator is fetched or opened; no network, model or experimental
procedure is invoked. Text and identities are retained as supplied, not redacted
or authenticated. Keep private inputs and generated artifacts outside this public
repository. No scientific, clinical, regulatory or development-stage decision is
made, and no source review or readiness is advanced automatically.
