# Supplied claim-position comparison

A citation alone does not say whether a supplied result supports an observation,
challenges a claim, or leaves a causal interpretation unresolved. Optional
`evidence_positions` on a synthesis statement records those **human-supplied
positions** with exact claim scope and source text. It does not generate positions,
validate source excerpts, infer causality, decide refutation or produce consensus.

## Fictional review journey

`examples/claim-comparison.json` extends the statistics/n/condition example.
The first statement cites two result rows from one supplied study. Its positions
label one result supportive and another challenging for an observation component,
while its causal component has unclear and not-assessed positions. These are
fictional interpretations for software testing. The second result concerns a
different endpoint: endpoint comparability and relevance are explicitly unassessed.
Two result rows or multiple aspect positions are **not independent studies or
votes**. No majority count, weighting, direction calculation or conclusion is made.

Use `synthesis_review.py examples/claim-comparison.json --text` to see grouped
positions beside result/source traces and the full intersecting condition record,
including supplied n and statistics. `work_review.py` connects relevant positions
to existing work packages; it creates no work, priorities or decisions.
`research_status.py` displays absent and unclear/unassessed position metadata.
The usual bundle contains complete synthesis JSON and linked statement IDs in
work-packages.csv. PRISMA record/report/study accounting is unchanged.

## Input contract

Every position requires exactly these nonempty text fields:

- `evidence_id`: an exact result ID already cited by this statement.
- `claim_component`: an exact substring of the supplied statement text.
- `aspect`: observation, causal, clinical_applicability, or other.
- `relation`: supports, challenges, mixed, unclear, or not_assessed.
- `rationale`, `limitations`: the author's interpretation and its limits.
- `source_locator`, `source_excerpt`: supplied evidence trace, not authenticated.
- `recorded_by`, `recorded_at`: supplied author label and ISO calendar date.

For each result/component/aspect combination, at most one position is allowed.
One result may have different positions for different components or aspects.
Conflicting reviewers for the same combination are not adjudicated by this
schema: retain their uncertainty in the supplied rationale/limitations and use an
appropriate unresolved relation, rather than silently overwriting or voting.
If the list is supplied it must cover every cited result at least once; use an
explicit not_assessed position when needed. An absent list means NOT_SUPPLIED;
an empty supplied list is invalid for a nonempty citation set. Nonexistent claim
substrings, uncited results, malformed fields/dates and duplicate identities fail
validation. A substring match establishes only literal linkage, not correct scope.
All aspects/components beyond the supplied ones remain unassessed, not implicitly
covered. Partial words or ambiguous excerpts should be replaced by a meaningful
component by the human author; the program does not infer semantics.

## Review and source boundaries

Groups use only identical component/aspect labels and list the original positions.
They retain `assessment=NOT_PERFORMED`; statement `support_status=NOT_ASSESSED`
never changes, including when all relations say supports or a review source hash
matches. Observational or interventional extraction labels and statistical
metadata never assign or override a relation. Challenges does not prove a claim
false, and no_difference_reported does not determine a position automatically.
Author and review labels are assertions, not authentication.

Positions join the existing statement source hash. Adding, editing or removing
positions stales a previously current statement review. Changes to cited result
conditions, n or statistics also stale it; missing metadata remains visible.
Position entries do not have separate source reviews: the status applies to the
**whole statement**, including its other cited results. Existing statements
without positions retain their earlier source bindings. The example retains old
hashes on purpose to show stale review rather than manufacturing fresh approval.

WP packets show a full statement and its review state for context, then separately
select `work_positions` whose evidence IDs belong to the WP. They explicitly list
`other_statement_evidence_ids`; full statement metadata must not be mistaken for
WP-specific coverage. Existing planning assertions remain bound to evidence and
work scope, not to these interpretation positions. This feature does not revise
priorities or certify a work package as accepted. Protocol and implementation
hashes identify the current review packet.

`statements_without_evidence_positions` and
`statements_with_unresolved_positions` are metadata queues, not support verdicts.
An absent synthesis stage produces null queues; a supplied empty synthesis stage
produces empty queues. All supplied positions saying supports/challenges/mixed
can clear the unclear/not_assessed queue without establishing adequacy, complete
aspect coverage, independent evidence, a census or scientific/clinical validity.
