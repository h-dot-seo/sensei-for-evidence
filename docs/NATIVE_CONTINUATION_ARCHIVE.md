# Preserve a supplied continuation RIS collection in one typed archive

Select this route only for the explicitly declared continuation dialect. Strict RIS, NBIB and NBIB-batch routes do not guess or accept it under another label. This adds a retained-byte/derivation path, not a new scientific, identity or human-review decision.

Use the shipped fictional inputs below. Replace OUTPUT with an existing empty directory outside the checkout. Nothing overwrites an existing output. No real source or retained review is rewritten, renewed or resealed.

```sh
python ris_continuation_intake.py preview examples/bibliographic-base.json examples/dialects/continuation.ris --dialect ris-untagged-continuation-empty-paragraphs-v1 --search-id local-primary --searched-at 2026-11-04T00:00:00Z --output OUTPUT/continuation.json
python ris_continuation_intake.py verify OUTPUT/continuation.json --intake-output OUTPUT/intake.json
python bibliographic_review.py template OUTPUT/intake.json --review-output OUTPUT/blank-choices.json
```

Stop. A person supplies row-level identity choices and rationale in a separate OUTPUT/manual-choices.json. The template does not choose new_record or infer publication identity. The next command only calculates the target for those supplied choices.

```sh
python bibliographic_review.py target examples/bibliographic-base.json OUTPUT/intake.json OUTPUT/manual-choices.json --review-output OUTPUT/target-review.json
```

Stop again. A person supplies the separate exact-target reviewer, date, rationale and import_for_screening decision in OUTPUT/manual-review.json. The software does not turn a template or target into approval. Then assemble and explicitly bind import index 0 to the continuation wrapper:

```sh
python bibliographic_review.py assemble examples/bibliographic-base.json OUTPUT/intake.json OUTPUT/manual-review.json --protocol-output OUTPUT/collected.json
python native_collection_bundle.py create OUTPUT/collected.json OUTPUT/continuation-collection.zip --ris-continuation 0=OUTPUT/continuation.json
python native_collection_bundle.py verify OUTPUT/continuation-collection.zip
python retained_bundle_describe.py OUTPUT/continuation-collection.zip --text
```

The last command only reads the recorded manifest and reports NOT_PERFORMED verification. It is not an alternative to the preceding verifier. The archive retains exact original RIS bytes under a generated .ris path, the normalized wrapper, explicit CSV-ledger association and unchanged ordinary research ZIP. Duplicate tags/occurrences, BOM and line endings are not removed. No extraction, code loading, network access or source locator opening occurs.

## Explicit compatibility cost

The wrapper and typed native archive remain their existing schema-1 shapes, with an explicit ris_continuation selection added. Same schema version does not promise cross-implementation replay. The typed archive's own implementation map gains the continuation parser/wrapper; the global research ENGINE_FILES set does not change. Updating the wrapper's obsolete unsupported-archive boundary changes that wrapper's own implementation fingerprint even though its CSV derivative and parser are unchanged.

Therefore old typed native archives and old continuation wrappers require their recorded original implementation. Current verifiers continue to reject their differing fingerprints. Do not edit a saved hash, relabel a strict wrapper, rewrite the archive or reuse a human review as if it had been newly issued. The unverified retained descriptor can show recorded/current differences without claiming replay or authenticity. Tests reconstruct actual previous source bytes and verify old artifacts with that source, then confirm current rejection; the product never loads code from an archive.

Existing strict RIS/NBIB wrappers, original native files, ordinary research ZIP and scientific/readiness decisions remain unchanged. Legacy native selections keep their existing format-count keys (no unused zero continuation key), but native archive bytes still change because their implementation map and descriptive boundary change. Handoff's explanatory boundary and self-fingerprint change; its gate/queue/decision calculations do not.

This is not source authentication, human authentication, complete research-history preservation, reference-manager compatibility certification or a scientific conclusion. Existing byte, binding and source-count limits are not raised. Real exports, human choices/reviews and outputs stay outside this public repository.

Historical shared-preflight tests explicitly recreate their former native dispatch/ENGINE/boundary environment to test that earlier extraction without output normalization. They do not claim current archives replay under old hashes. The new current/prior implementation tests independently establish the intentional replay rejection and original-code requirement.
