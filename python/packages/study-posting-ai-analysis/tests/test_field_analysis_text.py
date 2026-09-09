"""Tests for text field analysis and match classification."""

import pytest

from study_posting_ai_analysis.field_analysis import (
    analyze_text_field,
    compare_selected_text,
    find_first_picked_suggestion,
)
from study_posting_ai_analysis.models import MatchType
from text_post_edit_metrics.models import PostEditingResult

# ---------------------------------------------------------------------------
# find_first_picked_suggestion
# ---------------------------------------------------------------------------


def test_returns_index_within_the_suggestion_list() -> None:
    """The index refers to the offer list, not the selection list."""
    assert find_first_picked_suggestion(
        ["first", "second", "third"],
        ["third"],
    ) == (2, "third")


def test_returns_none_when_selection_was_not_offered() -> None:
    assert find_first_picked_suggestion(["first", "second"], ["other"]) is None


def test_duplicate_suggestions_report_the_first_occurrence() -> None:
    assert find_first_picked_suggestion(["a", "b", "a"], ["a"]) == (0, "a")


def test_empty_selections_return_none() -> None:
    assert find_first_picked_suggestion(["a"], []) is None


# ---------------------------------------------------------------------------
# compare_selected_text: outcome classification
# ---------------------------------------------------------------------------


def test_exact_match_records_a_verified_full_score() -> None:
    """Metrics are calculated even for EXACT, so the score is measured."""
    match, metrics = compare_selected_text(
        field="title",
        selected="Research Assistant",
        final="Research Assistant",
        allow_empty_final=False,
    )

    assert match is MatchType.EXACT
    assert metrics is not None
    assert metrics.ter_effort_saved == pytest.approx(1.0)


def test_cosmetic_equivalence_does_not_suppress_edit_distance() -> None:
    """
    That normalize_text_for_equivalence is used for classification only.

    If it ever preprocessed a metric input, character_edit_distance would become 0 and
    this test would fail.
    """
    match, metrics = compare_selected_text(
        field="title",
        selected="Resume: Data Analysis",
        final="resume data analysis",
        allow_empty_final=False,
    )

    assert match is MatchType.COSMETIC_EQUIVALENT
    assert isinstance(metrics, PostEditingResult)
    assert metrics.character_edit_distance > 0


def test_edited_match_is_classified_and_measured() -> None:
    match, metrics = compare_selected_text(
        field="title",
        selected="Research Assistant",
        final="Senior Research Coordinator",
        allow_empty_final=False,
    )

    assert match is MatchType.EDITED
    assert isinstance(metrics, PostEditingResult)


def test_optional_field_classifies_blank_final_as_removed() -> None:
    """Metrics are undefined: the normalized denominator would be zero."""
    match, metrics = compare_selected_text(
        field="contact.website",
        selected="https://example.edu",
        final="",
        allow_empty_final=True,
    )

    assert match is MatchType.REMOVED
    assert metrics is None


@pytest.mark.parametrize(
    "final",
    ["", "   ", "\n\t"],
    ids=["empty", "spaces", "tabs-newlines"],
)
def test_required_field_rejects_blank_final(final: str) -> None:
    """A blank required field is a validation error, not a score of zero."""
    with pytest.raises(ValueError, match="final saved text must not be blank"):
        compare_selected_text(
            field="title",
            selected="Research Assistant",
            final=final,
            allow_empty_final=False,
        )


def test_blank_check_precedes_the_exact_check() -> None:
    """Evaluation order: blank, then exact, then cosmetic, then edited."""
    match, _ = compare_selected_text(
        field="about",
        selected="",
        final="",
        allow_empty_final=True,
    )

    assert match is MatchType.REMOVED


@pytest.mark.parametrize(
    "field",
    ["", "   "],
    ids=["empty", "spaces"],
)
def test_blank_field_name_is_rejected(field: str) -> None:
    with pytest.raises(ValueError, match="field must be a non-empty string"):
        compare_selected_text(
            field=field,
            selected="text",
            final="text",
            allow_empty_final=False,
        )


