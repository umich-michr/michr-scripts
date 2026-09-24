from collections.abc import Callable
import json

import pandas as pd
import plotly.graph_objects as go
import pytest

from study_posting_audit_exploration import (
    ExplorationValidationError,
)
from study_posting_audit_exploration.publication import (
    ExplorationChartInputs,
    ExplorationCharts,
    SourcePopulationChartSpec,
    build_attempt_outcomes_chart,
    build_attempt_timing_chart,
    build_author_appointment_context_chart,
    build_author_attempt_start_experience_chart,
    build_author_experience_chart,
    build_author_handoff_chart,
    build_compensation_offer_composition_chart,
    build_compensation_suggestion_use_chart,
    build_completed_study_author_context_chart,
    build_completed_study_mix_chart,
    build_content_source_concordance_chart,
    build_edit_readability_relationship_chart,
    build_exploration_charts,
    build_repeated_source_consistency_chart,
    build_retry_pathways_chart,
    build_source_input_method_chart,
    build_source_size_latency_chart,
    build_study_completion_pathways_chart,
    build_suggestion_selection_by_index_chart,
    build_suggestion_selection_by_kind_chart,
)
from study_posting_audit_exploration.publication.charts import (
    build_field_selected_outcomes_chart,
    build_field_suggestion_adoption_chart,
    build_final_grade_bands_chart,
    build_readability_change_direction_chart,
    build_selected_vs_unselected_readability_chart,
)


def overview_rows() -> pd.DataFrame:
    """Return synthetic aggregate-only overview rows."""
    counts = {
        "all_attempt_count": ("All attempts", 10, 10),
        "complete_attempt_count": ("Completed attempts", 7, 10),
        "incomplete_attempt_count": ("Incomplete attempts", 3, 10),
        "completed_ai_attempt_count": ("Completed AI attempts", 4, 7),
        "completed_manual_attempt_count": ("Completed manual attempts", 3, 7),
        "incomplete_ai_attempt_count": ("Incomplete AI attempts", 2, 3),
        "incomplete_manual_attempt_count": ("Incomplete manual attempts", 1, 3),
    }
    rows: list[dict[str, object]] = []

    for metric_name, (label, count, denominator) in counts.items():
        rows.append(
            {
                "overview_metric_name": metric_name,
                "overview_metric_label": label,
                "metric_count": count,
                "metric_denominator_count": denominator,
                "metric_percentage": (
                    100.0 * count / denominator if denominator else None
                ),
                "metric_denominator_definition": (
                    "All audit attempts."
                    if metric_name == "all_attempt_count"
                    else "Published aggregate denominator."
                ),
            }
        )

    return pd.DataFrame.from_records(rows)


def grouped_attempt_rows() -> pd.DataFrame:
    """Return synthetic aggregate-only attempt rows."""
    rows: list[dict[str, object]] = [
        {
            "attempt_completion_group": "COMPLETE",
            "attempt_result": "COMPLETE",
            "attempt_authoring_mode": "AI",
            "grouping_dimension_1_name": "ATTEMPT_RESULT",
            "grouping_dimension_2_name": "AUTHORING_MODE",
            "attempt_count": 4,
            "attempt_count_with_nonmissing_study_info_page_time": 4,
            "attempt_count_missing_study_info_page_time": 0,
            "percentile_25_study_info_page_minutes": 1.0,
            "median_study_info_page_minutes": 2.0,
            "percentile_75_study_info_page_minutes": 3.0,
            "percentile_90_study_info_page_minutes": 4.0,
            "attempt_count_with_nonmissing_total_attempt_time": 4,
            "attempt_count_missing_total_attempt_time": 0,
            "percentile_25_total_attempt_minutes": 2.0,
            "median_total_attempt_minutes": 3.0,
            "percentile_75_total_attempt_minutes": 4.0,
            "percentile_90_total_attempt_minutes": 5.0,
        },
        {
            "attempt_completion_group": "INCOMPLETE",
            "attempt_result": "USER_DROPPED",
            "attempt_authoring_mode": "AI",
            "grouping_dimension_1_name": "ATTEMPT_RESULT",
            "grouping_dimension_2_name": "AUTHORING_MODE",
            "attempt_count": 2,
            "attempt_count_with_nonmissing_study_info_page_time": 2,
            "attempt_count_missing_study_info_page_time": 0,
            "percentile_25_study_info_page_minutes": 0.5,
            "median_study_info_page_minutes": 0.75,
            "percentile_75_study_info_page_minutes": 1.0,
            "percentile_90_study_info_page_minutes": 1.25,
            "attempt_count_with_nonmissing_total_attempt_time": 0,
            "attempt_count_missing_total_attempt_time": 2,
            "percentile_25_total_attempt_minutes": None,
            "median_total_attempt_minutes": None,
            "percentile_75_total_attempt_minutes": None,
            "percentile_90_total_attempt_minutes": None,
        },
        {
            "attempt_completion_group": "COMPLETE",
            "attempt_result": "COMPLETE",
            "attempt_authoring_mode": "MANUAL",
            "grouping_dimension_1_name": "ATTEMPT_RESULT",
            "grouping_dimension_2_name": "AUTHORING_MODE",
            "attempt_count": 3,
            "attempt_count_with_nonmissing_study_info_page_time": 3,
            "attempt_count_missing_study_info_page_time": 0,
            "percentile_25_study_info_page_minutes": 2.0,
            "median_study_info_page_minutes": 3.0,
            "percentile_75_study_info_page_minutes": 4.0,
            "percentile_90_study_info_page_minutes": 5.0,
            "attempt_count_with_nonmissing_total_attempt_time": 3,
            "attempt_count_missing_total_attempt_time": 0,
            "percentile_25_total_attempt_minutes": 4.0,
            "median_total_attempt_minutes": 5.0,
            "percentile_75_total_attempt_minutes": 6.0,
            "percentile_90_total_attempt_minutes": 7.0,
        },
        {
            "attempt_completion_group": "COMPLETE",
            "attempt_result": "ALL",
            "attempt_authoring_mode": "AI",
            "grouping_dimension_1_name": "COMPLETION_GROUP",
            "grouping_dimension_2_name": "AUTHORING_MODE",
            "attempt_count": 4,
            "attempt_count_with_nonmissing_study_info_page_time": 4,
            "attempt_count_missing_study_info_page_time": 0,
            "percentile_25_study_info_page_minutes": 1.0,
            "median_study_info_page_minutes": 2.0,
            "percentile_75_study_info_page_minutes": 3.0,
            "percentile_90_study_info_page_minutes": 4.0,
            "attempt_count_with_nonmissing_total_attempt_time": 4,
            "attempt_count_missing_total_attempt_time": 0,
            "percentile_25_total_attempt_minutes": 1.5,
            "median_total_attempt_minutes": 2.5,
            "percentile_75_total_attempt_minutes": 4.0,
            "percentile_90_total_attempt_minutes": 5.0,
        },
        {
            "attempt_completion_group": "COMPLETE",
            "attempt_result": "ALL",
            "attempt_authoring_mode": "MANUAL",
            "grouping_dimension_1_name": "COMPLETION_GROUP",
            "grouping_dimension_2_name": "AUTHORING_MODE",
            "attempt_count": 3,
            "attempt_count_with_nonmissing_study_info_page_time": 2,
            "attempt_count_missing_study_info_page_time": 1,
            "percentile_25_study_info_page_minutes": 2.0,
            "median_study_info_page_minutes": 3.0,
            "percentile_75_study_info_page_minutes": 4.0,
            "percentile_90_study_info_page_minutes": 5.0,
            "attempt_count_with_nonmissing_total_attempt_time": 3,
            "attempt_count_missing_total_attempt_time": 0,
            "percentile_25_total_attempt_minutes": 4.0,
            "median_total_attempt_minutes": 5.0,
            "percentile_75_total_attempt_minutes": 7.0,
            "percentile_90_total_attempt_minutes": 8.0,
        },
    ]

    return pd.DataFrame.from_records(rows)


def study_history_rows() -> pd.DataFrame:
    """Return synthetic aggregate-only study-pathway rows."""
    rows: list[dict[str, object]] = [
        {
            "final_completion_authoring_mode": "ALL",
            "distinct_study_count": 10,
            "study_count_with_preceding_incomplete_attempts": 4,
            "minimum_minutes_first_attempt_to_completion": 5.0,
            "median_minutes_first_attempt_to_completion": 20.0,
            "average_minutes_first_attempt_to_completion": 25.0,
            "standard_deviation_minutes_first_attempt_to_completion": 10.0,
            "maximum_minutes_first_attempt_to_completion": 60.0,
        },
        {
            "final_completion_authoring_mode": "AI",
            "distinct_study_count": 6,
            "study_count_with_preceding_incomplete_attempts": 2,
            "minimum_minutes_first_attempt_to_completion": 5.0,
            "median_minutes_first_attempt_to_completion": 15.0,
            "average_minutes_first_attempt_to_completion": 18.0,
            "standard_deviation_minutes_first_attempt_to_completion": 6.0,
            "maximum_minutes_first_attempt_to_completion": 35.0,
        },
        {
            "final_completion_authoring_mode": "MANUAL",
            "distinct_study_count": 4,
            "study_count_with_preceding_incomplete_attempts": 2,
            "minimum_minutes_first_attempt_to_completion": 10.0,
            "median_minutes_first_attempt_to_completion": 30.0,
            "average_minutes_first_attempt_to_completion": 35.0,
            "standard_deviation_minutes_first_attempt_to_completion": 12.0,
            "maximum_minutes_first_attempt_to_completion": 70.0,
        },
        {
            "final_completion_authoring_mode": "NOT_COMPLETED",
            "distinct_study_count": 2,
            "study_count_with_preceding_incomplete_attempts": 2,
            "minimum_minutes_first_attempt_to_completion": None,
            "median_minutes_first_attempt_to_completion": None,
            "average_minutes_first_attempt_to_completion": None,
            "standard_deviation_minutes_first_attempt_to_completion": None,
            "maximum_minutes_first_attempt_to_completion": None,
        },
    ]

    return pd.DataFrame.from_records(rows)


def author_handoff_rows() -> pd.DataFrame:
    """Return synthetic aggregate-only author-handoff rows."""
    return pd.DataFrame.from_records(
        [
            {
                "completed_attempt_authoring_mode": "AI",
                "author_handoff_category": "NO_PRECEDING_ATTEMPT",
                "distinct_completed_study_count": 4,
            },
            {
                "completed_attempt_authoring_mode": "AI",
                "author_handoff_category": ("ALL_PRECEDING_ATTEMPTS_BY_OTHER_AUTHORS"),
                "distinct_completed_study_count": 2,
            },
            {
                "completed_attempt_authoring_mode": "MANUAL",
                "author_handoff_category": (
                    "ALL_PRECEDING_ATTEMPTS_BY_COMPLETION_AUTHOR"
                ),
                "distinct_completed_study_count": 1,
            },
            {
                "completed_attempt_authoring_mode": "MANUAL",
                "author_handoff_category": ("MIXED_COMPLETION_AND_OTHER_AUTHORS"),
                "distinct_completed_study_count": 3,
            },
        ]
    )


