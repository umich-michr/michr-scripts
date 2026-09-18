from pathlib import Path

import pandas as pd
import pytest

from study_posting_audit_exploration import (
    ExplorationInputError,
    ExplorationValidationError,
)
from study_posting_audit_exploration.publication import (
    ExplorationChartInputs,
    ExplorationCharts,
    build_exploration_charts,
)
from study_posting_audit_exploration.publication.html_report import (
    render_html_report,
    write_html_report,
)


def overview_rows() -> pd.DataFrame:
    """Return synthetic aggregate-only overview rows."""
    return pd.DataFrame.from_records(
        [
            {
                "overview_metric_name": ("distinct_study_count_with_any_attempt"),
                "overview_metric_label": "Distinct studies",
                "metric_count": 10,
                "metric_denominator_count": 10,
                "metric_percentage": 100.0,
            },
            {
                "overview_metric_name": "distinct_completed_study_count",
                "overview_metric_label": "Completed studies",
                "metric_count": 8,
                "metric_denominator_count": 10,
                "metric_percentage": 80.0,
            },
        ]
    )


def quality_rows(
    *,
    malformed_appointment_count: int = 2,
) -> pd.DataFrame:
    """Return aggregate-only quality rows for HTML rendering."""
    rows: list[dict[str, object]] = [
        {
            "data_quality_check_name": f"SYNTHETIC_FATAL_{index:02d}",
            "severity_level": "FATAL",
            "affected_attempt_count": 0,
            "affected_distinct_study_count": 0,
            "affected_distinct_author_count": 0,
            "eligible_attempt_count": 10,
            "affected_attempt_percentage": 0.0,
            "analysis_consequence": (
                "Any detected case stops validation and publication."
            ),
        }
        for index in range(13)
    ]

    for name, affected, studies, authors in (
        ("ATTEMPT_AFTER_COMPLETION", 0, 0, 0),
        ("CREATED_BY_ID_VARIES_WITHIN_STUDY", 0, 0, 0),
        (
            "MALFORMED_APPOINTMENT",
            malformed_appointment_count,
            min(malformed_appointment_count, 2),
            min(malformed_appointment_count, 2),
        ),
    ):
        rows.append(
            {
                "data_quality_check_name": name,
                "severity_level": "WARNING",
                "affected_attempt_count": affected,
                "affected_distinct_study_count": studies,
                "affected_distinct_author_count": authors,
                "eligible_attempt_count": 10,
                "affected_attempt_percentage": 10.0 * affected,
                "analysis_consequence": (
                    "Malformed entries are excluded from appointment groups."
                    if name == "MALFORMED_APPOINTMENT"
                    else "Synthetic warning consequence."
                ),
            }
        )

    return pd.DataFrame.from_records(rows)


def attempt_rows() -> pd.DataFrame:
    """Return aggregate-only attempt chart rows."""
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
                "attempt_result": "ALL",
                "attempt_authoring_mode": "AI",
                "grouping_dimension_1_name": "AUTHORING_MODE",
                "grouping_dimension_2_name": "NONE",
                "attempt_count": 4,
                "attempt_count_with_nonmissing_study_info_page_time": 3,
                "attempt_count_missing_study_info_page_time": 1,
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
        ]
    )


def study_history_rows() -> pd.DataFrame:
    """Return aggregate-only study-pathway rows."""
    return pd.DataFrame.from_records(
        [
            {
                "final_completion_authoring_mode": "AI",
                "distinct_study_count": 4,
                "study_count_with_preceding_incomplete_attempts": 1,
                "minimum_minutes_first_attempt_to_completion": 4.0,
                "median_minutes_first_attempt_to_completion": 12.0,
                "average_minutes_first_attempt_to_completion": 14.0,
                "standard_deviation_minutes_first_attempt_to_completion": 5.0,
                "maximum_minutes_first_attempt_to_completion": 24.0,
            },
            {
                "final_completion_authoring_mode": "MANUAL",
                "distinct_study_count": 3,
                "study_count_with_preceding_incomplete_attempts": 2,
                "minimum_minutes_first_attempt_to_completion": 6.0,
                "median_minutes_first_attempt_to_completion": 18.0,
                "average_minutes_first_attempt_to_completion": 22.0,
                "standard_deviation_minutes_first_attempt_to_completion": 8.0,
                "maximum_minutes_first_attempt_to_completion": 40.0,
            },
        ]
    )


