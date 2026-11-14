# Human review positions for exact report-study pairs

A document can contain several supplied studies. Including that report, or
recording a report-level review, does not establish eligibility of each study.
`report_study_reviews` records separate human positions on exact
`(report_id, study_id)` pairs and the document source IDs the person says they used.

This is read-only review bookkeeping, not canonical study selection. It does not
filter results, change report inclusion, infer study identity/independence, vote,
verify reading or assess scientific or clinical correctness. Checked-in inputs
are fictional; keep actual sources and generated outputs outside this public repo.

## Reproduce the fictional journey

```sh
python report_study_review.py examples/report-study-reviews.json --text
python report_study_review.py examples/report-study-reviews.json --report-id=report-one --study-id=study-B --text
python report_study_review.py examples/report-study-reviews.json --report-id=report-one --study-id=study-B --template --output /outside/new-study-review.json
python report_study_review.py examples/report-study-reviews.json --report-id=report-one --study-id=study-C --text
python prisma_audit.py examples/report-study-reviews.json --text
python review_handoff.py examples/report-study-reviews.json --text
python research_bundle.py create examples/report-study-reviews.json /outside/new-study-review-bundle.zip
python research_bundle.py verify /outside/new-study-review-bundle.zip
```

Choose a new output path in an existing directory. The CLI validates the entire
input before selection. `--study-id` requires `--report-id`; the same study ID in
a different report is a different pair. A report-only selection shows its current
and explicitly referenced orphan pair views. Unknown reports/pairs are rejected.
`--output` creates a separate JSON artifact and refuses overwrite, including the
input. `--text` changes stdout only. Locators are never opened or executed.

The example retains five reports, three currently declared report-study
memberships and two result rows. Five human positions describe four pair views:

- Report one / study A: one include position using the main source.
- Report one / study B: opposing include/exclude positions naming different sources.
- Report two / study A: an unclear position with an explicitly unbound document digest.
- Report one / study C: a retained stale assertion for a no-longer-declared pair.

Four assertions match current context, one is stale, and two current memberships
have comparison cues. The orphan view is separate from that queue. Study B's
exclude position does not delete its result or override the report decision.
A current exclude position alongside result rows produces the literal
`CURRENT_EXCLUDE_POSITION_WITH_RESULT_ROWS` cue. It is navigation for human review,
not an invalid-result verdict, canonical exclusion or instruction to remove data.
The study-A opinion in one report does not clear the other report's review gap.
The same source IDs or equal source sets do not prove equivalent reviewed coverage.

## Supply an explicit human record

Each `report_study_reviews` row has exactly these fields:

```json
{
  "review_id": "a-stable-supplied-review-id",
  "report_id": "an-exact-report-id",
  "study_id": "an-exact-supplied-study-id",
  "reviewer": "a-supplied-reviewer-label",
  "reviewed_at": "2026-11-04",
  "decision": "unclear",
  "rationale": "The source leaves this study's criterion unresolved.",
  "reviewed_locator": "The section and extent actually reviewed.",
  "reviewed_source_ids": ["a-source-id-declared-for-this-report"],
  "source_basis_sha256": "the-exact-pair-target-actually-reviewed"
}
```

The placeholder hash is deliberately invalid. Actual hashes require 64 lowercase
hexadecimal characters. Scalar fields are nonblank literal strings; dates must be
real `YYYY-MM-DD` dates and positions `include`, `exclude` or `unclear`.
`reviewed_source_ids` is a nonempty list of unique literal source IDs, chosen by a
person. IDs are not trimmed, case-folded or concatenated for identity matching.
Duplicate review IDs and duplicate exact `(report_id, study_id, reviewer)` tuples
are rejected. One active assertion per exact tuple is supported, not authenticated
people or independent review. Preserve snapshots before replacing assertions.

1. Inspect the pair and its current declared membership, report source context and
   supplied results. Result presence is not proof of study eligibility.
2. Ensure the report has honest `report_sources` declarations. Missing descriptors
   produce `source_first_memberships` guidance, not invented sources or review rows.
   Use the [report source workflow](REPORT_REVIEWS.md) to supply them first.
3. Generate a blank pair-specific template. Only report ID, study ID and source
   hash are filled; reviewer, date, position, rationale, location and
   `reviewed_source_ids` remain null. The tool never chooses all sources for a person.
4. After human review, fill the fields. The separate
   [append-only intake](REPORT_STUDY_REVIEW_INTAKE.md) records completed rows via
   exact import review and replay, without manual protocol editing. Do not copy a fresh hash merely to erase a
   stale cue. Existing human fields and hashes remain visible but are not renewed.

Templates are available only for current memberships on retrieved reports with
at least one source descriptor. A null document digest remains unbound, and every
nonnull document digest is still a supplied claim rather than measured bytes.
Pending, unavailable and orphan pairs receive no new review scaffold.

## Keep source context and selected documents distinct

