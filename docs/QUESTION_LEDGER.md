# Supplied question records

Roadmap #42 and reader adjustment (a): optional `question_records` records supplied
questions and narrowly reviewed state changes. The immutable root `question` string
and existing gaps/statements are not rewritten. Links point from question records to
existing statements only. No question or hypothesis is generated. No answer is assessed.

## Supplied labels, not scientific closure

| Existing supplied label | Allowed separately reviewed next labels |
|---|---|
| OPEN | NARROWED, ANSWERED_WITHIN_BOUNDS, UNRESOLVED |
| NARROWED | ANSWERED_WITHIN_BOUNDS, UNRESOLVED |
| ANSWERED_WITHIN_BOUNDS | none |
| UNRESOLVED | none |

Every other transition, including same-state renewal, is rejected. The last two are
terminal **record labels in this tool**, not scientifically established completion.
This implements the reader's constraint not to renew or reopen terminal labels; it
does not introduce a research stopping rule. A separate policy for reopening them is
not implemented. Transition changes only status, statement_ids, basis_sha256,
recorded_by, recorded_at, rationale and limitations on one selected existing row.
Identity, text, origin, ancestry, reopening and all other rows/inputs stay unchanged.
Detached before/after review remains outside ordinary bundles; retain original input,
application and trusted implementation. This is not a signed history or chronology proof.

Each row has exact fields. Up to 100 total records are accepted. Parent IDs must exist
and be acyclic. NARROWED means this supplied parent has at least one child, not that
semantic narrowing was evaluated. A batch can add the parent and child together.
OPEN and UNRESOLVED can precede synthesis. ANSWERED_WITHIN_BOUNDS requires at least
one existing statement link, even if that statement is pending or stale. Such a link
never establishes an answer, support or acceptance. No links means a null basis.
Linked statement review bases form a sorted independent digest; changed bases are
reported as STALE_SOURCE without rewriting the record. Protocol-origin hash changes
are separately PROTOCOL_QUESTION_CHANGED. Bibliographic/adapter root immutability
still applies; the question tools cannot bypass that rejection.

Origin has exactly kind, ref_id, protocol_question_sha256, external_record_sha256 and
label. PROTOCOL uses the root-string hash and no ref_id. CHALLENGE and
READINESS_ASSERTION check existing IDs. AMENDMENT is a supplied textual reference,
not a verified amendment ledger. CONSULTATION accepts an optional opaque SHA-256
and label and requires explicit existing work-package or amendment-note reopening;
no external text, file, service or Persona record is read. Other origin-specific hash
fields must be null. OTHER has no reference ID. Declared origins and reviewer labels
are not authenticated people, source provenance or approvals.

## Complete local workflow

Supply `QUESTION_INPUT.json` and an existing `WORK` directory. The following uses
fictional candidate/transition files for the repository's synthetic demonstration.
They are not suitable research answers. For your work, author your own fields after
using template; `--statement-id ID` may be repeated to select current statement bases.
Transition-template defaults to the selected row's existing statement IDs and derives
current bases only in an incomplete proposal, leaving status/recorder/date/rationale/
limitations blank. It does not renew the stored row or infer permission to transition.

After each `target`, separately inspect the exact target and fill a new review JSON
with schema_version 1, receipt_id, exact target_sha256, decision
`record_supplied_questions`, reviewer, reviewed_at and rationale. The two review files
below must be supplied separately. A blank/rejected/stale review cannot assemble.
Import review records the supplied labels, not endorsement of an answer. Test code
supplies fictional reviewers solely for this synthetic walkthrough.

```sh
python question_intake.py template QUESTION_INPUT.json --output WORK/template.json
python question_intake.py target QUESTION_INPUT.json examples/manual-question-candidates.json --output WORK/target.json
python question_intake.py assemble QUESTION_INPUT.json examples/manual-question-candidates.json WORK/import-review.json --output WORK/application.json
python question_intake.py verify QUESTION_INPUT.json WORK/application.json --protocol-output WORK/questions.json
python question_intake.py transition-template WORK/questions.json question-one --output WORK/transition-template.json
python question_intake.py target WORK/questions.json examples/manual-question-transition.json --output WORK/transition-target.json
python question_intake.py assemble WORK/questions.json examples/manual-question-transition.json WORK/transition-review.json --output WORK/transition-application.json
python question_intake.py verify WORK/questions.json WORK/transition-application.json --protocol-output WORK/transitioned.json
python question_review.py WORK/transitioned.json --text
python compare_runs.py WORK/questions.json WORK/transitioned.json
python research_bundle.py create WORK/transitioned.json WORK/questions.zip
python research_bundle.py verify WORK/questions.zip
```

The engine, status, synthesis, comparison, handoff and bundle summary expose optional
question context. Readiness review adds counts **outside the gate ledger**. Existing
readiness gates, gate digests, completion rules and scientific NOT_READY remain unchanged.
Absence preserves existing run output and CLI text; new source fingerprints still change.
The old recorded implementation is needed to replay old detached applications/bundles.
Only fixed fictional walkthrough target hashes receive release maintenance. No actual
human review, source, old archive or review assertion is automatically rewritten.

## Input/output and validation boundaries

CLI reads are bounded: protocol 50,000,000 bytes, supplied document/review 10,000,000,
application 50,000,000. These are serialized-size limits, not total CPU/memory budgets.
Strict JSON rejects duplicate keys and nonfinite values. Output paths are exclusive;
this is not a race-proof ancestor-path defense or transactional multi-output write.
An earlier output can remain if a later output fails. Invalid input/unavailable output
uses exit 1 with fixed stderr and empty stdout. Successful replay means internally
consistent supplied records, not authenticity; consistently reauthored unsigned records
can replay. No automatic update, source access, model call, new gate or release approval.
