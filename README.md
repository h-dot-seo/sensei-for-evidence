# sensei-for-evidence

질문 정의부터 근거 수집·종합·반론 검토·결론 범위 판단까지 연결하는 연구 방법 프레임워크입니다.
A method-first framework for traceable evidence research and bounded conclusions.

## Core principle

**Search completion is not evidence sufficiency.** A persuasive narrative does not
replace a reproducible search, claim-linked evidence or an explicit uncertainty bound.

## Included

- Workflow design for neutral discovery, protocol lock, search, screening, extraction,
  normalization, appraisal, synthesis, independent challenge and controlled reopening.
- A portable agent workflow (`SKILL.md`) with plan/run/status/method/audit intents.
- A deterministic research-state validator (`validate_run.py`) and synthetic tests/example.

No private research projects, experiment results, evidence databases, article/book
full text, extracted figures, paid databases or real patent-census datasets are included.
This repository does not itself execute searches, read papers, run an LLM, determine
scientific adequacy or deliver a legal freedom-to-operate opinion.

## Quick start

Python 3.10+, standard library only:

```sh
python3 validate_run.py examples/state.json
python3 -m unittest discover -v
```

The pending synthetic state passes consistency checks while its conclusion remains
`NOT_READY`. A valid file is not a completed study. `COMPLETE` additionally requires
explicit sufficiency, readiness, QA, storage and traceable citation/artifact fields;
these remain recorded assertions until independently checked against real evidence.

## Research intents

| Intent | Output |
|---|---|
| Plan | Research map, scope, sources, criteria, extraction, appraisal and stop conditions |
| Run | Execution within a resolved question and versioned protocol |
| Status | Phase, coverage, contradiction, blocker and next action |
| Method | Established term, rationale, applicability, inputs, procedure, failures and references |
| Audit | Claim/evidence challenge, alternatives, surviving boundary and discriminating gaps |

Prefer established methods and current authoritative references appropriate to the
question. This framework does not reproduce or replace those standards.
See [architecture](docs/ARCHITECTURE.md), [workflow](SKILL.md),
[publication boundary](PUBLICATION.md), [security](SECURITY.md), and [rights](RIGHTS.md).
No license has been selected by the owner yet.

## Search-to-work-package workflow

```sh
python evidence_workflow.py examples/protocol.json
```

Provide a versioned question, criteria, exact search source/query/time/window,
record IDs and paging assertions, reasoned screening decisions, extracted evidence
and gaps. IDs must be normalized by the caller across search sources. Output preserves
search/screening ledgers, reconciles record counts before and after deduplication,
reports pending screening/extraction and creates evidence-linked work packages with
deliverables and acceptance criteria. Model, intervention, comparator, endpoint,
result, limitation and mechanism basis are explicit. Intervention evidence alone
does not establish causality. Clinical/development context may be supplied in gap
records; no clinical guideline retrieval or recommendation is performed.

This is an initial record-level ledger, not a complete PRISMA implementation:
report retrieval, study-level reconciliation, appraisal, dependency scheduling and
guideline/development evidence integration remain future work. Coverage assertions
are not independently authenticated; census and conclusion readiness stay unestablished.

### Dependency-aware research work

Gaps may include stable `work_package_id`, `depends_on` ID lists and `status`
(`PLANNED`, `IN_PROGRESS`, `COMPLETE`). Output includes a topological execution
order and unfinished dependencies. Unknown IDs, duplicate IDs and cycles fail.
`COMPLETE` requires `artifact_locator`, `acceptance_verified: true` and completed
dependencies. These are operator assertions; the tool does not fetch artifacts
or certify experiment quality. Evidence links remain mandatory.

## Report retrieval and full-text screening

```sh
python prisma_reports.py examples/report-protocol.json
```

Add `reports` with unique `report_id`, included `record_ids`, `retrieval`
(`retrieved`, `not_retrieved`, `pending`) and `decision` (`include`, `exclude`,
`pending`). Retrieved reports require a locator, failures/exclusions require a
reason, and included reports require `study_id`. The JSON output contains report
and study counts, pending work, exclusion counts, a deterministic report ledger and
CSV text. CSV cells beginning with formula characters are escaped. Multiple reports
may share a study ID; each input record maps to at most one report. Unmapped advanced
records remain visible. Report screening and existing extracted evidence/work
packages are separate views: this increment does not automatically revise earlier
extractions when full-text decisions change. It is PRISMA-oriented bookkeeping,
not a complete compliance checker, search backend or scientific review.
