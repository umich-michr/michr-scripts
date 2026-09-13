"""Aggregate study attempt histories and author handoffs."""

import pandas as pd

from study_posting_audit_exploration.statistics import describe_numeric

_ALL = "ALL"
_AI = "AI"
_MANUAL = "MANUAL"
_NOT_COMPLETED = "NOT_COMPLETED"

_STUDY_ATTEMPT_HISTORY_COLUMNS: tuple[str, ...] = (
    "final_completion_authoring_mode",
    "distinct_study_count",
    "study_count_with_no_completed_attempt",
    "study_count_with_preceding_incomplete_attempts",
    "study_percentage_with_preceding_incomplete_attempts",
    "total_preceding_incomplete_attempt_count",
    "total_preceding_ai_error_attempt_count",
    "total_preceding_ai_error_without_stack_trace_attempt_count",
    "total_preceding_user_dropped_attempt_count",
    "minimum_preceding_incomplete_attempt_count",
    "percentile_25_preceding_incomplete_attempt_count",
    "median_preceding_incomplete_attempt_count",
    "average_preceding_incomplete_attempt_count",
    "percentile_75_preceding_incomplete_attempt_count",
    "percentile_90_preceding_incomplete_attempt_count",
    "maximum_preceding_incomplete_attempt_count",
    "minimum_minutes_first_attempt_to_completion",
    "median_minutes_first_attempt_to_completion",
    "average_minutes_first_attempt_to_completion",
    "standard_deviation_minutes_first_attempt_to_completion",
    "maximum_minutes_first_attempt_to_completion",
    "study_count_with_author_change_before_completion",
    "study_percentage_with_author_change_before_completion",
)

_AUTHOR_HANDOFF_COLUMNS: tuple[str, ...] = (
    "completed_attempt_authoring_mode",
    "preceding_attempt_authoring_mode",
    "preceding_attempt_result",
    "author_handoff_category",
    "distinct_completed_study_count",
    "population_distinct_completed_study_count",
    "distinct_completed_study_percentage",
    "minimum_minutes_first_attempt_to_completion",
    "percentile_25_minutes_first_attempt_to_completion",
    "median_minutes_first_attempt_to_completion",
    "average_minutes_first_attempt_to_completion",
    "standard_deviation_minutes_first_attempt_to_completion",
    "percentile_75_minutes_first_attempt_to_completion",
    "maximum_minutes_first_attempt_to_completion",
)


def _percentage(
    numerator: int,
    denominator: int,
) -> float | None:
    """Return a percentage or ``None`` for an empty denominator."""
    if denominator == 0:
        return None

    return 100.0 * numerator / denominator


def _study_population(
    studies: pd.DataFrame,
    *,
    mode: str,
) -> pd.DataFrame:
    """Return the explicitly named study-history population."""
    if mode == _ALL:
        return studies

    if mode == _NOT_COMPLETED:
        return studies.loc[studies["study_is_completed"].eq(False)]

    return studies.loc[
        studies["study_is_completed"].eq(True)
        & studies["completed_attempt_authoring_mode"].eq(mode)
    ]


def _study_history_summary_row(
    studies: pd.DataFrame,
    *,
    mode: str,
) -> dict[str, object]:
    """Return one study-attempt-history summary row."""
    population = _study_population(
        studies,
        mode=mode,
    )
    study_count = len(population)
    no_completion_count = int(population["study_is_completed"].eq(False).sum())
    preceding_count = int(population["preceding_incomplete_attempt_count"].gt(0).sum())
    author_change_count = int(
        population["author_changed_before_completion"].eq(True).sum()
    )
    preceding_distribution = describe_numeric(
        population["preceding_incomplete_attempt_count"],
        metric_name="preceding_incomplete_attempt_count",
    )
    completion_minutes = describe_numeric(
        population["minutes_first_attempt_to_completion"],
        metric_name="minutes_first_attempt_to_completion",
    )

    return {
        "final_completion_authoring_mode": mode,
        "distinct_study_count": study_count,
        "study_count_with_no_completed_attempt": no_completion_count,
        "study_count_with_preceding_incomplete_attempts": preceding_count,
        "study_percentage_with_preceding_incomplete_attempts": _percentage(
            preceding_count,
            study_count,
        ),
        "total_preceding_incomplete_attempt_count": int(
            population["preceding_incomplete_attempt_count"].sum()
        ),
        "total_preceding_ai_error_attempt_count": int(
            population["preceding_ai_error_attempt_count"].sum()
        ),
        "total_preceding_ai_error_without_stack_trace_attempt_count": int(
            population["preceding_ai_error_without_stack_trace_attempt_count"].sum()
        ),
        "total_preceding_user_dropped_attempt_count": int(
            population["preceding_user_dropped_attempt_count"].sum()
        ),
        "minimum_preceding_incomplete_attempt_count": (preceding_distribution.minimum),
        "percentile_25_preceding_incomplete_attempt_count": (
            preceding_distribution.percentile_25
        ),
        "median_preceding_incomplete_attempt_count": (preceding_distribution.median),
        "average_preceding_incomplete_attempt_count": (preceding_distribution.average),
        "percentile_75_preceding_incomplete_attempt_count": (
            preceding_distribution.percentile_75
        ),
        "percentile_90_preceding_incomplete_attempt_count": (
            preceding_distribution.percentile_90
        ),
        "maximum_preceding_incomplete_attempt_count": (preceding_distribution.maximum),
        "minimum_minutes_first_attempt_to_completion": (completion_minutes.minimum),
        "median_minutes_first_attempt_to_completion": (completion_minutes.median),
        "average_minutes_first_attempt_to_completion": (completion_minutes.average),
        "standard_deviation_minutes_first_attempt_to_completion": (
            completion_minutes.standard_deviation
        ),
        "maximum_minutes_first_attempt_to_completion": (completion_minutes.maximum),
        "study_count_with_author_change_before_completion": (author_change_count),
        "study_percentage_with_author_change_before_completion": _percentage(
            author_change_count,
            study_count,
        ),
    }


