# Explicit multiple studies within a report

An included report can now declare `study_ids` instead of the legacy `study_id`.
This removes the requirement to invent extra records or split one paper into
multiple report identities merely to represent separately supplied studies.

These are operator-supplied identities. The software does not decide what counts
as a study, verify that two IDs are distinct studies, infer independence or treat
each assay, experiment, arm or result as another study.
Report-level inclusion also does not make a separate eligibility decision for
each listed study. `study_eligibility_assessment` remains `NOT_PERFORMED`; per-study
eligibility/exclusion decisions are outside this first migration.

## Bounded opt-in

```json
{"report_id": "report-one", "record_ids": ["record-one"], "retrieval": "retrieved", "decision": "include", "study_ids": ["study-A", "study-B"], "locator": "synthetic://report-one"}
```

- Use either `study_id` or `study_ids`, never both, including when one is null.
- The plural field must be a nonempty list of unique nonblank strings. Exact
  spelling, whitespace and order are retained; no case folding or normalization
  occurs. A singleton list is valid opt-in.
- In this increment, plural declarations represent **included, retrieved report
  memberships** only. Pending, excluded or unretrieved reports cannot use the
  plural field. Do not change eligibility or retrieval assertions to bypass this
  restriction; pre-inclusion study inventories are not implemented here.
- Every evidence row still has one `study_id` and its own result/evidence ID and
  locator. Its study must be explicitly declared by its included report. Multiple
  studies within one record require that record's report to use the plural form.
  An absent/unmapped report or a legacy scalar declaration does not authorize it.
- One record still maps to at most one report. Several explicitly mapped records
  may describe one report. The same literal supplied study ID may occur in more
  than one report, but no title, locator or apparent similarity creates that link.

Adding `study_ids` activates complete report-structure and evidence-membership
validation in the core workflow as well as the report tool. Legacy inputs without
the field retain their previous validation path and output structure. The field
was formerly ignored opaque metadata; it is now reserved and cannot be used for
an unrelated list. Supplied report rows are not rewritten in place.

## Reproduce the fictional example

```sh
python evidence_workflow.py examples/multi-study-report.json
python prisma_reports.py examples/multi-study-report.json
python prisma_audit.py examples/multi-study-report.json --text
python research_status.py examples/multi-study-report.json --text
python work_review.py examples/multi-study-report.json --work-package WP-RESULT-LINKS --text
python review_handoff.py examples/multi-study-report.json --text
python research_bundle.py create examples/multi-study-report.json /outside/new-multi-study.zip
python research_bundle.py verify /outside/new-multi-study.zip
```

Choose a new local bundle path outside this public repository. The example is
entirely fictional: two records, two reports, three distinct supplied study IDs,
two result rows and four report-study memberships. Report one declares A/B/C and
has results for A/B. Report two explicitly reuses A but has no result rows.

Two memberships therefore lack results: C in report one, and A in report two.
The A result from report one does not fill report two. This is source-specific
bookkeeping, not a judgment that extraction is exhaustive or scientifically adequate.

## Keep units and queues distinct

Existing counters retain their meaning:

- Record/report counts do not increase merely because a report declares more
  studies. `included_studies` counts exact distinct supplied study IDs across
  included reports, not independently verified study identities or study-level
  eligibility decisions. Its legacy name is retained for compatibility.
- `reports_with_extraction` means a report has at least one result row.
  `extraction_pending_reports` means an included report has no result rows.
  One result does not establish coverage of all declared studies.
- Record-level extraction queues likewise concern any/no result presence.

For opted-in protocols, `report_study_coverage` adds a separate membership ledger.
Membership IDs are exact input pointers such as `/reports/0/study_ids/1`; mixed
legacy scalar reports use `/reports/1/study_id`. Each membership lists matching
result IDs from that report and study, plus a result-presence flag.
These pointers identify locations in that one input, not stable identities across
versions. Reordering reports or studies changes the pointers without changing
the exact supplied report-study pairs.

PRISMA audit adds a separate report-study-membership partition, while existing
record and report partitions stay unchanged. Status and handoff add
`report_study_memberships_without_results`. This queue identifies pairs, not
global studies: another report's result never clears it. Missing memberships are
not scientific inadequacy scores, and an empty queue is not exhaustive extraction.

Work packets and synthesis snapshots retain explicit report-study coverage. A
work packet shows all memberships of reports explicitly reached through its
result citations or direct record source references, including other studies in
those reports. This extra source context is **not** an inferred work requirement,
new dependency or acceptance criterion. A planned-search reference alone does
not expand into every record/report in that search.

