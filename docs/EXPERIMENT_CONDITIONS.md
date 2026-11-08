# Supplied nonclinical comparison conditions

The optional `experimental_units` ledger structures supplied model, treatment,
concentration, time, comparator and causal-limit information around exact result
rows. It is extraction metadata, **not an experimental protocol, recommendation,
scientific appraisal or execution tool**. No actual procedure, organism, material,
dose, duration, model call or literature retrieval is generated.

The concrete gap was that free-text model/intervention/comparator descriptions
could not reliably distinguish conditions for multiple outcomes. The bounded v1
contract makes the comparison scope explicit without inferring missing values.

For reviewed append-only entry into an existing protocol, use
[manual condition intake](MANUAL_CONDITION_INTAKE.md). It retains explicit document
selections and human review in a detached replay record, while preserving existing
results and using this condition schema unchanged.

## Synthetic journey

```sh
python evidence_workflow.py examples/experiment-review.json
python work_review.py examples/experiment-review.json --work-package WP-TRANSLATION --text
python synthesis_review.py examples/experiment-review.json --text
python research_status.py examples/experiment-review.json --text
python research_bundle.py create examples/experiment-review.json ../synthetic-conditions.zip
python research_bundle.py verify ../synthetic-conditions.zip
```

The example uses a fictional, non-operational signal model, fictional concentration
and duration units, and no real experimental instructions. It links e1/e2 to one
comparison record and leaves e3 unlinked. Comparator duration and e2 observation
time/reference remain unresolved. Those limitations remain visible beside supplied
WP priorities and synthesis statements, without promoting any scientific claim.

## What one record means

Despite the field name, an `experimental_units` entry means **one supplied
treatment–comparator condition pair**, not an independent statistical experimental
unit, biological replicate, sample size or evidence-weight unit.

- `experiment_id` is unique and nonempty.
- `evidence_ids` is a nonempty unique list of existing result IDs.
- All linked results must share one exact supplied record ID and study ID. Those
  IDs are derived from evidence, not accepted as potentially conflicting inputs.
- A result cannot belong to multiple condition records in v1.
- Multiple linked results assert that those outcomes belong to this same pair;
  per-outcome observation times remain separate.

Do not attach multiple arms, doses or exposure conditions to one record and assume
all results apply to all of them. Represent separately sourced comparison/results
with distinct extraction IDs when justified by the source. Aggregated or ambiguous
results may remain unlinked. The tool never splits a result or invents assignments.

## Required record fields

- `source_locator` and `limitations`: supplied provenance and scope limitations.
- `model`: `kind`, `label`, `source_locator`, `limitations`. Kind is one of
  `in_vitro`, `in_vivo`, `ex_vivo`, `in_silico`, `other`, `unknown`. This is a supplied
  classification, not an automatically inferred model or validation result.
- `treatment`: `label`, `source_locator`, `concentration`, `exposure_time`.
- `comparator`: an explicit reporting state. If reported, it also has `label`,
  `source_locator`, `concentration`, `exposure_time`. Otherwise it has `reason`
  and `source_locator`, with no fabricated comparator or measurement values.
- `observation_times`: exactly one row per linked result, with `evidence_id`,
  `time` and `reference_event`.
- `causal_basis`, `causal_statement`, `causal_limitations`, `causal_source_locator`.

Nested shapes reject unknown fields. The source's model/treatment/comparator
wording is preserved; its scientific consistency with legacy free-text extraction
fields is **not** automatically assessed.

## Measurement and missingness contract

Concentration, exposure duration and observation time use this strict union:

- `status: reported`: nonempty string `value`, string `unit`, and `source_locator`.
- `status: not_reported`, `unknown`, or `not_applicable`: nonempty `reason` and
  `source_locator`, with **no** `value` or `unit` fields.

All fields must be explicitly supplied. Omission is not silently converted into
unknown, unreported, zero or not applicable. A reported zero must remain the source's
text, such as `"0"`, with its supplied unit; it is not a missingness marker.

Reported values are text so exact wording, precision or source ranges can be
preserved. There is no numeric coercion, unit conversion, normalization, dose
comparison, timing arithmetic or effect estimation. A source giving a value but
not its unit does not satisfy the reported union: keep it `unknown`, preserve the
partial source wording in `reason`, and do not fabricate `unit: "unknown"` as if a
unit had been reported. Separate unit-status support is outside v1.

Exposure duration is not outcome observation time. Every observation also requires
an explicit `reference_event` with the same reporting states. For `reported`, it
has `value` and `source_locator` but **no unit**. Other states have `reason` and
`source_locator`. The example's fictional source-defined event is not assumed to
be treatment start. No anchor is inferred from an elapsed value.

## Causal claims and uncertainty

`causal_basis` is one of `association`, `intervention`, `unknown` and must match the
existing supplied `mechanism_basis` labels of every linked result. This prevents a
structured row from silently upgrading an existing label; it is not a scientific
causal test. In particular, “intervention” is not proof of necessity, sufficiency,
specificity, mechanism or clinical translation.

