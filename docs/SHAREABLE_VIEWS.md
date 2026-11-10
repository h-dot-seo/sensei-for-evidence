# Shareable supplied-data status

`views_export.py status` renders only the existing `research_status.status()` result
into a new detached Markdown file. It adds a count table and all existing queue
items, scopes, optional retrospective records, readiness bookkeeping and fingerprints.
The bundle already has a count-only `summary.md`; this separate file also preserves
status details without modifying a protocol or the bundle's seven-file contract.
It is not a PRISMA diagram, final review or scientific/readiness decision.

## Synthetic rehearsal

Run from the repository root. Replace `OUTPUT` with an existing directory outside
this public checkout. Both output filenames must be new. The example is entirely
fictional. No model call, network request or clock read occurs.

```sh
python views_export.py status examples/prisma-audit.json --output OUTPUT/status.md
python views_export.py status examples/prisma-audit.json --output OUTPUT/status-text-receipt.md --text
```

Both files are byte-identical. The first command prints a JSON receipt; `--text`
changes only that receipt to quoted text. Neither duplicates the Markdown payload
on stdout. The receipt contains UTF-8 output byte count/SHA-256, canonical protocol
SHA-256, implementation hashes, queue/readiness counts and the negative claims.
`status: RENDERED` describes a serialization, not review completion or a signature.
A CLI success receipt is printed only after the output write finishes. Keep it with
the Markdown if you need the renderer fingerprint: the file preserves the original
status engine hashes, while the receipt additionally fingerprints `views_export.py`
and `prisma_audit.py` (the latter for the shareable-view implementation inventory;
its audit is not called for this command). Hashes do not authenticate sources.

## Reading the file

- Tables contain only program-owned labels and integer counts or `not supplied`.
  Queues overlap; do not sum rows into a total or treat ordering as a priority rank.
- Every status field is retained under a fixed heading. Optional inventory/review
  and historical-decision sections remain retrospective context, not new tasks.
- Every queue item is displayed as one quoted JSON value on its own fenced line,
  including nested records and any existing input pointers. No join or input pointer
  is invented. No handoff-only fields are imported.
- `null` preserves not-supplied/unknown values; `[]` preserves an available empty
  list and count zero. An omitted optional section remains omitted.
- Supplied strings never enter table cells, headings, links or inline code spans.
  `quoted_display` escapes control, format and Unicode line/paragraph separators.
  Each block's backtick fence is longer than every backtick run in its contents.
  This is inert text under standard fenced-code Markdown interpretation, not a
  guarantee for every renderer. No HTML page, scripts, links or renderer is added.
- The original status boundary and the view boundary remain inside the file.
  Census stays `NOT_ESTABLISHED`; mechanical conclusion readiness stays `NOT_READY`.

## Output and limits

The CLI reads at most 16 MiB plus one detection byte from the supplied protocol,
rejects duplicate JSON keys, nonfinite numbers, invalid UTF-8 and lone surrogates,
and bounds both complete Markdown and stdout receipt to 16 MiB before writing.
Object-key order does not change output bytes; list order remains significant.
The renderer fails closed if a future status field/queue cannot be represented.

The parent directory must already exist. The writer checks `lstat()` before
exclusive binary creation, refusing an existing file, directory or dangling link,
including on Windows. Existing bytes are never overwritten. Validation or size
failures create nothing. An operating-system write failure may leave an incomplete
new file; no success receipt is printed in that case. This is exclusive creation,
not atomic staged publication. Stable paths are required: concurrent path replacement
and ancestor aliases are not a supported security boundary.

The file and receipt are unredacted. Review them before sharing; keep real research
questions, IDs, pointers and outputs outside the public repository. This command
does not upload or authorize sharing anything. Mermaid, DOT, records CSV and handoff
Markdown are deferred; no model/network integration or new scientific judgement is
included in this status-only increment.