## Compare membership migrations without guessing identity

```sh
python compare_runs.py before-protocol.json after-protocol.json
python compare_runs.py before-protocol.json after-protocol.json --text
```

When either validated input uses `study_ids`, the comparison adds
`report_study_comparison`. Both sides are projected, including legacy scalar
memberships on the side without the plural field. Legacy-to-legacy comparisons
keep their previous JSON and text structure.
The comparator consumes validated report ledgers without constructing intermediate
CSV. Runtime-specific CSV character restrictions therefore do not alter or reject
an otherwise valid JSON identity during comparison. Default report CSV export is
unchanged; no ID is stripped, normalized or replaced to satisfy a CSV serializer.

Memberships are matched only by the exact pair of `report_id` and `study_id`.
The output keeps these as separate fields, without a delimiter-based key:

- Converting `study_id: "study-A"` to `study_ids: ["study-A"]` retains the pair.
  Declaration form and changed input location remain visible.
- Reordering report rows or the declared study list retains matching pairs and
  exposes changed locations/order, rather than creating or removing studies.
- Changing a literal report or study ID removes the old pair and adds the new
  pair, even if locators, result IDs or other content are identical. There is no
  automatic rename, merge, split or identity reconciliation.
- The same study ID in two reports yields two separate pairs. Adding a result
  for one does not change the other. Moving a result between pairs is shown as a
  removal and addition of that exact result ID at the affected pairs.

Each pair has before/after report assertions, declaration form and original study
order, input pointers, attached result IDs and full normalized result assertions.
Changed report fields and changed attached-result fields are listed separately.
Changing a source record link, locator or result value is therefore visible even
when the pair and result IDs stay the same. Partial result additions can change
pair coverage while existing report-level extraction counters stay unchanged.

`retained_count` means only that the same supplied pair exists on both sides.
`unchanged_count` is stricter: the entire pair snapshot, including input locations,
declaration order, report assertions and attached results, must be identical.
Neither count verifies source/study identity, independence or scientific meaning.
For an absent report ledger, the stage is `NOT_SUPPLIED` and pair counts are null;
an explicitly empty ledger is `SUPPLIED` with zero counts. Included memberships
only are projected; nonincluded report metadata remains in the ordinary report
entity comparison and is not converted into study eligibility assertions.

The readable view shows both membership states, changed fields and explicit
verification limits. Full assertion snapshots remain in JSON. This focused view
does not compare underlying searches, screening, context, appraisal or work
assertions; use the full comparison for those sections. No review is renewed,
no missing result is manufactured, and no clinical/development validity or
study-level eligibility is inferred from a label or a retained pair.

## Compatibility and safety

For legacy inputs, the seven-column report CSV remains byte-for-byte unchanged.
Opted-in report CSV preserves that prefix and appends `declared_study_ids` as a
JSON array. The old scalar cell is blank for plural reports; IDs are never joined
with an ambiguous delimiter. Included scalar reports in a mixed ledger appear as
one-element arrays in the added column. Nonincluded rows use an empty array.
Existing formula-safety quoting applies to exported cells.

Legacy normalized core/report/audit/status results, report CSV and existing
planning/completion/synthesis bindings remain unchanged for unchanged inputs.
Explicitly changing report membership is a real source change and can stale those
bindings. Bundles fingerprint the new shared validator and retain raw declarations.
Use the recorded implementation when verifying an older bundle or intake artifact.

An appraisal still belongs to one supplied study; an experimental unit still
belongs to one source record and study. A multi-study paper does not relax those
guards or make result rows independent votes. Source identity, study identity,
search completeness, scientific validity and clinical applicability remain
unverified. No real paper, result, procedure or guideline is included or retrieved.

[Full-text source/reviewer assertions](REPORT_REVIEWS.md) can describe several
documents for one report without splitting report or study identities. Their
positions remain report-level, and changing study assignments does not silently
rewrite the source target. Per-study eligibility and exhaustive document reading
remain separate, unperformed assessments.

The optional [report-study review ledger](REPORT_STUDY_REVIEWS.md) now preserves
separate human eligibility positions and reviewed-source ID selections for exact
pairs. It does not turn those positions into canonical study selection or filter
results. Pre-inclusion study inventory remains unimplemented; do not change report
eligibility merely to obtain study targets.
