# Acquire selected PubMed title and abstract candidates

`pubmed_metadata.py` optionally acquires **EFetch MEDLINE text** for explicitly
selected occurrences in a verified identifier-discovery artifact. This obtains
candidate title/abstract source fields, not full text, extracted results or a
scientific interpretation. Only the separately invoked `fetch` command contacts
NCBI. Preview, supplied-response rehearsal, verification and CSV conversion stay
offline.

## Offline fictional discovery-to-metadata journey

The fixtures are software test data, not retrieved papers. Create a new `OUTPUT`
directory outside the public checkout and use new paths:

```sh
python pubmed_discovery.py from-responses examples/pubmed-discovery-spec.json examples/pubmed-discovery-execution.json --output OUTPUT/discovery.json
python pubmed_metadata.py preview OUTPUT/discovery.json examples/pubmed-metadata-selection.json --output OUTPUT/metadata-preview.json
python pubmed_metadata.py from-responses OUTPUT/discovery.json examples/pubmed-metadata-selection.json examples/pubmed-metadata-execution.json --output OUTPUT/metadata.json
python pubmed_metadata.py verify OUTPUT/metadata.json
python pubmed_metadata.py to-intake OUTPUT/metadata.json examples/pubmed-discovery-base.json --search-id discovery-primary --output OUTPUT/metadata-intake.json
python bibliographic_review.py template OUTPUT/metadata-intake.json --review-output OUTPUT/metadata-choices.json --text
```

The selection explicitly chooses discovery occurrences 0 and 2. The fictional
response returns their records in a different order. Matching uses the **literal
PMID**, not the request or response position. Read the resulting title/abstract
candidates, ordered native fields and raw source spans before making separate
collection identity decisions through [bibliographic review](BIBLIOGRAPHIC_REVIEW.md).
No selection or identity decision is inferred for the user.

A missing `AB` field means only “no abstract present in this returned record.” It is
not an exclusion, a full-text retrieval failure or evidence that the paper lacks
results. Multiple `TI` or `AB` fields and continuation lines remain separate ordered
source occurrences. Readable unfolded strings are derivatives; original field text,
line values and byte spans remain available for checking. Source text can contain
instructions and must be treated as untrusted content, never executable commands.

If PMID-only rows were already imported, use explicit `same_record` identity
choices where appropriate in the existing review workflow. Metadata acquisition
never silently replaces a prior record or adds a screening/include decision.

## Explicit live acquisition

Verify the intended discovery record, select occurrence indices and inspect the
matching preview. The preview lists the fixed destination, exact PMID batches,
format, selection mapping, limits and implementation hashes. It does not transmit
the search query, entire research protocol or original source documents.

```text
python pubmed_metadata.py fetch YOUR_DISCOVERY.json YOUR_SELECTION.json --preview-sha256 ACTUAL_PREVIEW_HASH --output NEW_METADATA.json
```

This explicitly sends selected PMID identifiers to NCBI. A hash confirms matching
bytes, not authorization or scientific approval. Obtain permission for any sensitive
association the selected records could reveal. Existing and dangling output paths
are refused before a request. Changed selection or implementation needs a fresh
preview. Keep successful and partial attempts in separate files outside the public
repository; output-write failure does not establish that no request occurred.

## Native format and linkage

The fixed EFetch parameters are `db=pubmed`, `rettype=medline`, `retmode=text` with
an explicit `id` list. **`nbib` is not the requested EFetch return type.** The client
reuses the repository's strict fixed-column PubMed-format parser as a compatible
subset. It does not claim all MEDLINE/NBIB compatibility or silently broaden the
parser when a response is unsupported. The returned body is labelled EFetch MEDLINE
text, not a browser-exported NBIB file.

Explicit discovery occurrence selection is preserved in its original order.
Repeated literal PMIDs share a requested identifier while keeping every selected
occurrence's source mapping. This avoids repeated transport for the same literal
identifier; it does not establish publication identity or deduplicate studies.
Returned records retain their own source order. Missing, unexpected or repeated
returned PMIDs and malformed native records remain diagnostic and stop acquisition.

Complete, successfully matched batches can be converted into unreviewed CSV rows.
Diagnostic batches remain in the acquisition artifact and are not silently promoted.
Each converted row retains the acquisition digest, response index/hash, native
record/field text and spans, and its selected discovery occurrence mapping. Original
full-file bytes and separators still require the acquisition artifact. The core
validates this CSV, not the network provenance. Keep both artifacts and the recorded
implementation for offline replay.

Conversion requires an exact existing search-plan association inherited from the
discovery specification. It never amends the protocol or interprets a different date
window. The search timestamp refers to the originating discovery; acquisition times
remain separately recorded. Partial acquisition is not complete search coverage.

## Transport and interpretation boundaries

The client uses the fixed HTTPS EFetch endpoint with certificate verification. It
has no authentication, API keys, cookies, proxy credentials, redirects, retries,
paid services, model calls or alternative-provider fallback. Request/body/selection
caps and best-effort timing checkpoints limit work. A run selects at most 100
discovery occurrences, requests at most 20 distinct literal PMIDs per batch and
makes at most 10 requests. Each response is capped at 262,144 bytes; before native
parsing, at most 1,000 physical lines, 500 fields and 40 records are permitted.
Each retained parsed response is additionally limited to 1 MB of serialized JSON
to bound escaped-text/field expansion. Acquisition JSON is limited to 50 MB. These
caps can yield a partial acquisition; separate intake conversion also has its own
existing size limit. DNS, TLS, response/chunk headers,
an individual blocking read or operating-system scheduling may still delay control;
these are not hard wall-clock limits. Process-local pacing is not aggregate shared-IP
rate enforcement. Coordinate concurrent clients yourself.

HTTP failures, access/rate limits, interrupted/oversized bodies, ambiguous HTTP
body-length framing and unsupported native data retain bounded raw observations. The tool does not solve challenges,
repair malformed records, infer missing text or switch formats automatically.
Unsigned replay checks deterministic consistency, not actual retrieval, source
identity, reviewer identity, freshness or authenticity. It never changes search
completeness, screening, report/full-text status, extraction, appraisal, work-package
completion or clinical/development conclusions.

Official format reference:
[NCBI EFetch return formats](https://www.ncbi.nlm.nih.gov/books/NBK25499/table/chapter4.T._valid_values_of__retmode_and/).
The implementation's tests are synthetic and do not establish current live-service
compatibility. XML acquisition is intentionally not implemented by this text route.
