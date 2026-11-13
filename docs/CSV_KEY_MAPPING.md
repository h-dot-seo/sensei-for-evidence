# CSV intake when URL or DOI cells are blank

If every data row has a nonblank key column, explicitly select that same column
for both the record ID and the source locator. This is an existing importer path,
not a new dialect, wrapper, fallback rule or automatic column guess. It keeps the
original file unchanged. A locator is inert supplied text: it need not be a URL,
is never opened, and does not authenticate a source or identify a publication.

Do not repair blank URL cells or manufacture links. With `--id-column Key
--locator-column Key`, **every** row uses its literal Key value for both fields.
Blank and nonblank URL/DOI values remain in `original_values`, but neither is used
as the selected locator. The mapping is recorded in `column_mapping` and bound to
the review target. No row-by-row URL/key mixing or derived locator is performed.

## Reproduce the synthetic journey

`examples/dialects/keyed-csv.csv` is hand-written, entirely fictional UTF-8 CSV.
It contains a blank URL, a `.invalid` URL, blank DOI cells, a quoted multiline
abstract and a repeated key. No real export or provider compatibility is claimed.
From the repository root, replace `OUTPUT` with a new, existing directory outside
the checkout. The two output files must not exist:

```sh
python bibliographic_intake.py preview examples/source-work-protocol.json examples/dialects/keyed-csv.csv --search-id search-primary --searched-at 2026-11-04T00:00:00Z --id-column Key --locator-column Key --output OUTPUT/keyed-intake.json --text
python bibliographic_intake.py verify OUTPUT/keyed-intake.json --text
python bibliographic_review.py template OUTPUT/keyed-intake.json --review-output OUTPUT/keyed-review.json --text
```

The three commands leave the protocol unchanged and stop at an **unfilled**
reconciliation document. All three occurrences are retained. Both occurrences of
`fictional-a` retain that literal key as their locator; the duplicate-ID hint is
not publication matching or a deduplication decision. No conflicting locator is
invented from the different or missing URL cells. Review stays NOT_PERFORMED,
census NOT_ESTABLISHED and conclusion readiness NOT_READY. The blank resolutions
and null review must be supplied separately before any explicit import is possible.

## Declared grammar and failure boundaries

| Input condition | Existing CSV behavior |
|---|---|
| Exact `Key` header with a nonblank value on every data row | Accepted when both column flags explicitly name `Key` |
| Empty URL/DOI cell not selected by either flag | Preserved as an empty original value |
| Repeated Key | Separate occurrences and a literal duplicate-ID hint; no automatic merge |
| Quoted comma or multiline cell; LF or CRLF | Preserved, including original byte spans and newline bytes |
| No mapping flags for this fixture | Rejected: default required headers are absent |
| URL selected as locator while any URL cell is blank | Rejected, not replaced by Key |
| Missing, empty or whitespace-only selected Key value | Rejected; no positional ID or locator is synthesized |
| Wrong-case header, malformed rows or invalid UTF-8 | Rejected rather than guessed or repaired |

The inherited limits, byte provenance and exclusive output rules are described in
[bibliographic intake](BIBLIOGRAPHIC_INTAKE.md). A required key is not assumed to be
unique or stable across exports; reordering changes occurrence IDs. Byte checks
do not establish a complete search, genuine provider export, authorship or rights.
The unchanged importer retains the full supplied protocol and original CSV without
redaction. Keep real files and outputs private and outside the public checkout.
Continue through [explicit collection review](BIBLIOGRAPHIC_REVIEW.md), not by
editing the original export or treating the template as approved screening.

This guide covers only explicit same-column CSV mapping. It does not relax the
strict RIS grammar, add an untagged-continuation RIS parser, or add native archive
formats. Those are separate roadmap increments; no exporter-family conformance
is asserted here.
