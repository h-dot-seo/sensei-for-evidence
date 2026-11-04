# Operator handoff: one review entry point

## The practical gap

The fictional claim-comparison fixture contains conditions, n/statistics,
opposing supplied claim positions, guideline/development context and dependent
work deliverables. Previously an operator had to run three views and reconcile
queue IDs, source sections and work scope by hand. The new `review_handoff.py`
reuses these tools to give one read-only navigation sheet. It adds no scientific
schema, conclusion generator, external search client or alternate bundle engine.

## Reproduce the journey

Run from the repository root with Python 3.10+. These commands use only the
fictional checked-in fixture; they do not download papers or call models.

```sh
python review_handoff.py examples/claim-comparison.json --work-package WP-TRANSLATION --text
python search_manifest.py examples/claim-comparison.json
python prisma_audit.py examples/claim-comparison.json
python research_status.py examples/claim-comparison.json --text
python synthesis_review.py examples/claim-comparison.json --text
python work_review.py examples/claim-comparison.json --work-package WP-TRANSLATION --text
python research_bundle.py create examples/claim-comparison.json ../fictional-claim-review.zip
python research_bundle.py verify ../fictional-claim-review.zip
```

The ZIP path must not exist. Choose your own new output path outside the public
repository. The handoff command writes only stdout, in JSON by default or plain
text with `--text`. It does not write files, modify the protocol, execute its
listed detailed-view commands, start work or renew reviews. If you redirect the
handoff output, use a new file outside the repository and remember that shell
redirection may overwrite an existing file. Saved handoff text/JSON is a separate
artifact: bundle verification does not authenticate or verify it. Bundle outputs
remain the existing deterministic seven-file format.

The example should still show a missing planned search, pending report/screening
work, missing extraction/appraisal inputs, statistical/n reporting cues, stale
claim/planning reviews and blocked translation work. Verification succeeds only
for internal hashes and deterministic derivation, while census stays
NOT_ESTABLISHED and conclusion readiness stays NOT_READY.

## How to use the handoff

1. Read the record/result counts separately from report/study counts. These are
   supplied IDs and bookkeeping counts, not independent sample sizes.
2. For each nonempty queue, use the exact item IDs, input sections and matching
   row pointers to locate supplied data. `/experimental_units/0`, for example,
   means the first row of the protocol's experimental_units array. Pointers are
   navigation aids, not source locators or verification that the source is true.
   Matching rows may include a record's multiple search occurrences or related
   rows. Missing rows remain visible through section pointers and item IDs.
3. Read the operator instruction. It tells you which work must be done outside
   this tool: source retrieval, eligibility, extraction, applicability/appraisal,
   claim interpretation, or deliverable review. It is not a recommendation to
   manufacture missing data or declare every optional stage required.
4. Inspect the selected WP's deliverable, acceptance criterion, prerequisites,
   supplied rank and uncertainty, guideline/development limitations and exact
   claim positions. The full statement's review status includes other cited
   results; selected positions never imply a WP-specific endorsement.
5. Use the search manifest JSON view for exact query specifications, source-wise
   receipt limits and overlap. Use the PRISMA audit JSON view for member-level record/report/study accounting
   and exact exclusion/unavailable reasons. Use other detailed-view argument arrays
   for full source, condition, n, statistical,
   appraisal and claim trace. Replace the `PROTOCOL.json` placeholder with your
   actual path. Arrays are not copy-paste shell commands and are never executed
   automatically. Quote paths for your own shell when typing commands.
6. After a person actually reviews or changes source data, edit a separate
   working protocol under your own controls and rerun the views. A target hash
   is a source-match value, not scientific approval; never copy it merely to
   clear a stale-review queue. Work artifact acceptance is not inspected here.

## Scope and manual limits

All queues remain **protocol-wide**, including when one WP is selected. Selecting
WP-TRANSLATION filters the work summaries, not the census or review queues. The
sheet labels both scopes explicitly. Existing work dependencies and planning
assertions are reused without reprioritization. Queue display order is navigation,
not importance or an executable task order. Completed work is a supplied
assertion, not a verified finished artifact.

Each JSON step distinguishes NOT_SUPPLIED (null items), RECORDED_ITEMS and
NO_RECORDED_ITEMS. Plain text omits the last group to reduce noise; no recorded
items does not establish complete extraction, valid evidence or finished work.
An absent optional stage calls for a human scope decision. Unknown and unavailable
source data can legitimately stay unresolved. Uncited results and absent appraisal
are not automatically omission or quality failures.

Source inputs and implementation hashes identify which supplied data and code
produced the handoff, not who authored or approved it. Claim positions, excerpts,
review labels and guideline dates are unverified assertions. External retrieval,
full-text reading, guideline currency, scientific appraisal, causality, effect
validity, actual WP execution and independent acceptance remain manual or
unimplemented. This is an operator report, not a publication-ready evidence
synthesis or clinical decision.

## CLI failure behavior and tests

The full input is validated before any report is printed. Invalid JSON, invalid
linked data or an unknown work ID exits nonzero without a partial stdout report.
The optional missing search plan may be explicitly null, matching existing tool
semantics. Input row navigation uses queue-specific ID namespaces, not arbitrary ID fields.
Incomplete searches use authoritative search indices even when optional search IDs
are missing or duplicated. Legacy effective evidence IDs and autogenerated WP IDs
map to their original rows; report IDs are never mistaken for result IDs.
Generated work-selection arguments use --work-package=ID so leading-dash IDs remain
valid argument values.

The synthetic E2E test runs status, synthesis, selected WP, handoff text/JSON,
bundle create and bundle verify as actual subprocesses, using an input path with
spaces. It checks input bytes remain unchanged and no extra files are produced.
No real literature, model inference or scientific validity is tested.

The handoff also lists a separate [manual receipt-entry workflow](RECEIPT_INTAKE.md)
with BASE_PROTOCOL.json and FILLED_MOCK_RECEIPTS.json placeholders. This is not a
command to re-import over the current protocol. It requires a separate base, makes
no approvals, and can save only a new unreviewed candidate file.

With a selected WP, `prerequisite_review_view` suggests the existing work_review
command with `--include-prerequisites`. It is an argument array, never executed by
the handoff. See [prerequisite review](PREREQUISITE_REVIEW.md) for scope boundaries.

Opt-in [screening reviewer assertions](SCREENING_REVIEWS.md) add a protocol-wide
record queue and a detailed `screening_review.py` view. Navigation identifies the
original reviewer, canonical screening and search rows. A missing/current/stale
or differing position is a manual review cue, not an automatic eligibility
decision or a new work dependency. Review labels do not authenticate a person,
establish independent screening or verify a medical fact.
