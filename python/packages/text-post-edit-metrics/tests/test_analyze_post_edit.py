"""Tests for analyze_post_edit, the combined public metric entry point."""

import unicodedata

import pytest

from text_post_edit_metrics.metrics import (
    analyze_post_edit,
    calculate_character_metrics,
    calculate_soft_word_metrics,
    calculate_ter_metrics,
)
from text_post_edit_metrics.normalization import normalize_metric_text


def test_identical_text_returns_full_scores() -> None:
    text = "Research Assistant"

    result = analyze_post_edit(
        suggestion=text,
        final=text,
    )

    assert result.ter_rate == pytest.approx(0.0)
    assert result.ter_effort_saved_raw == pytest.approx(1.0)
    assert result.ter_effort_saved == pytest.approx(1.0)

    assert result.character_edit_distance == 0
    assert result.character_effort_saved_raw == pytest.approx(1.0)
    assert result.character_effort_saved == pytest.approx(1.0)

    assert result.soft_word_edit_distance == pytest.approx(0.0)
    assert result.soft_word_effort_saved_raw == pytest.approx(1.0)
    assert result.soft_word_effort_saved == pytest.approx(1.0)

    assert result.estimated_characters_saved == pytest.approx(len(text))

    assert result.suggestion_character_count == len(text)
    assert result.final_character_count == len(text)
    assert result.suggestion_word_count == 2
    assert result.final_word_count == 2


def test_combined_result_matches_individual_metric_functions() -> None:
    """Guards against a field being populated from the wrong calculation."""
    suggestion = "Support analysis of research data."
    final = "Support analysis of clinical research data."

    combined = analyze_post_edit(
        suggestion=suggestion,
        final=final,
    )

    ter = calculate_ter_metrics(suggestion, final)
    character = calculate_character_metrics(suggestion, final)
    soft_word = calculate_soft_word_metrics(suggestion, final)

    assert combined.ter_rate == pytest.approx(ter.ter_rate)
    assert combined.ter_effort_saved_raw == pytest.approx(ter.effort_saved_raw)
    assert combined.ter_effort_saved == pytest.approx(ter.effort_saved)

    assert combined.character_edit_distance == character.distance
    assert combined.character_effort_saved_raw == pytest.approx(
        character.effort_saved_raw
    )
    assert combined.character_effort_saved == pytest.approx(character.effort_saved)

    assert combined.soft_word_edit_distance == pytest.approx(soft_word.distance)
    assert combined.soft_word_effort_saved_raw == pytest.approx(
        soft_word.effort_saved_raw
    )
    assert combined.soft_word_effort_saved == pytest.approx(soft_word.effort_saved)


def test_character_and_soft_word_are_case_sensitive_but_ter_is_not() -> None:
    """The metric families deliberately use different case configurations."""
    result = analyze_post_edit(
        suggestion="Data Analysis",
        final="data analysis",
    )

    assert result.ter_rate == pytest.approx(0.0)
    assert result.character_edit_distance > 0
    assert result.soft_word_edit_distance > 0.0


def test_estimated_characters_saved_uses_character_distance() -> None:
    result = analyze_post_edit(
        suggestion="The data",
        final="The dataset",
    )

    expected = max(
        0.0,
        float(result.final_character_count - result.character_edit_distance),
    )

    assert result.estimated_characters_saved == pytest.approx(expected)


def test_estimated_characters_saved_is_bounded_below_at_zero() -> None:
    result = analyze_post_edit(
        suggestion="an extremely long and entirely unrelated suggestion",
        final="short",
    )

    assert result.estimated_characters_saved == pytest.approx(0.0)


def test_counts_are_reported_after_unicode_normalization() -> None:
    suggestion = unicodedata.normalize("NFD", "café research")
    final = unicodedata.normalize("NFC", "café research project")

    result = analyze_post_edit(
        suggestion=suggestion,
        final=final,
    )

    normalized_suggestion = normalize_metric_text(suggestion)
    normalized_final = normalize_metric_text(final)

    assert result.suggestion_character_count == len(normalized_suggestion)
    assert result.final_character_count == len(normalized_final)
    assert result.suggestion_word_count == len(normalized_suggestion.split())
    assert result.final_word_count == len(normalized_final.split())


def test_empty_suggestion_is_allowed_and_scores_zero() -> None:
    final = "A final response"

    result = analyze_post_edit(
        suggestion="",
        final=final,
    )

    assert result.suggestion_character_count == 0
    assert result.suggestion_word_count == 0
    assert result.character_edit_distance == len(final)
    assert result.character_effort_saved == pytest.approx(0.0)
    assert result.soft_word_effort_saved == pytest.approx(0.0)


def test_non_string_suggestion_is_rejected() -> None:
    with pytest.raises(TypeError, match="suggestion must be a string"):
        analyze_post_edit(
            suggestion=None,  # type: ignore[arg-type]
            final="final",
        )


def test_non_string_final_is_rejected() -> None:
    with pytest.raises(TypeError, match="final must be a string"):
        analyze_post_edit(
            suggestion="suggestion",
            final=None,  # type: ignore[arg-type]
        )


def test_empty_final_is_rejected() -> None:
    with pytest.raises(ValueError, match="final text must not be empty"):
        analyze_post_edit(
            suggestion="suggestion",
            final="",
        )


@pytest.mark.parametrize(
    "final",
    ["   ", "\n\t"],
    ids=["spaces", "tabs-newlines"],
)
def test_whitespace_only_final_is_rejected(final: str) -> None:
    with pytest.raises(ValueError, match="at least one word"):
        analyze_post_edit(
            suggestion="suggestion",
            final=final,
        )
