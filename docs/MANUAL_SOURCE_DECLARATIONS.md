# Append reviewed source declarations to retrieved reports

`report_source_intake.py` adds explicitly supplied new document descriptors to an
existing retrieved report. This covers later supplements or separately declared
versions, and first descriptors for a retrieved report with none. Registration
and retrieval-transition tools remain separate; neither updates an already
retrieved report merely to add a source. No direct editing of the protocol's
source list is needed for this append operation.

This is a declaration, not retrieval or source verification. It never opens a
locator, reads or hashes a document, selects the preferred/current version,
changes eligibility, discovers a study or renews a human review. All checked-in
examples are fictional; keep real/private inputs and outputs outside the repository.

## Explicit new declaration rows

The candidate document has exactly `schema_version: 1` and a nonempty ordered
`candidates` list, with at most 100 entries. Each entry has exactly these fields:

```json
{
  "source": {
    "source_id": "a-new-explicit-source-id",
    "report_id": "an-existing-retrieved-report-id",
    "source_locator": "an-inert-supplied-document-location",
    "document_version": "the-supplied-version-description",
    "document_sha256": null
  },
  "declared_by": "the-person-supplying-this-declaration",
  "declared_at": "2026-11-04",
  "declaration_note": "Why this additional document is declared and what remains uncertain."
}
```

The `source` object uses the existing five-field `report_sources` schema. Text
must be literal and nonblank. Dates must be real YYYY-MM-DD dates. The digest must
be explicit null or 64 lowercase hexadecimal characters; a valid-looking digest
is still an unverified supplied assertion. Null is not replaced with a locator
hash, inferred digest or invented byte content.

Each source ID must be new across the complete existing catalog and the supplied
batch. Reusing an existing ID is rejected, even with identical fields: this is not
an edit, replacement or upsert. Distinct IDs with identical locators/digests remain
separate declarations. Matching text or bytes does not merge sources or studies.
The command never chooses a preferred document or treats the latest date as authority.

Reports must already have supplied retrieval status `retrieved`; their full-text
choice may be pending, included or excluded. Unknown, pending-retrieval and
unavailable reports are rejected for this operation. Use the separate
[registration](MANUAL_REPORT_INTAKE.md) or [retrieval update](REPORT_RETRIEVAL_UPDATES.md)
workflow when applicable. Adding declarations never changes a report's retrieval
or eligibility status.

## Nine-command synthetic rehearsal

Use an existing outside directory named `OUTPUT` and new output filenames. The
following template fills only the explicitly selected report ID. Source ID,
locator/version, declarer/date/note remain null. The byte digest also stays null
unless an actual supplied expectation is available. The incomplete template is
not an accepted candidate or review.

```sh
python report_source_intake.py template examples/report-study-inventory-reviews.json --report-id=report-one --candidate-output OUTPUT/new-source-draft.json
python report_source_intake.py target examples/report-study-inventory-reviews.json examples/manual-source-declarations.json --output OUTPUT/source-target.json
```

The checked-in completed candidate fixture is different from the unfinished draft:
it explicitly declares two fictional additions, one for included `report-one` and
one for pending-assessment `report-three`. Its non-null digest is a fictional
unverified assertion, not a hash measured from a source file.

Copy only `review_document` from the prepared target to
`OUTPUT/completed-source-review.json`. Keep `schema_version` and `target_sha256`.
Fill `receipt_id`, `reviewer`, `reviewed_at`, `rationale` and
`decision: "append_source_declarations"`. Use clearly fictional labels/rationale
only for this rehearsal. Real use requires an actual separate review of the exact
input and declarations. Blank fields, wrong decisions and stale targets fail.