def author_handoff_rows() -> pd.DataFrame:
    """Return aggregate-only handoff rows."""
    return pd.DataFrame.from_records(
        [
            {
                "completed_attempt_authoring_mode": "AI",
                "author_handoff_category": "NO_PRECEDING_ATTEMPT",
                "distinct_completed_study_count": 3,
            },
            {
                "completed_attempt_authoring_mode": "AI",
                "author_handoff_category": ("ALL_PRECEDING_ATTEMPTS_BY_OTHER_AUTHORS"),
                "distinct_completed_study_count": 1,
            },
            {
                "completed_attempt_authoring_mode": "MANUAL",
                "author_handoff_category": (
                    "ALL_PRECEDING_ATTEMPTS_BY_COMPLETION_AUTHOR"
                ),
                "distinct_completed_study_count": 3,
            },
        ]
    )


def attempt_start_experience_rows() -> pd.DataFrame:
    """Return aggregate-only attempt-start experience rows."""
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
                "author_attempt_count_with_nonmissing_metric": 4,
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
                "author_attempt_count_with_nonmissing_metric": 3,
                "median_author_attempt_value": 5.0,
            },
        ]
    )


def current_author_experience_rows() -> pd.DataFrame:
    """Return aggregate-only query-time author experience rows."""
    rows: list[dict[str, object]] = [
        {
            "author_adoption_group": "ALL_AUTHORS",
            "experience_metric_name": (
                "total_studies_created_as_of_report_query_count"
            ),
            "experience_metric_unit": "studies",
            "author_count_with_nonmissing_metric": 4,
            "median_author_value": 10.0,
        },
        {
            "author_adoption_group": "AI_ONLY",
            "experience_metric_name": (
                "total_studies_created_as_of_report_query_count"
            ),
            "experience_metric_unit": "studies",
            "author_count_with_nonmissing_metric": 2,
            "median_author_value": 8.0,
        },
        {
            "author_adoption_group": "ALL_AUTHORS",
            "experience_metric_name": ("distinct_login_days_as_of_report_query_count"),
            "experience_metric_unit": "days",
            "author_count_with_nonmissing_metric": 4,
            "median_author_value": 30.0,
        },
        {
            "author_adoption_group": "AI_ONLY",
            "experience_metric_name": ("distinct_login_days_as_of_report_query_count"),
            "experience_metric_unit": "days",
            "author_count_with_nonmissing_metric": 2,
            "median_author_value": 20.0,
        },
    ]

    return pd.DataFrame.from_records(rows)


def grouped_study_rows() -> pd.DataFrame:
    """Return aggregate-only completed-study category rows."""
    rows: list[dict[str, object]] = [
        {
            "study_population_name": "COMPLETED_STUDIES",
            "final_completion_authoring_mode": "ALL",
            "grouping_dimension_1_name": "STUDY_PARTICIPANT_TYPE",
            "grouping_dimension_1_value": "HEALTHY",
            "grouping_dimension_2_name": "NONE",
            "group_values_are_mutually_exclusive": True,
            "distinct_study_count": 4,
            "population_distinct_study_count": 7,
            "distinct_study_percentage_within_population": 100.0 * 4.0 / 7.0,
        },
        {
            "study_population_name": "COMPLETED_STUDIES",
            "final_completion_authoring_mode": "ALL",
            "grouping_dimension_1_name": "STUDY_PARTICIPANT_TYPE",
            "grouping_dimension_1_value": "Other",
            "grouping_dimension_2_name": "NONE",
            "group_values_are_mutually_exclusive": True,
            "distinct_study_count": 3,
            "population_distinct_study_count": 7,
            "distinct_study_percentage_within_population": 100.0 * 3.0 / 7.0,
        },
        {
            "study_population_name": "COMPLETED_STUDIES",
            "final_completion_authoring_mode": "ALL",
            "grouping_dimension_1_name": "STUDY_DEPARTMENT",
            "grouping_dimension_1_value": "Synthetic Department",
            "grouping_dimension_2_name": "NONE",
            "group_values_are_mutually_exclusive": True,
            "distinct_study_count": 7,
            "population_distinct_study_count": 7,
            "distinct_study_percentage_within_population": 100.0,
        },
    ]

    return pd.DataFrame.from_records(rows)


