"""Display supplied patent ledger observations without legal or readiness judgement."""
import argparse
from pathlib import Path

from json_io import configure_utf8_stdio
import patent_links as links
from patent_intake import encode, write_new


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('protocol', type=Path)
    parser.add_argument('--text', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        result = links.review(links.read(args.protocol, links.MAX_PROTOCOL_BYTES))
        encoded = encode(result)
        rendered = links.render_text(result) if args.text else encoded.decode('utf-8')
        if len(rendered.encode('utf-8')) > links.MAX_OUTPUT_BYTES:
            raise ValueError('output byte limit')
        if args.output is not None:
            write_new(args.output, encoded)
        print(rendered, end='')
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError, RecursionError, OverflowError):
        parser.exit(1, 'patent review error: invalid, oversized or unreadable input, or unavailable new output; details withheld\n')


if __name__ == '__main__':
    raise SystemExit(main())
