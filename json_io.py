"""Strict shared JSON decoding for reproducible offline inputs."""
import json
import math
import sys
import unicodedata


def parse_json(raw):
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode('utf-8')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key: ' + ascii(key))
            result[key] = value
        return result

    def invalid(value):
        raise ValueError('invalid JSON numeric constant: ' + value)

    def finite_float(value):
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError('JSON number exceeds finite float range')
        return parsed

    parsed = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid,
                        parse_float=finite_float)
    pending = [parsed]
    while pending:
        value = pending.pop()
        if isinstance(value, str):
            if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
                raise ValueError('JSON strings must not contain unpaired surrogate code points')
        elif isinstance(value, dict):
            pending.extend(value.keys())
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
    return parsed


def configure_utf8_stdio():
    """Keep JSON CLI output UTF-8 even when redirected on non-UTF-8 hosts."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors=getattr(stream, 'errors', None) or 'strict')


def canonical_json_bytes(value):
    """Sorted compact UTF-8 representation for semantic input fingerprints."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(',', ':')).encode('utf-8')


def quoted_display(value):
    """Quote supplied values without allowing control/format characters to spoof labels."""
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return ''.join(json.dumps(char, ensure_ascii=True)[1:-1]
                   if unicodedata.category(char) in ('Cc', 'Cf', 'Zl', 'Zp') else char
                   for char in encoded)
