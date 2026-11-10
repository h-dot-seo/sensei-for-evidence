# Supplied-data accounting flow

`views_export.py flow` saves a detached Mermaid text file built from the existing
`prisma_audit.export_audit()` nodes and partition checks. It is not an official
PRISMA diagram, interchange format, compliance certificate or final review.
It performs no model call, network request, source retrieval or scientific judgement.
No renderer, HTML page, CDN dependency or rendering service is supplied.

## Fictional rehearsal

Run from the repository root; replace `OUTPUT` with an existing directory outside
this public checkout. Both output names must be new. The fixture is synthetic.

```sh
python views_export.py flow examples/prisma-audit.json --format mermaid --output OUTPUT/flow.mmd
python views_export.py flow examples/prisma-audit.json --output OUTPUT/flow-text.mmd --text
```

The files are byte-identical. `--text` changes only the stdout receipt. JSON and
quoted receipts include document byte length/raw SHA-256, canonical protocol hash,
implementation hashes and node/partition counts, not the diagram itself.
`node_count` counts distinct audit nodes, not the repeated alias boxes. Preserve
the receipt with the file. Hashes are fingerprints, not source authentication.

## Reading the accounting

Each partition is its own labelled group with local node aliases. A quantity may
appear in multiple groups: repeated labels refer to the same audit node, not extra
records. Never add those copies or independent partitions into a grand total.
All labels are fixed program vocabulary plus nonnegative integer counts. Supplied
questions, IDs, reasons, sources, locators and member lists are never interpolated.
An example node is plain text, not a renderer invocation:

```text
p0n0["identified_occurrences | record_occurrence | 13"]
```

- Solid arrows reproduce the audit's same-unit partition checks, including optional
  report-study membership partitions. They do not assert scientific readiness.
- Two separate dashed unit bridges show retained occurrences to unique records and
  mapped included records to sought reports. Their labels state that counts are
  not conserved across units. A missing stage remains `not supplied`, not an
  assertion that a mapping exists, and is never converted to zero.
- Study/result nodes outside partitions stay detached. No relationship is inferred.
- The plan-status node shows only the fixed plan status and counts of missing and
  incomplete planned searches. With no supplied plan both counts are `not supplied`.
- A visible boundary node retains the audit boundary, `Census: NOT_ESTABLISHED`
  and `Conclusion: NOT_READY`. Protocol and implementation hashes are comments.
- No links, click handlers, HTML labels, directives or supplied Mermaid syntax are
  generated. Tests check a limited fixed syntax grammar, not compatibility with
  every Mermaid version or rendering application. Rendering is an optional separate
  user action; inspect the file and renderer before use or sharing.

## Limits and privacy

Input, complete document and stdout receipt are independently limited to 16 MiB
before the file is opened. Strict JSON parsing rejects duplicate keys, invalid UTF-8,
nonfinite values and lone surrogates. Object-key order does not affect the output;
list order stays significant. Unsupported node vocabulary fails closed.

The same exclusive binary writer as [status Markdown](SHAREABLE_VIEWS.md) refuses
existing files, directories and dangling links via `lstat` then `xb`. It never
modifies the protocol. Validation/size errors create no output. An OS write error
may leave an incomplete new file; no success receipt is printed. Stable output paths
are required; concurrent replacement and ancestor aliases are not a security boundary.

Counts, protocol hashes and implementation fingerprints can disclose private work
or enable correlation even without supplied labels. Keep real files outside this
public repository. Saving does not upload or authorize sharing. Existing status
Markdown, audit engine and bundle payload contracts are unchanged. DOT, records CSV
and handoff Markdown remain separate follow-up work.
