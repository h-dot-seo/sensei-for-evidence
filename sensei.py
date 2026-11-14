"""List and run the root command-line scripts of this repository from one entry point.

`list` prints every root script that has a main entry point with the first sentence of
its docstring, then the supplied-input routes of the operator handoff catalog with their
scripts and guides. `run SCRIPT [ARGUMENTS ...]` executes one root script exactly as
`python SCRIPT [ARGUMENTS ...]` does, without a shell. The documented `python <script>`
form stays the primary one. `check` performs a read-only checkout/inventory smoke check
and runs one synthetic status fixture; it is not research validation or the test suite.
Repository modules are imported lazily by the subcommands that need them.
"""
import argparse
import ast
import json
import re
import runpy
import sys
import subprocess
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SELF = Path(__file__).name

BOUNDARY = ('Listing only: no script was executed, no file outside this repository was read and '
            'no network request was made. `python sensei.py run SCRIPT ...` is identical to '
            '`python SCRIPT ...`; it adds no scientific judgement, authentication or model call. '
            'Census stays NOT_ESTABLISHED and the mechanical conclusion readiness stays NOT_READY '
            'in every tool output.')


CHECK_BOUNDARY = ('Repository/inventory smoke check of this checkout; not the test suite, CI matrix '
                  'or research validation. No scientific judgement, authentication, model call or '
                  'network request. Census stays NOT_ESTABLISHED; conclusion readiness stays NOT_READY.')


def check_checkout():
    """Check listed bytes and syntax, then one synthetic status; never write bytecode."""
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from verify_manifest import verify
        from json_io import parse_json
        errors = verify(ROOT)
        extras = [error for error in errors if error.endswith(': unlisted file')]
        failures = [error for error in errors if not error.endswith(': unlisted file')]
        if failures:
            print('FAIL inventory: checkout differs from the published release')
            for error in failures:
                print('  ' + plain(error))
            print('SKIP syntax and synthetic status: inventory failed')
            return 1
        manifest = parse_json((ROOT / 'PUBLICATION_MANIFEST.json').read_text(encoding='utf-8'))
        if manifest.get('project') != 'sensei-for-evidence':
            print('FAIL inventory: expected sensei-for-evidence publication manifest')
            print('SKIP syntax and synthetic status: inventory failed')
            return 1
        print('PASS inventory: listed files match the checkout manifest (not authentication)')
        if extras:
            print('WARN inventory: unlisted additions; strict verify_manifest.py still fails')
            for error in extras:
                print('  ' + plain(error))
        sources = [row['path'] for row in manifest['files'] if row['path'].endswith('.py')]
        try:
            for name in sources:
                compile((ROOT / name).read_bytes(), name, 'exec', dont_inherit=True)
        except (OSError, SyntaxError, ValueError) as error:
            print('FAIL syntax: ' + plain(error))
            print('SKIP synthetic status: syntax failed')
            return 1
        print('PASS syntax: ' + str(len(sources)) + ' manifest-listed Python files; no bytecode written')
        try:
            result = subprocess.run(
                [sys.executable, '-B', str(ROOT / 'research_status.py'),
                 str(ROOT / 'examples' / 'review-demo.json')],
                cwd=ROOT, capture_output=True, timeout=30)
            if result.returncode != 0:
                raise ValueError('status exited ' + str(result.returncode))
            status = parse_json(result.stdout.decode('utf-8'))
            if (not isinstance(status, dict)
                    or status.get('census_claim') != 'NOT_ESTABLISHED'
                    or status.get('conclusion_readiness') != 'NOT_READY'):
                raise ValueError('synthetic status boundaries did not match')
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            print('FAIL synthetic status: ' + plain(error))
            return 1
        print('PASS synthetic status: NOT_ESTABLISHED / NOT_READY')
        return 0
    except (OSError, ValueError, TypeError, ImportError, SyntaxError) as error:
        print('FAIL checkout: ' + plain(error))
        return 1
    finally:
        sys.dont_write_bytecode = previous
        print(CHECK_BOUNDARY)


def plain(text):
    """Escape control and format characters so a listing line cannot spoof another line."""
    return ''.join(json.dumps(character, ensure_ascii=True)[1:-1]
                   if unicodedata.category(character) in ('Cc', 'Cf', 'Zl', 'Zp') else character
                   for character in str(text))


def first_sentence(docstring):
    """Return the first sentence of a module docstring on one line."""
    text = ' '.join((docstring or '').split())
    if not text:
        return '(no module docstring)'
    match = re.match(r'(.+?[.!?])(?:\s|$)', text)
    return match.group(1) if match else text


def has_entry_point(tree):
    """True when a module defines a top-level main() or guards a top-level __main__ block."""
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == 'main':
            return True
        if isinstance(node, ast.If):
            names = {child.id for child in ast.walk(node.test) if isinstance(child, ast.Name)}
            constants = {child.value for child in ast.walk(node.test)
                         if isinstance(child, ast.Constant) and isinstance(child.value, str)}
            if '__name__' in names and '__main__' in constants:
                return True
    return False


