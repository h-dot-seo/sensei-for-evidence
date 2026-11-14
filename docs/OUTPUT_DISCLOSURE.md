# Supplied research-output disclosures

Roadmap #44: record what an operator says was disclosed about research outputs.
This is not a repository publication release, a publishing action, permission to
publish, scientific closure or certification. `RELEASED_WITHIN_SCOPE` and `WITHHELD`
are supplied labels only. Mechanical release readiness remains `NOT_RELEASED`, actual
publication performed is false, disclosure assessment is `NOT_PERFORMED`, and the
scientific conclusion remains `NOT_READY` in every disclosure context.

## Existing facts, no new gates

The optional `output_disclosures` protocol list has at most 100 exact records. A new
record names an existing readiness assertion bound to the current gate digest. The
existing gate ledger and exact open-item IDs are reused, not recalculated by a new
policy. A supplied RELEASED label may coexist with NOT_READY/INSUFFICIENT and open
gates; a descriptive queue exposes this but does not reject or promote it. Readiness
and other old records are preserved. Later gate changes make the disclosure STALE_GATES;
no rebinding or label update occurs. Current assertion/context displays are observations
of the supplied current protocol, not the historical record of what someone knew.

`unresolved_issues` is a list of exact `{gate_id,item_id,statement}` objects. Missing
current open pairs and extra/noncurrent named pairs are reported, not judged. `r1`
is not covered by naming `r10`, and the same item in another gate is a different pair.
The statement text, coverage, limitations, assumptions, supplied confidence/relevance
and optional recommendation strength are never scored or inferred. Names must be
supplied, dates must be real ISO dates, and separate import-review fields remain blank
until explicitly authored. A distinct reviewer or authentic human participation is
not established by these editable labels.

`output_disclosure_review.py` reuses `synthesis_review.py` citation links and adds the
matching supplied report-source descriptors. This is linkage, not verified source bytes,
reading, support, citation truth or completeness. Locators remain inert strings.

## Optional explicit attachments

Target, assemble and verify accept the same optional `--artifact-observations FILE`
and `--bundle FILE`. Omitting an attachment at replay does not silently recover it from
the record or skip its check. Keep each original attachment and trusted implementation.

- A saved artifact-review JSON is supplied metadata. Its protocol hash must match the
  **original input before this append**, and its manifest metadata/summary must be
  internally consistent. Its recorded engine dictionary is displayed but neither matched
  to this release nor authenticated. No artifact path is opened. A recorded byte-match
  can survive after the actual file is deleted: this deliberately means only a retained
  observation, never current file existence, acceptance or authenticity. Negative/missing
  observations are descriptive checks, not publication gates. Required locators select
  existing supplied work metadata and never cause a filesystem or network read.
- An optional actual research ZIP is verified with the current canonical verifier.
  Its protocol must equal the original input's normalized JSON. Its manifest and full
  archive byte hashes are recorded. It points to the **pre-disclosure** bundle, not the
  new self-containing output. Different whitespace in an otherwise equivalent input may
  form a separately valid new target, but changes the archive bytes and cannot replay an
  earlier target. A resulting post-disclosure bundle cannot stand in for the original.
  Internal replay/hashes are not source authenticity or a scientific validation.

The canonical protocol records only attachment hashes, not saved observations, archives
or the separate import-review assertion. The detached application retains binding/check
context; it is unsigned. Consistently reauthored unsigned records can replay. Neither the
engine nor a view rechecks files when displaying the protocol's attachment declarations.

## Complete fictional rehearsal

Create a new empty `WORK` directory. All three repository JSON files below are explicitly
fictional. The observation file is synthetic supplied metadata, not a claim that a real
research artifact was inspected. The rehearsal intentionally supplies RELEASED with a
NOT_READY/INSUFFICIENT assertion to show that this is bookkeeping, not a publishing gate.

After target, separately fill `WORK/import-review.json` from its blank review document:
schema_version 1, receipt_id, exact target_sha256, decision `record_supplied_disclosures`,
reviewer, reviewed_at and rationale. The test supplies a fictional reviewer solely for
this rehearsal. No tool completes human fields, approves output or sends anything.

```sh
python output_disclosure_intake.py template examples/output-disclosure-input.json fictional-assertion --output WORK/template.json
python research_bundle.py create examples/output-disclosure-input.json WORK/before.zip
python output_disclosure_intake.py target examples/output-disclosure-input.json examples/manual-output-disclosures.json --artifact-observations examples/output-disclosure-observations.json --bundle WORK/before.zip --output WORK/target.json
python output_disclosure_intake.py assemble examples/output-disclosure-input.json examples/manual-output-disclosures.json WORK/import-review.json --artifact-observations examples/output-disclosure-observations.json --bundle WORK/before.zip --output WORK/application.json
python output_disclosure_intake.py verify examples/output-disclosure-input.json WORK/application.json --artifact-observations examples/output-disclosure-observations.json --bundle WORK/before.zip --protocol-output WORK/disclosed.json
python output_disclosure_review.py WORK/disclosed.json --text
python research_status.py WORK/disclosed.json --text
python compare_runs.py examples/output-disclosure-input.json WORK/disclosed.json --text
python review_handoff.py WORK/disclosed.json --text
python research_bundle.py create WORK/disclosed.json WORK/after.zip
python research_bundle.py verify WORK/after.zip
```

For real supplied work, author your own input/candidates and only explicitly authorized
saved observations. Omit both attachment options where not needed, consistently across
all three steps. Native-Windows secure artifact inspection remains unsupported and
fail-closed; accepting a saved observation here does not relax or bypass that policy.
No live external connection, source reading or publishing command is introduced.

## Compatibility and input/output boundary

Absence adds no run/context field and preserves old CLI output bytes, apart from explicit
implementation-fingerprint changes in views that display them. Existing gates and raw
prefixes stay unchanged. Only fixed fictional walkthrough target fields receive release
maintenance; no real review/source/archive is rewritten or automatically resealed.

Protocol/observation/application JSON inputs are bounded at 50,000,000 bytes; candidate
and review inputs at 10,000,000. Bundles use the existing inclusive payload+732 header
bound. These serialized-size limits are not total CPU/memory safety guarantees. Strict
JSON rejects duplicate keys and nonfinite numbers. Outputs create exclusively, but are
not an ancestor-path security boundary or a multi-file transaction: an earlier output
may remain when a later output fails. Caught input/output errors use exit 1, fixed stderr
and empty stdout. Stored attachment and reviewer metadata are not authenticated.

## Legacy validator remains separate

`validate_run.py` retains its legacy agent-state schema and its different COMPLETE
constraints. It is not invoked by this disclosure workflow. The current quick start
already uses protocol scaffolding rather than legacy state. No adapter derives legacy
phase/gate/next_action from protocols, and no supplied readiness assertion is promoted
into a legacy machine decision. Removal or a new policy is outside this change.
