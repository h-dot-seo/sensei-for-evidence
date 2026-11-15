"""Presentation-only CLI error categories; no file reads, parsing or validation."""
import json
from json_io import JsonNestingError, quoted_display


def fail(parser, tool, stage, label, error):
    """Exit 1 with a static argument label; never print filesystem exception text.

    Caller-supplied validation details are quoted, not confidentially redacted.
    Labels/stages must be code constants, never paths or supplied identifiers.
    """
    if stage == 'output':
        category = 'output-exists' if isinstance(error, FileExistsError) else 'output-error'
    elif isinstance(error, OSError):
        category = 'input-unreadable'
    elif isinstance(error, JsonNestingError):
        category = 'input-too-complex'
    elif isinstance(error, (json.JSONDecodeError, UnicodeError)):
        category = 'input-not-json'
    else:
        category = 'input-invalid'
    if isinstance(error, OSError):
        detail = 'output destination refused' if stage == 'output' else 'input could not be read'
    elif isinstance(error, KeyError):
        detail = 'required field is missing'
    elif isinstance(error, UnicodeError):
        detail = 'UTF-8 text is required'
    else:
        detail = str(error)
    parser.exit(1, tool + ' error: ' + category + ': ' + label + ': ' + quoted_display(detail) + '\n')
