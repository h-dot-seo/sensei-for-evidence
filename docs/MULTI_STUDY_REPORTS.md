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
