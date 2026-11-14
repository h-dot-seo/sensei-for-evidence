"""Inspect supplied result basis labels and their citation cues without reading documents."""
import argparse
import copy
from pathlib import Path
from evidence_workflow import run
from evidence_basis_links import BOUNDARY, statement_cues
from evidence_basis_intake import _normalized, _read, _encode, MAX_PROTOCOL_BYTES, MAX_APPLICATION_BYTES
from json_io import configure_utf8_stdio, quoted_display
from research_bundle import engine_hashes


def review(protocol):
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'protocol')
    research = run(protocol)
    supplied = 'evidence_bases' in research
    return _normalized(dict(schema_version=1, stage='SUPPLIED' if supplied else 'NOT_SUPPLIED',
        evidence_bases=copy.deepcopy(research.get('evidence_bases')),
        statement_cues=statement_cues(research) if supplied else None,
        engine_sha256=engine_hashes(), protocol_changed=False, external_calls=0,
        scientific_assessment='NOT_PERFORMED', boundary=BOUNDARY), MAX_APPLICATION_BYTES, 'review')


def render_text(result):
    return 'Supplied evidence basis review\n' + '\n'.join(quoted_display(k) + ': ' + quoted_display(v) for k,v in result.items()) + '\n'


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('protocol', type=Path)
    parser.add_argument('--text', action='store_true')
    args = parser.parse_args()
    try:
        result = review(_read(args.protocol, MAX_PROTOCOL_BYTES, 'protocol'))
        rendered = render_text(result) if args.text else _encode(result)
        if len(rendered.encode('utf-8')) > MAX_APPLICATION_BYTES:
            raise ValueError('output exceeds budget')
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError, OverflowError):
        parser.exit(1, 'evidence basis review error: invalid input or output\n')
    print(rendered, end='')


if __name__ == '__main__':
    main()
