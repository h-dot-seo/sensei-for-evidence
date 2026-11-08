# Record conclusion readiness against a mechanical gate ledger

`readiness_review.py` shows twelve mechanical gates derived from the supplied
records, each with its exact open items and one basis sentence, plus a hash of
that gate ledger. `readiness_intake.py` appends human-authored evidence-sufficiency
and conclusion-readiness assertions bound to that hash through a separate
exact-input import review. Together they are the executable form of the workflow's
step 9: assess evidence sufficiency and conclusion readiness separately, and reopen
targeted gaps explicitly. Neither tool assesses sufficiency, declares readiness,
adjudicates an assertion or changes any statement, review, challenge or work state.

## Gates, sufficiency and readiness are three different things

A **gate** is bookkeeping: it is CLOSED when the supplied items it counts are empty,
OPEN when some remain, and NOT_APPLICABLE when the stage it depends on was not
supplied and another gate carries that stage. Every gate can close while the science
stays unsettled, because closed gates only say that the ledgers have no listed
pending item, not that the evidence answers the question. **Evidence sufficiency**
is a human judgement about whether the recorded evidence can answer the bounded
question. **Conclusion readiness** is a human judgement about whether a bounded
conclusion may be stated now. Both labels are supplied, hash-bound and recorded as
assertions. The mechanical `conclusion_readiness` of every tool in this repository
stays `NOT_READY`; only `readiness_assertions` rows carry a supplied `READY` label,
and every output marks them as supplied assertions bound to a gate snapshot.

## Gate ledger

| Gate | CLOSED when | Open items |
|---|---|---|
| `search_plan_complete` | A plan is declared and no planned search is missing or incomplete | planned search IDs |
| `searches_complete` | Every supplied search has no completion or page issue | `/searches/N` input pointers |
| `screening_complete` | Every distinct supplied record ID has a screening decision | record IDs |
| `reports_resolved` | Reports are supplied and none is pending retrieval, not retrieved or pending full-text assessment; every included report has a result row; every included record maps to a report | report IDs and unmapped record IDs |
| `extraction_recorded` | No report ledger is supplied and no title/abstract-included record lacks a result row | record IDs |
| `cited_results_appraised` | Every result cited by a synthesis statement has a recorded appraisal | result IDs |
| `statements_reviewed_current` | Synthesis statements are supplied and none is pending or stale | statement IDs |
| `results_cited` | Synthesis statements are supplied and every extracted result is cited | result IDs |
| `challenges_recorded` | Every supplied statement has a recorded independent challenge | statement IDs |
| `challenges_resolved` | Challenges are supplied and none has an open material gap, is unresolved or has a stale binding | challenge IDs |
| `contexts_reviewed` | No recorded context is pending review | context IDs |
| `work_complete` | No work package is PLANNED or IN_PROGRESS | work package IDs |

Only three NOT_APPLICABLE cases exist: `search_plan_complete` without a declared
plan, `reports_resolved` without a report ledger, and `extraction_recorded` when a
report ledger is supplied (report-level extraction then belongs to
`reports_resolved`). When synthesis statements are not supplied, the four
statement-dependent gates stay OPEN with empty open items; when challenges are not
supplied, `challenges_resolved` stays OPEN the same way. An absent stage is not a
closed gate. Gates are listed in the order above, and `open_gate_ids`,
`closed_gate_ids` and `not_applicable_gate_ids` keep that order.

`gates_sha256` is the SHA-256 of the canonical gate ledger rows (gate ID, status,
open items, basis). It changes whenever an item opens or closes and is unchanged by
protocol edits that move no gate item, for example a version label or the
limitations text of an already pending statement. Version comparison shows those
other changes; the gate hash deliberately binds the gate snapshot only.

## Supplied readiness assertions

The optional top-level `readiness_assertions` list holds at most 100 rows. Each row
has exactly:

- `assertion_id`, `assessor`, `scope_statement`, `rationale` and `limitations` as
  supplied nonblank text; `assessed_at` as a real YYYY-MM-DD date.
- `evidence_sufficiency`: SUFFICIENT, INSUFFICIENT or UNASSESSED.
- `conclusion_readiness`: READY or NOT_READY.
- `gates_sha256`: the gate-ledger hash the assessor examined, 64 lowercase hex characters.
- `reopening`: null, or exactly one of an existing `work_package_id` or an
  `amendment_note`, with the same shape and rules as independent challenges. It is
  required when `conclusion_readiness` is NOT_READY and `evidence_sufficiency` is
  INSUFFICIENT; a NOT_READY assertion then reopens targeted work explicitly.

The engine derives, per assertion, `source_match_status` (CURRENT_GATES when the
supplied hash equals the current `gates_sha256`, otherwise STALE_GATES),
`current_gates_sha256`, `open_gates_at_assertion` (the open gate IDs recomputed from
the current ledger when the hashes match, otherwise null with
`open_gates_scope: UNKNOWN_STALE_GATES`), `ready_with_open_gates`,
`reopening_status` (OPEN_WORK, RECORDED_COMPLETE, OPEN_AMENDMENT or null) and
`assessment: NOT_PERFORMED`. The ledger lists `current_assertion_ids` and
`stale_assertion_ids`, both null when the section is not supplied.

