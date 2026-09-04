"""Tests for Unicode normalization, cosmetic equivalence, and helpers."""

import unicodedata

import pytest

from study_posting_ai_analysis.text_normalization import (
    clamp01,
    count_whitespace_tokens,
    is_blank_text,
    normalize_text_for_equivalence,
    unicode_nfc_normalize_text,
)


def _assert_equal(
    actual: object, expected: object, *, message: str | None = None
) -> None:
    if actual != expected:
        raise AssertionError(message or f"Expected {expected!r}, got {actual!r}")


# ---------------------------------------------------------------------------
# unicode_nfc_normalize_text
# ---------------------------------------------------------------------------


def test_composed_and_decomposed_forms_become_equal() -> None:
    """NFC is what allows the two spellings of "café" to compare as equal.

    Both forms are constructed with unicodedata rather than written as source
    literals, because an editor may silently normalize the file on save.
    """
    composed = unicodedata.normalize("NFC", "cafe\u0301")
    decomposed = unicodedata.normalize("NFD", "cafe\u0301")

    assert composed != decomposed, "Test setup failed: NFC and NFD forms are identical"
    assert len(decomposed) == len(composed) + 1

    assert unicode_nfc_normalize_text(composed) == unicode_nfc_normalize_text(
        decomposed
    )


def test_case_is_preserved_by_default() -> None:
    _assert_equal(unicode_nfc_normalize_text("Data Analysis"), "Data Analysis")


def test_case_folding_is_optional() -> None:
    _assert_equal(
        unicode_nfc_normalize_text("Data Analysis", case_sensitive=False),
        "data analysis",
    )


@pytest.mark.parametrize(
    "text",
    ["  leading and trailing  ", "with-hyphen", "punctuation!", "a  b"],
    ids=["whitespace", "hyphen", "punctuation", "double-space"],
)
def test_punctuation_and_whitespace_are_preserved(text: str) -> None:
    """Metric inputs must retain real differences, unlike the cosmetic rule."""
    _assert_equal(unicode_nfc_normalize_text(text), text)


# ---------------------------------------------------------------------------
# normalize_text_for_equivalence
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Hello, World!", "hello world"),
        ("  leading and trailing spaces  ", "leading and trailing spaces"),
        ("Multiple    spaces here", "multiple spaces here"),
        (
            "Text with-hyphens and.punctuation!",
            "text with hyphens and punctuation",
        ),
        (
            "Numbers 123 and symbols @#$ are removed.",
            "numbers 123 and symbols are removed",
        ),
        ("Résumé éàç", "resume eac"),
        ("  Hello\n\tWorld  ", "hello world"),
        ("  ", ""),
        ("", ""),
    ],
    ids=[
        "case-and-punctuation",
        "surrounding-whitespace",
        "repeated-spaces",
        "hyphen-and-period",
        "symbols-removed",
        "diacritics-stripped",
        "tabs-and-newlines",
        "whitespace-only",
        "empty",
    ],
)
def test_cosmetic_equivalence_transformation(text: str, expected: str) -> None:
    assert normalize_text_for_equivalence(text) == expected


def test_hyphenated_forms_are_split_by_the_cosmetic_rule() -> None:
    """Punctuation becomes a space, so hyphenation is cosmetic for matching.

    This differs deliberately from soft-word tokenization, where a hyphenated
    form remains a single token.
    """
    assert normalize_text_for_equivalence(
        "well-known"
    ) == normalize_text_for_equivalence("well known")


def test_cosmetic_rule_does_not_equate_substantively_different_text() -> None:
    """The rule is broad but must not collapse different words."""
    assert normalize_text_for_equivalence(
        "Research Assistant"
    ) != normalize_text_for_equivalence("Research Coordinator")


def test_nfkd_expands_compatibility_characters() -> None:
    """NFKD, unlike NFC, decomposes compatibility forms such as the ligature."""
    assert normalize_text_for_equivalence("ﬁle") == "file"


# ---------------------------------------------------------------------------
# is_blank_text
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", True),
        ("   ", True),
        ("\n\t ", True),
        ("a", False),
        ("  a  ", False),
        ("0", False),
    ],
    ids=["empty", "spaces", "tabs-newlines", "letter", "padded", "zero"],
)
def test_is_blank_text(text: str, expected: bool) -> None:
    assert is_blank_text(text) is expected


# ---------------------------------------------------------------------------
# count_whitespace_tokens
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", 0),
        ("   ", 0),
        ("one", 1),
        ("one two three", 3),
        ("one   two\nthree", 3),
        ("  padded  ", 1),
    ],
    ids=["empty", "whitespace", "single", "three", "mixed-whitespace", "padded"],
)
def test_count_whitespace_tokens(text: str, expected: int) -> None:
    assert count_whitespace_tokens(text) == expected


def test_punctuation_stays_attached_to_tokens() -> None:
    """Documented tokenization behavior: "data." is one token, not two."""
    assert count_whitespace_tokens("We analyze the data.") == 4


def test_hyphenated_form_is_one_token() -> None:
    assert count_whitespace_tokens("well-known result") == 2


# ---------------------------------------------------------------------------
# clamp01
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (-5.0, 0.0),
        (-0.001, 0.0),
        (0.0, 0.0),
        (0.5, 0.5),
        (1.0, 1.0),
        (1.001, 1.0),
        (42.0, 1.0),
    ],
    ids=[
        "far-negative",
        "just-negative",
        "zero",
        "midpoint",
        "one",
        "just-above-one",
        "far-above-one",
    ],
)
def test_clamp01(value: float, expected: float) -> None:
    assert clamp01(value) == pytest.approx(expected)