def attempt_start_experience_rows() -> pd.DataFrame:
    """Return synthetic attempt-start author experience rows."""
    return pd.DataFrame.from_records(
        [
            {
                "author_adoption_group": "ALL_AUTHORS",
                "attempt_completion_group": "ALL",
                "attempt_authoring_mode": "AI",
                "experience_metric_name": (
                    "prior_studies_created_before_attempt_start_count"
                ),
                "experience_metric_unit": "studies",
                "author_attempt_count_with_nonmissing_metric": 6,
                "author_attempt_count_missing_metric": 1,
                "percentile_25_author_attempt_value": 1.0,
                "median_author_attempt_value": 2.0,
                "average_author_attempt_value": 9.0,
                "percentile_75_author_attempt_value": 4.0,
            },
            {
                "author_adoption_group": "ALL_AUTHORS",
                "attempt_completion_group": "ALL",
                "attempt_authoring_mode": "MANUAL",
                "experience_metric_name": (
                    "prior_studies_created_before_attempt_start_count"
                ),
                "experience_metric_unit": "studies",
                "author_attempt_count_with_nonmissing_metric": 4,
                "author_attempt_count_missing_metric": 0,
                "percentile_25_author_attempt_value": 3.0,
                "median_author_attempt_value": 5.0,
                "average_author_attempt_value": 6.0,
                "percentile_75_author_attempt_value": 8.0,
            },
            {
                "author_adoption_group": "AI_ONLY",
                "attempt_completion_group": "ALL",
                "attempt_authoring_mode": "AI",
                "experience_metric_name": (
                    "prior_studies_created_before_attempt_start_count"
                ),
                "experience_metric_unit": "studies",
                "author_attempt_count_with_nonmissing_metric": 3,
                "author_attempt_count_missing_metric": 0,
                "percentile_25_author_attempt_value": 0.0,
                "median_author_attempt_value": 1.0,
                "average_author_attempt_value": 1.5,
                "percentile_75_author_attempt_value": 2.0,
            },
        ]
    )


def current_author_experience_rows() -> pd.DataFrame:
    """Return synthetic aggregate-only query-time author experience rows."""
    metric_specs = (
        (
            "total_studies_created_as_of_report_query_count",
            "studies",
            (12.0, 8.0, 15.0, 11.0),
        ),
        (
            "other_study_memberships_as_of_report_query_count",
            "studies",
            (5.0, 3.0, 7.0, 4.0),
        ),
        (
            "distinct_login_days_as_of_report_query_count",
            "days",
            (30.0, 20.0, 45.0, 35.0),
        ),
        (
            "login_history_span_days_as_of_report_query",
            "days",
            (300.0, 180.0, 420.0, 360.0),
        ),
    )
    adoption_groups = (
        "ALL_AUTHORS",
        "AI_ONLY",
        "MANUAL_ONLY",
        "BOTH_AI_AND_MANUAL",
    )
    rows: list[dict[str, object]] = []

    for metric_name, metric_unit, medians in metric_specs:
        for adoption_group, median in zip(
            adoption_groups,
            medians,
            strict=True,
        ):
            rows.append(
                {
                    "author_adoption_group": adoption_group,
                    "experience_metric_name": metric_name,
                    "experience_metric_unit": metric_unit,
                    "author_count_with_nonmissing_metric": 4,
                    "author_count_missing_metric": 1,
                    "percentile_25_author_value": max(median - 2.0, 0.0),
                    "median_author_value": median,
                    "average_author_value": median + 1.0,
                    "percentile_75_author_value": median + 3.0,
                }
            )

    return pd.DataFrame.from_records(rows)


def grouped_study_rows() -> pd.DataFrame:
    """Return synthetic aggregate-only completed-study category rows."""
    rows: list[dict[str, object]] = [
        {
            "study_population_name": "COMPLETED_STUDIES",
            "final_completion_authoring_mode": "ALL",
            "grouping_dimension_1_name": "STUDY_PARTICIPANT_TYPE",
            "grouping_dimension_1_value": "HEALTHY",
            "grouping_dimension_2_name": "NONE",
            "group_values_are_mutually_exclusive": True,
            "distinct_study_count": 5,
            "population_distinct_study_count": 10,
            "distinct_study_percentage_within_population": 50.0,
        },
        {
            "study_population_name": "COMPLETED_STUDIES",
            "final_completion_authoring_mode": "ALL",
            "grouping_dimension_1_name": "STUDY_PARTICIPANT_TYPE",
            "grouping_dimension_1_value": "Other",
            "grouping_dimension_2_name": "NONE",
            "group_values_are_mutually_exclusive": True,
            "distinct_study_count": 3,
            "population_distinct_study_count": 10,
            "distinct_study_percentage_within_population": 30.0,
        },
        {
            "study_population_name": "COMPLETED_STUDIES",
            "final_completion_authoring_mode": "ALL",
            "grouping_dimension_1_name": "STUDY_PARTICIPANT_TYPE",
            "grouping_dimension_1_value": "MISSING",
            "grouping_dimension_2_name": "NONE",
            "group_values_are_mutually_exclusive": True,
            "distinct_study_count": 2,
            "population_distinct_study_count": 10,
            "distinct_study_percentage_within_population": 20.0,
        },
        {
            "study_population_name": "COMPLETED_STUDIES",
            "final_completion_authoring_mode": "ALL",
            "grouping_dimension_1_name": "STUDY_DEPARTMENT",
            "grouping_dimension_1_value": "Department A",
            "grouping_dimension_2_name": "NONE",
            "group_values_are_mutually_exclusive": True,
            "distinct_study_count": 6,
            "population_distinct_study_count": 10,
            "distinct_study_percentage_within_population": 60.0,
        },
        {
            "study_population_name": "COMPLETED_STUDIES",
            "final_completion_authoring_mode": "ALL",
            "grouping_dimension_1_name": "STUDY_DEPARTMENT",
            "grouping_dimension_1_value": "Department B",
            "grouping_dimension_2_name": "NONE",
            "group_values_are_mutually_exclusive": True,
            "distinct_study_count": 4,
            "population_distinct_study_count": 10,
            "distinct_study_percentage_within_population": 40.0,
        },
        {
            "study_population_name": "COMPLETED_STUDIES",
            "final_completion_authoring_mode": "AI",
            "grouping_dimension_1_name": "STUDY_DEPARTMENT",
            "grouping_dimension_1_value": "Excluded mode",
            "grouping_dimension_2_name": "NONE",
            "group_values_are_mutually_exclusive": True,
            "distinct_study_count": 1,
            "population_distinct_study_count": 10,
            "distinct_study_percentage_within_population": 10.0,
        },
        {
            "study_population_name": "COMPLETED_STUDIES",
            "final_completion_authoring_mode": "ALL",
            "grouping_dimension_1_name": "STUDY_PARTICIPANT_TYPE",
            "grouping_dimension_1_value": "Excluded two-way",
            "grouping_dimension_2_name": "STUDY_DEPARTMENT",
            "group_values_are_mutually_exclusive": True,
            "distinct_study_count": 1,
            "population_distinct_study_count": 10,
            "distinct_study_percentage_within_population": 10.0,
        },
    ]

    return pd.DataFrame.from_records(rows)


def completed_study_author_context_rows() -> pd.DataFrame:
    """Return synthetic completed-study completion-author context rows."""
    rows: list[dict[str, object]] = []

    for dimension_name, values in (
        ("EFFECTIVE_ROLE", (("COORDINATOR", 4, 2), ("PI", 2, 2))),
        ("PI_STATUS", (("NON_PI", 4, 2), ("PI", 2, 2))),
    ):
        for value, ai_count, manual_count in values:
            for mode, count, mode_total in (
                ("AI", ai_count, 6),
                ("MANUAL", manual_count, 4),
            ):
                rows.append(
                    {
                        "context_dimension_name": dimension_name,
                        "context_dimension_value": value,
                        "final_completion_authoring_mode": mode,
                        "completed_study_count": count,
                        "mode_completed_study_count": mode_total,
                        "all_completed_study_count": 10,
                        "completed_study_percentage_within_mode": (
                            100.0 * count / mode_total
                        ),
                        "completed_study_percentage_overall": 10.0 * count,
                        "distinct_completion_author_count": max(count - 1, 1),
                    }
                )

    return pd.DataFrame.from_records(rows)


def grouped_author_rows() -> pd.DataFrame:
    """Return synthetic aggregate-only author context rows."""
    rows: list[dict[str, object]] = [
        {
            "author_population_name": "ALL_AUTHORS",
            "attempt_completion_group": "ALL",
            "attempt_authoring_mode": "ALL",
            "effective_author_role": "ALL",
            "grouping_dimension_name": "ALL",
            "grouping_dimension_value": "ALL",
            "group_values_are_mutually_exclusive": True,
            "distinct_author_count": 10,
            "population_distinct_author_count": 10,
            "distinct_author_percentage_within_population": 100.0,
            "distinct_author_count_classified_as_pi": 3,
        },
        {
            "author_population_name": "ALL_AUTHORS",
            "attempt_completion_group": "ALL",
            "attempt_authoring_mode": "ALL",
            "effective_author_role": "TEAM_MEMBER",
            "grouping_dimension_name": "EFFECTIVE_AUTHOR_ROLE",
            "grouping_dimension_value": "TEAM_MEMBER",
            "group_values_are_mutually_exclusive": True,
            "distinct_author_count": 7,
            "population_distinct_author_count": 10,
            "distinct_author_percentage_within_population": 70.0,
            "distinct_author_count_classified_as_pi": 1,
        },
        {
            "author_population_name": "ALL_AUTHORS",
            "attempt_completion_group": "ALL",
            "attempt_authoring_mode": "ALL",
            "effective_author_role": "PI",
            "grouping_dimension_name": "EFFECTIVE_AUTHOR_ROLE",
            "grouping_dimension_value": "PI",
            "group_values_are_mutually_exclusive": True,
            "distinct_author_count": 3,
            "population_distinct_author_count": 10,
            "distinct_author_percentage_within_population": 30.0,
            "distinct_author_count_classified_as_pi": 3,
        },
        {
            "author_population_name": "ALL_AUTHORS",
            "attempt_completion_group": "ALL",
            "attempt_authoring_mode": "ALL",
            "effective_author_role": "ALL",
            "grouping_dimension_name": "AUTHOR_APPOINTMENT_SCHOOL",
            "grouping_dimension_value": "School A",
            "group_values_are_mutually_exclusive": False,
            "distinct_author_count": 6,
            "population_distinct_author_count": 10,
            "distinct_author_percentage_within_population": 60.0,
            "distinct_author_count_classified_as_pi": 2,
        },
        {
            "author_population_name": "ALL_AUTHORS",
            "attempt_completion_group": "ALL",
            "attempt_authoring_mode": "ALL",
            "effective_author_role": "ALL",
            "grouping_dimension_name": "AUTHOR_APPOINTMENT_SCHOOL",
            "grouping_dimension_value": "School B",
            "group_values_are_mutually_exclusive": False,
            "distinct_author_count": 5,
            "population_distinct_author_count": 10,
            "distinct_author_percentage_within_population": 50.0,
            "distinct_author_count_classified_as_pi": 2,
        },
        {
            "author_population_name": "ALL_AUTHORS",
            "attempt_completion_group": "ALL",
            "attempt_authoring_mode": "ALL",
            "effective_author_role": "ALL",
            "grouping_dimension_name": "PI_APPOINTMENT_SCHOOL",
            "grouping_dimension_value": "PI School",
            "group_values_are_mutually_exclusive": False,
            "distinct_author_count": 4,
            "population_distinct_author_count": 10,
            "distinct_author_percentage_within_population": 40.0,
            "distinct_author_count_classified_as_pi": 2,
        },
        {
            "author_population_name": "ALL_AUTHORS",
            "attempt_completion_group": "ALL",
            "attempt_authoring_mode": "ALL",
            "effective_author_role": "ALL",
            "grouping_dimension_name": "AUTHOR_APPOINTMENT_DEPARTMENT",
            "grouping_dimension_value": "Emergency Medicine",
            "group_values_are_mutually_exclusive": False,
            "distinct_author_count": 5,
            "population_distinct_author_count": 10,
            "distinct_author_percentage_within_population": 50.0,
            "distinct_author_count_classified_as_pi": 2,
        },
        {
            "author_population_name": "ALL_AUTHORS",
            "attempt_completion_group": "ALL",
            "attempt_authoring_mode": "ALL",
            "effective_author_role": "ALL",
            "grouping_dimension_name": "PI_APPOINTMENT_DEPARTMENT",
            "grouping_dimension_value": "Neurology",
            "group_values_are_mutually_exclusive": False,
            "distinct_author_count": 3,
            "population_distinct_author_count": 10,
            "distinct_author_percentage_within_population": 30.0,
            "distinct_author_count_classified_as_pi": 2,
        },
        {
            "author_population_name": "ALL_AUTHORS",
            "attempt_completion_group": "ALL",
            "attempt_authoring_mode": "ALL",
            "effective_author_role": "ALL",
            "grouping_dimension_name": "AUTHOR_APPOINTMENT_TITLE",
            "grouping_dimension_value": "PROFESSOR",
            "group_values_are_mutually_exclusive": False,
            "distinct_author_count": 6,
            "population_distinct_author_count": 10,
            "distinct_author_percentage_within_population": 60.0,
            "distinct_author_count_classified_as_pi": 2,
        },
        {
            "author_population_name": "ALL_AUTHORS",
            "attempt_completion_group": "ALL",
            "attempt_authoring_mode": "ALL",
            "effective_author_role": "ALL",
            "grouping_dimension_name": "PI_APPOINTMENT_TITLE",
            "grouping_dimension_value": "ASSOCIATE PROFESSOR",
            "group_values_are_mutually_exclusive": False,
            "distinct_author_count": 4,
            "population_distinct_author_count": 10,
            "distinct_author_percentage_within_population": 40.0,
            "distinct_author_count_classified_as_pi": 2,
        },
    ]

    return pd.DataFrame.from_records(rows)


