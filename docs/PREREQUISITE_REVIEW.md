# Review a work package together with its prerequisites

A selected work packet previously showed only brief direct-dependency assertions.
An operator had to open each prerequisite separately to see its source gaps,
experimental reporting limits, guideline/development context and recorded planning
rationale. The opt-in `--include-prerequisites` flag reuses the existing packet
engine to show the entire explicit prerequisite chain in one command.

```sh
python review_handoff.py examples/prerequisite-review.json --work-package WP-TRANSLATION --text
python work_review.py examples/prerequisite-review.json --work-package WP-TRANSLATION --include-prerequisites --text
python work_review.py examples/prerequisite-review.json --work-package WP-TRANSLATION --include-prerequisites
```

The handoff provides a nonexecuted argument-array suggestion for the expanded view
when a work package is selected. With no selector it provides null. No new task,
decision, acceptance or research schema is introduced.

## Fictional research-management journey

The example connects four explicitly supplied work packages:

1. Receipt review: planned searches, including the missing secondary search.
2. Extraction review: a named source record and its existing result-ID inventory,
   without treating source-only work as linked extracted evidence.
3. Mechanism uncertainty review: existing synthetic results, condition/sampling/
   statistics reporting, development context and appraisal gaps.
4. Translation review: existing guideline/development assertions and applicability
   limits alongside its deliverable, acceptance criterion and dependencies.

Each packet retains its existing supplied planning rank, rationale, uncertainty
and source-match status. The earlier mechanism/translation ranks are deliberately
stale after the dependency changes; the tool does not renew or reinterpret them.
It does not create a scientific decision record from a priority assertion. All
actual scientific, clinical, regulatory and acceptance decisions remain human work.

## Selection and order

The flag requires one exact work-package selector. It expands only the transitive
`depends_on` links and includes the selected work itself. Shared evidence,
context, supplied priorities and downstream dependents do not add work. Completed
prerequisites remain visible, including their supplied artifact assertions.

Packets appear in the existing validated dependency-first traversal order. This
is neither a recommended priority order nor proof that work may scientifically
proceed. Ties/independent branches follow existing input traversal; they are not
ranked or optimized. Direct `blocked_by` retains its existing meaning: an unfinished
recorded prerequisite, not a scientific blocker assessment.

`dependency_review` records packet IDs, explicit edges, whether prerequisite
packets are included, omitted direct prerequisites and order/boundary text.
Without the flag, selected-only/lexical default selection stays unchanged and
omitted direct packets are disclosed. All validation still covers the whole
protocol, including work outside the selection. Cycle/missing-dependency guards
are unchanged. Traversal is iterative and shared prerequisites are included once.

Evidence counts and uncertainties stay scoped to each packet. A result repeated
across several packets is not several independent observations; no aggregate
scientific count is computed. Full-context/global search and rank summaries stay
labeled protocol-wide. Completing a supplied source-note task can remove a
recorded work block while missing searches, uncertain appraisal and clinical
applicability remain unresolved. No work is executed, approved or reprioritized.

Add `--brief` instead of `--text` for [compact navigation](WORK_NAVIGATION.md)
through the same selected prerequisite packets. The view separates recorded
unblocked, blocked, in-progress and completed assertions without recommending
what to execute or assessing scientific readiness.

## Completion-source cues without expanding packets

Every selected packet now includes `direct_prerequisite_completion_reviews` for
its explicit direct `depends_on` links, including when those prerequisite packets
are omitted. Each row retains the prerequisite's supplied work status, existing
completion-source status and supplied/current basis hashes. The dependency edges
also carry the supplied prerequisite status and completion-source status. These
are the same [completion binding](COMPLETION_BINDING.md) labels, not a new gate.

A dependent can remain mechanically unblocked while a completed prerequisite is
UNBOUND_COMPLETION or STALE_SOURCE. The brief view and operator handoff show this
beside the selected work, without reopening work, renewing a hash or verifying
acceptance. CURRENT_SOURCE is only a match for that prerequisite's own documented
scope. It does not recursively certify earlier prerequisites. Use the expanded
packet view to inspect every explicit ancestor and its own direct links.

```sh
python work_review.py examples/completion-binding.json --work-package WP-TRANSLATION --brief
python review_handoff.py examples/completion-binding.json --work-package WP-TRANSLATION --text
```

The synthetic example shows a CURRENT_SOURCE completed prerequisite while the
selected work itself remains unfinished. Shared evidence, unrelated work and
ranks do not add prerequisite completion rows. Empty rows mean no explicit direct
links, not proven readiness; acceptance and artifact-byte checks remain separate.
