# Continue imported bibliography into supplied assertions

Roadmap #42 reader obstacle (4) identified a real integration defect: after a valid
CSV/NBIB/RIS import, even adding `challenges: []` or `readiness_assertions: []`
failed the bibliographic immutable-context check. These two existing research
ledgers were missing from the enrichment allowance. This release adds exactly
those names, not arbitrary fields, and introduces no new ledger or CLI.

All challenge/readiness shapes, source/gate bindings, independent-label checks,
required reopening declarations, stale-target rejection and separate import review
remain governed by the existing validators. Empty supplied stages are not accepted
scientific judgments. Recording READY would remain a supplied assertion alongside
open gates, never mechanical readiness. Existing gate/closure policies are unchanged.
Question, criteria, plan and unknown root-field changes remain immutable-context
errors. Bibliographic import history and raw source/identity assertions are retained.
Mock-adapter/bibliographic mixing is still forbidden.

Only `bibliographic_integrity.py` changes among ENGINE modules. No challenge,
readiness, source-basis or offline-adapter implementation is changed. Old artifacts
and bundles require their recorded trusted implementation: this is not a migration
or automatic review refresh. Exactly the existing 15 fictional fixture target hashes
are maintained, preserving all other bytes and all supplied review facts. No real
user data, human review or original source is rewritten.

## Existing end-to-end routes

Start with a valid currently supported collection and your explicitly supplied
results/statements: [CSV collection](BIBLIOGRAPHIC_INTAKE.md),
[NBIB](PUBMED_NBIB_INTAKE.md), or [RIS](RIS_INTAKE.md). These formats do not establish
source authenticity, eligibility, result correctness or search completeness. Native
wrappers have their own retained-byte verification; ordinary collection verification
does not silently certify them. Keep the original collection and native records.

The commands below use `COLLECTED_PROTOCOL.json`, explicit
`CHALLENGE_REFERENCES.json` selecting existing statement IDs, and separately authored
`SUPPLIED_CHALLENGES.json`. The blank template is not a completed challenge.

```sh
python challenge_intake.py template COLLECTED_PROTOCOL.json CHALLENGE_REFERENCES.json --candidate-output challenge-blank.json
python challenge_intake.py target COLLECTED_PROTOCOL.json SUPPLIED_CHALLENGES.json --output challenge-target.json
```

A person inspects the target and supplies its separate review document as
`CHALLENGE_IMPORT_REVIEW.json`. No existing assertion is renewed by this operation.

```sh
python challenge_intake.py assemble COLLECTED_PROTOCOL.json SUPPLIED_CHALLENGES.json CHALLENGE_IMPORT_REVIEW.json --output challenge-application.json
python challenge_intake.py verify COLLECTED_PROTOCOL.json challenge-application.json --protocol-output challenged-protocol.json
python readiness_intake.py template challenged-protocol.json --candidate-output readiness-blank.json
```

After inspecting open gates and the bounded research, a person authors
`SUPPLIED_READINESS.json`. Its assertions and any required reopening note are human
inputs, not generated scientific conclusions. Keep the target digest supplied by
the current template only for that exact reviewed input.

```sh
python readiness_intake.py target challenged-protocol.json SUPPLIED_READINESS.json --output readiness-target.json
```

A separate supplied import review is saved as `READINESS_IMPORT_REVIEW.json`.

```sh
python readiness_intake.py assemble challenged-protocol.json SUPPLIED_READINESS.json READINESS_IMPORT_REVIEW.json --output readiness-application.json
python readiness_intake.py verify challenged-protocol.json readiness-application.json --protocol-output asserted-protocol.json
python research_status.py asserted-protocol.json --text
python readiness_review.py asserted-protocol.json --text
python research_bundle.py create asserted-protocol.json asserted-bundle.zip
python research_bundle.py verify asserted-bundle.zip
```

These are existing commands with existing output, exclusive-creation and error
contracts. No additional permissions, source connection or model call is introduced.
Retain before/after protocol inputs and detached review records; file existence alone
is not proof that verification succeeded.

## Synthetic verification boundary

The regression executes real CSV/NBIB/RIS preparation and explicit collection review,
then these twelve CLI commands for each format with fictional authored inputs. It
also covers empty and invalid ledgers, immutable/unknown fields, stale and tampered
records, origin declarations and optional evidence-basis labels. Its plain-protocol
comparison is a separate synthetic control: removing bibliography provenance changes
existing statement source bases, so that control's fictional challenge is bound to
its own current source before comparing gate semantics. No source hash is dropped
or rewritten in the actual imported protocol or retained application.
