# Link existing contexts to named work without renewing completion

`work_context_intake.py` provides a separate exact-input review for adding explicitly
selected existing context IDs to existing work. It never chooses relevant contexts,
creates work, determines clinical applicability or accepts a development milestone.

This completes the connection after [unassigned context intake](MANUAL_CONTEXT_INTAKE.md).
Unlike context import, assignment changes a selected work's source basis and can
also change the bases of its direct dependents. The target exposes these differences
before a human supplies the review. Existing ranks, completion assertions and
stored hashes are preserved, even when their derived source-match labels become stale.

## Synthetic eight-command continuation

First finish the [context-intake rehearsal](MANUAL_CONTEXT_INTAKE.md), preserving its
`OUTPUT/with-contexts.json` and other originals. Use the same existing output directory
outside this repository. The new operations start from that actual endpoint:

```sh
python work_context_intake.py template OUTPUT/with-contexts.json examples/work-context-references.json --candidate-output OUTPUT/work-context-draft.json
python work_context_intake.py target OUTPUT/with-contexts.json examples/manual-work-context-assignments.json --output OUTPUT/work-context-target.json
```

The template copies selected explicit work IDs only. Context selections stay null.
The separate available-context catalog contains **all** supplied contexts, including
possibly incompatible ones; it is neither a compatibility filter nor a recommendation.
Keep the unfinished draft separate from the completed synthetic assignment.

Inspect the target's selected work/context snapshots, changed_work_source_targets
and derived_source_status_changes. Copy its blank review_document to
`OUTPUT/work-context-review.json`, retain schema/hash and explicitly supply receipt_id,
reviewer, reviewed_at, rationale and `decision: "append_work_contexts"`.

```sh
python work_context_intake.py assemble OUTPUT/with-contexts.json examples/manual-work-context-assignments.json OUTPUT/work-context-review.json --output OUTPUT/work-context-application.json
python work_context_intake.py verify OUTPUT/with-contexts.json OUTPUT/work-context-application.json --protocol-output OUTPUT/with-work-context.json
python work_review.py OUTPUT/with-work-context.json --work-package WP-GUIDELINE-SOURCES --text
python prisma_audit.py OUTPUT/with-work-context.json --text
python research_bundle.py create OUTPUT/with-work-context.json OUTPUT/work-context-research.zip
python research_bundle.py verify OUTPUT/work-context-research.zip
```

The supplied guideline context appends to WP-GUIDELINE-SOURCES. Its pending context
review status remains pending. WP-DEVELOPMENT-SOURCES is a direct dependent: its
source basis changes, but the context is **not** assigned to it. Neither task is
completed or started. The other newly imported development context stays unassigned.
Search gaps, screening, evidence/study counts and existing context rows are unchanged.

## Explicit assignment rules

Reference JSON has exactly schema_version 1 and a nonempty unique work_package_ids
list. Candidate JSON has exactly schema_version 1 and assignments, a nonempty list
of at most 100 rows. Each row has exactly:

- work_package_id: an existing **raw explicit** work ID.
- context_ids: 1–100 unique, existing, nonblank exact IDs not already on that work.

Each work may appear only once per candidate batch. Unknown IDs, repeated/no-op
links, replacement/removal requests and extra fields are rejected. Positional
fallback IDs are deliberately unsupported. An explicitly stored ID such as WP-001
is valid; the same text derived from an unnamed gap is not silently materialized.

Selected IDs append in supplied order to the old context_ids prefix. Existing
ordering is retained. Absent versus explicitly empty old fields remain distinguishable
in before snapshots and replay. No context itself is altered or created.

The unchanged engine enforces scope:

- An evidence context must share at least one exact result ID with its target work.
- A source context requires source-review work and at least one identical typed
  planned-search or record reference. Search membership is not identity inheritance.
- Partial overlap is structurally allowed. It does not imply all context sources
  were reviewed, or the full context is scientifically/clinically applicable.

## Changed bases, preserved assertions

The exact target binds the full original, ordered assignments, implementation bytes,
selected raw/normalized work and context snapshots, and before/after planning source
targets for every work whose basis changes. This includes directly dependent work
outside the explicit selection. The explicitly_selected flag distinguishes them.

All original raw fields remain unchanged except selected context-ID suffixes.
Work meanings, evidence/source IDs, dependencies, status, artifact_locator,
acceptance_verified and completion_basis_sha256 remain literal supplied assertions.
Execution order and dependency blocking stay unchanged. Context rows and own review
attribution/status, evidence, PRISMA partitions, appraisals and synthesis assertions
also remain unchanged. Context-work links, pending-context cues and unassigned
context IDs may change mechanically.

Planning and completion current bases can change while stored ranks and hashes stay
unchanged. A stale planning rank stays in its assertion but no longer participates
in the existing current-rank groups. A COMPLETE assertion can become STALE_SOURCE
while remaining COMPLETE and satisfying the existing dependency rule. This operation
does not reopen it, renew its acceptance or inspect its artifact. Direct-dependent
changes are consistency cues, not recursive approval or automatic context inheritance.

## Replay and limits

Verification replays the entire application against its actual original and
recorded implementation before exporting a new protocol. Changed inputs, altered
snapshots or inconsistent resealed output fail. No automatic rebase occurs.
Consistently rewritten unsigned assertions can replay; people, chronology, actual
source reading and clinical correctness are not authenticated.

Candidate/reference/review files are bounded at 10 MB, protocol/application at
50 MB. These caps are not hard CPU/memory limits. JSON is strict. Rendering and
encoding precede exclusive creation; existing entries and observed dangling links
are refused. No atomic path-race/ancestor-alias defense is claimed; write failure
can leave a partial new file.

No external/model call, source-path resolution, artifact access, scientific or
regulatory assessment is performed. Keep actual original/application/implementation
records separately. Ordinary research bundles retain the resulting protocol, not
this detached history, and existing work-transition archives do not yet support
this application kind. Private text is not redacted. Use only fictional fixtures
in this public repository; census and conclusion readiness remain unestablished.
