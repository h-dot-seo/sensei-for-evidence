"""Expose a source-bound, partially reviewed command-effects contract without executing commands."""
import hashlib
import json
from pathlib import Path
import re

from json_io import parse_json

ROOT = Path(__file__).resolve().parent
REGISTRY = 'docs/command_contract.json'
MAX_BYTES = 2_000_000
BOUNDARY = ('Contract only: no listed command executed and no network request. '
            'Declarations are not permission, input acceptance, authentication or a recommended execution order. '
            'NOT_REVIEWED/null effects are unknown, not read-only. Exact-target receipt fields must not be '
            'invented and stale target hashes must not be copied to clear a queue; this contract does not enforce '
            'human review. Census stays NOT_ESTABLISHED; conclusion readiness stays NOT_READY.')


def _read(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('expected regular checkout file')
    with path.open('rb') as handle:
        raw = handle.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('checkout file exceeds bound')
    return raw


def _object(value, fields):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError('invalid declaration shape')


def _strings(value):
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value) or len(value) != len(set(value)):
        raise ValueError('invalid string inventory')


def _outcome(value, fields, codes, stdout, stderr=None):
    _object(value, fields)
    if type(value['exit_code']) is not int or value['exit_code'] not in codes or value['stdout'] not in stdout:
        raise ValueError('invalid outcome')
    if stderr is not None and value['stderr'] not in stderr:
        raise ValueError('invalid diagnostic channel')


def _effects(value):
    if value is None:
        return
    _object(value, ('inputs', 'outputs', 'network', 'success', 'caught_error', 'negative_report', 'usage_error', 'notes'))
    _strings(value['inputs'])
    if value['network'] not in ('none', 'explicit_NCBI_fetch') or not isinstance(value['notes'], str):
        raise ValueError('invalid effect')
    if not isinstance(value['outputs'], list):
        raise ValueError('invalid outputs')
    arguments = []
    for output in value['outputs']:
        _object(output, ('argument', 'condition', 'mode'))
        if not all(isinstance(output[key], str) and output[key] for key in output) or output['mode'] != 'exclusive_create':
            raise ValueError('invalid output')
        arguments.append(output['argument'])
    _strings(arguments)
    _outcome(value['success'], ('exit_code', 'stdout'), (0,), ('json', 'json_or_text'))
    _outcome(value['caught_error'], ('exit_code', 'stdout', 'stderr'), (1, 2), ('empty',), ('diagnostic_not_guaranteed_private',))
    _outcome(value['usage_error'], ('exit_code', 'stdout', 'stderr'), (2,), ('empty',), ('argparse_diagnostic',))
    negative = value['negative_report']
    if negative is not None:
        _outcome(negative, ('condition', 'exit_code', 'stdout', 'stderr'), (1, 2), ('json', 'json_or_text'), ('empty',))
        if not isinstance(negative['condition'], str) or not negative['condition']:
            raise ValueError('invalid negative report')


def contract():
    """Read declarations only after matching all root Python implementation bytes."""
    raw = _read(ROOT / REGISTRY)
    data = parse_json(raw)
    if not isinstance(data, dict) or set(data) != {'schema_version', 'implementation_sha256', 'commands'} or type(data['schema_version']) is not int or data['schema_version'] != 1:
        raise ValueError('unsupported registry')
    expected = data['implementation_sha256']
    names = {path.name for path in ROOT.glob('*.py')}
    if not isinstance(expected, dict) or set(expected) != names:
        raise ValueError('implementation inventory changed')
    total = 0
    for name, digest in expected.items():
        if not re.fullmatch(r'[a-z][a-z0-9_]*\.py', name) or not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise ValueError('invalid implementation binding')
        source = _read(ROOT / name)
        total += len(source)
        if total > 50_000_000 or hashlib.sha256(source).hexdigest() != digest:
            raise ValueError('implementation changed; declarations need review')
    from review_handoff import SUPPLIED_INPUT_WORKFLOWS
    rows = data['commands']
    if not isinstance(rows, list) or not rows or len(rows) > 1000:
        raise ValueError('invalid command registry')
    keys = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'script', 'subcommand', 'usage', 'purpose', 'guides', 'has_parser', 'effects'}:
            raise ValueError('invalid command row')
        if (not isinstance(row['script'], str) or type(row['has_parser']) is not bool
                or not isinstance(row['purpose'], str) or not row['purpose']
                or (row['subcommand'] is not None and (not isinstance(row['subcommand'], str) or not re.fullmatch(r'[a-z][a-z0-9_-]*', row['subcommand'])))
                or (row['has_parser'] and (not isinstance(row['usage'], str) or not row['usage']))
                or (not row['has_parser'] and row['usage'] is not None)):
            raise ValueError('invalid command metadata')
        _strings(row['guides'])
        if not row['guides'] or any(not re.fullmatch(r'(?:docs/)?[A-Za-z0-9_.-]+\.md', guide) for guide in row['guides']):
            raise ValueError('invalid guides')
        _effects(row['effects'])
        key = (row['script'], row['subcommand'])
        if key in keys or row['script'] not in expected:
            raise ValueError('duplicate or unknown command')
        keys.add(key)
        row['effect_status'] = 'REVIEWED' if row['effects'] is not None else 'NOT_REVIEWED'
        row['route_ids'] = [route['workflow_id'] for route in SUPPLIED_INPUT_WORKFLOWS
                            if any(entry['script'] == row['script'] and
                                   entry['arguments'] == ([row['subcommand']] if row['subcommand'] else []) + ['--help']
                                   for entry in route['entrypoints'])]
    routes = [dict(workflow_id=route['workflow_id'],
                   required_human_inputs=route['required_human_inputs'], boundary=route['boundary'])
              for route in SUPPLIED_INPUT_WORKFLOWS]
    return dict(schema_version=1, commands=rows, routes=routes,
                coverage=dict(commands=len(rows), reviewed_effects=sum(row['effects'] is not None for row in rows),
                              scope='Partial effects coverage; all other commands require guide and implementation review'),
                implementation_sha256=expected, registry_sha256=hashlib.sha256(raw).hexdigest(),
                hash_scope='Exact checkout bytes, not authentication or semantic verification',
                help_policy='Only has_parser=true supports parser-help discovery; audit_publication.py and verify_manifest.py run checks even with --help',
                failure_scope='Declared handled outcomes only; usage errors, unexpected exceptions, OS partial writes and resource exhaustion are not normalized',
                file_scope='Logical command outputs only; interpreter caches and OS/runtime activity are not a sandbox guarantee',
                census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY', boundary=BOUNDARY)


def render_text(result):
    """JSON-quote all catalog strings so control characters cannot spoof lines."""
    quote = lambda value: json.dumps(value, ensure_ascii=True, sort_keys=True)
    lines = ['Command effects contract (partial reviewed coverage):']
    for row in result['commands']:
        lines.append(quote([row['script'], row['subcommand']]) + ' ' + row['effect_status'])
        lines.append('  usage: ' + quote(row['usage']))
        lines.append('  effects: ' + quote(row['effects']))
        lines.append('  routes: ' + quote(row['route_ids']))
    lines.extend(['coverage: ' + quote(result['coverage']), 'routes: ' + quote(result['routes']),
                  result['help_policy'], result['failure_scope'], result['file_scope'], result['boundary']])
    return '\n'.join(lines) + '\n'
