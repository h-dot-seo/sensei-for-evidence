"""Local documentation syntax/inventory helpers; never execute shell or follow URLs."""
import hashlib
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


def documents(root):
    return sorted([*root.glob('*.md'), *(root/'docs').rglob('*.md')])


def parts(text):
    """Yield prose lines and exact fenced blocks; closing fences match opener kind/length."""
    lines=text.splitlines(keepends=True);prose=[];blocks=[];opened=None;body=[]
    for line in lines:
        if opened:
            if re.fullmatch(r' {0,3}'+re.escape(opened[0][0])+r'{'+str(len(opened[0]))+r',}\s*',line.rstrip('\r\n')):
                blocks.append((opened[1],''.join(body)));opened=None;body=[]
            else:body.append(line)
        else:
            m=re.match(r'^ {0,3}(`{3,}|~{3,})([^\r\n]*)[\r\n]*$',line)
            if m:opened=(m[1],m[2].strip())
            elif not line.startswith(('    ', '\t')):prose.append(line)
    if opened:raise ValueError('unclosed fenced block')
    return ''.join(prose),blocks


def inline_prose(text):
    return re.sub(r'(`+)(.*?)\1', '', text)


def anchors(text):
    prose,_=parts(text);used=set();result=[]
    for line in prose.splitlines():
        m=re.match(r'^ {0,3}#{1,6}\s+(.+?)(?:\s+#+\s*)?$',line)
        if not m:continue
        heading=re.sub(r'\[([^\]]+)\]\([^)]*\)',r'\1',m[1])
        slug=re.sub(r'[^\w\- ]','',heading.lower()).replace(' ','-')
        candidate=slug;n=0
        while candidate in used:n+=1;candidate=slug+'-'+str(n)
        used.add(candidate);result.append(candidate)
    return result


def links(text):
    prose,_=parts(text);prose=inline_prose(prose)
    # This repository's inline-link dialect; unsupported link forms fail the dialect check.
    return re.findall(r'!?\[[^\]\n]*\]\(([^\n)]*)\)',prose)


def local_target(root,source,target):
    """Return a confined target and decoded fragment; schemes are never accessed."""
    value=target.strip()
    if value.startswith('<') and value.endswith('>'):value=value[1:-1]
    parsed=urlsplit(value)
    if parsed.scheme or parsed.netloc:return None
    if parsed.query:raise ValueError('local query unsupported')
    if re.search(r'%(?![0-9A-Fa-f]{2})',parsed.path+parsed.fragment):raise ValueError('malformed percent escape')
    path=unquote(parsed.path,errors='strict');fragment=unquote(parsed.fragment,errors='strict')
    if '\\' in path or '\x00' in path or Path(path).is_absolute():raise ValueError('unsafe local path')
    resolved=(source.parent/path).resolve() if path else source.resolve()
    try:resolved.relative_to(root.resolve())
    except ValueError:raise ValueError('local link escapes checkout') from None
    return resolved,fragment


def dialect_issues(text):
    prose=inline_prose(parts(text)[0])
    # The one supported YAML front matter at the start is not a setext heading.
    if prose.startswith('---\n'):
        end=prose.find('\n---\n',4)
        if end>=0:prose=prose[end+5:]
    patterns={
        'reference definition':r'^ {0,3}\[[^\]]+\]:\s*\S',
        'reference link':r'\[[^\]\n]+\]\[[^\]\n]*\]',
        'HTML link/image or comment':r'<(?:a\b|img\b|!--)',
        'nested link destination':r'\]\([^\)\n]*\(',
        'setext heading':r'[^\n]\n {0,3}(?:={3,}|-{3,})\s*(?:\n|$)',
    }
    return [name for name,pattern in patterns.items() if re.search(pattern,prose,re.M|re.I)]


def check_links(root):
    failures=[];count=0
    for source in documents(root):
        text=source.read_text(encoding='utf-8')
        issues=dialect_issues(text)
        if issues:
            failures.append((str(source.relative_to(root)),'unsupported Markdown dialect',', '.join(issues)))
            continue
        for target in links(text):
            count+=1
            try:
                local=local_target(root,source,target)
                if local is None:continue
                path,fragment=local
                if not path.is_file():raise ValueError('missing local file')
                if fragment and (path.suffix!='.md' or fragment not in anchors(path.read_text(encoding='utf-8'))):
                    raise ValueError('missing local heading')
            except ValueError as error:failures.append((str(source.relative_to(root)),target,str(error)))
    return count,failures


