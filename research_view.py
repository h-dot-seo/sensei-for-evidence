"""Render a passive local HTML review navigator over supplied research data, never approval."""
import argparse
import base64
import hashlib
import html
import json
from pathlib import Path
import unicodedata

from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display
import review_handoff
import readiness_review
import prisma_audit
import synthesis_review
import work_review

MAX_PROTOCOL_BYTES = 50_000_000
MAX_OUTPUT_BYTES = 16 * 1024 * 1024
BOUNDARY = (
    'Read-only local navigation over supplied records, not a scientific report, approval or source verification. '
    'Opening or printing this snapshot does not rerun checks, save decisions or establish reading or identity. '
    'No model, network, external execution, canonical change or automatic adjudication. '
    'Census: NOT_ESTABLISHED. Conclusion: NOT_READY. '
    'PRIVATE FILE: supplied text and identifiers are retained without redaction; keep real outputs outside '
    'the public repository and public trackers, and share only with authorization.'
)
STYLE = '''
:root{color-scheme:light}*{box-sizing:border-box}body{margin:0;background:#f4f5f4;color:#203136;font:16px/1.55 system-ui,sans-serif;overflow-wrap:anywhere}
header,main,footer{max-width:1120px;margin:auto;padding:1.5rem}h1{font-size:2.1rem;line-height:1.2}h2{font-size:1.45rem}h3{font-size:1.1rem}
nav{background:#fff;border-block:1px solid #bdc9cc;padding:1rem}nav ul{max-width:1072px;margin:auto;padding:0;display:flex;flex-wrap:wrap;gap:.6rem 1.3rem;list-style:none}
a{color:#244e5e}a:focus-visible,summary:focus-visible{outline:3px solid #244e5e;outline-offset:3px}section{background:white;border:1px solid #bdc9cc;padding:1.3rem;margin-bottom:1.5rem}
.notice{border-left:4px solid #647d85;padding:.5rem 1rem;background:#edf1f2}.muted,.empty{color:#52666c}.eyebrow{letter-spacing:.08em;text-transform:uppercase;font-size:.8rem}
dl{margin:.5rem 0}dt{font-weight:650;margin-top:.7rem}dd{margin:.2rem 0 .5rem 1rem}details{border-left:2px solid #c8d3d6;padding:.3rem .8rem;margin:.6rem 0}summary{cursor:pointer;font-weight:600}ol{padding-left:1.3rem}
table{border-collapse:collapse;width:100%;font-size:.9rem}th,td{border:1px solid #c8d3d6;text-align:left;vertical-align:top;padding:.6rem}th{background:#edf1f2}.table-scroll{overflow-x:auto}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#edf1f2;padding:1rem;font:12px/1.5 ui-monospace,monospace}code{font-family:ui-monospace,monospace}
@media(max-width:640px){header,main,footer{padding:1rem}section{padding:1rem}dd{margin-left:.4rem}h1{font-size:1.65rem}}
@media print{body{background:white;font-size:10pt}header,main,footer{max-width:none;padding:.3rem}nav{display:none}h2,h3,summary{break-after:avoid}details::details-content{content-visibility:visible}details>*:not(summary){display:block!important}pre{font-size:8pt}}
'''
STYLE_SHA256 = base64.b64encode(hashlib.sha256(STYLE.encode('utf-8')).digest()).decode('ascii')
CSP = ("default-src 'none'; style-src 'sha256-" + STYLE_SHA256 +
       "'; base-uri 'none'; form-action 'none'; object-src 'none'; frame-src 'none'")
SECTIONS = (('overview','Scope and input'),('gates','Mechanical gates'),('assertions','Supplied assertions'),
            ('queues','Review queues'),('accounting','Supplied accounting'),('statements','Statements and challenges'),
            ('work','Selected work'),('snapshot','Exact view snapshot'))


def _escape(value):
    text = str(value)
    visible = ''.join(json.dumps(c,ensure_ascii=True)[1:-1] if unicodedata.category(c) in ('Cc','Cf','Zl','Zp') else c for c in text)
    return html.escape(visible,quote=True)


