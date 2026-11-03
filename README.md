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
- Per-record search-occurrence provenance with exact-ID-only deduplication.
  Similar IDs are not merged; repeated IDs are not verified duplicate publications.
- Record screening, report retrieval/full-text decisions, study IDs and reasoned
  exclusions, with separate record/result/report counts.
- Supplied nonclinical comparison conditions with model, concentration/exposure,
  observation-time anchors, comparator and causal limitations; no procedure or inference.
- Multiple result rows per source, including null findings, with extraction-level
  IDs and traceable locators. The current model allows one study ID per record/report.
- Supplied clinical-guideline and drug-development context, applicability limits,
  reviewer status and evidence/work-package links.
- Supplied appraisal methods and domain judgements, with reviewer provenance and
  missing-appraisal coverage. No appraisal score or consensus is inferred.
- Dependency-aware work packages, deliverables and explicit completion assertions.
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

Python 3.10+, no third-party dependencies. Run from the repository root:

```sh
python -m unittest discover -v
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
| `offline_adapter.py PROTOCOL.json FIXTURE.json [--reviews REVIEWS.json] [--protocol-output OUTPUT.json]` | Run the synthetic adapter contract and review gates |
| `synthesis_review.py PROTOCOL.json [--text]` | Review stage counts, supplied statement citations and unresolved limits |
| `work_review.py PROTOCOL.json [--work-package ID] [--text]` | Join evidence/context/uncertainty around a work deliverable |
| `research_status.py PROTOCOL.json [--text]` | View mechanical review queues and unknown stages |
| `validate_run.py STATE.json` | Validate selected state/release consistency rules |
| `evidence_workflow.py PROTOCOL.json` | Reconcile search, screening, results, context, appraisal and work |
| `prisma_reports.py PROTOCOL.json` | Add report/full-text/study and extraction-queue accounting |
| `research_bundle.py create PROTOCOL.json OUTPUT.zip` | Create a new portable supplied-data bundle |
| `research_bundle.py verify OUTPUT.zip` | Check hashes, implementation bytes and regenerated outputs |
| `compare_runs.py BEFORE.json AFTER.json` | Show mechanical input/ledger changes and version warnings |

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
