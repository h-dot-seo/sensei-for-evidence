# Lossless local PubMed NBIB preparation

`nbib_intake.py` brings a supported local NBIB export into the existing
[explicit bibliographic reconciliation](BIBLIOGRAPHIC_REVIEW.md) workflow. It
retains the native file and creates a deterministic CSV derivative with every
native field occurrence and record text. Existing CSV review and protocol
integrity rules are unchanged. This is not a provider connection or a search.

The [PubMed User Guide](https://pubmed.ncbi.nlm.nih.gov/help/) describes NBIB
citation-manager exports and repeatable PubMed fields. The
[NLM format announcement](https://www.nlm.nih.gov/pubs/techbull/ma20/ma20_pubmed_updated.html)
describes UTF-8 PubMed-format exports as `.txt` or `.nbib`. Those sources explain
the format's purpose; the deliberately strict parser contract below is this
software's supported subset, not a claim to accept every historical export.

## Prepare, inspect, then explicitly reconcile

`examples/pubmed-export.nbib` is entirely fictional, including its PMID strings,
titles and authors. It has three occurrences with two exact identifier strings.
It is not a retrieved citation set. Use new paths outside the public checkout;
their parent directory must already exist.

```sh
python nbib_intake.py preview examples/bibliographic-base.json examples/pubmed-export.nbib --search-id local-primary --searched-at 2026-11-04T00:00:00Z --output /outside/new-nbib.json --text
python nbib_intake.py verify /outside/new-nbib.json --intake-output /outside/new-csv-intake.json --text
python bibliographic_review.py template /outside/new-csv-intake.json --review-output /outside/new-choices.json --text
```

The template deliberately leaves every identity/withholding choice and rationale
unfilled. Inspect the native fields and original file before supplying each row's
`new_record`, `same_record` or `do_not_promote` choice. A repeated PMID does not
choose `same_record` automatically. Different identifiers with similar titles
are not merged. A canonical ID is the human's explicit choice, not necessarily
the generated `pubmed:` label.

After filling the choices, keep `review: null` and prepare a separate review:

```sh
python bibliographic_review.py target examples/bibliographic-base.json /outside/new-csv-intake.json /outside/new-choices.json --review-output /outside/new-review.json --text
```

Fill the new review's reviewer, real calendar date, rationale and
`import_for_screening` decision only after inspecting the exact target. Then:

```sh
python bibliographic_review.py assemble examples/bibliographic-base.json /outside/new-csv-intake.json /outside/new-review.json --protocol-output /outside/new-protocol.json --text
python research_status.py /outside/new-protocol.json
python prisma_audit.py /outside/new-protocol.json --text
python research_bundle.py create /outside/new-protocol.json /outside/new-bundle.zip
python research_bundle.py verify /outside/new-bundle.zip
```

Existing reconciliation requires an unimported common base and an unused planned
search. Later imports use that same base and the current protocol, as documented
in the reconciliation guide. Previewing an already used planned search does not
authorize replacing it. No mock-adapter ledger may be mixed into CSV promotion.

The resulting search remains incomplete. No screening, report, study, evidence,
guideline applicability or development recommendation is created. Withholding a
collection row is not a screening exclusion. File EOF and record counts do not
prove a search total, complete coverage or PRISMA compliance.

## Supported grammar and lossless records

- Strict UTF-8 with an optional initial BOM; LF, CRLF and bare CR terminate
  physical lines. NULs and invalid UTF-8 are rejected. An empty export or one
  containing only empty lines is rejected, not interpreted as a zero-hit search.
- Each record starts with exactly one `PMID` field. Its value is a single line of
  ASCII digits containing at least one nonzero digit. No whitespace trimming,
  integer conversion or leading-zero normalization occurs. `01` and `1` remain
  distinct literal strings, without deciding whether either is a real PMID.
- A tag has two to four uppercase ASCII letters/digits, beginning with a letter,
  padded with spaces to four characters, followed by `- ` and the value. For
  example, `TI  - ` starts a title field. Continuations start with six spaces;
  the remaining text is retained verbatim, including additional spaces.
- Physically empty lines separate records. Whitespace-only lines are not empty
  separators. An orphan continuation, malformed tag, second PMID in a record,
  folded PMID or missing record separator is rejected with a line-numbered
  error that does not echo the supplied content.
- Ordered repeated tags, unknown tags and separate continuation value lines are
  preserved. No author list is collapsed, title reconstructed, abstract interpreted,
  DOI extracted, identifier resolved or field silently discarded. Each record
  and field retains its exact raw text and span. Blank separator spans are also
  recorded. Record IDs are positional occurrences, not stable publication IDs.
- Spans use inclusive one-based physical lines and half-open zero-based byte
  offsets. SHA-256 covers the exact byte range, including line terminators and
  an initial BOM when that range contains it. The complete original file is
  retained as UTF-8 text that re-encodes to the original bytes.

Native inputs are limited to 10,000,000 bytes, 100,000 records and 200,000 physical
lines. Generated CSV must also satisfy the unchanged CSV parser's byte, line,
row and interpreter field-size limits. Retained text, field JSON and escaping
expand the file, so a native input below its limit can still be rejected when
converted. Serialized artifacts and rendered CLI output are bounded at
50,000,000 bytes. Limits are safety bounds, not coverage claims.

## CSV provenance is explicit, not native format authentication

Each native occurrence becomes one CSV row with these columns:

- `record_id`: `pubmed:` followed by the literal supplied PMID.
- `source_locator`: the derived `https://pubmed.ncbi.nlm.nih.gov/PMID/` form.
- `nbib_occurrence_id`: the positional native occurrence identifier.
- `nbib_original_export_sha256`: the complete native file's byte hash.
- `nbib_record_span_json`: its exact native byte/line span as canonical JSON text.
- `nbib_fields_json`: all ordered fields, continuation lines, raw text and field
  spans as canonical JSON text.
- `nbib_record_text`: the exact native record text, including its terminators.

The namespace and URL are local derivation conventions. The URL is never opened,
and a digit string is never certified as a real PMID. Repeated occurrences remain
separate rows. The outer artifact holds the native source, parsed records and
nested `csv_intake`. The inner intake's `source_export` and ordinary row spans
refer to the **derived CSV**, not the NBIB bytes. Native spans remain clearly
named inside the original-value columns.

`verify` reconstructs the complete conversion and CSV intake from retained native
bytes, protocol, selected plan and supplied timestamp. It compares every derived
field and current implementation hash, rejecting inconsistent edits, unknown
fields and merely resealed output. This proves internal byte/derivation
consistency, not source authenticity, query/export association, human identity,
timestamp authenticity or scientific truth. Someone who can replace all inputs
and recompute everything can create a different internally consistent artifact.

The unchanged CSV ledger, screening source snapshots and audit keep those column
strings. They verify the CSV derivation's supplied contents under their existing
rules; they do not independently invoke the NBIB verifier. **Keep the outer NBIB
artifact alongside the imported protocol and ordinary bundle.** It is needed
for the full original file, blank separators, native conversion replay and its
implementation hashes. The ordinary bundle does not automatically embed that
outer artifact or certify native parsing. Use the recorded implementation
revision for later replay if code bytes have changed.

For a separate inspection copy of the derivative:

```sh
python nbib_intake.py verify /outside/new-nbib.json --csv-output /outside/new-derived.csv --text
```

`--csv-output` and `--intake-output` are mutually exclusive. All output paths use
exclusive creation, reject existing files/symlinks and are opened only after
validation and serialization. An operating-system write failure can still leave
a partial new file. Omit output flags for a read-only preview/verification;
default stdout is JSON and `--text` safely quotes supplied values. Shell
redirection has its own overwrite behavior.

## Privacy and research boundary

Native exports may include abstracts, author affiliations or other supplied
personal/copyrighted content. Nothing is redacted. Keep real inputs and outputs
outside this public repository and review redistribution rights before sharing.
Only fictional metadata is shipped here. There are no external calls, full-text
article retrievals, extracted scientific observations, patient data, clinical advice or
experimental execution instructions in this workflow.
