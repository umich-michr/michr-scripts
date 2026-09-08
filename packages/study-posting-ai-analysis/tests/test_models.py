"""Tests for domain result models and their derived properties."""

from pathlib import Path

import pytest

from michr_text_post_editing import PostEditingResult
import study_posting_ai_analysis as package
from study_posting_ai_analysis.models import (
    CompensationAnalysis,
    FieldKind,
    LookupValueAnalysis,
    MatchType,
    Pick,
    TextFieldAnalysis,
)

# Resolved from this file's location so the tests pass regardless of the
# working directory pytest was invoked from.
PACKAGE_ROOT = Path(__file__).resolve().parent.parent
SPECIFICATION = PACKAGE_ROOT / "docs" / "analysis-specification.md"


def make_editing_result(ter_effort_saved: float) -> PostEditingResult:
    """Return a minimal editing result with the given TER score."""
    return PostEditingResult(
        ter_rate=1.0 - ter_effort_saved,
        ter_effort_saved_raw=ter_effort_saved,
        ter_effort_saved=ter_effort_saved,
        character_edit_distance=0,
        character_effort_saved_raw=1.0,
        character_effort_saved=1.0,
        soft_word_edit_distance=0.0,
        soft_word_effort_saved_raw=1.0,
        soft_word_effort_saved=1.0,
        estimated_characters_saved=0.0,
        suggestion_character_count=0,
        final_character_count=0,
        suggestion_word_count=0,
        final_word_count=0,
    )


def make_text_analysis(
    match: MatchType,
    *,
    metrics: PostEditingResult | None = None,
) -> TextFieldAnalysis:
    """Return a text analysis with the given outcome."""
    return TextFieldAnalysis(
        suggestion_counts={"title": 1},
        pick=Pick(kind="title", index=0) if metrics is not None else None,
        match=match,
        editing_metrics=metrics,
        selected_text="Research Assistant" if metrics is not None else None,
        final_text="Research Assistant",
    )


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


def test_match_type_values_are_stable() -> None:
    """Outcome names appear in exported data and must not change silently."""
    assert {outcome.value for outcome in MatchType} == {
        "EXACT",
        "COSMETIC_EQUIVALENT",
        "EDITED",
        "REMOVED",
        "UNASSISTED",
    }


def test_field_kind_values_are_stable() -> None:
    assert {kind.value for kind in FieldKind} == {
        "TEXT",
        "LOOKUP",
        "COMPENSATION",
        "CONTACT",
        "MERGED",
    }


# ---------------------------------------------------------------------------
# TextFieldAnalysis properties
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("match", "has_metrics", "expected"),
    [
        (MatchType.EXACT, True, 1.0),
        (MatchType.COSMETIC_EQUIVALENT, True, 1.0),
        (MatchType.EDITED, True, 0.75),
        (MatchType.REMOVED, False, 0.0),
        (MatchType.UNASSISTED, False, 0.0),
    ],
    ids=["exact", "cosmetic", "edited", "removed", "unassisted"],
)
def test_policy_adjusted_effort_saved(
    match: MatchType,
    has_metrics: bool,
    expected: float,
) -> None:
    """Full credit for exact and cosmetic; TER score for edited; zero otherwise."""
    metrics = make_editing_result(0.75) if has_metrics else None
    analysis = make_text_analysis(match, metrics=metrics)

    assert analysis.policy_adjusted_effort_saved == pytest.approx(expected)


def test_ter_effort_saved_is_none_without_metrics() -> None:
    """Undefined rather than zero, so it can be excluded from means."""
    analysis = make_text_analysis(MatchType.UNASSISTED)

    assert analysis.ter_effort_saved is None


def test_ter_effort_saved_reads_through_to_metrics() -> None:
    analysis = make_text_analysis(
        MatchType.EDITED,
        metrics=make_editing_result(0.42),
    )

    assert analysis.ter_effort_saved == pytest.approx(0.42)


# ---------------------------------------------------------------------------
# CompensationAnalysis properties
# ---------------------------------------------------------------------------


