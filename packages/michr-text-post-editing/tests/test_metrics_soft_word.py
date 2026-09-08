"""Tests for the weighted soft-word robustness measure."""

import math
import unicodedata

import pytest
from rapidfuzz.distance import Levenshtein

from michr_text_post_editing.metrics import (
    calculate_soft_word_metrics,
    weighted_soft_word_distance,
)
from michr_text_post_editing.normalization import clamp01

# ---------------------------------------------------------------------------
# Identity and boundary conditions
# ---------------------------------------------------------------------------


def test_identical_text_has_zero_distance_and_full_score() -> None:
    result = calculate_soft_word_metrics(
        "We analyze the data.",
        "We analyze the data.",
    )

    assert result.distance == pytest.approx(0.0)
    assert result.effort_saved_raw == pytest.approx(1.0)
    assert result.effort_saved == pytest.approx(1.0)


def test_empty_suggestion_requires_inserting_every_final_word() -> None:
    assert weighted_soft_word_distance("", "one two three") == pytest.approx(3.0)


def test_empty_final_requires_deleting_every_suggestion_word() -> None:
    """Defined at the distance layer, though the normalized score is not."""
    assert weighted_soft_word_distance("one two three", "") == pytest.approx(3.0)


@pytest.mark.parametrize(
    ("suggestion", "final"),
    [("one two three", ""), ("", ""), ("text", "   ")],
    ids=["empty-final", "both-empty", "whitespace-final"],
)
def test_normalized_score_rejects_wordless_final(
    suggestion: str,
    final: str,
) -> None:
    """The word-count denominator would be zero."""
    with pytest.raises(ValueError, match="final text contains no words"):
        calculate_soft_word_metrics(suggestion, final)


# ---------------------------------------------------------------------------
# Unequal-length alignments
# ---------------------------------------------------------------------------
# These cases confirm every source and target word contributes to the distance,
# and that no item is silently omitted when the sequences differ in length.


def test_two_suggestion_words_to_one_final_word_charges_an_extra_word() -> None:
    distance = weighted_soft_word_distance("very quickly", "fast")

    expected = 1.0 + min(
        Levenshtein.normalized_distance("very", "fast"),
        Levenshtein.normalized_distance("quickly", "fast"),
    )

    assert distance == pytest.approx(expected)
    assert distance >= 1.0


def test_one_suggestion_word_to_two_final_words_charges_an_extra_word() -> None:
    distance = weighted_soft_word_distance("fast", "very quickly")

    expected = 1.0 + min(
        Levenshtein.normalized_distance("fast", "very"),
        Levenshtein.normalized_distance("fast", "quickly"),
    )

    assert distance == pytest.approx(expected)
    assert distance >= 1.0


def test_distance_never_exceeds_delete_all_then_insert_all() -> None:
    """That path is always available, so it bounds the optimum."""
    distance = weighted_soft_word_distance("one two three four", "alpha beta")

    assert 0.0 <= distance <= 4.0 + 2.0


# ---------------------------------------------------------------------------
# Fractional substitution costs
# ---------------------------------------------------------------------------


def test_small_spelling_change_costs_less_than_unrelated_replacement() -> None:
    """The point of the measure: partial credit for within-word edits."""
    small_change = weighted_soft_word_distance(
        "We analyze data",
        "We analyzed data",
    )
    unrelated_change = weighted_soft_word_distance(
        "We analyze data",
        "We notwithstanding data",
    )

    assert 0.0 < small_change < 1.0
    assert unrelated_change > small_change


def test_article_replacement_uses_exact_rapidfuzz_cost() -> None:
    result = calculate_soft_word_metrics("I bit the bullet", "I bit a bullet")

    expected_cost = Levenshtein.normalized_distance("the", "a")
    expected_score = 1.0 - expected_cost / 4.0

    assert result.distance == pytest.approx(expected_cost)
    assert result.effort_saved_raw == pytest.approx(expected_score)
    assert result.effort_saved == pytest.approx(expected_score)


def test_denominator_is_the_final_word_count() -> None:
    result = calculate_soft_word_metrics(
        "We need to analyze the data logs.",
        "We need to analysis the data logs.",
    )

    expected_cost = Levenshtein.normalized_distance("analyze", "analysis")
    expected_score = 1.0 - expected_cost / 7.0

    assert result.distance == pytest.approx(expected_cost)
    assert result.effort_saved_raw == pytest.approx(expected_score)


def test_score_formula_is_consistent() -> None:
    final = "The final answer contains five words"
    result = calculate_soft_word_metrics(
        "The answer contains several words",
        final,
    )

    expected_raw = 1.0 - result.distance / len(final.split())

    assert result.effort_saved_raw == pytest.approx(expected_raw)
    assert result.effort_saved == pytest.approx(clamp01(expected_raw))


