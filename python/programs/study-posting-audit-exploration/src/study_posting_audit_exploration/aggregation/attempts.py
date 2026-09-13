"""Grouped attempt counts and timing distributions."""

from dataclasses import dataclass

import pandas as pd

from study_posting_audit_exploration.statistics import describe_numeric

_ALL = "ALL"
_MISSING_GROUP_VALUE = "MISSING"

_GROUPED_ATTEMPT_COLUMNS: tuple[str, ...] = (
    "attempt_completion_group",
    "attempt_result",
    "attempt_authoring_mode",
    "grouping_dimension_1_name",
    "grouping_dimension_1_value",
    "grouping_dimension_2_name",
    "grouping_dimension_2_value",
    "attempt_count",
    "population_attempt_count",
    "attempt_percentage_within_population",
    "attempt_count_with_nonmissing_study_info_page_time",
    "attempt_count_missing_study_info_page_time",
    "minimum_study_info_page_minutes",
    "percentile_25_study_info_page_minutes",
    "median_study_info_page_minutes",
    "average_study_info_page_minutes",
    "standard_deviation_study_info_page_minutes",
    "percentile_75_study_info_page_minutes",
    "percentile_90_study_info_page_minutes",
    "maximum_study_info_page_minutes",
    "attempt_count_with_nonmissing_total_attempt_time",
    "attempt_count_missing_total_attempt_time",
    "minimum_total_attempt_minutes",
    "percentile_25_total_attempt_minutes",
    "median_total_attempt_minutes",
    "average_total_attempt_minutes",
    "standard_deviation_total_attempt_minutes",
    "percentile_75_total_attempt_minutes",
    "percentile_90_total_attempt_minutes",
    "maximum_total_attempt_minutes",
)


@dataclass(frozen=True, slots=True)
class _AttemptGroupLabels:
    """Labels that identify one grouped-attempt population."""

    completion_group: str
    attempt_result: str
    authoring_mode: str
    dimension_1_name: str
    dimension_1_value: str
    dimension_2_name: str = "NONE"
    dimension_2_value: str = "NONE"


def _percentage(
    numerator: int,
    denominator: int,
) -> float | None:
    """Return a percentage or ``None`` for an empty denominator."""
    if denominator == 0:
        return None

    return 100.0 * numerator / denominator


def _group_value(value: object) -> str:
    """Return one explicit display value for a pandas grouping key."""
    if value is None or value is pd.NA or value is pd.NaT:
        return _MISSING_GROUP_VALUE

    return str(value)


def _summary_row(
    group: pd.DataFrame,
    *,
    population_count: int,
    labels: _AttemptGroupLabels,
) -> dict[str, object]:
    """Return one explicit grouped-attempt summary row."""
    study_info = describe_numeric(
        group["study_info_page_minutes"],
        metric_name="study_info_page_minutes",
    )
    total_time = describe_numeric(
        group["total_attempt_duration_minutes"],
        metric_name="total_attempt_duration_minutes",
    )
    attempt_count = len(group)

    return {
        "attempt_completion_group": labels.completion_group,
        "attempt_result": labels.attempt_result,
        "attempt_authoring_mode": labels.authoring_mode,
        "grouping_dimension_1_name": labels.dimension_1_name,
        "grouping_dimension_1_value": labels.dimension_1_value,
        "grouping_dimension_2_name": labels.dimension_2_name,
        "grouping_dimension_2_value": labels.dimension_2_value,
        "attempt_count": attempt_count,
        "population_attempt_count": population_count,
        "attempt_percentage_within_population": _percentage(
            attempt_count,
            population_count,
        ),
        "attempt_count_with_nonmissing_study_info_page_time": (
            study_info.nonmissing_count
        ),
        "attempt_count_missing_study_info_page_time": (study_info.missing_count),
        "minimum_study_info_page_minutes": study_info.minimum,
        "percentile_25_study_info_page_minutes": study_info.percentile_25,
        "median_study_info_page_minutes": study_info.median,
        "average_study_info_page_minutes": study_info.average,
        "standard_deviation_study_info_page_minutes": (study_info.standard_deviation),
        "percentile_75_study_info_page_minutes": study_info.percentile_75,
        "percentile_90_study_info_page_minutes": study_info.percentile_90,
        "maximum_study_info_page_minutes": study_info.maximum,
        "attempt_count_with_nonmissing_total_attempt_time": (
            total_time.nonmissing_count
        ),
        "attempt_count_missing_total_attempt_time": total_time.missing_count,
        "minimum_total_attempt_minutes": total_time.minimum,
        "percentile_25_total_attempt_minutes": total_time.percentile_25,
        "median_total_attempt_minutes": total_time.median,
        "average_total_attempt_minutes": total_time.average,
        "standard_deviation_total_attempt_minutes": (total_time.standard_deviation),
        "percentile_75_total_attempt_minutes": total_time.percentile_75,
        "percentile_90_total_attempt_minutes": total_time.percentile_90,
        "maximum_total_attempt_minutes": total_time.maximum,
    }


def _single_dimension_labels(
    *,
    column_name: str,
    dimension_name: str,
    value: object,
) -> _AttemptGroupLabels:
    """Return labels for one primary attempt dimension."""
    group_value = _group_value(value)

    return _AttemptGroupLabels(
        completion_group=(
            group_value if column_name == "attempt_completion_group" else _ALL
        ),
        attempt_result=(group_value if column_name == "attempt_result" else _ALL),
        authoring_mode=(
            group_value if column_name == "attempt_authoring_mode" else _ALL
        ),
        dimension_1_name=dimension_name,
        dimension_1_value=group_value,
    )


