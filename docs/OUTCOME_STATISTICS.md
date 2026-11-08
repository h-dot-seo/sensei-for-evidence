# Supplied outcome statistics review

This offline metadata workflow records what a supplied source says. It does not
calculate effects, significance, precision, sample sizes or causality. All values
in `examples/statistics-review.json` are fictional software-test data, not real
observations or experimental instructions.

## User journey

Run the ordinary protocol through `research_status.py`, `work_review.py` and
`synthesis_review.py`, or create and verify a reproducible `research_bundle.py`
archive. The example extends `sampling-review.json` with per-result statistics.
It deliberately retains older planning/synthesis review hashes, so those source
reviews are stale until a human records a new review. It also retains incomplete
search, full-text, appraisal and reporting stages; metadata does not establish a
census, evidence support or a final scientific review.

The example exposes different supplied arm unit labels and mean/median labels,
missing comparator dispersion, missing interval level, missing statistical test
and missing multiplicity adjustment. Its supplied direction and contrast estimate
are intentionally not derived from the arm summaries. The program preserves all
of them for source review rather than silently reconciling them. The numerical
relationship, endpoint comparability, statistical validity and internal
consistency of those assertions remain **NOT_ASSESSED**.

## Input contract

Optional `outcome_statistics` belongs to one `experimental_units` condition pair.
If supplied, it must be a list with every linked evidence ID exactly once. Each
row requires `evidence_id`, `source_locator`, `limitations`, `treatment`,
`comparator`, and `contrast`. Fixed arm roles refer to the condition pair, not
new arms or independent statistical units. Unassignable aggregate results must
not be silently mapped to a pair.

Each arm requires:

- `value`: textual summary value with its supplied unit.
- `summary_statistic`: textual label such as a supplied mean or median label.
- `dispersion`: textual variability value/range with its supplied unit.
- `dispersion_type`: supplied SD, SE, IQR or other label, never inferred.

Contrast requires:

- `measure`: supplied effect-measure label.
- `estimate`: supplied estimate with unit; no subtraction or ratio is computed.
- `uncertainty`: supplied interval/range text with unit; no interval is computed.
- `uncertainty_type` and `uncertainty_level`: supplied type and level separately.
- `statistical_test`, `p_value`, `multiplicity_adjustment`: supplied text only.
- `direction`: the source's direction assertion, never deduced from values or p.

All fields except direction use strict reporting-state objects. Reported objects
require `status`, nonempty textual `value`, and `source_locator`, plus `unit` for
arm value/dispersion and contrast estimate/uncertainty. Numeric JSON values,
booleans, nulls and partially populated reported fields are rejected. For
`unknown`, `not_reported` or `not_applicable`, provide only `status`, `reason`, and
`source_locator`. Put partially reported/ambiguous source text in `reason` rather
than inventing missing units or statistic labels. P-values remain textual (for
example inequalities); no range checks, thresholding or significance label is
computed. A dimensionless unit must be explicitly supplied, not guessed.

Reported direction requires `status`, `value`, `source_text`, `source_locator`,
and `orientation`. Allowed values: `higher`, `lower`, `no_difference_reported`,
`mixed`, `unclear`. Orientation must be `treatment_relative_to_comparator`.
If that orientation cannot be justified from the supplied source, use unknown
and preserve the wording/reason. Reverse orientation is rejected, never inverted
automatically. No-difference wording does not establish equivalence or absence of
an effect. Nonreported direction uses the ordinary status/reason/locator union.
Even reported source text is unverified; it is not checked against a full text.

## Review outputs and limits

`statistics_review.missing_fields` lists unknown/not_reported fields.
`literal_label_differences` compares only exact arm value-unit, summary-statistic,
dispersion-unit and dispersion-type labels when both are reported. These are cues for human
review, **not incompatibility or numerical inconsistency findings**. Case,
whitespace, synonyms, unit conversions and the meaning of labels are not
normalized. Different types may be appropriate; equal labels do not establish
comparability. No contrast-to-arm value, interval-to-estimate or p-to-direction
consistency judgment is performed. Not-applicable assertions are preserved,
not certified as appropriate. Empty cues do not mean complete or valid science.

Absent statistics metadata is queued under `units_without_outcome_statistics`.
Supplied metadata with missing fields or literal label differences is queued
under `units_with_statistics_review_cues`. Missing condition stage yields null;
a supplied empty condition ledger yields empty queues while evidence without a
condition stays separately visible. Conditions without this optional metadata
keep their earlier source bindings.

Status/synthesis show protocol-wide queues. WP packets and bundle CSV show only
intersecting conditions, but their cues cover each full condition including
sibling outcomes outside the packet; this scope is explicitly labeled. JSON
contains the full values, sources and review cues. Source-bound planning/synthesis
reviews bind supplied statistics and derived cues; changing or removing them
stales affected assertions without renewing or changing them. PRISMA counts
remain counts of records/reports/supplied study IDs, never observations or n.
`numeric_consistency=NOT_ASSESSED` and `effect_assessment=NOT_PERFORMED` remain fixed.