def root_scripts():
    """Every root *.py file except this dispatcher, as (name, parsed module) pairs."""
    for path in sorted(ROOT.glob('*.py')):
        if path.name != SELF and path.is_file():
            yield path, ast.parse(path.read_bytes(), filename=path.name)


def entry_point_scripts():
    """Sorted (file name, first docstring sentence) pairs for root scripts with an entry point."""
    return [(path.name, first_sentence(ast.get_docstring(tree)))
            for path, tree in root_scripts() if has_entry_point(tree)]


def catalog_routes():
    """Supplied-input routes of the operator handoff catalog: (id, title, scripts, guides)."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import review_handoff  # Imported here only: `list` is the one subcommand that needs it.
    routes = []
    for route in review_handoff.SUPPLIED_INPUT_WORKFLOWS:
        scripts = []
        for entry in route['entrypoints']:
            if entry['script'] not in scripts:
                scripts.append(entry['script'])
        routes.append((route['workflow_id'], route['title'], scripts, list(route['guide_paths'])))
    return routes


def render_listing(scripts, routes):
    lines = ['Root scripts with a command line (documented form `python SCRIPT ...`; '
             '`python sensei.py run SCRIPT ...` is equivalent):']
    for name, sentence in scripts:
        lines.append('  ' + plain(name).ljust(34) + ' ' + plain(sentence))
    lines.append('')
    lines.append('Supplied-input routes of the operator handoff catalog (review_handoff.py); '
                 'each route names guides to read and scripts whose parser help to inspect:')
    for workflow_id, title, names, guides in routes:
        lines.append('  ' + plain(workflow_id).ljust(34) + ' ' + plain(title))
        lines.append('      scripts: ' + ', '.join(plain(name) for name in names))
        lines.append('      guides:  ' + ', '.join(plain(guide) for guide in guides))
    lines.append('')
    lines.append(BOUNDARY)
    return '\n'.join(lines) + '\n'


def resolve_script(name):
    """Return the path of a listed root script, or raise ValueError for anything else."""
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*\.py', name):
        raise ValueError('not a root script file name: ' + plain(ascii(name)))
    path = ROOT / name
    # Exact directory-entry spelling matters on case-insensitive filesystems too.
    # Enumerate names only, never parse unrelated sources or cache stale eligibility.
    if (name == SELF or name not in {entry.name for entry in ROOT.iterdir()}
            or not path.is_file()):
        raise ValueError('not a listed root script: ' + plain(name) + ' (see `python sensei.py list`)')
    tree = ast.parse(path.read_bytes(), filename=path.name)
    if not has_entry_point(tree):
        raise ValueError('not a listed root script: ' + plain(name) + ' (see `python sensei.py list`)')
    return path


def run_script(path, arguments):
    """Execute one root script as __main__ with its own argv; SystemExit propagates unchanged."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    sys.argv = [str(path), *arguments]
    runpy.run_path(str(path), run_name='__main__')


def build_parser():
    parser = argparse.ArgumentParser(prog=SELF, description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=BOUNDARY)
    subparsers = parser.add_subparsers(dest='command', metavar='{list,run,check}', required=True)
    subparsers.add_parser('list', help='print the root scripts with a command line and the catalog routes',
                          description='Print every root script that has a main entry point, with the first '
                                      'sentence of its docstring, then the supplied-input routes of the '
                                      'operator handoff catalog with their scripts and guides.',
                          epilog=BOUNDARY)
    subparsers.add_parser('check', help='read-only checkout/inventory and synthetic status smoke check',
                          description=CHECK_BOUNDARY, epilog='Writes no bytecode; does not run the full suite.')
    runner = subparsers.add_parser('run', help='run one root script exactly as `python SCRIPT ...` would',
                                   description='Execute the named root script with the remaining arguments, '
                                               'without a shell. Only file names printed by `list` are accepted; '
                                               'the script keeps its own output, exit status and boundaries.',
                                   epilog=BOUNDARY)
    runner.add_argument('script', help='exact file name of a listed root script, for example research_status.py')
    runner.add_argument('arguments', nargs=argparse.REMAINDER, help='passed unchanged to the script')
    return parser


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors=getattr(stream, 'errors', None) or 'strict')
    parser = build_parser()
    args = parser.parse_args()
    if args.command == 'check':
        parser.exit(check_checkout())
    if args.command == 'list':
        sys.stdout.write(render_listing(entry_point_scripts(), catalog_routes()))
        return
    try:
        path = resolve_script(args.script)
    except ValueError as error:
        parser.exit(2, SELF + ' run: error: ' + str(error) + '\n')
    run_script(path, args.arguments)


if __name__ == '__main__':
    main()
