# sensei-for-evidence

질문 정의부터 검색·선별·추출·근거 검토·후속 작업까지 연결하는 추적 가능한 연구 워크플로입니다.
A method-first framework for traceable evidence research and bounded conclusions.

한국어 안내: [docs/README.ko.md](docs/README.ko.md)

**Search completion is not evidence sufficiency.** A consistent file, completed
work-package assertion or reproducible bundle is not a completed scientific study.

## Purpose and scope

| | |
|---|---|
| Does | Standard-library Python tools reconcile **supplied data** (search plans, receipts, citation files, screening, reports, results, context, appraisals, statements, challenges, work) into traceable ledgers, review queues, deterministic bundles and version comparisons, exposing what is missing, stale or unreviewed. |
| Does not | Search literature (only the explicitly invoked, preview-bound PubMed ESearch/EFetch clients make live requests), retrieve full text, read papers, call models, verify guideline currency, authenticate search pages, source locators or reviewer claims, appraise, meta-analyse, recommend clinically or give legal opinions. Census stays `NOT_ESTABLISHED`; conclusion readiness stays `NOT_READY`. |

## What is implemented

- **Collect**: preview-bound, keyless PubMed identifier discovery and explicit selected-PMID
  EFetch MEDLINE title/abstract acquisition with retained native observations, explicit
  caps/failures and separate unreviewed intake; declared search plans and optional page
  ledgers exposing missing sources, count mismatches, overlap, truncation and incomplete
  pagination; offline mock receipts with hash-bound review gates; exact CSV/NBIB/RIS export
  provenance with explicit identity reconciliation that promotes only incomplete searches
  into screening queues.
- **Screen**: per-record search-occurrence provenance with exact-ID-only deduplication
  (similar IDs are never merged, repeated IDs are not verified duplicates); record screening,
  report retrieval/full-text decisions, study IDs and reasoned exclusions with separate
  record/result/report counts; explicit multiple study IDs per report.
- **Extract**: multiple result rows per source including null findings, with extraction-level
  IDs and locators; local UTF-8 passage checks kept separate from scientific acceptance;
  supplied nonclinical comparison conditions (model, concentration/exposure, time anchors,
  comparator, causal limitations) without procedure or inference.
- **Contextualize and appraise**: supplied guideline/development context with applicability
  limits, reviewer status and evidence/work links; pre-extraction source context on searches,
  records and source-review work; supplied appraisal methods and domain judgements with
  provenance and missing-appraisal coverage, never a score or consensus.
- **Plan and work**: dependency-aware work packages, deliverables and explicit completion
  assertions, including source-review work before extraction; supplied planning ranks that
  never override dependencies; per-work-package review packets joining source lineage,
  applicability limits and appraisal provenance without decisions.
- **Synthesize, challenge, assess readiness**: PRISMA-oriented synthesis snapshots with exact
  citations, visible uncited evidence and source-bound reviews; supplied independent
  challenges (distinct challenger label, strongest alternative explanation, missing
  discriminating evidence, citation-integrity findings, conclusion width, outcome) bound to
  the statements' current bases, where a material gap must name reopening work or an
  amendment; twelve mechanical readiness gates with exact open items and a gate-ledger
  hash, plus supplied sufficiency/readiness assertions bound to that hash. Closed gates are
  bookkeeping, not sufficiency; the mechanical label stays NOT_READY.
- **Archive and compare**: deterministic offline ZIP bundles with SHA-256 checks, regeneration
  verification and CSV exports; typed native-collection and transition archives;
  version-to-version mechanical comparison with optional amendment notes.

- **Inspect implementation drift**: read-only per-file hash diagnostics for old bundles
  and detached records, with optional supplied publication-manifest matching.

- **Export counts**: native, conservative PRISMA-oriented crosswalk CSV with explicit
  search-arm choices, blank unknown stages and a full pending-work receipt.

- **Share records**: detached CSV of existing record/occurrence/report/result links,
  supplied review cues and explicit missing stages, with a bounded fingerprint receipt.

