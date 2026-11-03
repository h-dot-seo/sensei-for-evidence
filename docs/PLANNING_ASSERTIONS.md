# Supplied planning priorities and stale-source review

This feature records **a person's supplied rank and rationale**. It does not choose
priorities, infer scientific importance, produce medical/development advice or
change dependency ordering.

The concrete gap is preserving why a work package was ranked while noticing when
its supporting source context, evidence, appraisal or completion scope changes.
Previously the workflow had dependency ordering but no source-bound planning
assertions or explicit stale-priority view.

## Synthetic user journey

```sh
python work_review.py examples/planning-review.json --work-package WP-TRANSLATION --text
python research_status.py examples/planning-review.json --text
python evidence_workflow.py examples/planning-review.json
```

The synthetic planner gave `WP-TRANSLATION` rank 1 and its prerequisite
`WP-MECHANISM` rank 2. This intentionally shows that **declared rank is not execution
availability**: translation remains blocked until the prerequisite has a supplied
completion assertion. Completing that prerequisite changes dependency queues but
does not establish clinical applicability, regulatory readiness or a sound plan.

The existing source-linked packet keeps guideline population limits, development
stage/regulatory uncertainty, extraction-level appraisal coverage and the supplied
acceptance criteria beside the rank/rationale. Source completeness and conclusions
remain unestablished.

## Creating an assertion

1. Prepare and validate the ordinary protocol, including evidence, context,
   appraisals, dependencies and completion criteria.
2. Run `work_review.py` without any planning assertions. Each packet exposes
   `planning_review_target.basis` and `basis_sha256`. The ordinary workflow output
   also exposes all targets under `planning.review_targets`.
3. Review the supplied inputs and decide whether/how to rank the work yourself.
   Add one entry per chosen WP to top-level `planning_decisions`:

```json
{
  "work_package_id": "WP-TRANSLATION",
  "priority_rank": 1,
  "rationale": "A supplied planning rationale, not an inferred priority.",
  "uncertainty": "State unresolved source, applicability and planning assumptions.",
  "planner": "Your supplied reviewer label",
  "planned_at": "2026-11-03",
  "basis_sha256": "Copy the reviewed target's 64-character lowercase hash here"
}
```

The placeholder hash above is intentionally not valid. See
[the synthetic fixture](../examples/planning-review.json) for runnable assertions.
Rank must be a positive JSON integer, not a boolean, string or float. Smaller ranks
express earlier **supplied** ordinal preference. Ties are allowed; IDs within a tied
group are listed lexically for deterministic display, not automatically tie-broken.
No decision is required for every WP. Missing assertions remain `NOT_SUPPLIED`.
Unknown or duplicate WP targets and malformed records fail validation.

All of the WP's linked evidence, explicitly linked contexts and intersecting
appraisals are bound. There is no selective reference list that could silently
omit an inconvenient linked result or reviewer judgement.

## What the source binding covers

The versioned canonical basis contains:

- A shared source-scope hash over the original protocol's question, inclusion and
  exclusion criteria, declared search plan, supplied searches, screening and reports.
- The WP's scope fields, including its question, evidence/context links,
  deliverable, acceptance criterion and dependencies.
- Its direct dependencies' scope fields.
- Full linked extraction and context rows, and all intersecting appraisal rows.

The original protocol is the shared source snapshot. Output names the bound fields
and supplies their shared hash rather than duplicating a potentially large corpus
inside every target. Keep prior protocol versions if you need to investigate why a
hash became stale; the hash alone is not an amendment history.

WP/dependency `status`, `blocked_by`, `artifact_locator` and `acceptance_verified`
are excluded so ordinary recorded progress does not invalidate the source binding.
The planning ledger itself and the protocol version label are also excluded. An
unrelated WP-only change does not invalidate an existing assertion unless that WP
is a direct dependency. New work remains explicitly unranked. This does not prove
that an old ranking is still a good project-wide decision.

By contrast, changes to any supplied search/screening/report source context conservatively
invalidate all assertions, even if a search is not linked to one WP. Census-oriented
planning may need reassessment as the source set or accounting changes. This is an
explicit content-binding rule, not a claim that every source change is scientifically
important. Existing `compare_runs.py` can help inspect changed protocol fields.

Canonical JSON ignores object-key order and retains array order and JSON value
types. Reordering linked ID lists can therefore change a basis hash. Hashes are not
signatures, planner authentication, source verification or proof of good judgement.

## Current, stale and missing views

- `CURRENT_SOURCE`: the supplied basis hash matches the current bound inputs.
  This means content consistency only.
- `STALE_SOURCE`: the original rank/rationale is retained as a historical assertion;
  `current_priority_rank` is null and the WP is excluded from current rank groups.
- `NOT_SUPPLIED`: no planning assertion was provided; no rank is invented.

The tool exposes the current basis as a review target but **never renews an assertion
or copies its hash automatically**. A human can review changes and update an
assertion in a revised protocol. Stale assertions remain readable rather than
blocking all research views.

Current rank groups are protocol-wide supplied assertions, including completed work.
In a selected packet, `global_current_rank_groups` is labelled with that scope; it
is not a selected-WP list, outstanding-work queue or execution recommendation.

`research_status.py` exposes missing/stale planning queues separately from dependency
queues. `work_review.py` shows the assertion, source-match status and current basis.
The core `execution_order` remains unchanged; it is dependency ordering, not a
recommended schedule. `compare_runs.py` tracks supplied planning-decision changes.

Bundles retain planning views in JSON and append supplied/current rank, source
status, rationale, uncertainty, planner/date and basis hashes to `work-packages.csv`.
A stale rank remains in the supplied-rank column while the current-rank cell is
blank. Formula-like text receives the existing CSV safety handling. Bundle validity
can coexist with stale planning assertions, unresolved reviews and `NOT_READY`.

## Adapter enrichment and limits

Planning decisions are an explicitly permitted enrichment of a reviewed mock
adapter protocol, alongside work/context/appraisal additions. They do not permit
editing reviewed searches, screening, reports or accepted extraction rows. Existing
receipt checks still run before planning outputs are produced.

The synthetic test journey covers adapter receipts → reviewed extractions →
guideline/development/WP links → supplied ranks → prerequisite completion → packet
and bundle. No external call, real literature, credential, payment or data upload
is involved. Planner labels and all scientific/development statements remain
unverified supplied assertions; no automatic approval or prioritization is made.

[Supplied comparison conditions](EXPERIMENT_CONDITIONS.md) add exact result-linked
model/treatment/comparator and timing metadata. Full intersecting condition rows
participate in review/planning source binding when the ledger is supplied, with
explicit scope for sibling outcomes. No causal validity is inferred.
