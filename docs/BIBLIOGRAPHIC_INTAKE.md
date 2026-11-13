# Local bibliographic export intake

`bibliographic_intake.py` makes a local CSV export inspectable before a researcher
enters screening or extraction decisions. It retains the exact export bytes,
original columns, row locations and explicit association with a declared search.
It does not execute a provider, infer publication identity, deduplicate records or
turn the export into an accepted search receipt.

This is a **detached unreviewed collection artifact**. No imported row is counted
in the protocol's PRISMA-oriented accounting, evidence tables, guideline links or
development work. A separate [explicit reconciliation workflow](BIBLIOGRAPHIC_REVIEW.md)
can append an incomplete search after supplied row choices and export-level review.
The existing synthetic mock-receipt workflow remains separate.

For local PubMed-format `.nbib` files, use the
[lossless NBIB preparation bridge](PUBMED_NBIB_INTAKE.md). It retains the native
source and supplies a CSV derivative to this unchanged importer. Repeated native
tags and record text remain in original-value columns; no identity resolution is
automated. Keep the separate native artifact for full-file conversion replay.

## Reproduce the synthetic journey

All records in `examples/bibliographic-export.csv` are fictional. The source-work
protocol already has a synthetic search receipt; intake leaves it unchanged.
Choose a new artifact path outside this public checkout:

```sh
python bibliographic_intake.py preview examples/source-work-protocol.json examples/bibliographic-export.csv --search-id search-primary --searched-at 2026-11-04T00:00:00Z --text
python bibliographic_intake.py preview examples/source-work-protocol.json examples/bibliographic-export.csv --search-id search-primary --searched-at 2026-11-04T00:00:00Z --output /path/outside/checkout/new-intake.json --text
python bibliographic_intake.py verify /path/outside/checkout/new-intake.json --text
```

Use a suitable absolute local path on your operating system. Its parent directory
must exist. Output creation is exclusive: an existing file is never overwritten.
Omit `--output` for a read-only preview. Omit `--text` for structured JSON. A failed
validation does not create the requested output. An operating-system write failure
can leave a partial new file; verification rejects incomplete JSON.

The example exposes five occurrences, three sharing the exact ID `r1`, with two
different literal locators. All occurrences remain separate. Existing protocol
ID overlap is displayed separately from duplicates within the new export. Neither
is a publication match. The guideline and development rows are only supplied
bibliographic text, not extracted recommendations, applicability or evidence.

## Explicit inputs and byte provenance

If a CSV has a nonblank key on every row but blank URL or DOI cells, explicitly
use the same key column for both `--id-column` and `--locator-column`. The locator
is inert supplied text, not a fetched or authenticated link. Original blank cells
remain unchanged. See the tested [same-column mapping journey](CSV_KEY_MAPPING.md)
for `--id-column Key --locator-column Key`; missing/blank keys still fail closed.

- A valid protocol with a nonempty `search_plan` and a selected existing
  `search_id` is required. The exact source, query and window are copied from that
  plan. Extra plan fields are retained and identified as uninterpreted.
- `--searched-at` is a required nonblank operator-supplied string, not a verified
  provider timestamp. Associating a CSV with a search does not prove that the
  query produced the file. Selecting a search with existing receipts does not
  overwrite, append to or reconcile those receipts.
- CSV must use commas and strict UTF-8, optionally with an initial BOM. The first
  nonempty physical row is the header. Quoted commas and multiline cells are
  supported, as are LF, CRLF and bare-CR line endings. Physically empty rows are
  skipped but their locations and hashes are recorded. Empty quoted cells,
  delimiter-only rows and whitespace rows are not skipped.
- `record_id` and `source_locator` are the default required columns. Use
  `--id-column` and `--locator-column` to explicitly select other literal header
  names. No DOI/PMID/URL or title-matching rule is inferred. No locator is opened.
- Original headers and cell strings are preserved without stripping, case
  folding or normalization. Required values must be nonblank. Duplicate or blank
  headers, inconsistent row widths, NULs, invalid UTF-8 and malformed CSV are
  rejected. The interpreter's existing CSV field-size limit is also enforced.
- Each occurrence receives a positional candidate ID, not a stable publication
  identifier. Reordering the export changes these IDs. The header, each record
  and skipped empty row have inclusive 1-based physical line bounds and half-open
  0-based byte bounds, plus SHA-256 of that exact byte range. Terminators and the
  initial BOM, when present in the range, are included.
- The whole export has an exact byte length and SHA-256. Its retained UTF-8 text
  re-encodes to the original bytes, including BOM and newline differences. CSV
  input is limited to 10,000,000 bytes, 100,000 data rows and 200,000 physical
  lines including empty lines. Serialized artifacts
  are limited to 50,000,000 bytes; retention and derived fields can make an artifact
  larger than its export, so not every CSV below the input limit fits the output.

The full supplied protocol is retained with a canonical JSON hash. Object key
order does not change that protocol hash; list order and supplied values do. This
is distinct from the export's raw-byte hash. The saved artifact uses sorted,
indented UTF-8 JSON with LF; the artifact identity hash uses compact canonical
JSON, not the pretty file bytes. Text previews safely quote supplied identifiers
and locators; full column values and export text remain in JSON.

## What verification proves

`verify` checks the retained export length and hash, the current importer and
protocol-engine source hashes, and regenerates the complete artifact. Changed
row values, spans, statuses, effects, plan fields, unknown fields and review-target
hashes are rejected if inconsistent with those retained inputs. Use the recorded
implementation revision when checking an older artifact after code changes.

The `review_target` binds the artifact contents except that target itself. It is
an identity anchor for inspection, not an existing mock-adapter review target or
an acceptance decision. A consistent hash is not a signature: someone who can
replace the inputs and recompute all derived fields can create another internally
consistent artifact. Verification does not authenticate the source, timestamp,
query/export association, authorship or publication.

`UNREVIEWED_LOCAL_EXPORT`, `NOT_PERFORMED`, `NOT_ESTABLISHED` and `NOT_READY` remain
explicit. A header-only CSV is a valid zero-row intake, not evidence that a search
found nothing. End-of-file never proves a terminal provider page, search total,
complete coverage or PRISMA compliance. There are no external calls, scientific
quality judgments, clinical recommendations or experimental procedures.

## Keep real input private

The artifact retains the entire supplied protocol and CSV text without redaction.
It may contain private project details or copyrighted bibliographic content. Keep
real inputs and outputs outside the public repository, and review redistribution
rights before sharing. No real export or paper content is included in this release.

## Remaining research workflow gaps

This increment gives a researcher a reproducible local intake record, not a
complete literature collection pipeline. Explicit [reconciliation and screening
intake](BIBLIOGRAPHIC_REVIEW.md) is a separate step. Verified search-completion
evidence, many-study report representation, and source-review links to
guideline/development context before extraction remain separate work. Raw imported
labels never stand in for those decisions.
