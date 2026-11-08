# Preserve a selected reviewed work-history segment

Ordinary research bundles retain the current protocol but omit the detached
proposal, completer and reviewer records used to create or complete work.
`work_transition_bundle.py` packages a supplied contiguous segment of those
records with its actual initial and endpoint protocols, then replays it through
the existing intake verifiers. It does not create a new review or perform work.

Only three application kinds are accepted:

- detached_source_work_intake: explicitly reviewed new PLANNED source work.
- detached_evidence_work_intake: explicitly reviewed new PLANNED result-linked work.
- detached_work_completion_intake: one supplied completion with separate review.

Each step must replay from the preceding exact canonical protocol. The final
candidate must equal the supplied endpoint across the whole protocol, including
opaque metadata and JSON scalar types. Object-key order and whitespace do not
matter for this connection, but array order, strings, numeric types and all other
content do. There is no sorting, automatic rebase, deduplication, gap repair,
identity resolution or substitute review. Existing verifier rules remain the
authority, including completion dependencies and refusal to renew COMPLETE work.

## Thirteen-command synthetic work-history rehearsal

Use a new existing `OUTPUT` directory outside the repository. All fixtures,
locators and people below are fictional software examples. First propose a
source-review note explicitly linked to source-main and record-one:

```sh
python source_work_intake.py target examples/result-source-current.json examples/work-segment-source-candidates.json --output OUTPUT/source-target.json
```

Copy the target's review_document to `OUTPUT/source-review.json`, retain schema
and target hash, and explicitly fill receipt_id, reviewer, reviewed_at, rationale
and `decision: "import_source_work"`. Fictional labels are only appropriate for
this rehearsal; real use requires the actual corresponding review.

```sh
python source_work_intake.py assemble examples/result-source-current.json examples/work-segment-source-candidates.json OUTPUT/source-review.json --output OUTPUT/source-application.json
python source_work_intake.py verify examples/result-source-current.json OUTPUT/source-application.json --protocol-output OUTPUT/with-source-work.json
python evidence_work_intake.py target OUTPUT/with-source-work.json examples/work-segment-evidence-candidates.json --output OUTPUT/evidence-target.json
```

Copy this new target's review_document to `OUTPUT/evidence-review.json`, keep its
own schema/hash and fill all human fields with `decision: "import_evidence_work"`.
The proposed result-linked delivery note explicitly depends on the new source
note. It does not inherit verified reading or scientific acceptance from that link.

```sh
python evidence_work_intake.py assemble OUTPUT/with-source-work.json examples/work-segment-evidence-candidates.json OUTPUT/evidence-review.json --output OUTPUT/evidence-application.json
python evidence_work_intake.py verify OUTPUT/with-source-work.json OUTPUT/evidence-application.json --protocol-output OUTPUT/with-evidence-work.json
python work_completion_intake.py target OUTPUT/with-evidence-work.json examples/work-segment-completion.json --output OUTPUT/completion-target.json
```

Copy this third target's review_document to `OUTPUT/completion-review.json`, keep
its own schema/hash and fill all human fields with
`decision: "record_supplied_completion"`. This records the fictional source note's
completion assertion, not document authenticity, actual reading or search
completeness. Neither earlier review can substitute for this review.

```sh
python work_completion_intake.py assemble OUTPUT/with-evidence-work.json examples/work-segment-completion.json OUTPUT/completion-review.json --output OUTPUT/completion-application.json
python work_completion_intake.py verify OUTPUT/with-evidence-work.json OUTPUT/completion-application.json --protocol-output OUTPUT/completed.json
python work_transition_bundle.py create examples/result-source-current.json OUTPUT/completed.json OUTPUT/work-transitions.zip --application OUTPUT/source-application.json --application OUTPUT/evidence-application.json --application OUTPUT/completion-application.json --text
python work_transition_bundle.py verify OUTPUT/work-transitions.zip --text
python work_review.py OUTPUT/completed.json --work-package WP-RESULT-DELIVERY-NOTE --include-prerequisites --brief
python prisma_audit.py OUTPUT/completed.json --text
```

