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

For several local files explicitly associated with the same declared search,
use [multiple-file preparation](PUBMED_NBIB_BATCH.md) before collection review.
It retains each native file separately and produces one CSV intake; it does not
infer pagination, choose duplicate resolutions or replace an imported search.

## Prepare, inspect, then explicitly reconcile

`examples/pubmed-export.nbib` is entirely fictional, including its PMID strings,
titles and authors. It has three occurrences with two exact identifier strings.
It is not a retrieved citation set. Use new paths outside the public checkout;
their parent directory must already exist. Replace OUTPUT with that directory,
quote paths with spaces, and run these example commands from the repository root.
The test suite replays all14 commands below and supplies only the explicitly stated
fictional human choices between blocks. No stored hash-bound review chain is added.

For your own file, first [author and check your base](PROTOCOL_SCAFFOLD.md), retain
that ledger-free base unchanged, and substitute it for every bibliographic-base path.
Use your explicitly declared search ID and actual supplied export timestamp instead
of this example's labels. Substitute your local NBIB only at preview; retained wrapper
verification uses its original bytes. Keep real/private material outside this checkout.
The example's choices and dates are never suitable default research decisions.

```sh
python nbib_intake.py preview examples/bibliographic-base.json examples/pubmed-export.nbib --search-id local-primary --searched-at 2026-11-04T00:00:00Z --output OUTPUT/new-nbib.json --text
python nbib_intake.py verify OUTPUT/new-nbib.json --intake-output OUTPUT/new-csv-intake.json --text
python bibliographic_review.py template OUTPUT/new-csv-intake.json --review-output OUTPUT/new-choices.json --text
```

The template deliberately leaves every identity/withholding choice and rationale
unfilled. Inspect the native fields and original file before supplying each row's
`new_record`, `same_record` or `do_not_promote` choice. A repeated PMID does not
choose `same_record` automatically. Different identifiers with similar titles
are not merged. A canonical ID is the human's explicit choice, not necessarily
the generated `pubmed:` label.

For this fictional rehearsal only, fill the three rows in new-choices.json:

| Candidate | Disposition | Record ID | Rationale |
|---|---|---|---|
| csv-row-000001 | new_record | record-A | Fictional operator supplies identity A; not verified. |
| csv-row-000002 | same_record | record-A | Fictional operator explicitly associates this occurrence with A. |
| csv-row-000003 | new_record | record-B | Fictional operator keeps this occurrence separate as B. |

No title comparison or repeated PMID performs these choices. For real work, author
every choice and rationale yourself. Keep `review: null` and prepare a separate review:

```sh
python bibliographic_review.py target examples/bibliographic-base.json OUTPUT/new-csv-intake.json OUTPUT/new-choices.json --review-output OUTPUT/new-review.json --text
```

The new-review.json output retains resolutions and contains a separate `review`
object. Its target hash is already bound; keep it unchanged. Fill reviewer, real
calendar date, rationale and `import_for_screening` only after inspecting that target.
For this rehearsal the test supplies reviewer `Fictional NBIB reviewer`, reviewed_at
`2026-11-04`, rationale `Fictional collection review only; not source authentication.`,
and decision `import_for_screening`. Blanks and wrong targets are refused. Then:

```sh
python bibliographic_review.py assemble examples/bibliographic-base.json OUTPUT/new-csv-intake.json OUTPUT/new-review.json --protocol-output OUTPUT/new-protocol.json --text
```

The imported file has two collected record IDs, three retained native occurrences,
and no screening decisions. Collection identity association is not eligibility.
Supply separate title/abstract decisions, each against its own current target:

```sh
python screening_decision.py target OUTPUT/new-protocol.json --record-id record-A --output OUTPUT/screen-A-target.json
```

Copy only `decision_document` into OUTPUT/screen-A-decision.json and fill every human
field. For this rehearsal: decision `include`, reason `Fictional in-scope assertion.`,
adjudicator `Fictional NBIB screener`, decided_at `2026-11-04`, rationale `Fictional
screening bookkeeping only; no actual reading.`, source_locator `synthetic://screen/A`,
and receipt_id `fictional-nbib-A`. Preserve schema_version, record_id and target_sha256.

```sh
python screening_decision.py assemble OUTPUT/new-protocol.json OUTPUT/screen-A-decision.json --protocol-output OUTPUT/screened-A.json
python screening_decision.py target OUTPUT/screened-A.json --record-id record-B --output OUTPUT/screen-B-target.json
```

Copy that target's `decision_document` into OUTPUT/screen-B-decision.json. For this
rehearsal use the same fictional adjudicator/date/rationale, decision `exclude`,
reason `Fictional out-of-scope assertion.`, source_locator `synthetic://screen/B`,
and receipt_id `fictional-nbib-B`. Do not reuse A's target hash. Real decisions require
actual human assessment; these labels are deliberately invented software inputs.

```sh
python screening_decision.py assemble OUTPUT/screened-A.json OUTPUT/screen-B-decision.json --protocol-output OUTPUT/screened.json
python research_status.py OUTPUT/screened.json
python prisma_audit.py OUTPUT/screened.json --text
python research_bundle.py create OUTPUT/screened.json OUTPUT/new-bundle.zip
python research_bundle.py verify OUTPUT/new-bundle.zip
```

Existing reconciliation requires an unimported common base and an unused planned
search. Later imports use that same base and the current protocol, as documented
in the reconciliation guide. Previewing an already used planned search does not
authorize replacing it. No mock-adapter ledger may be mixed into CSV promotion.

The resulting search remains incomplete. Only the supplied screening choices are
added in the later steps: A included and B excluded. No report, study, evidence,
guideline applicability or development recommendation is created. Withholding a
collection row is not a screening exclusion. File EOF and record counts do not
prove a search total, complete coverage or PRISMA compliance.

The ordinary research bundle does not independently verify the original NBIB wrapper.
Keep new-nbib.json, new-csv-intake.json, the immutable common base, all completed human
inputs, every intermediate protocol and the matching implementation alongside it.
Use [native collection bundles](NATIVE_COLLECTION_BUNDLES.md) when you need the
corresponding native-wrapper archive workflow; ordinary bundle verification is not
that stronger claim. All exported filenames must be new, never silently overwritten.

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

For a single portable archive that verifies both layers and their exact import
association, use the optional [collection bundle](COLLECTION_BUNDLES.md).
It carries explicitly selected native wrappers with the unchanged ordinary
bundle and lists imports for which no native wrapper was supplied.

For a separate inspection copy of the derivative:

```sh
python nbib_intake.py verify OUTPUT/new-nbib.json --csv-output OUTPUT/new-derived.csv --text
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
