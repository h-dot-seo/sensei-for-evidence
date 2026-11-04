# Compare supplied completion assertions across protocol snapshots

A stale completion hash does not say which supplied fields changed. The
`completion_work_impact` view in `compare_runs.py` compares the existing work and
completion ledgers alongside the work/source bases recomputed from two supplied
protocol snapshots. It needs no amendment note and does not reconstruct the
original acceptance review from a hash.

```sh
python compare_runs.py examples/completion-binding.json examples/completion-amendment.json
python work_review.py examples/completion-amendment.json --work-package WP-TRANSLATION --include-prerequisites --brief
```

The entirely synthetic amendment changes the mechanism work's acceptance
criterion and artifact locator, a result limitation and a linked development
context version. It retains the supplied COMPLETE status and old completion
hash. The mechanism assertion therefore becomes STALE_SOURCE. The dependent
translation work remains NOT_COMPLETE, with source-basis changes and a changed
direct-prerequisite source label visible separately. No source or artifact is
opened, no completion is renewed and no scientific implication is inferred.

## What the focused view reports

`completion_work_impact.work_packages` includes every exact work ID appearing in
either input, sorted by ID. It provides:

- Before/after snapshots of the normalized work assertion, existing completion
  review, and compact direct-prerequisite completion-source rows.
- Changed work field names and changed completion-basis field names. The work's
  own literal artifact locator is separate from its work/source-basis hash.
- `work_source_changes.changed_sections`, identifying which existing planning
  basis sections differ. The view does not invent a new source-binding scope.
- Exact shared source field names, own work-scope field names, and added/removed/
  changed entity IDs and field names for direct dependency scopes, linked
  evidence, context, appraisals, experimental units and explicit rationale
  statements. The original input snapshots retain the full supplied values.
- Added/removed/changed direct-prerequisite completion rows, their before/after
  ID order and an order-change flag, separate from the dependent's own basis
  changes. The flag compares whole ID lists, so additions/removals also change it.
  These rows contain supplied status and source label only, not recursive
  acceptance certificates.

An optional external amendment note still binds only the exact input snapshots
and declared top-level change scope under the existing
[amendment-note contract](AMENDMENT_NOTES.md). It does not approve these changes.
The comparison view is available whether the note is absent, matching or
mismatched. The full entity comparison remains available too.

## Interpreting the cues

- RECOMPUTED_COMPLETION_BASIS_CHANGED means the two currently computed bases
  differ. It does not identify the original human acceptance basis from history.
- COMPLETION_SOURCE_LABEL_CHANGED records a literal status transition such as
  CURRENT_SOURCE to STALE_SOURCE, not its scientific significance.
- RECORDED_WORK_STATE_CHANGED and SUPPLIED_COMPLETION_FIELDS_CHANGED distinguish
  progress/blocking changes from supplied artifact, acceptance or hash fields.
- RECORDED_COMPLETE_STATUS_RETAINED_AFTER_BASIS_CHANGE means only that both
  supplied work statuses still say COMPLETE. The supplied hash might also have
  changed; neither retained status nor a new hash proves actual reassessment.
- DIRECT_PREREQUISITE_COMPLETION_ROWS_CHANGED does not imply that the dependent
  basis changed. For example, a direct prerequisite's own locator can stale its
  completion binding while the dependent's existing source basis stays unchanged.
- WORK_ADDED and WORK_REMOVED retain the one available snapshot. Two-sided basis
  field/details outputs are null, rather than implying an unchanged empty basis.

An already-stale assertion compared with itself has no new change cues and still
shows STALE_SOURCE on both sides. No cues does not mean acceptance, completeness
or an absence of earlier changes. Unfinished work has computed review targets but
does not acquire a completion assertion merely by being compared.

## Scope and limits

Both snapshots use the current engine, not historical engine replay. Basis
sections use the existing [planning scope](PLANNING_ASSERTIONS.md) and
[completion binding](COMPLETION_BINDING.md): shared question/search/screening/
report context, directly linked evidence and review metadata, and direct
dependency work scopes. Source-review work retains its documented result-ID
inventory scope, not implicitly linked result contents. Optional experimental
and rationale sections retain their existing boundaries. Lists retain their
order under the existing hash rules.

Progress fields and prerequisite artifact locators remain excluded from the
dependent work/source basis; the dependent's own locator is bound separately.
Unrelated context, statements and work are not added implicitly. Existing
positional-work-ID warnings apply: use explicit stable IDs before interpreting
longitudinal identity. Added or removed fields and literal-label differences
are not causal explanations or materiality judgments.

`change_significance` remains NOT_ASSESSED and `acceptance_assessment` remains
NOT_PERFORMED. No hash is automatically renewed, work reopened, dependency
bypassed, priority generated, clinical/research decision made or artifact bytes
verified. Census and conclusion readiness stay NOT_ESTABLISHED and NOT_READY.
This standalone comparison is not added to the portable bundle.
