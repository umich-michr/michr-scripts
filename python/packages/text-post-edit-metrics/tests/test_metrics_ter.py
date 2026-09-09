"""Tests for TER-derived metrics."""

import unicodedata

import pytest

from text_post_edit_metrics.metrics import calculate_ter_metrics
from text_post_edit_metrics.normalization import clamp01


def test_identical_text_has_zero_ter_and_full_effort_saved() -> None:
    result = calculate_ter_metrics(
        "We analyze the data.",
        "We analyze the data.",
    )

    assert result.ter_rate == pytest.approx(0.0)
    assert result.effort_saved_raw == pytest.approx(1.0)
    assert result.effort_saved == pytest.approx(1.0)


def test_effort_saved_is_one_minus_ter() -> None:
    """The transformation must remain exactly 1 - TER."""
    result = calculate_ter_metrics(
        "We analyze data.",
        "We carefully analyze clinical data.",
    )

    assert result.effort_saved_raw == pytest.approx(1.0 - result.ter_rate)
    assert result.effort_saved == pytest.approx(clamp01(result.effort_saved_raw))


def test_single_insertion_produces_expected_rate() -> None:
    """One inserted word against a six-word reference is one sixth."""
    result = calculate_ter_metrics(
        "Support analysis of research data.",
        "Support analysis of clinical research data.",
    )

    assert result.ter_rate == pytest.approx(1.0 / 6.0)


def test_bounded_score_stays_within_zero_and_one() -> None:
    result = calculate_ter_metrics("one two three four five six", "unrelated")

    assert 0.0 <= result.effort_saved <= 1.0


def test_costly_suggestion_retains_negative_raw_score() -> None:
    """Clamping must not discard evidence of a costly suggestion."""
    result = calculate_ter_metrics("one two three four five six", "unrelated")

    assert result.ter_rate > 1.0
    assert result.effort_saved_raw < 0.0
    assert result.effort_saved == pytest.approx(0.0)


def test_ter_is_case_insensitive_under_study_configuration() -> None:
    """Documented configuration: case_sensitive=False."""
    result = calculate_ter_metrics("DATA ANALYSIS", "data analysis")

    assert result.ter_rate == pytest.approx(0.0)
    assert result.effort_saved == pytest.approx(1.0)


def test_unicode_equivalent_text_is_treated_as_identical() -> None:
    composed = unicodedata.normalize("NFC", "cafe\u0301")
    decomposed = unicodedata.normalize("NFD", "cafe\u0301")

    assert composed != decomposed

    result = calculate_ter_metrics(composed, decomposed)

    assert result.ter_rate == pytest.approx(0.0)
    assert result.effort_saved == pytest.approx(1.0)


@pytest.mark.parametrize(
    "final",
    ["", "   ", "\n\t"],
    ids=["empty", "spaces", "tabs-newlines"],
)
def test_blank_final_text_is_rejected(final: str) -> None:
    """The reference-length denominator would be zero."""
    with pytest.raises(ValueError, match="final text contains no words"):
        calculate_ter_metrics("suggestion", final)
