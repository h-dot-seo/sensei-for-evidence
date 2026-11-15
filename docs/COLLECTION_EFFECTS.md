# Inspect the effects of a supplied collection journey

This extends the partial [command contract](AGENT_CONTRACT.md) across one existing
workflow: supplied CSV, single RIS/NBIB or an ordered NBIB batch, a separately
supplied identity review, and optional preservation/replay of selected native
originals. It adds **declarations and tests**, not another intake/archive engine,
permission to execute, source access, review authentication or scientific judgment.
All root implementation bytes and every existing example remain unchanged.

## The 17 inspected command profiles

| Script | Commands | Logical file inputs | Conditional new files |
|---|---|---|---|
| bibliographic_intake.py | preview, verify | protocol/export or artifact | preview `--output`; verify none |
| nbib_intake.py | preview, verify | protocol/export or artifact | preview `--output`; verify `--intake-output` OR `--csv-output` |
| ris_intake.py | preview, verify | protocol/export or artifact | preview `--output`; verify `--intake-output` OR `--csv-output` |
| nbib_batch_intake.py | preview, verify | protocol and repeated `--export SOURCE_ID=PATH`, or artifact | preview `--output`; verify `--intake-output` OR `--csv-output` |
| bibliographic_review.py | template, target, assemble | artifact; target/assemble also protocol and review_document | template/target `--review-output`; assemble `--protocol-output` |
| collection_bundle.py | create, verify | protocol and repeated `--nbib INDEX=PATH`, or bundle | create positional output; verify none |
| native_collection_bundle.py | create, verify | protocol and repeated `--ris`, `--nbib`, `--nbib-batch` INDEX=PATH, or bundle | create positional output; verify none |
| batch_collection_bundle.py | create, verify | protocol and repeated `--batch INDEX=PATH`, or bundle | create positional output; verify none |

The existing five NBIB/review profiles are unchanged and rechecked. Twelve
previously unknown profiles are added. Coverage is now 44 of 200 command entries;
156 remain `NOT_REVIEWED` with null effects. Neither a filename nor a `verify`
subcommand is evidence of read-only behavior. In particular, intake verification
can create a CSV or an intake artifact; the three archive verifiers emit only
stdout, without a logical file-output option. No archive is extracted.

`inputs` describes file-bearing arguments, not every scalar parameter. Source IDs,
import indices, explicit format flags, search IDs and supplied timestamps are still
required exactly as documented by each implementation. Batch source order is
supplied order. Wrapper indices refer to existing imports, not search-plan rows.
A locator string is inert; these 17 commands do not fetch it. Invalid identifiers,
unknown formats, missing references, stale bindings or malformed inputs remain
subject to the existing validators, not an acceptance promise in this contract.

## Outcomes and file contents

For all 17 profiles, accepted inputs produce JSON stdout, or text with `--text`,
and exit 0. An explicitly handled input/replay/write failure exits 1 with empty
stdout and a diagnostic on stderr. There is **no negative stdout-report profile**
in this selection: a rejected archive or altered artifact is an error, not JSON
with a false flag followed by exit 1. Usage errors, including mutually exclusive
intake output flags, exit 2. Other commands such as local source observers retain
their different negative-report contracts.

Output creation is exclusive, never an overwrite. Omission of an optional output
means no corresponding logical file is created. Output content is not necessarily
the stdout report: target writes its review document, assemble its protocol
candidate, native verify its nested intake or CSV bytes, and create its ZIP.
`--text` selects stdout rendering only, not a different output-file format.
Existing destinations are refused. An OS write failure can leave a partial **new**
file; this is not atomic staging, cleanup, or a complete race/path defense. The
contract describes handled failures, not every unexpected exception or a failed
stdout write. Diagnostics can contain supplied paths/data: quoting is not redaction.
Interpreter caches and OS/runtime activity are outside logical-output declarations.

## Follow the existing workflows, without invented review

Use [CSV intake](BIBLIOGRAPHIC_INTAKE.md) and
[separate identity review](BIBLIOGRAPHIC_REVIEW.md),
[single NBIB](PUBMED_NBIB_INTAKE.md), [RIS](RIS_INTAKE.md), or
[ordered NBIB batches](PUBMED_NBIB_BATCH.md) for the actual accepted input grammar.
Then choose the existing [NBIB archive](COLLECTION_BUNDLES.md),
[batch archive](BATCH_COLLECTION_BUNDLES.md), or
[explicit mixed native archive](NATIVE_COLLECTION_BUNDLES.md) as appropriate.
Do not select paths or format flags by guessing filenames.

A template is not a completed review. A target does not prove that a person has
reviewed anything. Supply the separately authored review required by the existing
workflow; do not invent another person's receipt fields or copy a stale hash to
clear a queue. These tools and this contract do not authenticate the reviewer.
Successful import, full selected-native coverage and successful archive replay do
not establish complete literature searching, source truth, scientific sufficiency,
or conclusion readiness. Existing gates and decisions remain unchanged.

## What was checked

`tests/test_collection_contract_journey.py` executes all 17 command identities in
real child processes, both JSON and text success modes. It checks exact logical
file creation, unchanged input bytes, JSON/file content relationships, raw CSV
bytes, identical output-file bytes under text rendering, and repeat-write refusal.
Four fictional journeys cover CSV, RIS, single NBIB and a two-file NBIB batch;
each exercises template, supplied identity choices, target, refusal of an unfinished
review, separately supplied fictional review and assembly. Native journeys then
create/replay all three archive types. Altered artifact targets, trailing ZIP bytes,
malformed wrapper bindings, missing inputs and contradictory output flags exercise
actual error channels. Synthetic test authorship is not real human approval.

The tests also pin all prior root Python and example bytes, check that exactly the
12 intended registry entries change, retain the old five profiles, and match the
source-bound registry. Existing command-reference tests compare parser usage.
The old tests continue to cover parser limits, invalid binding indices, mixed-format
selection, semantic archive tampering and resource boundaries. This addition is
not a claim of exhaustive effects for all 200 entries, stronger archive safety,
external reference-manager compatibility, authenticity, or OS confinement.
