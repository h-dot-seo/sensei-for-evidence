# sensei-for-evidence

질문 정의부터 검색·선별·추출·근거 검토·후속 작업까지 연결하는 추적 가능한 연구 워크플로입니다.
A method-first framework for traceable evidence research and bounded conclusions.

**Search completion is not evidence sufficiency.** A consistent file, completed
work-package assertion or reproducible bundle is not a completed scientific study.

## What is implemented

Standard-library Python tools reconcile **supplied data**, without calling search
services or models:

- Declared search plans and optional page ledgers, including missing sources,
  count mismatches, overlap, truncation and incomplete pagination.
- Provider-neutral mock search/extraction receipts with hash-bound operator review
  gates; unreviewed proposals never enter accepted evidence. No live API client.
- Local UTF-8 CSV export provenance and explicit supplied identity reconciliation,
  with raw-row retention and incomplete-search promotion into screening queues.
- Per-record search-occurrence provenance with exact-ID-only deduplication.
  Similar IDs are not merged; repeated IDs are not verified duplicate publications.
- Record screening, report retrieval/full-text decisions, study IDs and reasoned
  exclusions, with separate record/result/report counts.
- Supplied nonclinical comparison conditions with model, concentration/exposure,
  observation-time anchors, comparator and causal limitations; no procedure or inference.
- Multiple result rows per source, including null findings, with extraction-level
  IDs and traceable locators. Included reports may explicitly declare multiple
  study IDs, with separate report-study result-presence accounting.
- Supplied clinical-guideline and drug-development context, applicability limits,
  reviewer status and evidence/work-package links.
- Explicit pre-extraction source context linked to declared searches or enumerated
  records and source-review work, without inventing evidence or study IDs.
- Supplied appraisal methods and domain judgements, with reviewer provenance and
  missing-appraisal coverage. No appraisal score or consensus is inferred.
- Dependency-aware work packages, deliverables and explicit completion assertions,
  including source-review work before any result has been extracted.
- PRISMA-oriented synthesis review snapshots with exact result citations, visible
  uncited evidence and source-bound supplied reviews; no generated conclusions.
- Supplied planning ranks with rationale/uncertainty and source-staleness checks;
  ranks never override dependencies or become automated recommendations.
- Per-work-package review packets joining source lineage, guideline/development
  applicability limits, appraisal provenance and local review gaps without decisions.
- Deterministic offline ZIP bundles, SHA-256 checks, regeneration verification and
  CSV exports, plus version-to-version mechanical comparison.

No live literature retrieval, full-text reading, guideline currency verification,
scientific appraisal, meta-analysis, clinical recommendation or legal opinion is
performed. Search pages, source locators and reviewer claims are not authenticated.
Census and conclusion readiness remain `NOT_ESTABLISHED` and `NOT_READY`.

## Quick start

New to the tools? Follow the [first offline run](docs/FIRST_RUN.md): 11 tested
commands from a declared question and mock receipt through explicit supplied
reviews, PRISMA accounting, nonclinical/context work and a verified bundle.
Human-authored inputs and automatic bookkeeping are separated at each step.

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
experimental/clinical recommendation. Comparing the demo with itself reports no
input changes; use two supplied protocol versions for a real mechanical comparison.

## Choose a command