def build_study_attempt_history_summary(
    studies: pd.DataFrame,
) -> pd.DataFrame:
    """Return four explicit study-history populations."""
    rows = [
        _study_history_summary_row(
            studies,
            mode=mode,
        )
        for mode in (
            _ALL,
            _AI,
            _MANUAL,
            _NOT_COMPLETED,
        )
    ]

    return pd.DataFrame.from_records(
        rows,
        columns=list(_STUDY_ATTEMPT_HISTORY_COLUMNS),
    )


def _handoff_category(
    study: pd.Series,
) -> str:
    """Return one mutually exclusive completed-study handoff category."""
    preceding_count = int(study["preceding_incomplete_attempt_count"])

    if preceding_count == 0:
        return "NO_PRECEDING_ATTEMPT"

    same_count = int(study["preceding_incomplete_attempt_count_by_completion_author"])
    other_count = int(study["preceding_incomplete_attempt_count_by_other_authors"])

    if same_count and other_count:
        return "MIXED_COMPLETION_AND_OTHER_AUTHORS"

    if same_count:
        return "ALL_PRECEDING_ATTEMPTS_BY_COMPLETION_AUTHOR"

    return "ALL_PRECEDING_ATTEMPTS_BY_OTHER_AUTHORS"


def _preceding_mode_and_result(
    attempts: pd.DataFrame,
    *,
    study_num: str,
) -> tuple[str, str]:
    """Return immediately preceding mode and result, or NONE values."""
    preceding = attempts.loc[
        attempts["study_num"].eq(study_num)
        & attempts["is_preceding_incomplete_attempt"].eq(True)
    ]

    if preceding.empty:
        return "NONE", "NONE"

    last = preceding.sort_values(
        by=["attempt_sequence_number", "audit_record_id"],
        kind="stable",
    ).iloc[-1]

    return (
        str(last["attempt_authoring_mode"]),
        str(last["attempt_result"]),
    )


def _handoff_rows(
    *,
    attempts: pd.DataFrame,
    studies: pd.DataFrame,
) -> list[dict[str, object]]:
    """Return one intermediate row per completed study."""
    completed = studies.loc[studies["study_is_completed"].eq(True)]
    population_count = len(completed)
    rows: list[dict[str, object]] = []

    for _, study in completed.iterrows():
        study_num = str(study["study_num"])
        preceding_mode, preceding_result = _preceding_mode_and_result(
            attempts,
            study_num=study_num,
        )
        rows.append(
            {
                "completed_attempt_authoring_mode": str(
                    study["completed_attempt_authoring_mode"]
                ),
                "preceding_attempt_authoring_mode": preceding_mode,
                "preceding_attempt_result": preceding_result,
                "author_handoff_category": _handoff_category(study),
                "study_num": study_num,
                "minutes_first_attempt_to_completion": study[
                    "minutes_first_attempt_to_completion"
                ],
                "population_distinct_completed_study_count": population_count,
            }
        )

    return rows


def _aggregate_handoff_group(
    group: pd.DataFrame,
) -> dict[str, object]:
    """Return one grouped handoff summary row."""
    first = group.iloc[0]
    distribution = describe_numeric(
        group["minutes_first_attempt_to_completion"],
        metric_name="minutes_first_attempt_to_completion",
    )
    count = int(group["study_num"].nunique())
    population_count = int(first["population_distinct_completed_study_count"])

    return {
        "completed_attempt_authoring_mode": first["completed_attempt_authoring_mode"],
        "preceding_attempt_authoring_mode": first["preceding_attempt_authoring_mode"],
        "preceding_attempt_result": first["preceding_attempt_result"],
        "author_handoff_category": first["author_handoff_category"],
        "distinct_completed_study_count": count,
        "population_distinct_completed_study_count": population_count,
        "distinct_completed_study_percentage": _percentage(
            count,
            population_count,
        ),
        "minimum_minutes_first_attempt_to_completion": distribution.minimum,
        "percentile_25_minutes_first_attempt_to_completion": (
            distribution.percentile_25
        ),
        "median_minutes_first_attempt_to_completion": distribution.median,
        "average_minutes_first_attempt_to_completion": distribution.average,
        "standard_deviation_minutes_first_attempt_to_completion": (
            distribution.standard_deviation
        ),
        "percentile_75_minutes_first_attempt_to_completion": (
            distribution.percentile_75
        ),
        "maximum_minutes_first_attempt_to_completion": distribution.maximum,
    }


def build_author_handoff_summary(
    *,
    attempts: pd.DataFrame,
    studies: pd.DataFrame,
) -> pd.DataFrame:
    """Return grouped author-handoff pathways for completed studies."""
    rows = _handoff_rows(
        attempts=attempts,
        studies=studies,
    )

    if not rows:
        return pd.DataFrame(columns=list(_AUTHOR_HANDOFF_COLUMNS))

    detail = pd.DataFrame.from_records(rows)
    grouping_columns = [
        "completed_attempt_authoring_mode",
        "preceding_attempt_authoring_mode",
        "preceding_attempt_result",
        "author_handoff_category",
    ]
    summary_rows = [
        _aggregate_handoff_group(group)
        for _, group in detail.groupby(
            grouping_columns,
            sort=True,
            dropna=False,
        )
    ]

    return pd.DataFrame.from_records(
        summary_rows,
        columns=list(_AUTHOR_HANDOFF_COLUMNS),
    )
