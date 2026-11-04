"""Parse local bibliographic CSV bytes without resolving or merging records.

Spans include original line terminators and an optional initial UTF-8 BOM.
A header-only file is valid intake, not evidence of search completeness.
"""
import csv
import hashlib
import io
import re

MAX_EXPORT_BYTES = 10_000_000
MAX_RECORDS = 100_000
MAX_PHYSICAL_LINES = 200_000


def _line_offsets(raw):
    """Return physical line boundaries; only CR, LF and CRLF end lines."""
    offsets = [0]
    for match in re.finditer(b'\r\n|\r|\n', raw):
        if len(offsets) > MAX_PHYSICAL_LINES:
            raise ValueError(f'line {MAX_PHYSICAL_LINES + 1}: export exceeds physical line limit')
        offsets.append(match.end())
    if offsets[-1] != len(raw):
        if len(offsets) > MAX_PHYSICAL_LINES:
            raise ValueError(f'line {MAX_PHYSICAL_LINES + 1}: export exceeds physical line limit')
        offsets.append(len(raw))
    return offsets


def _span(raw, offsets, start, end):
    byte_start, byte_end = offsets[start - 1], offsets[end]
    return dict(line_start=start, line_end=end, byte_start=byte_start,
                byte_end=byte_end,
                sha256=hashlib.sha256(raw[byte_start:byte_end]).hexdigest())


def parse_export(raw: bytes, id_column='record_id', locator_column='source_locator'):
    """Return literal CSV rows, byte provenance and non-destructive ID warnings.

    No identifiers, locators or cells are normalized. Whitespace-only required
    values are rejected, but whitespace around nonblank values is preserved.
    Parser errors never include input cell contents. The interpreter's existing
    CSV field-size limit is respected and is never changed by this function.
    """
    if not isinstance(raw, bytes):
        raise ValueError('line 1: export must be bytes')
    if not raw:
        raise ValueError('line 1: export is empty')
    if len(raw) > MAX_EXPORT_BYTES:
        raise ValueError('line 1: export exceeds byte limit')
    offsets = _line_offsets(raw)
    if b'\x00' in raw:
        nul_offset = raw.index(b'\x00')
        line = 1 + sum(end <= nul_offset for end in offsets[1:])
        raise ValueError(f'line {line}: NUL bytes are not allowed')
    try:
        text = raw.decode('utf-8', errors='strict')
    except UnicodeDecodeError as exc:
        line = 1 + sum(end <= exc.start for end in offsets[1:])
        raise ValueError(f'line {line}: export must be strict UTF-8') from None
    if text.startswith('\ufeff'):
        text = text[1:]
    for name in (id_column, locator_column):
        if not isinstance(name, str) or not name.strip():
            raise ValueError('line 1: chosen column names must be nonblank strings')

    result = dict(headers=[], header_source_span=None, record_rows=[],
                  ignored_blank_spans=[], duplicate_record_ids=[], locator_conflicts=[])
    reader = csv.reader(io.StringIO(text, newline=''), dialect='excel', strict=True)
    headers = None
    occurrences = {}
    while True:
        start = reader.line_num + 1
        try:
            values = next(reader)
        except StopIteration:
            break
        except csv.Error:
            raise ValueError(f'line {max(start, reader.line_num)}: malformed CSV or CSV field-size limit exceeded') from None
        end = reader.line_num
        span = _span(raw, offsets, start, end)
        # csv.reader returns [] only for an empty physical CSV row. A quoted
        # empty cell, delimiter-only row or whitespace row must not be skipped.
        if not values:
            result['ignored_blank_spans'].append(span)
            continue
        if headers is None:
            if any(not value.strip() for value in values):
                raise ValueError(f'line {start}: blank CSV header')
            if len(set(values)) != len(values):
                raise ValueError(f'line {start}: duplicate CSV header')
            if id_column not in values or locator_column not in values:
                raise ValueError(f'line {start}: required chosen column is missing')
            headers = values
            result['headers'] = list(headers)
            result['header_source_span'] = span
            continue
        if len(values) != len(headers):
            raise ValueError(f'line {start}: CSV row width does not match header')
        original = dict(zip(headers, values))
        record_id, locator = original[id_column], original[locator_column]
        if not record_id.strip() or not locator.strip():
            raise ValueError(f'line {start}: required value is blank')
        if len(result['record_rows']) >= MAX_RECORDS:
            raise ValueError(f'line {start}: export exceeds record limit')
        candidate_id = f"csv-row-{len(result['record_rows']) + 1:06d}"
        row = dict(candidate_id=candidate_id, record_id=record_id,
                   source_locator=locator, original_values=original, source_span=span)
        result['record_rows'].append(row)
        occurrences.setdefault(record_id, []).append(row)
    if headers is None:
        raise ValueError('line 1: export has no CSV header')
    for record_id, rows in occurrences.items():
        if len(rows) < 2:
            continue
        candidates = [row['candidate_id'] for row in rows]
        result['duplicate_record_ids'].append(dict(record_id=record_id, candidate_ids=candidates))
        locators = sorted({row['source_locator'] for row in rows})
        if len(locators) > 1:
            result['locator_conflicts'].append(dict(record_id=record_id,
                source_locators=locators, candidate_ids=list(candidates)))
    return result
