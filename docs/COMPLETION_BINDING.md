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
Local artifact byte reports also show the completion-source status separately;
matching bytes cannot repair a stale completion assertion.

## Important limits

Recorded COMPLETE and dependency unblocking semantics are unchanged. A dependent
WP can therefore be mechanically unblocked while its prerequisite has an unbound
or stale completion assertion; inspect the review queues before deciding what to
do. This flag is not an automatic execution gate or recommendation. Existing
artifact checks remain opt-in and separate. No criterion, clinical applicability,
regulatory stage, evidence adequacy or scientific conclusion is validated.