```sh
python report_source_intake.py assemble examples/report-study-inventory-reviews.json examples/manual-source-declarations.json OUTPUT/completed-source-review.json --output OUTPUT/source-application.json
python report_source_intake.py verify examples/report-study-inventory-reviews.json OUTPUT/source-application.json --protocol-output OUTPUT/with-sources.json
python report_review.py examples/report-study-inventory-reviews.json --report-id=report-one --text
python report_review.py OUTPUT/with-sources.json --report-id=report-one --text
python report_source_check.py template OUTPUT/with-sources.json --source-id=source-extra-three --output OUTPUT/source-byte-template.json
python research_bundle.py create OUTPUT/with-sources.json OUTPUT/research.zip
python research_bundle.py verify OUTPUT/research.zip
```

This adds two declarations (four to six) and changes no record/report flow,
canonical report/study membership, result, condition, task or raw review assertion.
The before/after report view exposes changed source context and any newly stale
positions; an unchanged stored opinion is not a renewed review. The byte-check
template is unfinished and performs no source inspection. Its relative `path`
and expected `bytes` still require an explicit human mapping.

For actual local comparison, follow [source-byte checks](REPORT_SOURCE_CHECK.md).
The separate checker can compare a selected descriptor's non-null expected digest
with an explicitly mapped local file. Safe source inspection requires its POSIX
no-follow access support; native Windows fails closed, with template generation
still available. No source-byte check result is automatically ingested as reading,
source authenticity, eligibility or persistent protocol approval.

## What changes and what stays bound

Only new `report_sources` rows are appended, in candidate order. Every existing
row and other raw field stays unchanged, including opaque metadata, searches,
CSV provenance, source declarations, review hashes, report/study membership,
results, conditions and work-completion assertions. Whole-protocol validation and
exact record/report flow equality are checked before an application is returned.
Mock adapter contexts are rejected; no provenance is erased to make intake pass.

The target binds the entire original protocol, ordered candidates, selected
reports' before/after source catalogs, mapped record provenance, generated output
pointers and implementation hashes. A change to unrelated context still makes the
import review stale. There is no automatic rebase or reusable generic approval.
The detached receipt retains supplied declaration/review metadata and before/after
source summaries; only the five-field descriptors enter the protocol. Complete
canonical replay compares the entire application, not just editable checksums.
These unsigned assertions do not authenticate the declarer/reviewer, chronology
or actual execution; consistently reauthored inputs can still replay.

A new source on a report changes that report's entire declared source context.
Even an unselected supplemental descriptor can stale report, study and inventory
review targets and document-bound work. Existing raw positions, work statuses and
hashes remain untouched. Not every downstream assertion has a source binding, and
an unchanged row does not establish reassessment or continued scientific validity.
No majority, consensus, action priority or required new task is inferred.

Adding a new non-null-digest descriptor does **not** fill an earlier null digest.
The old descriptor remains, so whole-catalog views still say
`DOCUMENT_BYTES_UNBOUND` if any descriptor is unbound. A local match for the new
source does not verify the older one or remove it from the catalog. Editing/removing
old declarations and choosing a canonical version are outside this intake.

## Retention, limits and unsupported scope

Keep the actual original protocol, detached application and recorded implementation
for verification. Ordinary research/native archives retain the enriched protocol,
not this application's declaration/review history. Existing report/extraction
transition archives do not accept this new application kind. Do not omit an
intervening source change from a purported contiguous segment; start a separate
segment afterward if appropriate, without claiming the missing history.

Limits are 100 candidates, 10 MB candidate/review input, and 50 MB protocol or
application input/output. These bound byte volume, not hard CPU/memory usage.
Strict JSON types, duplicate keys, non-finite values, unpaired surrogates, invalid
whole protocols and unknown fields fail rather than being repaired or coerced.
JSON outputs are prepared before creation; `--text` affects stdout only. Existing
entries, directories and observed dangling links are refused by inspection and
exclusive creation. This is not an atomic path-race/ancestor-alias defense; a
failed write can leave a partial new file.

No source locator is followed, private content redacted or output transmitted.
Review access before sharing any generated artifact. No PDF parsing, publisher
validation, automatic citation identity, source replacement, digest computation,
review supersession, scientific/clinical inference or completeness proof is
provided. Census remains `NOT_ESTABLISHED`, conclusions `NOT_READY`.
