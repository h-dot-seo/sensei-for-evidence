# Bounded optional PubMed identifier discovery

`pubmed_discovery.py` adds an explicit, keyless ESearch path to the supplied-data
workflow. **ESearch returns PMID identifiers, not abstracts, full text or extracted
evidence.** Preview, replay, verification and intake conversion stay offline.
Only the separately invoked, preview-bound `fetch` command contacts NCBI.

A small bounded run can be useful for finding candidate records while keeping its
limits inspectable. It is not a database census, authenticated source snapshot,
query-quality assessment, eligibility decision or completed literature review.
The existing mock adapter and read-only search manifest are unchanged.

## Offline synthetic discovery-to-screening preparation

The supplied specification and response fixture are entirely fictional. The native
response bodies are synthetic software test data, not retrieved citations. Use new
paths in an existing `OUTPUT` directory outside this public checkout:

```sh
python pubmed_discovery.py preview examples/pubmed-discovery-spec.json --output OUTPUT/pubmed-preview.json
python pubmed_discovery.py from-responses examples/pubmed-discovery-spec.json examples/pubmed-discovery-execution.json --output OUTPUT/pubmed-discovery.json
python pubmed_discovery.py verify OUTPUT/pubmed-discovery.json
python pubmed_discovery.py to-intake OUTPUT/pubmed-discovery.json examples/pubmed-discovery-base.json --search-id discovery-primary --output OUTPUT/pubmed-intake.json
python bibliographic_review.py template OUTPUT/pubmed-intake.json --review-output OUTPUT/pubmed-choices.json --text
```

The resulting CSV intake is **unreviewed derived identifier data**, not an NBIB/RIS
export or fetched bibliography. Read its provenance and the retained native response
wrapper before choosing each row's identity or withholding decision through the
[existing bibliographic review](BIBLIOGRAPHIC_REVIEW.md) path. Even repeated exact
PMIDs remain separate occurrences; no `same_record` choice is made automatically.
Withholding a collection row is not a title/abstract screening exclusion.

After explicitly filling the choices, keep the choices document's review null and
prepare a separate collection target:

```sh
python bibliographic_review.py target examples/pubmed-discovery-base.json OUTPUT/pubmed-intake.json OUTPUT/pubmed-choices.json --review-output OUTPUT/pubmed-collection-review.json --text
```

Inspect that exact target and fill its actual reviewer, date, rationale and
`import_for_screening` decision before using the existing assemble command. This
page does not supply human decisions or claim that an unreviewed identifier list
has already entered research. Any imported search remains incomplete under the
existing intake rules. No screening, report, study, abstract or result is inferred.

## Explicit live execution

Create your own specification outside the repository and inspect its preview.
The preview exposes the exact parameters to be sent, including the fixed HTTPS
endpoint and descending publication-date sort. Sorting determines which IDs enter
a capped run; it is not a scientific relevance ranking.

The live command requires the **actual hash returned by the matching preview**:

```text
python pubmed_discovery.py fetch YOUR_SPEC.json --preview-sha256 ACTUAL_PREVIEW_HASH --output NEW_DISCOVERY.json
```

This command transmits the query and declared ESearch parameters to NCBI. Do not
include personal, confidential or otherwise restricted information without
permission to transmit it there. A source's access and usage conditions still
apply. The local tool does not obtain authorization on an agent's or institution's
behalf. No credential, API key, email, cookie, authentication, CAPTCHA handling or
paid service is used. The protocol, original documents and unrelated project fields
are not sent merely because the discovery artifact is later converted to intake.

Do not copy the illustrative placeholder hash or interpret a matching hash as
scientific approval. Changing the specification requires a fresh preview. Existing
output paths are refused; keep successful and partial runs separately rather than
silently replacing earlier observations. A failed output write may leave a partial
new file and does not prove the network request failed.

## Request scope and limits

The standalone request keeps the exact query text and explicit run limits: 1–100
IDs per page, 1–1,000 requested occurrences and 1–10 requests. Each native body is
limited to 65,536 bytes; discovery JSON is limited to 20 MB. The preview records
10-second request and 60-second overall checkpoints and one-second request spacing.
These conservative caps can stop before all reported matches are observed. Optional
date parameters are explicit, paired full dates with a selected NCBI date type;
there is no free-text date interpretation, synonym expansion, query repair,
automatic partitioning or spell correction. Unknown fields and unsupported options
are rejected rather than silently sent or ignored.

