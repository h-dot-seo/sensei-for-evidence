# Opt-in local artifact byte review

A work package's artifact_locator is ordinarily just a supplied assertion.
`artifact_review.py` optionally checks local bytes without opening that locator as
a URL or inferring a file path. Supply a separate manifest and a dedicated root:

```sh
python artifact_review.py examples/artifact-review-protocol.json examples/artifact-review-manifest.json --root examples/local-artifacts
```

This offline synthetic example hashes a fictional receipt-review note while its
WP remains IN_PROGRESS. No real paper, model, browser, network or credentials are
used. The interrupted receipt and missing search remain unresolved. The output
includes the WP question, deliverable, acceptance criterion, dependency/blocked
assertions and byte-check results for human comparison. No criterion is assessed.

## Explicit input contract

The manifest has exactly `schema_version: 1` and an `artifacts` list. Each entry
has exactly work_package_id, artifact_locator, path, bytes and sha256. See
`examples/artifact-review-manifest.json` for the complete input format.

- Work IDs must exist and be unique; the locator must exactly match that WP's
  supplied artifact_locator. There is no guessed locator-to-path mapping.
- Paths are canonical POSIX-style relative file paths inside the explicit root.
  No absolute artifact paths, parent traversal (also rejected in root spellings), URLs, backslashes, alternate data streams,
  control characters, duplicate/case-colliding paths or protected metadata paths.
- Expected bytes must be a non-boolean integer, 0–10,000,000 per file and at most
  50,000,000 total. At most 1,000 artifact entries and 50,000,000 bytes per CLI
  input JSON are accepted. Expected SHA-256 is 64 lowercase hexadecimal characters.
  These are supplied expectations, not independently authenticated provenance.
- Validate every entry before opening any artifact. Only listed files are read;
  no recursive discovery, content extraction, output writing or protocol mutation.
  Ordinary filesystem access-time metadata may change when a file is read.
- A dedicated trusted, quiescent directory is required. All root/parent components
  use descriptor-relative no-follow access. Symlinks, hardlinked files and
  nonregular files are rejected. Size is checked before hashing, reads are bounded,
  and metadata changes during the read cause rejection. This is not a security
  boundary against a privileged actor concurrently altering the filesystem.

## Platform and permission boundaries

The initial implementation requires POSIX directory-descriptor support and
O_NOFOLLOW/O_DIRECTORY. On Windows or another unsupported environment it fails
closed with `no artifacts inspected`. It does not fall back to unsafe path reads.
Use an authorized POSIX workspace with synthetic artifacts for this example.
The tool neither requests broader filesystem permissions nor bypasses OS access
restrictions. Root/path access failures produce a generic failure, not a retry
outside the selected directory. Input protocol/manifest paths are explicitly
supplied regular-file CLI inputs (terminal symlinks/reparse points are rejected); do not pass credentials or private material for publication.

## Results are not acceptance

BYTES_MATCH means only that the bytes read match the supplied size and digest.
Other statuses distinguish size/hash mismatch, missing files, rejected file types,
unsafe/unreadable paths and detected changes during reading. No file content or
absolute root path appears in the report. The supplied relative path, locator,
expected/observed sizes and hashes remain visible metadata; keep reports local
unless sharing them is explicitly authorized.

`all_requested_bytes_match` is true only for a nonempty manifest where every
requested artifact matches. An empty manifest is not a successful inspection.
`uninspected_work_ids` is an inventory, not a task-requirement or adequacy judgment.
The CLI exits 0 only for a nonempty all-match result; mismatches/empty manifests
print their report and exit 1. Invalid inputs/platform/root errors exit 1 without
an artifact report. Existing validation rejects inconsistent COMPLETE/dependency
assertions before artifact access. No check completes a WP, changes acceptance,
approves a receipt, clears a prerequisite or establishes scientific readiness.

This report is a point-in-time standalone view, with protocol, manifest and
implementation hashes. It is not automatically embedded in PRISMA exports or the
seven-file research bundle. Files can change after checking; a matching digest
never proves authenticity, scientific correctness or adequate acceptance criteria.

Byte-check rows also show `completion_source_status` from the existing work review.
A byte match does not make stale/unbound [completion metadata](COMPLETION_BINDING.md)
current and never changes supplied status or acceptance.
