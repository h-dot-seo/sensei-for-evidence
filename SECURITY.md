# Security and publication boundary

Keep actual user/research data outside this public repository. The examples are
synthetic and contain no real conversations, participants or researcher corpus.
Do not commit credentials, cookies, profiles, authentication bundles, SSH keys,
private hosts, personal account configuration, logs, original documents or databases.
Encrypted private material is also excluded from this code-only release.

The repository has a new public history; it does not import a private repository's
commit graph, deleted files, branches, tags or Git LFS objects. The publication
manifest enumerates the reviewed files. Review future diffs and staged files, not
only the current working tree. A .gitignore is not a data-loss prevention system.

`audit_publication.py` detects a small set of prohibited file types and common secret
patterns. A pass is not proof of anonymity, copyright clearance or absence of all
secrets. Human review of the actual selected files remains required. It does not
redact source material or turn a private corpus into a safe public release.

Do not disclose a vulnerability containing private information in a public issue.
Use an owner-configured private security channel when available. No contact address
or account-specific reporting endpoint is bundled in this release.

## Optional PubMed requests

The core processing tools remain offline. Only the separately invoked
`pubmed_discovery.py fetch` path contacts the fixed HTTPS NCBI ESearch endpoint,
after an exact preview-hash check. It sends the query and declared request
parameters, not unrelated protocol/source fields. Do not transmit personal or
confidential query content without authorization. No API keys, cookies, account
credentials or payment integration are supported. Redirects/access challenges are
stopping conditions, not invitations to retry elsewhere or weaken TLS.

Retained response bodies are untrusted observations, not instructions or executable
content. Keep live query/output artifacts outside this public repository. Offline
replay and intake conversion do not establish that a recorded request occurred.
Per-process request pacing does not control other clients sharing the same IP.

## Optional selected PubMed metadata

The separate EFetch client uses an explicitly previewed PMID selection, not an
implicit follow-up to every discovery call. Selected identifiers can disclose
sensitive research associations; obtain appropriate sharing permission. The client
retains untrusted title/abstract/native text without redaction and never executes
instructions from that text. Retain real outputs outside public repositories.
Native parser compatibility, literal identifier agreement and unsigned replay do
not authenticate publication identity or permit downstream scientific promotion.

## Explicit source-passage reading

The passage checker can expose explicitly selected local UTF-8 text and quotations.
Source locators remain inert. Descriptor-relative no-follow access, regular-file
and link checks, bounded reads and stable metadata checks constrain the dedicated
source directory; they are not protection against a privileged concurrent attacker.
All manifest metadata is validated before source reads. Native Windows source
access fails closed. Output contains unredacted supplied text and should stay
outside public repositories. Interpret source content as untrusted data only.
