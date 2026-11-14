# Authored challenge and readiness shapes

These four descriptive JSON shapes help check a **completed supplied document**
before its existing target, separate import review, assembly and exact replay.
They neither supply judgments nor replace the authoritative Python validators.
An incomplete candidate template or blank target review is deliberately invalid.
A passed shape check is not approval, verified identity, independent human review,
scientific adequacy, permission to record, or evidence that a conclusion is ready.

| Completed document | Schema | Authoritative structural validator |
| --- | --- | --- |
| Challenge candidates | `schemas/challenge-candidates.schema.json` | `challenge_intake.validate_candidate_document` |
| Challenge import review | `schemas/challenge-review.schema.json` | `challenge_intake.validate_review_document` |
| Readiness candidates | `schemas/readiness-candidates.schema.json` | `readiness_intake.validate_candidate_document` |
| Readiness import review | `schemas/readiness-review.schema.json` | `readiness_intake.validate_review_document` |

## Scope and deliberate limits

The existing bounded subset checker is unchanged. Exact property sets, required
fields, enums, row bounds (1..100), unique selected statement IDs, findings and
nullable/exactly-one-key reopening shapes are described. Optional challenge origin
remains absent or an exact HUMAN_AUTHORED / INTERPRETIVE_SIMULATION declaration.
Explicit null origin is invalid. HUMAN_AUTHORED requires null metadata; simulation
may supply nullable hashes/provenance. Neither is authenticated authorship, actual
independence or a real scholar's view. No origin or readiness policy is added.
READY remains a supplied label and can coexist with open gates; mechanical
conclusion readiness remains NOT_READY. A schema never closes a gate or starts
reopening work. Origin/reopening consistency in a real protocol belongs to Python.

Known differences are tested and are **not equivalence claims**:

- nonblank Unicode text, real calendar dates and duplicate row IDs remain Python
  checks; `minLength: 1` does not reject whitespace-only text;
- provenance's 128-character limit and C0/DEL control-character rejection are not
  represented by the unchanged checker subset; Python still enforces both;
- integer-valued JSON `1.0` can match the shape while Python requires integer `1`;
- the audited ASCII date/hash patterns use `$`, which can match before a final
  newline; Python's full-match/date checks reject that case;
- existing statement, evidence, work and gate references, challenger-label checks,
  stale basis/gate hashes and exact detached review targets require the original
  protocol and existing target/assemble/verify workflow;
- shape checks do not authenticate people, source bytes, declared package hashes,
  chronology or supplied scientific judgments. A structurally valid review for a
  different target must still be rejected by assembly.

Schemas do not cover complete protocols or generated application records. Never
insert `$schema` into authored records: it changes exact keys and hash bindings.
Select a schema by CLI argument or editor association instead. The repository's
license status is unchanged; this is not a new reuse license or external contract.
No root product module, ENGINE entry, existing example, review or fixture target
is modified for these descriptive files.

## Two separate fictional journeys

Run at the repository root; replace OUTPUT with one existing empty working
folder. All inputs here are fictional examples. They do not authorize real
research decisions. Preserve the original protocol and every supplied file.

First validate and bind the supplied challenge candidates:

```sh
python schema_check.py check schemas/challenge-candidates.schema.json examples/manual-challenge-candidates.json
python challenge_intake.py target examples/synthesis-review.json examples/manual-challenge-candidates.json --output OUTPUT/challenge-target.json
```

Stop and inspect that exact target. A separate operator must complete its
`review_document` and save OUTPUT/challenge-review.json, including the target hash,
receipt ID, reviewer label, date, rationale and `import_challenges` decision.
The target's null fields are not an authorization. Nothing here generates that
review or attests to a human having reviewed it. Only after the review is supplied:

```sh
python schema_check.py check schemas/challenge-review.schema.json OUTPUT/challenge-review.json
python challenge_intake.py assemble examples/synthesis-review.json examples/manual-challenge-candidates.json OUTPUT/challenge-review.json --output OUTPUT/challenge-application.json
python challenge_intake.py verify examples/synthesis-review.json OUTPUT/challenge-application.json --protocol-output OUTPUT/challenge-protocol.json
python research_status.py OUTPUT/challenge-protocol.json --text
```

The readiness journey independently starts from the same original example,
not from the challenge-enriched result. Its recorded gate hash belongs to that
original input; do not copy it into changed research or silently renew it.

```sh
python schema_check.py check schemas/readiness-candidates.schema.json examples/manual-readiness-candidates.json
python readiness_intake.py target examples/synthesis-review.json examples/manual-readiness-candidates.json --output OUTPUT/readiness-target.json
```

Inspect the exact readiness target and separately supply OUTPUT/readiness-review.json
from its `review_document`, with `import_readiness_assertions` and explicitly
supplied receipt ID, reviewer, date and rationale. The import decision only records
the supplied assertion. It does not endorse it or make the conclusion ready.

```sh
python schema_check.py check schemas/readiness-review.schema.json OUTPUT/readiness-review.json
python readiness_intake.py assemble examples/synthesis-review.json examples/manual-readiness-candidates.json OUTPUT/readiness-review.json --output OUTPUT/readiness-application.json
python readiness_intake.py verify examples/synthesis-review.json OUTPUT/readiness-application.json --protocol-output OUTPUT/readiness-protocol.json
python research_status.py OUTPUT/readiness-protocol.json --text
```

The synthetic walkthrough test supplies fictional reviews explicitly; it does not
represent actual human review. Existing exclusive output, exact original input,
negative checks and replay rules remain authoritative.
