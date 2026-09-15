"""Grouped distinct-study summaries."""

from dataclasses import dataclass

import pandas as pd

from study_posting_audit_exploration.statistics import describe_numeric

_ALL = "ALL"
_AI = "AI"
_MANUAL = "MANUAL"
_NOT_COMPLETED = "NOT_COMPLETED"
_MISSING = "MISSING"

GROUPED_STUDY_COLUMNS: tuple[str, ...] = (
    "study_population_name",
    "final_completion_authoring_mode",
    "grouping_dimension_1_name",
    "grouping_dimension_1_value",
    "grouping_dimension_2_name",
    "grouping_dimension_2_value",
    "group_values_are_mutually_exclusive",
    "distinct_study_count",
    "population_distinct_study_count",
    "distinct_study_percentage_within_population",
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
    "maximum_preceding_incomplete_attempt_count",
    "minimum_minutes_first_attempt_to_completion",
    "percentile_25_minutes_first_attempt_to_completion",
    "median_minutes_first_attempt_to_completion",
    "average_minutes_first_attempt_to_completion",
    "standard_deviation_minutes_first_attempt_to_completion",
    "percentile_75_minutes_first_attempt_to_completion",
    "maximum_minutes_first_attempt_to_completion",
    "minimum_completed_attempt_study_info_page_minutes",
    "median_completed_attempt_study_info_page_minutes",
    "average_completed_attempt_study_info_page_minutes",
    "standard_deviation_completed_attempt_study_info_page_minutes",
    "maximum_completed_attempt_study_info_page_minutes",
)


@dataclass(frozen=True, slots=True)
class _StudyGroupLabels:
    """Labels for one grouped-study population."""

    population_name: str
    completion_mode: str
    dimension_1_name: str
    dimension_1_value: str
    dimension_2_name: str = "NONE"
    dimension_2_value: str = "NONE"
    values_are_mutually_exclusive: bool = True


def _percentage(numerator: int, denominator: int) -> float | None:
    """Return a percentage or ``None`` for an empty denominator."""
    if denominator == 0:
        return None

    return 100.0 * numerator / denominator


def _group_value(value: object) -> str:
    """Return an explicit group value."""
    if value is None or value is pd.NA or value is pd.NaT:
        return _MISSING

    return str(value)


def _population(
    studies: pd.DataFrame,
    *,
    population_name: str,
) -> pd.DataFrame:
    """Return one explicit study population."""
    if population_name == "ALL_STUDIES_WITH_ATTEMPTS":
        return studies

    if population_name == "COMPLETED_STUDIES":
        return studies.loc[studies["study_is_completed"].eq(True)]

    return studies.loc[studies["study_is_completed"].eq(False)]


def _completion_mode_population(
    population: pd.DataFrame,
    *,
    completion_mode: str,
) -> pd.DataFrame:
    """Return one completion-mode subset."""
    if completion_mode == _ALL:
        return population

    if completion_mode == _NOT_COMPLETED:
        return population.loc[population["study_is_completed"].eq(False)]

    return population.loc[
        population["study_is_completed"].eq(True)
        & population["completed_attempt_authoring_mode"].eq(completion_mode)
    ]


