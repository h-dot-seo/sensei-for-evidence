# First offline run: question → receipts → review → evidence → work

Start here before exploring every command. This walkthrough executes only bundled
fictional inputs. It never searches literature, reads a paper, calls an AI, verifies
a clinical guideline or decides scientific validity. Python 3.10+ and the standard
library are sufficient. Run from the repository root.

Create a new empty output directory **outside this repository** yourself. Replace
`OUTPUT` in the commands below with its path. Quote paths containing spaces. The
tests run these exact command blocks with a temporary directory, on supported CI
platforms. All created protocol/ZIP targets must be new; commands refuse overwrite.
Stdout is a report, not a newly saved protocol unless --protocol-output is given.
Real/private research does not belong in the public examples or repository.

## 1. Inspect the declared question and search-entry contract

Read examples/adapter-protocol.json: its question, inclusion/exclusion criteria and
declared primary/secondary searches are supplied text. The example also contains
anticipated fictional screening/report assertions; these are **not** decisions
produced by a search. Before enumeration, this base is an adapter/intake input,
not a complete research protocol for downstream audit commands.

```sh
python receipt_intake.py template examples/adapter-protocol.json
```

Null fields are placeholders needing supplied facts, not zero results. The bundled
adapter-fixture.json is a separately authored mock exchange with enumerated pages,
source locators and proposed result rows. It is not the output of a live provider.

## 2. Assemble unreviewed search/extraction candidates

```sh
python offline_adapter.py examples/adapter-protocol.json examples/adapter-fixture.json --protocol-output OUTPUT/unreviewed.json
python prisma_audit.py OUTPUT/unreviewed.json
```

Expected: two exact record IDs are enumerated, accepted evidence is empty, review
receipts are pending and searches are not marked complete by the adapter. Included
screening/report assertions were supplied in the base; they do not accept proposed
extractions. The secondary planned search remains missing. PRISMA audit counts
records, reports, supplied study IDs and result rows separately.

## 3. Apply the prewritten fictional review decisions

Read examples/adapter-reviews.json before running this command. It records explicit
fictional reviewer decisions bound to the mock receipt hashes. The tool validates
those assertions; it does not perform the review. Do not reuse them with changed
receipts or real literature.

```sh
python offline_adapter.py examples/adapter-protocol.json examples/adapter-fixture.json --reviews examples/adapter-reviews.json --protocol-output OUTPUT/reviewed.json
python prisma_audit.py OUTPUT/reviewed.json
```

Expected: two accepted supplied result rows, one source record with extraction,
one included report and one supplied study. Two results are not two studies.
Source authenticity, complete extraction and census remain unestablished.

## 4. Compare separately authored nonclinical/context/work inputs

examples/first-run-enriched.json starts with that same reviewed protocol and adds
only an explicit version, contexts, appraisals, experimental_units and gaps. These
are hand-authored fictional inputs, **not extraction or recommendations generated
by the adapter**. The comparison exposes exactly those changed sections.

```sh
python compare_runs.py OUTPUT/reviewed.json examples/first-run-enriched.json
python work_review.py examples/first-run-enriched.json --work-package WP-TRANSLATION --include-prerequisites --brief
```

The four-WP chain is receipt review → extraction review → mechanism uncertainty
review → translation review. Each has supplied deliverables/acceptance criteria.
Nonclinical condition metadata retains unknown observation timing and causal
limitations; no experimental procedure is run. Guideline population/applicability
and development-stage/regulatory assertions remain separate and unverified.
Missing appraisal and source gaps remain visible. No planning rank is invented.
Use --text instead of --brief to inspect the complete joined packets.

## 5. See what a completed work assertion actually changes

examples/first-run-note-complete.json differs only in version and the receipt-note
WP: status COMPLETE, a fictional artifact_locator and acceptance_verified: true.
These are prewritten assertions. No note is created, opened or accepted by this
command. The unchanged completion guard requires a locator, exact true acceptance
and completed prerequisites; this example's first WP has no prerequisites.

```sh
python compare_runs.py examples/first-run-enriched.json examples/first-run-note-complete.json
python work_review.py examples/first-run-note-complete.json --work-package WP-TRANSLATION --include-prerequisites --brief
```

Expected: extraction-review work is no longer blocked by the receipt-note WP.
Mechanism/translation work remains blocked. The secondary search is still missing;
no receipt review, evidence, appraisal or scientific readiness is changed. A locator
is not proof an artifact exists. Optional local byte verification is a separate
POSIX-only [artifact review](LOCAL_ARTIFACT_REVIEW.md), not part of this sequence.

## 6. Preserve and verify the supplied run

```sh
python research_bundle.py create examples/first-run-note-complete.json OUTPUT/first-run.zip
python research_bundle.py verify OUTPUT/first-run.zip
```

The seven-file bundle preserves supplied data and reproducible outputs without
redaction. Verification checks hashes and deterministic regeneration, not truth,
source completeness or scientific acceptance. Keep it local unless sharing has
been authorized. Final bounds remain NOT_ESTABLISHED and NOT_READY.

## When a command stops

- Target already exists: use a different new output path. Do not delete real work
  or overwrite a protocol just to rerun this exercise.
- Changed fixture/review hash: reconcile the source and obtain a new explicit human
  review; never edit a hash simply to bypass the gate.
- Invalid source/result/context/work reference: fix the supplied reference and
  inspect its scope. Do not invent evidence IDs to satisfy a task.
- COMPLETE without locator/acceptance/prerequisites: retain unfinished status until
  the actual completion assertions can be honestly supplied.
- Valid report with missing searches or unresolved review cues: this is expected in
  the example, not certification of census or permission to draw a conclusion.

After this rehearsal, use [operator handoff](OPERATOR_HANDOFF.md) to navigate the
existing tools and [manual receipt intake](RECEIPT_INTAKE.md) for entry checks.
Actual source access, screening/extraction, appraisal, hypotheses, decisions and
acceptance remain authorized human research work outside this mock walkthrough.
