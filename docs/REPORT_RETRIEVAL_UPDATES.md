# Record supplied report retrieval updates

`report_retrieval.py` connects a previously registered, unassessed report to a
later explicitly supplied retrieval outcome. It does not retrieve documents.
A separate review binds the entire original input, proposed states and source
declarations before the candidate protocol can be exported through exact replay.

Use this after [manual report registration](MANUAL_REPORT_INTAKE.md). Do not
register the same report again to work around an earlier pending/unavailable
state. Record IDs and report IDs remain the same; no duplicate or new identity is
created. Full-text eligibility remains pending until a separate
[full-text decision](REPORT_DECISIONS.md).

## Bounded transitions

Only these transitions are supported:

- `pending` to `not_retrieved`.
- `pending` to `retrieved`.
- `not_retrieved` to `retrieved`.

The prior report must be unassessed. Same-state updates, reversals, edits to
already retrieved reports and changes to included/excluded reports are refused.
This is not a general correction or document-version-management tool. A repeated
failed attempt cannot be logged by pretending it changed the state. No event
chronology is authenticated by these editable files.

Every candidate explicitly supplies `retrieval`, `locator` and `reason`. Locator
and reason are each either nonblank text or null. Retrieved requires a locator;
not-retrieved requires a reason. When a previously unavailable report is supplied,
the human may explicitly replace its old failure reason with null. The previous
raw values remain in the original protocol and detached receipt. They are not
retained as a historical ledger inside the candidate protocol.

## Continue the synthetic registration example

First complete the registration recipe and retain its exported protocol at
`/outside/new-report-protocol.json`. Its three reports are:

- `report-A`: retrieved, pending full-text decision.
- `report-B`: not retrieved, pending full-text decision.
- `report-C`: retrieval pending, pending full-text decision.

All identifiers and assertions in this recipe are fictional. Choose new output
paths outside the public repository. An optional incomplete scaffold accepts only
explicitly selected existing report IDs:

```sh
python report_retrieval.py template /outside/new-report-protocol.json examples/retrieval-update-references.json --output /outside/new-retrieval-draft.json --text
```

Only the supplied report IDs are copied. Every retrieval/source/human field is
blank. Explicitly fill the source list or `[]`; null is not accepted as a decision
to omit sources. No prior retrieval state is copied into a new assertion.

The complete synthetic `examples/manual-retrieval-candidates.json` asserts that
report B was later supplied and report C remains unavailable after an attempt:

```sh
python report_retrieval.py target /outside/new-report-protocol.json examples/manual-retrieval-candidates.json --output /outside/new-retrieval-target.json --text
```

Inspect the original and proposed report/source contexts. Save its
`review_document` separately, then fill `receipt_id`, `reviewer`, `reviewed_at`,
`rationale` and `decision: update_retrieval`. Preserve its target hash. Review dates
must be real `YYYY-MM-DD` dates, and identities and rationale must be honestly
supplied. No reviewer independence or authority is verified.

```sh
python report_retrieval.py assemble /outside/new-report-protocol.json examples/manual-retrieval-candidates.json /outside/new-retrieval-review.json --output /outside/new-retrieval-application.json --text
python report_retrieval.py verify /outside/new-report-protocol.json /outside/new-retrieval-application.json --protocol-output /outside/new-retrieval-protocol.json --text
python prisma_audit.py /outside/new-retrieval-protocol.json --text
python research_status.py /outside/new-retrieval-protocol.json --text
python report_review.py /outside/new-retrieval-protocol.json --report-id report-B --template --text
```

The result still has six records, four included records and three sought reports.
It now has two retrieved reports, one not-retrieved report and no retrieval-pending
reports. Both retrieved reports remain unassessed. There are no included/excluded
reports, studies or results. Unavailability is not a full-text exclusion. Search
totals remain unknown and the planned follow-up search remains missing.

## Candidate and source contract

The candidate document has exactly `schema_version: 1` and `candidates`, with one
to 100 entries. Each entry contains exactly:

- `report_id`, `retrieval`, `locator`, `reason`.
- `source_declarations`, an explicit list, possibly empty.
- `updated_by`, `updated_at`, `update_note`, all supplied nonblank human metadata.

Source declarations use the existing exact descriptor schema: `source_id`,
`report_id`, `source_locator`, `document_version`, `document_sha256`. They must
belong to their candidate's report and their source IDs must be new and unique.
No previous descriptor is overwritten, even when two descriptors assert the same
bytes. Digests are null or 64 lowercase hexadecimal characters and remain
unverified. Declaring a document alongside a not-retrieved report does not change
that outcome or imply access. The separate [source-byte checker](REPORT_SOURCE_CHECK.md)
can compare an explicitly supplied file later; it does not authenticate the file
or prove it was read.

Existing source rows remain byte-equivalent as JSON values. Source declaration
order is retained. If the ledger was absent and no new sources are supplied, it
remains absent. A supplied empty ledger remains supplied and empty.

## Preserve context and expose stale review

Only the three controlled fields on selected report rows and append-only source
declarations may change. Report order, report IDs, record grouping, full-text
choices, study declarations, search/screening data, evidence, nonclinical metadata,
work, planning and all existing assertions remain unchanged. Missing decision
fields stay missing; the existing schema interprets them as pending.

Both complete protocols pass the existing validators. Malformed prior inputs and
new source IDs that conflict with retained downstream references are rejected;
old assertions are not erased to make the update work. Mock-adapter receipts lock
report declarations and those protocols are explicitly refused, as in manual
report registration. Manual and bibliographic-import paths are supported.

Retrieval, locator and document declarations contribute to report source context.
Changing that context makes previously current report reviews and study inventory
assertions stale. Original hashes, dates, reviewer positions and orphan study
assertions remain untouched. The operation does not renew a review, select a
study, resolve a disagreement or make a full-text decision. A separate new review
or assessment must be supplied through its own workflow.

## Replay and limits

Assembly creates a detached application, not a bare protocol. Verification
reconstructs the complete application from the retained original input and the
recorded implementation, then compares canonical JSON exactly. Changed input,
candidate order/content, human assertions or implementation reject an old review.
Resealing only the outer receipt does not repair a mismatch. This is consistency,
not cryptographic proof of human identity or an immutable audit log.

The receipt retains prior/proposed source contexts, selected existing report
reviews, supplied updater/reviewer metadata and before/after counts. Ordinary
bundles preserve the candidate protocol, not the original input or detached
retrieval history. Keep all three with the recorded code revision for replay.

Candidate/review inputs are limited to 10,000,000 bytes; protocols, application
records and rendered output to 50,000,000 bytes. At most 1,000 new source descriptors
are accepted per operation. Strict JSON/schema validation and serialization happen
before output creation. Outputs use final-entry inspection and exclusive creation,
including refusal of dangling final symlinks. This is not a race-proof or
parent-directory-alias boundary; a write failure may leave a partial new file.

No source locator is followed and no external call occurs. Supplied text is not
redacted. Keep real research and generated files outside the public checkout.
Counts and replay never establish census completeness, full PRISMA compliance,
extraction completeness, source authenticity, reading or scientific validity.