def _summary_row(
    group: pd.DataFrame,
    *,
    population_count: int,
    labels: _StudyGroupLabels,
) -> dict[str, object]:
    """Return one grouped-study summary row."""
    study_count = int(group["study_num"].nunique())
    preceding_study_count = int(group["preceding_incomplete_attempt_count"].gt(0).sum())
    preceding = describe_numeric(
        group["preceding_incomplete_attempt_count"],
        metric_name="preceding_incomplete_attempt_count",
    )
    completion_minutes = describe_numeric(
        group["minutes_first_attempt_to_completion"],
        metric_name="minutes_first_attempt_to_completion",
    )
    study_info_minutes = describe_numeric(
        group["completed_attempt_study_info_page_minutes"],
        metric_name="completed_attempt_study_info_page_minutes",
    )

    return {
        "study_population_name": labels.population_name,
        "final_completion_authoring_mode": labels.completion_mode,
        "grouping_dimension_1_name": labels.dimension_1_name,
        "grouping_dimension_1_value": labels.dimension_1_value,
        "grouping_dimension_2_name": labels.dimension_2_name,
        "grouping_dimension_2_value": labels.dimension_2_value,
        "group_values_are_mutually_exclusive": (labels.values_are_mutually_exclusive),
        "distinct_study_count": study_count,
        "population_distinct_study_count": population_count,
        "distinct_study_percentage_within_population": _percentage(
            study_count,
            population_count,
        ),
        "study_count_with_preceding_incomplete_attempts": (preceding_study_count),
        "study_percentage_with_preceding_incomplete_attempts": _percentage(
            preceding_study_count,
            study_count,
        ),
        "total_preceding_incomplete_attempt_count": int(
            group["preceding_incomplete_attempt_count"].sum()
        ),
        "total_preceding_ai_error_attempt_count": int(
            group["preceding_ai_error_attempt_count"].sum()
        ),
        "total_preceding_ai_error_without_stack_trace_attempt_count": int(
            group["preceding_ai_error_without_stack_trace_attempt_count"].sum()
        ),
        "total_preceding_user_dropped_attempt_count": int(
            group["preceding_user_dropped_attempt_count"].sum()
        ),
        "minimum_preceding_incomplete_attempt_count": preceding.minimum,
        "percentile_25_preceding_incomplete_attempt_count": (preceding.percentile_25),
        "median_preceding_incomplete_attempt_count": preceding.median,
        "average_preceding_incomplete_attempt_count": preceding.average,
        "percentile_75_preceding_incomplete_attempt_count": (preceding.percentile_75),
        "maximum_preceding_incomplete_attempt_count": preceding.maximum,
        "minimum_minutes_first_attempt_to_completion": (completion_minutes.minimum),
        "percentile_25_minutes_first_attempt_to_completion": (
            completion_minutes.percentile_25
        ),
        "median_minutes_first_attempt_to_completion": (completion_minutes.median),
        "average_minutes_first_attempt_to_completion": (completion_minutes.average),
        "standard_deviation_minutes_first_attempt_to_completion": (
            completion_minutes.standard_deviation
        ),
        "percentile_75_minutes_first_attempt_to_completion": (
            completion_minutes.percentile_75
        ),
        "maximum_minutes_first_attempt_to_completion": (completion_minutes.maximum),
        "minimum_completed_attempt_study_info_page_minutes": (
            study_info_minutes.minimum
        ),
        "median_completed_attempt_study_info_page_minutes": (study_info_minutes.median),
        "average_completed_attempt_study_info_page_minutes": (
            study_info_minutes.average
        ),
        "standard_deviation_completed_attempt_study_info_page_minutes": (
            study_info_minutes.standard_deviation
        ),
        "maximum_completed_attempt_study_info_page_minutes": (
            study_info_minutes.maximum
        ),
    }


def _population_modes(
    studies: pd.DataFrame,
) -> list[tuple[str, str, pd.DataFrame, int]]:
    """Return every nonempty population/mode combination."""
    combinations: list[tuple[str, str, pd.DataFrame, int]] = []

    for population_name in (
        "ALL_STUDIES_WITH_ATTEMPTS",
        "COMPLETED_STUDIES",
        "STUDIES_WITHOUT_COMPLETION",
    ):
        population = _population(
            studies,
            population_name=population_name,
        )
        population_count = int(population["study_num"].nunique())

        for completion_mode in (
            _ALL,
            _AI,
            _MANUAL,
            _NOT_COMPLETED,
        ):
            mode_population = _completion_mode_population(
                population,
                completion_mode=completion_mode,
            )

            if mode_population.empty and completion_mode != _ALL:
                continue

            combinations.append(
                (
                    population_name,
                    completion_mode,
                    mode_population,
                    population_count,
                )
            )

    return combinations


def _base_rows(studies: pd.DataFrame) -> list[dict[str, object]]:
    """Return ungrouped rows for every population and mode."""
    return [
        _summary_row(
            mode_population,
            population_count=population_count,
            labels=_StudyGroupLabels(
                population_name=population_name,
                completion_mode=completion_mode,
                dimension_1_name="ALL",
                dimension_1_value="ALL",
            ),
        )
        for (
            population_name,
            completion_mode,
            mode_population,
            population_count,
        ) in _population_modes(studies)
    ]