The pair source basis binds schema/scope, exact report/study IDs, the existing
report-source basis hash and whether the pair is currently declared. That report
hash binds question/criteria, mapped record provenance, retrieval/locator and the
whole ordered report-source descriptor catalog. Catalogs are shared once rather
than copied into every study target.

`reviewed_source_ids` separately states the human-selected subset. It does not
change what the context hash means. Adding or changing even an unselected source
can conservatively stale a review. Changing the selected subset is a change to the
supplied assertion, not a verified new reading. `reviewed_locator` retains page,
section and scope in prose; no document parser checks it. Different literal source
sets are shown, never interpreted as scientific disagreement or coverage quality.

Membership pointers, sibling study IDs/order, results, work, reviewer assertions
and protocol-version labels are outside the pair basis. Scalar-to-singleton
migration and reordering retain an unchanged pair hash. Criteria, source metadata
or mapped provenance changes stale it. Removing a membership changes the presence
flag. Losing report inclusion also removes its active memberships under the current
schema, even though the older report-review source hash excludes canonical report
decisions. These two hash scopes intentionally answer different questions.

Hashes are not signatures, proof of reading, source authenticity, correct study
identity or verified eligibility. `CURRENT_SOURCE` means supplied hash equality
only. The separate canonical report decision is displayed as context and is never
compared with a study opinion as agreement between the same units.

## Retain unresolved assertions without inventing history

If a declared study or selected source disappears, an old assertion can remain
stale. A no-longer-declared pair has a null membership pointer and an explicit
`MEMBERSHIP_NOT_CURRENTLY_DECLARED` cue. Missing source selections appear in
`unresolved_reviewed_source_ids` with `UNRESOLVED_REVIEWED_SOURCE_IDS`.

These are unverified supplied orphan records, not proof that the pair/source was
previously valid. They do not create memberships, eligible studies or extraction
requirements. Known report IDs are still required; when removing an entire report,
retain the prior protocol/bundle rather than inventing a replacement report.

Validation prevents a stale hash from silently legitimizing a current claim:

- A matching pair hash requires a currently declared membership and existing
  selected source IDs belonging to that report.
- A matching hash for an orphan target is rejected.
- A currently known source ID assigned to another report is always rejected,
  including in stale assertions. It is never rebound by similarity or old labels.
- Unknown/deleted selected source IDs are retained only with a stale hash.

A supplied study ID and page/section description do not verify that the document
actually describes that study or that it is independent from another supplied ID.
Dates never choose a winner. Stale positions remain visible but are excluded from
current-position comparisons. Orphan assertions have their own retrospective
summary and are not added to current-membership review queues. Preserve full
protocol snapshots when historical reconstruction matters; these rows alone do
not authenticate a complete timeline.

## Counts, compatibility and the remaining review-scope gap

The optional `report_study_review` view appears in core/report/audit/synthesis
exports. Status and handoff add `study_memberships_with_review_cues` for current
pairs, exact report/source/review/result pointers and a detailed read-only view.
`pair_views` includes current and explicitly referenced orphan pairs;
`current_memberships` counts actual declarations and `orphan_pair_views` counts
unresolved pair views, not historical or eligible studies.

Comparison adds optional `report_study_review_changes` with exact pair keys and
before/after assertions, targets and cues. Renamed IDs are not inferred to be the
same study. Two matching labels are not consensus, and empty cues do not prove
complete reading, scientific quality, verified bytes or eligibility correctness.

Existing record/report/study counts, result rows, extraction queues and CSV bytes
remain unchanged by these opinions. In particular, legacy `included_studies`
still counts distinct supplied IDs on included reports, not canonically selected
studies. `study_eligibility_assessment: NOT_PERFORMED` keeps its existing meaning:
no engine/canonical assessment occurs. Separately supplied human positions do not
change that flag. `canonical_study_selection` remains `NOT_MODELED`.

This increment is post-inclusion bookkeeping. The existing schema permits plural
study memberships only on included retrieved reports. Do not mark a report included
just to obtain study-review templates. The separate descriptive inventory below
now has a separate [candidate-review scope](INVENTORY_CANDIDATE_REVIEWS.md),
without canonical per-study selection or result filtering. This membership-review
scope and its hashes remain unchanged.

Omitting `report_study_reviews` preserves legacy projection shapes. `[]` opts in;
null is invalid. Empty opt-in without reports is allowed, while nonempty rows
require known reports. The key is reserved enrichment in CSV-import histories.
Bundles retain raw assertions and helper fingerprints within the unchanged
seven-file format; they do not archive full text or verify document bytes.

The separate [descriptive candidate inventory](REPORT_STUDY_INVENTORY.md) now
records source-linked descriptions before full-text inclusion. It intentionally
does not migrate this review scope or enable fresh review scaffolds for undeclared
memberships. Its hash excludes membership presence; never interchange the hashes.
