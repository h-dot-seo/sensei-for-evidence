# Append-only full-text reviewer-position intake

The existing [report review template](REPORT_REVIEWS.md) supplies blank assertions,
but recording them previously required hand-editing `report_reviews` in a protocol.
This wrapper closes that gap with exact target, separate import review, detached
assembly and full replay. It does not duplicate the existing template, read source
files, add source descriptors, supersede reviewers or write canonical report decisions.
CSV export/import is outside this increment; supplied positions use strict JSON.

## Four stages

1. Use `report_review.py --template` for retrieved reports with supplied source
   descriptors. A human fills the blank fields after actual review. Put only the
   completed rows into a candidate object with exactly `schema_version: 1` and
   `report_reviews: [...]`, not the entire template view or working protocol.
2. `report_review_intake.py target` validates the original and proposed append,
   exposing exact source targets and before/after review cues. It drafts a blank
   import review, not approval. Every new source_basis_sha256 must match the current
   supplied source context; no old hash is filled or refreshed automatically.
3. A separate human supplies import receipt_id, reviewer, reviewed_at (`YYYY-MM-DD`)
   and rationale for action `import_report_reviews` and the exact target_sha256.
   `assemble` creates only a detached application.
4. `verify` replays against the unchanged original protocol. Only full agreement
   permits `--protocol-output` to publish a new protocol with the appended rows.

Positions may be `include`, `exclude` or `unclear`; no vote or canonical decision
is inferred. Existing IDs and exact (report_id, reviewer) pairs cannot recur.
Reviewer supersession is not implemented. Existing stale assertions remain unchanged.

## Source limitations

New positions require `retrieval=retrieved` and at least one supplied descriptor.
Pending/unavailable reports and reports without descriptors fail closed even if a
syntactically valid basis hash is supplied. Use the separate source-declaration and
retrieval workflows first, then obtain a fresh review target. Nothing in this tool
retrieves a report or makes it available.

Null document digests are allowed but remain visibly `DOCUMENT_BYTES_UNBOUND`.
Non-null digests are supplied assertions, never measured or verified here. Locators
are inert and never hashed as document bytes, opened or fetched. `reviewed_locator`
is human coverage prose, not a verified source subset. Matching context does not
establish reading, identical coverage, source authenticity or reviewer identity.
An unrelated protocol edit can leave a position's source basis unchanged, but it
still invalidates an existing import review because that review binds the whole input.

## Synthetic walkthrough

From the repository root, replace `OUTPUT` with an existing empty directory outside
the checkout. The candidate and import-review fixtures are entirely fictional.
Inspect the blank scaffold and proposed target before assembly. For real work stop
and supply human assertions and separate review; do not reuse these fixture choices.

```sh
python report_review.py examples/report-reviews.json --report-id=report-one --template --output OUTPUT/scaffold.json
python report_review_intake.py target examples/report-reviews.json examples/report-review-intake/positions.json --output OUTPUT/target.json
python report_review_intake.py assemble examples/report-reviews.json examples/report-review-intake/positions.json examples/report-review-intake/import-review.json --output OUTPUT/application.json
python report_review_intake.py verify examples/report-reviews.json OUTPUT/application.json --protocol-output OUTPUT/protocol.json
```

The final verification report is JSON on stdout. `verify --output REPORT.json`
saves only a report instead. The two output options are mutually exclusive.
The original protocol and all old assertions remain byte-for-byte untouched as
files; within the new candidate, every raw field except the appended review suffix
is preserved. Canonical reports, report_sources, memberships, evidence and counts
do not change. Retain the detached application for the separate import review.

## Replay, limits and output safety

The target/application bind canonical JSON hashes of the original and candidate
rows, selected source snapshots, review cues, separate import review and implementation.
Object key order is ignored; list order and literal values remain significant.
Replay compares the whole reconstructed application, not a few recorded hashes.
Import approval records recording intent only, not scientific endorsement. Detached
import IDs are labels rather than a globally verified registry. Consistently
reauthored unsigned records can replay; hashes are not signatures or chronology.

At most 100 complete candidate positions, 10 MB candidate/review JSON and 50 MB
protocol/target/application. Selected source snapshot bytes are capped before
retaining another copy; the complete target/application is checked again afterward.
The entire original and candidate are validated, not just selected reports. Existing
source/canonical schemas and engine validators remain unchanged.

New intake outputs reuse complete-file exclusive publication: write/flush/close a
same-directory temporary file, then publish by hard link without replacement.
Existing entries and missing parents fail; unsupported hard-link filesystems fail
closed. At most one final output is written per command. A failure before publication
leaves no new final file, with temporary cleanup attempted. Cleanup or stdout failure
after publication may leave a complete output, so inspect before retrying. This is
not an ancestor-race security boundary. The existing template retains its original
exclusive-write semantics. Keep real sources, assertions and applications outside
this public repository; no network/model call or scientific readiness is asserted.