- **Share status**: detached Markdown with all supplied status fields and review
  queues, quoted data, unknown-versus-zero counts and an output fingerprint receipt.

See [shareable status](docs/SHAREABLE_VIEWS.md) for the tested read-only Markdown
rehearsal and safe sharing boundaries.

See [native count crosswalk](docs/PRISMA_FLOW_TEMPLATE.md) for the tested rehearsal
and the distinction from external PRISMA diagram templates.

## Start here

- [First offline run](docs/FIRST_RUN.md): 11 tested commands from a declared question and
  mock receipt to supplied reviews, PRISMA accounting, context work and a verified bundle.
- [NBIB-to-evidence rehearsal](docs/BATCH_TO_EVIDENCE.md), then the
  [second-search continuation](docs/SECOND_SEARCH_CONTINUATION.md): citation files through
  reconciliation, screening, reports, results and an original-source bundle.
- [RIS intake](docs/RIS_INTAKE.md) for the supported RIS subset, archived with NBIB wrappers
  by the [typed native collection archive](docs/NATIVE_COLLECTION_BUNDLES.md).
- [Operator handoff](docs/OPERATOR_HANDOFF.md): one read-only sheet of manual queues and
  every supplied-input route, executing nothing.

## Quick start

Python 3.10+, no third-party dependencies. Run from the repository root:

```sh
python -m unittest discover -v
python review_handoff.py examples/claim-comparison.json --work-package WP-TRANSLATION --text
python research_status.py examples/review-demo.json --text
python evidence_workflow.py examples/review-demo.json
python prisma_reports.py examples/review-demo.json
python research_bundle.py create examples/review-demo.json ../synthetic-review.zip
python research_bundle.py verify ../synthetic-review.zip
python compare_runs.py examples/review-demo.json examples/review-demo.json
```

The ZIP output must not already exist. Keep real research inputs and generated
bundles outside this public repository: bundles preserve all supplied data without
redaction. No upload or external request is made by these commands.

The **entirely synthetic** demo deliberately remains unfinished:

- Two identified records, one included report/study and two result rows.
- One planned source is missing, one context review is pending and one result has
  no recorded appraisal.
- `WP-TRANSLATION` depends on unfinished `WP-MECHANISM`.
- Bundle verification can pass while all scientific-readiness bounds remain closed.

It illustrates bookkeeping and test behavior, not research findings or an
experimental/clinical recommendation.

## Commands at a glance

Exact usage of every script and subcommand: [command reference](docs/COMMANDS.md); narratives by stage: [workflows](docs/WORKFLOWS.md).

Layout: every command-line script is a module at the repository root and runs as
`python <script>.py ...` from there, next to the engine modules it imports; the synthetic
test suite is the `tests/` package that `python -m unittest discover -v` recurses into.
The dispatcher `sensei.py` lists those scripts and runs one of them without changing any
documented command.