def field_adoption_rows() -> pd.DataFrame:
    """Return synthetic aggregate-only field adoption rows."""
    return pd.DataFrame.from_records(
        [
            {
                "field_name": "title",
                "analysis_type": "TEXT",
                "completed_ai_attempt_count": 10,
                "completed_ai_attempt_count_with_suggestion_offered": 9,
                "completed_ai_attempt_count_with_suggestion_selected": 7,
                "completed_ai_attempt_count_selected_and_exactly_retained": 2,
                "completed_ai_attempt_count_selected_and_cosmetically_changed": 1,
                "completed_ai_attempt_count_selected_and_lightly_edited": 1,
                "completed_ai_attempt_count_selected_and_moderately_edited": 1,
                "completed_ai_attempt_count_selected_and_heavily_edited": 1,
                "completed_ai_attempt_count_selected_and_unclassified_edit": 1,
                "completed_ai_attempt_count_selected_and_replaced": 0,
                "completed_ai_attempt_count_selected_then_cleared": 0,
                "completed_ai_attempt_count_unassisted": 3,
                "suggestion_selection_percentage_among_attempts_with_offer": (
                    100.0 * 7.0 / 9.0
                ),
            },
            {
                "field_name": "description",
                "analysis_type": "TEXT",
                "completed_ai_attempt_count": 10,
                "completed_ai_attempt_count_with_suggestion_offered": 8,
                "completed_ai_attempt_count_with_suggestion_selected": 5,
                "completed_ai_attempt_count_selected_and_exactly_retained": 1,
                "completed_ai_attempt_count_selected_and_cosmetically_changed": 1,
                "completed_ai_attempt_count_selected_and_lightly_edited": 1,
                "completed_ai_attempt_count_selected_and_moderately_edited": 0,
                "completed_ai_attempt_count_selected_and_heavily_edited": 1,
                "completed_ai_attempt_count_selected_and_unclassified_edit": 0,
                "completed_ai_attempt_count_selected_and_replaced": 1,
                "completed_ai_attempt_count_selected_then_cleared": 0,
                "completed_ai_attempt_count_unassisted": 5,
                "suggestion_selection_percentage_among_attempts_with_offer": 62.5,
            },
            {
                "field_name": "lookupField",
                "analysis_type": "LOOKUP",
                "completed_ai_attempt_count": 10,
                "completed_ai_attempt_count_with_suggestion_offered": 10,
                "completed_ai_attempt_count_with_suggestion_selected": 8,
                "completed_ai_attempt_count_selected_and_exactly_retained": 0,
                "completed_ai_attempt_count_selected_and_cosmetically_changed": 0,
                "completed_ai_attempt_count_selected_and_lightly_edited": 0,
                "completed_ai_attempt_count_selected_and_moderately_edited": 0,
                "completed_ai_attempt_count_selected_and_heavily_edited": 0,
                "completed_ai_attempt_count_selected_and_unclassified_edit": 0,
                "completed_ai_attempt_count_selected_and_replaced": 0,
                "completed_ai_attempt_count_selected_then_cleared": 0,
                "completed_ai_attempt_count_unassisted": 2,
                "suggestion_selection_percentage_among_attempts_with_offer": 80.0,
            },
        ]
    )


def compensation_analysis_rows() -> pd.DataFrame:
    """Return synthetic generic, specific, and composition summaries."""
    composition = [
        {
            "summary_grain": "OFFER_COMPOSITION",
            "population_name": population,
            "offer_composition_category": category,
            "generic_suggestion_count": None,
            "specific_suggestion_count": None,
            "attempt_count": count,
            "population_attempt_count": population_count,
            "attempt_percentage": 100.0 * count / population_count,
            "is_exact_three_plus_three": None,
            "consistency_category": None,
        }
        for population, population_count, category, count in (
            ("ALL_COMPLETED_AI_ATTEMPTS", 10, "BOTH_KINDS", 6),
            ("ALL_COMPLETED_AI_ATTEMPTS", 10, "GENERIC_ONLY", 2),
            ("ALL_COMPLETED_AI_ATTEMPTS", 10, "SPECIFIC_ONLY", 1),
            ("ALL_COMPLETED_AI_ATTEMPTS", 10, "NEITHER", 1),
            ("FINAL_COMPENSATION_YES", 8, "BOTH_KINDS", 6),
            ("FINAL_COMPENSATION_YES", 8, "GENERIC_ONLY", 1),
            ("FINAL_COMPENSATION_YES", 8, "SPECIFIC_ONLY", 1),
            ("FINAL_COMPENSATION_YES", 8, "NEITHER", 0),
        )
    ]
    composition_json = json.dumps(
        composition,
        sort_keys=True,
        separators=(",", ":"),
    )

    return pd.DataFrame.from_records(
        [
            {
                "compensation_suggestion_kind": "genericCompensation",
                "completed_ai_attempt_count_with_suggestion": 10,
                "offered_suggestion_count": 30,
                "selected_suggestion_count": 4,
                "suggestion_selection_percentage": 100.0 * 4.0 / 30.0,
                "offer_composition_summary_json": composition_json,
            },
            {
                "compensation_suggestion_kind": "specificCompensation",
                "completed_ai_attempt_count_with_suggestion": 8,
                "offered_suggestion_count": 24,
                "selected_suggestion_count": 2,
                "suggestion_selection_percentage": 100.0 * 2.0 / 24.0,
                "offer_composition_summary_json": composition_json,
            },
        ]
    )


def suggestion_selection_rows() -> pd.DataFrame:
    """Return synthetic aggregate-only suggestion-selection rows."""
    return pd.DataFrame.from_records(
        [
            {
                "field_name": "title",
                "suggestion_kind": "title",
                "suggestion_index": 0,
                "offered_suggestion_count": 18,
                "selected_suggestion_count": 7,
                "unselected_suggestion_count": 11,
                "completed_ai_attempt_count_with_at_least_one_suggestion": 9,
                "completed_ai_attempt_count_with_selected_suggestion": 7,
                "suggestion_level_selection_percentage": 100.0 * 7.0 / 18.0,
                "attempt_level_selection_percentage": 100.0 * 7.0 / 9.0,
                "suggestion_count_at_index": 9,
                "selected_suggestion_count_at_index": 5,
                "selection_percentage_at_index": 100.0 * 5.0 / 9.0,
            },
            {
                "field_name": "title",
                "suggestion_kind": "title",
                "suggestion_index": 1,
                "offered_suggestion_count": 18,
                "selected_suggestion_count": 7,
                "unselected_suggestion_count": 11,
                "completed_ai_attempt_count_with_at_least_one_suggestion": 9,
                "completed_ai_attempt_count_with_selected_suggestion": 7,
                "suggestion_level_selection_percentage": 100.0 * 7.0 / 18.0,
                "attempt_level_selection_percentage": 100.0 * 7.0 / 9.0,
                "suggestion_count_at_index": 9,
                "selected_suggestion_count_at_index": 2,
                "selection_percentage_at_index": 100.0 * 2.0 / 9.0,
            },
            {
                "field_name": "compensation",
                "suggestion_kind": "genericCompensation",
                "suggestion_index": 0,
                "offered_suggestion_count": 6,
                "selected_suggestion_count": 3,
                "unselected_suggestion_count": 3,
                "completed_ai_attempt_count_with_at_least_one_suggestion": 6,
                "completed_ai_attempt_count_with_selected_suggestion": 3,
                "suggestion_level_selection_percentage": 50.0,
                "attempt_level_selection_percentage": 50.0,
                "suggestion_count_at_index": 6,
                "selected_suggestion_count_at_index": 3,
                "selection_percentage_at_index": 50.0,
            },
        ]
    )


def readability_change_rows() -> pd.DataFrame:
    """Return synthetic selected-to-final readability summaries."""
    return pd.DataFrame.from_records(
        [
            {
                "field_name": "title",
                "readability_measure_name": "flesch_kincaid_grade",
                "paired_selected_final_attempt_count": 6,
                "attempt_count_value_decreased": 2,
                "attempt_count_no_material_change": 1,
                "attempt_count_value_increased": 3,
                "percentage_value_decreased": 100.0 * 2.0 / 6.0,
                "percentage_no_material_change": 100.0 / 6.0,
                "percentage_value_increased": 50.0,
                "unchanged_absolute_tolerance": 0.1,
                "short_text_readability_caution": True,
            },
            {
                "field_name": "description",
                "readability_measure_name": "flesch_kincaid_grade",
                "paired_selected_final_attempt_count": 5,
                "attempt_count_value_decreased": 3,
                "attempt_count_no_material_change": 1,
                "attempt_count_value_increased": 1,
                "percentage_value_decreased": 60.0,
                "percentage_no_material_change": 20.0,
                "percentage_value_increased": 20.0,
                "unchanged_absolute_tolerance": 0.1,
                "short_text_readability_caution": False,
            },
            {
                "field_name": "title",
                "readability_measure_name": "word_count",
                "paired_selected_final_attempt_count": 6,
                "attempt_count_value_decreased": 1,
                "attempt_count_no_material_change": 2,
                "attempt_count_value_increased": 3,
                "percentage_value_decreased": 100.0 / 6.0,
                "percentage_no_material_change": 100.0 * 2.0 / 6.0,
                "percentage_value_increased": 50.0,
                "unchanged_absolute_tolerance": 0.1,
                "short_text_readability_caution": True,
            },
        ]
    )


