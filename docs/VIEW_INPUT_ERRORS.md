# Diagnose status, handoff and comparison input failures

This contract applies only to the command-line entry points of `research_status.py`,
`review_handoff.py` and `compare_runs.py`. It is not a repository-wide CLI contract.
The status → handoff → compare workflow uses the same supplied protocols; a malformed
file should not expose its private path or contents just to explain which input failed.

Each supplied protocol or optional amendment is read once with a limit of 50,000,000
bytes (inclusive). UTF-8 and the existing strict JSON rules apply, including duplicate
keys, nonfinite numbers and surrogate rejection. The top level must be an object.
JSON value depth is at most128 edges below that root, including scalar leaves;
the Python parser can refuse nesting earlier. These are input bounds, not an execution
wall-time, output-size or total-memory guarantee. Use stable regular files you control;
this is not a no-follow reader, concurrent-filesystem sandbox or timeout for special files.

## Error output

Input errors exit1 with empty stdout and one fixed-text stderr line:

`comparison error: input-not-json: after protocol: "Expected strict UTF-8 JSON."`

Categories and action:

- `input-unreadable`: confirm that the named argument points to a readable file.
- `input-too-large`: the file exceeds the per-input byte limit; use the supported scope,
  not truncation or removal of provenance to force a file through.
- `input-not-json`: check UTF-8 and strict JSON syntax. Filenames, duplicate-key values,
  parser fragments and line contents are deliberately not repeated.
- `input-too-complex`: parser capacity or the explicit depth bound was exceeded.
- `input-invalid`: a JSON object or validated protocol/selection was required. Consult
  the corresponding workflow's required fields and relationships. The CLI does not
  reproduce raw engine exception details that might contain supplied IDs or text.

Reading/parsing labels are `protocol`, `before protocol`, `after protocol`, and
`amendment`. Semantic comparison failure is labeled `comparison inputs`; it does not
claim to diagnose which side is invalid. Handoff semantic failures use `protocol or
work selection`, including an unknown selected work ID. No source bytes, filenames,
absolute paths or selected IDs appear in these caught-input errors.

Usage mistakes remain argparse exit2 and can repeat command-line tokens. This privacy
boundary concerns successfully parsed input arguments, not usage-error redaction or
normal reports. Successful JSON/text reports still contain the supplied research data.

## Preserved result contracts

Success is exit0 and the existing JSON/text schema. An amendment binding mismatch is
still a structurally valid comparison report on stdout with exit1 and empty stderr.
Do not treat every exit1 as missing output. See [amendment notes](AMENDMENT_NOTES.md)
and [comparison](COMPLETION_COMPARISON.md). No new exit3/4, automatic correction,
review, canonical decision or schema migration is introduced.

These limits apply to CLI file inputs only. In-memory `status`, `handoff` and
`compare_protocols` functions and engine validation logic are unchanged. The three
view-module byte fingerprints change; matching output shape is not byte-identical
historical implementation. ENGINE_FILES, retained source fixtures and schema2 contracts
are unchanged. Other commands still have their own documented input/error behavior.
