"""Tests for lookup field analysis."""

import pytest

from study_posting_ai_analysis.field_analysis import analyze_lookup_values
from study_posting_ai_analysis.models import MatchType

# ---------------------------------------------------------------------------
# Outcomes
# ---------------------------------------------------------------------------


def test_identical_sets_are_exact_with_full_similarity() -> None:
    result = analyze_lookup_values(
        suggested=[1, 2],
        picked=[1, 2],
        saved=[1, 2],
    )

    assert result.match is MatchType.EXACT
    assert result.similarity == pytest.approx(1.0)


def test_differing_sets_use_jaccard_similarity() -> None:
    result = analyze_lookup_values(
        suggested=[1, 2, 3],
        picked=[1, 2],
        saved=[2, 3],
    )

    assert result.match is MatchType.EDITED
    assert result.similarity == pytest.approx(1.0 / 3.0)
    assert result.kept == frozenset({2})
    assert result.dropped == frozenset({1})
    assert result.added == frozenset({3})


def test_nothing_picked_is_unassisted_with_policy_similarity() -> None:
    """That 0.0 is a policy assignment, not a calculation.

    A refactor computing Jaccard on empty sets would raise ZeroDivisionError here.
    """
    result = analyze_lookup_values(
        suggested=[1, 2],
        picked=[],
        saved=[5],
    )

    assert result.match is MatchType.UNASSISTED
    assert result.similarity == pytest.approx(0.0)


def test_disjoint_sets_have_zero_similarity() -> None:
    result = analyze_lookup_values(
        suggested=[1, 2],
        picked=[1],
        saved=[9],
    )

    assert result.match is MatchType.EDITED
    assert result.similarity == pytest.approx(0.0)


def test_saved_values_never_offered_are_reported() -> None:
    result = analyze_lookup_values(
        suggested=[1, 2],
        picked=[1],
        saved=[1, 7],
    )

    assert result.saved_not_offered == frozenset({7})


@pytest.mark.parametrize(
    "absent",
    [None, []],
    ids=["none", "empty-list"],
)
def test_absent_values_are_treated_as_empty_sets(absent: object) -> None:
    result = analyze_lookup_values(
        suggested=absent,
        picked=absent,
        saved=absent,
    )

    assert result.match is MatchType.UNASSISTED
    assert result.offered == frozenset()
    assert result.picked == frozenset()
    assert result.saved == frozenset()


def test_duplicate_identifiers_collapse_into_a_set() -> None:
    """Similarity is computed over unique values."""
    result = analyze_lookup_values(
        suggested=[1, 1, 2],
        picked=[1, 1],
        saved=[1],
    )

    assert result.offered == frozenset({1, 2})
    assert result.picked == frozenset({1})
    assert result.match is MatchType.EXACT


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_picking_an_unoffered_identifier_is_rejected() -> None:
    with pytest.raises(ValueError, match="not among the offered values"):
        analyze_lookup_values(suggested=[1], picked=[2], saved=[2])


def test_boolean_identifier_is_rejected() -> None:
    """
    That isinstance(item, bool) remains in require_integer_set.

    Removing it makes [True] silently become {1}.
    """
    with pytest.raises(TypeError, match="integer IDs only"):
        analyze_lookup_values(suggested=[True], picked=[], saved=[])


@pytest.mark.parametrize(
    ("suggested", "picked", "saved"),
    [
        (["1"], [], []),
        ([1.5], [], []),
        ([1], [], [None]),
    ],
    ids=["string", "float", "none-in-saved"],
)
def test_non_integer_identifiers_are_rejected(
    suggested: object,
    picked: object,
    saved: object,
) -> None:
    with pytest.raises(TypeError, match="integer IDs only"):
        analyze_lookup_values(
            suggested=suggested,
            picked=picked,
            saved=saved,
        )


def test_non_list_value_is_rejected() -> None:
    with pytest.raises(TypeError, match="must be a list of integer IDs"):
        analyze_lookup_values(suggested="1,2", picked=[], saved=[])


# ---------------------------------------------------------------------------
# Set partition consistency
# ---------------------------------------------------------------------------


def test_kept_and_dropped_partition_the_picked_set() -> None:
    """Every picked identifier is either kept or dropped, never both."""
    result = analyze_lookup_values(
        suggested=[1, 2, 3, 4],
        picked=[1, 2, 3],
        saved=[2, 3, 8],
    )

    assert result.kept | result.dropped == result.picked
    assert result.kept & result.dropped == frozenset()