def readability_target_rows() -> pd.DataFrame:
    """Return synthetic final grade-band summaries."""
    note = (
        "Grade-level formulas are indicators only and do not establish comprehension."
    )

    return pd.DataFrame.from_records(
        [
            {
                "attempt_authoring_mode": "AI",
                "field_name": "title",
                "readability_measure_name": "flesch_kincaid_grade",
                "final_text_attempt_count": 8,
                "attempt_count_at_or_below_grade_6": 2,
                "attempt_count_above_grade_6_through_grade_8": 2,
                "attempt_count_above_grade_8_through_grade_10": 1,
                "attempt_count_above_grade_10": 3,
                "percentage_at_or_below_grade_8": 50.0,
                "short_text_readability_caution": True,
                "target_interpretation_note": note,
            },
            {
                "attempt_authoring_mode": "MANUAL",
                "field_name": "description",
                "readability_measure_name": "flesch_kincaid_grade",
                "final_text_attempt_count": 6,
                "attempt_count_at_or_below_grade_6": 1,
                "attempt_count_above_grade_6_through_grade_8": 2,
                "attempt_count_above_grade_8_through_grade_10": 2,
                "attempt_count_above_grade_10": 1,
                "percentage_at_or_below_grade_8": 50.0,
                "short_text_readability_caution": False,
                "target_interpretation_note": note,
            },
        ]
    )


def selected_comparison_rows() -> pd.DataFrame:
    """Return synthetic selected-versus-unselected summaries."""
    return pd.DataFrame.from_records(
        [
            {
                "field_name": "title",
                "readability_measure_name": "flesch_kincaid_grade",
                (
                    "completed_ai_attempt_count_with_selected_and_"
                    "unselected_suggestions"
                ): 5,
                "median_selected_minus_mean_unselected_value": -0.5,
                "attempt_count_selected_value_lower": 3,
                "attempt_count_selected_value_equal_within_tolerance": 1,
                "attempt_count_selected_value_higher": 1,
                "equality_tolerance": 0.1,
            },
            {
                "field_name": "description",
                "readability_measure_name": "flesch_kincaid_grade",
                (
                    "completed_ai_attempt_count_with_selected_and_"
                    "unselected_suggestions"
                ): 4,
                "median_selected_minus_mean_unselected_value": 0.75,
                "attempt_count_selected_value_lower": 1,
                "attempt_count_selected_value_equal_within_tolerance": 1,
                "attempt_count_selected_value_higher": 2,
                "equality_tolerance": 0.1,
            },
        ]
    )


def edit_readability_cross_rows() -> pd.DataFrame:
    """Return synthetic edit-intensity/readability-direction rows."""
    scheme = "EXPLORATORY_CHARACTER_RATIO_10_30"

    return pd.DataFrame.from_records(
        [
            {
                "field_name": "title",
                "edit_intensity_threshold_scheme_name": scheme,
                "edit_intensity_category": "LIGHT_EDIT",
                "readability_direction_category": ("CONSENSUS_GRADE_LEVEL_DECREASE"),
                "completed_ai_attempt_count": 5,
                "completed_ai_attempt_count_with_selected_final_pair": 2,
                "percentage_within_edit_intensity_category": 40.0,
                ("median_flesch_kincaid_grade_change_final_minus_selected"): -0.6,
                "median_consensus_grade_level_change": -1.0,
            },
            {
                "field_name": "title",
                "edit_intensity_threshold_scheme_name": scheme,
                "edit_intensity_category": "LIGHT_EDIT",
                "readability_direction_category": "NO_MATERIAL_CHANGE",
                "completed_ai_attempt_count": 5,
                "completed_ai_attempt_count_with_selected_final_pair": 1,
                "percentage_within_edit_intensity_category": 20.0,
                ("median_flesch_kincaid_grade_change_final_minus_selected"): 0.0,
                "median_consensus_grade_level_change": 0.0,
            },
            {
                "field_name": "description",
                "edit_intensity_threshold_scheme_name": scheme,
                "edit_intensity_category": "EDITED_UNCLASSIFIED",
                "readability_direction_category": ("MIXED_FORMULA_DIRECTION"),
                "completed_ai_attempt_count": 4,
                "completed_ai_attempt_count_with_selected_final_pair": 2,
                "percentage_within_edit_intensity_category": 50.0,
                ("median_flesch_kincaid_grade_change_final_minus_selected"): 0.25,
                "median_consensus_grade_level_change": 0.0,
            },
        ]
    )


def source_context_distribution_rows() -> pd.DataFrame:
    """Return aggregate-only source-context category rows."""
    rows: list[dict[str, object]] = [
        {
            "population_name": "ALL_SUCCESSFUL_AI_GENERATIONS",
            "summary_dimension_name": "INPUT_METHOD",
            "summary_dimension_value": "docx_file",
            "eligible_attempt_count": 5,
            "category_attempt_count": 3,
            "category_attempt_percentage": 60.0,
        },
        {
            "population_name": "ALL_SUCCESSFUL_AI_GENERATIONS",
            "summary_dimension_name": "INPUT_METHOD",
            "summary_dimension_value": "pdf_file",
            "eligible_attempt_count": 5,
            "category_attempt_count": 2,
            "category_attempt_percentage": 40.0,
        },
        {
            "population_name": "COMPLETED_AI_ATTEMPTS",
            "summary_dimension_name": "INPUT_METHOD",
            "summary_dimension_value": "docx_file",
            "eligible_attempt_count": 3,
            "category_attempt_count": 2,
            "category_attempt_percentage": 200 / 3,
        },
        {
            "population_name": "COMPLETED_AI_ATTEMPTS",
            "summary_dimension_name": "INPUT_METHOD",
            "summary_dimension_value": "pdf_file",
            "eligible_attempt_count": 3,
            "category_attempt_count": 1,
            "category_attempt_percentage": 100 / 3,
        },
    ]

    return pd.DataFrame.from_records(rows)


def source_size_latency_rows() -> pd.DataFrame:
    """Return aggregate-only source-size-band latency rows."""
    rows: list[dict[str, object]] = [
        {
            "population_name": "ALL_SUCCESSFUL_AI_GENERATIONS",
            "source_size_band_name": "Q1_OF_2",
            "source_size_band_sequence": 1,
            "source_size_band_lower_bound_chars": 100.0,
            "source_size_band_upper_bound_chars": 200.0,
            "reported_source_group": "ALL",
            "band_attempt_count": 3,
            "attempt_count_with_latency": 3,
            "attempt_count_missing_latency": 0,
            "median_source_size_chars": 150.0,
            "percentile_25_latency_ms": 900.0,
            "median_latency_ms": 1_000.0,
            "percentile_75_latency_ms": 1_100.0,
            "percentile_90_latency_ms": 1_200.0,
        },
        {
            "population_name": "ALL_SUCCESSFUL_AI_GENERATIONS",
            "source_size_band_name": "Q2_OF_2",
            "source_size_band_sequence": 2,
            "source_size_band_lower_bound_chars": 300.0,
            "source_size_band_upper_bound_chars": 500.0,
            "reported_source_group": "ALL",
            "band_attempt_count": 2,
            "attempt_count_with_latency": 1,
            "attempt_count_missing_latency": 1,
            "median_source_size_chars": 400.0,
            "percentile_25_latency_ms": 1_800.0,
            "median_latency_ms": 2_000.0,
            "percentile_75_latency_ms": 2_200.0,
            "percentile_90_latency_ms": 2_300.0,
        },
        {
            "population_name": "COMPLETED_AI_ATTEMPTS",
            "source_size_band_name": "Q1_OF_2",
            "source_size_band_sequence": 1,
            "source_size_band_lower_bound_chars": 100.0,
            "source_size_band_upper_bound_chars": 200.0,
            "reported_source_group": "ALL",
            "band_attempt_count": 2,
            "attempt_count_with_latency": 2,
            "attempt_count_missing_latency": 0,
            "median_source_size_chars": 160.0,
            "percentile_25_latency_ms": 1_100.0,
            "median_latency_ms": 1_200.0,
            "percentile_75_latency_ms": 1_300.0,
            "percentile_90_latency_ms": 1_400.0,
        },
        {
            "population_name": "COMPLETED_AI_ATTEMPTS",
            "source_size_band_name": "Q2_OF_2",
            "source_size_band_sequence": 2,
            "source_size_band_lower_bound_chars": 300.0,
            "source_size_band_upper_bound_chars": 500.0,
            "reported_source_group": "ALL",
            "band_attempt_count": 1,
            "attempt_count_with_latency": 1,
            "attempt_count_missing_latency": 0,
            "median_source_size_chars": 420.0,
            "percentile_25_latency_ms": 2_400.0,
            "median_latency_ms": 2_400.0,
            "percentile_75_latency_ms": 2_400.0,
            "percentile_90_latency_ms": 2_400.0,
        },
    ]

    return pd.DataFrame.from_records(rows)


def repeated_source_rows() -> pd.DataFrame:
    """Return aggregate-only completed-path transition rows."""
    rows: list[dict[str, object]] = []

    for dimension in (
        "SOURCE_SIZE",
        "REPORTED_CONTENT_SOURCE",
        "INPUT_METHOD",
        "SOURCE_SIGNATURE_PROXY",
    ):
        for category, count, percentage in (
            ("SAME", 3, 60.0),
            ("CHANGED", 2, 40.0),
            ("MISSING", 2, 100.0),
        ):
            rows.append(
                {
                    "summary_grain": (
                        "COMPLETED_AI_PATH_CONSECUTIVE_SUCCESSFUL_AI_TRANSITION"
                    ),
                    "comparison_dimension_name": dimension,
                    "comparison_category": category,
                    "population_unit_count": 7,
                    "contributing_study_count": 3,
                    "eligible_unit_count": (2 if category == "MISSING" else 5),
                    "category_unit_count": count,
                    "category_unit_percentage": percentage,
                    "unit_count_with_latency_change": count,
                    "median_latency_change_ms": (
                        100.0 if category == "CHANGED" else 0.0
                    ),
                }
            )

    return pd.DataFrame.from_records(rows)


def content_source_rows() -> pd.DataFrame:
    """Return synthetic aggregate-only concordance rows."""
    return pd.DataFrame.from_records(
        [
            {
                "attempt_completion_group": "ALL",
                "reported_study_content_source": "registry",
                "inferred_study_content_source": "registry",
                "ai_attempt_count": 3,
                "reported_source_attempt_count": 4,
                "attempt_percentage_within_reported_source": 75.0,
            },
            {
                "attempt_completion_group": "ALL",
                "reported_study_content_source": "registry",
                "inferred_study_content_source": "other",
                "ai_attempt_count": 1,
                "reported_source_attempt_count": 4,
                "attempt_percentage_within_reported_source": 25.0,
            },
            {
                "attempt_completion_group": "COMPLETE",
                "reported_study_content_source": "registry",
                "inferred_study_content_source": "registry",
                "ai_attempt_count": 2,
                "reported_source_attempt_count": 2,
                "attempt_percentage_within_reported_source": 100.0,
            },
        ]
    )


def test_completed_study_mix_chart_ranks_mutually_exclusive_groups() -> None:
    figure = build_completed_study_mix_chart(
        grouped_study_rows(),
        dimension_name="STUDY_PARTICIPANT_TYPE",
        title="Completed studies by participant type",
    )
    bar = figure.data[0]

    assert figure.layout.title.text == "Completed studies by participant type"
    assert bar.orientation == "h"
    assert list(bar.y) == ["MISSING", "Other", "HEALTHY"]
    assert list(bar.x) == [2, 3, 5]
    assert [list(values) for values in bar.customdata] == [
        [20.0, 10],
        [30.0, 10],
        [50.0, 10],
    ]
    assert figure.layout.yaxis.tickmode == "array"
    assert list(figure.layout.yaxis.tickvals) == [
        "MISSING",
        "Other",
        "HEALTHY",
    ]
    assert list(figure.layout.yaxis.ticktext) == [
        "MISSING",
        "Other",
        "HEALTHY",
    ]
    assert figure.layout.height >= 420


