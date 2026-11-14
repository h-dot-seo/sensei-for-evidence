# Append-only positions on described study candidates

This completes the manual-copy gap in [report-study reviews](INVENTORY_CANDIDATE_REVIEWS.md).
Use its existing blank template, then supply JSON candidate rows to this separate
exact-target/import-review/assembly/replay workflow. It does not choose study identity,
include or exclude a canonical membership, remove results, or infer adjudication.

## Human inputs and gates

A candidate has exactly `schema_version: 1` and `report_study_inventory_reviews: [...]`.
Every row uses the existing assertion schema. Keep the exact current pair basis;
fill review_id, report_id, study_id, reviewer, reviewed_at, decision, rationale,
reviewed_locator and both explicitly chosen reviewed_inventory_ids and reviewed_source_ids. Template human
fields, including the source subset, stay null until a human supplies them.

New rows require a currently described exact report/study pair on a retrieved report
with source descriptors, not an included membership. Pending or excluded report
eligibility is permitted. Unavailable/pending retrieval is not. Explicit
reviewed_inventory_ids must select existing descriptions for this exact pair;
reviewed_source_ids must select existing descriptors on that same report. Both
subsets are nonempty unique literal IDs and neither is inferred or required to equal
the other subset's source coverage. Input order is retained; IDs are not normalized.

The candidate-review basis binds every ordered full same-pair description, including
unselected descriptions and their recorded source hashes, plus the full report source
catalog. Changes to even an unselected same-pair description or source can stale it.
Other-pair changes can preserve this basis but still stale the separate import review,
which binds the whole protocol. Membership-review hashes are a different domain and
cannot substitute. Never refill old hashes or automatically renew a position.

Current reviews may explicitly cite stale inventory descriptions without making those
descriptions current or correct. Null document digests remain unbound; non-null digests
are not measured or authenticated. Old orphan/stale positions and inventory descriptions
remain unchanged. New orphan positions, duplicate review IDs or duplicate exact
(report_id, study_id, reviewer) tuples fail. There is no supersession. No position
changes report decisions, included memberships, canonical studies or result rows.

## Four-step synthetic walkthrough

Run from the repository root. Replace `OUTPUT` with an existing empty directory
outside the checkout. The candidate and import review are fictional rehearsal inputs.
Inspect scaffold and target before assembly. In real work, stop to supply actual
human positions and a separate import review; do not reuse fixture assertions.

```sh
python report_study_inventory_review.py examples/report-study-inventory-reviews.json --report-id=report-three --study-id=candidate-X --template --output OUTPUT/scaffold.json
python report_study_inventory_review_intake.py target examples/report-study-inventory-reviews.json examples/report-study-inventory-review-intake/positions.json --output OUTPUT/target.json
python report_study_inventory_review_intake.py assemble examples/report-study-inventory-reviews.json examples/report-study-inventory-review-intake/positions.json examples/report-study-inventory-review-intake/import-review.json --output OUTPUT/application.json
python report_study_inventory_review_intake.py verify examples/report-study-inventory-reviews.json OUTPUT/application.json --protocol-output OUTPUT/protocol.json
```

Target drafts a blank separate import review. A human supplies receipt_id, reviewer,
reviewed_at and rationale, with action `import_report_study_inventory_reviews` and the unchanged
target_sha256. It authorizes recording, not endorsing study eligibility. Assembly
creates a detached application. Verify reconstructs it against the original protocol
and permits a new protocol only when the entire record matches. Canonical reports,
memberships, sources, evidence, work, counts and every old assertion stay unchanged.
Retain the application for separate import-review provenance.

## Shared safety and operational limits

The existing `reviewed_intake_safety.py` shares strict separate import-review
validation and complete replay comparison. Domain rules stay in the wrapper and
existing engine validators. The wrapper binds helper bytes as well as its own and
all existing engine bytes. Older targets require recorded implementation or fresh
human review, never automatic rebase. No canonical schema or ENGINE_FILES bytes change.

Limits: 1–100 positions, 10 MB candidate/review JSON, 50 MB protocol/target/application.
Selected pair snapshots are budgeted, and their full report source targets are
retained once per report before final complete-record size checks. All input and
candidate validators run, not only selected-pair checks. Object-key order is ignored
for JSON hashes; list order/literal values remain significant. Hashes and detached
receipt labels do not prove identity, chronology or scientific correctness.

At most one new output per command. `verify --output REPORT.json` saves only the
report instead of a protocol; it cannot be combined with `--protocol-output`.
The shared complete-file writer flushes/closes a same-directory temporary file,
then exclusively hard-links it into place. Existing entries are never replaced,
and unsupported hard links/missing parents fail closed. Failures before publication
leave no final output; cleanup is attempted. A cleanup/stdout failure after publication
may leave a complete output, so inspect before retrying. There is no ancestor-race
security guarantee. The existing template keeps its original exclusive-write behavior.
Keep real sources, positions and applications out of this public repository. No
locator is opened; no network/model call, identity check, reading or adjudication occurs.
