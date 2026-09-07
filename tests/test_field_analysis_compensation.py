"""Tests for compensation text and offersCompensation flag analysis."""

import pytest

from study_posting_ai_analysis.field_analysis import analyze_compensation
from study_posting_ai_analysis.models import MatchType

GENERIC = "Participants will be compensated."
SPECIFIC = "Participants receive a $50 gift card."

NO_SUGGESTIONS: dict[str, object] = {
    "genericCompensation": [],
    "specificCompensation": [],
}


# ---------------------------------------------------------------------------
# The five scenarios that define requiredness behavior
# ---------------------------------------------------------------------------


def test_ai_true_saved_true_with_edited_text() -> None:
    """The ordinary assisted case: a suggestion was taken and refined."""
    result = analyze_compensation(
        {"genericCompensation": [GENERIC], "specificCompensation": []},
        {"genericCompensation": [GENERIC], "specificCompensation": []},
        "Eligible participants will be compensated.",
        True,
        True,
    )

    assert result.match is MatchType.EDITED
    assert result.editing_metrics is not None
    assert result.flag_accepted is True
    assert result.compensation_text_required is True


def test_ai_true_saved_true_requires_text() -> None:
    """Text is mandatory when the saved flag is True."""
    with pytest.raises(ValueError, match="final text is required"):
        analyze_compensation(
            {"genericCompensation": [GENERIC], "specificCompensation": []},
            NO_SUGGESTIONS,
            "",
            True,
            True,
        )


def test_ai_false_user_sets_true_and_writes_unassisted_text() -> None:
    """The user overrode the recommendation and wrote text independently."""
    result = analyze_compensation(
        NO_SUGGESTIONS,
        NO_SUGGESTIONS,
        SPECIFIC,
        False,
        True,
    )

    assert result.match is MatchType.UNASSISTED
    assert result.pick is None
    assert result.editing_metrics is None
    assert result.flag_accepted is False
    assert result.flag_changed is True
    assert result.compensation_text_required is True


def test_ai_false_saved_false_permits_blank_text() -> None:
    result = analyze_compensation(
        NO_SUGGESTIONS,
        NO_SUGGESTIONS,
        "",
        False,
        False,
    )

    assert result.match is MatchType.UNASSISTED
    assert result.flag_accepted is True
    assert result.flag_changed is False
    assert result.compensation_text_required is False


def test_ai_true_user_sets_false_and_clears_text() -> None:
    """A selection followed by clearing is REMOVED, with metrics undefined."""
    result = analyze_compensation(
        {"genericCompensation": [GENERIC], "specificCompensation": []},
        {"genericCompensation": [GENERIC], "specificCompensation": []},
        "",
        True,
        False,
    )

    assert result.match is MatchType.REMOVED
    assert result.pick is not None
    assert result.editing_metrics is None
    assert result.flag_accepted is False
    assert result.flag_changed is True
    assert result.compensation_text_required is False


def test_selected_text_cannot_be_blank_while_saved_flag_is_true() -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        analyze_compensation(
            {"genericCompensation": [GENERIC], "specificCompensation": []},
            {"genericCompensation": [GENERIC], "specificCompensation": []},
            "",
            True,
            True,
        )


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------


def test_specific_category_selection_is_recorded_with_its_kind() -> None:
    result = analyze_compensation(
        {"genericCompensation": [GENERIC], "specificCompensation": [SPECIFIC]},
        {"genericCompensation": [], "specificCompensation": [SPECIFIC]},
        SPECIFIC,
        True,
        True,
    )

    assert result.match is MatchType.EXACT
    assert result.pick is not None
    assert result.pick.kind == "specificCompensation"
    assert result.pick.index == 0


def test_suggestion_counts_cover_both_categories() -> None:
    result = analyze_compensation(
        {
            "genericCompensation": [GENERIC],
            "specificCompensation": [SPECIFIC, "Another offer."],
        },
        NO_SUGGESTIONS,
        "",
        True,
        False,
    )

    assert result.suggestion_counts == {
        "genericCompensation": 1,
        "specificCompensation": 2,
    }


def test_multiple_selections_across_categories_are_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="At most one compensation text suggestion may be selected",
    ):
        analyze_compensation(
            {
                "genericCompensation": [GENERIC],
                "specificCompensation": [SPECIFIC],
            },
            {
                "genericCompensation": [GENERIC],
                "specificCompensation": [SPECIFIC],
            },
            SPECIFIC,
            True,
            True,
        )


def test_multiple_selections_within_one_category_are_rejected() -> None:
    first = "First suggestion."
    second = "Second suggestion."

    with pytest.raises(
        ValueError,
        match="At most one compensation text suggestion may be selected",
    ):
        analyze_compensation(
            {
                "genericCompensation": [first, second],
                "specificCompensation": [],
            },
            {
                "genericCompensation": [first, second],
                "specificCompensation": [],
            },
            first,
            True,
            True,
        )


def test_selection_absent_from_the_offer_list_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="none of the selected text values occur",
    ):
        analyze_compensation(
            {"genericCompensation": [GENERIC], "specificCompensation": []},
            {"genericCompensation": ["Never offered."], "specificCompensation": []},
            "Never offered.",
            True,
            True,
        )


# ---------------------------------------------------------------------------
# Flag validation
# ---------------------------------------------------------------------------


def test_missing_saved_flag_is_rejected_when_required() -> None:
    with pytest.raises(ValueError, match="must be saved as True or False"):
        analyze_compensation({}, {}, "", None, None, radio_required=True)


def test_absent_recommendation_leaves_acceptance_undefined() -> None:
    """Undefined rather than False, so it can be excluded from a rate."""
    result = analyze_compensation({}, {}, "", None, False, radio_required=True)

    assert result.flag_suggested is None
    assert result.flag_saved is False
    assert result.flag_accepted is None
    assert result.flag_changed is None


@pytest.mark.parametrize(
    "invalid_flag",
    [1, 0, "true", []],
    ids=["one", "zero", "string", "list"],
)
def test_non_boolean_flag_is_rejected(invalid_flag: object) -> None:
    """Bool subclasses int, so only an exact type check rejects 1 and 0."""
    with pytest.raises(TypeError, match="must be True, False, or None"):
        analyze_compensation({}, {}, "", invalid_flag, True)


def test_optional_flag_is_permitted_when_not_required() -> None:
    result = analyze_compensation(
        {},
        {},
        "",
        None,
        None,
        radio_required=False,
    )

    assert result.flag_saved is None
    assert result.compensation_text_required is False


# ---------------------------------------------------------------------------
# Container validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "absent",
    [None, {}],
    ids=["none", "empty-object"],
)
def test_absent_containers_are_treated_as_no_suggestions(absent: object) -> None:
    result = analyze_compensation(absent, absent, "", False, False)

    assert result.suggestion_counts == {
        "genericCompensation": 0,
        "specificCompensation": 0,
    }
    assert result.match is MatchType.UNASSISTED


def test_non_object_suggestion_container_is_rejected() -> None:
    with pytest.raises(TypeError, match="must be a dictionary"):
        analyze_compensation([], {}, "", False, False)


def test_non_string_final_text_is_rejected() -> None:
    with pytest.raises(TypeError, match="must be a string"):
        analyze_compensation({}, {}, 50, False, False)
