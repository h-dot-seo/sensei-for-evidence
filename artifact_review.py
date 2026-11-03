"""Opt-in local work-artifact byte checks; never acceptance or scientific review."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from evidence_workflow import run
from prisma_reports import report_flow
from research_bundle import engine_hashes
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json

MAX_FILE_BYTES = 10_000_000
MAX_TOTAL_BYTES = 50_000_000
MAX_ARTIFACTS = 1000
MAX_INPUT_BYTES = 50_000_000
BOUNDARY = ('Local byte consistency only, against supplied expected hashes. No content is returned, '
            'interpreted or transmitted. Matching bytes do not verify authorship, source authenticity, '
            'acceptance criteria, scientific validity or work completion. Protocol status, acceptance '
            'and dependency assertions are never changed. Use a dedicated, trusted, quiescent artifact '
            'directory; this is not a security boundary against a privileged concurrent filesystem attacker.')


def secure_open_supported():
    return (os.name == 'posix' and hasattr(os, 'O_NOFOLLOW') and hasattr(os, 'O_DIRECTORY')
            and os.open in os.supports_dir_fd)


def safe_relative(value):
    if (not isinstance(value,str) or not value or '\\' in value or ':' in value
            or any(ord(c)<32 or ord(c)==127 for c in value)):
        raise ValueError('artifact path must be a portable relative file path')
    p=PurePosixPath(value)
    if (p.is_absolute() or not p.parts or p.as_posix()!=value or
            any(part in ('.','..','.git','.aws','.codex') or part.endswith((' ','.')) for part in p.parts)):
        raise ValueError('unsafe artifact path')
    return p.parts


def validate_manifest(manifest, work):
    if (not isinstance(manifest,dict) or set(manifest)!={'schema_version','artifacts'}
            or type(manifest['schema_version']) is not int or manifest['schema_version']!=1
            or not isinstance(manifest['artifacts'],list)):
        raise ValueError('artifact manifest requires schema_version 1 and artifacts list')
    if len(manifest['artifacts'])>MAX_ARTIFACTS:raise ValueError('too many artifact entries')
    rows=[];seen=set();paths=set();total=0
    for entry in manifest['artifacts']:
        if not isinstance(entry,dict) or set(entry)!={'work_package_id','artifact_locator','path','bytes','sha256'}:
            raise ValueError('invalid artifact manifest entry fields')
        wid=entry['work_package_id']
        if not isinstance(wid,str) or wid not in work or wid in seen:
            raise ValueError('artifact work package must be known and unique')
        locator=entry['artifact_locator']
        if not isinstance(locator,str) or not locator.strip() or locator!=work[wid].get('artifact_locator'):
            raise ValueError('artifact locator must exactly match the supplied work package')
        parts=safe_relative(entry['path'])
        if entry['path'].casefold() in paths:raise ValueError('duplicate artifact path')
        if type(entry['bytes']) is not int or not 0<=entry['bytes']<=MAX_FILE_BYTES:
            raise ValueError('artifact size outside supported byte limit')
        if not isinstance(entry['sha256'],str) or re.fullmatch('[0-9a-f]{64}',entry['sha256']) is None:
            raise ValueError('artifact SHA-256 must be lowercase hexadecimal')
        total+=entry['bytes']
        if total>MAX_TOTAL_BYTES:raise ValueError('artifact total exceeds byte limit')
        rows.append((entry,parts));seen.add(wid);paths.add(entry['path'].casefold())
    return rows


def open_root(root):
    # Every component, including the explicit root itself, is opened without
    # following symlinks. Keep directory descriptors rather than resolving paths.
    if '..' in Path(root).parts:raise ValueError('artifact root must not contain parent traversal')
    absolute=Path(os.path.abspath(root))
    if absolute==Path(absolute.anchor):raise ValueError('artifact root must be a dedicated directory')
    flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW
    fd=os.open(absolute.anchor,flags)
    try:
        for part in absolute.parts[1:]:
            next_fd=os.open(part,flags,dir_fd=fd)
            os.close(fd);fd=next_fd
        return fd
    except BaseException:
        os.close(fd);raise


def check_file(root_fd,parts,entry):
    directory=os.dup(root_fd);fd=None
    try:
        for part in parts[:-1]:
            nxt=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=directory)
            os.close(directory);directory=nxt
        listed=os.stat(parts[-1],dir_fd=directory,follow_symlinks=False)
        if not stat.S_ISREG(listed.st_mode) or listed.st_nlink!=1:
            return dict(status='REJECTED_FILE_TYPE',observed_bytes=None,observed_sha256=None)
        # NONBLOCK prevents a raced FIFO from hanging before fstat rejects it.
        fd=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=directory)
        before=os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink!=1
                or (listed.st_dev,listed.st_ino)!=(before.st_dev,before.st_ino)):
            return dict(status='REJECTED_FILE_TYPE',observed_bytes=None,observed_sha256=None)
        if before.st_size>MAX_FILE_BYTES or before.st_size!=entry['bytes']:
            return dict(status='SIZE_MISMATCH',observed_bytes=before.st_size,observed_sha256=None)
        digest=hashlib.sha256();count=0
        while True:
            chunk=os.read(fd,min(65536,entry['bytes']-count+1))
            if not chunk:break
            count+=len(chunk)
            if count>entry['bytes']:return dict(status='CHANGED_DURING_READ',observed_bytes=count,observed_sha256=None)
            digest.update(chunk)
        after=os.fstat(fd)
        signature=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink)
        if count!=entry['bytes'] or signature(before)!=signature(after):
            return dict(status='CHANGED_DURING_READ',observed_bytes=count,observed_sha256=None)
        sha=digest.hexdigest()
        return dict(status='BYTES_MATCH' if sha==entry['sha256'] else 'HASH_MISMATCH',observed_bytes=count,observed_sha256=sha)
    except FileNotFoundError:
        return dict(status='MISSING',observed_bytes=None,observed_sha256=None)
    except OSError:
        # Do not expose filesystem exception strings or absolute paths.
        return dict(status='UNREADABLE_OR_UNSAFE_PATH',observed_bytes=None,observed_sha256=None)
    finally:
        if fd is not None:os.close(fd)
        os.close(directory)


def review_artifacts(protocol,manifest,root):
    research=run(protocol)
    if 'reports' in protocol:report_flow(protocol)
    work={row['work_package_id']:row for row in research['work_packages']}
    rows=validate_manifest(manifest,work) # Validate ALL metadata before opening artifacts.
    if not secure_open_supported():
        raise ValueError('secure descriptor-relative no-follow file access unavailable; no artifacts inspected')
    try:root_fd=open_root(root)
    except OSError as error:raise ValueError('artifact root unreadable or unsafe; no artifacts inspected') from error
    results=[]
    try:
        for entry,parts in rows:
            item=work[entry['work_package_id']]
            results.append(dict(entry,**check_file(root_fd,parts,entry),
                supplied_work_status=item['status'],question=item['question'],deliverable=item['deliverable'],
                acceptance_criterion=item['acceptance_criterion'],supplied_acceptance_verified=item.get('acceptance_verified'),
                depends_on=list(item['depends_on']),blocked_by=list(item['blocked_by']),
                acceptance_assessment='NOT_PERFORMED'))
    finally:os.close(root_fd)
    checked={r['work_package_id'] for r in results}
    return dict(schema_version=1,protocol_sha256=hashlib.sha256(canonical_json_bytes(protocol)).hexdigest(),
                manifest_sha256=hashlib.sha256(canonical_json_bytes(manifest)).hexdigest(),
                engine_sha256=dict(engine_hashes(),**{'artifact_review.py':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}),
                artifacts=results,uninspected_work_ids=sorted(set(work)-checked),
                all_requested_bytes_match=bool(results) and all(r['status']=='BYTES_MATCH' for r in results),
                inspection_scope='explicit manifest entries only; unlisted work is not inspected',
                census_claim='NOT_ESTABLISHED',conclusion_readiness='NOT_READY',boundary=BOUNDARY)


def read_input(path):
    metadata=path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or bool(getattr(metadata,'st_file_attributes',0) & getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0)):
        raise ValueError('input JSON must be a regular non-symlink file')
    fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0)|getattr(os,'O_BINARY',0))
    try:
        current=os.fstat(fd)
        if not stat.S_ISREG(current.st_mode):raise ValueError('input JSON must be a regular file')
        if current.st_size>MAX_INPUT_BYTES:raise ValueError('input JSON exceeds byte limit')
        chunks=[];count=0
        while True:
            chunk=os.read(fd,min(65536,MAX_INPUT_BYTES-count+1))
            if not chunk:break
            count+=len(chunk)
            if count>MAX_INPUT_BYTES:raise ValueError('input JSON exceeds byte limit')
            chunks.append(chunk)
        return parse_json(b''.join(chunks))
    finally:os.close(fd)


def main():
    configure_utf8_stdio();parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('protocol',type=Path);parser.add_argument('manifest',type=Path)
    parser.add_argument('--root',type=Path,required=True,help='explicit dedicated local artifact directory; never inferred from a locator')
    args=parser.parse_args()
    try:result=review_artifacts(read_input(args.protocol),read_input(args.manifest),args.root)
    except OSError:parser.exit(1,'explicit input file unreadable\n')
    except (ValueError,TypeError,KeyError) as error:parser.exit(1,str(error)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if not result['all_requested_bytes_match']:parser.exit(1)

if __name__=='__main__':main()