# ---------------------------------------------------------------------------
# analyze_text_field
# ---------------------------------------------------------------------------


def test_no_selection_is_unassisted() -> None:
    result = analyze_text_field(
        field="about",
        suggested=["Offered text"],
        selected=[],
        final="Independently written text",
        allow_empty_final=True,
    )

    assert result.match is MatchType.UNASSISTED
    assert result.pick is None
    assert result.editing_metrics is None
    assert result.selected_text is None
    assert result.final_text == "Independently written text"


def test_selection_records_its_offer_index() -> None:
    result = analyze_text_field(
        field="title",
        suggested=["First offer", "Second offer"],
        selected=["Second offer"],
        final="Second offer",
        allow_empty_final=False,
    )

    assert result.pick is not None
    assert result.pick.kind == "title"
    assert result.pick.index == 1
    assert result.match is MatchType.EXACT


def test_suggestion_count_is_reported_even_when_unselected() -> None:
    """Offer coverage requires counting suggestions that were not taken."""
    result = analyze_text_field(
        field="purpose",
        suggested=["A", "B", "C"],
        selected=[],
        final="Written independently",
        allow_empty_final=False,
    )

    assert result.suggestion_counts == {"purpose": 3}


def test_absent_suggestions_are_treated_as_none_offered() -> None:
    result = analyze_text_field(
        field="about",
        suggested=None,
        selected=None,
        final="Text",
        allow_empty_final=True,
    )

    assert result.suggestion_counts == {"about": 0}
    assert result.match is MatchType.UNASSISTED


def test_absent_final_value_is_treated_as_blank() -> None:
    result = analyze_text_field(
        field="about",
        suggested=[],
        selected=[],
        final=None,
        allow_empty_final=True,
    )

    assert result.final_text == ""
    assert result.match is MatchType.UNASSISTED


def test_multiple_selections_are_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="at most one suggestion may be selected",
    ):
        analyze_text_field(
            field="title",
            suggested=["A", "B"],
            selected=["A", "B"],
            final="A",
            allow_empty_final=False,
        )


def test_selection_absent_from_the_offer_list_is_rejected() -> None:
    """Guards against a selection that was never actually offered."""
    with pytest.raises(
        ValueError,
        match="none of the selected text values occur",
    ):
        analyze_text_field(
            field="title",
            suggested=["Offered"],
            selected=["Never offered"],
            final="Never offered",
            allow_empty_final=False,
        )


def test_unassisted_blank_required_field_is_rejected() -> None:
    with pytest.raises(ValueError, match="final saved text must not be blank"):
        analyze_text_field(
            field="title",
            suggested=[],
            selected=[],
            final="",
            allow_empty_final=False,
        )


def test_unassisted_blank_optional_field_is_permitted() -> None:
    result = analyze_text_field(
        field="about",
        suggested=[],
        selected=[],
        final="",
        allow_empty_final=True,
    )

    assert result.match is MatchType.UNASSISTED
    assert result.final_text == ""


def test_non_string_suggestion_container_is_rejected() -> None:
    with pytest.raises(TypeError, match="must be a list of strings"):
        analyze_text_field(
            field="title",
            suggested="not a list",
            selected=[],
            final="Text",
            allow_empty_final=False,
        )


def test_non_string_suggestion_item_is_rejected() -> None:
    with pytest.raises(TypeError, match="must contain strings only"):
        analyze_text_field(
            field="title",
            suggested=[1],
            selected=[],
            final="Text",
            allow_empty_final=False,
        )


def test_non_string_final_value_is_rejected() -> None:
    with pytest.raises(TypeError, match="must be a string"):
        analyze_text_field(
            field="title",
            suggested=[],
            selected=[],
            final=42,
            allow_empty_final=False,
        )