def _primary_population_rows(
    attempts: pd.DataFrame,
) -> list[dict[str, object]]:
    """Return overall and primary attempt-status rows."""
    population_count = len(attempts)
    rows = [
        _summary_row(
            attempts,
            population_count=population_count,
            labels=_AttemptGroupLabels(
                completion_group=_ALL,
                attempt_result=_ALL,
                authoring_mode=_ALL,
                dimension_1_name="ALL",
                dimension_1_value="ALL",
            ),
        )
    ]

    grouping_specs = (
        ("attempt_completion_group", "COMPLETION_GROUP"),
        ("attempt_result", "ATTEMPT_RESULT"),
        ("attempt_authoring_mode", "AUTHORING_MODE"),
    )

    for column_name, dimension_name in grouping_specs:
        for value, group in attempts.groupby(
            column_name,
            sort=True,
            dropna=False,
        ):
            rows.append(
                _summary_row(
                    group,
                    population_count=population_count,
                    labels=_single_dimension_labels(
                        column_name=column_name,
                        dimension_name=dimension_name,
                        value=value,
                    ),
                )
            )

    return rows


def _completion_by_mode_rows(
    attempts: pd.DataFrame,
) -> list[dict[str, object]]:
    """Return completion-group by authoring-mode rows."""
    population_count = len(attempts)
    rows: list[dict[str, object]] = []

    for keys, group in attempts.groupby(
        ["attempt_completion_group", "attempt_authoring_mode"],
        sort=True,
        dropna=False,
    ):
        completion_group, authoring_mode = keys
        completion_value = _group_value(completion_group)
        mode_value = _group_value(authoring_mode)
        rows.append(
            _summary_row(
                group,
                population_count=population_count,
                labels=_AttemptGroupLabels(
                    completion_group=completion_value,
                    attempt_result=_ALL,
                    authoring_mode=mode_value,
                    dimension_1_name="COMPLETION_GROUP",
                    dimension_1_value=completion_value,
                    dimension_2_name="AUTHORING_MODE",
                    dimension_2_value=mode_value,
                ),
            )
        )

    return rows


def _result_by_mode_rows(
    attempts: pd.DataFrame,
) -> list[dict[str, object]]:
    """Return exact-result by authoring-mode rows."""
    population_count = len(attempts)
    rows: list[dict[str, object]] = []

    for keys, group in attempts.groupby(
        ["attempt_result", "attempt_authoring_mode"],
        sort=True,
        dropna=False,
    ):
        attempt_result, authoring_mode = keys
        result_value = _group_value(attempt_result)
        mode_value = _group_value(authoring_mode)
        rows.append(
            _summary_row(
                group,
                population_count=population_count,
                labels=_AttemptGroupLabels(
                    completion_group=_ALL,
                    attempt_result=result_value,
                    authoring_mode=mode_value,
                    dimension_1_name="ATTEMPT_RESULT",
                    dimension_1_value=result_value,
                    dimension_2_name="AUTHORING_MODE",
                    dimension_2_value=mode_value,
                ),
            )
        )

    return rows


def _single_source_dimension_rows(
    attempts: pd.DataFrame,
) -> list[dict[str, object]]:
    """Return source-type and content-source rows."""
    population_count = len(attempts)
    rows: list[dict[str, object]] = []
    grouping_specs = (
        ("source_type", "SOURCE_TYPE"),
        ("study_content_source", "STUDY_CONTENT_SOURCE"),
    )

    for column_name, dimension_name in grouping_specs:
        for value, group in attempts.groupby(
            column_name,
            sort=True,
            dropna=False,
        ):
            rows.append(
                _summary_row(
                    group,
                    population_count=population_count,
                    labels=_AttemptGroupLabels(
                        completion_group=_ALL,
                        attempt_result=_ALL,
                        authoring_mode=_ALL,
                        dimension_1_name=dimension_name,
                        dimension_1_value=_group_value(value),
                    ),
                )
            )

    return rows


def _combined_source_rows(
    attempts: pd.DataFrame,
) -> list[dict[str, object]]:
    """Return source-type by content-source rows."""
    population_count = len(attempts)
    rows: list[dict[str, object]] = []

    for keys, group in attempts.groupby(
        ["source_type", "study_content_source"],
        sort=True,
        dropna=False,
    ):
        source_type, content_source = keys
        rows.append(
            _summary_row(
                group,
                population_count=population_count,
                labels=_AttemptGroupLabels(
                    completion_group=_ALL,
                    attempt_result=_ALL,
                    authoring_mode=_ALL,
                    dimension_1_name="SOURCE_TYPE",
                    dimension_1_value=_group_value(source_type),
                    dimension_2_name="STUDY_CONTENT_SOURCE",
                    dimension_2_value=_group_value(content_source),
                ),
            )
        )

    return rows


def build_grouped_attempt_summary(
    attempts: pd.DataFrame,
) -> pd.DataFrame:
    """Return grouped attempt counts and timing distributions."""
    rows = [
        *_primary_population_rows(attempts),
        *_completion_by_mode_rows(attempts),
        *_result_by_mode_rows(attempts),
        *_single_source_dimension_rows(attempts),
        *_combined_source_rows(attempts),
    ]

    return pd.DataFrame.from_records(
        rows,
        columns=list(_GROUPED_ATTEMPT_COLUMNS),
    )
