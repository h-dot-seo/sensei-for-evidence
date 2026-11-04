# Supplied full-text document versions and reviewer positions

A retrieved report's locator identifies supplied context, not the exact document
bytes a person reviewed. `report_sources` and `report_reviews` keep document-version
assertions and human positions separate from canonical report eligibility. This is
a read-only review target and scaffold, not a full-text reader or decision writer.

No document is fetched, opened, parsed, authenticated or fact-checked. Supplied
SHA-256 values are not measured by this tool. All checked-in examples are fictional;
keep real/private sources and generated outputs outside this public repository.

## Reproduce the fictional review

```sh
python report_review.py examples/report-reviews.json --text
python report_review.py examples/report-reviews.json --report-id=report-one --text
python report_review.py examples/report-reviews.json --report-id=report-three --template --output /outside/new-source-scaffold.json
python report_review.py examples/report-reviews.json --report-id=report-one --template --output /outside/new-review-scaffold.json
python prisma_audit.py examples/report-reviews.json --text
python review_handoff.py examples/report-reviews.json --text
python research_bundle.py create examples/report-reviews.json /outside/new-report-review-bundle.zip
python research_bundle.py verify /outside/new-report-review-bundle.zip
```

Choose new paths in an existing local directory. `--output` writes a separate JSON
view or scaffold using exclusive creation. It refuses existing paths, including
the input. `--text` affects stdout only. Nothing changes the protocol, opens a
locator or generates a canonical eligibility judgment. The entire protocol and
all report/evidence links are validated before any `--report-id` selection.

The example has five records and five reports. Two included reports declare four
report-study memberships across three distinct supplied study IDs. Two result rows
remain attached to report one. Three reports are marked retrieved, one pending and
one unavailable; only the two included reports count as assessed. Separate reviews
show opposing current positions, an unclear position with a missing byte digest,
and a retained stale position for an unavailable report. None changes those counts.

## Declare the sources honestly

Each `report_sources` row has exactly these fields:

```json
{
  "source_id": "a-stable-supplied-document-id",
  "report_id": "an-exact-report-id",
  "source_locator": "an-inert-document-location-description",
  "document_version": "the-supplied-version-or-edition-description",
  "document_sha256": null
}
```

All fields other than the digest are nonblank literal strings. The digest must be
explicit `null` or 64 lowercase hexadecimal characters. Null means the document
bytes are unbound; a locator or version label is never converted into a byte hash.
Even a syntactically valid digest remains a supplied, unverified assertion.

Source IDs are globally unique and report IDs must exist. Multiple source IDs may
refer to one report, allowing a main document, supplements or different supplied
versions. Identical locators or hashes do not merge them. No preferred/current
version is selected, and listing several descriptors does not assert that all
files were read. Describe actual reviewed coverage in the human assertion.
`reviewed_locator` records this coverage in prose, not a validated subset of source
IDs. Two current positions can refer to different personally reviewed subsets of
the same declared catalog; matching hashes do not establish equivalent coverage.

This increment retains the current supplied descriptor set, not a document-version
archive. Preserve protocol/bundle snapshots before replacing declarations. A
source descriptor does not make an unavailable report retrieved or amend its
canonical decision. Source locators can identify external material but remain
inert text; document access, copyright and authenticity require separate handling.

## Prepare and record a human position

1. Inspect a report's target, mapped record provenance, source declarations and
   current canonical row. A matching supplied source hash is not proof of access.
2. For a retrieved report without source declarations, `--template` provides a
   blank `report_sources` row. Supply the real declaration in a separate working
   protocol, then regenerate the target. No review hash is filled prematurely.
3. For a retrieved report with at least one descriptor, the template provides a
   blank `report_reviews` row with only report ID and current source hash filled.
   A null document digest remains visibly `DOCUMENT_BYTES_UNBOUND`; the template
   does not invent or approve it. Pending/unavailable reports receive navigation
   context but no new full-text review scaffold.
4. After actual human review, supply the missing fields and copy only the completed
   assertion rows into the working protocol. Existing opinions, reviewer labels
   and dates are not copied into new scaffolds or automatically renewed.
5. A canonical full-text decision remains a separate supplied `reports` field.
   This command never applies a review, votes or changes study assignments.

Each review has exactly these fields:

```json
{
  "review_id": "a-stable-supplied-review-id",
  "report_id": "an-exact-report-id",
  "reviewer": "a-supplied-reviewer-label",
  "reviewed_at": "2026-11-04",
  "decision": "unclear",
  "rationale": "The supplied source leaves a criterion unresolved.",
  "reviewed_locator": "The page, section and extent actually reviewed.",
  "source_basis_sha256": "the-exact-source-target-actually-reviewed"
}
```