| Entry points | Purpose |
|---|---|
| `sensei.py` | `list` prints every root script with its first docstring sentence and the operator-handoff routes with their guides, executing nothing; `run <script> [args...]` runs one root script exactly as `python <script>` does |
| `review_handoff.py`, `research_status.py` | Read-only operator sheet with manual queues and supplied-input routes; review queues |
| `evidence_workflow.py`, `prisma_reports.py`, `prisma_audit.py` | Reconcile search → screening → results → work; report/full-text accounting; PRISMA-oriented export |
| `views_export.py status` | Save supplied-data status Markdown with every queue and a separate receipt; no readiness judgement |
| `views_export.py records` | Save existing supplied-record joins as detached CSV; no adjudication or bundle change |
| `views_export.py flow` | Save accounting-only Mermaid text with separate partitions and unit bridges; no official diagram or renderer |
| `prisma_flow_template.py` | Export a native supplied-count crosswalk CSV, not an external PRISMA template |
| `search_manifest.py`, `receipt_intake.py`, `offline_adapter.py` | Frozen query/receipt accounting; manual receipt rehearsal; offline mock adapter |
| `bibliographic_intake.py`, `nbib_intake.py`, `nbib_batch_intake.py`, `ris_intake.py`, `bibliographic_review.py` | Preserve CSV/NBIB/RIS exports byte-exactly, then reconcile identities explicitly into screening |
| `pubmed_discovery.py`, `pubmed_metadata.py` | Optional preview-bound live ESearch/EFetch; the only networked commands |
| `screening_review.py`, `screening_decision.py` | Supplied reviewer positions; explicit supplied screening decisions |
| the ten `report_*.py` command-line scripts, `inventory_intake.py` | Report registration, retrieval updates, source declarations and byte checks, full-text positions and decisions, report-study positions and inventory |
| `result_*.py`, `condition_intake.py` | Worksheets, passage checks, manual result intake, drift comparison, text corrections, nonclinical conditions |
| `context_intake.py`, `work_context_intake.py`, `appraisal_intake.py`, `appraisal_source_review.py` | Supplied context and work assignment; supplied appraisals and later comparison |
| `synthesis_review.py`, `challenge_intake.py`, `readiness_review.py`, `readiness_intake.py` | Synthesis snapshot; independent challenges; readiness gates and sufficiency/readiness assertions |
| `work_review.py`, `source_work_intake.py`, `evidence_work_intake.py`, `work_completion_intake.py`, `artifact_review.py` | Work packets; reviewed work proposals and completion; artifact byte checks |
| `research_bundle.py`, `*_bundle.py`, `compare_runs.py`, `validate_run.py` | Deterministic bundles and archives; version comparison; state validation |

See [implementation revisions](docs/IMPLEMENTATION_REVISIONS.md) to diagnose old
artifacts without executing historical code.

## Documentation

- [Implementation revision inspection](docs/IMPLEMENTATION_REVISIONS.md)

