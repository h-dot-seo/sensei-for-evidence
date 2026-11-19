---
name: sensei-evidence
description: Review a research question, source-linked results and counterevidence, and hand unresolved evidence gaps to planning.
---

# Evidence review

Work from the repository root and the shared protocol. Use the root SKILL.md research method and existing search, eligibility and appraisal routes. Frame the question with PICO or PECO where appropriate. Start a review with `python synthesis_review.py PROTOCOL --text`.

Return a Markdown table of question, observation, source locator, evidence IDs, interpretation and uncertainty. Record exactly which missing comparison, source or result could change the conclusion. For a gap that needs work, hand the planner the question, existing evidence IDs and expected deliverable. Preserve unknowns and competing interpretations.

When planning returns a work package, inspect the delivered source and locator and reassess the relevant statement against the evidence. Package completion alone cannot close the scientific gap.