A READY assertion is permitted while gates are OPEN. A human may close scope
deliberately, for example when an unavailable report or an unfinished secondary
work package lies outside the bounded question. The engine does not refuse this;
it records the open gates at the asserted snapshot beside the assertion and requires
the scope statement and rationale to be nonblank, so the closure is visible and
explained rather than implied. Nothing here promotes the mechanical label.

## Blank drafting and explicit candidate records

The template takes only the protocol; there is no reference document because a
readiness assertion is protocol-wide rather than selected per statement or result.
It binds the current `gates_sha256`, lists the full gate ledger with its open,
closed and not-applicable gates, and leaves every human field null with
`reopening: null`. No blank is interpreted as sufficiency, readiness or review.

The candidate document has exactly `schema_version: 1` and a nonempty
`readiness_assertions` list of at most 100 rows with the exact fields above. Target
preparation fails if a row's `gates_sha256` no longer matches the current ledger,
because an assertion recorded against gates the assessor did not see would bind to
a different open-item set. Regenerate the template and re-examine instead of copying
hashes. New IDs must be unique across the existing ledger and the batch; existing
assertions cannot be replaced or merged.

## Eight-command synthetic readiness rehearsal

Use a new existing `OUTPUT` directory outside this repository. All fixture labels,
scope statements and rationale are fictional software data, not an assessment of
any real evidence base.

```sh
python readiness_intake.py template examples/synthesis-review.json --candidate-output OUTPUT/readiness-draft.json
python readiness_intake.py target examples/synthesis-review.json examples/manual-readiness-candidates.json --output OUTPUT/readiness-target.json
```

Keep the unfinished draft separate. The completed fictional candidate records one
NOT_READY assertion with INSUFFICIENT evidence that reopens the existing
`WP-MECHANISM` work, bound to the current gate hash of the fixture. Copy the
target's review_document to `OUTPUT/readiness-review.json`, retain schema and hash,
and explicitly fill receipt_id, reviewer, reviewed_at, rationale and
`decision: "import_readiness_assertions"`. This separate review records the supplied
row; it is not agreement with the assessment. Use fictional labels only for this
rehearsal.

```sh
python readiness_intake.py assemble examples/synthesis-review.json examples/manual-readiness-candidates.json OUTPUT/readiness-review.json --output OUTPUT/readiness-application.json
python readiness_intake.py verify examples/synthesis-review.json OUTPUT/readiness-application.json --protocol-output OUTPUT/with-readiness.json
python readiness_review.py OUTPUT/with-readiness.json --text
python research_status.py OUTPUT/with-readiness.json --text
python research_bundle.py create OUTPUT/with-readiness.json OUTPUT/research.zip
python research_bundle.py verify OUTPUT/research.zip
```

On the fixture, ten gates are OPEN (the missing planned search, the unscreened
record, five report-stage items, one unappraised cited result, one pending
statement review, one uncited result, two statements without a challenge, the
absent challenge stage, one pending context and two unfinished work packages), one
is CLOSED (`searches_complete`) and one is NOT_APPLICABLE (`extraction_recorded`).
After the import, the assertion is listed as bound to the current gates with
`reopening_status: OPEN_WORK`, research status prints `Open readiness gates: 10` and
`Supplied readiness assertions: current 1, stale 0`, and the bundle summary repeats
both lines. Record flow, report counts, statements, challenges, work packages,
planning and the gate ledger itself are unchanged. Census remains `NOT_ESTABLISHED`
and the mechanical conclusion stays `NOT_READY`.

## Bindings, staleness and downstream views

If any gate item later opens or closes, for example when the pending statement is
reviewed or a new appraisal covers the cited result, the gate hash changes and the
assertion is listed under `stale_assertion_ids` with unknown open gates. Nothing is
renewed automatically; the assessor must re-examine and record a new assertion. The
reopening work keeps its own recorded state; completing it later makes the
assertion stale and changes its reopening status to RECORDED_COMPLETE without
changing the assertion.

`research_status.py` adds a `readiness` summary (stage, counts, open gate IDs,
current and stale assertion IDs) and two text lines without adding review queues.
`review_handoff.py` lists `readiness_review.py` among its detailed views and the
`readiness_intake` route with four parser-help entry points. The synthesis snapshot
carries the gate ledger and assertions beside its statements, the bundle summary
prints the two readiness lines and keeps assertion rows in `protocol.json`, and
version comparison lists added, removed and changed assertions plus, with an
amendment note, gate status transitions by gate ID.

## Replay, preservation and limits

Verification regenerates the entire application against its actual original and
recorded implementation. Unrelated original changes, candidate changes and resealed
output changes fail replay. This is not authentication: consistently reauthored
unsigned labels can replay, and dates are checked for calendar syntax, not
chronology. Keep the original, the detached application and the recorded
implementation together.

Candidate and review inputs are limited to 10 MB; protocols and applications to
50 MB; 100 assertions per batch and per protocol. Strict JSON, exact row schemas and
whole-protocol validation apply. Output is prepared before exclusive creation;
existing entries and observed dangling links are refused. This is not an atomic
path-race defense, and a failed write may leave a partial new file.

No external call, model call, source reading or experimental procedure is
performed. Supplied private text is retained without redaction; keep real inputs
and generated records outside this public repository. Neither a closed gate, a
matching hash nor a recorded READY assertion establishes evidence sufficiency,
scientific acceptance or clinical applicability; the mechanical conclusion
readiness of every output remains `NOT_READY`.
