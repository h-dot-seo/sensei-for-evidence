# Compare guideline/development context amendments with work packages

A context can retain its supplied `reviewed` label after its source version,
applicability statement or linked result changes. The existing `compare_runs.py`
now joins its mechanical comparison to explicitly context-linked work packages,
so operators need not manually cross-reference context, result and work ledgers.
It does not determine whether any amendment is clinically significant or whether
a recorded review is valid.

```sh
python work_review.py examples/translation-review.json --work-package WP-TRANSLATION --text
python compare_runs.py examples/translation-review.json examples/context-amendment.json
python work_review.py examples/context-amendment.json --work-package WP-TRANSLATION --text
```

The entirely fictional amendment changes the guideline version, access date,
population/setting and applicability text. It separately changes the development
version/stage/limitations and a linked result's limitations, retaining the old
reviewer/date/status assertion. No real guideline or development program is
queried, endorsed or advanced. Both protocols use the same current implementation
for comparison; this is not historical engine replay.

## Focused output

`context_work_impact.contexts` includes every context ID appearing in either input:

- Separate before/after snapshots of full supplied context assertions, including
  issuer/locator/version, population/setting, applicability and limitations.
  Guideline recommendation strength/certainty remain distinct from development
  stage/regulatory status. Literal field changes are listed, not interpreted.
- `date_roles` separates accessed_at from the recorded reviewed_at. Neither is a
  publication/effective date. No currency, supersession or date adequacy check is
  performed. Missing review dates remain null, not invented.
- Exact linked result rows and their added/removed/changed IDs and fields.
- Explicit context-linked WP snapshots with question, deliverable, acceptance
  criterion, dependencies, blocked state and supplied artifact/completion fields.
  Shared result IDs, other context results and other WP results are separated.
- Added/removed work links and changed linked work assertions, with the union of
  old/new explicitly linked WP IDs offered for manual comparison when a cue exists.
  An unassigned context remains unassigned; tasks are not generated.

`REVIEW_LABEL_RETAINED_AFTER_INPUT_CHANGE` means only that the same reviewed
status, reviewer and review date survived changed context or linked-result
assertions. A changed review date does not prove reassessment either.
`review_validity` stays NOT_VERIFIED and `change_significance` stays NOT_ASSESSED.
Work progress changes can produce a work-assertion cue without claiming the
source context changed. No work status, priority or acceptance is updated.

Only explicit context_ids connect work. Sharing an evidence ID is insufficient;
removed context links remain visible on the before side. Source-review work has
no implicit guideline/development linkage. Positional default WP IDs retain the
existing comparison warning; use explicit stable IDs for longitudinal tracking.

## Limits

This focused view compares context, linked result and directly context-linked
work assertions. Search/report/appraisal/experimental-condition changes remain
in the full comparison rather than being silently interpreted as context changes.
Inspect `changed_protocol_fields` and `entity_changes` as well. Missing source
retrieval, applicability appraisal and scientific validity remain unresolved.
Access dates do not establish guideline currency; supplied development labels do
not establish regulatory clearance or a stage transition. Matching snapshots are
not approval. The output is standalone and is not added to the research bundle.
