# Compact work review navigation

Detailed prerequisite packets preserve evidence and context, but they can be long.
`--brief` provides a compact projection of the same validated packets so an operator
can locate unfinished work, its expected deliverable and the existing review cues
before opening the detailed material. It does not choose the user's next task.

```sh
python work_review.py examples/prerequisite-review.json --work-package WP-TRANSLATION --include-prerequisites --brief
python work_review.py examples/prerequisite-review.json --work-package WP-TRANSLATION --include-prerequisites --text
python work_review.py examples/rationale-links.json --work-package WP-TRANSLATION --brief
```

`--brief` and `--text` are mutually exclusive. Without either, the existing full
JSON output is unchanged. Selection and optional prerequisite expansion use the
same validated work engine; there is no new task, stage or decision schema.

## What the operator sees

- Packet-scope groups of recorded unblocked PLANNED work, unblocked IN_PROGRESS
  work, blocked unfinished work and COMPLETE assertions. IDs within groups are
  lexically sorted, never priority-ranked. An IN_PROGRESS task can still be blocked
  by its supplied unfinished prerequisites and remains in the blocked group.
- Each packet's supplied question, deliverable, acceptance criterion, dependencies
  and blocked state, alongside artifact/acceptance assertions explicitly labeled
  as not checked. This view never opens local artifacts.
- Existing planning source-match status, human rationale and uncertainty, plus
  explicitly supplied rationale statement IDs. Stale planning is not renewed.
- Nonempty existing review cues. Missing stages are listed separately; empty cues
  are omitted from brief text without implying completeness. The Python
  `navigation_summary(result)` projection retains original null/empty values.
- Named source-review inputs and their supplied search indices and screening/report/result-ID
  stages. Source-only work is not implicitly converted into evidence-level work.
- Existing statement review/support status and supplied work-linked position
  labels, with other statement evidence IDs kept separate. Full position rationale,
  excerpts, conditions and context remain available in the detailed packets.

The synthetic prerequisite example shrinks the detailed text by more than half
in the regression test, while retaining all selected work and its deliverables.
The first receipt-note WP can be dependency-unblocked while its secondary search
is missing. A COMPLETE note can still retain source gaps. Neither state proves
scientific readiness, source completeness or acceptance of its contents.

## Scope and limitations

Groups apply only to the packets selected for display. Without prerequisite
expansion, missing prerequisite packets are disclosed rather than silently added.
The search-plan display remains explicitly protocol-wide. Group ordering does not
encode priority, recommended action, deadlines, ownership or stage advancement.
No task is generated, executed, accepted or clinically approved. The operator must
inspect sources and make the actual research-management and scientific decisions.
Census remains NOT_ESTABLISHED and conclusion readiness remains NOT_READY.
