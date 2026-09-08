"""Tests for analyze_selected_suggestion, the combined metric entry point."""

import pytest

from study_posting_ai_analysis.metrics import (
    analyze_selected_suggestion,
    calculate_character_metrics,
    calculate_soft_word_metrics,
    calculate_ter_metrics,
)
from study_posting_ai_analysis.text_normalization import unicode_nfc_normalize_text


def test_identical_suggestion_returns_full_scores() -> None:
    text = "Research Assistant"

    result = analyze_selected_suggestion(
        field_name="title",
        suggestion=text,
        final=text,
    )

    assert result.field_name == "title"

    assert result.ter_rate == pytest.approx(0.0)
    assert result.ter_effort_saved_raw == pytest.approx(1.0)
    assert result.ter_effort_saved == pytest.approx(1.0)

    assert result.character_edit_distance == 0
    assert result.character_effort_saved == pytest.approx(1.0)

    assert result.soft_word_edit_distance == pytest.approx(0.0)
    assert result.soft_word_effort_saved == pytest.approx(1.0)

    assert result.estimated_characters_saved == pytest.approx(len(text))

    assert result.suggestion_character_count == len(text)
    assert result.final_character_count == len(text)
    assert result.suggestion_word_count == 2
    assert result.final_word_count == 2


def test_wiring_matches_the_individual_metric_functions() -> None:
    """Guards against a field being populated from the wrong calculation."""
    suggestion = "Support analysis of research data."
    final = "Support analysis of clinical research data."

    combined = analyze_selected_suggestion(
        field_name="purpose",
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


def test_character_metrics_are_case_sensitive_but_ter_is_not() -> None:
    """The two measures use deliberately different case configurations."""
    result = analyze_selected_suggestion(
        field_name="title",
        suggestion="Data Analysis",
        final="data analysis",
    )

    assert result.character_edit_distance > 0
    assert result.soft_word_edit_distance > 0.0
    assert result.ter_rate == pytest.approx(0.0)


def test_estimated_characters_saved_formula() -> None:
    result = analyze_selected_suggestion(
        field_name="description",
        suggestion="The data",
        final="The dataset",
    )

    expected = max(
        0.0,
        float(result.final_character_count - result.character_edit_distance),
    )

    assert result.estimated_characters_saved == pytest.approx(expected)


def test_estimated_characters_saved_is_bounded_below_at_zero() -> None:
    """A suggestion costlier than the final text must not report a negative."""
    result = analyze_selected_suggestion(
        field_name="about",
        suggestion="an extremely long and entirely unrelated suggestion",
        final="short",
    )

    assert result.estimated_characters_saved == pytest.approx(0.0)


def test_counts_are_reported_after_unicode_normalization() -> None:
    """Counts reflect the NFC form, not the raw source spelling."""
    suggestion = "cafe\u0301 research"
    final = "caf\u00e9 research project"

    result = analyze_selected_suggestion(
        field_name="about",
        suggestion=suggestion,
        final=final,
    )

    normalized_suggestion = unicode_nfc_normalize_text(suggestion)
    normalized_final = unicode_nfc_normalize_text(final)

    assert result.suggestion_character_count == len(normalized_suggestion)
    assert result.final_character_count == len(normalized_final)
    assert result.suggestion_word_count == len(normalized_suggestion.split())
    assert result.final_word_count == len(normalized_final.split())


def test_empty_suggestion_is_allowed_and_scores_zero() -> None:
    """A field initialized empty is valid input; it simply saves nothing."""
    final = "A final response"

    result = analyze_selected_suggestion(
        field_name="purpose",
        suggestion="",
        final=final,
    )

    assert result.suggestion_character_count == 0
    assert result.suggestion_word_count == 0
    assert result.character_edit_distance == len(final)
    assert result.character_effort_saved == pytest.approx(0.0)
    assert result.soft_word_effort_saved == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field_name",
    ["", "   ", "\n\t"],
    ids=["empty", "spaces", "tabs-newlines"],
)
def test_blank_field_name_is_rejected(field_name: str) -> None:
    with pytest.raises(ValueError, match="field_name must be a non-empty string"):
        analyze_selected_suggestion(
            field_name=field_name,
            suggestion="suggestion",
            final="final",
        )


def test_non_string_field_name_is_rejected() -> None:
    with pytest.raises(ValueError, match="field_name must be a non-empty string"):
        analyze_selected_suggestion(
            field_name=None,  # type: ignore[arg-type]
            suggestion="suggestion",
            final="final",
        )


def test_non_string_suggestion_is_rejected() -> None:
    with pytest.raises(TypeError, match="suggestion must be a string"):
        analyze_selected_suggestion(
            field_name="title",
            suggestion=None,  # type: ignore[arg-type]
            final="final",
        )


def test_non_string_final_is_rejected() -> None:
    with pytest.raises(TypeError, match="final must be a string"):
        analyze_selected_suggestion(
            field_name="title",
            suggestion="suggestion",
            final=None,  # type: ignore[arg-type]
        )


def test_empty_final_is_rejected() -> None:
    """REMOVED outcomes must not reach this function."""
    with pytest.raises(ValueError, match="final saved text must not be empty"):
        analyze_selected_suggestion(
            field_name="title",
            suggestion="suggestion",
            final="",
        )


def test_whitespace_only_final_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least one word"):
        analyze_selected_suggestion(
            field_name="title",
            suggestion="suggestion",
            final="   \n\t",
        )