The displayed hash placeholder is deliberately invalid. Actual source hashes
require 64 lowercase hex characters. Dates must be real `YYYY-MM-DD` dates;
positions are `include`, `exclude` or `unclear`. All fields are nonblank literal
strings. Unknown fields, unknown reports, duplicate review IDs and duplicate exact
`(report_id, reviewer)` pairs are rejected. One active assertion per exact reviewer
label is supported. Labels do not authenticate people or establish independence.
Preserve earlier snapshots when replacing an assertion; review supersession is
not implemented. Old positions may remain after source declarations are removed
or retrieval status changes, retaining their original hashes and dates.

## What is bound, and what is not

A report target binds the exact report ID, question and criteria, ordered mapped
record IDs and their source-basis hashes, supplied retrieval state, raw report
locator including its presence/absence, and all ordered source descriptors for
that report. Record targets retain their search occurrence and mapped CSV-row
context. Full containing search bodies are stored once in a shared catalog, not
copied into every report. Hashes use canonical supplied JSON: object-key order is
ignored; list order, literal values and types remain significant.

Changing source version/digest/locator, retrieval, mapped records, criteria or
containing search context can stale a position. The source target deliberately
excludes canonical report decision/reason, assigned study IDs, reviewer ledger,
results, work packages and protocol-version label. A later canonical choice does
not circularly stale the review that may have informed it. These excluded values
remain visible separately; changing them may affect other existing workflow
bindings and is not scientifically endorsed by an unchanged report-review target.

`CURRENT_SOURCE` and `STALE_SOURCE` compare only supplied hashes. Independently:

- `SOURCE_NOT_SUPPLIED`: no document descriptor exists for the report.
- `DOCUMENT_BYTES_UNBOUND`: at least one descriptor has a null byte digest.
- `SUPPLIED_DIGESTS`: every descriptor has a supplied digest, still unverified.
- `document_bytes_verification` remains `NOT_PERFORMED` in all three cases.

A current hash can accompany an unavailable report or absent/unbound source; it
never certifies actual reading. `matches_recorded_decision` compares only explicit
include/exclude labels, not reasons or eligibility correctness. It is null for
unclear positions and absent/pending canonical decisions. Stale positions remain
visible but are excluded from current-position comparisons. Different/unclear
positions are shown, never adjudicated. Empty comparison cues do not prove that
reading, source verification or a review is complete.

## Counts, study boundaries and compatibility

The optional `report_review` projection is preserved in core/report/audit/synthesis
views. Status and handoff expose `reports_with_review_cues` with exact report,
source and reviewer input pointers and a detailed read-only view. Cues describe
supplied missing context or literal differences, not scientific quality or a
mandatory sequence of tasks. Constant verification limitations remain explicit
boundaries rather than permanently unresolved work queues.

Run-to-run comparison adds `report_review_changes` only when either input opts in.
It retains before/after source declarations, human assertions and source targets.
An unchanged opinion can become stale after a source change. A changed declared
digest is not independently verified change to remote document bytes.

Report inclusion is not a per-study eligibility judgment. Multiple supplied study
IDs within a report remain separate declarations, and result presence does not
prove complete extraction. Reviewer opinions never add records, reports, studies
or results to PRISMA counts. No quorum, latest-date winner or consensus is inferred.

Omitting both keys preserves legacy payload shapes and CSV bytes. Explicit empty
lists opt in; null is invalid. `stage`, `report_stage`, `source_stage` and
`review_stage` separately identify supplied stages. Nonempty declarations/reviews
without a report stage are rejected. Both keys are now reserved enrichment fields
in CSV import histories. The seven-file bundle retains raw assertions and the
validator fingerprint; it does not archive document bytes. Verify engine-bound
artifacts using their recorded implementation version, not automatic reapproval.

For a person's position on an individual declared study, use the separate
[exact report-study review workflow](REPORT_STUDY_REVIEWS.md). It records explicit
reviewed-source IDs without comparing its opinion to report inclusion as if the
units were interchangeable. Report-level positions and hashes remain unchanged.

## Optional local byte comparison

[Explicit local source-byte checks](REPORT_SOURCE_CHECK.md) can separately compare
selected local files with non-null supplied document digests. This does not change
this read-only review projection: its `document_bytes_verification` remains
`NOT_PERFORMED`, and a separate local match does not authenticate the source,
prove reading, renew a position or adjudicate eligibility.

## Separate canonical decision application

[Detached full-text decision records](REPORT_DECISIONS.md) can apply a separately
supplied human choice and explicit study declaration after structural validation.
They retain these positions unchanged and never infer a vote or correct outcome.
The original protocol and separate application record are needed for replay;
this review projection does not become an embedded decision history.

## Reviewed append of new source declarations

[Source declaration intake](MANUAL_SOURCE_DECLARATIONS.md) provides a separate
reviewed append path for an already retrieved report, including later supplements.
It preserves existing declarations and reviews, does not fill old null digests or
select a preferred version, and exposes changed source contexts without renewal.
