"""Full-matrix reference implementation for differential testing.

Exists solely to verify the memory-optimized two-row implementation in
``metrics.weighted_soft_word_distance``. It intentionally prioritizes
readability over memory efficiency and must not be used in production code.

Because both implementations use the same recurrence and the same RapidFuzz
substitution-cost function, agreement verifies implementation consistency
rather than independently validating the metric. See
docs/analysis-specification.md section 15.
"""

from rapidfuzz.distance import Levenshtein

from text_post_edit_metrics.normalization import (
    normalize_metric_text,
)


def reference_full_matrix_distance(
    suggestion: str,
    final: str,
    *,
    insertion_cost: float = 1.0,
    deletion_cost: float = 1.0,
    case_sensitive: bool = True,
) -> float:
    """Calculate weighted soft-word distance using a full matrix.

    Parameters
    ----------
    suggestion
        The applied LLM suggestion.
    final
        The final text saved by the user.
    insertion_cost
        Cost of inserting one word.
    deletion_cost
        Cost of deleting one word.
    case_sensitive
        When ``False``, case differences are ignored.

    Returns
    -------
    float
        The minimum total weighted cost.
    """
    normalized_suggestion = normalize_metric_text(
        suggestion,
        case_sensitive=case_sensitive,
    )
    normalized_final = normalize_metric_text(
        final,
        case_sensitive=case_sensitive,
    )

    suggestion_words = normalized_suggestion.split()
    final_words = normalized_final.split()

    number_of_suggestion_words = len(suggestion_words)
    number_of_final_words = len(final_words)

    matrix = [
        [0.0] * (number_of_final_words + 1)
        for _ in range(number_of_suggestion_words + 1)
    ]

    # Transform each suggestion prefix into an empty final string by deleting
    # every word processed so far.
    for suggestion_position in range(number_of_suggestion_words + 1):
        matrix[suggestion_position][0] = suggestion_position * deletion_cost

    # Transform an empty suggestion into each final prefix by inserting every
    # final word.
    for final_position in range(number_of_final_words + 1):
        matrix[0][final_position] = final_position * insertion_cost

    for suggestion_position in range(1, number_of_suggestion_words + 1):
        suggestion_word = suggestion_words[suggestion_position - 1]

        for final_position in range(1, number_of_final_words + 1):
            final_word = final_words[final_position - 1]

            substitution_cost = Levenshtein.normalized_distance(
                suggestion_word,
                final_word,
            )

            cost_after_insertion = (
                matrix[suggestion_position][final_position - 1] + insertion_cost
            )
            cost_after_deletion = (
                matrix[suggestion_position - 1][final_position] + deletion_cost
            )
            cost_after_substitution = (
                matrix[suggestion_position - 1][final_position - 1] + substitution_cost
            )

            matrix[suggestion_position][final_position] = min(
                cost_after_insertion,
                cost_after_deletion,
                cost_after_substitution,
            )

    return matrix[number_of_suggestion_words][number_of_final_words]
