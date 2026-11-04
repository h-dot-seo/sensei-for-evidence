# Compare supplied appraisal context after later edits

`appraisal_source_review.py` compares an exactly replayed appraisal import with a
later valid protocol. It is read-only and never labels an appraisal scientifically
current, invalid, accepted or reassessed. The original import review is retained,
not refreshed. Matching unsigned assertions do not authenticate their authors.

After the synthetic [appraisal intake rehearsal](MANUAL_APPRAISAL_INTAKE.md), run:

```sh
python appraisal_source_review.py examples/synthesis-review.json OUTPUT/appraisal-application.json OUTPUT/with-appraisals.json --text
python appraisal_source_review.py examples/synthesis-review.json OUTPUT/appraisal-application.json OUTPUT/later-protocol.json --output OUTPUT/appraisal-comparison.json
```

The first command compares the replayed candidate with itself. The second requires
an explicitly supplied later valid snapshot; this tool does not create that file.
Use a new existing output directory outside the repository. Inputs and output
retain supplied text without redaction; keep real data outside this public repo.

## What is compared

Only originally imported appraisal IDs and their originally cited normalized result
IDs are followed, in historical order. For each appraisal the output shows:

- Literal before/after appraisal rows and changed top-level fields, including
  method/domain wording, attribution and result-link additions or removals.
- Raw and normalized before/after results. Raw optional/opaque metadata is retained;
  normalized results follow the existing engine rather than a new equivalence rule.
- Historical and current explicit-ID versus legacy-record-ID origins and pointers.
  A legacy result matches the exact normalized ID, never a fuzzy title or locator.
- The original cited record's search/criteria provenance and mapped report context.
- Separately, the actual matched result's current record/report context, so a moved
  result cannot hide behind the unchanged source context of its original record.

Report comparisons include report decisions, supplied study membership, source
basis and the ordered whole mapped source catalog. They do not select documents
that support an appraisal or demonstrate that a source was read. Search/context
changes can alter a source basis while the result wording remains unchanged.
Array positions are navigation; a pure result/appraisal reorder does not change
literal identity comparisons. Search occurrence order remains part of its source
context and may change that comparison.

Statuses are UNCHANGED, CHANGED, MISSING, ADDED and NOT_PRESENT_EITHER. Absence on
both sides is not evidence of adequate source coverage. Current report/source stage
labels separately expose omitted stages. Missing results are shown only when the
entire supplied current protocol remains valid; dangling references are rejected,
not repaired. New result links are visible in appraisal changed fields but are not
expanded into historical context that was never recorded. Unrelated appraisals and
results are not compared. Linked-result counts are per appraisal/result pair, not
independent findings, unique results or study counts.

## Replay and limits

The original protocol and detached application must replay against the recorded
implementation before any comparison is returned. Current input undergoes the
existing full workflow and report validation. These checks do not establish that
the later protocol descends from that candidate, verify real source bytes, establish
reviewer independence or validate appraisal methods. Consistently reauthored unsigned
assertions can replay. Preserve the original and the recorded implementation.

No scientific judgement, review renewal, PRISMA recount decision, work state,
planning rank or evidence field is written. All outputs explicitly retain
NOT_ASSESSED appraisal validity, NOT_PERFORMED renewed review and NOT_ESTABLISHED
lineage. No network request, model call, source-path resolution or artifact reading
occurs. This detached comparison is not a new durable approval ledger and is not
included in existing specialized transition archives.

Inputs and canonical output are limited to 50 MB each; rendered output is checked
before writing. These are byte bounds, not hard CPU or memory ceilings. JSON is
strict, output creation is exclusive, and existing files or observed dangling
links are refused. Creation is not an atomic ancestor-alias or path-race defense;
a write failure may leave a partial new file.