def _tree(value):
    if isinstance(value,dict):
        if not value:yield '<span class="empty">Empty object; no fields supplied.</span>';return
        yield '<dl>'
        for key in sorted(value):
            yield '<dt>'+_escape(key)+'</dt><dd>'
            item=value[key]
            if isinstance(item,(dict,list)) and item:
                yield '<details><summary>Supplied fields or entries ('+str(len(item))+')</summary>'
                yield from _tree(item);yield '</details>'
            else:yield from _tree(item)
            yield '</dd>'
        yield '</dl>'
    elif isinstance(value,list):
        if not value:yield '<span class="empty">Empty list; no entries supplied.</span>';return
        yield '<ol>'
        for item in value:yield '<li>';yield from _tree(item);yield '</li>'
        yield '</ol>'
    elif value is None:yield '<span class="empty">NOT_SUPPLIED (null)</span>'
    elif type(value) is bool:yield 'true' if value else 'false'
    else:yield _escape(value)


class _Document:
    def __init__(self):self.parts=[];self.bytes=0
    def add(self,text):
        self.bytes+=len(text.encode('utf-8'))
        if self.bytes>MAX_OUTPUT_BYTES:raise ValueError('HTML exceeds 16 MiB; use the existing JSON views, no truncation performed')
        self.parts.append(text)
    def data(self,value):
        for chunk in _tree(value):self.add(chunk)
    def section(self,name,boundary):
        title=dict(SECTIONS)[name]
        self.add('<section id="'+name+'"><h2>'+title+'</h2><p class="notice">'+_escape(boundary)+'</p>')
    def table(self,rows,columns):
        self.add('<div class="table-scroll"><table><thead><tr>'+''.join('<th scope="col">'+_escape(c)+'</th>' for c in columns)+'</tr></thead><tbody>')
        for row in rows:
            self.add('<tr>')
            for key in columns:self.add('<td>');self.data(row[key]);self.add('</td>')
            self.add('</tr>')
        self.add('</tbody></table></div>')
    def finish(self):return ''.join(self.parts).encode('utf-8')


def snapshot(protocol,work_package_id=None):
    # Normalize as strict bounded JSON before any computation; never mutate caller input.
    raw=canonical_json_bytes(protocol)
    if len(raw)>MAX_PROTOCOL_BYTES:raise ValueError('protocol exceeds byte limit')
    protocol=parse_json(raw)
    handoff=review_handoff.handoff(protocol,work_package_id)
    gates=readiness_review.review(protocol);audit=prisma_audit.export_audit(protocol);synthesis=synthesis_review.snapshot(protocol)
    hashes={}
    for result in (handoff,gates,audit,synthesis):
        if result['protocol_sha256']!=handoff['protocol_sha256']:raise ValueError('view protocol bindings differ')
        for name,digest in result['engine_sha256'].items():
            if name in hashes and hashes[name]!=digest:raise ValueError('view implementation bindings differ')
            hashes[name]=digest
    hashes['research_view.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return dict(schema_version=1,question=handoff['question'],protocol_version=handoff['protocol_version'],
        protocol_sha256=handoff['protocol_sha256'],engine_sha256=hashes,handoff=handoff,readiness=gates,accounting=audit,
        synthesis={key:synthesis[key] for key in ('synthesis_stage','statements','challenge_stage','challenge_ledger','challenge_boundary','synthesis_boundary','boundary')},
        census_claim='NOT_ESTABLISHED',conclusion_readiness='NOT_READY',external_calls=0,boundary=BOUNDARY)