The source intake grows two tasks to three, the evidence intake grows three to
four, and completion keeps four tasks while marking only WP-DOCUMENT-TRACE-NOTE
COMPLETE. WP-RESULT-DELIVERY-NOTE becomes mechanically unblocked but stays PLANNED.
All four existing result rows, report accounting and old tasks remain unchanged.
The result task retains its explicit direct-dependency document context; this is
not a recursive source-approval chain. Artifact bytes are not checked and criteria
are not independently assessed. Census remains NOT_ESTABLISHED and conclusions
NOT_READY, including after successful archive verification.

## What travels in the archive

The ZIP contains only generated regular-file paths:

- protocols/initial.json and protocols/endpoint.json: exact supplied bytes.
- applications/step-000000.json onward: exact application bytes in explicit order.
- chain.json: raw/canonical hashes, receipt identifiers, replay results and the
  explicit work IDs selected by each proposal/completion step.
- summary.txt and manifest.json: bounded claims, generated file inventory and
  implementation fingerprints.

Explicit step IDs name the new proposals or selected completion target, not every
indirect effect. For example, completing the source note can unblock the result
note without that result note becoming an explicit completion target. The complete
original application retains its derived-blocking change records, proposal and
completion metadata, reviewer assertions, snapshots and source/locator bindings.

Operator input filenames and current host paths are not added. Supplied text may
already contain sensitive locators or identities; those remain verbatim. No
artifact bytes, native citation files, original source documents, external files,
code or credentials are added. Save the separately recorded implementation needed
to replay the archive. Embedded code is not accepted or loaded. The archive can
be renamed or moved without needing the original operator file paths.

## Historical context, not current approval

A retained source/result snapshot and completion hash apply to their recorded
step context. Verification does not renew them for a later changed document,
result, criterion or protocol. A later source amendment can stale a completed
work's binding without changing its COMPLETE label; the older archive can still
verify as a consistent historical segment. Substituting that changed endpoint
into the original segment fails exact matching. No source, appraisal, synthesis,
clinical context or project decision receives a new human assessment.

Stale or unbound completions already present in the initial protocol remain
untouched. The original engine can treat their COMPLETE statuses as satisfied
dependencies; archive verification does not convert these cues into recursive
acceptance certificates. It recomputes mechanical consistency, not the truth or
adequacy of supplied completion, priorities or deliverables.

A valid prefix or suffix can be packaged by supplying its actual starting input
and endpoint. This does not prove that omitted earlier/later work never happened.
Reordered, omitted or duplicate applications fail when they break exact replay;
the format cannot discover unrecorded or consistently reauthored history.
Unsigned metadata does not authenticate proposal authors, completers, reviewers,
chronology, globally unique receipt IDs or execution.

## Verification and limits

Verification rejects unknown application kinds and runs only the fixed existing
source-work, evidence-work and completion verifiers. Implementation fingerprints
cover their engine files and directly used helpers, including strict JSON and
exclusive-output helpers. New implementation bytes require the matching recorded
implementation rather than a silent replay upgrade.

The entire archive is regenerated and compared byte-for-byte, not merely checked
against editable hashes. Generated ZIP order, regular-file metadata and stored
compression are fixed. Duplicate/unexpected/traversal paths, embedded code,
symlinks, encryption, compressed entries, altered metadata, malformed JSON, bad
CRC, mismatched payloads and changed chain/summary assertions are rejected.
Canonical byte-identical repacking is accepted; changed ZIP bytes invalidate this
byte receipt. No extraction, network call or locator traversal is performed.

Limits are 1–20 supplied steps and 50 MB for the stored archive and retained
payload total. Existing per-intake limits still apply. This is not a hard CPU or
memory ceiling. Outputs are serialized before exclusive creation; existing
entries and observed dangling links are refused. This is not an atomic path-race
or ancestor-alias defense, and a failed write can leave a partial new output.

Collection, screening, report/retrieval, source-declaration, descriptive inventory,
result/correction and condition transitions are not supported steps. Use separate
[report-transition](REPORT_TRANSITION_BUNDLES.md) or
[extraction-transition](EXTRACTION_TRANSITION_BUNDLES.md) segments where applicable;
these formats do not together establish complete project history. A work segment
can begin after an actual extraction endpoint, but does not package that earlier
extraction history automatically. No completeness, PRISMA compliance, scientific
acceptance, clinical applicability or development readiness is established.
