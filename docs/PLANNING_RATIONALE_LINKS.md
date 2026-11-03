# Link supplied planning rationale to hypotheses and opposing positions

Planning assertions already contain a human-supplied rank, rationale and
uncertainty. Synthesis statements already contain supplied claim text, citations,
limitations and optional supporting/challenging/unclear/not-assessed positions.
Optional `rationale_statement_ids` connects these existing records without a new
decision or hypothesis schema.

```sh
python work_review.py examples/rationale-links.json --work-package WP-TRANSLATION --include-prerequisites --text
python review_handoff.py examples/rationale-links.json --work-package WP-TRANSLATION --text
python synthesis_review.py examples/rationale-links.json --text
```

The synthetic example explicitly cites statement-1 in each planning rationale.
It preserves the supplied observation challenge and unresolved causal positions.
The fictional operator chooses the rationale and rank; the tool does not decide
whether to proceed, stop, defer, reject a hypothesis or change a development stage.
Unknown positions are not generated as automatic hold decisions.

## Optional planning field

Add a nonempty list of unique known statement IDs as `rationale_statement_ids` to
an existing planning_decisions entry. Every statement must share at least one
result ID with the referenced work package. Merely sharing a study, source record
or context is insufficient. Source-only work with no evidence cannot claim an
evidence-linked rationale through this field. Omit it when no statement link has
been supplied; an empty list, unknown ID or duplicate is rejected.

The same validated synthesis engine supplies the statement. No statement text,
position or evidence is copied into a competing input schema. No new links are
inferred from rationale wording. Legacy planning assertions without this field
keep their prior source-basis calculation and do not suddenly bind all synthesis.

## Source binding and review

A linked planning target additionally hashes the full derived statement,
including text, citations, limitations, source-match metadata, recorded review
metadata, positions and its current synthesis basis hash. Thus an amendment to
linked statement text, a recorded challenge/unknown position or a sibling result
within that statement can stale the planning rank. This is content consistency,
not proof that the original reasoning was valid or the new content is important.
Unlinked statement edits do not become planning dependencies through this field.

Use the existing planning review-target workflow to inspect changed inputs and
record a new assertion only after a human chooses to do so. Hashes are never
renewed automatically. `CURRENT_SOURCE` remains source consistency only.
Changing reviewer/date metadata may also change the linked source basis; it never
establishes genuine reassessment or scientific support.

Derived `rationale_statement_links` in the planning ledger show full statements
plus `work_evidence_ids` and `other_statement_evidence_ids`. Whole-statement
context remains visible; sibling results do not become directly linked work
results or independent votes. `rationale_support_assessment` is always
NOT_PERFORMED. A supplied challenge is not independently confirmed refutation.

Existing WP packets, operator handoff and research JSON in the seven-file bundle
preserve these links. The bundle's work CSV still contains its existing planning
fields; inspect research JSON or packets for the complete rationale citation and
position detail. The feature neither changes dependency order nor creates an
acceptance decision, clinical recommendation, regulatory determination or priority.
