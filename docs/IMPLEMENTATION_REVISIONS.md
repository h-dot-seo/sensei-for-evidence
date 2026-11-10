# Inspect recorded implementation revisions

When an old bundle or detached record fails replay after an update, inspect its
recorded implementation bytes without running anything from the selected checkout.
This diagnostic is outside `research_bundle.ENGINE_FILES`; it never repairs inputs,
ignores drift, invokes a verifier, reads Git metadata or downloads historical code.

The following rehearsal uses the entirely fictional review-demo protocol. Create
OUTPUT as an existing directory outside this checkout. These commands are tested
exactly as written; no real research data is included.

```sh
python research_bundle.py create examples/review-demo.json OUTPUT/review-demo.zip
python implementation_check.py inspect OUTPUT/review-demo.zip --manifest PUBLICATION_MANIFEST.json
```

Use `--engine-root DIR` to compare an explicitly supplied local source directory.
Use repeatable `--manifest FILE` to compare supplied publication inventories. A
manifest MATCH means every recorded name/hash pair appears in its files list;
release and date are supplied labels, not authenticated provenance. This is not
full publication-manifest validation. No tags are presumed to exist or created.
Manifest candidates do not change the exit status: they help locate a revision
when the selected directory differs.

The inspector walks strict JSON for every nested `engine_sha256` and
`implementation_sha256` map, plus `adapter_receipts.adapter_engine_sha256` as
`offline_adapter.py`. Each declaration retains its escaped JSON pointer, including
conflicting repeated declarations. ZIP input reads only one top-level manifest.json
in memory, never extracts entries and does not verify archive payloads.

Recorded names must be bare ASCII letters, digits or underscores followed by `.py`;
hashes must be 64 lowercase hexadecimal characters. Invalid declarations are shown
as INVALID and never used as paths. Source files and their ancestors must not be
links, Windows reparse points or junctions. Missing files are MISSING; changed
bytes are DIFFERS. A complete report precedes exit 1 for differences, invalid inputs
or NO_HASHES. Exit 0 means only that every recorded file matches. `--text` safely
quotes supplied values. The command writes no output files; JSON goes to stdout.

Bounds are 50,000,000 input bytes, 5,000,000 JSON/manifest bytes, 5,000,000 bytes per
source file, 100,000 JSON nodes/archive entries and 10,000 hash declarations.
Malformed JSON, duplicate keys, nonfinite numbers, oversized or encrypted manifests
fail closed. Corrupt DEFLATE, BZIP2 or LZMA manifest data produces the same INVALID
report with exit 1, in JSON or quoted text, without a decoder traceback. Filesystem
checks are not a sandbox against concurrent path replacement; inspect stable
directories under your control.

The report lists candidate verify usage from the current command reference for
recorded modules. These are hints, not artifact-type detection: retained wrappers
may contain several modules. Read the matching historical command documentation,
then separately run that artifact's verifier from a trusted matching directory.
Detached application verifiers commonly also need the original protocol; matching
implementation bytes do not check those inputs or remove that requirement.

MATCH is byte identity only, not verification, authentication, release provenance
or a signature. Unhashed imports and the Python runtime are not covered. No model,
network or scientific assessment is performed. Census remains NOT_ESTABLISHED and
conclusion readiness remains NOT_READY. Preserve the recorded source revision;
never edit an old artifact's hashes to make it match a newer implementation.