def test_completed_study_mix_chart_height_grows_with_category_count() -> None:
    """Keep every study-category label visible without requiring hover."""
    rows = grouped_study_rows()
    template = rows.loc[
        rows["grouping_dimension_1_name"].eq("STUDY_DEPARTMENT")
        & rows["final_completion_authoring_mode"].eq("ALL")
        & rows["grouping_dimension_2_name"].eq("NONE")
    ].iloc[0]
    additions = pd.DataFrame.from_records(
        [
            {
                **template.to_dict(),
                "grouping_dimension_1_value": f"Synthetic Department {index:02d}",
                "distinct_study_count": index + 1,
            }
            for index in range(20)
        ]
    )
    rows = pd.concat([rows, additions], ignore_index=True)

    figure = build_completed_study_mix_chart(
        rows,
        dimension_name="STUDY_DEPARTMENT",
        title="Completed studies by department",
    )
    bar = figure.data[0]

    assert len(bar.y) == 22
    assert len(figure.layout.yaxis.tickvals) == 22
    assert len(figure.layout.yaxis.ticktext) == 22
    assert figure.layout.height == 34 * 22 + 150


def test_completed_study_department_chart_excludes_other_modes() -> None:
    figure = build_completed_study_mix_chart(
        grouped_study_rows(),
        dimension_name="STUDY_DEPARTMENT",
        title="Completed studies by department",
    )
    bar = figure.data[0]

    assert list(bar.y) == ["Department B", "Department A"]
    assert list(bar.x) == [4, 6]


def test_completed_study_mix_chart_rejects_overlapping_groups() -> None:
    rows = grouped_study_rows()
    rows.loc[
        rows["grouping_dimension_1_name"].eq("STUDY_PARTICIPANT_TYPE"),
        "group_values_are_mutually_exclusive",
    ] = False

    with pytest.raises(
        ExplorationValidationError,
        match="must contain mutually exclusive groups",
    ):
        build_completed_study_mix_chart(
            rows,
            dimension_name="STUDY_PARTICIPANT_TYPE",
            title="Completed studies by participant type",
        )


def test_completed_study_author_role_chart_uses_study_counts() -> None:
    """Show completed studies, not a permanent author classification."""
    figure = build_completed_study_author_context_chart(
        completed_study_author_context_rows(),
        dimension_name="EFFECTIVE_ROLE",
        title="Completed studies by authoring mode and completion-author role",
    )
    traces = {str(trace.name): trace for trace in figure.data}

    assert figure.layout.barmode == "stack"
    assert figure.layout.title.text == (
        "Completed studies by authoring mode and completion-author role"
    )
    assert list(traces["COORDINATOR"].y) == ["AI", "MANUAL"]
    assert list(traces["COORDINATOR"].x) == [4, 2]
    assert list(traces["COORDINATOR"].customdata[0]) == [
        4,
        6,
        10,
        100.0 * 4.0 / 6.0,
        40.0,
        3,
    ]
    hover = str(traces["COORDINATOR"].hovertemplate)
    assert "each completed study contributes once" in hover
    assert "unique completed attempt" in hover
    assert "different context across studies" in hover


def test_completed_study_pi_status_chart_uses_study_specific_labels() -> None:
    """Describe PI status for each study rather than as a permanent identity."""
    figure = build_completed_study_author_context_chart(
        completed_study_author_context_rows(),
        dimension_name="PI_STATUS",
        title=("Completed studies by authoring mode and completion-author PI status"),
    )
    traces = {str(trace.name): trace for trace in figure.data}

    assert set(traces) == {
        "PI for this study",
        "Non-PI for this study",
    }
    assert list(traces["PI for this study"].x) == [2, 2]
    assert "Share within mode" in str(traces["Non-PI for this study"].hovertemplate)
    assert "Share of all completed studies" in str(
        traces["Non-PI for this study"].hovertemplate
    )
    assert "Distinct completion authors represented" in str(
        traces["Non-PI for this study"].hovertemplate
    )


def test_attempt_outcomes_chart_partitions_all_attempts() -> None:
    figure = build_attempt_outcomes_chart(overview_rows())
    traces = {str(trace.name): trace for trace in figure.data}

    assert figure.layout.title.text == "How the captured attempts ended"
    assert figure.layout.barmode == "stack"
    assert list(traces) == [
        "Completed — AI",
        "Completed — manual",
        "Incomplete — AI",
        "Incomplete — manual",
    ]
    assert [trace.orientation for trace in figure.data] == ["h", "h", "h", "h"]
    assert [list(trace.x) for trace in figure.data] == [[4], [3], [2], [1]]
    assert [list(trace.y) for trace in figure.data] == [
        ["All attempts"],
        ["All attempts"],
        ["All attempts"],
        ["All attempts"],
    ]
    assert traces["Completed — AI"].customdata[0][0] == pytest.approx(40.0)
    assert traces["Completed — AI"].customdata[0][1] == 7
    assert traces["Completed — AI"].customdata[0][2] == pytest.approx(100.0 * 4.0 / 7.0)
    assert "Share within completion group" in str(
        traces["Completed — AI"].hovertemplate
    )
    assert traces["Incomplete — AI"].marker.pattern.shape == "/"
    assert traces["Completed — AI"].textangle == 0
    assert "AI complete" in str(traces["Completed — AI"].text[0])
    assert figure.layout.height == 420


def test_attempt_outcomes_chart_rejects_contradictory_partition() -> None:
    rows = overview_rows()
    rows.loc[
        rows["overview_metric_name"].eq("incomplete_manual_attempt_count"),
        "metric_count",
    ] = 2

    with pytest.raises(
        ExplorationValidationError,
        match="do not partition their completion groups",
    ):
        build_attempt_outcomes_chart(rows)


def test_attempt_outcomes_chart_rejects_duplicate_overview_metric() -> None:
    rows = pd.concat(
        [
            overview_rows(),
            overview_rows().loc[
                overview_rows()["overview_metric_name"].eq("all_attempt_count")
            ],
        ],
        ignore_index=True,
    )

    with pytest.raises(
        ExplorationValidationError,
        match="contains duplicate metric",
    ):
        build_attempt_outcomes_chart(rows)


def test_attempt_outcomes_chart_requires_every_partition_metric() -> None:
    rows = overview_rows().loc[
        overview_rows()["overview_metric_name"].ne("incomplete_manual_attempt_count")
    ]

    with pytest.raises(
        ExplorationValidationError,
        match="lacks required metric 'incomplete_manual_attempt_count'",
    ):
        build_attempt_outcomes_chart(rows)


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("not-a-number", "must be numeric"),
        (1.5, "must be a nonnegative integer"),
        (-1, "must be a nonnegative integer"),
    ],
)
def test_attempt_outcomes_chart_rejects_invalid_counts(
    value: object,
    message: str,
) -> None:
    records = overview_rows().to_dict(orient="records")

    for record in records:
        if record["overview_metric_name"] == "completed_ai_attempt_count":
            record["metric_count"] = value

    rows = pd.DataFrame.from_records(records)

    with pytest.raises(
        ExplorationValidationError,
        match=message,
    ):
        build_attempt_outcomes_chart(rows)


def test_attempt_outcomes_chart_rejects_completion_partition_mismatch() -> None:
    rows = overview_rows()
    rows.loc[
        rows["overview_metric_name"].eq("incomplete_attempt_count"),
        "metric_count",
    ] = 4

    with pytest.raises(
        ExplorationValidationError,
        match="completion counts do not partition all attempts",
    ):
        build_attempt_outcomes_chart(rows)


def test_attempt_timing_chart_shows_two_timing_distributions() -> None:
    figure = build_attempt_timing_chart(grouped_attempt_rows())
    traces = {str(trace.name): trace for trace in figure.data}

    assert figure.layout.title.text == ("Completed-attempt timing by authoring mode")
    assert figure.layout.barmode == "group"
    assert figure.layout.height == 460
    assert figure.layout.yaxis.title.text == "Median minutes"
    assert list(traces["Study-information-page time"].x) == [
        "AI",
        "MANUAL",
    ]
    assert list(traces["Study-information-page time"].y) == [2.0, 3.0]
    assert list(traces["Study-information-page time"].error_y.arrayminus) == [
        1.0,
        1.0,
    ]
    assert list(traces["Study-information-page time"].error_y.array) == [
        1.0,
        1.0,
    ]
    assert list(traces["Total attempt time"].y) == [2.5, 5.0]
    assert [list(value[:2]) for value in traces["Total attempt time"].customdata] == [
        [4, 0],
        [3, 0],
    ]
    assert "90th percentile" in str(traces["Total attempt time"].hovertemplate)
    assert "Attempts missing timing value" in str(
        traces["Total attempt time"].hovertemplate
    )


def test_study_completion_pathways_chart_uses_completed_modes() -> None:
    figure = build_study_completion_pathways_chart(study_history_rows())

    assert (
        figure.layout.title.text == "Completed-study pathways by final authoring mode"
    )
    assert figure.layout.barmode == "stack"
    assert list(figure.data[0].x) == ["AI", "MANUAL"]
    assert list(figure.data[0].y) == [4, 2]
    assert list(figure.data[1].y) == [2, 2]


def test_author_handoff_chart_aggregates_categories_by_mode() -> None:
    figure = build_author_handoff_chart(author_handoff_rows())

    assert figure.layout.title.text == "Author handoffs before study completion"
    assert figure.layout.barmode == "stack"
    assert list(figure.data[0].x) == ["AI", "MANUAL"]
    assert list(figure.data[0].y) == [4, 0]
    assert list(figure.data[1].y) == [0, 1]
    assert list(figure.data[2].y) == [2, 0]
    assert list(figure.data[3].y) == [0, 3]


def test_author_attempt_start_chart_uses_exact_percentile_interval() -> None:
    figure = build_author_attempt_start_experience_chart(
        attempt_start_experience_rows()
    )
    interval, median_markers, mean_markers = figure.data

    assert figure.layout.title.text == (
        "Studies created before attempt start: distribution summary"
    )
    assert list(interval.x) == ["AI", "AI", "AI", "MANUAL", "MANUAL", "MANUAL"]
    assert list(interval.y) == [1.0, 4.0, None, 3.0, 8.0, None]
    assert list(median_markers.x) == ["AI", "MANUAL"]
    assert list(median_markers.y) == [2.0, 5.0]
    assert list(mean_markers.y) == [9.0, 6.0]
    assert float(mean_markers.y[0]) > float(interval.y[1])
    assert [values[4] for values in mean_markers.customdata] == [6, 4]
    assert [values[5] for values in mean_markers.customdata] == [1, 0]
    assert "Observations with value" in str(mean_markers.hovertemplate)
    assert "Observations missing value" in str(mean_markers.hovertemplate)
    assert "25th percentile" in str(mean_markers.hovertemplate)
    assert "Median:" in str(mean_markers.hovertemplate)
    assert "Mean:" in str(mean_markers.hovertemplate)
    assert "75th percentile" in str(mean_markers.hovertemplate)
    assert "Definition:" in str(mean_markers.hovertemplate)


def test_query_time_author_experience_tooltip_uses_author_grain() -> None:
    figure = build_author_experience_chart(
        current_author_experience_rows(),
        metric_unit="days",
    )
    median_markers = figure.data[1]

    assert "Observations with value" in str(median_markers.hovertemplate)
    assert "Observations missing value" in str(median_markers.hovertemplate)
    assert "25th percentile" in str(median_markers.hovertemplate)
    assert "75th percentile" in str(median_markers.hovertemplate)
    assert "Unit:" in str(median_markers.hovertemplate)
    assert "Definition:" in str(median_markers.hovertemplate)
    assert median_markers.customdata[0][4] == 4
    assert median_markers.customdata[0][5] == 1
    assert median_markers.customdata[0][6] == "days"