Start and reference
- [First offline run](docs/FIRST_RUN.md)
- [Operator handoff](docs/OPERATOR_HANDOFF.md)
- [NBIB-to-evidence rehearsal](docs/BATCH_TO_EVIDENCE.md)
- [Second-search continuation](docs/SECOND_SEARCH_CONTINUATION.md)
- [Command reference](docs/COMMANDS.md)
- [Workflows](docs/WORKFLOWS.md)
- [Detailed usage and compatibility](docs/USAGE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [한국어 안내](docs/README.ko.md)
- [Validation history](docs/VALIDATION_HISTORY.md)

Search plans, receipts and source work
- [Search manifest](docs/SEARCH_MANIFEST.md)
- [Receipt intake](docs/RECEIPT_INTAKE.md)
- [Adapter contract](docs/ADAPTER_CONTRACT.md)
- [Source-review work](docs/SOURCE_REVIEW_WORK.md)
- [Source work intake](docs/SOURCE_WORK_INTAKE.md)
- [Source contexts](docs/SOURCE_CONTEXTS.md)
- [Work document sources](docs/WORK_DOCUMENT_SOURCES.md)

Citation files and collection
- [CSV intake](docs/BIBLIOGRAPHIC_INTAKE.md)
- [NBIB intake](docs/PUBMED_NBIB_INTAKE.md)
- [NBIB batch](docs/PUBMED_NBIB_BATCH.md)
- [RIS intake](docs/RIS_INTAKE.md)
- [Collection review](docs/BIBLIOGRAPHIC_REVIEW.md)
- [Collection bundles](docs/COLLECTION_BUNDLES.md)
- [Batch collection bundles](docs/BATCH_COLLECTION_BUNDLES.md)
- [Native collection bundles](docs/NATIVE_COLLECTION_BUNDLES.md)
- [PubMed discovery](docs/PUBMED_DISCOVERY.md)
- [PubMed metadata](docs/PUBMED_METADATA.md)

Screening and reports
- [Screening reviews](docs/SCREENING_REVIEWS.md)
- [Screening decisions](docs/SCREENING_DECISIONS.md)
- [PRISMA audit](docs/PRISMA_AUDIT.md)
- [Multi-study reports](docs/MULTI_STUDY_REPORTS.md)
- [Report intake](docs/MANUAL_REPORT_INTAKE.md)
- [Retrieval updates](docs/REPORT_RETRIEVAL_UPDATES.md)
- [Source declarations](docs/MANUAL_SOURCE_DECLARATIONS.md)
- [Source check](docs/REPORT_SOURCE_CHECK.md)
- [Report reviews](docs/REPORT_REVIEWS.md)
- [Report decisions](docs/REPORT_DECISIONS.md)
- [Report-study reviews](docs/REPORT_STUDY_REVIEWS.md)
- [Study inventory](docs/REPORT_STUDY_INVENTORY.md)
- [Inventory intake](docs/MANUAL_INVENTORY_INTAKE.md)
- [Candidate reviews](docs/INVENTORY_CANDIDATE_REVIEWS.md)
- [Report transitions](docs/REPORT_TRANSITION_BUNDLES.md)

Results and conditions
- [Extraction worksheets](docs/EXTRACTION_WORKSHEETS.md)
- [Passage check](docs/RESULT_PASSAGE_CHECK.md)
- [Result intake](docs/MANUAL_RESULT_INTAKE.md)
- [Result source review](docs/RESULT_SOURCE_REVIEW.md)
- [Result corrections](docs/RESULT_CORRECTIONS.md)
- [Condition intake](docs/MANUAL_CONDITION_INTAKE.md)
- [Experiment conditions](docs/EXPERIMENT_CONDITIONS.md)
- [Outcome statistics](docs/OUTCOME_STATISTICS.md)
- [Claim comparison](docs/CLAIM_COMPARISON.md)
- [Extraction transitions](docs/EXTRACTION_TRANSITION_BUNDLES.md)

Context, appraisal, synthesis and readiness
- [Context intake](docs/MANUAL_CONTEXT_INTAKE.md)
- [Work context intake](docs/WORK_CONTEXT_INTAKE.md)
- [Context amendments](docs/CONTEXT_AMENDMENTS.md)
- [Appraisal intake](docs/MANUAL_APPRAISAL_INTAKE.md)
- [Appraisal source review](docs/APPRAISAL_SOURCE_REVIEW.md)
- [Appraisal transitions](docs/APPRAISAL_TRANSITION_BUNDLES.md)
- [Synthesis review](docs/SYNTHESIS_REVIEW.md)
- [Independent challenge](docs/INDEPENDENT_CHALLENGE.md)
- [Conclusion readiness](docs/CONCLUSION_READINESS.md)

Planning, work and completion
- [Work review](docs/WORK_REVIEW.md)
- [Work navigation](docs/WORK_NAVIGATION.md)
- [Prerequisite review](docs/PREREQUISITE_REVIEW.md)
- [Planning assertions](docs/PLANNING_ASSERTIONS.md)
- [Rationale links](docs/PLANNING_RATIONALE_LINKS.md)
- [Amendment notes](docs/AMENDMENT_NOTES.md)
- [Completion binding](docs/COMPLETION_BINDING.md)
- [Completion comparison](docs/COMPLETION_COMPARISON.md)
- [Evidence work intake](docs/EVIDENCE_WORK_INTAKE.md)
- [Completion intake](docs/WORK_COMPLETION_INTAKE.md)
- [Work transitions](docs/WORK_TRANSITION_BUNDLES.md)
- [Artifact review](docs/LOCAL_ARTIFACT_REVIEW.md)

## Research method and publication boundary

- [Workflow instructions](SKILL.md)
- [Architecture and methodological boundaries](docs/ARCHITECTURE.md)
- [Validation record](VALIDATION.md)
- [Public extraction boundary](PUBLICATION.md)
- [Security](SECURITY.md) and [rights](RIGHTS.md)

Only generic code, documentation and synthetic fixtures are included. No private
research corpus, account information, article/book full text, figures, real
experimental results or scientific validation data are included. No license has
been selected by the owner yet.

See [supplied-data accounting flow](docs/ACCOUNTING_FLOW.md) for a tested detached
Mermaid text view of existing audit counts, not an official PRISMA diagram.

See [records CSV](docs/RECORDS_CSV.md) for the tested export, column meanings and
unredacted-data sharing boundary.
