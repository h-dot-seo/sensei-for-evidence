"""Strict shared JSON decoding for reproducible offline inputs."""
import json
import math
import sys


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
