# Public extraction record

Release scope: framework concepts and executable generic code only.

Included by explicit allowlist: documentation, source code, synthetic examples,
tests, empty record templates, agent instructions and publication checks.
Excluded: source corpora, actual conversations, person-specific persona packages,
research/experimental databases, project evidence tables, real validation results,
books/articles/figures, private configurations, profiles, cookies, keys, logs,
authentication bundles, backups, and all private Git history/LFS objects.

No claim is made that a real persona or scientific project was validated by this
release. Runtime test results concern only the generic code and synthetic fixtures.
See README for implemented versus specified behavior and known integration limits.

The manifest binds this release's file bytes. It excludes itself to avoid a recursive
hash dependency. A source hash establishes identity; it does not establish scholarly
support, personal consent or redistribution rights.

Inventory verification rejects unlisted checkout files and symlink/path ambiguity,
in addition to checking listed bytes. Git metadata, generated Python caches and
the manifest itself are excluded. This is not a secret detector, authorship
signature or permission to publish material outside the selected public scope.

## Owner decision on live PubMed requests (2026-11-08)

The separately invoked PubMed ESearch/EFetch clients described in SECURITY.md are
an approved part of this public release boundary. All other processing remains
offline, no credential or API key is supported, and live query/output artifacts
stay outside this repository.