# ---------------------------------------------------------------------------
# Directional operation costs
# ---------------------------------------------------------------------------
# Unequal costs detect a reversal that would remain hidden if both were 1.


def test_insertion_and_deletion_costs_are_not_cross_wired() -> None:
    insertion = weighted_soft_word_distance(
        "",
        "word",
        insertion_cost=2.0,
        deletion_cost=3.0,
    )
    deletion = weighted_soft_word_distance(
        "word",
        "",
        insertion_cost=2.0,
        deletion_cost=3.0,
    )

    assert insertion == pytest.approx(2.0)
    assert deletion == pytest.approx(3.0)


def test_nonempty_insertion_uses_insertion_cost() -> None:
    distance = weighted_soft_word_distance(
        "one",
        "one two",
        insertion_cost=2.0,
        deletion_cost=3.0,
    )

    assert distance == pytest.approx(2.0)


def test_nonempty_deletion_uses_deletion_cost() -> None:
    distance = weighted_soft_word_distance(
        "one two",
        "one",
        insertion_cost=2.0,
        deletion_cost=3.0,
    )

    assert distance == pytest.approx(3.0)


@pytest.mark.parametrize(
    "invalid_cost",
    [math.inf, -math.inf, math.nan],
    ids=["positive-infinity", "negative-infinity", "nan"],
)
def test_non_finite_insertion_cost_is_rejected(invalid_cost: float) -> None:
    with pytest.raises(ValueError, match="insertion_cost must be finite"):
        weighted_soft_word_distance("one", "one two", insertion_cost=invalid_cost)


@pytest.mark.parametrize(
    "invalid_cost",
    [math.inf, -math.inf, math.nan],
    ids=["positive-infinity", "negative-infinity", "nan"],
)
def test_non_finite_deletion_cost_is_rejected(invalid_cost: float) -> None:
    with pytest.raises(ValueError, match="deletion_cost must be finite"):
        weighted_soft_word_distance("one two", "one", deletion_cost=invalid_cost)


def test_negative_insertion_cost_is_rejected() -> None:
    with pytest.raises(ValueError, match="insertion_cost must be non-negative"):
        weighted_soft_word_distance("one", "one two", insertion_cost=-1.0)


def test_negative_deletion_cost_is_rejected() -> None:
    with pytest.raises(ValueError, match="deletion_cost must be non-negative"):
        weighted_soft_word_distance("one two", "one", deletion_cost=-1.0)


# ---------------------------------------------------------------------------
# Raw and bounded scores
# ---------------------------------------------------------------------------


def test_costly_suggestion_retains_negative_raw_score() -> None:
    result = calculate_soft_word_metrics("one two three four five", "unrelated")

    assert result.effort_saved_raw < 0.0
    assert result.effort_saved == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("suggestion", "final"),
    [
        ("identical text", "identical text"),
        ("one two three four", "different"),
        ("short", "short final text"),
        ("analyze data", "analyzed data"),
    ],
    ids=["identical", "mostly-replaced", "extended", "suffix-change"],
)
def test_bounded_score_always_within_zero_and_one(
    suggestion: str,
    final: str,
) -> None:
    result = calculate_soft_word_metrics(suggestion, final)

    assert 0.0 <= result.effort_saved <= 1.0


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------


def test_repeated_whitespace_does_not_affect_tokenization() -> None:
    result = calculate_soft_word_metrics("one   two\nthree", "one two three")

    assert result.distance == pytest.approx(0.0)
    assert result.effort_saved == pytest.approx(1.0)


def test_case_is_preserved_by_default() -> None:
    """The study-level configuration is case-sensitive, unlike TER."""
    result = calculate_soft_word_metrics("Data Analysis", "data analysis")

    assert result.distance > 0.0


def test_case_sensitivity_is_configurable() -> None:
    result = calculate_soft_word_metrics(
        "Data Analysis",
        "data analysis",
        case_sensitive=False,
    )

    assert result.distance == pytest.approx(0.0)
    assert result.effort_saved == pytest.approx(1.0)


def test_unicode_equivalent_text_has_zero_distance() -> None:
    composed = unicodedata.normalize("NFC", "cafe\u0301")
    decomposed = unicodedata.normalize("NFD", "cafe\u0301")

    assert composed != decomposed

    result = calculate_soft_word_metrics(composed, decomposed)

    assert result.distance == pytest.approx(0.0)
    assert result.effort_saved == pytest.approx(1.0)
