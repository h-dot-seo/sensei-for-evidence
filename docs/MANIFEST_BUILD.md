# Reproduce a publication inventory

This closes the non-engine maintenance path: edit a trusted checkout, update its
current release record, generate a new inventory, review it, then explicitly replace
the old manifest and run the full checks. It is not an invitation or license to
contribute. RIGHTS.md remains authoritative. No tags, branch deletion, remote settings,
license decision, engine resealing or scientific validation are performed.

Use the actual release label and date you chose. For this release:

```sh
python build_manifest.py --release 0.115.0-public-manifest-build --date 2026-11-14 --check
```

For changed files use `--output ../candidate-manifest.json` instead of `--check`.
The output must be a new file outside the publication root. Review the diff, then
replace PUBLICATION_MANIFEST.json yourself. Do not use shell output redirection:
PowerShell versions can change encoding. Afterwards run `python verify_manifest.py`,
`python audit_publication.py` and `python -m unittest discover -v`.
Update VALIDATION.md current release and its Latest change `Release:` line, and append
`## YYYY-MM-DD: FULL-RELEASE-LABEL` to docs/VALIDATION_HISTORY.md before generating.

`--root DIR` selects a trusted checkout. Existing manifest declaration fields are
required and copied, never inferred. Unknown header fields are rejected rather than
silently discarded. Release and real calendar date are explicit; no clock is read.
Existing inventory rows are replaced by actual bytes, not trusted. File paths are
sorted by Unicode code point, JSON uses ASCII escapes and two-space indentation,
UTF-8 with final LF. `--check` compares these exact bytes with the existing manifest;
it is stricter than verification of inventory bytes alone.

The generator imports the existing verifier's exclusion and link rules. It rejects
links/reparse points (including ancestors), nonregular entries, case collisions and
unsafe names through the existing verifier, and carriage-return bytes in any included
file. `.git` and `__pycache__` are excluded. The manifest excludes itself. It stages
exact read bytes in temporary local storage and runs the unchanged verifier and limited publication audit on all staged bytes
including candidate metadata before
any output creation. Limits: 10,000 files and directories each and 100 MiB aggregate included bytes; the
existing manifest also has a 100 MiB input limit. Temporary data is not secure erasure.

Exit 0: exact match or created; exit 1: check mismatch; exit 2: malformed/unsupported
input, limits or filesystem failure. Validation failure creates no output; an OS
failure during the final exclusive write may leave a partial file. Source files are
never replaced. This is not an atomic snapshot or a hostile-filesystem sandbox:
stop concurrent edits and use a trusted tree, then verify the installed manifest.
Headers remain owner assertions; hashing does not establish privacy, rights or truth.
ENGINE_FILES changes still need their separate fixture/review refresh procedure.
