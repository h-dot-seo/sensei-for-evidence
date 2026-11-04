# Explicit local report-source byte checks

A supplied `report_sources.document_sha256` is a claim. The separate
`report_source_check.py` command can compare that claim with bytes in an explicit
local file. It does not fetch or parse a document, infer reading, authenticate a
publisher, adjudicate eligibility or change the working protocol.

This bounded command uses the existing secure local artifact checker. Byte checks
require POSIX descriptor-relative no-follow file access. Native Windows and other
unsupported environments **fail closed without inspecting sources**; template
creation remains available. There is no weaker platform fallback.

## Reproduce the fictional example

```sh
python report_source_check.py template examples/report-source-check-protocol.json --source-id=source-main --output /outside/new-source-template.json
python report_source_check.py check examples/report-source-check-protocol.json examples/report-source-check-manifest.json --root examples/local-sources --text
python report_source_check.py check examples/report-source-check-protocol.json examples/report-source-check-manifest.json --root examples/local-sources --output /outside/new-source-observation.json
```

Use a new output path in an existing directory. Outputs are created exclusively;
existing files, including inputs, are never overwritten. A disk-full or write
failure may leave a newly created partial output; creation is not an atomic commit.
`--output` always saves
JSON and `--text` only changes stdout. The saved template is an envelope: copy its
`manifest` object to a separate manifest file and fill its deliberate nulls.
The whole template envelope is not a valid manifest.

The checked-in 225-byte text file is explicitly fictional and contains no article,
scientific result or experiment. Its mapped source matches the declared digest.
A source with a null digest and another unselected source remain uninspected.
Real/private documents, manifests and generated observations belong outside this
public repository. No source content is emitted or transmitted by this command.

## Explicit manifest and human mapping

The manifest has exactly these fields:

```json
{
  "schema_version": 1,
  "sources": [
    {
      "source_id": "source-main",
      "report_id": "report-one",
      "source_descriptor_sha256": "a-current-descriptor-fingerprint-from-the-template",
      "path": "fictional-report.txt",
      "bytes": 225
    }
  ]
}
```

The placeholder fingerprint is deliberately invalid. A real fingerprint is the
SHA-256 of the complete canonical source descriptor, including exact source/report
IDs, locator, version and declared document digest. It is not the document-byte
hash and cannot be substituted for a report-review or study-review source hash.
Changing a descriptor requires explicitly reviewing the mapping and generating a
new template. Object-key order is ignored; literal values remain significant.

1. Keep a dedicated, trusted, quiescent directory with only the documents you want
   to inspect. Use only material you are authorized to access.
2. Select exact declared source IDs. A template fills the source/report IDs and
   descriptor fingerprint, leaving `path` and `bytes` null for a person to supply.
3. Confirm the local file actually represents the declared source. The software
   does not establish that relationship merely because the operator mapped it.
4. Enter the portable relative path and exact nonnegative byte count in a separate
   manifest. Paths are never inferred from `source_locator`, even if it looks like
   a file path or URL.
5. Run the check and review its separate observations. Keep actual reading,
   source-authenticity checks and human eligibility judgments separate.

A null `document_sha256` has no comparison expectation. It receives source-first
guidance rather than a checkable scaffold. The checker rejects it even if a
manifest supplies a current descriptor fingerprint. Establish the expected digest
through a separate explicit source-declaration process; this command never
computes a new declaration, silently updates one or renews any human assertion.

Each selected source ID and case-folded relative path must be unique. The report
ID must match that source's descriptor. Unknown IDs, extra/missing fields, stale
fingerprints, duplicate mappings, Boolean/fractional sizes, traversal, absolute
paths, URL paths and protected metadata paths are rejected. All protocol and
manifest metadata are validated before any source directory is opened, including
unselected report/result links and later manifest entries.

## What an observation establishes

The detached result retains the selected descriptor, descriptor fingerprint,
current report source-basis hash, supplied retrieval label and explicit manifest
mapping. Each inspected entry reports one of:

- `BYTES_MATCH`: measured byte count and SHA-256 match supplied expectations.
- `HASH_MISMATCH` or `SIZE_MISMATCH`: local bytes differ from an expectation.
- `MISSING`: the mapped file is absent.
- `REJECTED_FILE_TYPE` or `UNREADABLE_OR_UNSAFE_PATH`: the checker did not accept
  the local path or file type.
- `CHANGED_DURING_READ`: observed file size/metadata changed during inspection.

Observed hashes are absent when no complete stable read was obtained. Empty
manifests are not success. `all_requested_bytes_match` concerns only nonempty
explicit selections; it says nothing about unlisted source IDs, which remain in
`uninspected_source_ids`. A check exits nonzero when any selected entry does not
match or when selection is empty, while still returning/saving a valid observation
for ordinary mismatch/missing-file outcomes. Invalid metadata or unsupported access
fails without creating an output observation.

The result includes whole protocol, manifest and implementation fingerprints,
including the reused checker. Its report source hash retains mapped search/CSV
provenance, but the descriptor-bound file manifest does not freeze all research
criteria. Later criteria changes can leave the same file mapping valid while
changing that report context. Different identifiers are never merged because
hashes match; equal bytes do not establish one underlying study or source identity.

`EXPLICIT_MANIFEST_ONLY` describes the scope of attempted local comparison, not
successful verification of every source. The result is an unsigned, editable,
point-in-time observation. It is not an authenticated receipt, proof of historical
reading, persistent proof of future file state, or verification of scientific
claims, authorship, eligibility or document rights. An unavailable retrieval label
is preserved even if the operator supplied matching local bytes.

## Filesystem and publication boundaries

Limits are 1,000 selected entries, 10,000,000 bytes per file, 50,000,000 aggregate
expected bytes, and 50,000,000 bytes per JSON input file. These bound byte volume,
not elapsed time on a stalled or network filesystem. Symlinked roots, parent
components or files, hardlinks, directories and FIFOs are not accepted. The reused
checker detects selected identity/size/time changes during reading. It is not a
security boundary against a privileged concurrent filesystem attacker.

Results omit source contents and the explicit absolute root. They retain supplied
source metadata, relative mappings and hashes, which can still be sensitive.
Review outputs before sharing; omission of document text is not anonymization.
Filesystem diagnostics do not repeat absolute paths or source content.

No observation is ingested into the canonical protocol or seven-file research
bundle. Ordinary review/inventory views still correctly say their supplied digests
are unverified and `document_bytes_verification` is `NOT_PERFORMED`. Existing
semantic hashes, counts, CSV exports, queues and bundle bytes remain unchanged.
The separate command's result must not be relabeled as human review completion.

## Adding a separate source declaration

[Reviewed source declaration intake](MANUAL_SOURCE_DECLARATIONS.md) can append a
new descriptor to an already retrieved report. It does not compute an expected
digest or replace an older null-digest row. Existing descriptors remain separate;
a matching byte check for one new source does not verify the whole catalog.
