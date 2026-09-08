"""Study-specific text classification helpers.

Pure functions only: no database, filesystem, pandas, or logging dependencies.

Metric normalization belongs to ``michr-text-post-editing``. This module owns
only the study-posting product policy used to classify cosmetic equivalence and
the blank-text predicate used by field requiredness rules.

``normalize_text_for_equivalence`` must never preprocess a metric input. Doing
so would hide textual changes the metrics are intended to measure.
"""

import unicodedata

_COSMETIC_CATEGORY_PREFIXES = frozenset({"P", "S"})


def normalize_text_for_equivalence(text: str) -> str:
    """Apply the study's broad cosmetic-equivalence transformation.

    Processing, in order:

    1. Unicode compatibility decomposition using ``NFKD``.
    2. Unicode-aware case folding.
    3. Removal of combining marks.
    4. Replacement of punctuation and symbols with spaces.
    5. Whitespace collapsing and trimming.

    Parameters
    ----------
    text
        Text to transform.

    Returns
    -------
    str
        Transformed text suitable only for equality comparison.
    """
    normalized = unicodedata.normalize("NFKD", text)
    normalized = normalized.casefold()

    normalized = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )

    normalized = "".join(
        " "
        if unicodedata.category(character)[0] in _COSMETIC_CATEGORY_PREFIXES
        else character
        for character in normalized
    )

    return " ".join(normalized.split())


def is_blank_text(text: str) -> bool:
    """Return whether text contains no non-whitespace characters."""
    return not text.strip()
