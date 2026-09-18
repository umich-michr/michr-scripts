from collections.abc import Callable

import pandas as pd
import plotly.graph_objects as go
import pytest

from study_posting_audit_exploration import (
    ExplorationValidationError,
)
from study_posting_audit_exploration.publication import (
    ExplorationChartInputs,
    ExplorationCharts,
    build_attempt_outcomes_chart,
    build_attempt_timing_chart,
    build_author_appointment_context_chart,
    build_author_attempt_start_experience_chart,
    build_author_experience_chart,
    build_author_handoff_chart,
    build_completed_study_mix_chart,
    build_content_source_concordance_chart,
    build_edit_readability_relationship_chart,
    build_exploration_charts,
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


def grouped_attempt_rows() -> pd.DataFrame:
    """Return synthetic aggregate-only attempt rows."""
    return pd.DataFrame.from_records(
        [
            {
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
                "attempt_count_with_nonmissing_total_attempt_time": 2,
                "attempt_count_missing_total_attempt_time": 0,
                "percentile_25_total_attempt_minutes": 0.75,
                "median_total_attempt_minutes": 1.0,
                "percentile_75_total_attempt_minutes": 1.25,
                "percentile_90_total_attempt_minutes": 1.5,
            },
            {
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
                "attempt_result": "ALL",
                "attempt_authoring_mode": "AI",
                "grouping_dimension_1_name": "AUTHORING_MODE",
                "grouping_dimension_2_name": "NONE",
                "attempt_count": 6,
                "attempt_count_with_nonmissing_study_info_page_time": 5,
                "attempt_count_missing_study_info_page_time": 1,
                "percentile_25_study_info_page_minutes": 1.0,
                "median_study_info_page_minutes": 2.0,
                "percentile_75_study_info_page_minutes": 3.0,
                "percentile_90_study_info_page_minutes": 4.0,
                "attempt_count_with_nonmissing_total_attempt_time": 6,
                "attempt_count_missing_total_attempt_time": 0,
                "percentile_25_total_attempt_minutes": 1.5,
                "median_total_attempt_minutes": 2.5,
                "percentile_75_total_attempt_minutes": 4.0,
                "percentile_90_total_attempt_minutes": 5.0,
            },
            {
                "attempt_result": "ALL",
                "attempt_authoring_mode": "MANUAL",
                "grouping_dimension_1_name": "AUTHORING_MODE",
                "grouping_dimension_2_name": "NONE",
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
    )


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
                "median_author_attempt_value": 2.0,
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
                "median_author_attempt_value": 5.0,
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
                "median_author_attempt_value": 1.0,
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
                    "median_author_value": median,
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


def content_source_rows() -> pd.DataFrame:
    """Return synthetic aggregate-only concordance rows."""
    return pd.DataFrame.from_records(
        [
            {
                "attempt_completion_group": "ALL",
                "reported_study_content_source": "registry",
                "inferred_study_content_source": "registry",
                "ai_attempt_count": 3,
            },
            {
                "attempt_completion_group": "ALL",
                "reported_study_content_source": "registry",
                "inferred_study_content_source": "other",
                "ai_attempt_count": 1,
            },
            {
                "attempt_completion_group": "COMPLETE",
                "reported_study_content_source": "registry",
                "inferred_study_content_source": "registry",
                "ai_attempt_count": 2,
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


def test_attempt_outcomes_chart_uses_aggregate_counts() -> None:
    figure = build_attempt_outcomes_chart(grouped_attempt_rows())

    assert figure.layout.title.text == "Attempt outcomes by authoring mode"
    assert figure.layout.barmode == "stack"
    assert list(figure.data[0].x) == ["AI", "MANUAL"]
    assert list(figure.data[0].y) == [4, 3]


def test_attempt_timing_chart_shows_two_timing_distributions() -> None:
    figure = build_attempt_timing_chart(grouped_attempt_rows())
    traces = {str(trace.name): trace for trace in figure.data}

    assert figure.layout.title.text == (
        "Attempt timing distributions by authoring mode"
    )
    assert figure.layout.barmode == "group"
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
        [6, 0],
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


def test_author_attempt_start_experience_chart_uses_attempt_grain() -> None:
    figure = build_author_attempt_start_experience_chart(
        attempt_start_experience_rows()
    )
    bar = figure.data[0]

    assert figure.layout.title.text == ("Median studies created before attempt start")
    assert list(bar.x) == ["AI", "MANUAL"]
    assert list(bar.y) == [2.0, 5.0]
    assert [values[0] for values in bar.customdata] == [6, 4]
    assert "Author-attempt observations with value" in str(bar.hovertemplate)
    assert "Definition:" in str(bar.hovertemplate)


def test_query_time_author_experience_tooltip_uses_author_grain() -> None:
    figure = build_author_experience_chart(
        current_author_experience_rows(),
        metric_unit="days",
    )
    bar = figure.data[0]

    assert "Distinct authors with value" in str(bar.hovertemplate)
    assert "Unit:" in str(bar.hovertemplate)
    assert "Definition:" in str(bar.hovertemplate)
    assert bar.customdata[0][0] == 4
    assert bar.customdata[0][1] == "days"


def test_author_experience_chart_separates_units() -> None:
    studies_figure = build_author_experience_chart(
        current_author_experience_rows(),
        metric_unit="studies",
    )
    days_figure = build_author_experience_chart(
        current_author_experience_rows(),
        metric_unit="days",
    )

    assert (
        studies_figure.layout.title.text
        == "Median author experience at report query time: studies"
    )
    assert studies_figure.layout.barmode == "group"
    assert len(studies_figure.data) == 2
    assert list(studies_figure.data[0].x) == [
        "All authors",
        "AI only",
        "Manual only",
        "Both AI and manual",
    ]
    assert list(studies_figure.data[0].y) == [12.0, 8.0, 15.0, 11.0]
    assert list(studies_figure.data[1].y) == [5.0, 3.0, 7.0, 4.0]

    assert (
        days_figure.layout.title.text
        == "Median author experience at report query time: days"
    )
    assert len(days_figure.data) == 2
    assert list(days_figure.data[0].y) == [30.0, 20.0, 45.0, 35.0]
    assert list(days_figure.data[1].y) == [300.0, 180.0, 420.0, 360.0]


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
            grouped_attempt_summary=grouped_attempt_rows(),
            study_attempt_history_summary=study_history_rows(),
            author_handoff_summary=author_handoff_rows(),
            attempt_start_experience_summary=(attempt_start_experience_rows()),
            current_author_experience_summary=(current_author_experience_rows()),
            grouped_study_summary=grouped_study_rows(),
            grouped_author_summary=grouped_author_rows(),
            field_adoption_editing_summary=field_adoption_rows(),
            suggestion_selection_summary=suggestion_selection_rows(),
            field_readability_change_summary=readability_change_rows(),
            field_readability_target_summary=readability_target_rows(),
            selected_vs_unselected_readability_summary=(selected_comparison_rows()),
            field_edit_readability_cross_summary=edit_readability_cross_rows(),
            content_source_matrix=content_source_rows(),
        )
    )

    assert isinstance(charts, ExplorationCharts)
    assert charts.attempt_outcomes_by_mode.data
    assert charts.attempt_timing_distribution_by_mode.data
    assert charts.study_completion_pathways.data
    assert charts.author_handoff_categories.data
    assert charts.author_attempt_start_experience.data
    assert charts.author_experience_studies.data
    assert charts.author_experience_days.data
    assert charts.content_source_concordance.data
    assert charts.completed_study_participant_mix.data
    assert charts.completed_study_department_mix.data
    assert charts.author_appointment_schools.data
    assert charts.pi_appointment_schools.data
    assert charts.field_suggestion_adoption.data
    assert charts.field_selected_outcomes.data
    assert charts.suggestion_selection_by_kind.data
    assert charts.suggestion_selection_by_index.data
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
    attempt_columns = grouped_attempt_rows().columns
    study_columns = study_history_rows().columns
    handoff_columns = author_handoff_rows().columns
    attempt_start_experience_columns = attempt_start_experience_rows().columns
    attempt_start_experience_figure = build_author_attempt_start_experience_chart(
        pd.DataFrame(columns=attempt_start_experience_columns)
    )
    experience_columns = current_author_experience_rows().columns
    content_columns = content_source_rows().columns
    grouped_study_columns = grouped_study_rows().columns
    grouped_author_columns = grouped_author_rows().columns
    field_adoption_columns = field_adoption_rows().columns
    suggestion_columns = suggestion_selection_rows().columns
    readability_change_columns = readability_change_rows().columns
    readability_target_columns = readability_target_rows().columns
    selected_comparison_columns = selected_comparison_rows().columns

    attempt_figure = build_attempt_outcomes_chart(pd.DataFrame(columns=attempt_columns))
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
                    "attempt_result": ["COMPLETE"],
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
