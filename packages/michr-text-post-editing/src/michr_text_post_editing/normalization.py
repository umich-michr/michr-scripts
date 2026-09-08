"""Text normalization and numeric helpers for post-editing metrics.

Pure functions only: no database, filesystem, pandas, logging, or
application-specific business rules.

Metric inputs use Unicode Normalization Form C (NFC). Punctuation, diacritics,
and whitespace are preserved so that actual textual edits remain measurable.
"""

import unicodedata


def normalize_metric_text(
    text: str,
    *,
    case_sensitive: bool = True,
) -> str:
    """Normalize text for post-editing metric calculations.

    Unicode NFC normalization makes canonically equivalent strings comparable
    while preserving punctuation, diacritics, and whitespace. Case is
    preserved unless ``case_sensitive`` is ``False``.

    Parameters
    ----------
    text
        Text to normalize.
    case_sensitive
        Whether capitalization differences should be preserved.

    Returns
    -------
    str
        NFC-normalized text, optionally case-folded.
    """
    normalized_text = unicodedata.normalize("NFC", text)

    if not case_sensitive:
        normalized_text = normalized_text.casefold()

    return normalized_text


def count_whitespace_tokens(text: str) -> int:
    """Count tokens using whitespace boundaries.

    Punctuation remains attached to adjacent tokens, hyphenated forms remain
    one token, and repeated whitespace does not affect the count.

    Parameters
    ----------
    text
        Text to tokenize.

    Returns
    -------
    int
        Number of whitespace-delimited tokens.
    """
    return len(text.split())


def clamp01(value: float) -> float:
    """Bound a numeric value to the inclusive interval ``[0, 1]``.

    Raw post-editing scores may be negative and are retained separately.
    Bounding is used only for reporting values.

    Parameters
    ----------
    value
        Raw score.

    Returns
    -------
    float
        ``value`` bounded to ``[0, 1]``.
    """
    return min(1.0, max(0.0, value))
