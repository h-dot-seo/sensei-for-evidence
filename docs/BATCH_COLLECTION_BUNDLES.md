# Portable native batch collection bundles

`batch_collection_bundle.py` packages explicitly selected
[NBIB batch preparations](PUBMED_NBIB_BATCH.md), every original native file in
those batches, and an unchanged ordinary research bundle in one deterministic
ZIP. Each batch must match the **exact historical CSV intake already retained at
its selected import index**. Packaging does not import records, repair ledgers,
renew reviews or change research decisions.

This is a separate opt-in format. Existing single-file `collection_bundle.py`,
NBIB preparation tools and ordinary research bundles are unchanged, including
their implementation fingerprints. Use the tool for the format actually selected;
no native format or attachment is inferred from column names or source hashes.

For selected RIS and NBIB imports together, use the separate
[explicitly typed native archive](NATIVE_COLLECTION_BUNDLES.md). It preserves
original files and exact import bindings across supported wrapper types. These
older archive formats remain unchanged and do not accept RIS wrappers.

## Package an already reviewed batch

First complete the fictional preparation and explicit collection-review journey
in the batch guide. Retain its `/outside/new-batch.json` wrapper and imported
`/outside/new-protocol.json`. Select the zero-based historical import index:

```sh
python batch_collection_bundle.py create /outside/new-protocol.json /outside/new-batch-collection.zip --batch 0=/outside/new-batch.json --text
python batch_collection_bundle.py verify /outside/new-batch-collection.zip --text
```

For several independently imported batches, repeat `--batch INDEX=PATH`. Each
index must exist and may be selected once. Argument order does not affect archive
bytes because bindings are sorted by import index. In contrast, order **within
a batch** is retained and is part of its original review target. Files belonging
to separate declared searches remain separate imports, not one inferred search.

Paths are explicitly supplied local inputs. No path is taken from artifact text,
source labels, URLs or locators; none of those references is opened. The path after
the first `=` may contain more `=` characters. Local wrapper/protocol filesystem
paths are not written into the archive. Caller-supplied source labels inside a
wrapper remain present exactly as supplied and may themselves contain private text.

## Three linked checks, no new acceptance decision

1. The existing research validators check the entire current protocol and its
   import ledger, including prior human assertions and later valid enrichments.
2. Each selected batch wrapper is fully replayed from its retained original files,
   source labels/order, common-base protocol and supplied timestamp. Its complete
   CSV intake must equal the historical intake reconstructed from the selected
   ledger entry and the ledger's original common base. Matching filenames, PMID
   strings, query text, CSV text alone or native hashes alone is insufficient.
3. Each original-file archive member must be byte-for-byte identical to that
   wrapper's retained source. The complete outer ZIP is regenerated, including
   the unchanged ordinary research ZIP, binding records, summary and manifest,
   and compared against all supplied archive bytes.

The historical common base is deliberately not replaced by the current enriched
protocol. Later screening, result, condition, source-work or planning additions
may remain valid without erasing collection provenance. Altered historical inputs
are rejected, not rebased or repaired.

The binding record includes exact receipt, reconstructed-intake and canonical
wrapper hashes. For every bound native source it records its source index and
label, native byte length/hash, native record-occurrence count and generated
archive path. Source spans still refer to that individual native file. Repeated
PMIDs and identical original files remain separate occurrences, including separate
archive members; no deduplication or publication identity decision is introduced.

## Archive members

- `research.zip`: the unchanged ordinary bundle, retaining exact current protocol
  JSON input bytes and deterministic research outputs.
- `native/import-000000.json`: the selected batch wrapper for import zero. Wrapper
  JSON is normalized; its original JSON whitespace/key order is not preserved.
- `native/import-000000/source-000000.nbib`: the exact first native source file of
  that batch, including its original BOM, line endings, blank separators and any
  missing final newline. Further sources use consecutive zero-based indices.
- `bindings.json`: all import statuses and the explicit source/import links.
- `summary.txt`: attachment counts and boundaries, not a scientific report.
- `manifest.json`: payload byte lengths/hashes and implementation fingerprints.

Every native member path is generated from integer positions, never a source label
or filesystem name. The same bytes under two source labels are stored twice.
Renaming archive entries, reordering wrapper sources or swapping different member contents
invalidates the canonical receipt even if a ZIP program recalculates CRC values
or someone updates editable manifest hashes.

All entries use fixed metadata and uncompressed ZIP storage. Exact protocol
whitespace is intentionally significant, while equivalent wrapper JSON key order
is normalized. Unpacking and re-zipping is not a valid canonical bundle unless
every byte and metadata detail is reproduced. Verification reads in memory and
never extracts files, executes source text, opens locators or calls the network.

## Partial attachment stays explicit

Every existing bibliographic import appears in `bindings.json`. Selected exact
matches have status `NBIB_BATCH_WRAPPER_BOUND`. Other imports have status
`NO_BATCH_WRAPPER_SUPPLIED` and no asserted native sources. They may be ordinary
CSV imports, single-file native imports or unsupplied batch imports. The format
is not guessed. An unselected batch's originals are not invented or reconstructed
from its CSV rows.

The summary separates `bound_batch_wrappers` from `bound_native_sources`, both
counts of supplied attachments. They are not publication counts, search totals,
page counts or proof of complete retrieval. Covering every retained import still
does not establish complete literature coverage, valid identity mappings,
correct screening, reviewer authenticity or scientific validity. Searches remain
incomplete exactly as recorded before packaging.

## Limits, output safety and replay requirements

The outer ZIP and aggregate uncompressed entry size are bounded at 50,000,000
bytes, with at most 100 selected imports and 10,000 original-source occurrences.
Each wrapper still supports at most 100 sources, and all its native/CSV/artifact
limits remain in force. Ordinary research-bundle limits also apply. Retaining
original members in addition to wrappers and protocol provenance duplicates data,
so inputs that pass individually may exceed the combined limit.

Verification rejects missing, extra or duplicate entries, unsafe paths, nonregular
entries, compression, encryption and inconsistent byte/derivation data. Strict
JSON and complete canonical replay reject extra fields and typed substitutions,
not just changed checksums. The implementation fingerprint includes the batch
packager and its intake/research dependencies. Implementation source code is not
embedded: a separate checkout of the recorded code revision is required for
replay, but the original input files and their original locations are not. Use
that revision when any bound implementation bytes have changed; no automatic
migration or review renewal occurs.

The output parent directory must already exist and the output must be new.
Validation and output serialization precede opening it. Creation rejects observed
existing final entries, including dangling symlinks, then uses exclusive binary
open. This is not atomic protection against concurrent path replacement or
parent-directory aliases. A write failure can leave a partial new file.
Verification is read-only. `--text` provides a short summary; JSON is the default.

Checksums are not signatures. A person able to replace all unsigned inputs and
consistently recreate the entire protocol/review history can produce a different
internally consistent bundle. Passing verification is not authentication,
independent scientific review, PRISMA certification or acceptance of research.

## Keep supplied private text private

The archive retains original native text, source labels, protocol and reviewer
assertions without redaction. Abstracts, affiliations and other contents may be
private or restricted for redistribution. Store actual research inputs/outputs
outside this public checkout and check access and rights before sharing.
Only synthetic metadata is shipped and tested. Packaging performs no live
retrieval, clinical recommendation, experimental execution or completeness claim.