def test_author_experience_chart_facets_metrics_and_omits_missing_groups() -> None:
    rows = current_author_experience_rows()
    missing = rows["experience_metric_name"].eq(
        "other_study_memberships_as_of_report_query_count"
    ) & rows["author_adoption_group"].eq("BOTH_AI_AND_MANUAL")
    rows = rows.loc[~missing]

    studies_figure = build_author_experience_chart(rows, metric_unit="studies")
    days_figure = build_author_experience_chart(rows, metric_unit="days")

    assert studies_figure.layout.title.text == (
        "Author experience at report query time: studies"
    )
    assert [annotation.text for annotation in studies_figure.layout.annotations] == [
        "Total studies created",
        "Other study memberships",
    ]
    assert len(studies_figure.data) == 6
    membership_interval = studies_figure.data[3]
    assert "Both AI and manual" not in list(membership_interval.x)
    assert 0.0 not in [value for value in membership_interval.y if value is not None]

    assert days_figure.layout.title.text == (
        "Author experience at report query time: days"
    )
    assert [annotation.text for annotation in days_figure.layout.annotations] == [
        "Distinct login days",
        "Login-history span",
    ]
    assert len(days_figure.data) == 6


def test_field_suggestion_adoption_chart_uses_explicit_denominator() -> None:
    figure = build_field_suggestion_adoption_chart(field_adoption_rows())

    assert figure.layout.title.text == ("AI suggestion offers and selections by field")
    assert figure.layout.barmode == "group"
    assert list(figure.data[0].x) == ["Title", "Description"]
    assert list(figure.data[0].y) == [9, 8]
    assert list(figure.data[1].y) == [7, 5]
    assert figure.data[0].customdata[0][0] == 10
    assert figure.data[0].customdata[0][3] == pytest.approx(100.0 * 7.0 / 9.0)
    assert "Selection among attempts with offer" in str(figure.data[0].hovertemplate)


def test_field_selected_outcomes_chart_preserves_unclassified() -> None:
    figure = build_field_selected_outcomes_chart(field_adoption_rows())
    traces_by_name = {str(trace.name): trace for trace in figure.data}

    assert figure.layout.title.text == ("Selected AI suggestion outcomes by field")
    assert figure.layout.barmode == "stack"
    assert list(traces_by_name["Edited, unclassified"].y) == [1, 0]
    assert list(traces_by_name["Replaced"].y) == [0, 1]
    assert "edited-unclassified remains separate from replaced" in str(
        traces_by_name["Edited, unclassified"].customdata[0][1]
    )


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda frame: frame.drop(columns=["offer_composition_summary_json"]),
            "lacks required chart column",
        ),
        (
            lambda frame: frame.assign(offer_composition_summary_json="not-json"),
            "contains invalid offer_composition_summary_json",
        ),
        (
            lambda frame: frame.assign(
                offer_composition_summary_json=json.dumps({"not": "a list"})
            ),
            "must contain a JSON list of objects",
        ),
        (
            lambda frame: frame.assign(
                offer_composition_summary_json=[
                    frame["offer_composition_summary_json"].iloc[0],
                    json.dumps([]),
                ]
            ),
            "must contain one consistent offer_composition_summary_json payload",
        ),
    ],
)
def test_compensation_offer_composition_chart_rejects_invalid_payloads(
    mutate: Callable[[pd.DataFrame], pd.DataFrame],
    message: str,
) -> None:
    """Reject missing, malformed, non-list, and inconsistent payloads."""
    with pytest.raises(ExplorationValidationError, match=message):
        build_compensation_offer_composition_chart(
            mutate(compensation_analysis_rows()),
            population_name="ALL_COMPLETED_AI_ATTEMPTS",
            title="Synthetic title",
        )


def test_compensation_offer_composition_chart_returns_population_empty_state() -> None:
    """Render an empty state when a requested population is absent."""
    figure = build_compensation_offer_composition_chart(
        compensation_analysis_rows(),
        population_name="SYNTHETIC_ABSENT",
        title="Synthetic absent population",
    )

    assert figure.layout.annotations[0].text


@pytest.mark.parametrize(
    ("mutate_rows", "message"),
    [
        (
            lambda rows: rows[:-1],
            "lacks required categories",
        ),
        (
            lambda rows: [
                {
                    **row,
                    "population_attempt_count": (
                        11
                        if row["offer_composition_category"] == "BOTH_KINDS"
                        else row["population_attempt_count"]
                    ),
                }
                for row in rows
            ],
            "inconsistent population counts",
        ),
        (
            lambda rows: [
                {
                    **row,
                    "attempt_count": (
                        7
                        if row["offer_composition_category"] == "BOTH_KINDS"
                        else row["attempt_count"]
                    ),
                }
                for row in rows
            ],
            "counts do not reconcile",
        ),
    ],
)
def test_compensation_offer_composition_chart_reconciles_categories(
    mutate_rows: Callable[[list[dict[str, object]]], list[dict[str, object]]],
    message: str,
) -> None:
    """Require complete, denominator-consistent composition rows."""
    summary = compensation_analysis_rows()
    rows = json.loads(summary["offer_composition_summary_json"].iloc[0])
    all_rows = [
        row for row in rows if row["population_name"] == "ALL_COMPLETED_AI_ATTEMPTS"
    ]
    other_rows = [
        row for row in rows if row["population_name"] != "ALL_COMPLETED_AI_ATTEMPTS"
    ]
    summary["offer_composition_summary_json"] = json.dumps(
        [*mutate_rows(all_rows), *other_rows]
    )

    with pytest.raises(ExplorationValidationError, match=message):
        build_compensation_offer_composition_chart(
            summary,
            population_name="ALL_COMPLETED_AI_ATTEMPTS",
            title="Synthetic title",
        )


def test_compensation_suggestion_use_chart_is_attempt_level() -> None:
    """Compare offered and selected attempts, retaining instance context."""
    figure = build_compensation_suggestion_use_chart(compensation_analysis_rows())
    traces = {str(trace.name): trace for trace in figure.data}

    assert figure.layout.title.text == (
        "Compensation text offers and selections by kind"
    )
    assert figure.layout.barmode == "group"
    assert list(traces["Attempts offered this kind"].y) == [
        "Generic compensation",
        "Specific compensation",
    ]
    assert list(traces["Attempts offered this kind"].x) == [10, 8]
    assert list(traces["Attempts selecting this kind"].x) == [4, 2]
    assert list(traces["Attempts offered this kind"].customdata[0]) == [
        10,
        4,
        40.0,
        30,
    ]
    assert "Attempt-level selection" in str(
        traces["Attempts offered this kind"].hovertemplate
    )
    assert "Text suggestion instances offered" in str(
        traces["Attempts offered this kind"].hovertemplate
    )


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda frame: frame.assign(
                compensation_suggestion_kind="SYNTHETIC_UNKNOWN"
            ),
            "contains unsupported suggestion kinds",
        ),
        (
            lambda frame: frame.assign(offered_suggestion_count=4.5),
            "must contain a nonnegative integer",
        ),
        (
            lambda frame: frame.assign(offered_suggestion_count=True),
            "must contain a nonnegative integer",
        ),
        (
            lambda frame: frame.assign(offered_suggestion_count="invalid"),
            "must contain a nonnegative integer",
        ),
        (
            lambda frame: frame.assign(
                completed_ai_attempt_count_with_suggestion=1,
                selected_suggestion_count=2,
            ),
            "selected-attempt count must not exceed offered-attempt count",
        ),
    ],
)
def test_compensation_suggestion_use_chart_rejects_invalid_aggregates(
    mutate: Callable[[pd.DataFrame], pd.DataFrame],
    message: str,
) -> None:
    """Reject unsupported kinds, fractional counts, and impossible totals."""
    with pytest.raises(ExplorationValidationError, match=message):
        build_compensation_suggestion_use_chart(mutate(compensation_analysis_rows()))


def test_suggestion_selection_by_kind_chart_distinguishes_denominators() -> None:
    figure = build_suggestion_selection_by_kind_chart(suggestion_selection_rows())
    bar = figure.data[0]

    assert figure.layout.title.text == ("Suggestion selection by field and kind")
    assert list(bar.x) == [
        "Compensation — Generic compensation",
        "Title",
    ]
    assert list(bar.y) == [
        50.0,
        pytest.approx(100.0 * 7.0 / 9.0),
    ]
    title_customdata = bar.customdata[1]
    assert list(title_customdata[:4]) == [9, 7, 18, 7]
    assert title_customdata[4] == pytest.approx(100.0 * 7.0 / 18.0)
    assert "Attempt-level selection" in str(bar.hovertemplate)
    assert "Suggestion-level selection" in str(bar.hovertemplate)


def test_suggestion_selection_by_index_chart_is_zero_based() -> None:
    figure = build_suggestion_selection_by_index_chart(suggestion_selection_rows())
    traces_by_name = {str(trace.name): trace for trace in figure.data}
    title_trace = traces_by_name["Title"]

    assert figure.layout.title.text == ("Selection by zero-based suggestion index")
    assert list(title_trace.x) == [0, 1]
    assert list(title_trace.y) == [
        pytest.approx(100.0 * 5.0 / 9.0),
        pytest.approx(100.0 * 2.0 / 9.0),
    ]
    assert [list(value) for value in title_trace.customdata] == [
        [9, 5],
        [9, 2],
    ]
    assert "Zero-based suggestion index" in str(title_trace.hovertemplate)


def test_readability_change_chart_uses_final_minus_selected_direction() -> None:
    figure = build_readability_change_direction_chart(readability_change_rows())
    traces = {str(trace.name): trace for trace in figure.data}

    assert figure.layout.title.text == (
        "Selected-to-final Flesch-Kincaid direction by field"
    )
    assert figure.layout.barmode == "stack"
    assert list(traces["Final value decreased"].x) == [
        "Description",
        "Title",
    ]
    assert list(traces["Final value decreased"].y) == [3, 2]
    assert list(traces["Final value increased"].y) == [1, 3]
    assert (figure.layout.legend.title.text) == "Final minus selected direction"
    assert "No-material-change tolerance" in str(
        traces["No material change"].hovertemplate
    )


def test_final_grade_bands_chart_uses_observed_final_texts() -> None:
    figure = build_final_grade_bands_chart(readability_target_rows())
    traces = {str(trace.name): trace for trace in figure.data}

    assert figure.layout.title.text == ("Observed final Flesch-Kincaid grade bands")
    assert figure.layout.barmode == "stack"
    assert list(traces["At or below grade 6"].x) == [
        "Description — MANUAL",
        "Title — AI",
    ]
    assert list(traces["At or below grade 6"].y) == [1, 2]
    assert "Observed nonblank final texts" in str(
        traces["At or below grade 6"].hovertemplate
    )
    assert "Short-text caution applies" in str(
        traces["At or below grade 6"].customdata[1][2]
    )


def test_selected_vs_unselected_chart_uses_comparable_attempts() -> None:
    figure = build_selected_vs_unselected_readability_chart(selected_comparison_rows())
    bar = figure.data[0]

    assert figure.layout.title.text == (
        "Selected versus mean-unselected Flesch-Kincaid difference"
    )
    assert list(bar.x) == ["Description", "Title"]
    assert list(bar.y) == [0.75, -0.5]
    assert [list(value) for value in bar.customdata] == [
        [4, 1, 1, 2, 0.1],
        [5, 3, 1, 1, 0.1],
    ]
    assert "Comparable completed AI attempts" in str(bar.hovertemplate)
    assert len(figure.layout.shapes) == 1


