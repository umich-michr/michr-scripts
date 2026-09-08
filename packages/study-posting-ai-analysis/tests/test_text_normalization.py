"""Tests for study-specific text classification helpers."""

import pytest

from study_posting_ai_analysis.text_normalization import (
    is_blank_text,
    normalize_text_for_equivalence,
)


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
        "symbols",
        "diacritics",
        "tabs-and-newlines",
        "whitespace-only",
        "empty",
    ],
)
def test_cosmetic_equivalence_transformation(
    text: str,
    expected: str,
) -> None:
    assert normalize_text_for_equivalence(text) == expected


def test_cosmetic_rule_equates_hyphenated_and_spaced_forms() -> None:
    assert normalize_text_for_equivalence(
        "well-known"
    ) == normalize_text_for_equivalence("well known")


def test_cosmetic_rule_does_not_equate_different_words() -> None:
    assert normalize_text_for_equivalence(
        "Research Assistant"
    ) != normalize_text_for_equivalence("Research Coordinator")


def test_nfkd_expands_compatibility_characters() -> None:
    assert normalize_text_for_equivalence("ﬁle") == "file"


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