def render(protocol,work_package_id=None):
    result=snapshot(protocol,work_package_id);h=result['handoff'];g=result['readiness'];a=result['accounting'];s=result['synthesis']
    out=_Document();out.add('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">')
    out.add('<meta http-equiv="Content-Security-Policy" content="'+_escape(CSP)+'"><meta name="referrer" content="no-referrer">')
    out.add('<title>Supplied research | human review navigator</title><style>'+STYLE+'</style></head><body>')
    out.add('<header><p class="eyebrow">Local read-only snapshot</p><h1>Supplied research review navigator</h1><p class="notice">'+_escape(BOUNDARY)+'</p></header>')
    out.add('<nav aria-label="Review sections"><ul>'+''.join('<li><a href="#'+key+'">'+title+'</a></li>' for key,title in SECTIONS)+'</ul></nav><main>')
    out.section('overview',BOUNDARY);out.data({key:result[key] for key in ('question','protocol_version','protocol_sha256','engine_sha256')});out.add('</section>')
    out.section('gates',readiness_review.BOUNDARY);out.add('<p>'+_escape(g['gate_scope'])+'</p>');out.data({'gates_sha256':g['gates_sha256'],'gates_hash_scope':g['gates_hash_scope']})
    out.table(g['gate_ledger'],('gate_id','status','open_items','basis'));out.add('</section>')
    out.section('assertions',g['readiness_boundary']);out.add('<p>Supplied human assertions only. READY here is not this page’s conclusion.</p>')
    out.data({key:g[key] for key in ('assertion_stage','assertion_scope','gates_sha256','assertion_ledger','current_assertion_ids','stale_assertion_ids')});out.add('</section>')
    out.section('queues',review_handoff.BOUNDARY);out.add('<p>Protocol-wide queues in defined order, not priority or severity order. Selecting work narrows only work summaries.</p>')
    for step in h['manual_review_steps']:
        out.add('<details'+(' open' if step['state']=='RECORDED_ITEMS' else '')+'><summary>'+_escape(step['queue'])+' · '+_escape(step['state'])+'</summary>')
        out.data(step);out.add('</details>')
    out.add('</section>');out.section('accounting',prisma_audit.BOUNDARY);out.table(a['nodes'],('node_id','unit','stage','count','member_ids'))
    out.add('<h3>Partition checks over supplied records</h3>');out.data(a['partition_checks']);out.add('<details><summary>Complete supplied accounting view</summary>');out.data(a);out.add('</details></section>')
    out.section('statements',synthesis_review.BOUNDARY);out.data(s);out.add('</section>')
    out.section('work',work_review.BOUNDARY);out.data({'work_selection':h['work_selection'],'selected_work':h['selected_work'],'manual_work_remaining':h['manual_work_remaining']});out.add('</section>')
    out.section('snapshot',BOUNDARY);out.add('<p>This is the composed view snapshot, not the original protocol or a verification receipt.</p><details><summary>Copyable JSON view snapshot</summary><pre>')
    out.add(html.escape(json.dumps(result,ensure_ascii=True,sort_keys=True,indent=2,allow_nan=False),quote=True));out.add('</pre></details></section></main><footer><p>'+_escape(BOUNDARY)+'</p></footer></body></html>')
    raw=out.finish()
    receipt=dict(schema_version=1,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),protocol_sha256=result['protocol_sha256'],
        census_claim='NOT_ESTABLISHED',conclusion_readiness='NOT_READY',external_calls=0,boundary=BOUNDARY)
    return raw,receipt


def _read(path):
    with path.open('rb') as stream:raw=stream.read(MAX_PROTOCOL_BYTES+1)
    if len(raw)>MAX_PROTOCOL_BYTES:raise ValueError('protocol exceeds byte limit')
    return raw


def _write_new(path,raw):
    try:path.lstat()
    except FileNotFoundError:pass
    else:raise ValueError('output path already exists')
    with path.open('xb') as stream:stream.write(raw)


def main():
    configure_utf8_stdio();parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('protocol',type=Path);parser.add_argument('--work-package');parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:
        raw,receipt=render(parse_json(_read(args.protocol)),args.work_package)
        summary=json.dumps(receipt,ensure_ascii=False,allow_nan=False)+'\n'
        summary.encode('utf-8')
        if args.output is None:print(raw.decode('utf-8'),end='')
        else:_write_new(args.output,raw);print(summary,end='')
    except (ValueError,OSError,KeyError,TypeError,UnicodeError,RecursionError) as error:
        parser.exit(1,'research view: '+quoted_display(str(error))+'\n')


if __name__=='__main__':main()
