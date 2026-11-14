# Start with your own supplied protocol

This offline two-step helper writes a blank starting draft, then checks the values
**you supply**. It does not invent a question, criteria, sources, queries, windows,
IDs, search results or approval. No network/model calls. Keep real research text and
outputs outside this public repository. A mechanically valid base is not an adequate
plan, protocol lock, ethics approval or a completed study.

## First: an unfilled draft

Choose new filenames in an existing working directory. The stdout wrapper includes
boundaries and implementation hashes; `--draft-output` writes only the draft object.

```sh
python protocol_scaffold.py template --draft-output /outside/starting-draft.json
```

Fill `starting-draft.json`, not the wrapper. Supply:

- Nonblank literal `question` and `version` strings.
- Nonempty `inclusion_criteria` and `exclusion_criteria` lists of nonblank strings.
- A nonempty `search_plan` list. Every row has exactly `search_id`, `source`, `query`
  and `window`, all nonblank strings. Search IDs must be distinct exact strings.
- Leave `searches`, `screening`, `evidence` and `gaps` as empty arrays in this new base.

Do not clear an existing research protocol to satisfy this check. It deliberately
rejects existing research and unknown fields, including `adapter_receipts`,
`bibliographic_imports` and `$schema`. It cannot tell whether an operator manually
removed research before supplying a file. Keep prior work separately and unchanged.

The template begins with null question/version, empty criteria and one null-filled
plan row. None is consent, a completed assertion or a meaningful search. The tests
fill a fictional question/criteria and one fictional source/query/window between
these two blocks; those choices are not a recommended plan for your research.

## Second: check and save a new base

```sh
python protocol_scaffold.py check /outside/starting-draft.json --protocol-output /outside/starting-base.json
python receipt_intake.py template /outside/starting-base.json
```

The second command demonstrates that the checked base can produce a separate blank
mock-receipt scaffold on stdout. It executes no search and leaves request IDs, dates, counts,
pages and extraction facts unfilled. Continue only with supplied facts and the
[receipt-intake guide](RECEIPT_INTAKE.md), or choose the appropriate documented
[bibliographic import](BIBLIOGRAPHIC_INTAKE.md) workflow. No future import is authorized
or performed by this starting check.

Without `--protocol-output`, check writes only a JSON report. Invalid drafts return
exit2 and `missing_hints` JSON pointers (or a Python validator error), never a new base.
Malformed/oversized JSON returns an escaped error with exit2. Valid drafts pass both
`receipt_intake.fresh_base` and `evidence_workflow.run` before export. Stored protocol
fields are exactly the supplied fields, with no boundary/status keys injected. The
reported digest uses sorted compact JSON, not the pretty-printed output bytes.

## Boundaries and compatibility

- This recommended starting shape is intentionally stricter than the general Python
  validators. It is not a complete protocol schema or a JSON Schema checker.
- The [descriptive base schema and explain](SCHEMAS.md) can assist authoring, but
  this command remains the authoritative starting-shape check. Automatic PubMed-plan
  derivation is not provided. PubMed paths require their documented exact four-key plan with source
  `pubmed` and a query/window consistent with the supplied discovery specification;
  see [PubMed discovery](PUBMED_DISCOVERY.md). The scaffold does not check that
  provider-specific relationship or make a live request.
- Preserve the original ledger-free common base for later imports; do not overwrite
  it with an enriched candidate or erase prior research to recreate it.
- Inputs and serialized output are bounded at10MB. Objects are handled in memory.
  UTF-8 strict JSON rules apply; no duplicate keys, nonfinite numbers or silent coercion.
- All writes use exclusive new files. Existing paths/final symlinks are refused.
  OS write failures may leave a partial new file; hostile ancestor/path races are not
  sandboxed or transactional. Formatting may change but supplied JSON values do not.
- Checks establish neither plan/query adequacy nor source authenticity, completeness,
  scientific correctness or rights to redistribute any supplied material.

[Command reference](COMMANDS.md) · [First-run rehearsal](FIRST_RUN.md)

[Authored document schemas and explain](SCHEMAS.md) cover the starting-base and
collection-choice/review path. Shape checks do not replace exact workflow validation.
