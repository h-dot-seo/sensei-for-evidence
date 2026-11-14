# Author starting, collection and decision documents

These descriptive JSON Schema documents support the authoring path from a new base
through bibliographic choices and import review to supplied screening/report decisions.
They help inspect structure **before** invoking the authoritative workflow. They never
supply choices, copy a new target hash, authenticate a reviewer or authorize an import.

| Document | Schema | Next authoritative check |
|---|---|---|
| Recommended ledger-free starting base | `schemas/base-protocol.schema.json` | `protocol_scaffold.py check`, then the chosen intake |
| Completed row choices, review still null | `schemas/bibliographic-choices.schema.json` | `bibliographic_review.py target` with original protocol and intake |
| Completed title/abstract screening decision | `schemas/screening-decision.schema.json` | `screening_decision.py assemble` with original protocol and exact target |
| Completed full-text report decision | `schemas/report-decision.schema.json` | `report_decision.py assemble` with original protocol and exact target |
| Choices plus separately supplied review | `schemas/bibliographic-reviewed.schema.json` | `bibliographic_review.py assemble` with the exact same context |

Use your editor's filename mapping or explicitly open the schema. **Do not add a
`$schema` field to the input document**: exact-key validators may reject it and it
changes protocol identity. `$schema` in the schema file is only a dialect declaration;
this tool never downloads it. Repository rights remain governed by [RIGHTS.md](../RIGHTS.md).

## Rehearse with existing fictional inputs

```sh
python schema_check.py explain schemas/screening-decision.schema.json
python schema_check.py check schemas/screening-decision.schema.json examples/screening-decision-document.json
python schema_check.py explain schemas/report-decision.schema.json
python schema_check.py check schemas/report-decision.schema.json examples/report-decision-document.json
python schema_check.py explain schemas/base-protocol.schema.json
python schema_check.py check schemas/base-protocol.schema.json examples/bibliographic-base.json
python schema_check.py check schemas/bibliographic-choices.schema.json examples/batch-to-evidence/collection-choices.json
python schema_check.py explain schemas/bibliographic-reviewed.schema.json
python schema_check.py check schemas/bibliographic-reviewed.schema.json examples/batch-to-evidence/collection-review.json
```

`explain` emits the selected schema's title, descriptions and complete field rules,
not a separately maintained third rules table. `check` emits pointer/rule diagnostics,
exact input/schema SHA-256 and checker hash. It does not echo document values. It
returns0 for a shape match,1 for a structural mismatch,2 for unsupported schema,
malformed strict JSON, I/O or processing limits. No files are written by the checker.
Input digests and diagnostic property names may themselves be sensitive; this is not
an anonymizer. Keep real files outside this public repository and review before sharing.

Continue through [the existing NBIB-to-evidence rehearsal](BATCH_TO_EVIDENCE.md).
Its tests check the three collection-path documents while also running the actual
intake/target/assembly path. Blank choices and incomplete target reviews deliberately
fail the completed-document schemas. A passing schema check must never be used to
skip exact target preparation, separate supplied review, input binding or replay.

## Decisions remain supplied and bound to their actual targets

The screening and report schemas describe completed decision documents, not blank
target templates or approval receipts. Report inclusion requires exactly one of a
scalar study_id or nonempty unique study_ids; exclusion requires null. Study labels
are supplied memberships, not proof of distinct eligible studies. Both decisions
require an explicit include/exclude, source locator, adjudicator, date, rationale,
reason, receipt ID and target digest. Structure never supplies these values.

The existing [screening](SCREENING_DECISIONS.md) and [report](REPORT_DECISIONS.md)
rehearsals check their supplied fictional document before assembly. Their exact-target
validators still reject stale hashes and mismatching IDs even after a shape match.
The report schema uses uniqueItems; the checker's1,000-item comparison bound is a
processing limit, not a new limit on authoritative report study declarations.

## Deliberately not a second authority

The Python workflow validators remain authoritative. The base schema describes the
stricter **recommended starting shape**, not every protocol accepted by `run()`.
Full protocols, other intake candidates, output records and schemas/explain for the
rest of the system are not included. The explicit test inventory classifies every
checked-in example, including106 outside these five document shapes; no conformance
claim is made for excluded files. Existing snapshots/schema2 contracts do not change.

Engine-only checks include:
- Nonblank versus merely nonempty strings, actual calendar dates and unique search IDs.
- Exact candidate coverage, unique candidate identities, existing/new record IDs and
  common-base/source context. `same_record` is a supplied assertion, not identity proof.
- Equality to the actual reviewed target hash.64 hex characters alone prove nothing.
- Original artifact/implementation bytes and deterministic assembly/replay.

JSON Schema permits numeric1.0 as an integer and considers1 and1.0 equal. Python's
exact integer schema-version checks may reject1.0. Whitespace-only text and
2026-02-30 may pass a descriptive shape but fail authoritative checks. Tests preserve
these differences instead of implying general equivalence. The audited patterns use
standard search semantics: `$` can also match before a final newline. Thus64hex plus
final LF may match the shape but still fails equality to the exact workflow target. Structural required-key,
unknown-key, disposition and null-record rules have mutation checks against the
existing validators; that does not establish equivalence for all possible inputs.

## Supported bounded subset

This is **not a general draft2020-12 implementation**. Supported keywords are `$schema`,
`title`, `description`, `type`, `properties`, `required`, boolean `additionalProperties`,
`items`, `minItems`, `maxItems`, `minLength`, `enum`, `const`, `oneOf` and `uniqueItems`.
`pattern` supports only the two audited ASCII date/hash patterns used here. Other
keywords, remote/local `$ref`, formats, conditionals and arbitrary regexes fail closed,
including in unused branches. No external resource or schema code executes.

Booleans are not numbers. Numeric equality treats1 and1.0 alike, recursively for
objects/arrays and uniqueItems. oneOf must match exactly one branch. JSON parsing is
strict UTF-8 without duplicate keys/nonfinite numbers. Limits: schema10MB, document
and report50MB, depth64 across both complete input trees,100,000 combined tree/schema/check/equality
visits,5,000,000 string-comparison characters,100 diagnostics,1,000 items for
quadratic uniqueItems comparisons. Processing is in memory. Hitting a limit returns2,
not a claim that the document is invalid. General schemas should use a separately
chosen full validator, still followed by the authoritative research workflow.

[Starting protocol](PROTOCOL_SCAFFOLD.md) · [Bibliographic reconciliation](BIBLIOGRAPHIC_REVIEW.md)

Retained artifact navigation: [record kinds, object versions and verification guides](RECORD_SCHEMAS.md). This index is not validation or migration.
