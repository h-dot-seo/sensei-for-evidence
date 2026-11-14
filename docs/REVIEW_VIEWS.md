# Passive local HTML review navigator

`research_view.py` composes existing handoff, readiness, supplied accounting and
statement views for a collaborator who does not run Python. It is not a scientific
report, approval, a census or evidence verification. Census: NOT_ESTABLISHED.
Conclusion: NOT_READY. Every section retains its source boundary.

```sh
python research_view.py examples/claim-comparison.json --output OUTPUT/claim-review.html
python research_view.py examples/claim-comparison.json --work-package WP-TRANSLATION --output OUTPUT/selected-review.html
```

Open the new HTML locally. Fixed section links and disclosure triangles support
navigation; there are no scripts, forms, external resources or data-derived links.
The page is a snapshot: opening it does not run checks, record decisions or prove
that someone read anything. Supplied READY assertions remain in their own ledger,
never the page conclusion. Gate status and queue state are text, not severity colors.
Empty, missing and recorded queues remain distinguishable in defined, non-priority order.

Without `--output`, HTML goes to stdout. With it, stdout is a short JSON receipt
with bytes, SHA-256 and protocol binding, not the supplied text. Output creation is
exclusive: existing files and dangling links are refused. The full HTML is built
before writing; exceeding 16 MiB fails without truncating. OS write failures may
leave an incomplete new output, so verify the receipt before relying on a file.
The input limit is 50,000,000 bytes. Symlink races and hostile filesystems are not
sandboxed. No network, model, additional approval or canonical change occurs.

`--work-package` narrows only selected work summaries. Queues remain protocol-wide.
Use the existing JSON views if the full document exceeds the output bound. The
copyable snapshot is the composed view, not the original protocol or a verification
receipt. It retains supplied text and identifiers; it is **not anonymized**.
Keep real inputs and generated HTML outside the public repository and public
trackers. Share only with authorization. Printing is browser-dependent; expand
disclosures when reviewing details. The JSON snapshot preserves their complete data.

Markdown, bundle inclusion, interactive decisions and source authentication are
not implemented by this view. Existing modules and ENGINE_FILES are unchanged.
