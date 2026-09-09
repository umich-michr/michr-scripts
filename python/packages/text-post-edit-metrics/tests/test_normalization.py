"""Tests for generic metric text normalization and numeric helpers."""

import unicodedata

import pytest

from text_post_edit_metrics.normalization import (
    clamp01,
    count_whitespace_tokens,
    normalize_metric_text,
)


def test_canonically_equivalent_text_normalizes_identically() -> None:
    """NFC makes composed and decomposed spellings compare as equal."""
    composed = unicodedata.normalize("NFC", "cafe\u0301")
    decomposed = unicodedata.normalize("NFD", "cafe\u0301")

    assert composed != decomposed
    assert normalize_metric_text(composed) == normalize_metric_text(decomposed)


def test_case_is_preserved_by_default() -> None:
    assert normalize_metric_text("Data Analysis") == "Data Analysis"


def test_case_folding_can_be_requested() -> None:
    assert (
        normalize_metric_text(
            "Data Analysis",
            case_sensitive=False,
        )
        == "data analysis"
    )


@pytest.mark.parametrize(
    "text",
    [
        "  leading and trailing  ",
        "with-hyphen",
        "punctuation!",
        "a  b",
        "Résumé",
    ],
    ids=[
        "surrounding-whitespace",
        "hyphen",
        "punctuation",
        "repeated-space",
        "diacritic",
    ],
)
def test_metric_normalization_preserves_textual_differences(text: str) -> None:
    """NFC must not hide punctuation, whitespace, or diacritic differences."""
    assert normalize_metric_text(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", 0),
        ("   ", 0),
        ("one", 1),
        ("one two three", 3),
        ("one   two\nthree", 3),
        ("well-known result", 2),
        ("data.", 1),
    ],
    ids=[
        "empty",
        "whitespace-only",
        "single",
        "three",
        "mixed-whitespace",
        "hyphenated",
        "punctuation-attached",
    ],
)
def test_count_whitespace_tokens(text: str, expected: int) -> None:
    assert count_whitespace_tokens(text) == expected


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
