# Explicit bibliographic reconciliation and screening intake

`bibliographic_review.py` connects a [verified local intake artifact](BIBLIOGRAPHIC_INTAKE.md)
to the existing research workflow. Every CSV row needs an explicit supplied
identity/triage choice, followed by a separate export-level review assertion bound
to the exact current protocol, artifact and choices. The tool appends one
**incomplete** search and retains the raw collection rows separately.

This is not authenticated human review, publication identity verification, source
authentication, eligibility screening or a complete-search claim. No model or
provider is contacted. Review metadata describes an operator's supplied assertion.

## Synthetic end-to-end example

The base, CSV and resolution example below are entirely fictional. Choose new
paths outside this public checkout. The parent directory must already exist.

```sh
python bibliographic_intake.py preview examples/bibliographic-base.json examples/bibliographic-export.csv --search-id local-primary --searched-at 2026-11-04T00:00:00Z --output /outside/new-intake.json --text
python bibliographic_review.py template /outside/new-intake.json --review-output /outside/new-blank-choices.json --text
python bibliographic_review.py target examples/bibliographic-base.json /outside/new-intake.json examples/bibliographic-resolutions.json --review-output /outside/new-review.json --text
```

Use suitable local paths for your operating system. The blank template deliberately
fills no identity decisions. The example resolutions show three literal `r1` rows
explicitly linked to one canonical record, a guideline candidate retained as a
second record, and a development row withheld. The conflicting locators survive.

The `target` command validates all row choices and writes a review document with
the exact target hash. Reviewer, date, rationale and decision remain null. Inspect
the source bytes, row choices and current protocol. Only then supply those four
fields. The sole supported decision is `import_for_screening`; `reviewed_at` must
be a real calendar date in YYYY-MM-DD form. This decision does not approve search
completeness, scientific quality or any clinical action. Do not treat the fictional
example as evidence that a real record has been reviewed.

```sh
python bibliographic_review.py assemble examples/bibliographic-base.json /outside/new-intake.json /outside/new-review.json --protocol-output /outside/new-screening-protocol.json --text
python research_status.py /outside/new-screening-protocol.json
python prisma_audit.py /outside/new-screening-protocol.json --text
python research_bundle.py create /outside/new-screening-protocol.json /outside/new-screening-bundle.zip
python research_bundle.py verify /outside/new-screening-bundle.zip
```

Assembly refuses null or stale review fields. Successful assembly introduces two
canonical records awaiting ordinary screening. It retains five collection rows:
four promoted row occurrences and one withheld row. It creates no screening,
report, extraction, guideline recommendation or development decision. Existing
research fields and decisions are copied without change; inputs are not modified.

All file-output flags use exclusive creation and never overwrite an existing file.
Validation happens before opening output. An operating-system write error can
leave a partial new file, which must not be treated as a valid output. Omit output
flags for previews; default stdout is structured JSON and `--text` safely quotes
supplied text. Shell redirection has its own overwrite behavior.

## Complete row choices, no inferred identity

The review document has exactly `schema_version: 1`, `resolutions`, and `review`.
Each resolution has exactly `candidate_id`, `disposition`, `record_id`, and a
nonblank `rationale`:

- `new_record`: explicitly declares a new nonblank canonical ID absent from the
  current protocol and every other new-record declaration in this batch.
- `same_record`: explicitly links to a record already in the current protocol,
  or a canonical ID declared by a new-record row in this batch. The new-record
  row may appear later. Review-row ordering is normalized to CSV candidate order.
- `do_not_promote`: retains the collection row without adding a record membership.
  Its `record_id` must be null. This is not a title/abstract exclusion and produces
  no screening reason or exclusion count.

Every candidate must occur exactly once. Missing, extra, duplicate and unknown
choices are rejected. Identical literal IDs, titles or locators never choose a
disposition automatically. One canonical ID may intentionally represent rows with
different literal locators, but this remains an explicit unverified assertion and
all original locators remain inspectable. A header-only or all-withheld export
still requires explicit export-level review and remains an incomplete search.

The review target binds the original intake's canonical artifact hash and intake
target, the full current protocol hash, and canonical ordered resolutions. Changing
any of those inputs requires a new reviewed target. `target` requires `review:null`
and never silently renews a previously supplied review.

## Repeated imports without recursive snapshots

The first import requires the intake snapshot to equal the current protocol
exactly. The resulting ledger saves that **common base once**. It must contain
neither a local import ledger nor a mock-adapter ledger.

For another planned search, prepare the next intake against the original common
base file, then run `target` and `assemble` against the current enriched protocol.
Do not clear current research or use an intermediate imported protocol as a new
base. The base artifact's overlap hints describe the historical base only;
reconciliation collision/link checks use the exact current protocol, including
records introduced by earlier imports. The two versions are displayed separately.

Each appended receipt stores its intake without `protocol_snapshot`, plus the
pre-import current protocol body without the ledger and its exact preceding-entry
count. Validation reconstructs the original intake with the common base, and the
historical current protocol with exactly the preceding ledger prefix. Full source
artifacts and review bindings can therefore be regenerated without recursively
storing earlier ledgers inside each snapshot. Historical bodies may still grow
with research content; the aggregate protocol is bounded at 50,000,000 canonical
JSON bytes and 100 imports. Saved pretty JSON must also fit the 50,000,000-byte
output limit. These are resource limits, not a scientific search limit.

Question, criteria, search plan and unknown/opaque base fields remain unchanged.
Version, screening, reports, evidence, work packages, contexts, appraisals,
planning, synthesis and experimental metadata may evolve under their existing
validators. Current searches must remain exactly the base searches followed by
ordered normalized imports. A planned search already executed cannot be imported
again, and mock-adapter provenance cannot be mixed into this ledger. Revising the
search plan, replacing searches or migrating between provenance workflows is not
supported here; the tool refuses rather than deleting or rebasing research.

## Accounting and integrity boundaries

Every imported search has `complete:false`, unknown total and continuation, and
no fabricated provider pages. Review cannot change these to complete. Canonical
IDs appear once per search in the existing search-membership occurrence counts.
Raw CSV rows are a separate collection unit, including repeated and withheld rows.

Research JSON and PRISMA audit JSON expose `bibliographic_collection`, with raw
rows, dispositions, original values, exact byte/line spans and stored JSON pointers.
PRISMA canonical-record entries link back to the promoted collection rows. Existing
PRISMA membership partitions retain their original meaning and do not count raw
duplicate CSV rows as additional canonical search memberships.

The bundle retains protocol provenance and derived collection output, and its
implementation fingerprint includes all intake, parser, reconciliation and
integrity dependencies. Editing retained bytes, derived spans, row choices,
historical context, prefix order, attached search or review binding breaks
validation unless all relevant assertions are consistently replaced. Hashes are
not signatures: a party able to fabricate inputs and recompute reviews can create
another internally consistent record. Source authenticity, publication identity,
complete coverage, clinical applicability and scientific conclusions remain
unverified after a successful import. Keep real exports, protocols and generated
artifacts private and outside the public repository.

After collection, [supplied screening reviewer positions](SCREENING_REVIEWS.md)
can retain separate title/abstract assessments against the exact criteria and
mapped source-row context. Adding those assertions is allowed enrichment, not a
new import or automatic screening decision. Original CSV history remains intact;
conflicting or stale reviewer positions do not alter canonical PRISMA counts.

[Authored document schemas and explain](SCHEMAS.md) cover the starting-base and
collection-choice/review path. Shape checks do not replace exact workflow validation.
