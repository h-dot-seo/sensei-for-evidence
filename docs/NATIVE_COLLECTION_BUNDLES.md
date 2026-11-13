# Carry selected RIS and NBIB originals with their exact imports

`native_collection_bundle.py` creates a portable snapshot of an existing protocol,
its ordinary research ZIP, explicitly selected native wrappers, and every original
file retained by those wrappers. It supports only these explicit formats:

- `ris`: one wrapper from `ris_intake.py`, with its single supported-subset RIS file.
- `nbib`: one wrapper from `nbib_intake.py`, with its single supported-subset NBIB file.
- `nbib_batch`: one wrapper from `nbib_batch_intake.py`, with all its ordered NBIB files.

The original intake, review and archive engines are unchanged. This is a new
archive format, not a conversion of old ZIPs, a new intake format, or a replacement
for separate human collection review. Existing NBIB-only archive verifiers do not
accept this format, and this verifier does not reinterpret their archives.

The practical benefit is keeping a supplied RIS file's exact full bytes, including
BOM and separators, together with its reviewed CSV import and current research
snapshot. A mixed-source project can carry selected supported RIS/NBIB imports in
one archive. No source file, wrapper format, import index or identity is guessed.

## Archive the supplied RIS rehearsal

First follow [RIS intake and explicit reconciliation](RIS_INTAKE.md). Use the exact
wrapper and resulting protocol from that workflow, an existing output directory
outside this repository, and a new output filename:

```sh
python native_collection_bundle.py create /outside/new-ris-protocol.json /outside/new-ris-native.zip --ris 0=/outside/new-ris-wrapper.json --text
python native_collection_bundle.py verify /outside/new-ris-native.zip --text
```

Replace `/outside` with your actual directory and quote arguments containing
spaces. The index is zero-based in `bibliographic_imports.imports`, not the planned
search list or native record list. For this specific rehearsal, the single new
import is index 0. The four raw occurrences and their supplied three promoted/one
withheld choices remain in the ledger. The two canonical search memberships still
await screening; the search stays incomplete. Archiving changes none of them.

Move or copy the resulting ZIP to another directory and verify it there with the
recorded implementation available. Original input filesystem paths are not needed:
the archive retains the protocol, wrappers and original native bytes. Keep the exact archive bytes; a differently serialized ZIP is a different byte
receipt. Reconstructing identical canonical ZIP bytes is still valid.

## Select mixed formats explicitly

For an already reviewed project with RIS at import 0, single NBIB at import 1 and
NBIB batch at import 2, the shape is:

```sh
python native_collection_bundle.py create CURRENT.json NEW.zip --ris 0=RIS_WRAPPER.json --nbib 1=NBIB_WRAPPER.json --nbib-batch 2=BATCH_WRAPPER.json --text
python native_collection_bundle.py verify NEW.zip --text
```

These uppercase names are placeholders, not repository fixtures or a claim that
those imports exist in your protocol. Inspect the actual ledger and select the
retained wrappers deliberately. Each flag can be repeated. Supply at least one
selection and at most 100; an import index can appear only once across all flags.
The order of selections does not change the archive bytes. The declared format,
not the wrapper filename extension or contents, selects the existing verifier.
Wrong formats are rejected rather than retried as another format.

A valid wrapper for another search or timestamp cannot be substituted, even when
it retains identical original bytes. A selected wrapper's **entire** CSV intake
must match the historical ledger intake, reconstructed with its original common
base. Search name, file hash, record count or identifiers alone are not enough.
Later valid screening/report/result enrichment can remain in the current protocol;
the native wrapper is still checked against that import's historical base.

Every current import appears in `bindings.json`. Selected ones are
`NATIVE_WRAPPER_BOUND` and identify the explicit format. Unselected ones are
`NO_NATIVE_WRAPPER_SUPPLIED`, with no inferred format. Such imports might be plain
CSV or native imports whose wrappers were not supplied. An uncovered import is
not evidence of a missing database search, and full wrapper coverage is not a
complete literature search, complete history or readiness for conclusions.

## Retained files and exact replay

The ZIP contains:

- `research.zip`: the unchanged ordinary research archive, including the exact
  input protocol bytes and its normal derived outputs.
