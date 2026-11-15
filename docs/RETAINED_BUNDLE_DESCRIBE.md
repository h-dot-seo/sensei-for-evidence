# Inspect a retained collection or transition ZIP

A received ZIP may have been produced by an older implementation. Its existing
verifier deliberately refuses an implementation mismatch. This separate reader
shows its **supplied, unverified manifest** and the differing implementation file
names without replaying the bundle or weakening that verifier.

From the repository root, with a locally supplied archive:

```sh
python retained_bundle_describe.py OUTPUT/retained.zip
python retained_bundle_describe.py --text OUTPUT/retained.zip
python retained_bundle_describe.py --output OUTPUT/descriptor.json OUTPUT/retained.zip
```

The output path must not already exist. The last command writes JSON and also prints
JSON. With `--text`, stdout is quoted text but the optional file remains JSON.
There is no extraction, network access, imported archive code, or automatic verifier
execution. The displayed verifier command uses the placeholder `BUNDLE.zip`.

## Supported records, not a universal archive reader

Only schema 1 manifests with these seven explicit modes are supported:

| Supplied mode | Existing verifier |
| --- | --- |
| `explicit_native_collection_bundle` | `collection_bundle.py verify` |
| `explicit_nbib_batch_collection_bundle` | `batch_collection_bundle.py verify` |
| `explicit_typed_native_collection_bundle` | `native_collection_bundle.py verify` |
| `explicit_report_transition_bundle` | `report_transition_bundle.py verify` |
| `explicit_extraction_transition_bundle` | `extraction_transition_bundle.py verify` |
| `explicit_appraisal_transition_bundle` | `appraisal_transition_bundle.py verify` |
| `explicit_work_transition_bundle` | `work_transition_bundle.py verify` |

Ordinary research ZIPs are explicitly unsupported here; use
[the separate research descriptor](RESEARCH_BUNDLE_DESCRIBE.md). Other schema
versions, unknown fields, and unsupported inventories are refused. This does not
promise to read every historical or future archive. The original recorded
implementation and its inputs may still be needed for actual replay.

## What the result means

`recorded_unverified` contains the supplied manifest, including its file hashes,
claims and implementation map. `bundle_sha256` hashes the exact received ZIP bytes,
including any trailing bytes. Neither is source authentication. `MATCH` means only
that the supplied implementation map equals the current files' map. `DIFFERS` lists
the union of missing, added and changed names. Neither result is verification.

`verification`, `payload_hash_verification`, `derivation_replay` and
`canonical_zip_verification` remain `NOT_PERFORMED`. Top-level readiness remains
`NOT_READY`. A supplied `READY` or approval-like string stays inside the unverified
record and is not promoted to a scientific, identity, legal, or human-review finding.
No existing readiness, gate, protocol, builder or verifier behavior is changed.

The reader opens only `manifest.json`. ZIP CRC checking applies to that member,
not to other payloads. It checks manifest field shape and declared inventory sizes;
it does **not** hash payloads or open internal research ZIPs, source documents,
bindings, protocols, applications, or chains. A same-size payload alteration may
therefore still be described. Noncanonical but readable ZIP bytes, including trailing
bytes, are not certified or necessarily refused. Use the existing verifier separately
for its stronger checks, with the required original implementation when appropriate.

## Limits and privacy

Input ZIP bytes and total declared uncompressed entry bytes are each limited to
50,000,000 inclusive. Before reading the manifest, the reader limits inventory count
to 10,104 and refuses duplicate/unsafe names, directories, unsupported file types,
encryption, compression other than STORED, and unequal compressed/uncompressed sizes.
After parsing, a family-specific aggregate entry ceiling, allowed names and
required fixed entries apply. Individual binding/source counts, numbering continuity
and semantic relationships are not checked. Names are fixed or strictly numbered relative paths.
The manifest uses the existing strict JSON parser and its nesting limit. Its
implementation map has 1–512 lowercase module names (at most 128 characters each)
and lowercase 64-digit SHA-256 strings. Manifest boundary/assertion strings have a
4,096-character limit. Unknown fields, boolean sizes and duplicate file rows fail.

JSON and quoted text each have a 16 MiB UTF-8 output limit. Text quotes control
characters rather than treating supplied text as terminal commands. Supplied manifest
text can still contain private information: it is **not redacted**. Do not share the
descriptor without reviewing that content. No claim is made about total CPU or memory
safety, authenticity, canonicality, or complete hostile-archive containment.

Caught input/output errors produce a fixed stderr message, empty stdout and exit 1;
argument usage errors use exit 2. Successful description uses exit 0 even when the
implementation differs, because no verification occurred. Output creation is exclusive
and refuses existing entries, but is not an atomic transaction; a failed write can
leave a partial file. The reader never rewrites the archive or renews any decision.
