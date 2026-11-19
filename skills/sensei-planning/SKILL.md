---
name: sensei-planning
description: Turn evidence gaps into dependent work packages, deliverable and milestone tables, and Mermaid planning views.
---

# Project planning

Use the shared protocol and its existing gaps and work package IDs. Start with the research question, evidence IDs and requested deliverable from evidence review. Record purpose, scope and success criteria in a short charter. For each package agree on a deliverable and acceptance criterion. Record explicit prerequisite IDs in depends_on. Preserve source identifiers across handoffs.

From the repository root inspect a package with `python work_review.py PROTOCOL --work-package ID --text`. Generate either Mermaid view from the same workflow output:

```sh
python evidence_workflow.py PROTOCOL | python skills/sensei-planning/diagram.py wbs
python evidence_workflow.py PROTOCOL | python skills/sensei-planning/diagram.py dependencies
```

The WBS groups each work package under the project and shows its deliverable. The dependency view shows prerequisite → dependent edges. Use a milestone table for review criteria and supplied dates. Produce a Gantt only when dates or durations are supplied. Use FigJam only for a requested collaborative layout.

Return the work package ID, deliverable, supporting locator and completion status to evidence review. Keep the scientific conclusion open for reassessment.