def shell_blocks(root):
    values={}
    for source in documents(root):
        n=0
        for info,body in parts(source.read_text(encoding='utf-8'))[1]:
            if info!='sh':continue
            key=str(source.relative_to(root)).replace('\\','/')+'::'+str(n);n+=1
            values[key]={'body':body,'sha256':hashlib.sha256(body.encode('utf-8')).hexdigest()}
    return values


def command_argv(body):
    import shlex
    commands=[]
    for line in body.splitlines():
        if not line.strip() or line.lstrip().startswith('#'):continue
        if any(c in line for c in (';', '|', '&', '<', '>', '`', '$', '\\')):
            raise ValueError('shell syntax is not permitted')
        args=shlex.split(line)
        if len(args)<2 or args[0]!='python' or not re.fullmatch(r'[a-z][a-z0-9_]*\.py',args[1]):
            raise ValueError('only literal root Python argv permitted')
        commands.append(args[1:])
    if not commands:raise ValueError('empty command block')
    return commands


def execute_block(root,body,entry,folder):
    import os
    import subprocess
    import sys
    import tempfile
    commands=command_argv(body)
    if commands!=entry['argv']:raise ValueError('command argv differs from reviewed allowlist')
    allowed={'evidence_workflow.py','research_status.py','review_handoff.py','work_review.py',
        'synthesis_review.py','compare_runs.py','prisma_audit.py','prisma_reports.py',
        'report_review.py','report_study_review.py','report_study_inventory.py','search_manifest.py','research_bundle.py'}
    mappings=entry['scratch']
    if len(mappings)!=len(set(mappings.values())) or any('/' in value or value in ('','..','.') for value in mappings.values()):
        raise ValueError('scratch names must be distinct flat names')
    if len(commands)!=len(entry['returncodes']):raise ValueError('missing exact exit expectations')
    results=[]
    for argv,expected in zip(commands,entry['returncodes']):
        if argv[0] not in allowed:raise ValueError('script not approved for fixture execution')
        converted=[]
        for arg in argv[1:]:
            if arg in mappings:converted.append(str(folder/mappings[arg]))
            elif arg.startswith('examples/'):
                source=(root/arg).resolve()
                if not source.is_relative_to((root/'examples').resolve()) or not source.is_file():raise ValueError('not a shipped example')
                converted.append(str(source))
            elif '/' in arg or '\\' in arg:raise ValueError('unapproved path argument')
            else:converted.append(arg)
        with tempfile.TemporaryFile() as stdout,tempfile.TemporaryFile() as stderr:
            result=subprocess.run([sys.executable,str(root/argv[0]),*converted],cwd=folder,
                env=dict(os.environ,PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1'),
                stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,timeout=30,check=False)
            if stdout.tell()>2_000_000 or stderr.tell()>2_000_000:raise ValueError('captured output exceeds test budget')
            stdout.seek(0);stderr.seek(0);out=stdout.read();err=stderr.read()
        if result.returncode!=expected or err:raise AssertionError((argv[0],result.returncode,expected,err))
        results.append((result.returncode,len(out),hashlib.sha256(out).hexdigest()))
    if len(commands)!=len(entry['returncodes']):raise ValueError('missing exact exit expectations')
    return results


def parse_only(body,entry):
    """Only the explicitly reviewed research_bundle parser; stop before product code."""
    import argparse
    import importlib
    from unittest.mock import patch
    commands=command_argv(body)
    if commands!=entry['argv'] or any(a[0]!='research_bundle.py' for a in commands):
        raise ValueError('parser not explicitly approved')
    module=importlib.import_module('research_bundle')
    original=argparse.ArgumentParser.parse_args
    class Parsed(BaseException):pass
    for argv in commands:
        def stop(parser,args=None,namespace=None):
            original(parser,argv[1:],namespace)
            raise Parsed()
        with patch.object(argparse.ArgumentParser,'parse_args',stop):
            try:module.main()
            except Parsed:pass
            else:raise AssertionError('parser stop was not reached')
    return len(commands)
