"""Tests for character-level Levenshtein metrics."""

import unicodedata

import pytest

from study_posting_ai_analysis.metrics import calculate_character_metrics
from study_posting_ai_analysis.text_normalization import clamp01


@pytest.mark.parametrize(
    ("suggestion", "final", "expected_distance"),
    [
        ("data", "data", 0),
        ("data", "date", 1),
        ("", "data", 4),
        ("The data", "The dataset", 3),
    ],
    ids=["identical", "substitution", "empty-suggestion", "suffix-added"],
)
def test_character_distance(
    suggestion: str,
    final: str,
    expected_distance: int,
) -> None:
    result = calculate_character_metrics(suggestion, final)

    assert result.distance == expected_distance


def test_identical_text_has_full_score() -> None:
    result = calculate_character_metrics("data", "data")

    assert result.distance == 0
    assert result.effort_saved_raw == pytest.approx(1.0)
    assert result.effort_saved == pytest.approx(1.0)


def test_score_formula_uses_final_character_count() -> None:
    """Score is 1 - distance / len(final), not the suggestion length."""
    final = "The dataset"
    result = calculate_character_metrics("The data", final)

    expected_raw = 1.0 - result.distance / len(final)

    assert result.effort_saved_raw == pytest.approx(expected_raw)
    assert result.effort_saved == pytest.approx(clamp01(expected_raw))


def test_one_substitution_in_four_characters_scores_three_quarters() -> None:
    result = calculate_character_metrics("data", "date")

    assert result.effort_saved == pytest.approx(0.75)


def test_empty_suggestion_requires_inserting_every_character() -> None:
    result = calculate_character_metrics("", "data")

    assert result.distance == 4
    assert result.effort_saved_raw == pytest.approx(0.0)
    assert result.effort_saved == pytest.approx(0.0)


def test_costly_suggestion_retains_negative_raw_score() -> None:
    """Clamping must not discard evidence that editing exceeded the baseline."""
    result = calculate_character_metrics("a very long suggestion", "x")

    assert result.effort_saved_raw < 0.0
    assert result.effort_saved == pytest.approx(0.0)


def test_case_is_preserved_by_default() -> None:
    """The study-level configuration is case-sensitive, unlike TER."""
    result = calculate_character_metrics("Data", "data")

    assert result.distance == 1


def test_case_sensitivity_is_configurable() -> None:
    insensitive = calculate_character_metrics(
        "Data",
        "data",
        case_sensitive=False,
    )

    assert insensitive.distance == 0
    assert insensitive.effort_saved == pytest.approx(1.0)


def test_unicode_equivalent_text_has_zero_distance() -> None:
    composed = unicodedata.normalize("NFC", "cafe\u0301")
    decomposed = unicodedata.normalize("NFD", "cafe\u0301")

    assert composed != decomposed

    result = calculate_character_metrics(composed, decomposed)

    assert result.distance == 0
    assert result.effort_saved == pytest.approx(1.0)


def test_empty_final_text_is_rejected() -> None:
    """The denominator would be zero."""
    with pytest.raises(ValueError, match="final text is empty"):
        calculate_character_metrics("data", "")
