"""Tests for immutable readability result validation."""

from math import inf, nan

import pytest

from text_readability_metrics import (
    InvalidReadabilityResultError,
    ReadabilityResult,
)


def valid_values() -> dict[str, object]:
    """Return one complete valid readability result mapping."""
    return {
        "flesch_kincaid_grade": 1.0,
        "automated_readability_index": 2.0,
        "coleman_liau_index": 3.0,
        "gunning_fog": 4.0,
        "dale_chall_readability_score": 5.0,
        "estimated_reading_time_seconds": 6.0,
        "sentence_count": 7,
        "word_count": 8,
        "syllable_count": 9,
        "letter_count": 10,
        "polysyllable_count": 11,
    }


def build_result(**overrides: object) -> ReadabilityResult:
    """Build a result with selected values replaced."""
    values = valid_values()
    values.update(overrides)
    return ReadabilityResult(**values)  # type: ignore[arg-type]


def test_result_normalizes_integer_score_values_to_float() -> None:
    result = build_result(
        flesch_kincaid_grade=-1,
        estimated_reading_time_seconds=0,
    )

    assert result.flesch_kincaid_grade == -1.0
    assert type(result.flesch_kincaid_grade) is float
    assert result.estimated_reading_time_seconds == 0.0
    assert type(result.estimated_reading_time_seconds) is float


@pytest.mark.parametrize(
    "field_name",
    [
        "flesch_kincaid_grade",
        "automated_readability_index",
        "coleman_liau_index",
        "gunning_fog",
        "dale_chall_readability_score",
        "estimated_reading_time_seconds",
    ],
)
@pytest.mark.parametrize("value", [True, "1.0", None])
def test_score_fields_require_numbers(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(
        InvalidReadabilityResultError,
        match=rf"{field_name} must be a finite number",
    ):
        build_result(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "flesch_kincaid_grade",
        "automated_readability_index",
        "coleman_liau_index",
        "gunning_fog",
        "dale_chall_readability_score",
        "estimated_reading_time_seconds",
    ],
)
@pytest.mark.parametrize("value", [nan, inf, -inf])
def test_score_fields_require_finite_numbers(
    field_name: str,
    value: float,
) -> None:
    with pytest.raises(
        InvalidReadabilityResultError,
        match=rf"{field_name} must be a finite number",
    ):
        build_result(**{field_name: value})


def test_estimated_reading_time_must_not_be_negative() -> None:
    with pytest.raises(
        InvalidReadabilityResultError,
        match="estimated_reading_time_seconds must not be negative",
    ):
        build_result(estimated_reading_time_seconds=-0.1)


@pytest.mark.parametrize(
    "field_name",
    [
        "sentence_count",
        "word_count",
        "syllable_count",
        "letter_count",
        "polysyllable_count",
    ],
)
@pytest.mark.parametrize("value", [True, 1.5, "1", None])
def test_count_fields_require_integers(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(
        InvalidReadabilityResultError,
        match=rf"{field_name} must be a nonnegative integer",
    ):
        build_result(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "sentence_count",
        "word_count",
        "syllable_count",
        "letter_count",
        "polysyllable_count",
    ],
)
def test_count_fields_must_not_be_negative(field_name: str) -> None:
    with pytest.raises(
        InvalidReadabilityResultError,
        match=rf"{field_name} must be a nonnegative integer",
    ):
        build_result(**{field_name: -1})