def field_adoption_rows() -> pd.DataFrame:
    """Return aggregate-only field-adoption rows."""
    return pd.DataFrame.from_records(
        [
            {
                "field_name": "title",
                "analysis_type": "TEXT",
                "completed_ai_attempt_count": 4,
                "completed_ai_attempt_count_with_suggestion_offered": 4,
                "completed_ai_attempt_count_with_suggestion_selected": 3,
                "completed_ai_attempt_count_selected_and_exactly_retained": 1,
                "completed_ai_attempt_count_selected_and_cosmetically_changed": 0,
                "completed_ai_attempt_count_selected_and_lightly_edited": 1,
                "completed_ai_attempt_count_selected_and_moderately_edited": 0,
                "completed_ai_attempt_count_selected_and_heavily_edited": 0,
                "completed_ai_attempt_count_selected_and_unclassified_edit": 1,
                "completed_ai_attempt_count_selected_and_replaced": 0,
                "completed_ai_attempt_count_selected_then_cleared": 0,
                "completed_ai_attempt_count_unassisted": 1,
                "suggestion_selection_percentage_among_attempts_with_offer": 75.0,
            }
        ]
    )


def suggestion_selection_rows() -> pd.DataFrame:
    """Return aggregate-only suggestion-selection rows."""
    return pd.DataFrame.from_records(
        [
            {
                "field_name": "title",
                "suggestion_kind": "title",
                "suggestion_index": 0,
                "offered_suggestion_count": 8,
                "selected_suggestion_count": 3,
                "unselected_suggestion_count": 5,
                "completed_ai_attempt_count_with_at_least_one_suggestion": 4,
                "completed_ai_attempt_count_with_selected_suggestion": 3,
                "suggestion_level_selection_percentage": 37.5,
                "attempt_level_selection_percentage": 75.0,
                "suggestion_count_at_index": 4,
                "selected_suggestion_count_at_index": 3,
                "selection_percentage_at_index": 75.0,
            }
        ]
    )


def readability_change_rows() -> pd.DataFrame:
    """Return aggregate-only readability-change rows."""
    return pd.DataFrame.from_records(
        [
            {
                "field_name": "title",
                "readability_measure_name": "flesch_kincaid_grade",
                "paired_selected_final_attempt_count": 3,
                "attempt_count_value_decreased": 1,
                "attempt_count_no_material_change": 1,
                "attempt_count_value_increased": 1,
                "percentage_value_decreased": 100.0 / 3.0,
                "percentage_no_material_change": 100.0 / 3.0,
                "percentage_value_increased": 100.0 / 3.0,
                "unchanged_absolute_tolerance": 0.1,
                "short_text_readability_caution": True,
            }
        ]
    )


def readability_target_rows() -> pd.DataFrame:
    """Return aggregate-only final grade-band rows."""
    return pd.DataFrame.from_records(
        [
            {
                "attempt_authoring_mode": "AI",
                "field_name": "title",
                "readability_measure_name": "flesch_kincaid_grade",
                "final_text_attempt_count": 4,
                "attempt_count_at_or_below_grade_6": 1,
                "attempt_count_above_grade_6_through_grade_8": 1,
                "attempt_count_above_grade_8_through_grade_10": 1,
                "attempt_count_above_grade_10": 1,
                "percentage_at_or_below_grade_8": 50.0,
                "short_text_readability_caution": True,
                "target_interpretation_note": (
                    "Grade-level formulas are indicators only."
                ),
            }
        ]
    )


