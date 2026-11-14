# Read a received research archive before replay

A research ZIP may come from an older implementation. Its verifier will correctly
refuse replay under different engine bytes. This reader shows its recorded context
without extracting files or running code stored in the archive. Use OUTPUT as an
existing directory outside the checkout for this fictional rehearsal:

```sh
python research_bundle.py create examples/review-demo.json OUTPUT/received.zip
python research_bundle_describe.py OUTPUT/received.zip
python research_bundle_describe.py OUTPUT/received.zip --text
```

`recorded_unverified` contains the recorded flow, gates hash and open gate IDs.
Missing or explicitly null fields remain null, never zero or an empty queue.
Question/version are supplied strings. `protocol_sha256` is computed from canonical
protocol JSON; `bundle_sha256` hashes the supplied ZIP. The recorded input hash is
copied, not compared to the protocol. These are different hash scopes, not signatures.
The implementation comparison includes missing/extra names; MATCH is only equality
with this checkout's engine map, not archive validity or derivation verification.

This tool accepts only the ordinary research schema2 manifest and exactly seven
named entries. Collection/batch/native/transition bundles and schema1 prototypes are
not supported. Entry types must be regular Unix-created STORED files, not encrypted,
with equal stored/uncompressed sizes. Each JSON is parsed strictly. No entry is
extracted. The reader reads manifest/protocol/research only; ZIP CRC errors in these
reads can reject corruption, but other payloads and their manifest hashes are NOT
verified. No canonical repacking or derived output replay occurs. A changed recorded
flow with plausible types can still be displayed, explicitly unverified.

Limits: 50,000,000 aggregate declared entry bytes, 51,000,000 archive bytes (separate
metadata allowance),16,000,000 output bytes. Serialization completes before stdout.
These are byte bounds, not total-memory or runtime guarantees. The engine generator's
entry limit remains unchanged. This trusted-file reader is not a concurrent filesystem
sandbox and has no special-file read timeout. Errors exit1 with fixed non-echoing text
and no stdout; successful description, even DIFFERS, exits0. Usage errors remain
argparse. JSON escapes control characters; text quotes supplied values. Normal reports
may contain private questions or other supplied data. No file output option is provided.

For actual verification, preserve the original bytes and use
[implementation inspection](IMPLEMENTATION_REVISIONS.md) to locate matching trusted
code, then follow the [research bundle verifier](USAGE.md#portable-offline-research-bundle).
The reader does not execute historical code, select a revision, repair hashes, reopen
work, close gates, approve sources or establish readiness. Its census/readiness claims
are fixed NOT_ESTABLISHED/NOT_READY regardless of recorded values.