def test_edit_readability_chart_preserves_categories_and_denominators() -> None:
    figure = build_edit_readability_relationship_chart(edit_readability_cross_rows())
    traces = {str(trace.name): trace for trace in figure.data}
    decreased = traces["Consensus grade-level decrease"]
    mixed = traces["Mixed formula direction"]

    assert figure.layout.title.text == (
        "Edit intensity and consensus grade-level direction"
    )
    assert figure.layout.barmode == "stack"
    assert list(decreased.x) == [
        "Title — Light edit (N=5)",
        "Description — Edited, unclassified (N=4)",
    ]
    assert list(decreased.y) == [40.0, 0.0]
    assert list(mixed.y) == [0.0, 50.0]
    assert list(decreased.customdata[0][:4]) == [
        "Title",
        "Light edit",
        "Character edit ratio at or below 10%",
        "Grade-level formulas agreed on a downward direction",
    ]
    assert list(decreased.customdata[0][4:7]) == [5, 2, 40.0]
    hovertemplate = str(decreased.hovertemplate)
    assert "Fields in this group" in hovertemplate
    assert "Fields with this result" in hovertemplate
    assert "Share of this group" in hovertemplate
    assert "final text minus selected suggestion" in hovertemplate
    assert "Median consensus direction value" not in hovertemplate
    assert "Published percentage" not in hovertemplate


def test_source_input_method_charts_use_explicit_populations() -> None:
    returned = build_source_input_method_chart(
        source_context_distribution_rows(),
        spec=SourcePopulationChartSpec(
            population_name="ALL_SUCCESSFUL_AI_GENERATIONS",
            input_method_title=(
                "Input method for AI generations that returned a result"
            ),
            latency_title="Unused latency title",
            count_label="Generation attempts returning a result",
            denominator_label=(
                "Share among generation attempts with a recorded input method"
            ),
            empty_population_label="AI generations that returned a result",
        ),
    )
    completed = build_source_input_method_chart(
        source_context_distribution_rows(),
        spec=SourcePopulationChartSpec(
            population_name="COMPLETED_AI_ATTEMPTS",
            input_method_title=("Input method for completed AI-assisted attempts"),
            latency_title="Unused latency title",
            count_label="Completed AI-assisted attempts",
            denominator_label=(
                "Share among completed AI-assisted attempts with a "
                "recorded input method"
            ),
            empty_population_label="completed AI-assisted attempts",
        ),
    )

    returned_bar = returned.data[0]
    completed_bar = completed.data[0]

    assert returned.layout.title.text == (
        "Input method for AI generations that returned a result"
    )
    assert list(returned_bar.x) == [2, 3]
    assert "Generation attempts returning a result" in str(returned_bar.hovertemplate)
    assert "Successful AI generations" not in str(returned_bar.hovertemplate)

    assert completed.layout.title.text == (
        "Input method for completed AI-assisted attempts"
    )
    assert list(completed_bar.x) == [1, 2]
    assert "Completed AI-assisted attempts" in str(completed_bar.hovertemplate)


def test_source_size_latency_charts_use_explicit_populations() -> None:
    returned = build_source_size_latency_chart(
        source_size_latency_rows(),
        spec=SourcePopulationChartSpec(
            population_name="ALL_SUCCESSFUL_AI_GENERATIONS",
            input_method_title="Unused input title",
            latency_title=(
                "Latency by source-size band for AI generations that returned a result"
            ),
            count_label="Generation attempts returning a result",
            denominator_label="Unused denominator label",
            empty_population_label="AI generations that returned a result",
        ),
    )
    completed = build_source_size_latency_chart(
        source_size_latency_rows(),
        spec=SourcePopulationChartSpec(
            population_name="COMPLETED_AI_ATTEMPTS",
            input_method_title="Unused input title",
            latency_title=(
                "Latency by source-size band for completed AI-assisted attempts"
            ),
            count_label="Completed AI-assisted attempts",
            denominator_label="Unused denominator label",
            empty_population_label="completed AI-assisted attempts",
        ),
    )

    returned_bar = returned.data[0]
    completed_bar = completed.data[0]

    assert list(returned_bar.y) == [1.0, 2.0]
    assert list(completed_bar.y) == [1.2, 2.4]
    assert list(returned_bar.error_y.arrayminus) == [0.1, 0.2]
    assert list(completed_bar.error_y.arrayminus) == [0.1, 0.0]
    assert "Generation attempts returning a result in band" in str(
        returned_bar.hovertemplate
    )
    assert "Completed AI-assisted attempts in band" in str(completed_bar.hovertemplate)
    assert "Attempts missing captured latency" in str(returned_bar.hovertemplate)


def test_repeated_source_consistency_chart_separates_denominators() -> None:
    figure = build_repeated_source_consistency_chart(repeated_source_rows())
    traces = {str(trace.name): trace for trace in figure.data}

    assert figure.layout.title.text == (
        "Captured source changes between AI generations before completion"
    )
    assert figure.layout.barmode == "stack"
    assert list(traces["Unchanged"].x) == [60.0, 60.0, 60.0, 60.0]
    assert list(traces["Changed"].x) == [40.0, 40.0, 40.0, 40.0]
    assert "Missing or unavailable" not in traces
    assert "Comparable transitions" in str(traces["Changed"].hovertemplate)
    assert "Percentage among comparable transitions" in str(
        traces["Changed"].hovertemplate
    )
    assert "Positive means the later generation took longer" in str(
        traces["Changed"].hovertemplate
    )
    assert len(figure.layout.annotations) == 4
    assert {str(annotation.text) for annotation in figure.layout.annotations} == {
        "Unavailable: 2 of 7 transitions (28.6%)"
    }
    assert figure.layout.xaxis.title.text == ("Percentage among comparable transitions")


def test_repeated_source_chart_suppresses_zero_unavailable_labels() -> None:
    rows = repeated_source_rows()
    missing = rows["comparison_category"].eq("MISSING")
    rows.loc[missing, "population_unit_count"] = 5
    rows.loc[missing, "eligible_unit_count"] = 0
    rows.loc[missing, "category_unit_count"] = 0
    rows.loc[missing, "category_unit_percentage"] = pd.NA

    figure = build_repeated_source_consistency_chart(rows)

    assert len(figure.layout.annotations) == 0
    assert figure.layout.margin.r == 70


def study_retry_pathway_rows() -> pd.DataFrame:
    """Return aggregate-only retry pathway rows."""
    return pd.DataFrame.from_records(
        [
            {
                "pathway_category": "SINGLE_ATTEMPT_AI_COMPLETION",
                "pathway_sequence": 1,
                "study_count": 4,
                "population_study_count": 10,
                "study_percentage": 40.0,
                "median_attempt_count": 1.0,
                "study_count_with_author_change": 0,
                "median_minutes_first_to_completion": 0.0,
                "median_minutes_first_to_last_observed_attempt": None,
            },
            {
                "pathway_category": "AI_TO_MANUAL_COMPLETION",
                "pathway_sequence": 5,
                "study_count": 2,
                "population_study_count": 10,
                "study_percentage": 20.0,
                "median_attempt_count": 3.0,
                "study_count_with_author_change": 1,
                "median_minutes_first_to_completion": 45.0,
                "median_minutes_first_to_last_observed_attempt": None,
            },
            {
                "pathway_category": "MIXED_MODES_NO_COMPLETION_OBSERVED",
                "pathway_sequence": 13,
                "study_count": 1,
                "population_study_count": 10,
                "study_percentage": 10.0,
                "median_attempt_count": 2.0,
                "study_count_with_author_change": 0,
                "median_minutes_first_to_completion": None,
                "median_minutes_first_to_last_observed_attempt": 30.0,
            },
        ]
    )


def test_retry_pathways_chart_is_horizontal_and_mutually_exclusive() -> None:
    """Render one horizontal bar per stable study pathway."""
    figure = build_retry_pathways_chart(study_retry_pathway_rows())
    bar = figure.data[0]

    assert figure.layout.title.text == "Observed retry pathways"
    assert bar.orientation == "h"
    assert list(bar.x) == [4, 2, 1]
    assert len(bar.y) == 3
    assert "AI to manual" in str(bar.y[1])
    assert "no completion observed" in str(bar.y[2]).lower()


def test_content_source_chart_uses_all_attempt_population() -> None:
    figure = build_content_source_concordance_chart(content_source_rows())
    heatmap = figure.data[0]

    assert figure.layout.title.text == "Reported versus inferred content source"
    assert list(heatmap.x) == ["other", "registry"]
    assert list(heatmap.y) == ["registry"]
    assert [list(row) for row in heatmap.z] == [[1, 3]]


def test_chart_bundle_contains_all_figures() -> None:
    charts = build_exploration_charts(
        ExplorationChartInputs(
            overview_summary=overview_rows(),
            grouped_attempt_summary=grouped_attempt_rows(),
            study_attempt_history_summary=study_history_rows(),
            author_handoff_summary=author_handoff_rows(),
            study_retry_pathway_summary=study_retry_pathway_rows(),
            attempt_start_experience_summary=(attempt_start_experience_rows()),
            current_author_experience_summary=(current_author_experience_rows()),
            grouped_study_summary=grouped_study_rows(),
            completed_study_author_context_summary=(
                completed_study_author_context_rows()
            ),
            grouped_author_summary=grouped_author_rows(),
            field_adoption_editing_summary=field_adoption_rows(),
            compensation_analysis_summary=compensation_analysis_rows(),
            suggestion_selection_summary=suggestion_selection_rows(),
            field_readability_change_summary=readability_change_rows(),
            field_readability_target_summary=readability_target_rows(),
            selected_vs_unselected_readability_summary=(selected_comparison_rows()),
            field_edit_readability_cross_summary=edit_readability_cross_rows(),
            content_source_matrix=content_source_rows(),
            source_context_distribution_summary=(source_context_distribution_rows()),
            source_size_latency_summary=source_size_latency_rows(),
            repeated_attempt_source_consistency_summary=(repeated_source_rows()),
        )
    )

    assert isinstance(charts, ExplorationCharts)
    assert charts.attempt_outcomes_by_mode.data
    assert charts.attempt_timing_distribution_by_mode.data
    assert charts.study_completion_pathways.data
    assert charts.author_handoff_categories.data
    assert charts.retry_pathways.data
    assert charts.author_attempt_start_experience.data
    assert charts.author_experience_studies.data
    assert charts.author_experience_days.data
    assert charts.content_source_concordance.data
    assert charts.returned_result_input_method_preference.data
    assert charts.returned_result_source_size_latency.data
    assert charts.completed_ai_input_method_preference.data
    assert charts.completed_ai_source_size_latency.data
    assert charts.repeated_attempt_source_consistency.data
    assert charts.completed_study_participant_mix.data
    assert charts.completed_study_department_mix.data
    assert charts.completed_studies_by_completion_author_role.data
    assert charts.completed_studies_by_completion_author_pi_status.data
    assert charts.author_appointment_schools.data
    assert charts.pi_appointment_schools.data
    assert charts.author_appointment_departments.data
    assert charts.pi_appointment_departments.data
    assert charts.author_appointment_titles.data
    assert charts.pi_appointment_titles.data
    assert charts.field_suggestion_adoption.data
    assert charts.field_selected_outcomes.data
    assert charts.suggestion_selection_by_kind.data
    assert charts.suggestion_selection_by_index.data
    assert charts.compensation_suggestion_use.data
    assert charts.readability_change_direction.data
    assert charts.final_grade_bands.data
    assert charts.selected_vs_unselected_readability.data
    assert charts.edit_readability_relationship.data


def assert_edit_readability_chart_has_accessible_empty_state() -> None:
    """Assert the edit/readability chart provides empty-state text."""
    figure = build_edit_readability_relationship_chart(
        pd.DataFrame(columns=edit_readability_cross_rows().columns)
    )

    assert figure.layout.annotations[0].text