def selected_comparison_rows() -> pd.DataFrame:
    """Return aggregate-only selected-comparison rows."""
    return pd.DataFrame.from_records(
        [
            {
                "field_name": "title",
                "readability_measure_name": "flesch_kincaid_grade",
                (
                    "completed_ai_attempt_count_with_selected_and_"
                    "unselected_suggestions"
                ): 3,
                "median_selected_minus_mean_unselected_value": -0.5,
                "attempt_count_selected_value_lower": 2,
                "attempt_count_selected_value_equal_within_tolerance": 0,
                "attempt_count_selected_value_higher": 1,
                "equality_tolerance": 0.1,
            }
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


def content_rows() -> pd.DataFrame:
    """Return aggregate-only content-source rows."""
    return pd.DataFrame.from_records(
        [
            {
                "attempt_completion_group": "ALL",
                "reported_study_content_source": "registry",
                "inferred_study_content_source": "registry",
                "ai_attempt_count": 4,
            }
        ]
    )


def completed_study_author_context_rows() -> pd.DataFrame:
    """Return synthetic completed-study completion-author context rows."""
    return pd.DataFrame.from_records(
        [
            {
                "context_dimension_name": "EFFECTIVE_ROLE",
                "context_dimension_value": "COORDINATOR",
                "final_completion_authoring_mode": "AI",
                "completed_study_count": 6,
                "mode_completed_study_count": 6,
                "all_completed_study_count": 10,
                "completed_study_percentage_within_mode": 100.0,
                "completed_study_percentage_overall": 60.0,
                "distinct_completion_author_count": 4,
            },
            {
                "context_dimension_name": "EFFECTIVE_ROLE",
                "context_dimension_value": "PI",
                "final_completion_authoring_mode": "MANUAL",
                "completed_study_count": 4,
                "mode_completed_study_count": 4,
                "all_completed_study_count": 10,
                "completed_study_percentage_within_mode": 100.0,
                "completed_study_percentage_overall": 40.0,
                "distinct_completion_author_count": 3,
            },
            {
                "context_dimension_name": "PI_STATUS",
                "context_dimension_value": "NON_PI",
                "final_completion_authoring_mode": "AI",
                "completed_study_count": 6,
                "mode_completed_study_count": 6,
                "all_completed_study_count": 10,
                "completed_study_percentage_within_mode": 100.0,
                "completed_study_percentage_overall": 60.0,
                "distinct_completion_author_count": 4,
            },
            {
                "context_dimension_name": "PI_STATUS",
                "context_dimension_value": "PI",
                "final_completion_authoring_mode": "MANUAL",
                "completed_study_count": 4,
                "mode_completed_study_count": 4,
                "all_completed_study_count": 10,
                "completed_study_percentage_within_mode": 100.0,
                "completed_study_percentage_overall": 40.0,
                "distinct_completion_author_count": 3,
            },
        ]
    )


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


def charts() -> ExplorationCharts:
    """Return synthetic aggregate-only chart bundle."""
    return build_exploration_charts(
        ExplorationChartInputs(
            grouped_attempt_summary=attempt_rows(),
            study_attempt_history_summary=study_history_rows(),
            author_handoff_summary=author_handoff_rows(),
            attempt_start_experience_summary=(attempt_start_experience_rows()),
            current_author_experience_summary=(current_author_experience_rows()),
            grouped_study_summary=grouped_study_rows(),
            completed_study_author_context_summary=(
                completed_study_author_context_rows()
            ),
            grouped_author_summary=grouped_author_rows(),
            field_adoption_editing_summary=field_adoption_rows(),
            suggestion_selection_summary=suggestion_selection_rows(),
            field_readability_change_summary=readability_change_rows(),
            field_readability_target_summary=readability_target_rows(),
            selected_vs_unselected_readability_summary=(selected_comparison_rows()),
            field_edit_readability_cross_summary=edit_readability_cross_rows(),
            content_source_matrix=content_rows(),
        )
    )


def test_html_report_is_self_contained_and_accessible() -> None:
    html = render_html_report(
        overview_summary=overview_rows(),
        data_quality_summary=quality_rows(),
        charts=charts(),
    )
    normalized_html = " ".join(html.split())

    assert html.startswith("<!doctype html>")
    assert '<html lang="en">' in html
    assert "<h1>Study Posting Audit Exploration</h1>" in html
    assert 'id="executive-overview-heading"' in html
    assert 'id="study-pathways-heading"' in html
    assert "Study pathways and author handoffs" in html
    assert "Completed-study pathways by final authoring mode" in html
    assert "Author handoffs before study completion" in html
    assert "Distinct studies" in html
    assert "10" in html
    assert "plotly.js" in html.lower()
    assert 'src="https://cdn.plot.ly' not in html
    assert "These descriptive results do not" in normalized_html
    assert "establish causality and must not be" in normalized_html
    assert "Readability formulas are indicators only" in normalized_html

    assert 'id="author-experience-heading"' in html
    assert "Author experience and activity" in html
    assert "Median studies created before attempt start" in html
    assert "Median author experience at report query time: studies" in html
    assert "Median author experience at report query time: days" in html
    assert "These charts describe attempt authors" in normalized_html
    assert "The first chart uses an author-attempt grain" in normalized_html
    assert "The next two charts use a unique-author grain" in normalized_html
    assert (
        "Counts may differ because the attempt-start chart counts "
        "author-attempt observations"
    ) in normalized_html
    assert "missing values can further reduce either count" in normalized_html
    assert "not historical snapshots of individual attempts" in normalized_html

    assert 'id="study-mix-heading"' in html
    assert "Participant and department mix" in html
    assert "Completed studies by participant type" in html
    assert "Completed studies by department" in html
    assert "Other and missing categories are retained" in normalized_html

    assert 'id="field-adoption-heading"' in html
    assert "AI field adoption and editing" in html
    assert "AI suggestion offers and selections by field" in html
    assert "Selected AI suggestion outcomes by field" in html
    assert "Field populations and denominators can differ" in normalized_html
    assert "Edited-unclassified is kept separate from replaced" in normalized_html
    assert "do not establish writing quality" in normalized_html


def test_html_report_explains_appointment_context() -> None:
    """Explain parsed appointment facets and overlapping groups."""
    html = render_html_report(
        overview_summary=overview_rows(),
        data_quality_summary=quality_rows(),
        charts=charts(),
    )
    normalized_html = " ".join(html.split())

    assert 'id="author-context-heading"' in html
    assert "Author and principal-investigator appointment context" in html
    assert "Distinct authors by effective role" not in html
    assert "Authors classified as study principal investigators" not in html
    assert "Author appointment schools" in html
    assert "Principal-investigator appointment schools" in html
    assert "Author appointment departments" in html
    assert "Principal-investigator appointment departments" in html
    assert "Author appointment titles" in html
    assert "Principal-investigator appointment titles" in html
    assert "Title:Department:School" in normalized_html
    assert "not intended to sum to 100 percent" in normalized_html
    assert "counts distinct attempt authors represented" in normalized_html


def test_html_report_explains_completed_study_author_context() -> None:
    """Explain the completed-study grain and study-specific author context."""
    html = render_html_report(
        overview_summary=overview_rows(),
        data_quality_summary=quality_rows(),
        charts=charts(),
    )
    normalized_html = " ".join(html.split())

    assert 'id="completed-study-author-context-heading"' in html
    assert "Completed studies by authoring mode and completion-author context" in html
    assert "Completed studies by authoring mode and completion-author role" in html
    assert "Completed studies by authoring mode and completion-author PI status" in html
    assert "Each completed study contributes exactly once" in normalized_html
    assert "specific to that study" in normalized_html
    assert (
        "Chart values measure completed studies, not distinct people" in normalized_html
    )
    assert "same person can complete several studies" in normalized_html
    assert "different roles" in normalized_html
    assert "non-principal investigator for another" in normalized_html
    assert (
        "Distinct completion authors appear only as aggregate hover context"
        in normalized_html
    )


def test_html_report_explains_workflow_timing() -> None:
    """Verify attempt-level and study-level timing interpretation."""
    html = render_html_report(
        overview_summary=overview_rows(),
        data_quality_summary=quality_rows(),
        charts=charts(),
    )
    normalized_html = " ".join(html.split())

    assert 'id="attempts-heading"' in html
    assert "Attempts and workflow timing" in html
    assert "Attempt timing distributions by authoring mode" in html
    assert "Time from first attempt to study completion" not in html
    assert "25th through 75th percentiles" in normalized_html
    assert "observed minimum through maximum" not in normalized_html
    assert "do not establish author effort, efficiency" in normalized_html


def test_html_report_explains_suggestion_choice_denominators() -> None:
    html = render_html_report(
        overview_summary=overview_rows(),
        data_quality_summary=quality_rows(),
        charts=charts(),
    )
    normalized_html = " ".join(html.split())

    assert 'id="suggestion-choice-heading"' in html
    assert "Suggestion choice" in html
    assert "Suggestion selection by field and kind" in html
    assert "Selection by zero-based suggestion index" in html
    assert "Attempt-level selection is the percentage" in normalized_html
    assert "Suggestion-level selection is the percentage" in normalized_html
    assert "index 0 is the first offered suggestion" in normalized_html
    assert "does not establish that a suggestion was better" in normalized_html


def test_html_report_explains_readability_indicators() -> None:
    html = render_html_report(
        overview_summary=overview_rows(),
        data_quality_summary=quality_rows(),
        charts=charts(),
    )
    normalized_html = " ".join(html.split())

    assert 'id="readability-heading"' in html
    assert "Readability indicators" in html
    assert "Selected-to-final Flesch-Kincaid direction by field" in html
    assert "Observed final Flesch-Kincaid grade bands" in html
    assert "Selected versus mean-unselected Flesch-Kincaid difference" in html
    assert "Selected versus unselected suggestions" in html
    assert "exactly one selected suggestion" in normalized_html
    assert "at least one unselected suggestion" in normalized_html
    assert "usable readability values for both" in normalized_html
    assert "An omitted field means no observations met" in normalized_html
    assert "does not mean the field was absent from the audit" in normalized_html
    assert "comparable-attempt count in hover text" in normalized_html
    assert "final minus selected" in normalized_html
    assert (
        "Lower or higher formula values are not automatically better" in normalized_html
    )
    assert "Titles are short text" in normalized_html
    assert "Sample counts and tolerances appear in hover text" in normalized_html

    assert "Edit intensity and consensus grade-level direction" in html
    assert "How edit size is classified" in html
    assert "How readability direction is classified" in html
    assert "How to read a bar" in html
    assert "Worked example" in html
    assert "character edit ratio at or below 10%" in normalized_html
    assert "ratio above 10% and at or below 30%" in normalized_html
    assert "ratio above 30%" in normalized_html
    assert "EXPLORATORY_CHARACTER_RATIO_10_30" in html
    assert "Mixed direction is not the same as no material change" in (normalized_html)
    assert "unfilled remainder represents fields without a usable pair" in (
        normalized_html
    )
    assert "Lower is not automatically better" in normalized_html


def test_html_report_excludes_identifier_and_payload_values() -> None:
    html = render_html_report(
        overview_summary=overview_rows(),
        data_quality_summary=quality_rows(),
        charts=charts(),
    )

    forbidden_values = (
        "synthetic-author@example.edu",
        "SYNTHETIC-STUDY-1",
        "selected_text",
        "final_text",
        "LLM_SUGGESTIONS",
        "FINAL_SUBMISSION",
    )

    for value in forbidden_values:
        assert value not in html


def test_write_html_report_creates_utf8_file(
    tmp_path: Path,
) -> None:
    path = tmp_path / "report.html"

    write_html_report(
        path,
        overview_summary=overview_rows(),
        data_quality_summary=quality_rows(),
        charts=charts(),
    )

    assert path.is_file()
    assert path.read_text(encoding="utf-8").startswith("<!doctype html>")


def test_write_html_report_wraps_io_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "report.html"

    def fail_write(
        _self: Path,
        *_args: object,
        **_kwargs: object,
    ) -> int:
        raise OSError("synthetic write failure")

    monkeypatch.setattr(Path, "write_text", fail_write)

    with pytest.raises(
        ExplorationInputError,
        match="Could not write exploration HTML report",
    ):
        write_html_report(
            path,
            overview_summary=overview_rows(),
            data_quality_summary=quality_rows(),
            charts=charts(),
        )


def test_html_report_displays_aggregate_data_quality() -> None:
    """Display fatal-pass guarantees and nonzero warning context."""
    html = render_html_report(
        overview_summary=overview_rows(),
        data_quality_summary=quality_rows(),
        charts=charts(),
    )
    normalized_html = " ".join(html.split())

    assert 'id="data-quality-heading"' in html
    assert "Data quality" in html
    assert "Fatal validation checks passed" in normalized_html
    assert "13 of 13" in normalized_html
    assert "Warning categories detected" in normalized_html
    assert "1 of 3" in normalized_html
    assert "Warning occurrences" in normalized_html
    assert "Malformed Appointment" in normalized_html
    assert "Affected attempts: 2 of 10 (20.0%)" in normalized_html
    assert "Affected studies: 2" in normalized_html
    assert "Affected authors: 2" in normalized_html
    assert "Malformed entries are excluded from appointment groups." in (
        normalized_html
    )
    assert "No attempts occurred after completion." in normalized_html
    assert "No studies had varying CREATED_BY_ID values." in normalized_html
    assert "quality/data_quality_summary.csv" in normalized_html
    assert "not a distinct-attempt count" in normalized_html
    assert "do not establish a cause" in normalized_html


def test_html_report_displays_no_warning_state() -> None:
    """Clearly state when no warning check affected attempts."""
    html = render_html_report(
        overview_summary=overview_rows(),
        data_quality_summary=quality_rows(malformed_appointment_count=0),
        charts=charts(),
    )
    normalized_html = " ".join(html.split())

    assert "Warning categories detected" in normalized_html
    assert "0 of 3" in normalized_html
    assert "No warning checks affected attempts in this run." in normalized_html
    assert "No malformed appointment entries affected attempts." in normalized_html


def test_html_report_requires_quality_columns() -> None:
    """Reject an incomplete aggregate quality input."""
    with pytest.raises(
        ExplorationValidationError,
        match="lacks required HTML columns",
    ):
        render_html_report(
            overview_summary=overview_rows(),
            data_quality_summary=pd.DataFrame(
                {
                    "severity_level": ["WARNING"],
                }
            ),
            charts=charts(),
        )
