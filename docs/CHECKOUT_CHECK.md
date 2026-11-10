# First-hour checkout smoke check

Python 3.10+, standard library only. Run this command from the repository root:

```sh
python sensei.py check
```

Or run `python PATH/TO/sensei-for-evidence/sensei.py check` from any directory.
It reads this checkout, writes no bytecode or output files, makes no network/model
call and does not inspect your own research inputs. PASS/FAIL lines cover:

1. Listed files against the local publication manifest. Changed or missing listed
   files and unsafe entries fail. This is consistency, not authentication of the
   manifest or its publisher. Do not use an untrusted checkout as a security scanner.
2. In-memory compilation of exactly the manifest-listed Python files, including tests.
   Extra directories are not compiled. There is no recursive compileall invocation.
3. One bundled synthetic status (`examples/review-demo.json`), required to exit zero
   and retain census `NOT_ESTABLISHED` and conclusion readiness `NOT_READY`.
   This subprocess has a 30-second timeout; overall runtime depends on inventory size.

Ordinary unlisted files produce WARN and may still exit zero. Symlinks, junctions,
nonregular entries and other inventory errors fail; nothing is silently ignored beyond
the strict verifier's existing exclusions. `python verify_manifest.py` remains strict
and fails on unlisted additions too. Keep environments and outputs outside the checkout.
A failed inventory skips syntax and status; failed syntax skips status. Any FAIL exits
nonzero. The command does not repair files or update the manifest.

Full verification (several minutes): `python -m unittest discover -v`, followed by
`python audit_publication.py` and `python verify_manifest.py`. The publication audit
is a maintainer scan, not part of this smoke check. The CI matrix remains required.
This is a repository/inventory smoke check, not the test suite or research validation.
It establishes no scientific adequacy, source authenticity or readiness.

For your own files, the primary direct form is
`python PATH/TO/sensei-for-evidence/research_status.py ./my-protocol.json`.
The equivalent dispatcher form is
`python PATH/TO/sensei-for-evidence/sensei.py run research_status.py ./my-protocol.json`.
Relative input/output paths use your current directory, not the checkout directory.
Guides use repository-relative examples and must be replayed from the repository root.
Keep real inputs and generated artifacts outside this public repository.
