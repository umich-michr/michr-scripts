"""Reported and LLM-inferred content-source concordance."""

import pandas as pd

_AI = "AI"
_ALL = "ALL"
_COMPLETE = "COMPLETE"
_INCOMPLETE = "INCOMPLETE"

CONTENT_SOURCE_CONCORDANCE_SUMMARY_COLUMNS: tuple[str, ...] = (
    "attempt_completion_group",
    "ai_attempt_count",
    "ai_attempt_count_with_both_content_source_values",
    "ai_attempt_count_with_matching_content_source",
    "ai_attempt_count_with_different_content_source",
    ("ai_attempt_percentage_with_different_content_source_among_comparable_attempts"),
    "ai_attempt_count_with_both_other_text_values",
    "ai_attempt_count_with_matching_other_text_value",
    "ai_attempt_count_with_different_other_text_value",
    ("ai_attempt_percentage_with_different_other_text_value_among_comparable_attempts"),
    "comparison_normalization_rule",
)

CONTENT_SOURCE_CONCORDANCE_MATRIX_COLUMNS: tuple[str, ...] = (
    "attempt_completion_group",
    "reported_study_content_source",
    "inferred_study_content_source",
    "ai_attempt_count",
    "reported_source_attempt_count",
    "attempt_percentage_within_reported_source",
)

_DIFFERENT_SOURCE_PERCENTAGE_COLUMN = (
    "ai_attempt_percentage_with_different_content_source_among_comparable_attempts"
)
_DIFFERENT_OTHER_PERCENTAGE_COLUMN = (
    "ai_attempt_percentage_with_different_other_text_value_among_comparable_attempts"
)
_COMPARISON_RULE = (
    "Trim surrounding whitespace and compare using Unicode casefold; "
    "null and blank remain missing."
)


def _percentage(
    numerator: int,
    denominator: int,
) -> float | None:
    """Return a percentage or ``None`` for an empty denominator."""
    if denominator == 0:
        return None

    return 100.0 * numerator / denominator


def _normalize_comparison_value(value: object) -> str | None:
    """Return normalized nonblank comparison text."""
    if not isinstance(value, str):
        return None

    stripped = value.strip()

    return None if not stripped else stripped.casefold()


def _completion_population(
    ai_attempts: pd.DataFrame,
    *,
    completion_group: str,
) -> pd.DataFrame:
    """Return the requested AI-attempt completion population."""
    if completion_group == _ALL:
        return ai_attempts

    return ai_attempts.loc[ai_attempts["attempt_completion_group"].eq(completion_group)]


def _comparison_counts(
    population: pd.DataFrame,
    *,
    left_column: str,
    right_column: str,
) -> tuple[int, int, int]:
    """Return comparable, matching, and differing row counts."""
    pairs = [
        (
            _normalize_comparison_value(left),
            _normalize_comparison_value(right),
        )
        for left, right in zip(
            population[left_column],
            population[right_column],
            strict=True,
        )
    ]
    comparable = [
        (left, right) for left, right in pairs if left is not None and right is not None
    ]
    matching = sum(left == right for left, right in comparable)

    return (
        len(comparable),
        matching,
        len(comparable) - matching,
    )


def _summary_row(
    ai_attempts: pd.DataFrame,
    *,
    completion_group: str,
) -> dict[str, object]:
    """Return one concordance summary population."""
    population = _completion_population(
        ai_attempts,
        completion_group=completion_group,
    )
    comparable_source, matching_source, different_source = _comparison_counts(
        population,
        left_column="study_content_source",
        right_column="llm_inferred_study_content_source",
    )
    comparable_other, matching_other, different_other = _comparison_counts(
        population,
        left_column="study_content_source_other_value",
        right_column="llm_inferred_study_content_source_other_value",
    )

    return {
        "attempt_completion_group": completion_group,
        "ai_attempt_count": len(population),
        "ai_attempt_count_with_both_content_source_values": comparable_source,
        "ai_attempt_count_with_matching_content_source": matching_source,
        "ai_attempt_count_with_different_content_source": different_source,
        _DIFFERENT_SOURCE_PERCENTAGE_COLUMN: _percentage(
            different_source,
            comparable_source,
        ),
        "ai_attempt_count_with_both_other_text_values": comparable_other,
        "ai_attempt_count_with_matching_other_text_value": matching_other,
        "ai_attempt_count_with_different_other_text_value": different_other,
        _DIFFERENT_OTHER_PERCENTAGE_COLUMN: _percentage(
            different_other,
            comparable_other,
        ),
        "comparison_normalization_rule": _COMPARISON_RULE,
    }


def build_content_source_concordance_summary(
    attempts: pd.DataFrame,
) -> pd.DataFrame:
    """Return all, complete, and incomplete AI-attempt concordance rows."""
    ai_attempts = attempts.loc[attempts["attempt_authoring_mode"].eq(_AI)]
    rows = [
        _summary_row(
            ai_attempts,
            completion_group=completion_group,
        )
        for completion_group in (
            _ALL,
            _COMPLETE,
            _INCOMPLETE,
        )
    ]

    return pd.DataFrame.from_records(
        rows,
        columns=list(CONTENT_SOURCE_CONCORDANCE_SUMMARY_COLUMNS),
    )


def _matrix_population(
    attempts: pd.DataFrame,
    *,
    completion_group: str,
) -> pd.DataFrame:
    """Return comparable AI rows for one matrix population."""
    population = attempts.loc[attempts["attempt_authoring_mode"].eq(_AI)]

    if completion_group != _ALL:
        population = population.loc[
            population["attempt_completion_group"].eq(completion_group)
        ]

    output = population.copy()
    output["_reported_normalized"] = [
        _normalize_comparison_value(value) for value in output["study_content_source"]
    ]
    output["_inferred_normalized"] = [
        _normalize_comparison_value(value)
        for value in output["llm_inferred_study_content_source"]
    ]

    return output.loc[
        output["_reported_normalized"].notna() & output["_inferred_normalized"].notna()
    ]


def _reported_source_counts(
    population: pd.DataFrame,
) -> dict[str, int]:
    """Return comparable AI-attempt counts by reported source."""
    return {
        str(reported_value): len(group)
        for reported_value, group in population.groupby(
            "_reported_normalized",
            sort=True,
            dropna=False,
        )
    }


def build_content_source_concordance_matrix(
    attempts: pd.DataFrame,
) -> pd.DataFrame:
    """Return reported-versus-inferred source counts for heatmaps."""
    rows: list[dict[str, object]] = []

    for completion_group in (
        _ALL,
        _COMPLETE,
        _INCOMPLETE,
    ):
        population = _matrix_population(
            attempts,
            completion_group=completion_group,
        )
        reported_counts = _reported_source_counts(population)

        for keys, group in population.groupby(
            [
                "_reported_normalized",
                "_inferred_normalized",
            ],
            sort=True,
            dropna=False,
        ):
            reported_value, inferred_value = keys
            reported_text = str(reported_value)
            reported_count = reported_counts[reported_text]
            attempt_count = len(group)
            rows.append(
                {
                    "attempt_completion_group": completion_group,
                    "reported_study_content_source": reported_text,
                    "inferred_study_content_source": str(inferred_value),
                    "ai_attempt_count": attempt_count,
                    "reported_source_attempt_count": reported_count,
                    "attempt_percentage_within_reported_source": _percentage(
                        attempt_count,
                        reported_count,
                    ),
                }
            )

    return pd.DataFrame.from_records(
        rows,
        columns=list(CONTENT_SOURCE_CONCORDANCE_MATRIX_COLUMNS),
    )
