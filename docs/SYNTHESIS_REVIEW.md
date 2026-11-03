# PRISMA-oriented accounting and synthesis review snapshot

`synthesis_review.py` combines the existing search/record/report accounting with
**supplied, citation-linked statements**. It does not write a scientific synthesis,
assess whether a statement is supported, or produce a final systematic review.

The concrete usability gap was protocol-wide synthesis review: work packets expose
only evidence linked to work, leaving unassigned results and statement citations
without a common review view. This snapshot includes all extracted results, even
those assigned to no work package and cited by no statement.

## Synthetic end-to-end example

```sh
python synthesis_review.py examples/synthesis-review.json --text
python synthesis_review.py examples/synthesis-review.json
python research_status.py examples/synthesis-review.json --text
python research_bundle.py create examples/synthesis-review.json ../synthetic-synthesis.zip
python research_bundle.py verify ../synthetic-synthesis.zip
```

The bundle output must not already exist. All example data and reviewer assertions
are synthetic. No actual source, full text or guideline is fetched.

The fixture deliberately separates units and unfinished stages:

- 10 distinct supplied record IDs: 9 screened, 1 pending. Of the screened records,
  1 is excluded and 8 included at title/abstract level.
- 6 reports: 4 have supplied retrieved assertions, 1 is unavailable and 1 pending.
  Of the 4 retrieved reports, 3 have full-text decisions and 1 awaits assessment.
- 2 included reports, 1 excluded report, and 2 distinct included supplied study IDs.
- 3 extraction rows from just 1 record/report/study. One included report has no
  extraction. Two record IDs map to the already-extracted report-1.
- One planned search is missing; one included record has no report mapping.
- Statement-1 has a source-matching supplied review; statement-2 is pending.
  Result e3 is uncited and assigned to no WP. Some extraction rows lack appraisal.

Counts do not imply one record per report, one report per study or one result per
study. Exact-ID repeated occurrences are not independently confirmed duplicate
publications. Study IDs and report mappings are supplied, not authenticated.

## Visible accounting and source limits

JSON and text preserve search receipts/accounting, record screening, the full report
ledger and report exclusion reasons, including retrieval-failure reasons and source
locators for reports with no extracted results. Missing report or synthesis stages
remain `NOT_SUPPLIED`/null. A supplied empty statement list differs from no stage.

Record-level extraction bookkeeping is explicitly scoped to **title/abstract-included
records without any result row**. It can include a full-text-excluded record or an
alternate record mapped to an already-extracted report. It is not a count of required
full-text extraction tasks. The separate `included_reports_without_extraction` queue
uses included report IDs. Neither establishes exhaustive extraction.

The review queues also retain missing/incomplete searches, unscreened/unmapped
records, unavailable/pending full text, pending assessments, appraisal/context gaps
and existing work/planning queues. These queues overlap and must not be added into
one count of remaining scientific work.

## Supplied statement contract

Optional top-level `synthesis_statements` is an array. Each entry requires:

- Unique nonempty `statement_id`.
- Nonempty `text` and `limitations`, supplied by the author.
- Nonempty, unique `evidence_ids` referencing existing extracted results.
- Optional `context_ids`, each sharing at least one cited result.
- `review_status`: `pending` (default) or `reviewed`.

Unknown fields are rejected. Empty, malformed or unknown evidence citations fail
with the statement ID rather than producing an apparently reviewed uncited claim.
These are **extraction-level citation IDs**, not a fabricated author-year/DOI
bibliography. Context-only or uncited narrative is outside this statement contract;
do not invent result citations to satisfy it.

Every statement packet includes exact extraction/source traces, screening/report
links, explicit context scope and intersecting appraisals. Context and appraisal
intersections are shown separately from their other linked extraction IDs. Sharing
a study does not extend an appraisal to another result. Different reviewer
judgements remain separate; there is no consensus or score.

`evidence_without_statement_citation` means only that no supplied statement names
that extraction ID. It is not an automatic claim that relevant evidence was omitted.
When the synthesis stage is absent, this field is null rather than diagnosing every
result as missing a citation.

## Review preparation and staleness

For a pending statement, the snapshot exposes `statement_review_targets` containing
its current canonical basis and hash. An author can inspect that target and, after
review, explicitly supply `reviewer`, ISO-date `reviewed_at`, `basis_sha256` and
`review_status: "reviewed"`. The tool never fills in a reviewer, changes status or
renews a stale hash.

The basis binds statement wording, limitations and citation lists to:

- Question/eligibility scope and supplied search plan, searches, screening and
  reports, represented by one shared source-scope hash.
- Full cited extraction rows, explicitly cited context and intersecting appraisals.

Review metadata itself is excluded to avoid a self-referential hash. Object-key
order is ignored; list order and JSON value types are retained. A supplied reviewed
statement becomes `STALE_SOURCE` when its bound inputs change; its old review
metadata remains visible. `CURRENT_SOURCE` means content matching only, not an
authenticated reviewer or a validated scientific statement.

Changes to **uncited** extraction rows do not invalidate a statement's cited-source
review hash. Those results remain visible in the full inventory/uncited list. This
is not a review of the entire evidence corpus or a semantic completeness check.
Changing unrelated statements or WP progress also does not invalidate the binding.
Keep previous protocol versions to inspect changes; a hash is not amendment history.

All statements always carry `support_status: "NOT_ASSESSED"`, even when reviewed
and source-matching. Citation linkage alone establishes neither entailment nor
causal, scientific or clinical validity.

## Adapter, bundles and reproducibility

A reviewed mock adapter protocol may be enriched with synthesis statements without
changing its reviewed sources. Existing adapter integrity checks still reject edited
accepted evidence or stale receipt provenance. Compact candidate source locators,
quotes and extractor labels are displayed as unverified source aids; they do not
prove source authenticity or that a model actually ran.

The core workflow, report output, status, comparison and existing bundle JSON carry
statement review metadata and gaps. Bundle verification rechecks source bindings and
regeneration, but permits visibly stale supplied reviews. A valid bundle is not a
scientific approval. The standalone `synthesis_review.py` snapshot is not a new
archive payload; retain its original protocol and recorded implementation hashes
(including the status implementation dependency) to reproduce it.

Text values are quoted with control/format/line-separator characters escaped. JSON
input is strict UTF-8 and rejects duplicate keys/non-finite numbers. Neither output
is redacted; keep real source texts and reviewer metadata outside the public repo.
No network call, model, credential, paid service or upload is used.

Even with empty mechanical queues, the snapshot retains
`extraction_completeness: NOT_ESTABLISHED`, `census_claim: NOT_ESTABLISHED` and
`conclusion_readiness: NOT_READY`. It claims neither full PRISMA compliance nor an
actual literature census, guideline currency, scientific synthesis or clinical
recommendation.