def make_compensation(
    flag_suggested: bool | None,
    flag_saved: bool | None,
) -> CompensationAnalysis:
    return CompensationAnalysis(
        suggestion_counts={"genericCompensation": 0, "specificCompensation": 0},
        pick=None,
        match=MatchType.UNASSISTED,
        editing_metrics=None,
        selected_text=None,
        final_text="",
        flag_suggested=flag_suggested,
        flag_saved=flag_saved,
    )


@pytest.mark.parametrize(
    ("suggested", "saved", "accepted", "changed"),
    [
        (True, True, True, False),
        (False, False, True, False),
        (True, False, False, True),
        (False, True, False, True),
        (None, True, None, None),
        (True, None, None, None),
    ],
    ids=[
        "both-true",
        "both-false",
        "changed-to-false",
        "changed-to-true",
        "no-recommendation",
        "no-saved-value",
    ],
)
def test_compensation_flag_properties(
    suggested: bool | None,
    saved: bool | None,
    accepted: bool | None,
    changed: bool | None,
) -> None:
    """Acceptance is undefined when either value is missing."""
    analysis = make_compensation(suggested, saved)

    assert analysis.flag_accepted is accepted
    assert analysis.flag_changed is changed


@pytest.mark.parametrize(
    ("flag_saved", "required"),
    [(True, True), (False, False), (None, False)],
    ids=["saved-true", "saved-false", "saved-none"],
)
def test_compensation_text_required_follows_saved_flag(
    flag_saved: bool | None,
    required: bool,
) -> None:
    """Text is required exactly when the saved flag is True."""
    analysis = make_compensation(True, flag_saved)

    assert analysis.compensation_text_required is required


# ---------------------------------------------------------------------------
# LookupValueAnalysis properties
# ---------------------------------------------------------------------------


def make_lookup(
    offered: set[int],
    picked: set[int],
    saved: set[int],
    match: MatchType,
    similarity: float,
) -> LookupValueAnalysis:
    return LookupValueAnalysis(
        offered=frozenset(offered),
        picked=frozenset(picked),
        saved=frozenset(saved),
        match=match,
        similarity=similarity,
    )


def test_lookup_set_partitions_are_derived_consistently() -> None:
    """kept, dropped, added, and saved_not_offered follow from the three sets."""
    analysis = make_lookup(
        offered={1, 2, 3},
        picked={1, 2},
        saved={2, 3, 9},
        match=MatchType.EDITED,
        similarity=1.0 / 4.0,
    )

    assert analysis.kept == frozenset({2})
    assert analysis.dropped == frozenset({1})
    assert analysis.added == frozenset({3, 9})
    assert analysis.saved_not_offered == frozenset({9})


def test_lookup_partitions_are_empty_when_nothing_was_picked() -> None:
    analysis = make_lookup(
        offered={1, 2},
        picked=set(),
        saved={5},
        match=MatchType.UNASSISTED,
        similarity=0.0,
    )

    assert analysis.kept == frozenset()
    assert analysis.dropped == frozenset()
    assert analysis.added == frozenset({5})
    assert analysis.saved_not_offered == frozenset({5})


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------


def test_result_models_are_immutable() -> None:
    """Frozen dataclasses prevent a result from being altered after analysis."""
    analysis = make_text_analysis(MatchType.UNASSISTED)

    with pytest.raises(AttributeError):
        analysis.match = MatchType.EXACT  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Documentation alignment
# ---------------------------------------------------------------------------
# These assertions make one class of documentation drift structurally
# impossible rather than merely discouraged.


def test_specification_documents_every_match_type() -> None:
    """Every outcome name must appear in the analysis specification."""
    specification = SPECIFICATION.read_text(encoding="utf-8")

    for outcome in MatchType:
        assert outcome.value in specification, (
            f"{outcome.value} is not documented in docs/analysis-specification.md"
        )


def test_package_exposes_its_public_api() -> None:
    """A missing __init__.py would make this an implicit namespace package."""
    assert package.__file__ is not None
    assert package.__version__ == "0.1.0"
    assert "MatchType" in package.__all__


def test_package_ships_typing_marker() -> None:
    """PEP 561 marker; without it, consumers lose all type information."""
    package_directory = Path(package.__file__).parent

    assert (package_directory / "py.typed").is_file()
