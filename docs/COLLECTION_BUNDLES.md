# Portable native collection bundles

`collection_bundle.py` packages an existing research protocol and explicitly
selected NBIB preparation artifacts together. It checks that each native
artifact produced the **exact CSV intake already retained at the selected import
index**, then carries both the ordinary research bundle and native artifacts in
one deterministic archive. It neither imports new records nor changes any
screening, extraction, source-review or work-package assertion.

This closes a portability gap in [NBIB preparation](PUBMED_NBIB_INTAKE.md): the
ordinary research bundle retains CSV provenance but does not independently
verify the separate native wrapper. Ordinary bundles remain unchanged. The new
opt-in collection bundle verifies both layers and their exact association.

This format accepts single-file wrappers only. For multi-file batch wrappers and
their separate original-source members, use the independent
[batch-native collection format](BATCH_COLLECTION_BUNDLES.md). Existing single-file
archive bytes and replay rules are unchanged.

For selected RIS and NBIB imports together, use the separate
[explicitly typed native archive](NATIVE_COLLECTION_BUNDLES.md). It preserves
original files and exact import bindings across supported wrapper types. These
older archive formats remain unchanged and do not accept RIS wrappers.

## Use existing, explicitly reviewed collection records

First complete the fictional NBIB preparation and explicit reconciliation journey
in the NBIB guide. Its outputs are a native preparation artifact such as
`/outside/new-nbib.json` and an imported protocol such as
`/outside/new-protocol.json`. Select the protocol's zero-based import index:

```sh
python collection_bundle.py create /outside/new-protocol.json /outside/new-collection.zip --nbib 0=/outside/new-nbib.json --text
python collection_bundle.py verify /outside/new-collection.zip --text
```

For several retained imports, repeat the option:

```sh
python collection_bundle.py create /outside/current-protocol.json /outside/new-collection.zip --nbib 0=/outside/first-nbib.json --nbib 2=/outside/third-nbib.json --text
```

Paths must refer to local files selected by the operator. No path is inferred
from a locator, URL, artifact content or record identifier. Local filesystem paths
are not written into the archive. The path after the first `=` can itself contain
`=`. The output must be a new file with an existing parent directory. Creation
is exclusive, including existing symlinks. Validation and serialization finish
before opening it; an operating-system write failure can still leave a partial
new file. Nothing is uploaded or shared automatically.

The protocol must already contain a valid bibliographic import ledger. At least
one native binding is required. Each explicit import index must be an existing
integer index and can appear only once. Argument order does not affect archive
bytes; bindings are sorted by index. A native artifact that has not yet been
imported cannot be attached as if it were part of the collection.

## Exact historical association

For each selected import, the tool reconstructs its full CSV intake from the
retained import entry and the ledger's original common-base protocol. That
reconstructed intake must exactly equal the native wrapper's `csv_intake` under
canonical JSON comparison. It is not enough to share a PMID, title, query, search
ID, native-file hash or derived CSV text.

This comparison deliberately uses the **historical common base**, not the current
enriched protocol. Later valid screening, result, condition or planning additions
do not erase earlier collection provenance. Existing protocol integrity rules
still validate all retained imports and human assertions. An altered historical
base or receipt is not repaired by this packaging operation.

The generated binding record includes the import index, exact receipt hash,
canonical reconstructed-intake hash, canonical native-wrapper hash, original
NBIB byte hash and internally generated archive member path. Native verification
replays parsing and CSV derivation; ordinary bundle verification replays research
outputs. Neither process authenticates who supplied or reviewed the input.

## Explicit partial attachment

Every bibliographic import is listed. Selected, verified matches are labeled
`NATIVE_WRAPPER_BOUND`; all others are `NO_NATIVE_WRAPPER_SUPPLIED`. Covered and
uncovered import indices are shown separately.

An uncovered import is not automatically an invalid NBIB import. It may be an
ordinary CSV import, or its native wrapper may simply not have been supplied.
NBIB-looking column names do not establish origin. Even binding every retained
import does not establish complete literature coverage, correct query execution,
publication identity, correct screening or scientific validity. Search completion
and all existing research decisions remain unchanged.

## Archive and verification contract

The archive contains:

- `research.zip`: the unchanged ordinary research bundle, preserving the exact
  supplied current protocol JSON bytes and its deterministic derived outputs.
- One native-wrapper JSON member per selected import, under an internally
  generated `native/` path. Wrapper JSON is reserialized deterministically;
  whitespace/key order of the supplied wrapper JSON file are not preserved.
  Its retained NBIB source text still re-encodes to the exact original native bytes.
- `bindings.json`: exact associations, all-import attachment status and explicit
  limits on the claims being made.
- `summary.txt`: a readable attachment summary and research boundaries.
- `manifest.json`: exact payload byte lengths/hashes and implementation fingerprints.

All entries use fixed metadata and uncompressed ZIP storage. The archive is
deterministic for the same protocol bytes and semantically identical native
artifacts. Different protocol whitespace is deliberately a different input.
Unpacking and re-zipping with different metadata is not a valid canonical bundle.

Verification works in memory without extracting files. It rejects unexpected,
missing or duplicate entries, unsafe member names and unsupported ZIP metadata,
then checks payloads, every native artifact, the ordinary research bundle and
the exact import associations. It rebuilds the archive and compares the complete
bytes. Updating only editable hashes cannot legitimize a changed summary,
association or derived output. A wholly replaced, consistently reauthored set of
unsigned inputs can still produce a different internally consistent archive;
hashes are not signatures or independent source attestations.

The maximum archive size and aggregate uncompressed payload size are 50,000,000
bytes, with at most 100 selected bindings. Existing protocol, NBIB, CSV and
ordinary-bundle limits also apply. Native wrappers duplicate some data already
in the protocol, so individually acceptable inputs may exceed the combined
limit. Invalid or oversized builds do not create the output. Verification needs
the recorded implementation revision if any bound code bytes have changed.

## Keep private research private

The bundle retains the entire supplied protocol, original NBIB text and reviewer
assertions without redaction. Abstracts, affiliations and other supplied content
may be private or subject to redistribution limits. Store real inputs and outputs
outside this public repository and review access and rights before sharing.
Only fictional records are used in validation. There are no external calls,
medical fact checks, generated experimental instructions or automatic claims of
search completeness, clinical validity or research readiness.
