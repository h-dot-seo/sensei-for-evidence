"""Conservative text escaping for spreadsheet-facing CSV cells."""


def safe_csv_cell(value):
    text = str(value)
    # Escape whitespace prefixes too: consumers may trim or interpret controls
    # before formula detection. Preserve the original text after the apostrophe.
    if text and (text[0] in '=+-@' or text[0].isspace()):
        return "'" + text
    return text