- `native/import-NNNNNN.json`: the selected wrapper in deterministic JSON form.
  Its input JSON whitespace/key order is normalized, not retained verbatim.
- `native/import-NNNNNN/source-NNNNNN.ris` or `.nbib`: the exact original source
  bytes from that wrapper. Source paths are generated only from bounded indices
  and the explicit supported format, never labels, URLs or filenames.
- `bindings.json`: the exact import receipt and canonical intake/wrapper hashes,
  source occurrence metadata, and explicit covered/uncovered import indices.
- `summary.txt` and `manifest.json`: the bounded summary, payload byte hashes and
  exact implementation fingerprints.

Single-file wrappers have one derived source index 0 and no invented source label.
NBIB batch source labels and order remain exactly as supplied, as inert metadata.
Repeated original files and repeated records stay separate. The archive does not
deduplicate, choose an identifier, or turn RIS occurrence labels into publication
identity. Supported grammar and parser limits remain those of each intake; this
adds no RIS dialect support, multi-file RIS intake, or mixed-format search intake.

Verification strictly decodes the retained JSON, checks the allowed regular stored
ZIP members and resource bounds, validates the full current protocol and its
historical receipts, and invokes each explicitly selected wrapper's own verifier.
It checks the exact CSV association, regenerates the ordinary research ZIP and all
native members, and compares the **entire canonical ZIP bytes**. Merely resealing
editable file hashes cannot make a changed derived output consistent. Altered
metadata, compression, ordering, extra/missing members, prefix/trailer bytes and
re-zipping that changes archive bytes fail too. No archive is extracted, supplied code loaded, or source
locator opened. URLs and attachment paths remain inert text.

The verifier fingerprints the union of all supported native intake implementations,
the ordinary research engine, and this archive module. A change in any one of these
files, including a format not selected in a particular archive, requires the
recorded implementation to verify that old receipt. The ZIP does not embed or
install Python/code. Retain the matching repository revision separately. These
hashes are internal consistency receipts, not signatures, human authentication or
proof of provider origin. An actor who changes all supplied inputs can construct
a different internally consistent archive.

## API, safety and unsupported scope

Python callers use `build_bundle(protocol_raw, bindings)` and `verify_bundle(raw)`.
`protocol_raw` and the archive are exact bytes. Each binding is a plain dictionary
with exactly `import_index` (nonnegative integer, not Boolean), `format` (one of
`ris`, `nbib`, `nbib_batch`) and `artifact` (the plain wrapper object). A nonempty
plain list contains the selections. `create(protocol_path, destination, bindings)`
reads the explicit protocol path, builds and exclusively creates the output.
No API changes any protocol object or research decision.

The final archive, combined payload data and CLI output are each bounded by
50,000,000 bytes. There are at most 100 bindings and 10,000 retained native source
occurrences; each selected wrapper must satisfy its own smaller source, record,
line, CSV-field and artifact bounds. The original protocol and repeated nested
native metadata can consume the limit before the original files do. The tool uses
in-memory construction; these are file-size limits, not a fixed memory/CPU ceiling
or a general-purpose hostile-ZIP sandbox.

Serialization and stdout rendering are checked before writing. Output uses final-
entry inspection and exclusive creation: existing files, directories and observed
dangling symlinks are refused; inspection errors are not bypassed. This is not an
atomic transaction or a defense against concurrent ancestor/path replacement. A
write failure may leave a partial new file. Shell redirection has separate risks.

This archive does **not** retain detached applications or every intermediate
protocol, complete research history, downloaded documents, permission to redistribute
sources, or independently reviewed scientific conclusions. There is no automatic
review renewal, eligibility decision, source/reviewer authentication, query/date
verification, search completion, publication identity verification or PRISMA
compliance claim. Full-text and result-transition receipts still need their own
retention. Census stays `NOT_ESTABLISHED`; conclusion readiness stays `NOT_READY`.
All source text and metadata are retained without redaction. Keep private or real
research and generated archives outside this public repository.

The separate [explicit continuation dialect](RIS_CONTINUATION_INTAKE.md) is
not admitted to existing native archives; keep its wrapper separately. Its parser
does not relax or replace the strict RIS route documented here.
