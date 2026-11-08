# Review completion assertions after source or criteria changes

A supplied COMPLETE task can retain acceptance_verified: true even when its
criteria, evidence or applicability context changes. Optional
`completion_basis_sha256` on that existing gap/work entry records which work/source
scope and artifact locator the completion assertion referred to. It does not
assess whether the task was done or change its recorded status automatically.

```sh
python work_review.py examples/completion-binding.json --work-package WP-MECHANISM --text
python research_status.py examples/completion-binding.json --text
python review_handoff.py examples/completion-binding.json --text
```

The entirely synthetic example supplies one matching hash-bound completion
assertion. Guideline applicability and source completeness remain unestablished.
No artifact is opened or scientific review carried out by these commands.

## Reuse of the existing work/source scope

The completion basis hashes the existing planning review target's source/work
basis plus the work's own literal artifact_locator. That source basis includes
question/criteria/search/screening/report context, work deliverable and acceptance
criterion, direct prerequisite work scopes, linked results/context/appraisals,
intersecting experimental metadata and any explicitly linked rationale statements.
See [planning scope](PLANNING_ASSERTIONS.md) and [rationale links](PLANNING_RATIONALE_LINKS.md).
Source-only work retains its existing source/result-ID inventory scope, not all
result content. Unrelated context/statements do not become links implicitly.

The new hash field is excluded from work/progress scope to avoid hashing itself.
Legacy planning review-target hashes remain unchanged when this field is absent
or added. Rank values are not acceptance criteria. The literal artifact locator
is bound separately; its bytes, existence, authorship and history are not bound.
Dependency artifact locators/progress remain excluded by the existing planning
scope, and only direct dependency work scopes are included, not a recursive
completion certificate. A matching hash is not scientific or project approval.

## Input and review procedure

- The optional field is 64 lowercase hexadecimal characters and is allowed only
  with an explicit COMPLETE status assertion.
- Existing COMPLETE guards still require a nonempty artifact locator, exact
  acceptance_verified: true and completed prerequisites. A hash bypasses none.
- Review targets are available for unfinished work too. A human may first supply
  the intended artifact locator while work is IN_PROGRESS, inspect the existing
  completion basis in the full packet, then record completion and its basis only
  after genuinely reviewing the criteria and scope. Do not copy hashes as a way to
  assert acceptance without doing the work.
- Source/criteria amendments or a changed own locator can stale the binding.
  The tool never renews hashes or decides whether the task must be reopened.

Derived `planning.completion_ledger` labels every work entry:

- NOT_COMPLETE: no completion assertion to assess.
- UNBOUND_COMPLETION: legacy COMPLETE assertion with no supplied basis hash.
- CURRENT_SOURCE: supplied hash matches current work/source/locator metadata.
- STALE_SOURCE: supplied hash differs from that metadata.

All entries retain acceptance_assessment and artifact_content_verification as
NOT_PERFORMED. Research status/handoff queues expose unbound and stale completion
assertions; work packets and brief navigation show their separate source status.
Optional external amendment comparison includes these observed transitions.
Selected work packets, brief navigation and handoff also expose each direct
prerequisite's completion-source status even when its full packet is omitted.
These are [direct-link review cues](PREREQUISITE_REVIEW.md#completion-source-cues-without-expanding-packets),
not recursive acceptance certificates or changes to dependency blocking.
Local artifact byte reports also show the completion-source status separately;
matching bytes cannot repair a stale completion assertion.

## Important limits

Recorded COMPLETE and dependency unblocking semantics are unchanged. A dependent
WP can therefore be mechanically unblocked while its prerequisite has an unbound
or stale completion assertion; inspect the review queues before deciding what to
do. This flag is not an automatic execution gate or recommendation. Existing
artifact checks remain opt-in and separate. No criterion, clinical applicability,
regulatory stage, evidence adequacy or scientific conclusion is validated.

## Portable CSV and bundle summary

`research_bundle.py create` appends completion columns to `work-packages.csv`:

- `supplied_artifact_locator` and `supplied_acceptance_verified` retain the
  supplied assertions as CSV text. Missing fields are empty; booleans display as
  True/False. They are not independent file or acceptance checks.
- `completion_source_status`, `supplied_completion_basis_sha256` and
  `current_completion_basis_sha256` distinguish matching, stale, unbound and
  unfinished assertions. The supplied hash is empty when absent, including for
  legacy COMPLETE work; the current target is available for unfinished work too.
- `completion_acceptance_assessment` and
  `completion_artifact_content_verification` remain NOT_PERFORMED.
- `direct_prerequisite_completion_sources` is a JSON array of exact direct
  prerequisite IDs, supplied work statuses and completion-source labels, in the
  supplied dependency order. An empty array means no direct links, not readiness.
  It does not recursively certify earlier prerequisites.

Existing CSV columns retain their order. Formula-like artifact locators receive
the same conservative CSV escaping as other supplied text; original protocol and
research JSON retain their unescaped values. CSV is an export, not an input for
renewing completion hashes. No source status modifies the supplied COMPLETE or
blocked_by assertions.

The bundle summary counts unbound and stale completed work separately and keeps
nonverification and NOT_READY limits visible. A zero count is not proof that work
or science is complete. Regeneration verification detects altered CSV labels even
if an archive's file hashes were rewritten. It verifies consistency with supplied
inputs and the recorded engine, not whether the assertions are true. Existing
bundles still require their recorded implementation bytes for verification.

To locate changed fields between two supplied snapshots, use
[completion amendment comparison](COMPLETION_COMPARISON.md). It compares current
recomputed work/source sections and direct prerequisite labels; an old hash alone
cannot reconstruct the original reviewed input or establish why it changed.

## Optional document-source context

[Document-linked source work](WORK_DOCUMENT_SOURCES.md) adds explicit selected
source descriptors and whole same-report source context to opted-in work bases
and their direct dependents. Completion binding inherits those context changes
without changing recorded COMPLETE status or certifying acceptance. Legacy work
without the new field keeps its previous source scope and hash semantics.

[Reviewed work completion](WORK_COMPLETION_INTAKE.md) provides a separate exact-target
review and replay path for one existing unfinished task. It records only supplied
completion/locator/acceptance and the reviewed source binding, preserves earlier
COMPLETE assertions, and does not inspect artifacts or assess acceptance.
