# Preserve supplied RIS citations before explicit reconciliation

`ris_intake.py` accepts a documented fixed-column UTF-8 RIS subset and preserves
its exact native bytes, ordered record/field occurrences and byte/line spans.
It creates an unreviewed CSV intake for the existing explicit collection-review
workflow. This gives supplied RIS exports a path that does not require manually
copying selected fields into CSV and losing the rest of the original input.

There is no database connection, literature retrieval, identifier lookup,
automatic deduplication, screening or completeness claim. RIS source/query/date
association remains a supplied assertion. A valid wrapper is not reviewed evidence.

RIS variants differ. [Zotero's official format documentation](https://www.zotero.org/support/dev/data_formats#ris)
describes common departures from the specification; its
[exporter source](https://github.com/zotero/translators/blob/master/RIS.js) is an
informative implementation reference for tagged TY/ER framing. This tool is a
separate implementation with the narrower contract below, not a Zotero translator
or a claim of compatibility with every database, reference manager or RIS dialect.
No third-party translator code or real literature fixture is included.

## Prepare and inspect the fictional example

Use a new existing output directory outside the repository. The example contains
four deliberately fictional references, repeated DOI/ID values, repeated fields,
a conflicting DOI, an unopened attachment locator, an identifier-free reference
and one candidate explicitly withheld by the supplied choices.

```sh
python ris_intake.py preview examples/bibliographic-base.json examples/ris-export.ris --search-id local-primary --searched-at 2026-11-04T00:00:00Z --output /outside/new-ris-wrapper.json --text
python ris_intake.py verify /outside/new-ris-wrapper.json --intake-output /outside/new-ris-intake.json --text
python bibliographic_review.py template /outside/new-ris-intake.json --review-output /outside/new-ris-blank-choices.json --text
python bibliographic_review.py target examples/bibliographic-base.json /outside/new-ris-intake.json examples/ris-resolutions.json --review-output /outside/new-ris-review.json --text
```

Replace `/outside` with your actual directory, and quote paths containing spaces.
The blank template fills no identity choices. The fictional choices separately
declare the first row new, link the second to it, declare the identifier-free third
row new, and withhold the fourth. No DOI or title chooses these dispositions.
Withholding is collection triage, not a title/abstract exclusion.

Inspect the original input and the exact current-protocol target. The generated
review document leaves reviewer, date, rationale and decision null. Complete a
separate review only after actual human inspection. Use a real `YYYY-MM-DD` date
and decision `import_for_screening`; keep the exact target actually reviewed.
These examples are software-test data, not evidence of a real person's review.

```sh
python bibliographic_review.py assemble examples/bibliographic-base.json /outside/new-ris-intake.json /outside/filled-ris-review.json --protocol-output /outside/new-ris-protocol.json --text
python research_status.py /outside/new-ris-protocol.json --text
python prisma_audit.py /outside/new-ris-protocol.json --text
python research_bundle.py create /outside/new-ris-protocol.json /outside/new-ris-research.zip
python research_bundle.py verify /outside/new-ris-research.zip
python ris_intake.py verify /outside/new-ris-wrapper.json --text
```

For those supplied choices, four raw occurrences become three promoted raw rows,
one withheld raw row and two canonical search memberships awaiting screening.
The one appended search remains incomplete with unknown total and continuation;
the secondary planned search remains missing. There are no reports, study
declarations, result rows or eligibility decisions created by this import.

For a later **unused** planned search, prepare its wrapper against the same
original ledger-free common base, then target/assemble against the current enriched
protocol, as in [bibliographic reconciliation](BIBLIOGRAPHIC_REVIEW.md). Do not erase
prior provenance or use an intermediate imported protocol as a new base. Already
used search IDs and immutable-plan changes remain unsupported.

## Supported grammar, not universal RIS compatibility

- Strict UTF-8 bytes, with an optional BOM only at the beginning. CRLF, LF and bare
  CR physical line endings are supported and preserved, including mixed endings
  and an absent final newline. Unicode paragraph/line-separator characters inside
  values are not treated as physical line breaks.
- A record starts with `TY  - TYPE` and closes with `ER  -` or `ER  - `, where the
  ER value is exactly empty. Records may be adjacent or separated by empty lines.
  TY must contain one uppercase alphanumeric token of 1–16 characters beginning
  with a letter. Unknown type tokens are retained, not mapped to a study design.
- Field tags have two uppercase alphanumeric characters beginning with a letter,
  followed by exactly two spaces and a hyphen. An optional single space introduces
  the literal value, which may be empty. Unknown tags and repeated tag occurrences
  remain ordered; their values are not reduced to a dictionary or normalized.
- Only lines beginning with six spaces can continue a preceding non-TY field.
  The six-space prefix is removed from that separate `value_lines` element, while
  exact physical text and bytes remain in the field's `raw_text` and span. An
  indented string resembling TY or ER remains content, not a record boundary.
- Empty lines are allowed outside records only. Unindented/other-indent multiline
  continuations, blank paragraphs within open records, missing ER, orphan fields,
  one-space tag padding, lowercase tags and legacy encodings are rejected rather
  than guessed or silently repaired. In particular, some otherwise legitimate RIS
  exports with unindented multiline abstracts are outside this initial subset.

Keep a rejected original unchanged. Use a supported export option or the separate
[supplied CSV route](BIBLIOGRAPHIC_INTAKE.md) with its own provenance limits; do not
silently rewrite native files and represent the result as the original. Empty or
blank-only files are not accepted as evidence of a zero-hit search. A supported
TY/ER-only record is a retained occurrence, not proof of a real publication.

## Occurrence labels are not publication identity

The CSV's required `record_id` is generated as
`ris-occurrence:<original file SHA-256>:<positional ris-record ID>`. Its required
`source_locator` is the inert text
`supplied-ris-sha256:<original file SHA-256>#<positional ris-record ID>`.
These identify a position in an exact supplied file, not a publication, database
accession, DOI or accessible document. They are not stable across file changes:
adding a blank separator changes the file hash and therefore all occurrence labels.
That does not mean the represented publications changed.

DO, ID, AN, UR, L1 and every other field are retained without selecting a preferred
value. Missing identifiers do not prevent collection; repeated identifiers and
even identical native records do not merge occurrences. A citation URL or local
attachment path is never opened. Canonical record IDs and cross-source links still
require explicit human choices, not the generated occurrence labels or metadata.
The nested CSV duplicate-ID and overlap hints compare these occurrence labels
only. Empty hint lists do not establish an absence of duplicate publications or
cross-source overlap; inspect the retained native fields and choose explicitly.

The derivative also carries `ris_occurrence_id`, `ris_original_export_sha256`,
`ris_record_type`, `ris_record_span_json`, `ris_fields_json` and `ris_record_text`.
Record and field spans refer to the original RIS file, not the CSV. Byte offsets
are zero-based with exclusive ends; physical-line spans are one-based inclusive.
Field raw text reconstructs the exact record, and record plus outside blank spans
cover the entire original input. The wrapper retains the entire original text,
size and digest, including separator lines and any initial BOM.

For an inspection copy of the derivative, use a new path:

```sh
python ris_intake.py verify /outside/new-ris-wrapper.json --csv-output /outside/new-ris-derived.csv --text
```

`--csv-output` and `--intake-output` are mutually exclusive. This derivative is
source-preserving interchange, not a general promise of spreadsheet safety. CSV
quoting is not formula neutralization. Inspect untrusted data as text/JSON or use
an explicitly text-only spreadsheet import with formula execution disabled.

## Replay, archive and resource boundaries

Verification checks exact retained source length/digest and implementation hashes,
reparses the native input, regenerates the CSV and nested intake, and compares the
entire wrapper using canonical JSON. Unknown fields, tampered spans/ordering,
changes to selected query/time, type substitutions and mismatched implementation
bytes fail. Object-key order and JSON formatting are ignored; native bytes and
list order are not. A party able to rebuild all supplied inputs can make a different
consistent wrapper: hashes are not signatures or authentication.

Keep the wrapper and recorded implementation. Ordinary research bundles retain
CSV provenance and embedded native record metadata, but do not independently
verify this RIS conversion or retain all native separators. The existing
single/batch **NBIB** collection archives do not accept RIS wrappers. The separate
[typed native collection archive](NATIVE_COLLECTION_BUNDLES.md) now accepts explicit
RIS bindings and can retain them alongside supported NBIB wrappers and original
files. It verifies each selected wrapper against its exact historical CSV import,
not merely a matching search name. It is not a complete research-history archive.
A separately retained RIS wrapper can still be replayed using the recorded code.

The native parser allows at most 10,000,000 bytes, 100,000 records and 200,000
physical lines. The derived CSV must also satisfy the existing CSV parser's byte,
record, physical-line and interpreter field-size limits, which are not raised.
Retained native fields, JSON and quoting can expand the derivative beyond those
limits even when the original fits. Serialized wrappers and CLI output are limited
to 50,000,000 bytes. Strict JSON/UTF-8 and all output encodings are checked before
creating an output file.

Every output is exclusively created. Observed existing final entries, including
dangling symlinks, are refused; a failed path inspection is not bypassed. This is
not an atomic transaction or protection against concurrent parent/path replacement.
A write failure may leave a partial new file. `--text` changes stdout only; saved
wrapper/intake outputs remain JSON. Shell redirection has separate overwrite risks.

No source authenticity, reviewer identity, retrieval chronology, document reading,
publication identity, search or extraction completeness, PRISMA compliance,
scientific correctness or clinical suitability is established. Keep real/private
exports outside this public repository. All supplied metadata, abstracts and
attachment locator text are retained without redaction or rights clearance.
