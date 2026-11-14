"""Shared strict import-review and whole-application replay checks, without domain decisions or IO."""
from challenge_intake import _date, _normalized, _schema, REVIEW_FIELDS
from json_io import canonical_json_bytes


def validate_import_review(document, action, byte_limit):
    review = _normalized(document, byte_limit, 'import review')
    _schema(review, REVIEW_FIELDS, 'import review')
    if any(not isinstance(review[key], str) or not review[key].strip() for key in REVIEW_FIELDS - {'schema_version'}):
        raise ValueError('import-review fields must be nonblank supplied strings')
    if review['decision'] != action:
        raise ValueError('import review decision must be '+action)
    _date(review['reviewed_at'], 'import reviewed_at')
    return review


def replay_application(protocol, application, kind, assembler, byte_limit):
    """Reconstruct through the caller's domain assembler and compare every recorded field."""
    record = _normalized(application, byte_limit, 'application')
    _schema(record, {'schema_version','kind','receipt','protocol_candidate'}, 'application')
    if (record['kind'] != kind or not isinstance(record['receipt'], dict)
            or not {'candidate_document','assertion'} <= set(record['receipt'])):
        raise ValueError('invalid detached reviewed application')
    replay = assembler(protocol, record['receipt']['candidate_document'], record['receipt']['assertion'])
    if canonical_json_bytes(replay) != canonical_json_bytes(record):
        raise ValueError('application differs from exact original-input replay')
    return replay
