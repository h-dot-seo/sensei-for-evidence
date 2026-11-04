"""Preserve an explicit fixed-column UTF-8 RIS subset without identity inference.

Records start with TY and end with an empty ER. Fields have two uppercase
alphanumeric tag characters followed by two spaces, a hyphen and optional
space/value. Only six-space continuations are supported. Unknown tags and types
are retained; this is not a universal RIS or bibliographic-semantic validator.
"""
import hashlib
import re

MAX_EXPORT_BYTES = 10_000_000
MAX_RECORDS = 100_000
MAX_PHYSICAL_LINES = 200_000
_TAG = re.compile(r'([A-Z][A-Z0-9])  -(?: (.*))?\Z')
_TYPE = re.compile(r'[A-Z][A-Z0-9]{0,15}\Z')


def parse_export(raw: bytes):
    """Return ordered fields/records and exact byte/physical-line provenance.

    Byte spans are zero-based with exclusive ends; line spans are one-based
    inclusive. Record spans include TY and ER and their terminators. Blank lines
    outside records are retained separately. No tag supplies a canonical ID.
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
    except UnicodeDecodeError as error:
        line = 1 + sum(end <= error.start for end in offsets[1:])
        raise ValueError(f'line {line}: export must be strict UTF-8') from None

    def span(first, last):
        start, end = offsets[first - 1], offsets[last]
        return dict(line_start=first, line_end=last, byte_start=start, byte_end=end,
                    sha256=hashlib.sha256(raw[start:end]).hexdigest())

    def text(first, last):
        return raw[offsets[first - 1]:offsets[last]].decode('utf-8')

    result = dict(records=[], ignored_blank_spans=[], physical_lines=len(offsets) - 1,
                  initial_utf8_bom=raw.startswith(b'\xef\xbb\xbf'))
    fields = []
    record_start = field_start = None

    def finish_field(last):
        fields[-1]['source_span'] = span(field_start, last)
        fields[-1]['raw_text'] = text(field_start, last)

    for number in range(1, len(offsets)):
        physical = text(number, number)
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
                raise ValueError(f'line {number}: empty line inside an unfinished record; explicit ER required')
            result['ignored_blank_spans'].append(span(number, number))
            continue
        if line.startswith('      '):
            if not fields or fields[-1]['tag'] == 'TY':
                raise ValueError(f'line {number}: continuation requires a non-TY field in an open record')
            fields[-1]['value_lines'].append(line[6:])
            continue
        matched = _TAG.fullmatch(line)
        if matched is None:
            raise ValueError(f'line {number}: unsupported fixed-column field or continuation')
        tag, value = matched[1], matched[2] if matched[2] is not None else ''
        if not fields:
            if tag != 'TY':
                raise ValueError(f'line {number}: record must start with TY')
            if _TYPE.fullmatch(value) is None:
                raise ValueError(f'line {number}: TY must have one literal uppercase type token')
            if len(result['records']) >= MAX_RECORDS:
                raise ValueError(f'line {number}: export exceeds record limit')
            record_start = number
        else:
            if tag == 'TY':
                raise ValueError(f'line {number}: new TY before explicit ER')
            finish_field(number - 1)
        if tag == 'ER' and value != '':
            raise ValueError(f'line {number}: ER must be empty')
        fields.append(dict(tag=tag, value_lines=[value]))
        field_start = number
        if tag == 'ER':
            finish_field(number)
            result['records'].append(dict(candidate_id=f"ris-record-{len(result['records']) + 1:06d}",
                record_type=fields[0]['value_lines'][0], fields=fields,
                source_span=span(record_start, number), raw_text=text(record_start, number)))
            fields = []
    if fields:
        raise ValueError(f'line {record_start}: record lacks explicit closing ER')
    if not result['records']:
        raise ValueError('line 1: export contains no records')
    return result