| Command | Purpose |
|---|---|
| `review_handoff.py PROTOCOL.json [--work-package ID] [--text]` | Read-only operator sheet: manual queues, input locations, work deliverables and detailed-view navigation |
| `receipt_intake.py template BASE.json` / `check BASE.json RECEIPTS.json [--text] [--protocol-output NEW.json]` | Guide synthetic manual receipt entry and inspect unreviewed candidates through the existing adapter |
| `bibliographic_intake.py preview PROTOCOL.json EXPORT.csv --search-id ID --searched-at TEXT [--output NEW.json] [--text]` / `verify ARTIFACT.json [--text]` | Retain exact local CSV bytes and inspect detached unreviewed candidates |
| `bibliographic_review.py template ARTIFACT.json` / `target PROTOCOL.json ARTIFACT.json CHOICES.json` / `assemble PROTOCOL.json ARTIFACT.json REVIEW.json [--protocol-output NEW.json] [--text]` | Bind explicit collection choices and supplied review to an append-only incomplete search |
| `offline_adapter.py PROTOCOL.json FIXTURE.json [--reviews REVIEWS.json] [--protocol-output OUTPUT.json]` | Run the synthetic adapter contract and review gates |
| `synthesis_review.py PROTOCOL.json [--text]` | Review stage counts, supplied statement citations and unresolved limits |
| `work_review.py PROTOCOL.json [--work-package ID] [--text]` | Join evidence/context/uncertainty around a work deliverable |
| `research_status.py PROTOCOL.json [--text]` | View mechanical review queues and unknown stages |
| `validate_run.py STATE.json` | Validate selected state/release consistency rules |
| `evidence_workflow.py PROTOCOL.json` | Reconcile search, screening, results, context, appraisal and work |
| `search_manifest.py PROTOCOL.json [--text]` | Freeze exact query specs and source-wise receipt, interruption and overlap accounting without executing searches |
| `prisma_audit.py PROTOCOL.json [--text]` | Export unit-specific members, exclusion reasons, identity links and supplied-count partitions |
| `prisma_reports.py PROTOCOL.json` | Add report/full-text/study and extraction-queue accounting |
| `research_bundle.py create PROTOCOL.json OUTPUT.zip` | Create a new portable supplied-data bundle |
| `research_bundle.py verify OUTPUT.zip` | Check hashes, implementation bytes and regenerated outputs |
| `compare_runs.py BEFORE.json AFTER.json [--text]` | Show mechanical input/ledger changes, explicit report-study migrations, completion-source differences and version warnings |
| `screening_review.py PROTOCOL.json [--record-id ID] [--template] [--text]` | Inspect source-bound supplied reviewer positions or prepare blank assertions without deciding eligibility |
| `screening_decision.py target/assemble/inspect ...` | Apply only an explicit supplied screening choice to a new candidate, retaining source/reviewer decision receipts |
| `report_review.py PROTOCOL.json [--report-id ID] [--template] [--text]` | Inspect supplied full-text versions and reviewer positions without verifying documents or changing decisions |
| `report_study_review.py PROTOCOL.json [--report-id ID --study-id ID] [--template] [--text]` | Keep exact report-study human positions and explicit reviewed-source selections separate from report eligibility |
| `report_study_inventory.py PROTOCOL.json [--report-id ID --study-id ID] [--template] [--text]` | Describe explicit candidate studies before full-text inclusion without creating memberships or eligibility |

Use [detailed usage and compatibility](docs/USAGE.md) for field requirements,
examples, ID migration, stage definitions, strict JSON rules and limitations.
Existing bundles require their recorded implementation bytes for verification.
Comparison hashes ignore object key order but retain list order; exact-input bundle
hashes preserve original bytes. Neither kind of hash is a signature.

## Research method and publication boundary

The framework supports plan, run, status, method and audit intents. Choose
question-appropriate established methods, preserve contradictions and uncertainty,
and distinguish supplied observations from interpretation and decisions.

- [Workflow instructions](SKILL.md)
- [Architecture and methodological boundaries](docs/ARCHITECTURE.md)
- [Validation record](VALIDATION.md)
- [Public extraction boundary](PUBLICATION.md)
- [Security](SECURITY.md) and [rights](RIGHTS.md)

Only generic code, documentation and synthetic fixtures are included. No private
research corpus, account information, article/book full text, figures, real
experimental results or scientific validation data are included. No license has
been selected by the owner yet.

See [the mock adapter contract](docs/ADAPTER_CONTRACT.md) for the synthetic
search → receipt review → extraction review → report/status/bundle example.

See [work review packets](docs/WORK_REVIEW.md) for the synthetic guideline,
development and research-management handoff example.

See [supplied planning assertions](docs/PLANNING_ASSERTIONS.md) for recording a
rank, checking changed source context and keeping priority separate from dependencies.

See [synthesis review snapshots](docs/SYNTHESIS_REVIEW.md) for the record/report/
study/result accounting and supplied statement review journey.

See [nonclinical condition records](docs/EXPERIMENT_CONDITIONS.md) for the fictional
model/condition → result → WP/synthesis review journey.

