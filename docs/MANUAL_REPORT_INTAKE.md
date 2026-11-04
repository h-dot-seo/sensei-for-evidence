# Register supplied reports before full-text decisions

`report_intake.py` closes the manual gap between title/abstract screening and
report-level assessment. It appends explicit human-authored report mappings and
optional document declarations through a separate exact-target review. The input
records must already have canonical `include` screening decisions and must not
be mapped to existing reports.

This is registration, not retrieval or eligibility adjudication. Every new
report's full-text decision is explicitly `pending`. No study ID, result,
nonclinical condition or scientific judgment is created. Use the existing
[full-text decision](REPORT_DECISIONS.md), [result intake](MANUAL_RESULT_INTAKE.md)
and [condition intake](MANUAL_CONDITION_INTAKE.md) steps separately afterward.

## Why record and report units stay separate

Several included records may be explicitly grouped into one report. The tool
never chooses that grouping, infers a report from a title/identifier, merges
publications or generates report IDs. One supplied record can map to at most one
report under the existing schema. A non-retrieved report is a retrieval outcome,
not a full-text exclusion. A retrieved report remains unassessed until a separate
supplied full-text choice is applied.

The fictional examples contain six enumerated records: four included, one
excluded and one unscreened. The primary search is incomplete and a planned
follow-up source is missing. Registration describes:

- `report-A`, explicitly grouping `r1` and `r2`, asserted retrieved, with one
  supplied document declaration whose byte hash is unknown.
- `report-B`, mapped to `r3`, asserted not retrieved with a supplied reason.
- `report-C`, mapped to `r4`, with retrieval pending.

These produce three sought reports, one retrieved, one not retrieved and one
retrieval-pending. No report is included/excluded and there are no studies or
results. Record counts stay unchanged. These are synthetic software-test
assertions, not actual literature or verification of acquisition.

## Draft, review and replay

Choose a new existing output directory outside the public repository. An optional
blank scaffold takes an explicit record group, not a query or automatic selection:

```sh
python report_intake.py template examples/report-intake-base.json examples/report-intake-references.json --output /outside/new-report-draft.json --text
```

The file contains one deliberately incomplete candidate. Only the supplied
`record_ids` and fixed `decision: pending` restriction are filled. Report ID,
retrieval, applicable locator/reason, source declarations and human metadata must
be supplied. `source_declarations` is null in the draft: explicitly replace it with
the actual list or `[]`, never treat the draft as accepted input.

The fully human-authored synthetic `examples/manual-report-candidates.json`
illustrates all three retrieval states. Prepare its exact review target:

```sh
python report_intake.py target examples/report-intake-base.json examples/manual-report-candidates.json --output /outside/new-report-target.json --text
```

Save the returned `review_document` as a separate JSON file. Fill its receipt ID,
reviewer, real calendar date, rationale and `decision: import_reports` only after
inspecting the exact original, supplied reports, document declarations and source
snapshots. Preserve the target hash; no decision or reviewer is chosen for you.
Then create and replay the detached application:

```sh
python report_intake.py assemble examples/report-intake-base.json examples/manual-report-candidates.json /outside/new-report-review.json --output /outside/new-report-application.json --text
python report_intake.py verify examples/report-intake-base.json /outside/new-report-application.json --protocol-output /outside/new-report-protocol.json --text
python prisma_audit.py /outside/new-report-protocol.json --text
python research_status.py /outside/new-report-protocol.json --text
python report_review.py /outside/new-report-protocol.json --report-id report-A --template --text
```

Assembly writes an application record, not a bare protocol. Protocol export is
available only after complete replay against the retained original. Changing any
original field, source/grouping/retrieval assertion, human registration field or
bound implementation changes the target. Stale reviews are rejected rather than
renewed or rebased. The receipt is editable and unsigned, not immutable history.

## Candidate contract

The top-level object contains exactly `schema_version: 1` and `candidates`, with
one to 100 entries. Each entry has exactly:

- `report`: exactly `report_id`, nonempty unique `record_ids`, `retrieval`,
  `decision`, `locator`, and `reason`. IDs and record grouping are supplied.
  `decision` must be `pending`, with no `study_id` or `study_ids` fields.
