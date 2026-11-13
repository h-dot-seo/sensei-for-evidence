# Explicit RIS continuation dialect

This separate parser/wrapper accepts only the operator-declared
`ris-untagged-continuation-empty-paragraphs-v1` dialect. It does not guess a
reference-manager product or claim exporter compatibility. The fixture is entirely
fictional. Use the existing [strict RIS route](RIS_INTAKE.md) for its original grammar.
Neither verifier accepts the other wrapper. Existing strict RIS implementation
bytes and native archive formats are unchanged.

## Grammar and rejection boundaries

| Byte/text pattern | Declared continuation dialect |
| --- | --- |
| Strict UTF-8, optional initial BOM, LF/CRLF/CR terminators | Retained exactly |
| `TY  - JOUR` and empty `ER  -` framing | Required; no TY continuation or implicit closing |
| Uppercase two-character tag, two spaces and hyphen | Ordered separate field; unknown tags retained |
| Untagged line inside open record after non-TY field | Literal continuation of that field |
| Six-space continuation | Six spaces removed only from value; raw bytes retained |
| Empty line after non-TY field inside record | Empty paragraph value, never discarded |
| Empty line outside record | Retained as separate blank span |
| Untagged line outside record or after TY | Rejected with line number |
| One-space tag padding, lowercase or 3–4-character tag-like prefix, indented malformed tag | Rejected with line number, not repaired |
| Any tab, invalid UTF-8 or NUL | Rejected |

Tag-like means optional whitespace followed by one to four ASCII alphanumeric
characters followed by whitespace and a hyphen, or an immediately adjacent
hyphen followed by whitespace/end-of-line. This intentionally conservative
boundary can reject narrative such as `A - sentence`; select another source route,
not silent repair. A valid unindented `AB  - ` inside abstract text becomes a
separate preserved field. `ER  -` closes the record; following untagged text then
fails as an orphan. Such text is never silently discarded. Whitespace-only lines
other than empty lines are literal continuations when permitted (tabs still fail).
Resource limits remain 10 MB, 100,000 records and 200,000 physical lines.

## Synthetic walkthrough

Run from the repository root. Replace `OUTPUT` with an existing empty directory
outside the checkout. Outputs must not already exist. The dialect is mandatory;
verification reads the bound dialect from the wrapper rather than guessing it.

```sh
python ris_continuation_intake.py preview examples/source-work-protocol.json examples/dialects/continuation.ris --dialect ris-untagged-continuation-empty-paragraphs-v1 --search-id search-primary --searched-at 2026-11-04T00:00:00Z --output OUTPUT/continuation.json --text
python ris_continuation_intake.py verify OUTPUT/continuation.json --intake-output OUTPUT/continuation-intake.json --text
python bibliographic_intake.py verify OUTPUT/continuation-intake.json --text
python bibliographic_review.py template OUTPUT/continuation-intake.json --review-output OUTPUT/continuation-review.json --text
```

Stop at the unfilled review template. Identity choices, exact-target human review
and any later protocol update remain separate explicit work. No search completion,
source authenticity, deduplication, publication identity or scientific conclusion
is established. IDs and inert locators name file occurrences only. URLs and
attachment values are never opened. Repeated tags and occurrences stay separate.

The wrapper retains original full-file bytes as exact UTF-8 text, field and record
raw text, physical-line/byte spans and hashes, the deterministic CSV derivative,
explicit dialect in `mode` and `source_export.format`, and implementation hashes.
Verification reconstructs all fields. Hash consistency is not source authentication.
The unchanged CSV core cannot independently verify native provenance. Retain this
wrapper and the original export separately: neither existing NBIB nor typed
[native archives](NATIVE_COLLECTION_BUNDLES.md) accept this dialect. Do not change
an archive format label to force admission. Native archive support is deferred.
Store real exports and outputs outside this public repository; no redaction is
performed. This route makes no network calls and does not mutate the protocol.