Outcome- and arm-specific sample reporting is available in the fictional
[`sampling-review.json`](examples/sampling-review.json) workflow. It exposes
missing n semantics and independence explanations without inferring sample size
or assessing statistics. See [condition metadata](docs/EXPERIMENT_CONDITIONS.md#outcome-specific-sample-reporting).

[`statistics-review.json`](examples/statistics-review.json) demonstrates supplied
arm summaries, statistical metadata and explicitly oriented effect-direction
text. [Outcome statistics review](docs/OUTCOME_STATISTICS.md) explains missing
fields and literal-label cues without numerical or scientific inference.

[`claim-comparison.json`](examples/claim-comparison.json) adds human-supplied
observation/causal claim positions alongside source-linked results, n and statistics.
[Claim-position comparison](docs/CLAIM_COMPARISON.md) explains exact scope,
stale review and why positions are not independent votes or inferred conclusions.

Start with the [operator handoff journey](docs/OPERATOR_HANDOFF.md) to see which
steps remain human work and reproduce evidence → claim/guideline → WP → bundle
review using real CLI commands on the fictional fixture.

The [PRISMA-oriented accounting export](docs/PRISMA_AUDIT.md) exposes exact member
IDs and record/report/study/result links for audit, without certifying a complete
search or PRISMA compliance. Try `examples/prisma-audit.json`.

Before wiring a live provider, use the [search query/receipt manifest](docs/SEARCH_MANIFEST.md)
with `examples/search-manifest.json` to inspect exact requests, missing runtime
fields and source-wise unresolved receipts. No query translation or execution occurs.

For manual-entry rehearsal, start with [receipt intake](docs/RECEIPT_INTAKE.md).
It generates deliberately unfilled request/page fields and checks a filled mock
fixture without accepting reviews or overwriting existing research.

[Source-review work packages](docs/SOURCE_REVIEW_WORK.md) connect unreviewed manual
receipts to search/screening/extraction deliverables without fabricating evidence
IDs. Try `examples/source-work-protocol.json` with the existing work/handoff CLIs.

PRISMA audit JSON also exposes [work/deliverable traceability](docs/PRISMA_AUDIT.md#work-and-deliverable-traceability):
explicit source/result work references, indirect report links and unverified
artifact assertions, without treating task completion as source approval.

[Opt-in local artifact review](docs/LOCAL_ARTIFACT_REVIEW.md) checks explicitly
listed synthetic local files against supplied size/SHA-256 expectations using
safe POSIX directory descriptors. Unsupported platforms fail closed; matching
bytes are never acceptance of a work package or scientific conclusion.

[Guideline/development amendment comparison](docs/CONTEXT_AMENDMENTS.md) extends
compare_runs with explicit context→result→work snapshots and retained-review-label
cues. Version/access/review dates, applicability and uncertainty stay separate;
no clinical significance, regulatory decision or new priority is inferred.

[Prerequisite review packets](docs/PREREQUISITE_REVIEW.md) open a selected WP and
its explicit transitive prerequisites together, preserving source/experimental/
guideline gaps and supplied planning rationale beside deliverables and completion
criteria. Dependency-first display is not an automated research decision.

[Planning rationale citations](docs/PLANNING_RATIONALE_LINKS.md) connect existing
human planning assertions to supplied hypotheses and challenging/unresolved
positions. They add source-change tracking, not automated rationale validation,
refutation, clinical decisions or new priorities.

[Compact work navigation](docs/WORK_NAVIGATION.md) adds `work_review.py --brief`
for packet-scoped status groups, deliverables, completion criteria and existing
review cues. It shortens the review view without choosing the next task.

[Supplied amendment notes](docs/AMENDMENT_NOTES.md) optionally bind a human change
reason, scope and version labels to the exact inputs of compare_runs, with observed
review/work-state transitions. Matching notes are not change approval or legal,
scientific or regulatory validation.

[Completion source binding](docs/COMPLETION_BINDING.md) flags unbound/stale COMPLETE
assertions after work/source/locator changes, reusing planning source scope. It
never verifies acceptance, renews a hash or automatically reopens work.

Selected work views also expose [direct prerequisite completion cues](docs/PREREQUISITE_REVIEW.md#completion-source-cues-without-expanding-packets):
CURRENT/STALE/UNBOUND source labels remain visible even when full prerequisite
packets are omitted. Recorded unblocking stays separate from acceptance review.

[Portable work-package CSV exports](docs/COMPLETION_BINDING.md#portable-csv-and-bundle-summary)
also preserve supplied completion assertions, source-binding hashes, direct
prerequisite labels and explicit nonverification states without changing work status.

[Completion amendment comparison](docs/COMPLETION_COMPARISON.md) identifies changed
work/source sections and direct prerequisite labels across two supplied snapshots.
It separates own artifact-locator changes from source-basis changes without
reconstructing historical acceptance reasons or reopening completed work.

Add `--text` to [protocol comparison](docs/COMPLETION_COMPARISON.md#readable-comparison-output)
for a read-only summary with exact input hashes, changed field names, all work
source states and amendment-binding results. Full JSON remains the default.

[Local bibliographic CSV intake](docs/BIBLIOGRAPHIC_INTAKE.md) preserves exact export
bytes, original rows and an explicit search-plan association in a detached,
unreviewed artifact. Duplicate occurrences and locator conflicts remain visible;
byte-consistency verification does not authenticate the source or promote rows
into screening, PRISMA counts, guideline links or development evidence.

[Explicit CSV reconciliation](docs/BIBLIOGRAPHIC_REVIEW.md) connects those artifacts
to screening through supplied per-row identity/withholding choices and a separate
exact-context review. Repeated imports retain flat source provenance and raw-row
accounting while appending only incomplete searches, with no eligibility decisions.

[Pre-extraction context links](docs/SOURCE_CONTEXTS.md) connect supplied guideline
and development questions to exact typed source references and source-review work.
They preserve applicability uncertainty and remain separate from extracted evidence.

[Multiple studies in one report](docs/MULTI_STUDY_REPORTS.md) supports explicit
plural study declarations while keeping legacy record/report counts unchanged.
Missing report-study result memberships stay visible without inferring identity,
independence, study-level eligibility or exhaustive extraction.

[Supplied screening reviewer positions](docs/SCREENING_REVIEWS.md) preserve
separate title/abstract judgments, source/criteria hashes and differing or stale
assertions after collection. They never vote, adjudicate eligibility, authenticate
reviewers or replace canonical screening and PRISMA counts.

[Explicit supplied screening decisions](docs/SCREENING_DECISIONS.md) connect those
positions to a separately authored human choice. Target-bound assembly retains
before/after rows and source/reviewer snapshots, refuses structural conflicts,
and never votes, authenticates chronology or verifies medical correctness.

[Supplied full-text reviewer positions](docs/REPORT_REVIEWS.md) bind separate human
positions to declared document versions and mapped record context. Read-only
scaffolds preserve missing/unverified digests, source coverage and disagreement;
no document reading, consensus or per-study eligibility is inferred.

[Exact report-study reviewer positions](docs/REPORT_STUDY_REVIEWS.md) distinguish
human opinions on individual studies from report inclusion. Explicit source-ID
selections and unresolved orphan assertions remain visible without choosing a
canonical study outcome, changing PRISMA counts or filtering extracted results.

[Descriptive candidate inventory](docs/REPORT_STUDY_INVENTORY.md) permits source-linked
human descriptions on retrieved reports before their full-text inclusion decision.
Novel-label scaffolds do not count as stored assertions or change included study
memberships, prior review targets, results or pending-work queues.

[Explicit local source-byte checks](docs/REPORT_SOURCE_CHECK.md) compare a selected
local document with its supplied source digest through a bounded no-follow file
checker. Detached observations never certify reading, authenticity or eligibility,
change canonical state, or follow locators. Unsupported platforms fail closed.

[Explicit full-text decision records](docs/REPORT_DECISIONS.md) apply a separately
supplied human include/exclude choice and exact study declaration to a detached
candidate. Replay against the original input precedes protocol export; conflicting
result links are rejected rather than deleted, and reviewer positions never vote.

[Document-linked source work](docs/WORK_DOCUMENT_SOURCES.md) optionally binds named
report-source versions to a source-review task and its direct dependents. Changed
document context can stale planning/completion assertions without reopening work,
automatically accepting it, or changing legacy task hashes when omitted.