def _single_dimension_rows(
    studies: pd.DataFrame,
) -> list[dict[str, object]]:
    """Return one-dimensional mutually exclusive study groups."""
    rows: list[dict[str, object]] = []
    grouping_specs = (
        ("study_participant_type", "STUDY_PARTICIPANT_TYPE"),
        ("study_department", "STUDY_DEPARTMENT"),
        ("source_type", "SOURCE_TYPE"),
        ("study_content_source", "STUDY_CONTENT_SOURCE"),
    )

    for (
        population_name,
        completion_mode,
        mode_population,
        population_count,
    ) in _population_modes(studies):
        if mode_population.empty:
            continue

        for column_name, dimension_name in grouping_specs:
            for value, group in mode_population.groupby(
                column_name,
                sort=True,
                dropna=False,
            ):
                rows.append(
                    _summary_row(
                        group,
                        population_count=population_count,
                        labels=_StudyGroupLabels(
                            population_name=population_name,
                            completion_mode=completion_mode,
                            dimension_1_name=dimension_name,
                            dimension_1_value=_group_value(value),
                        ),
                    )
                )

    return rows


def _two_dimension_rows(
    studies: pd.DataFrame,
) -> list[dict[str, object]]:
    """Return approved mutually exclusive two-dimensional study groups."""
    rows: list[dict[str, object]] = []
    grouping_specs = (
        (
            "study_participant_type",
            "STUDY_PARTICIPANT_TYPE",
            "study_department",
            "STUDY_DEPARTMENT",
        ),
        (
            "source_type",
            "SOURCE_TYPE",
            "study_content_source",
            "STUDY_CONTENT_SOURCE",
        ),
    )

    for (
        population_name,
        completion_mode,
        mode_population,
        population_count,
    ) in _population_modes(studies):
        if mode_population.empty:
            continue

        for (
            column_1,
            dimension_1,
            column_2,
            dimension_2,
        ) in grouping_specs:
            for keys, group in mode_population.groupby(
                [column_1, column_2],
                sort=True,
                dropna=False,
            ):
                value_1, value_2 = keys
                rows.append(
                    _summary_row(
                        group,
                        population_count=population_count,
                        labels=_StudyGroupLabels(
                            population_name=population_name,
                            completion_mode=completion_mode,
                            dimension_1_name=dimension_1,
                            dimension_1_value=_group_value(value_1),
                            dimension_2_name=dimension_2,
                            dimension_2_value=_group_value(value_2),
                        ),
                    )
                )

    return rows


def _appointment_rows(
    studies: pd.DataFrame,
    appointments: pd.DataFrame,
) -> list[dict[str, object]]:
    """Return non-mutually-exclusive appointment groups."""
    rows: list[dict[str, object]] = []
    appointment_specs = (
        ("AUTHOR", "appointment_title", "AUTHOR_APPOINTMENT_TITLE"),
        (
            "AUTHOR",
            "appointment_department",
            "AUTHOR_APPOINTMENT_DEPARTMENT",
        ),
        ("AUTHOR", "appointment_school", "AUTHOR_APPOINTMENT_SCHOOL"),
        ("PI", "appointment_title", "PI_APPOINTMENT_TITLE"),
        ("PI", "appointment_department", "PI_APPOINTMENT_DEPARTMENT"),
        ("PI", "appointment_school", "PI_APPOINTMENT_SCHOOL"),
    )

    for (
        population_name,
        completion_mode,
        mode_population,
        population_count,
    ) in _population_modes(studies):
        if mode_population.empty:
            continue

        for source, column_name, dimension_name in appointment_specs:
            selected_appointments = appointments.loc[
                appointments["appointment_source"].eq(source)
            ]
            joined = mode_population.merge(
                selected_appointments[
                    [
                        "study_num",
                        column_name,
                    ]
                ],
                on="study_num",
                how="inner",
                validate="one_to_many",
            )

            for value, group in joined.groupby(
                column_name,
                sort=True,
                dropna=False,
            ):
                rows.append(
                    _summary_row(
                        group.drop_duplicates(subset=["study_num"]),
                        population_count=population_count,
                        labels=_StudyGroupLabels(
                            population_name=population_name,
                            completion_mode=completion_mode,
                            dimension_1_name=dimension_name,
                            dimension_1_value=_group_value(value),
                            values_are_mutually_exclusive=False,
                        ),
                    )
                )

    return rows


def build_grouped_study_summary(
    studies: pd.DataFrame,
    *,
    appointments: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Return grouped study counts and completion-history distributions."""
    rows = [
        *_base_rows(studies),
        *_single_dimension_rows(studies),
        *_two_dimension_rows(studies),
    ]

    if appointments is not None and not appointments.empty:
        rows.extend(
            _appointment_rows(
                studies,
                appointments,
            )
        )

    return pd.DataFrame.from_records(
        rows,
        columns=list(GROUPED_STUDY_COLUMNS),
    )