The supplied claim, causal limitations and locator remain visible. Derived fields
always retain `condition_review_status: NOT_ASSESSED` and
`causal_assessment: NOT_PERFORMED`. Unknown model kind, unknown/unreported comparator
or measurements are listed in `unresolved_fields`. Not-applicable remains an
operator assertion, not proof that a design is adequate.

## WP, synthesis and review-source links

Work and synthesis views include every full condition record intersecting their
linked/cited result IDs. Each view shows the intersection and the record's other
outcome IDs separately. An appraisal or statement about e1 does not expand to e2
just because both share a condition or study.

Unresolved-condition flags are explicitly scoped to the **entire intersecting
condition record, including its other outcomes**. An e1-only packet may therefore
show a condition whose unresolved field is e2's observation time. It is not a
claim that e1 itself lacks that value; the exact paths and other-result scope are
shown. No queue count is converted into a scientific priority.

All full intersecting condition records and the supplied-stage marker participate
in planning and synthesis source bases. Changing conditions, outcome membership,
limits or timing anchors stales affected assertions; unrelated condition changes
do not. No review hash or priority is automatically renewed. Omitted-ledger legacy
bases remain unchanged. Adding/removing the stage or a relevant record is visible
in the binding. Direct helpers reject omission of condition binding when a ledger
is supplied.

An absent ledger is `NOT_SUPPLIED` with null coverage queues in the shared workflow
and status. A supplied empty list is `SUPPLIED`, with all results explicitly lacking
condition links. Lack of a link does not mean a study is poor, unusable or incomplete.

Reviewed mock adapter protocols permit this metadata enrichment without changing
accepted extraction rows. Original receipt integrity checks still apply. Comparison
tracks experimental-unit changes. Existing bundle JSON carries the full ledger;
work CSV appends condition IDs, missing-link IDs and stage. The archive file set
is unchanged, and unit counts are never presented as independent replicate counts.

## Boundaries

Save the original protocol and recorded implementation to reproduce the view.
Source labels, locators, condition assignments and scientific claims are supplied,
not authenticated. Outputs retain source/reviewer text without redaction; keep real
inputs and generated artifacts outside the public repository.

All fixtures are synthetic. There are no external calls, credentials, costs or
uploads. No pathogen enhancement/transmission details or operational biological
procedures are included. Census, extraction completeness and conclusion readiness
remain unestablished/not ready, regardless of condition-field completeness.

## Outcome-specific sample reporting

`outcome_sampling` is an optional list on each supplied condition. When supplied,
it must cover every linked evidence ID exactly once. The fictional
`examples/sampling-review.json` adds it to the condition example, deliberately
leaving old planning/synthesis review hashes stale for a reviewer to revisit.
Run it with `synthesis_review.py`, `work_review.py`, `research_status.py`, or the
ordinary reproducible bundle command. PRISMA record/report/study counts do not
change when sample metadata is added.

Each row requires `evidence_id`, `source_locator`, `limitations`, `analysis_unit`,
`independence_basis`, `treatment`, and `comparator`. The two arms each require
`animal_n`, `biological_n`, `technical_n`, and `analyzed_n`. Each n uses the same
strict reporting-state union as condition measurements: reported textual value,
unit (what is being counted, including denominator/scope), and source locator;
or explicit unknown/not_reported/not_applicable with reason and locator.
Analysis unit and independence basis use that union without a unit field.
An independence basis is a supplied explanation, not an independence finding.
Do not replace missing units or populations with guesses. Preserve ambiguous or
partly reported n in an unknown field's reason and source locator.

Counts may differ by result, arm, population and time. A condition pair is not a
statistical unit; readings are not assumed to be independent organisms or
biological replicates. No totals, numeric consistency check, inferred n, sample
size recommendation, statistical adequacy or effect calculation is performed.
The two arm roles are fixed and scoped to this condition's treatment/comparator;
aggregate results or extra arms must not be silently assigned here. No automatic
cross-arm or cross-outcome numerical discrepancy verdict is made. Such supplied
ambiguities belong in `limitations` and require human source review.

Missing metadata is queued under `units_without_outcome_sampling`; supplied
unknown/not_reported fields are listed individually in `sampling_review` and
queued under `units_with_unresolved_sampling`. Missing condition stage yields
null queues, whereas a supplied empty condition ledger yields empty queues.
Not_applicable assertions are preserved, not validated as appropriate. Even when
all fields are reported, `independence_assessment=NOT_PERFORMED` and
`numeric_consistency=NOT_ASSESSED` remain fixed. WP queues cover full intersecting
condition records, including sibling outcomes outside that WP, as already
labeled in the packet. Synthesis citations, source-bound review hashes, comparison
diffs and bundle JSON carry the full metadata; changing it stales affected
planning/synthesis assertions. Older protocols without this optional metadata
retain their condition source bindings, but now display the missing-metadata
queue. This is reporting coverage, not scientific approval.
