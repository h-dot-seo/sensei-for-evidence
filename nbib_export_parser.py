"""Lossless local NBIB intake for an explicit fixed-column PubMed-format subset.

Not an all-NBIB compatibility parser. Only initial BOM, CR/LF/CRLF physical
lines, PMID-first records, padded 2-4 character tags and six-space continuations
are supported. Repeated fields are ordered occurrences, never dictionaries.
"""
import hashlib
import re

MAX_EXPORT_BYTES = 10_000_000
MAX_RECORDS = 100_000
MAX_PHYSICAL_LINES = 200_000
_TAG = re.compile(r'([A-Z][A-Z0-9]{1,3})( *)- (.*)\Z')


def parse_export(raw: bytes):
    """Retain exact record/field bytes as UTF-8 text with zero-based byte spans.

    Line spans are one-based, inclusive. Byte ends are exclusive. Terminators
    belong to their physical lines; separating empty lines belong to neither
    record. An initial BOM belongs to the first physical line's byte span.
    Error messages identify location without disclosing supplied content.
    """
    if type(raw) is not bytes or not raw:
        raise ValueError('line 1: export must be nonempty bytes')
    if len(raw) > MAX_EXPORT_BYTES:
        raise ValueError('line 1: export exceeds byte limit')
    offsets = [0]
    for match in re.finditer(b'\r\n|\r|\n', raw):
        offsets.append(match.end())
        if len(offsets) - 1 > MAX_PHYSICAL_LINES:
            raise ValueError(f'line {MAX_PHYSICAL_LINES + 1}: export exceeds physical line limit')
    if offsets[-1] != len(raw):
        offsets.append(len(raw))
    if len(offsets) - 1 > MAX_PHYSICAL_LINES:
        raise ValueError(f'line {MAX_PHYSICAL_LINES + 1}: export exceeds physical line limit')
    if b'\x00' in raw:
        nul_offset = raw.index(b'\x00')
        line = 1 + sum(end <= nul_offset for end in offsets[1:])
        raise ValueError(f'line {line}: NUL bytes are not allowed')
    try:
        raw.decode('utf-8', errors='strict')
    except UnicodeDecodeError as exc:
        line = 1 + sum(end <= exc.start for end in offsets[1:])
        raise ValueError(f'line {line}: export must be strict UTF-8') from None

    def span(start, end):
        first, last = offsets[start - 1], offsets[end]
        return dict(line_start=start, line_end=end, byte_start=first, byte_end=last,
                    sha256=hashlib.sha256(raw[first:last]).hexdigest())

    def retained(start, end):
        return raw[offsets[start - 1]:offsets[end]].decode('utf-8')

    result = dict(records=[], ignored_blank_spans=[], duplicate_pmids=[],
                  physical_lines=len(offsets) - 1, initial_utf8_bom=raw.startswith(b'\xef\xbb\xbf'))
    fields = []
    record_start = None
    field_start = None
    occurrences = {}

    def finish_field(end):
        fields[-1]['source_span'] = span(field_start, end)
        fields[-1]['raw_text'] = retained(field_start, end)

    def finish_record(end):
        finish_field(end)
        pmid = fields[0]['value_lines']
        if (len(pmid) != 1 or re.fullmatch(r'[0-9]+', pmid[0]) is None
                or not any(char != '0' for char in pmid[0])):
            raise ValueError(f'line {record_start}: PMID must be one positive ASCII decimal line')
        candidate = f"nbib-record-{len(result['records']) + 1:06d}"
        result['records'].append(dict(candidate_id=candidate, pmid=pmid[0],
            source_span=span(record_start, end), raw_text=retained(record_start, end), fields=list(fields)))
        occurrences.setdefault(pmid[0], []).append(candidate)

    for number in range(1, len(offsets)):
        physical = retained(number, number)
        if physical.endswith('\r\n'):
            line = physical[:-2]
        elif physical.endswith(('\r', '\n')):
            line = physical[:-1]
        else:
            line = physical
        if number == 1 and line.startswith('\ufeff'):
            line = line[1:]
        if not line:
            if fields:
                finish_record(number - 1)
                fields = []
            result['ignored_blank_spans'].append(span(number, number))
            continue
        if line.startswith('      '):
            if not fields:
                raise ValueError(f'line {number}: orphan continuation')
            fields[-1]['value_lines'].append(line[6:])
            continue
        match = _TAG.fullmatch(line)
        if match is None or len(match[1]) + len(match[2]) != 4:
            raise ValueError(f'line {number}: malformed fixed-column field')
        tag, value = match[1], match[3]
        if not fields:
            if tag != 'PMID':
                raise ValueError(f'line {number}: record must start with PMID')
            if len(result['records']) >= MAX_RECORDS:
                raise ValueError(f'line {number}: export exceeds record limit')
            record_start = number
        else:
            if tag == 'PMID':
                raise ValueError(f'line {number}: repeated PMID or missing empty-line separator')
            finish_field(number - 1)
        fields.append(dict(tag=tag, value_lines=[value]))
        field_start = number
    if fields:
        finish_record(len(offsets) - 1)
    if not result['records']:
        raise ValueError('line 1: export contains no records')
    result['duplicate_pmids'] = [dict(pmid=pmid, candidate_ids=ids)
        for pmid, ids in occurrences.items() if len(ids) > 1]
    return result
