"""Unicode normalization, cosmetic equivalence, and small numeric helpers.

Pure functions only: no database, filesystem, pandas, or logging
dependencies.

Two distinct normalizations live here and must not be confused:

``unicode_nfc_normalize_text``
    Applied to every metric input. Preserves punctuation, diacritics, and
    whitespace so that real edits remain measurable.

``normalize_text_for_equivalence``
    Applied only when classifying a result as ``COSMETIC_EQUIVALENT``. It is
    deliberately broad and would hide genuine edits if used upstream of a
    metric.

See docs/analysis-specification.md sections 6 and 9.
"""

import unicodedata

# Unicode general-category prefixes treated as cosmetic by the equivalence
# transformation: P covers punctuation, S covers symbols.
_COSMETIC_CATEGORY_PREFIXES = frozenset({"P", "S"})


def unicode_nfc_normalize_text(
    text: str,
    *,
    case_sensitive: bool = True,
) -> str:
    r"""Normalize Unicode representation for edit-distance calculations.

    Punctuation, diacritics, and whitespace are preserved. Case is preserved
    unless ``case_sensitive`` is ``False``.

    Composed and decomposed spellings of the same character are made equal, so
    ``"café"`` and ``"cafe\\u0301"`` compare as identical.

    Parameters
    ----------
    text
        Text to normalize.
    case_sensitive
        When ``False``, Unicode-aware case folding is applied.

    Returns
    -------
    str
        The NFC-normalized text.
    """
    normalized_text = unicodedata.normalize("NFC", text)

    if not case_sensitive:
        normalized_text = normalized_text.casefold()

    return normalized_text


def normalize_text_for_equivalence(text: str) -> str:
    """Apply the study's broad cosmetic-equivalence rule.

    Processing, in order:

    1. Unicode compatibility decomposition using ``NFKD``, so that accented
       characters become a base character followed by combining marks.
    2. Unicode-aware case folding.
    3. Removal of combining marks, including decomposed diacritics.
    4. Replacement of punctuation and symbols with spaces.
    5. Whitespace collapsing and trimming.

    This function is used **only** for ``MatchType.COSMETIC_EQUIVALENT``
    classification. It must never be used as preprocessing for an edit-distance
    metric, because doing so would hide actual textual edits.

    Parameters
    ----------
    text
        Text to transform.

    Returns
    -------
    str
        The transformed text, suitable only for equality comparison.
    """
    # Decompose so that accents become separate combining marks, converting
    # "é" into "e" followed by a combining acute accent.
    normalized = unicodedata.normalize("NFKD", text)

    normalized = normalized.casefold()

    # Drop accents and other combining marks.
    normalized = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )

    # Replace punctuation and symbols with spaces so that "with-hyphens" and
    # "with hyphens" become equal.
    normalized = "".join(
        " "
        if unicodedata.category(character)[0] in _COSMETIC_CATEGORY_PREFIXES
        else character
        for character in normalized
    )

    # Collapse spaces, tabs, and newlines, and trim the result.
    return " ".join(normalized.split())


def is_blank_text(text: str) -> bool:
    """Return whether text contains no non-whitespace characters.

    Parameters
    ----------
    text
        Text to inspect.

    Returns
    -------
    bool
        ``True`` when the text is empty or whitespace only.
    """
    return not text.strip()


def count_whitespace_tokens(text: str) -> int:
    """Count words using whitespace tokenization.

    Punctuation remains attached to adjacent tokens and hyphenated forms remain
    a single token. Repeated whitespace does not affect the count.

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
    """Restrict a value to the inclusive interval ``[0, 1]``.

    Used to produce bounded reporting scores from raw effort-saved values,
    which may be negative. The raw value is always retained alongside the
    bounded one so that costly suggestions remain identifiable.

    Parameters
    ----------
    value
        Raw score.

    Returns
    -------
    float
        The value bounded to ``[0, 1]``.
    """
    return min(1.0, max(0.0, value))
