# Keep original and converted-text declarations separate

A PDF hash cannot validate a UTF-8 conversion. First declare the original and the
converted representation as different sources for the same retrieved report, using
[reviewed source declarations](MANUAL_SOURCE_DECLARATIONS.md). Supply the actual
representation's digest, and record the conversion tool/version, original source ID,
process and uncertainties in `document_version` and the reviewed `declaration_note`.
No conversion tool is selected, installed or executed by Sensei. Never substitute a
PDF hash for the text bytes or treat matching text as faithful scientific conversion.

The result candidate must explicitly select the converted-text source. The original
need not be selected for passage reading. Existing passage `template` still produces
strict version1 and blank human choices. To opt into declared conversion context,
make the manifest `schema_version: 2`; every source mapping must then include
`derived_from`, either null (no association supplied) or an object with exactly:

- `source_id`: a different source already declared for this same report.
- `source_descriptor_sha256`: the exact canonical hash of that complete declaration.

Obtain this descriptor hash from the existing [source-check template](REPORT_SOURCE_CHECK.md),
not by inventing a value. No copied `document_sha256`, path, tool label or extra keys
are accepted in the reference. The original declaration must have a nonnull digest.
Unknown, self-referential, cross-report or stale references fail before source access.
The whole protocol, candidates and manifest are validated first. A descriptor edit
requires deliberate new binding and review of the association, never automatic repair.

## Fictional local rehearsal

The two new JSON fixtures explicitly declare an original representation with an
invented hash; its bytes are deliberately absent. This is not a real PDF, OCR result
or proof of conversion. They reuse the existing fictional UTF-8 source and manual
result candidates. Use an existing OUTPUT directory outside the public checkout:

```sh
python result_passage_check.py catalog examples/derived-passage-protocol.json examples/result-passage-candidates.json examples/derived-passage-manifest.json --root examples --output OUTPUT/derived-catalog.json --text
python result_passage_check.py check examples/derived-passage-protocol.json examples/result-passage-candidates.json examples/derived-passage-manifest.json --root examples --output OUTPUT/derived-passages.json --text
```

Source-byte access still requires the existing POSIX descriptor/no-follow contract.
Native Windows fails closed, with no weaker fallback. Tests expect that refusal on
unsupported platforms; these commands do not claim native Windows passage support.

Version2 observations keep the text's supplied and observed hashes beside a
`conversion_context` containing the exact supplied original descriptor and its hash.
`conversion_verification` and `original_bytes_check` are fixed `NOT_PERFORMED` for
this reference. Its locator is never opened. Only mapped text paths are read.
If the original also has its own explicit source mapping, that independent mapping
is handled normally, not verified by the conversion reference.

The association is supplied bookkeeping: chronology, conversion fidelity, transitive
lineage, semantic support, reading and scientific acceptance are not established.
It is not a recursively validated conversion graph. Null is not a verified absence
of conversion. Text mismatch, byte mismatch and uncheckable-source reports retain
their existing negative-result behavior; context is not approval to ignore them.

Version1 remains strict and does not accept `derived_from` or emit conversion context.
Version2 is explicit opt-in; its output is schema2, while unrelated schema2 tools are
unchanged. In-memory and saved version1 observation bytes have a changed checker hash,
so retain the original implementation to reproduce old observations. No ENGINE_FILES,
canonical fields, intake reviews or source declarations are changed by checking.
The existing exclusive-output, pre-read output-size budget and privacy limits apply.
