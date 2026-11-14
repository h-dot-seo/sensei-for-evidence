# Read-only decision-batch target preview

This increment previews an edited [decision sheet](SCREENING_DECISION_SHEETS.md)
and drafts an **unapproved** import-review document. It does not apply decisions,
export a candidate protocol or create an application file. Batch `assemble` and
`verify` are not implemented. Use the existing [single-record workflow](SCREENING_DECISIONS.md)
when an actual reviewed application is needed. Do not mistake this preview for one.

Human decision fields must already be supplied. No vote, consensus, recommendation,
reviewer-position conversion or adjudication is performed. Each completed row is
simulated in sheet order using the existing single-record `prepare` and `assemble`
operations in memory, including their entire before/after evidence/report guards.
A failure at any step rejects the whole preview without writing an output. The
original protocol remains unchanged, even if a later simulated row fails.

## Synthetic walkthrough

Run from the repository root. Replace `OUTPUT` with an existing empty directory
outside the checkout. The fixture contains explicitly fictional supplied choices
and blank rows, not generated decisions. Inspect the target, then **stop**: the
blank review is not approval and this release cannot apply a batch.

```sh
python screening_decision_batch.py target examples/screening-reviews.json examples/screening-decision-batch/filled.csv --output OUTPUT/target.json
```

Only `target.json` is written. Omit `--output` to inspect JSON on stdout. It contains
`READ_ONLY_TARGET_PREVIEW`, `approval_granted=false`, `application_exported=false`,
and blank human receipt ID/reviewer/date/rationale fields. The fixed review action
`apply_screening_decisions` describes the future operation, not consent to it.
No candidate protocol is included. Existing output entries, including final symlinks,
are refused. Missing parents fail. Writes are exclusive but not atomic; I/O failures
can leave partial new output. No ancestor-path/race security guarantee is made.

## Exact source and human-cell rules

The CSV must have the decision export's exact ordered headers. Every read-only cell
is compared to a fresh export of the unchanged original protocol in sheet order:
source bases, literal/escaped IDs, protocol hash, retained displays, prior canonical
row and supplied review context/hash. An original protocol change, including unrelated
screening or new reviewer assertions, invalidates the old sheet. Never refill hashes
or rebase automatically. Keep the original protocol with the sheet and re-examine new
context before making fresh assertions. A subset/reordering of exported rows is
allowed and defines the simulation order, but duplicates are rejected.

Fully empty human rows are skipped and explicitly listed with spans. A partly filled
row fails. Completed rows require unique new receipt IDs, literal `include`/`exclude`,
a nonblank reason/adjudicator/rationale/locator and a real `YYYY-MM-DD` date. Dates do
not pick a winner. Human fields starting with apostrophe, `=`, `+`, `-`, `@` or whitespace
are rejected as formula/escape ambiguity; nothing is unescaped or guessed. Use the
existing JSON workflow for literal assertions outside this CSV subset. Positions
sheets are a different contract and are not accepted here.

## Hypothetical targets, not applied receipts

The preview binds raw sheet SHA-256/bytes, parsed human cells and original byte spans,
the whole original protocol, implementation hashes, projected flows and a projected
protocol hash. Each `hypothetical_steps` entry states `applied=false`, retains the exact
supplied choice, projected row, ordinary target snapshot and hypothetical receipt hash.
The second and later targets are computed from prior simulated steps, not from a
pre-approved per-record target. They are not evidence of execution, human approval or
stored receipt history. The future reviewed batch target must bind this exact sheet
and chain. No native receipt schema or ENGINE_FILES bytes change here.

Limits: 1–100 sheet rows and at least one completed decision, 10 MB CSV, 50 MB
protocol and target. Hypothetical step payload bytes are capped cumulatively before
retaining another step, and the complete target is checked again at the end. A successful preview can include at most 100 completed decisions,
and preflight enforces the engine's existing 1,000-receipt lifetime limit. The source
export's whole-catalog and parser field limits still apply. Existing receipt validation
is repeated during simulation and can be expensive near the lifetime cap; this is a
bounded batch convenience, not high-volume processing. A preview does not reserve
capacity or make later inputs current. Hashes are not authentication; consistently
reauthored unsigned inputs can replay. Keep real sheets, source text and previews out
of the public repository. Locators are never opened; no network/model calls, source
reading, identity verification, adjudication or conclusion readiness are established.
