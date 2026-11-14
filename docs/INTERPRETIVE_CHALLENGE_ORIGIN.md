# Declared origin of interpretive challenges

An origin is a **supplied declaration**, not authentication. HUMAN_AUTHORED does
not establish that a human wrote or reviewed a challenge. INTERPRETIVE_SIMULATION
is neither the simulated scholar's view nor new empirical evidence. An absent
origin is UNDECLARED, never inferred human authorship. Package and consultation
hashes are DECLARED_NOT_VERIFIED: no file, source, model or network is accessed.

This implements roadmap #100's adjusted optional-field route, not its separate
suggested gate policy. Operators still supply every challenge statement, outcome,
reopening reference and exact-target recording review. No challenge, review,
scientific judgment, consensus, independence or closure decision is generated.

## Optional schema 1 field

Candidate documents remain schema_version 1. Existing rows are not rewritten or
upgraded. The existing null template remains unchanged and does not insert origin.
If the operator chooses to declare origin, add exactly this object to that row:

```json
{
  "kind": "INTERPRETIVE_SIMULATION",
  "package_sha256": null,
  "consultation_record_sha256": null,
  "declared_provenance": null
}
```

`kind` is HUMAN_AUTHORED or INTERPRETIVE_SIMULATION. Both hash fields must be null
or exactly 64 lowercase hexadecimal characters. The consultation hash may be the
operator-supplied canonical payload hash of an adopted Persona answer or argument-map
envelope. It is separate from the package hash. Matching digest syntax proves none
of the provenance, authorship, source authenticity or interpretation.

`declared_provenance` is null or exactly these five fields: provider_id, model_id,
run_id, operator_id, execution_location. All values are nonblank strings of at most
128 characters, with C0 controls and DEL forbidden. execution_location must be local,
remote or unknown. This matches the current Persona declared-provenance contract;
the repositories do not import or execute each other and no cross-repository
version negotiation or live integration is claimed. Use public fictional labels in
public fixtures, never private author identifiers or personal persona packages.

A HUMAN_AUTHORED declaration must have both hashes and provenance explicitly null.
This is consistency of the declaration, not evidence of human authorship. A simulated
challenge may have null metadata when none is supplied; the tool does not invent it.
An explicitly supplied null origin, empty object, extra field or invalid value is
rejected rather than treated as omission. No operator-label cue is implemented.

## What changes and what does not

The normalized challenge ledger derives origin_kind for every row. Missing origin
produces UNDECLARED only in that derived view; the raw protocol and candidate stay
unchanged. When at least one origin is declared, statement links additionally list
human_challenge_ids, interpretive_challenge_ids and undeclared_challenge_ids, and the
view includes statements_with_only_interpretive_challenges. That queue requires a
nonempty challenge set all explicitly labeled INTERPRETIVE_SIMULATION. A human or
undeclared row prevents that classification; its presence is not proof of review.
Stale/unresolved rows are not hidden or renewed by origin labels. The usual source
and outcome queues remain separate and unchanged.

Status adds the optional queue/count/text only when a declaration is present;
handoff uses the same statement IDs and literal source rows. Synthesis and comparison
already carry whole challenge rows, so origin becomes visible without changing those
implementations. Comparison correctly reports supplied origin as a raw field change.
The bundle summary adds an origin cue only when declared. No declared origin means
no optional queue, split or summary line. The derived UNDECLARED per-row label is an
intentional new display field, not a gate or signature verdict.

**readiness_links.py is unchanged**, including its basis sentences and gate rules.
Exactly the same challenge IDs, outcomes and reopening state yield the same gate
rows and gates_sha256 with or without origin. Existing readiness assertions retain
their usual current/stale status. Interpretive MATERIAL_GAP/UNRESOLVED challenges
still follow the existing resolution queues. There is no penalty or automatic
acceptance for a self-declared kind. Any future gating rule requires a separate
explicit decision and is not implemented here.

## Implementation compatibility and synthetic maintenance

The ENGINE files changed are exactly challenge_links.py and research_bundle.py.
Non-engine code changes are challenge_intake.py, research_status.py and
review_handoff.py. The ENGINE_FILES list, offline_adapter.py, allowlists, canonical
screening/report decisions and readiness_links.py are unchanged.

Changing engine bytes changes intake targets, manifests and deterministic archive
bytes even for protocols with no origin. Old applications and bundles must be replayed
with their recorded trusted implementation, not made current by rewriting hashes.
Only the repository's fifteen explicitly synthetic walkthrough target fields are updated
as controlled maintenance. The initial roadmap listed ten fields; five later synthetic import-review fixtures
were found by full-suite failures and explicitly added to this maintenance scope.
No real review, reviewer, decision, date, rationale or
source bytes are changed; no public/automatic hash-refresh command is added.

Regression boundaries are explicit:
- The 43rd increment's original twelve-view baseline JSON file is byte-preserved.
  Its existing named self-fingerprint exclusions remain. The only additional
  substitutions before comparing the entire recorded JSON/text are the exact paths
  `/engine_sha256/challenge_links.py` and `/engine_sha256/research_bundle.py`, from
  current file bytes back to their independently recorded previous values.
  No other field, queue, gate or text line is removed or normalized.
- Four actual preceding-release run baselines bind their exact input and gate digest.
  With no declared origin, removing only each new
  `/challenge/challenge_ledger/<index>/origin_kind` value UNDECLARED recovers the
  entire previous run result. Raw inputs are unchanged.
- Separate comparisons test declared origins while requiring all non-challenge
  engine output, all readiness rows/digests, and every prior status queue/count to
  remain equal. Optional supplied fields are not treated as invisible raw changes.

## Fictional rehearsal

The sample labels name a simulation of fictional-persona-A, not a real scholar.
The 1/2-filled digests are deliberately synthetic declarations, not verified payloads.
Use an empty output directory; commands assume the repository working directory.
The existing INDEPENDENT_CHALLENGE guide and its two blocks/ten commands are unchanged.
This separate guide is exercised as ten actual CLI commands in a temporary directory.

```sh
python challenge_intake.py template examples/synthesis-review.json examples/challenge-references.json --candidate-output origin-blank.json
python challenge_intake.py target examples/synthesis-review.json examples/interpretive-challenge-candidates.json --output origin-target.json
```

Create `origin-review.json` separately from the target's review_document. Supply
receipt_id `fictional-origin-import`, decision `import_challenges`, reviewer
`Fictional import reviewer`, reviewed_at `2026-11-14`, and rationale
`Record fictional origin declarations only`. These are explicit fictional test
choices, not automatic acceptance or recommended decisions for actual research.
Keep the exact target_sha256 unchanged.

```sh
python challenge_intake.py assemble examples/synthesis-review.json examples/interpretive-challenge-candidates.json origin-review.json --output origin-application.json
python challenge_intake.py verify examples/synthesis-review.json origin-application.json --protocol-output origin-protocol.json
python research_status.py origin-protocol.json
python review_handoff.py origin-protocol.json
python synthesis_review.py origin-protocol.json
python compare_runs.py examples/synthesis-review.json origin-protocol.json
python research_bundle.py create origin-protocol.json origin-bundle.zip
python research_bundle.py verify origin-bundle.zip
```

The existing separate import review binds the exact origin fields together with all
other supplied candidate content and the current implementation. Editing a declared
hash after target invalidates that review; it does not merely update a cosmetic label.
Existing strict input, size and exclusive-output contracts remain, including their
existing error channels. Outputs may expose all supplied labels and hashes; they are
not anonymized and real/private inputs must not be published by default. No new
network permission, legal assertion, license decision or release tag is involved.