- `source_declarations`: an explicit list, possibly empty, of full existing
  `report_sources` descriptors. Each contains `source_id`, matching `report_id`,
  `source_locator`, `document_version`, and `document_sha256`.
- `registered_by`, `registered_at`, `registration_note`: nonblank supplied human
  metadata. The date must be a real `YYYY-MM-DD` calendar date.

Retrieval is explicitly `pending`, `not_retrieved`, or `retrieved`. Locator and
reason must each be nonblank text or explicit null. Retrieved requires a locator;
not-retrieved requires a reason. Those requirements do not verify the assertions.
Nulls are retained as supplied, not converted into invented source descriptions.

Every document declaration must belong to its candidate's new report. Source IDs
must be unique across the new batch and existing declarations. The document hash
is explicit null or 64 lowercase hex characters. Neither form triggers reading
or file hashing. Non-null hashes remain unverified. Descriptors can accompany
pending or not-retrieved reports without upgrading their retrieval state. Multiple
descriptors are retained without choosing a preferred version or asserting that
any document was read.

If every source list is empty and `report_sources` was absent, that stage stays
absent. An already supplied empty source ledger remains supplied and empty. An
absent report stage becomes supplied when reports are explicitly registered;
the receipt records its prior stage as absent, not a fabricated zero-count stage.

## Preservation, constraints and next steps

Only `reports` and, when provided, `report_sources` receive ordered append-only
additions. Every old raw field and existing row remains unchanged, including
screening decisions, results, nonclinical metadata, collection receipts, review
assertions, work, planning and completion assertions. The complete original and
candidate protocols undergo existing validators. Malformed prior data, report-ID
collisions, already mapped records or conflicts are rejected, never repaired.

Legacy evidence without a report ledger cannot be silently migrated by creating
pending reports: its existing results need separately reconciled included report
memberships. This command does not edit existing reports, update a pending
retrieval later, attach new versions to old reports, or replace a mapping. Those
changes require an explicit separately validated workflow; do not register a
duplicate report to bypass the existing mapping constraint.

Mock-adapter protocols are also refused: their existing receipt contract locks
report declarations into the original reviewed context. This tool does not
relax that contract, rebase its receipts or erase provenance to make an import
work. The supported registration path is supplied manual or bibliographic-import
protocols that satisfy the unchanged validators.

For a retrieved new report, prepare source-bound reviewer positions and apply an
explicit full-text decision with a supplied study declaration. Only then can
manual result intake reference that report/study/document. Nonclinical condition
intake remains another separate human-reviewed addition. The regression journey
tests this sequence with fictional, non-operational, explicitly missing condition
metadata. Registration itself supplies no experimental values or instructions.
For an explicitly selected local document and a supplied digest, the separate
[source-byte checker](REPORT_SOURCE_CHECK.md) can compare bytes without claiming
reading, authenticity or scientific support.

PRISMA partition checks account for supplied memberships, not verified publication
identity or complete searching. A second record grouped into an extracted report
does not need its own result row to make that report's result presence true.
Unknown search totals, missing sources and unassessed reports remain visible.
Census and extraction completeness remain `NOT_ESTABLISHED`; conclusions remain
`NOT_READY`.

## Replay, files and privacy

The target retains the full-input/candidate hashes, selected record source targets,
proposed report/document contexts and implementation fingerprints. Registration
metadata and review remain in the detached application; report rows and supplied
document declarations persist in the candidate protocol. Ordinary research bundles
do not embed this detached receipt or original input. Keep them and the recorded
code revision for later replay. Byte equality does not authenticate a person,
document, retrieval event, report identity or scientific claim.

Candidate/review inputs are bounded at 10,000,000 bytes, protocol/application
inputs at 50,000,000 bytes, and candidate source declarations at 1,000 in total.
JSON and rendered text output are bounded at 50,000,000 bytes. Invalid JSON,
unknown fields, type substitutions and serialization failures are rejected before
opening output. Files use final-entry inspection followed by exclusive creation,
including dangling-symlink refusal. This is not a race-proof or parent-alias
security boundary; a write failure can leave a partial new file.

No locator is followed and no external call occurs. Supplied text is not redacted.
Keep actual research and outputs outside the public checkout, and check rights and
recipient access before sharing. Only synthetic metadata is shipped here.
