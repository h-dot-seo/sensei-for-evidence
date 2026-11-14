# Reviewed decision-batch application and replay

This separate application tool closes the batch workflow. It uses the same internal
simulation as [target preview](SCREENING_DECISION_BATCH_PREVIEW.md), including exact
read-only CSV comparison, sequential ordinary targets and full before/after guards.
No engine receipt schema changes. A complete separate human import review must match
the exact target; blank, stale or mismatched review fields fail without output.

## Four steps and human boundary

1. Export a [blank decision sheet](SCREENING_DECISION_SHEETS.md). A human supplies
   each intended choice and its reason, adjudicator, date, rationale, locator and
   unique decision receipt ID. This is separate from reviewer positions.
2. Run `screening_decision_batch.py target` against the original protocol and inspect
   every supplied row, source/review context and projected change. All read-only
   cells must remain exact. The preview is not an application or approval.
3. A human supplies the target's import review: receipt_id, reviewer, reviewed_at
   (`YYYY-MM-DD`) and rationale. The action must be `apply_screening_decisions` and
   target_sha256 must be unchanged. Run `assemble` to create a detached application.
4. `verify` replays the complete application against the unchanged original protocol.
   Only an exact match permits `--protocol-output` to publish a new protocol.

Import review authorizes recording the exact supplied choices, not endorsing their
scientific reasoning or authenticating reviewers. Dates do not pick winners. No
votes, consensus, reviewer-position conversion or adjudication is inferred. Never
edit hashes to rebase an old sheet/review. Any input or implementation change needs
a fresh target and review. The preview hash now includes this application module,
so previews from earlier versions intentionally require fresh review.

## Synthetic walkthrough

From the repository root, replace `OUTPUT` with an existing empty directory outside
the checkout. The checked-in sheet and review are entirely fictional human inputs
for a reproducible rehearsal. Inspect target.json before assembly. In real work,
stop there and have a human fill the review; do not reuse this synthetic review.

```sh
python screening_decision_batch.py target examples/screening-reviews.json examples/screening-decision-batch/filled.csv --output OUTPUT/target.json
python screening_decision_batch_apply.py assemble examples/screening-reviews.json examples/screening-decision-batch/filled.csv examples/screening-decision-batch/import-review.json --output OUTPUT/application.json
python screening_decision_batch_apply.py verify examples/screening-reviews.json OUTPUT/application.json --protocol-output OUTPUT/protocol.json
```

The final verification report is JSON on stdout. `verify --output REPORT.json`
can instead save only the report. `--output` and `--protocol-output` are mutually
exclusive: there is at most one new destination per command. Assembly requires an
explicit application output and cannot directly export a protocol.

## Preservation, provenance and replay

The original protocol/file remains untouched. The detached candidate changes only
explicitly supplied canonical decision/reason rows and appends ordinary receipts,
preserving existing history prefixes, reviewer positions and every other field.
A late-step evidence/report guard failure rejects the whole assembly without output.

The application retains exact raw CSV bytes (base64), byte hash/spans, full target,
separate import review, implementation hashes and candidate. Verify reconstructs
all of it and compares exact canonical JSON, not just selected hashes. Raw CSV byte
changes still matter, including BOM/newlines. JSON object order is immaterial;
list order and supplied values are retained. Keep the detached application alongside
the new protocol: native receipts alone do not retain the separate batch import
review. Import receipt IDs are detached labels, not a globally checked registry.
Unsigned records are not authentication; consistently reauthored inputs can replay.

## Limits and complete exclusive publication

The preview's 100-row cap, existing 1,000-decision lifetime cap, full guards and
cumulative target budget are unchanged. Protocol/application limits are 50 MB,
CSV/review limits 10 MB, with serialized output limits checked before publication.
The whole application may exceed its limit even if the separate preview fits;
reduce batch size rather than discard provenance.

Each output is written and flushed to a temporary file in the destination directory,
closed, then published through an exclusive hard link. An existing file, directory
or final symlink is never replaced. Writing or linking failure before publication
leaves no new final output; temporary cleanup is attempted in all cases. Filesystems
without hard-link support fail closed. This requires no Windows symlink privilege.
A cleanup failure after publication can leave a complete final output and a temporary
file, and an stdout failure after protocol publication can report an error despite
a complete new protocol. Check the outcome before retrying. This is not an
ancestor-path race security guarantee or a multi-file transaction. Keep real
sheets, abstracts, reviews and applications outside this public repository.
