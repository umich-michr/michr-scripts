"""Tests for generic post-editing result models."""

from dataclasses import FrozenInstanceError

import pytest

import michr_text_post_editing as package
from michr_text_post_editing.models import (
    CharacterResult,
    PostEditingResult,
    SoftWordResult,
    TerResult,
)


def make_post_editing_result() -> PostEditingResult:
    """Return a representative combined result."""
    return PostEditingResult(
        ter_rate=0.25,
        ter_effort_saved_raw=0.75,
        ter_effort_saved=0.75,
        character_edit_distance=4,
        character_effort_saved_raw=0.80,
        character_effort_saved=0.80,
        soft_word_edit_distance=0.5,
        soft_word_effort_saved_raw=0.90,
        soft_word_effort_saved=0.90,
        estimated_characters_saved=16.0,
        suggestion_character_count=18,
        final_character_count=20,
        suggestion_word_count=3,
        final_word_count=4,
    )


def test_ter_result_preserves_raw_and_bounded_values() -> None:
    result = TerResult(
        ter_rate=1.25,
        effort_saved_raw=-0.25,
        effort_saved=0.0,
    )

    assert result.ter_rate == pytest.approx(1.25)
    assert result.effort_saved_raw == pytest.approx(-0.25)
    assert result.effort_saved == pytest.approx(0.0)


def test_character_result_preserves_distance_and_scores() -> None:
    result = CharacterResult(
        distance=4,
        effort_saved_raw=0.8,
        effort_saved=0.8,
    )

    assert result.distance == 4
    assert result.effort_saved_raw == pytest.approx(0.8)
    assert result.effort_saved == pytest.approx(0.8)


def test_soft_word_result_preserves_distance_and_scores() -> None:
    result = SoftWordResult(
        distance=0.5,
        effort_saved_raw=0.9,
        effort_saved=0.9,
    )

    assert result.distance == pytest.approx(0.5)
    assert result.effort_saved_raw == pytest.approx(0.9)
    assert result.effort_saved == pytest.approx(0.9)


def test_combined_result_exposes_every_metric_family() -> None:
    result = make_post_editing_result()

    assert result.ter_rate == pytest.approx(0.25)
    assert result.ter_effort_saved == pytest.approx(0.75)

    assert result.character_edit_distance == 4
    assert result.character_effort_saved == pytest.approx(0.80)

    assert result.soft_word_edit_distance == pytest.approx(0.5)
    assert result.soft_word_effort_saved == pytest.approx(0.90)

    assert result.estimated_characters_saved == pytest.approx(16.0)

    assert result.suggestion_character_count == 18
    assert result.final_character_count == 20
    assert result.suggestion_word_count == 3
    assert result.final_word_count == 4


@pytest.mark.parametrize(
    "field_name",
    [
        "ter_rate",
        "character_edit_distance",
        "soft_word_edit_distance",
        "final_character_count",
    ],
)
def test_result_models_are_immutable(field_name: str) -> None:
    result = make_post_editing_result()

    with pytest.raises(FrozenInstanceError):
        setattr(result, field_name, 999)


def test_public_api_exports_result_models() -> None:
    assert package.TerResult is TerResult
    assert package.CharacterResult is CharacterResult
    assert package.SoftWordResult is SoftWordResult
    assert package.PostEditingResult is PostEditingResult
