# Append-only exact report-study reviewer positions

This completes the manual-copy gap in [report-study reviews](REPORT_STUDY_REVIEWS.md).
Use its existing blank template, then supply JSON candidate rows to this separate
exact-target/import-review/assembly/replay workflow. It does not choose study identity,
include or exclude a canonical membership, remove results, or infer adjudication.

## Human inputs and gates

A candidate has exactly `schema_version: 1` and `report_study_reviews: [...]`.
Every row uses the existing assertion schema. Keep the exact current pair basis;
fill review_id, report_id, study_id, reviewer, reviewed_at, decision, rationale,
reviewed_locator and the explicitly chosen reviewed_source_ids. Template human
fields, including the source subset, stay null until a human supplies them.

New rows require a currently declared exact report/study pair on a retrieved report
with source descriptors. Each selected source ID must exist on that same report.
Unknown/other-report source IDs, duplicate IDs and empty subsets fail. No implicit
'all sources' choice is made. The input order of the selected sources is retained;
labels and IDs are literal, never trimmed or combined into approximate identities.

The pair basis binds the whole report source catalog, not just the chosen subset.
Changes to even an unselected descriptor can stale it. Unrelated input changes may
leave the basis unchanged but still stale an import review, which binds the whole
protocol. Never refill old hashes or automatically renew a position. Null document
digests remain unbound; supplied non-null digests are not measured or authenticated.
Human coverage prose and differing subsets do not prove equivalent or different reading.

Old orphan and stale assertions remain unchanged. New orphan assertions are refused.
Duplicate review IDs and exact (report_id, study_id, reviewer) tuples fail; reviewer
supersession is not implemented. An exclude position on a pair with results produces
the existing comparison cue only: it never deletes results or changes membership.

## Four-step synthetic walkthrough

Run from the repository root. Replace `OUTPUT` with an existing empty directory
outside the checkout. The candidate and import review are fictional rehearsal inputs.
Inspect scaffold and target before assembly. In real work, stop to supply actual
human positions and a separate import review; do not reuse fixture assertions.

```sh
python report_study_review.py examples/report-study-reviews.json --report-id=report-one --study-id=study-A --template --output OUTPUT/scaffold.json
python report_study_review_intake.py target examples/report-study-reviews.json examples/report-study-review-intake/positions.json --output OUTPUT/target.json
python report_study_review_intake.py assemble examples/report-study-reviews.json examples/report-study-review-intake/positions.json examples/report-study-review-intake/import-review.json --output OUTPUT/application.json
python report_study_review_intake.py verify examples/report-study-reviews.json OUTPUT/application.json --protocol-output OUTPUT/protocol.json
```

Target drafts a blank separate import review. A human supplies receipt_id, reviewer,
reviewed_at and rationale, with action `import_report_study_reviews` and the unchanged
target_sha256. It authorizes recording, not endorsing study eligibility. Assembly
creates a detached application. Verify reconstructs it against the original protocol
and permits a new protocol only when the entire record matches. Canonical reports,
memberships, sources, evidence, work, counts and every old assertion stay unchanged.
Retain the application for separate import-review provenance.

## Shared safety and operational limits

A small `reviewed_intake_safety.py` helper now shares only strict import-review
validation and complete replay comparison with report-review intake. Source/pair
rules remain in their specific wrappers and existing engine validators. Both bind
the helper's bytes; older targets require their recorded implementation or fresh
review, not automatic rebasing. The older report-intake fixture is regenerated for
this version and remains regression-tested. No canonical schema or ENGINE_FILES
bytes change.

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