The client restricts the destination to the fixed HTTPS ESearch endpoint and uses
ordinary certificate validation. It does not follow redirects, authenticate, retry,
acquire keys, switch providers or work around rate/access failures. Per-request,
elapsed checkpoints, response-byte, request-count and record-count bounds apply.
Time limits are socket/checkpoint safeguards, not hard wall-clock guarantees: DNS,
TLS, response headers, chunk headers, a blocking read and operating-system scheduling
may delay returning control. Its per-process
throttle is below NCBI's anonymous ceiling, but cannot guarantee aggregate compliance
when other tools share the same IP. Coordinate concurrent clients yourself.

NCBI's PubMed ESearch limit is 10,000 returned IDs: both retmax and retstart+retmax
must stay within it. Smaller local caps are intentional and do not extend that
boundary. A large reported count is not permission to bypass it by unreviewed query
splitting. A new scoped query requires an explicit specification and its own record.

## Raw observations and partial results

Every recorded attempt retains its supplied parameters, time, HTTP/transport
observation and bounded native body bytes where available. Complete bytes and
incomplete/truncated bodies are distinguished. Binary/non-JSON failures are retained
as bounded observations rather than decoded into plausible citations. Cookies and
authentication headers are not archived. Recorded attempt metadata is unsigned;
offline replay cannot establish that a network request actually occurred.

The supported JSON subset checks decimal-string count/offset/returned-size fields,
ordered positive-ASCII PMID strings and query translation. The full native body
retains unknown fields. Provider errors/warnings, malformed/duplicate-key JSON,
unexpected offsets, short/empty nonterminal pages, overlong lists, changing counts
or translations and repeated page IDs remain diagnostic. A warning is not silently
converted into adequate query interpretation.

Error-only execution is not a valid zero-hit search and cannot produce a normal
identifier intake. Valid zero-result responses remain distinguishable from missing,
failed or capped observations and stay in the fully traceable native discovery
artifact. Conversion requires at least one candidate occurrence: a header-only CSV
has no supported place for row-level discovery provenance, so zero-hit conversion
is refused without inventing a candidate. Prior usable pages are retained when a later request
fails or a bound stops the run. Repeated identifiers are never silently removed.

Accounting for a provider-reported count does not authenticate its total, prove a
stable index snapshot or establish completeness. Publication-date filtering does
not prevent indexing changes during pagination. Query translation itself is a
recorded provider assertion, not proof the intended question was searched correctly.
Census stays NOT_ESTABLISHED, search completeness unestablished and conclusions NOT_READY.

## Separate plan association and conversion

Conversion is an explicit later step, not a plan amendment. It requires the selected
existing plan to match the source and verbatim query and a supported exact window
representation. `query_defined` declares that the literal term is the entire search,
including any intended date restriction; an unrestricted term is allowed if intentional.
For explicit separate dates, the window uses `datetype:YYYY/MM/DD..YYYY/MM/DD`.
Arbitrary window text or extra unimplemented filters are rejected, never rewritten.
This is format compatibility, not scientific/search-plan approval.

The minimal CSV retains identifier conventions and discovery/response provenance
references. PubMed URL conventions do not verify identity or source content. The
existing core validates and preserves the CSV, not the actual NCBI execution. Keep
the discovery wrapper, original specification, actual base protocol and recorded
implementation for separate offline verification. Ordinary research bundles do not
independently replay the native discovery wrapper.

## Verification and security boundary

Artifact verification reconstructs the recorded transformation without making a
fresh search. Tampered inputs, hashes, derived accounting or implementation bytes
are rejected. Consistently rewritten unsigned records can still replay: matching
bytes are not authentication, human review or proof of retrieval.

The tests and documented rehearsal use synthetic transports only. They do not
validate current NCBI behavior, search adequacy or scientific findings. Real queries
and returned data belong outside the public repository. The optional transport
expands only identifier discovery; it does not retrieve papers, appraise evidence,
produce mechanisms or infer clinical/development decisions.

Official references:

- [Current ESearch parameters](https://www.ncbi.nlm.nih.gov/books/NBK25499/)
- [Annotated returned UID counts](https://www.ncbi.nlm.nih.gov/books/NBK25500/)
- [PubMed's 10,000-ID boundary](https://ncbiinsights.ncbi.nlm.nih.gov/2021/10/05/updated-pubmed-api/)
- [Anonymous request-rate guidance](https://eutilities.github.io/site/API_Key/usageandkey/)
- [PubMed date semantics](https://pubmed.ncbi.nlm.nih.gov/help/#searching-by-date)
- [NCBI HTTPS guidance](https://www.ncbi.nlm.nih.gov/home/develop/https-guidance/)

The Books references were checked through indexed official excerpts when direct
reading encountered a browser challenge. No real ESearch query was used for this
implementation's verification. Returned-size semantics have official XML examples;
the supported modern JSON checks remain a conservative, offline-tested subset.
