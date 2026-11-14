# Inspect protocol root field names

A misspelled optional field can be treated as absent by a general protocol tool.
For example, renaming `appraisals` to `apraisals` does not make it an appraisal ledger.
This separate read-only view makes names outside the checkout's declared inventory
visible without guessing corrections, inspecting values or changing the protocol.

```sh
python protocol_keys.py list
python protocol_keys.py inspect examples/review-demo.json
python protocol_keys.py inspect examples/review-demo.json --text
```

`list` emits the26 declared protocol-root field names in this release. `inspect`
emits sorted `recognized_top_level_keys` and `unrecognized_top_level_keys` only, plus
fixed scope/boundary and checker implementation hashes. There is no input digest,
value preview, nested-key walk, field suggestion or research validation. JSON is
ASCII-escaped; text visibly quotes control/format characters in supplied names.
Unknown names do not cause a nonzero exit. Empty objects and null-valued known fields
can still be inventoried: that does not make them valid research protocols.

For your own file, run `python protocol_keys.py inspect PATH/TO/PROTOCOL.json`.
If you see `apraisals`, examine the original input and relevant [field guide](USAGE.md)
yourself. The tool neither knows that a name is a typo nor recommends renaming it.
Custom metadata and future fields can also be outside this checkout's inventory.
Generic comparison/hashing may still retain them even though no declared field
semantics are recorded here. No input is dropped or rejected because a name is unknown.

## Scope and safety

- The caller chooses a protocol-root object. This is not a candidate, review,
  detached application, fixture envelope or legacy agent-state schema detector.
- Known means declared somewhere in the current protocol tools, not required,
  accepted in every workflow, correctly populated or scientifically appropriate.
  For a new ledger-free base, use [starting-protocol check](PROTOCOL_SCAFFOLD.md).
- No engine, status, handoff, schema2 snapshot, review target, queue or gate is changed.
  Use existing authoritative Python validators for shape/context/binding checks.
- No output files are written, no research scripts are invoked and no network/model calls
  occur. Success emits stdout only. Missing/unreadable/oversized or malformed strict
  UTF-8 JSON and nonobjects return exit2 with a generic message and no stdout.
  Error diagnostics deliberately omit paths, parser fragments and values.
- Input and serialized report limit50MB; JSON parsing is in memory, so values are
  necessarily decoded but are not semantically inspected, echoed or hashed.
- Names themselves may contain private information. This is not anonymization, and
  a name copied from a sensitive value remains sensitive. Keep real files outside
  the public repository and review any output before sharing.

## Inventory maintenance

The explicit tuple in protocol_keys.py is the inventory, not an automatic schema.
Tests compare it in both directions with named `protocol[...]`, `.get/.pop/.setdefault`
and membership accesses, including finite literal loop/comprehension keys, literal constants and the
explicitly audited handoff section tables. Unresolved
named dynamic accesses fail the drift test. All shipped root protocol examples must
have recognized keys. This is not whole-program data-flow analysis: aliases or future
dynamic extensions require manual review. Generic iteration/hash/diff is not a field
semantics declaration. Do not add names merely to silence a reported difference.

The broader detached-record registry and schemas/explain work remain separate.
This view does not promise compatibility, migration or validity of saved records;
verification still needs the recorded implementation.

[Command reference](COMMANDS.md) · [Compatibility](USAGE.md)
