"""Randomized differential tests for the soft-word implementation.

The production implementation retains only two rows of the dynamic-programming
matrix. These tests verify it against a readable full-matrix implementation.

Because both use the same recurrence and the same RapidFuzz substitution-cost
function, agreement verifies implementation consistency rather than
independently validating the metric. See docs/analysis-specification.md
section 15.

Marked slow: excluded by "make test-fast".
"""

import random

import pytest
from tests.helpers.reference_impl import reference_full_matrix_distance

from text_post_edit_metrics.metrics import weighted_soft_word_distance

# Vocabularies deliberately include orthographically similar words, so that
# fractional substitution costs are exercised rather than only whole-word
# insertions and deletions.
_SIMILAR_VOCABULARY = (
    "data",
    "analysis",
    "analyze",
    "student",
    "research",
    "quickly",
    "fast",
)

_FIELD_VOCABULARY = (
    "title",
    "purpose",
    "description",
    "compensation",
    "about",
)


def _random_text(
    generator: random.Random,
    vocabulary: tuple[str, ...],
    maximum_words: int,
) -> str:
    """Return whitespace-joined random words, possibly an empty string."""
    word_count = generator.randint(0, maximum_words)

    return " ".join(generator.choices(vocabulary, k=word_count))


@pytest.mark.slow
def test_optimized_implementation_matches_reference_with_equal_costs() -> None:
    """1,000 pseudorandom pairs with insertion and deletion costs of 1."""
    generator = random.Random(42)

    for case_number in range(1_000):
        suggestion = _random_text(generator, _SIMILAR_VOCABULARY, 8)
        final = _random_text(generator, _SIMILAR_VOCABULARY, 8)

        optimized = weighted_soft_word_distance(suggestion, final)
        reference = reference_full_matrix_distance(suggestion, final)

        assert optimized == pytest.approx(reference, abs=1e-12), (
            f"case {case_number}: {suggestion!r} -> {final!r}"
        )


@pytest.mark.slow
def test_optimized_implementation_matches_reference_with_unequal_costs() -> None:
    """500 pseudorandom pairs with unequal insertion and deletion costs.

    Unequal costs detect a reversal that would remain hidden if both were 1.
    """
    generator = random.Random(123)

    insertion_cost = 1.25
    deletion_cost = 1.75

    for case_number in range(500):
        suggestion = _random_text(generator, _FIELD_VOCABULARY, 6)
        final = _random_text(generator, _FIELD_VOCABULARY, 6)

        optimized = weighted_soft_word_distance(
            suggestion,
            final,
            insertion_cost=insertion_cost,
            deletion_cost=deletion_cost,
        )
        reference = reference_full_matrix_distance(
            suggestion,
            final,
            insertion_cost=insertion_cost,
            deletion_cost=deletion_cost,
        )

        assert optimized == pytest.approx(reference, abs=1e-12), (
            f"case {case_number}: {suggestion!r} -> {final!r}"
        )


@pytest.mark.parametrize(
    ("suggestion", "final"),
    [
        ("", ""),
        ("", "one"),
        ("one", ""),
        ("one one one", "one"),
        ("one", "one one one"),
        ("analyze analyze", "analysis analysis"),
    ],
    ids=[
        "both-empty",
        "empty-suggestion",
        "empty-final",
        "repeated-to-single",
        "single-to-repeated",
        "repeated-substitution",
    ],
)
def test_implementations_agree_on_boundary_cases(
    suggestion: str,
    final: str,
) -> None:
    """Explicit edge cases, not left to chance in the randomized runs."""
    optimized = weighted_soft_word_distance(suggestion, final)
    reference = reference_full_matrix_distance(suggestion, final)

    assert optimized == pytest.approx(reference, abs=1e-12)
