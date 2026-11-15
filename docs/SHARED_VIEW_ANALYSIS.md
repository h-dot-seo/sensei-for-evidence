# Same-call analysis reuse in composed review views

Roadmap #52 adjustment8 identified repeated engine analysis inside the operator
handoff. Search-ledger references and evidence indexes were already implemented;
this change removes a different, remaining repeated-work cost, without changing
those data contracts or expanding the meaning of any gate.

## Scope and measured work

The four non-engine modules research_status.py, synthesis_review.py, work_review.py
and review_handoff.py separate private projections from their public entry points.
A handoff computes an analysis and the optional report flow once for that invocation,
then passes them to status, work and synthesis projections. A standalone synthesis
snapshot reuses its analysis for its status queues. No result is retained for a future
call. Each public API/CLI still performs its own validation. There is no public
prevalidated-input parameter, command option, file format or process-wide cache.
Private projection functions are trusted implementation details, not supported ways
to validate a supplied or persisted analysis. Original public signatures remain.

Actual old/current instrumentation counts calls to evidence_workflow.run, not wall
clock speed. With no report stage, handoff changes from4 to1 engine executions and
snapshot from2 to1. With reports, handoff changes from8 to2 and snapshot from4 to2.
Standalone status and work packets remain1/2 respectively. The remaining second
execution is prisma_reports.report_flow's own validation, deliberately unchanged.
All ENGINE sources and their filename set are unchanged.

## Preserved boundaries

- No scientific decision, readiness gate, queue, schema2 field, ordering or source
  link is changed. Optional work selection, prerequisite options and map context retain
  their existing meaning and invalid-input channels.
- Inputs and same-call intermediate analysis are not mutated. Changing a result from
  a previous call does not contaminate the input or another invocation; changing an
  input triggers fresh validation and new protocol binding.
- Four implementation fingerprints necessarily change. Comparisons with the actual
  prior code control only those four exact source-byte hash reads; all stdout/stderr/
  exit bytes then match. Uncontrolled current output fingerprints are also checked.
  Existing historical baseline JSON remains unmodified with an exact source reversal
  for these four modules. This test mechanism is not a public replay or reseal tool.
- Bound historical artifacts may require the original implementation. No stored
  record, real human review or user protocol is rewritten to bypass that requirement.
  All fixed15 fictional targets are actually replayed; unchanged targets are left as-is.

## Limits and verification

The reduction is a deterministic execution-count observation on supplied synthetic
cases, not a general linear-complexity, CPU, memory or wall-time guarantee. Existing
wide statement/context links can still create large outputs. Input and ZIP byte/depth
limits remain where they were. No network calls, new approvals, gate policies or
library dependency are introduced.

Tests cover actual before/after engine counts, forty prior/current CLI paths (default
JSON/text, selected/unknown work, brief/prerequisite rendering, current/stale optional
map contexts and invalid inputs), public validation and unsupported-parameter refusal,
input/intermediate preservation, recursive result mutation, repeated and changed-input
calls, exact four-file changes and unchanged ENGINE/other root sources. Existing
view, map, scale-shape and guide regressions remain in the suite. These are fictional
software checks, not scientific or reviewer validation.