def assert_attempt_timing_chart_has_accessible_empty_state() -> None:
    """Assert the attempt-timing chart provides empty-state text."""
    figure = build_attempt_timing_chart(
        pd.DataFrame(columns=grouped_attempt_rows().columns)
    )

    assert figure.layout.annotations[0].text


def test_charts_return_accessible_empty_states() -> None:
    study_columns = study_history_rows().columns
    handoff_columns = author_handoff_rows().columns
    attempt_start_experience_columns = attempt_start_experience_rows().columns
    attempt_start_experience_figure = build_author_attempt_start_experience_chart(
        pd.DataFrame(columns=attempt_start_experience_columns)
    )
    experience_columns = current_author_experience_rows().columns
    content_columns = content_source_rows().columns
    grouped_study_columns = grouped_study_rows().columns
    completed_study_context_columns = completed_study_author_context_rows().columns
    grouped_author_columns = grouped_author_rows().columns
    field_adoption_columns = field_adoption_rows().columns
    suggestion_columns = suggestion_selection_rows().columns
    readability_change_columns = readability_change_rows().columns
    readability_target_columns = readability_target_rows().columns
    selected_comparison_columns = selected_comparison_rows().columns

    attempt_figure = build_attempt_outcomes_chart(
        pd.DataFrame(columns=overview_rows().columns)
    )
    study_figure = build_study_completion_pathways_chart(
        pd.DataFrame(columns=study_columns)
    )
    handoff_figure = build_author_handoff_chart(pd.DataFrame(columns=handoff_columns))
    experience_figure = build_author_experience_chart(
        pd.DataFrame(columns=experience_columns),
        metric_unit="studies",
    )
    content_figure = build_content_source_concordance_chart(
        pd.DataFrame(columns=content_columns)
    )
    study_mix_figure = build_completed_study_mix_chart(
        pd.DataFrame(columns=grouped_study_columns),
        dimension_name="STUDY_PARTICIPANT_TYPE",
        title="Completed studies by participant type",
    )
    completion_author_context_figure = build_completed_study_author_context_chart(
        pd.DataFrame(columns=completed_study_context_columns),
        dimension_name="EFFECTIVE_ROLE",
        title=("Completed studies by authoring mode and completion-author role"),
    )
    author_appointment_figure = build_author_appointment_context_chart(
        pd.DataFrame(columns=grouped_author_columns),
        dimension_name="AUTHOR_APPOINTMENT_SCHOOL",
        title="Author appointment schools",
    )

    field_adoption_figure = build_field_suggestion_adoption_chart(
        pd.DataFrame(columns=field_adoption_columns)
    )
    field_outcomes_figure = build_field_selected_outcomes_chart(
        pd.DataFrame(columns=field_adoption_columns)
    )
    suggestion_kind_figure = build_suggestion_selection_by_kind_chart(
        pd.DataFrame(columns=suggestion_columns)
    )
    suggestion_index_figure = build_suggestion_selection_by_index_chart(
        pd.DataFrame(columns=suggestion_columns)
    )
    readability_change_figure = build_readability_change_direction_chart(
        pd.DataFrame(columns=readability_change_columns)
    )
    readability_target_figure = build_final_grade_bands_chart(
        pd.DataFrame(columns=readability_target_columns)
    )
    selected_comparison_figure = build_selected_vs_unselected_readability_chart(
        pd.DataFrame(columns=selected_comparison_columns)
    )

    assert attempt_figure.layout.annotations[0].text
    assert_attempt_timing_chart_has_accessible_empty_state()
    assert study_figure.layout.annotations[0].text
    assert handoff_figure.layout.annotations[0].text
    assert attempt_start_experience_figure.layout.annotations[0].text
    assert experience_figure.layout.annotations[0].text
    assert content_figure.layout.annotations[0].text
    assert study_mix_figure.layout.annotations[0].text
    assert completion_author_context_figure.layout.annotations[0].text
    assert author_appointment_figure.layout.annotations[0].text
    assert field_adoption_figure.layout.annotations[0].text
    assert field_outcomes_figure.layout.annotations[0].text
    assert suggestion_kind_figure.layout.annotations[0].text
    assert suggestion_index_figure.layout.annotations[0].text
    assert readability_change_figure.layout.annotations[0].text
    assert readability_target_figure.layout.annotations[0].text
    assert selected_comparison_figure.layout.annotations[0].text
    assert_edit_readability_chart_has_accessible_empty_state()


@pytest.mark.parametrize(
    ("builder", "frame"),
    [
        (
            build_attempt_outcomes_chart,
            pd.DataFrame(
                {
                    "overview_metric_name": ["all_attempt_count"],
                }
            ),
        ),
        (
            build_study_completion_pathways_chart,
            pd.DataFrame(
                {
                    "final_completion_authoring_mode": ["AI"],
                }
            ),
        ),
        (
            build_author_handoff_chart,
            pd.DataFrame(
                {
                    "completed_attempt_authoring_mode": ["AI"],
                }
            ),
        ),
        (
            build_author_attempt_start_experience_chart,
            pd.DataFrame(
                {
                    "author_adoption_group": ["ALL_AUTHORS"],
                }
            ),
        ),
        (
            lambda frame: build_author_experience_chart(
                frame,
                metric_unit="studies",
            ),
            pd.DataFrame(
                {
                    "author_adoption_group": ["ALL_AUTHORS"],
                }
            ),
        ),
        (
            build_content_source_concordance_chart,
            pd.DataFrame(
                {
                    "attempt_completion_group": ["ALL"],
                }
            ),
        ),
        (
            lambda frame: build_completed_study_mix_chart(
                frame,
                dimension_name="STUDY_PARTICIPANT_TYPE",
                title="Completed studies by participant type",
            ),
            pd.DataFrame(
                {
                    "study_population_name": ["COMPLETED_STUDIES"],
                }
            ),
        ),
        (
            lambda frame: build_completed_study_author_context_chart(
                frame,
                dimension_name="EFFECTIVE_ROLE",
                title=(
                    "Completed studies by authoring mode and completion-author role"
                ),
            ),
            pd.DataFrame(
                {
                    "context_dimension_name": ["EFFECTIVE_ROLE"],
                }
            ),
        ),
        (
            lambda frame: build_author_appointment_context_chart(
                frame,
                dimension_name="AUTHOR_APPOINTMENT_SCHOOL",
                title="Author appointment schools",
            ),
            pd.DataFrame(
                {
                    "author_population_name": ["ALL_AUTHORS"],
                }
            ),
        ),
        (
            build_field_suggestion_adoption_chart,
            pd.DataFrame(
                {
                    "field_name": ["title"],
                }
            ),
        ),
        (
            build_field_selected_outcomes_chart,
            pd.DataFrame(
                {
                    "field_name": ["title"],
                }
            ),
        ),
        (
            build_suggestion_selection_by_kind_chart,
            pd.DataFrame(
                {
                    "field_name": ["title"],
                }
            ),
        ),
        (
            build_suggestion_selection_by_index_chart,
            pd.DataFrame(
                {
                    "field_name": ["title"],
                }
            ),
        ),
        (
            build_readability_change_direction_chart,
            pd.DataFrame(
                {
                    "field_name": ["title"],
                }
            ),
        ),
        (
            build_final_grade_bands_chart,
            pd.DataFrame(
                {
                    "field_name": ["title"],
                }
            ),
        ),
    ],
)
def test_charts_require_aggregate_columns(
    builder: Callable[[pd.DataFrame], go.Figure],
    frame: pd.DataFrame,
) -> None:
    with pytest.raises(
        ExplorationValidationError,
        match="lacks required chart columns",
    ):
        builder(frame)


def test_author_appointment_context_chart_preserves_overlapping_groups() -> None:
    figure = build_author_appointment_context_chart(
        grouped_author_rows(),
        dimension_name="AUTHOR_APPOINTMENT_SCHOOL",
        title="Author appointment schools",
    )
    bar = figure.data[0]

    assert list(bar.y) == ["School B", "School A"]
    assert list(bar.x) == [5, 6]
    assert "Groups may overlap" in str(bar.hovertemplate)


def test_appointment_context_chart_uses_dimension_specific_labels() -> None:
    """Use department and title wording rather than school wording."""
    department = build_author_appointment_context_chart(
        grouped_author_rows(),
        dimension_name="AUTHOR_APPOINTMENT_DEPARTMENT",
        title="Author appointment departments",
    )
    title = build_author_appointment_context_chart(
        grouped_author_rows(),
        dimension_name="PI_APPOINTMENT_TITLE",
        title="Principal-investigator appointment titles",
    )

    department_bar = department.data[0]
    title_bar = title.data[0]

    assert department.layout.yaxis.title.text == "Appointment department"
    assert "Appointment department" in str(department_bar.hovertemplate)
    assert list(department_bar.y) == ["Emergency Medicine"]
    assert department.layout.yaxis.tickmode == "array"
    assert list(department.layout.yaxis.tickvals) == ["Emergency Medicine"]
    assert list(department.layout.yaxis.ticktext) == ["Emergency Medicine"]
    assert department.layout.height >= 420
    assert title.layout.yaxis.title.text == "Appointment title"
    assert "Appointment title" in str(title_bar.hovertemplate)
    assert list(title_bar.y) == ["ASSOCIATE PROFESSOR"]
    assert title.layout.yaxis.tickmode == "array"
    assert list(title.layout.yaxis.tickvals) == ["ASSOCIATE PROFESSOR"]
    assert list(title.layout.yaxis.ticktext) == ["ASSOCIATE PROFESSOR"]
    assert title.layout.height >= 420


def test_appointment_chart_height_grows_with_category_count() -> None:
    """Keep every appointment category label visible without requiring hover."""
    rows = grouped_author_rows()
    template = rows.loc[
        rows["grouping_dimension_name"].eq("AUTHOR_APPOINTMENT_TITLE")
    ].iloc[0]
    additions = pd.DataFrame.from_records(
        [
            {
                **template.to_dict(),
                "grouping_dimension_value": f"SYNTHETIC TITLE {index:02d}",
                "distinct_author_count": index + 1,
            }
            for index in range(20)
        ]
    )
    rows = pd.concat([rows, additions], ignore_index=True)

    figure = build_author_appointment_context_chart(
        rows,
        dimension_name="AUTHOR_APPOINTMENT_TITLE",
        title="Author appointment titles",
    )
    bar = figure.data[0]

    assert len(bar.y) == 21
    assert len(figure.layout.yaxis.tickvals) == 21
    assert len(figure.layout.yaxis.ticktext) == 21
    assert figure.layout.height == 34 * 21 + 150


def test_author_appointment_context_chart_rejects_unsupported_dimension() -> None:
    """Reject dimensions that are not appointment title, department, or school."""
    with pytest.raises(
        ExplorationValidationError,
        match="unsupported appointment chart dimension",
    ):
        build_author_appointment_context_chart(
            grouped_author_rows(),
            dimension_name="UNKNOWN_APPOINTMENT_DIMENSION",
            title="Unsupported",
        )


def test_author_appointment_context_chart_rejects_exclusive_groups() -> None:
    rows = grouped_author_rows()
    rows.loc[
        rows["grouping_dimension_name"].eq("AUTHOR_APPOINTMENT_SCHOOL"),
        "group_values_are_mutually_exclusive",
    ] = True

    with pytest.raises(
        ExplorationValidationError,
        match="must contain non-mutually-exclusive groups",
    ):
        build_author_appointment_context_chart(
            rows,
            dimension_name="AUTHOR_APPOINTMENT_SCHOOL",
            title="Author appointment schools",
        )
