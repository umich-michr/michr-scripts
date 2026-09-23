from collections.abc import Callable
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
    specs = (
        ("all_attempt_count", "All attempts", 12, 12),
        (
            "distinct_study_count_with_any_attempt",
            "Distinct studies",
            10,
            10,
        ),
        ("distinct_completed_study_count", "Completed studies", 8, 10),
        (
            "distinct_author_count_with_any_attempt",
            "Distinct attempt authors",
            6,
            6,
        ),
        (
            "distinct_completed_study_count_final_mode_ai",
            "Completed studies authored with AI",
            4,
            8,
        ),
        (
            "distinct_completed_study_count_final_mode_manual",
            "Completed studies authored manually",
            4,
            8,
        ),
        ("complete_attempt_count", "Completed attempts", 8, 12),
        ("incomplete_attempt_count", "Incomplete attempts", 4, 12),
        ("completed_ai_attempt_count", "Completed AI attempts", 4, 8),
        ("completed_manual_attempt_count", "Completed manual attempts", 4, 8),
        ("incomplete_ai_attempt_count", "Incomplete AI attempts", 1, 4),
        ("incomplete_manual_attempt_count", "Incomplete manual attempts", 3, 4),
        (
            "distinct_completed_study_count_with_preceding_incomplete_attempts",
            "Completed studies with preceding incomplete attempts",
            3,
            8,
        ),
        (
            "distinct_completed_study_count_with_preceding_ai_error_attempts",
            "Completed studies with preceding AI errors",
            1,
            8,
        ),
    )

    return pd.DataFrame.from_records(
        [
            {
                "overview_metric_name": metric_name,
                "overview_metric_label": label,
                "metric_count": count,
                "metric_denominator_count": denominator,
                "metric_percentage": (
                    100.0 * count / denominator if denominator else None
                ),
                "metric_denominator_definition": "Synthetic aggregate denominator.",
            }
            for metric_name, label, count, denominator in specs
        ]
    )


def feedback_records() -> pd.DataFrame:
    """Return synthetic source records for authorized feedback rendering."""
    return pd.DataFrame.from_records(
        [
            {
                "ID": 30,
                "USER_FEEDBACK_COMMENTS": (
                    "Synthetic feedback with <tags> & special characters."
                ),
                "AUTHOR_USER_NAME": "forbidden-author@example.edu",
                "STUDY_NUM": "FORBIDDEN-STUDY",
                "LLM_SUGGESTIONS": "FORBIDDEN-SUGGESTION-PAYLOAD",
                "FINAL_SUBMISSION": "FORBIDDEN-FINAL-PAYLOAD",
            },
            {
                "ID": 10,
                "USER_FEEDBACK_COMMENTS": "Synthetic feedback shown first.",
                "AUTHOR_USER_NAME": "another-forbidden-author@example.edu",
                "STUDY_NUM": "ANOTHER-FORBIDDEN-STUDY",
                "LLM_SUGGESTIONS": "ANOTHER-FORBIDDEN-SUGGESTION",
                "FINAL_SUBMISSION": "ANOTHER-FORBIDDEN-FINAL",
            },
            {
                "ID": 20,
                "USER_FEEDBACK_COMMENTS": "   ",
                "AUTHOR_USER_NAME": "blank-feedback-author@example.edu",
                "STUDY_NUM": "BLANK-FEEDBACK-STUDY",
                "LLM_SUGGESTIONS": "BLANK-FEEDBACK-SUGGESTION",
                "FINAL_SUBMISSION": "BLANK-FEEDBACK-FINAL",
            },
            {
                "ID": 40,
                "USER_FEEDBACK_COMMENTS": pd.NA,
                "AUTHOR_USER_NAME": "missing-feedback-author@example.edu",
                "STUDY_NUM": "MISSING-FEEDBACK-STUDY",
                "LLM_SUGGESTIONS": "MISSING-FEEDBACK-SUGGESTION",
                "FINAL_SUBMISSION": "MISSING-FEEDBACK-FINAL",
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
    """Return aggregate-only completed-attempt timing rows."""
    return pd.DataFrame.from_records(
        [
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
                "attempt_completion_group": "COMPLETE",
                "attempt_result": "ALL",
                "attempt_authoring_mode": "AI",
                "grouping_dimension_1_name": "COMPLETION_GROUP",
                "grouping_dimension_2_name": "AUTHORING_MODE",
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


def content_rows() -> pd.DataFrame:
    """Return aggregate-only content-source rows."""
    return pd.DataFrame.from_records(
        [
            {
                "attempt_completion_group": "ALL",
                "reported_study_content_source": "registry",
                "inferred_study_content_source": "registry",
                "ai_attempt_count": 4,
                "reported_source_attempt_count": 4,
                "attempt_percentage_within_reported_source": 100.0,
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


def retry_card_rows() -> pd.DataFrame:
    """Return four identifier-free retry card aggregates."""
    return pd.DataFrame.from_records(
        [
            {
                "retry_card_group": group,
                "study_count": count,
                "population_study_count": 10,
                "study_percentage": 10.0 * count,
                "median_attempt_count": median_attempts,
                "ai_only_study_count": ai_only,
                "manual_only_study_count": manual_only,
                "both_modes_study_count": both,
            }
            for group, count, median_attempts, ai_only, manual_only, both in (
                ("SINGLE_ATTEMPT_COMPLETED", 5, 1.0, 3, 2, 0),
                ("MULTIPLE_ATTEMPTS_COMPLETED", 3, 3.0, 1, 0, 2),
                (
                    "SINGLE_ATTEMPT_NO_COMPLETION_OBSERVED",
                    1,
                    1.0,
                    1,
                    0,
                    0,
                ),
                (
                    "MULTIPLE_ATTEMPTS_NO_COMPLETION_OBSERVED",
                    1,
                    2.0,
                    0,
                    1,
                    0,
                ),
            )
        ]
    )


def study_retry_pathway_rows() -> pd.DataFrame:
    """Return stable aggregate-only retry pathway rows."""
    categories = (
        ("SINGLE_ATTEMPT_AI_COMPLETION", "COMPLETED", "AI", 3, 1.0),
        ("SINGLE_ATTEMPT_MANUAL_COMPLETION", "COMPLETED", "MANUAL", 2, 1.0),
        ("REPEATED_AI_ONLY_TO_AI_COMPLETION", "COMPLETED", "AI", 1, 3.0),
        ("REPEATED_MANUAL_ONLY_TO_MANUAL_COMPLETION", "COMPLETED", "MANUAL", 0, None),
        ("AI_TO_MANUAL_COMPLETION", "COMPLETED", "MANUAL", 1, 2.0),
        ("MANUAL_TO_AI_COMPLETION", "COMPLETED", "AI", 0, None),
        ("MIXED_OR_ALTERNATING_TO_AI_COMPLETION", "COMPLETED", "AI", 1, 4.0),
        ("MIXED_OR_ALTERNATING_TO_MANUAL_COMPLETION", "COMPLETED", "MANUAL", 0, None),
        (
            "SINGLE_ATTEMPT_AI_NO_COMPLETION_OBSERVED",
            "NO_COMPLETION_OBSERVED",
            "AI",
            1,
            1.0,
        ),
        (
            "SINGLE_ATTEMPT_MANUAL_NO_COMPLETION_OBSERVED",
            "NO_COMPLETION_OBSERVED",
            "MANUAL",
            0,
            None,
        ),
        (
            "REPEATED_AI_ONLY_NO_COMPLETION_OBSERVED",
            "NO_COMPLETION_OBSERVED",
            "AI",
            0,
            None,
        ),
        (
            "REPEATED_MANUAL_ONLY_NO_COMPLETION_OBSERVED",
            "NO_COMPLETION_OBSERVED",
            "MANUAL",
            1,
            2.0,
        ),
        (
            "MIXED_MODES_NO_COMPLETION_OBSERVED",
            "NO_COMPLETION_OBSERVED",
            "MIXED",
            0,
            None,
        ),
    )
    rows = []

    for sequence, (category, state, mode, count, median_attempts) in enumerate(
        categories,
        start=1,
    ):
        rows.append(
            {
                "pathway_category": category,
                "pathway_sequence": sequence,
                "completion_state": state,
                "final_or_latest_mode": mode,
                "study_count": count,
                "population_study_count": 10,
                "study_percentage": 10.0 * count,
                "median_attempt_count": median_attempts,
                "percentile_75_attempt_count": median_attempts,
                "study_count_with_mode_change": int(
                    count > 0 and ("TO_" in category or "MIXED" in category)
                ),
                "study_count_with_author_change": int(count > 0 and sequence == 5),
                "study_count_with_ai_error": 0,
                "study_count_with_user_dropped_attempt": 0,
                "study_count_with_returned_result_ai": count if "AI" in category else 0,
                "source_comparison_eligible_study_count": 0,
                "study_count_with_source_size_change": 0,
                "study_count_with_reported_source_change": 0,
                "study_count_with_input_method_change": 0,
                "study_count_with_source_signature_change": 0,
                "ai_exposed_study_count": count if "AI" in category else 0,
                "study_count_with_feedback_recorded": 0,
                "study_count_with_completed_timing": count
                if state == "COMPLETED"
                else 0,
                "median_minutes_first_to_completion": 20.0
                if state == "COMPLETED" and count
                else None,
                "study_count_with_unresolved_observed_span": count
                if state == "NO_COMPLETION_OBSERVED"
                else 0,
                "median_minutes_first_to_last_observed_attempt": 45.0
                if state == "NO_COMPLETION_OBSERVED" and count
                else None,
                "study_count_with_report_run_cutoff": count
                if state == "NO_COMPLETION_OBSERVED"
                else 0,
                "median_minutes_latest_attempt_to_report_run_cutoff": 1_440.0
                if state == "NO_COMPLETION_OBSERVED" and count
                else None,
                "median_minutes_first_attempt_to_report_run_cutoff": 1_485.0
                if state == "NO_COMPLETION_OBSERVED" and count
                else None,
                "timing_definition": "Synthetic timing definition.",
                "interpretation_note": "Synthetic descriptive caution.",
            }
        )

    return pd.DataFrame.from_records(rows)


def retry_characteristic_rows() -> pd.DataFrame:
    """Return aggregate-only retry characteristic rows."""
    return pd.DataFrame.from_records(
        [
            {
                "study_outcome_group": group,
                "study_count": count,
                "median_attempt_count": median_attempts,
                "multiple_attempt_study_count": 1,
                "percentage_with_multiple_attempts": 25.0,
                "both_modes_study_count": 1,
                "percentage_with_both_modes": 25.0,
                "author_change_study_count": 1,
                "percentage_with_author_change": 25.0,
                "ai_error_study_count": 1,
                "percentage_with_ai_error": 25.0,
                "user_dropped_study_count": 1,
                "percentage_with_user_dropped_attempt": 25.0,
                "returned_result_ai_study_count": count if ai_exposed else 0,
                "percentage_with_returned_result_ai": 100.0 if ai_exposed else 0.0,
                "source_comparison_eligible_study_count": 1 if ai_exposed else 0,
                "source_signature_change_study_count": 1 if ai_exposed else 0,
                "percentage_with_source_signature_change_among_eligible": 100.0
                if ai_exposed
                else None,
                "ai_exposed_study_count": count if ai_exposed else 0,
                "feedback_recorded_study_count": 1 if ai_exposed else 0,
                "percentage_with_feedback_recorded_among_ai_exposed": 25.0
                if ai_exposed
                else None,
                "study_count_with_completed_timing": count
                if group != "NO_COMPLETION_OBSERVED"
                else 0,
                "median_minutes_first_to_completion": 30.0
                if group != "NO_COMPLETION_OBSERVED"
                else None,
                "study_count_with_unresolved_observed_span": count
                if group == "NO_COMPLETION_OBSERVED"
                else 0,
                "median_minutes_first_to_last_observed_attempt": 45.0
                if group == "NO_COMPLETION_OBSERVED"
                else None,
                "study_count_with_report_run_cutoff": count
                if group == "NO_COMPLETION_OBSERVED"
                else 0,
                "median_minutes_latest_attempt_to_report_run_cutoff": 1_440.0
                if group == "NO_COMPLETION_OBSERVED"
                else None,
                "median_minutes_first_attempt_to_report_run_cutoff": 1_485.0
                if group == "NO_COMPLETION_OBSERVED"
                else None,
                "timing_definition": "Synthetic timing definition.",
                "interpretation_note": "Synthetic descriptive caution.",
            }
            for group, count, median_attempts, ai_exposed in (
                ("COMPLETED_AI", 4, 2.0, True),
                ("COMPLETED_MANUAL", 4, 1.5, True),
                ("NO_COMPLETION_OBSERVED", 2, 1.5, False),
            )
        ]
    )


def charts() -> ExplorationCharts:
    """Return synthetic aggregate-only chart bundle."""
    return build_exploration_charts(
        ExplorationChartInputs(
            overview_summary=overview_rows(),
            grouped_attempt_summary=attempt_rows(),
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
            suggestion_selection_summary=suggestion_selection_rows(),
            field_readability_change_summary=readability_change_rows(),
            field_readability_target_summary=readability_target_rows(),
            selected_vs_unselected_readability_summary=(selected_comparison_rows()),
            field_edit_readability_cross_summary=edit_readability_cross_rows(),
            content_source_matrix=content_rows(),
            source_context_distribution_summary=(source_context_distribution_rows()),
            source_size_latency_summary=source_size_latency_rows(),
            repeated_attempt_source_consistency_summary=(repeated_source_rows()),
        )
    )


def test_html_report_is_self_contained_and_accessible() -> None:
    html = render_html_report(
        records=feedback_records(),
        overview_summary=overview_rows(),
        author_handoff_summary=author_handoff_rows(),
        retry_card_summary=retry_card_rows(),
        retry_characteristics_summary=retry_characteristic_rows(),
        data_quality_summary=quality_rows(),
        repeated_attempt_source_consistency_summary=(repeated_source_rows()),
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
    assert 'id="interpretation-heading"' not in html
    assert "Interpretation and privacy" not in html

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


def test_html_report_explains_source_context_and_latency() -> None:
    """Explain both populations and dynamic completed-path context."""
    rendered = render_html_report(
        records=feedback_records(),
        overview_summary=overview_rows(),
        author_handoff_summary=author_handoff_rows(),
        retry_card_summary=retry_card_rows(),
        retry_characteristics_summary=retry_characteristic_rows(),
        data_quality_summary=quality_rows(),
        repeated_attempt_source_consistency_summary=(repeated_source_rows()),
        charts=charts(),
    )
    normalized = " ".join(rendered.split())

    assert "Source context, repeated attempts, and latency" in rendered
    assert "All AI generations that returned a result" in rendered
    assert "Completed AI-assisted attempts" in rendered
    assert "Input method for AI generations that returned a result" in rendered
    assert (
        "Latency by source-size band for AI generations "
        "that returned a result" in rendered
    )
    assert "Input method for completed AI-assisted attempts" in rendered
    assert "Latency by source-size band for completed AI-assisted attempts" in rendered
    assert "AI generation that returned a result" in rendered
    assert "It does not mean that the study posting was created." in normalized
    assert (
        "Each completed study contributes its unique completed "
        "AI-assisted attempt once." in normalized
    )
    assert "How to read input method and latency" in rendered
    assert "This counts generations, not necessarily 50 different studies" in (
        normalized
    )
    assert "Bar height is median generation latency in seconds" in normalized
    assert "error line spans the 25th to 75th percentile" in normalized
    assert "a 6-second bar with an error line from 4 to 9 seconds" in normalized
    assert "different populations" in normalized
    assert "How to read the reported-versus-inferred heatmap" in rendered
    assert "vertical axis" in normalized
    assert "horizontal axis" in normalized
    assert "cell contains 18" in normalized
    assert "5 were reported as A and inferred as B" in normalized
    assert "Diagonal cells show matching normalized labels" in normalized
    assert "Neither pattern proves which label is correct" in normalized

    for panel_title in (
        "How to read input method and latency",
        "How to read the reported-versus-inferred heatmap",
    ):
        summary = rendered.index(f"<summary>{panel_title}</summary>")
        panel_start = rendered.rfind(
            '<details class="explanation-panel">',
            0,
            summary,
        )
        panel_end = rendered.index("</details>", summary)
        panel = rendered[panel_start:panel_end]
        assert '<details class="explanation-panel" open' not in panel

    assert "<strong>7</strong>" in rendered
    assert "<strong>3</strong>" in rendered
    assert "consecutive-generation transitions from" in normalized
    assert "completed AI studies are represented." in normalized
    assert "5 comparable and 2 unavailable" in normalized
    assert (
        "Captured source changes between AI generations before completion" in rendered
    )
    assert "generation 1 to generation 2" in normalized
    assert "4,200 source characters" in normalized
    assert "captured latency increased by 1.5 seconds" in normalized
    assert "unchanged-source proxy" in normalized
    assert "not proof that source text was identical" in normalized
    assert (
        "Positive latency change means the later generation took longer" in normalized
    )
    assert "successful AI generation" not in rendered.casefold()


def test_html_report_explains_author_handoff_categories() -> None:
    """Provide a collapsed, accessible explanation beside the handoff chart."""
    html = render_html_report(
        records=feedback_records(),
        overview_summary=overview_rows(),
        author_handoff_summary=author_handoff_rows(),
        retry_card_summary=retry_card_rows(),
        retry_characteristics_summary=retry_characteristic_rows(),
        data_quality_summary=quality_rows(),
        repeated_attempt_source_consistency_summary=(repeated_source_rows()),
        charts=charts(),
    )
    normalized = " ".join(html.split())

    panel_summary = html.index(
        "<summary>How to read the author-handoff categories</summary>"
    )
    panel_start = html.rfind(
        '<details class="explanation-panel">',
        0,
        panel_summary,
    )
    panel_end = html.index("</details>", panel_summary)
    panel = html[panel_start:panel_end]

    assert "<details" in panel
    assert '<details class="explanation-panel" open' not in panel
    assert "How to read the author-handoff categories" in panel
    assert "completion author" in panel
    assert "No preceding attempt" in panel
    assert "All preceding attempts by completion author" in panel
    assert "All preceding attempts by other authors" in panel
    assert "Mixed completion and other authors" in panel
    assert "Suppose Alex made the completed attempt" in normalized
    assert "Each completed study appears in exactly one category." in normalized
    assert "Each full bar is all completed studies" in normalized
    assert "Segment heights are completed-study counts" in normalized
    assert "if an AI bar contains 20 completed studies" in normalized
    assert "does not show why responsibility changed" in normalized
    assert "do not explain why an author changed" in normalized
    assert (
        html.index("Completed-study pathways by final authoring mode")
        < panel_start
        < html.index(
            "Author handoffs before study completion",
            panel_end,
        )
    )
    assert "details.explanation-panel:not([open])" in html
    assert "display: block" in html


def test_html_report_explains_author_experience_and_study_mix() -> None:
    """Explain author time points and completed-study category bars."""
    html = render_html_report(
        records=feedback_records(),
        overview_summary=overview_rows(),
        author_handoff_summary=author_handoff_rows(),
        retry_card_summary=retry_card_rows(),
        retry_characteristics_summary=retry_characteristic_rows(),
        data_quality_summary=quality_rows(),
        repeated_attempt_source_consistency_summary=(repeated_source_rows()),
        charts=charts(),
    )
    normalized_html = " ".join(html.split())

    assert "How to compare attempt-time and query-time experience" in html
    assert "five AI attempts have prior-study counts" in normalized_html
    assert "the AI bar is 2 studies" in normalized_html
    assert "an author with three attempts contributes three observations" in (
        normalized_html
    )
    assert "the median author in that group had 6 distinct calendar days" in (
        normalized_html
    )
    assert "different observation units and time points" in normalized_html

    experience_summary = html.index(
        "<summary>How to compare attempt-time and query-time experience</summary>"
    )
    experience_panel_start = html.rfind(
        '<details class="explanation-panel">',
        0,
        experience_summary,
    )
    experience_panel_end = html.index("</details>", experience_summary)
    experience_panel = html[experience_panel_start:experience_panel_end]
    assert '<details class="explanation-panel" open' not in experience_panel

    assert "One bar represents one category" in normalized_html
    assert "each completed study contributes once per chart" in normalized_html
    assert "do not compare completion rates between categories" in normalized_html


def test_html_report_explains_appointment_context() -> None:
    """Explain parsed appointment facets and overlapping groups."""
    html = render_html_report(
        records=feedback_records(),
        overview_summary=overview_rows(),
        author_handoff_summary=author_handoff_rows(),
        retry_card_summary=retry_card_rows(),
        retry_characteristics_summary=retry_characteristic_rows(),
        data_quality_summary=quality_rows(),
        repeated_attempt_source_consistency_summary=(repeated_source_rows()),
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
    assert "How to interpret overlapping appointment groups" in html
    assert "count attempt authors according to" in normalized_html
    assert "their studies' named principal investigators" in normalized_html
    assert "among 10 distinct attempt authors" in normalized_html
    assert "the chart does not count 11 different people" in normalized_html
    assert "not greater feature use per person" in normalized_html

    summary = html.index(
        "<summary>How to interpret overlapping appointment groups</summary>"
    )
    panel_start = html.rfind('<details class="explanation-panel">', 0, summary)
    panel_end = html.index("</details>", summary)
    panel = html[panel_start:panel_end]
    assert '<details class="explanation-panel" open' not in panel


def test_html_report_explains_completed_study_author_context() -> None:
    """Explain the completed-study grain and study-specific author context."""
    html = render_html_report(
        records=feedback_records(),
        overview_summary=overview_rows(),
        author_handoff_summary=author_handoff_rows(),
        retry_card_summary=retry_card_rows(),
        retry_characteristics_summary=retry_characteristic_rows(),
        data_quality_summary=quality_rows(),
        repeated_attempt_source_consistency_summary=(repeated_source_rows()),
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
    assert "How to read completion-author context" in html
    assert "Each horizontal bar is one final authoring mode" in normalized_html
    assert "Segment length is a completed-study count" in normalized_html
    assert "if the manual bar contains 15 completed studies" in normalized_html
    assert "not six necessarily different people" in normalized_html
    assert "do not measure effort by other team members" in normalized_html

    summary = html.index("<summary>How to read completion-author context</summary>")
    panel_start = html.rfind('<details class="explanation-panel">', 0, summary)
    panel_end = html.index("</details>", summary)
    panel = html[panel_start:panel_end]
    assert '<details class="explanation-panel" open' not in panel


def test_html_report_has_navigation_and_faculty_summary() -> None:
    html = render_html_report(
        records=feedback_records(),
        overview_summary=overview_rows(),
        author_handoff_summary=author_handoff_rows(),
        retry_card_summary=retry_card_rows(),
        retry_characteristics_summary=retry_characteristic_rows(),
        data_quality_summary=quality_rows(),
        repeated_attempt_source_consistency_summary=(repeated_source_rows()),
        charts=charts(),
    )
    normalized = " ".join(html.split())

    assert '<nav aria-labelledby="report-contents-heading">' in html
    assert 'id="report-contents-heading"' in html
    assert 'id="faculty-summary-heading"' in html
    assert html.index('id="report-contents-heading"') < html.index(
        'id="faculty-summary-heading"'
    )
    assert html.index('id="faculty-summary-heading"') < html.index(
        'id="executive-overview-heading"'
    )
    assert "12 attempts representing 10 studies" in normalized
    assert "8 completed studies (80.0%)" in normalized
    assert "4 used AI as the final authoring mode" in normalized
    assert "4 were authored manually" in normalized
    assert "3 completed studies had" in normalized
    assert "1 of 3 reportable warning categories" in normalized
    assert "2 AI-usefulness feedback responses" in normalized


def test_html_report_toc_targets_unique_sections_in_report_order() -> None:
    html = render_html_report(
        records=feedback_records(),
        overview_summary=overview_rows(),
        author_handoff_summary=author_handoff_rows(),
        retry_card_summary=retry_card_rows(),
        retry_characteristics_summary=retry_characteristic_rows(),
        data_quality_summary=quality_rows(),
        repeated_attempt_source_consistency_summary=(repeated_source_rows()),
        charts=charts(),
    )

    expected_ids = (
        "executive-overview-heading",
        "data-quality-heading",
        "study-pathways-heading",
        "retry-pathways-heading",
        "author-experience-heading",
        "completed-study-author-context-heading",
        "author-context-heading",
        "study-mix-heading",
        "field-adoption-heading",
        "suggestion-choice-heading",
        "readability-heading",
        "content-source-heading",
        "user-feedback-heading",
    )

    href_positions = []
    target_positions = []

    for section_id in expected_ids:
        assert html.count(f'href="#{section_id}"') == 1
        assert html.count(f'id="{section_id}"') == 1
        href_positions.append(html.index(f'href="#{section_id}"'))
        target_positions.append(html.index(f'id="{section_id}"'))

    assert href_positions == sorted(href_positions)
    assert target_positions == sorted(target_positions)


def test_html_report_uses_progressive_disclosure_defaults() -> None:
    html = render_html_report(
        records=feedback_records(),
        overview_summary=overview_rows(),
        author_handoff_summary=author_handoff_rows(),
        retry_card_summary=retry_card_rows(),
        retry_characteristics_summary=retry_characteristic_rows(),
        data_quality_summary=quality_rows(),
        repeated_attempt_source_consistency_summary=(repeated_source_rows()),
        charts=charts(),
    )

    for section_id in (
        "executive-overview-heading",
        "data-quality-heading",
        "study-pathways-heading",
        "user-feedback-heading",
    ):
        assert (
            f'<details class="report-section" open>\n    <summary id="{section_id}"'
        ) in html

    for section_id in (
        "retry-pathways-heading",
        "author-experience-heading",
        "completed-study-author-context-heading",
        "author-context-heading",
        "study-mix-heading",
        "field-adoption-heading",
        "suggestion-choice-heading",
        "readability-heading",
        "content-source-heading",
    ):
        assert (
            f'<details class="report-section">\n    <summary id="{section_id}"'
        ) in html

    assert html.count('<details class="report-section"') == 13
    assert "details.report-section:not([open]) > section" in html
    assert "display: block" in html


def test_html_report_explains_observed_retry_patterns() -> None:
    """Render cards, chart, semantic table, and collapsed interpretation."""
    html = render_html_report(
        records=feedback_records(),
        overview_summary=overview_rows(),
        author_handoff_summary=author_handoff_rows(),
        retry_card_summary=retry_card_rows(),
        retry_characteristics_summary=retry_characteristic_rows(),
        data_quality_summary=quality_rows(),
        repeated_attempt_source_consistency_summary=repeated_source_rows(),
        charts=charts(),
    )
    normalized = " ".join(html.split())

    assert "Retry pathways and observed workflow patterns" in html
    assert "One recorded attempt, completed" in html
    assert "Multiple recorded attempts, no completion observed" in html
    assert "Observed retry pathways" in html
    assert "AI → AI → manual completion" in html
    assert '<table class="retry-table">' in html
    assert 'scope="col"' in html
    assert 'scope="row"' in html
    assert "Source change among eligible" in html
    assert "Feedback among AI-exposed" in html
    assert "First attempt to completion end" in html
    assert "First to latest observed attempt" in html
    assert "Latest attempt to report-run cutoff" in html
    assert "First attempt to report-run cutoff" in html
    assert "1,440 minutes (n=2)" in normalized
    assert "1,485 minutes (n=2)" in normalized
    assert "How to read the retry summary" in html
    assert "Each study appears in exactly one card." in normalized
    assert "12 of 50 studies" in normalized
    assert "A study appears in only one bar" in normalized
    assert "does not mean zero percent" in normalized
    assert "observed activity span is 2 days" in normalized
    assert "follow-up after the latest attempt is 7 days" in normalized
    assert "total observation window is 9 days" in normalized
    assert "How to interpret observed retry patterns" in html
    assert "patterns support targeted qualitative follow-up" in normalized.lower()
    assert "That the study was abandoned" in html

    section_start = html.index('<summary id="retry-pathways-heading">')
    details_start = html.rfind(
        '<details class="report-section">',
        0,
        section_start,
    )
    assert details_start >= 0
    assert (
        '<details class="report-section" open>' not in html[details_start:section_start]
    )

    reading_summary = html.index(
        "<summary>How to read the retry summary</summary>",
        section_start,
    )
    reading_start = html.rfind(
        '<details class="explanation-panel">',
        section_start,
        reading_summary,
    )
    reading_end = html.index("</details>", reading_summary)
    reading_panel = html[reading_start:reading_end]

    interpretation_summary = html.index(
        "<summary>How to interpret observed retry patterns</summary>",
        reading_end,
    )
    interpretation_start = html.rfind(
        '<details class="explanation-panel">',
        reading_end,
        interpretation_summary,
    )
    interpretation_end = html.index("</details>", interpretation_summary)
    interpretation_panel = html[interpretation_start:interpretation_end]

    assert '<details class="explanation-panel" open' not in reading_panel
    assert '<details class="explanation-panel" open' not in interpretation_panel
    assert reading_start < interpretation_start
    assert "details.explanation-panel:not([open])" in html


def test_html_report_loads_plotly_before_first_chart() -> None:
    """Load Plotly before the first overview chart executes."""
    html = render_html_report(
        records=feedback_records(),
        overview_summary=overview_rows(),
        author_handoff_summary=author_handoff_rows(),
        retry_card_summary=retry_card_rows(),
        retry_characteristics_summary=retry_characteristic_rows(),
        data_quality_summary=quality_rows(),
        repeated_attempt_source_consistency_summary=(repeated_source_rows()),
        charts=charts(),
    )

    plotly_library_position = html.lower().find("plotly.js")
    first_chart_position = html.find("How the captured attempts ended")
    study_pathways_position = html.find(
        "Completed-study pathways by final authoring mode"
    )

    assert plotly_library_position != -1
    assert first_chart_position != -1
    assert study_pathways_position != -1
    assert plotly_library_position < first_chart_position
    assert first_chart_position < study_pathways_position
    assert html.lower().count("plotly.js v") == 1


def test_html_report_explains_overview_charts_in_plain_language() -> None:
    """Provide a collapsed worked example for the overview charts."""
    html = render_html_report(
        records=feedback_records(),
        overview_summary=overview_rows(),
        author_handoff_summary=author_handoff_rows(),
        retry_card_summary=retry_card_rows(),
        retry_characteristics_summary=retry_characteristic_rows(),
        data_quality_summary=quality_rows(),
        repeated_attempt_source_consistency_summary=repeated_source_rows(),
        charts=charts(),
    )
    normalized = " ".join(html.split())

    summary = "How to read the overview charts"
    panel_summary = html.index(f"<summary>{summary}</summary>")
    panel_start = html.rfind(
        '<details class="explanation-panel">',
        0,
        panel_summary,
    )
    panel_end = html.index("</details>", panel_summary)
    panel = html[panel_start:panel_end]

    assert panel_start >= 0
    assert '<details class="explanation-panel" open' not in panel
    assert "This chart counts audit attempts, not studies." in normalized
    assert "one study can have several attempts" in normalized
    assert "Each completed study contributes once." in normalized
    assert "5 of 20 completed studies" in normalized
    assert "the middle half of recorded values" in normalized
    assert "a median of 8 minutes" in normalized
    assert "does not show that the mode caused" in normalized
    assert (
        html.index("Completed-attempt timing by authoring mode")
        < panel_start
        < html.index(
            '<summary id="data-quality-heading">',
            panel_end,
        )
    )
    assert "details.explanation-panel:not([open])" in html
    assert "display: block" in html


def test_html_report_explains_workflow_timing() -> None:
    """Verify overview timing interpretation without duplicate rendering."""
    html = render_html_report(
        records=feedback_records(),
        overview_summary=overview_rows(),
        author_handoff_summary=author_handoff_rows(),
        retry_card_summary=retry_card_rows(),
        retry_characteristics_summary=retry_characteristic_rows(),
        data_quality_summary=quality_rows(),
        repeated_attempt_source_consistency_summary=(repeated_source_rows()),
        charts=charts(),
    )
    normalized_html = " ".join(html.split())

    assert 'id="attempts-heading"' not in html
    assert "Attempts and workflow timing" not in html
    assert html.count("Completed-attempt timing by authoring mode") == 1
    assert html.count("How the captured attempts ended") == 1
    assert "Recorded time for completed attempts" in html
    assert "Time from first attempt to study completion" not in html
    assert "25th through 75th percentiles" in normalized_html
    assert "observed minimum through maximum" not in normalized_html
    assert "do not establish author effort, efficiency" in normalized_html


def test_html_report_explains_suggestion_choice_denominators() -> None:
    html = render_html_report(
        records=feedback_records(),
        overview_summary=overview_rows(),
        author_handoff_summary=author_handoff_rows(),
        retry_card_summary=retry_card_rows(),
        retry_characteristics_summary=retry_characteristic_rows(),
        data_quality_summary=quality_rows(),
        repeated_attempt_source_consistency_summary=(repeated_source_rows()),
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
    assert "How to read the suggestion-choice charts" in html
    assert "if 12 eligible attempts received" in normalized_html
    assert "the bar is 75%" in normalized_html
    assert "if a group offered 10 suggestions at index 0" in normalized_html
    assert "its index-0 point is 40%" in normalized_html
    assert "Later positions may have fewer opportunities" in normalized_html

    summary = html.index("<summary>How to read the suggestion-choice charts</summary>")
    panel_start = html.rfind('<details class="explanation-panel">', 0, summary)
    panel_end = html.index("</details>", summary)
    panel = html[panel_start:panel_end]
    assert '<details class="explanation-panel" open' not in panel


def test_html_report_explains_field_adoption_and_editing() -> None:
    """Explain field offer, selection, and selected-edit populations."""
    html = render_html_report(
        records=feedback_records(),
        overview_summary=overview_rows(),
        author_handoff_summary=author_handoff_rows(),
        retry_card_summary=retry_card_rows(),
        retry_characteristics_summary=retry_characteristic_rows(),
        data_quality_summary=quality_rows(),
        repeated_attempt_source_consistency_summary=(repeated_source_rows()),
        charts=charts(),
    )
    normalized_html = " ".join(html.split())

    assert "How to read field adoption and editing" in html
    assert "if 20 completed AI attempts had a description suggestion" in (
        normalized_html
    )
    assert "The selection percentage is 40%" in normalized_html
    assert "not 8 divided by every completed AI attempt" in normalized_html
    assert "if 10 attempts selected a title suggestion" in normalized_html
    assert "3 of those 10 selected attempts" in normalized_html
    assert "does not show that the edit improved or harmed" in normalized_html

    summary = html.index("<summary>How to read field adoption and editing</summary>")
    panel_start = html.rfind('<details class="explanation-panel">', 0, summary)
    panel_end = html.index("</details>", summary)
    panel = html[panel_start:panel_end]
    assert '<details class="explanation-panel" open' not in panel


def test_html_report_explains_readability_indicators() -> None:
    html = render_html_report(
        records=feedback_records(),
        overview_summary=overview_rows(),
        author_handoff_summary=author_handoff_rows(),
        retry_card_summary=retry_card_rows(),
        retry_characteristics_summary=retry_characteristic_rows(),
        data_quality_summary=quality_rows(),
        repeated_attempt_source_consistency_summary=(repeated_source_rows()),
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
    assert "How to read direction and final grade bands" in html
    assert "5 lower, 4 within tolerance, and 3 higher" in normalized_html
    assert "segments of 5, 4, and 3" in normalized_html
    assert "if an AI-description bar contains 20 final texts" in normalized_html
    assert "6 of those 20 formula values fell in that band" in normalized_html
    assert "not a reading-age assignment or a quality rating" in normalized_html
    assert "How to read selected versus unselected differences" in html
    assert "selected suggestion's Flesch-Kincaid value minus the mean" in (
        normalized_html
    )
    assert "a bar at -0.5" in normalized_html
    assert "selected suggestion's formula value was" in normalized_html
    assert "0.5 grade levels higher at the median" in normalized_html
    assert "formula-score differences only" in normalized_html

    for panel_title in (
        "How to read direction and final grade bands",
        "How to read selected versus unselected differences",
    ):
        summary = html.index(f"<summary>{panel_title}</summary>")
        panel_start = html.rfind('<details class="explanation-panel">', 0, summary)
        panel_end = html.index("</details>", summary)
        panel = html[panel_start:panel_end]
        assert '<details class="explanation-panel" open' not in panel

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


def test_html_report_displays_authorized_user_feedback_table() -> None:
    html = render_html_report(
        records=feedback_records(),
        overview_summary=overview_rows(),
        author_handoff_summary=author_handoff_rows(),
        retry_card_summary=retry_card_rows(),
        retry_characteristics_summary=retry_characteristic_rows(),
        data_quality_summary=quality_rows(),
        repeated_attempt_source_consistency_summary=(repeated_source_rows()),
        charts=charts(),
    )
    normalized_html = " ".join(html.split())

    assert 'id="user-feedback-heading"' in html
    assert "User feedback on AI assistance" in html
    assert "<table" in html
    assert "<caption>" in html
    assert "Available AI-usefulness feedback ordered by audit record ID" in (
        normalized_html
    )
    assert '<th scope="col">Audit record ID</th>' in html
    assert '<th scope="col">User feedback</th>' in html
    assert normalized_html.index("Synthetic feedback shown first.") < (
        normalized_html.index(
            "Synthetic feedback with &lt;tags&gt; &amp; special characters."
        )
    )
    assert ">10<" in normalized_html
    assert ">30<" in normalized_html
    assert ">20<" not in normalized_html
    assert ">40<" not in normalized_html
    assert "<tags>" not in html
    assert "&lt;tags&gt; &amp; special characters." in html
    assert html.rstrip().endswith("</html>")
    assert "Interpretation and privacy" not in html
    assert html.index("User feedback on AI assistance") < html.index("</main>")


def test_html_report_displays_feedback_empty_state() -> None:
    html = render_html_report(
        records=pd.DataFrame(
            {
                "ID": pd.Series(dtype="Int64"),
                "USER_FEEDBACK_COMMENTS": pd.Series(dtype="string"),
            }
        ),
        overview_summary=overview_rows(),
        author_handoff_summary=author_handoff_rows(),
        retry_card_summary=retry_card_rows(),
        retry_characteristics_summary=retry_characteristic_rows(),
        data_quality_summary=quality_rows(),
        repeated_attempt_source_consistency_summary=(repeated_source_rows()),
        charts=charts(),
    )

    assert "No user feedback about AI usefulness was available" in html
    assert '<table class="feedback-table">' not in html


@pytest.mark.parametrize(
    ("records", "message"),
    [
        (
            pd.DataFrame(
                {
                    "ID": [1],
                }
            ),
            "lacks required feedback columns",
        ),
        (
            pd.DataFrame(
                {
                    "ID": [pd.NA],
                    "USER_FEEDBACK_COMMENTS": ["Synthetic feedback"],
                }
            ),
            "require an audit record ID",
        ),
        (
            pd.DataFrame(
                {
                    "ID": ["not-numeric"],
                    "USER_FEEDBACK_COMMENTS": ["Synthetic feedback"],
                }
            ),
            "require numeric audit record IDs",
        ),
        (
            pd.DataFrame(
                {
                    "ID": [1.5],
                    "USER_FEEDBACK_COMMENTS": ["Synthetic feedback"],
                }
            ),
            "require integer audit record IDs",
        ),
    ],
)
def test_html_report_validates_feedback_records(
    records: pd.DataFrame,
    message: str,
) -> None:
    with pytest.raises(
        ExplorationValidationError,
        match=message,
    ):
        render_html_report(
            records=records,
            overview_summary=overview_rows(),
            author_handoff_summary=author_handoff_rows(),
            retry_card_summary=retry_card_rows(),
            retry_characteristics_summary=retry_characteristic_rows(),
            data_quality_summary=quality_rows(),
            repeated_attempt_source_consistency_summary=(repeated_source_rows()),
            charts=charts(),
        )


def test_html_report_excludes_identifier_and_payload_values() -> None:
    html = render_html_report(
        records=feedback_records(),
        overview_summary=overview_rows(),
        author_handoff_summary=author_handoff_rows(),
        retry_card_summary=retry_card_rows(),
        retry_characteristics_summary=retry_characteristic_rows(),
        data_quality_summary=quality_rows(),
        repeated_attempt_source_consistency_summary=(repeated_source_rows()),
        charts=charts(),
    )

    forbidden_values = (
        "synthetic-author@example.edu",
        "SYNTHETIC-STUDY-1",
        "selected_text",
        "final_text",
        "LLM_SUGGESTIONS",
        "FINAL_SUBMISSION",
        "forbidden-author@example.edu",
        "FORBIDDEN-STUDY",
        "FORBIDDEN-SUGGESTION-PAYLOAD",
        "FORBIDDEN-FINAL-PAYLOAD",
        "another-forbidden-author@example.edu",
        "ANOTHER-FORBIDDEN-STUDY",
        "ANOTHER-FORBIDDEN-SUGGESTION",
        "ANOTHER-FORBIDDEN-FINAL",
    )

    for value in forbidden_values:
        assert value not in html


def test_write_html_report_creates_utf8_file(
    tmp_path: Path,
) -> None:
    path = tmp_path / "report.html"

    write_html_report(
        path,
        records=feedback_records(),
        overview_summary=overview_rows(),
        author_handoff_summary=author_handoff_rows(),
        retry_card_summary=retry_card_rows(),
        retry_characteristics_summary=retry_characteristic_rows(),
        data_quality_summary=quality_rows(),
        repeated_attempt_source_consistency_summary=(repeated_source_rows()),
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
            records=feedback_records(),
            overview_summary=overview_rows(),
            author_handoff_summary=author_handoff_rows(),
            retry_card_summary=retry_card_rows(),
            retry_characteristics_summary=retry_characteristic_rows(),
            data_quality_summary=quality_rows(),
            repeated_attempt_source_consistency_summary=(repeated_source_rows()),
            charts=charts(),
        )


def test_html_report_rejects_missing_overview_columns() -> None:
    with pytest.raises(
        ExplorationValidationError,
        match="overview_summary lacks required HTML columns",
    ):
        render_html_report(
            records=feedback_records(),
            overview_summary=pd.DataFrame(
                {
                    "overview_metric_name": ["all_attempt_count"],
                }
            ),
            author_handoff_summary=author_handoff_rows(),
            retry_card_summary=retry_card_rows(),
            retry_characteristics_summary=retry_characteristic_rows(),
            data_quality_summary=quality_rows(),
            repeated_attempt_source_consistency_summary=(repeated_source_rows()),
            charts=charts(),
        )


def test_html_report_rejects_missing_required_kpi_metric() -> None:
    rows = overview_rows().loc[
        overview_rows()["overview_metric_name"].ne(
            "distinct_author_count_with_any_attempt"
        )
    ]

    with pytest.raises(
        ExplorationValidationError,
        match="lacks required metric 'distinct_author_count_with_any_attempt'",
    ):
        render_html_report(
            records=feedback_records(),
            overview_summary=rows,
            author_handoff_summary=author_handoff_rows(),
            retry_card_summary=retry_card_rows(),
            retry_characteristics_summary=retry_characteristic_rows(),
            data_quality_summary=quality_rows(),
            repeated_attempt_source_consistency_summary=(repeated_source_rows()),
            charts=charts(),
        )


def test_html_report_rejects_pathway_count_above_completed_population() -> None:
    rows = overview_rows()
    rows.loc[
        rows["overview_metric_name"].eq(
            "distinct_completed_study_count_with_preceding_incomplete_attempts"
        ),
        "metric_count",
    ] = 9

    with pytest.raises(
        ExplorationValidationError,
        match="outside the completed-study population",
    ):
        render_html_report(
            records=feedback_records(),
            overview_summary=rows,
            author_handoff_summary=author_handoff_rows(),
            retry_card_summary=retry_card_rows(),
            retry_characteristics_summary=retry_characteristic_rows(),
            data_quality_summary=quality_rows(),
            repeated_attempt_source_consistency_summary=(repeated_source_rows()),
            charts=charts(),
        )


def test_html_report_requires_author_handoff_columns() -> None:
    with pytest.raises(
        ExplorationValidationError,
        match="author_handoff_summary lacks required HTML columns",
    ):
        render_html_report(
            records=feedback_records(),
            overview_summary=overview_rows(),
            author_handoff_summary=pd.DataFrame(
                {
                    "author_handoff_category": ["NO_PRECEDING_ATTEMPT"],
                }
            ),
            retry_card_summary=retry_card_rows(),
            retry_characteristics_summary=retry_characteristic_rows(),
            data_quality_summary=quality_rows(),
            repeated_attempt_source_consistency_summary=(repeated_source_rows()),
            charts=charts(),
        )


def test_html_report_requires_repeated_source_columns() -> None:
    """Reject incomplete repeated-source aggregate input."""
    with pytest.raises(
        ExplorationValidationError,
        match="lacks required HTML columns",
    ):
        render_html_report(
            records=feedback_records(),
            overview_summary=overview_rows(),
            author_handoff_summary=author_handoff_rows(),
            retry_card_summary=retry_card_rows(),
            retry_characteristics_summary=retry_characteristic_rows(),
            data_quality_summary=quality_rows(),
            repeated_attempt_source_consistency_summary=pd.DataFrame(
                {
                    "summary_grain": [
                        "COMPLETED_AI_PATH_CONSECUTIVE_SUCCESSFUL_AI_TRANSITION"
                    ]
                }
            ),
            charts=charts(),
        )


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (
            lambda rows: rows.assign(
                population_unit_count=[
                    8,
                    *rows["population_unit_count"].iloc[1:].tolist(),
                ]
            ),
            "inconsistent population counts",
        ),
        (
            lambda rows: rows.loc[
                ~(
                    rows["comparison_dimension_name"].eq("SOURCE_SIZE")
                    & rows["comparison_category"].eq("MISSING")
                )
            ],
            "requires SAME, CHANGED, and MISSING",
        ),
        (
            lambda rows: rows.assign(
                eligible_unit_count=[
                    (4 if index == 1 else value)
                    for index, value in enumerate(rows["eligible_unit_count"])
                ]
            ),
            "inconsistent comparable denominators",
        ),
        (
            lambda rows: rows.assign(
                category_unit_count=[
                    (1 if index == 2 else value)
                    for index, value in enumerate(rows["category_unit_count"])
                ]
            ),
            "comparison counts do not reconcile",
        ),
    ],
)
def test_html_report_validates_repeated_source_context(
    mutator: Callable[[pd.DataFrame], pd.DataFrame],
    message: str,
) -> None:
    """Reject internally contradictory repeated-source aggregates."""
    with pytest.raises(
        ExplorationValidationError,
        match=message,
    ):
        render_html_report(
            records=feedback_records(),
            overview_summary=overview_rows(),
            author_handoff_summary=author_handoff_rows(),
            retry_card_summary=retry_card_rows(),
            retry_characteristics_summary=retry_characteristic_rows(),
            data_quality_summary=quality_rows(),
            repeated_attempt_source_consistency_summary=mutator(repeated_source_rows()),
            charts=charts(),
        )


def test_html_report_explains_empty_repeated_source_pathways() -> None:
    """Provide an explicit empty state for completed-path transitions."""
    empty = pd.DataFrame(columns=repeated_source_rows().columns)
    rendered = render_html_report(
        records=feedback_records(),
        overview_summary=overview_rows(),
        author_handoff_summary=author_handoff_rows(),
        retry_card_summary=retry_card_rows(),
        retry_characteristics_summary=retry_characteristic_rows(),
        data_quality_summary=quality_rows(),
        repeated_attempt_source_consistency_summary=empty,
        charts=charts(),
    )
    normalized = " ".join(rendered.split())

    assert (
        "No completed AI pathway contained two generation attempts "
        "that returned a result"
    ) in normalized
    assert "Available comparisons" not in rendered


def test_html_report_displays_aggregate_data_quality() -> None:
    """Display fatal-pass guarantees and nonzero warning context."""
    html = render_html_report(
        records=feedback_records(),
        overview_summary=overview_rows(),
        author_handoff_summary=author_handoff_rows(),
        retry_card_summary=retry_card_rows(),
        retry_characteristics_summary=retry_characteristic_rows(),
        data_quality_summary=quality_rows(),
        repeated_attempt_source_consistency_summary=(repeated_source_rows()),
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
        records=feedback_records(),
        overview_summary=overview_rows(),
        author_handoff_summary=author_handoff_rows(),
        retry_card_summary=retry_card_rows(),
        retry_characteristics_summary=retry_characteristic_rows(),
        data_quality_summary=quality_rows(malformed_appointment_count=0),
        repeated_attempt_source_consistency_summary=(repeated_source_rows()),
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
            records=feedback_records(),
            overview_summary=overview_rows(),
            author_handoff_summary=author_handoff_rows(),
            retry_card_summary=retry_card_rows(),
            retry_characteristics_summary=retry_characteristic_rows(),
            data_quality_summary=pd.DataFrame(
                {
                    "severity_level": ["WARNING"],
                }
            ),
            repeated_attempt_source_consistency_summary=(repeated_source_rows()),
            charts=charts(),
        )


def test_html_report_requires_retry_cutoff_columns() -> None:
    """Reject retry characteristics without cutoff timing columns."""
    rows = retry_characteristic_rows().drop(
        columns=["study_count_with_report_run_cutoff"]
    )

    with pytest.raises(
        ExplorationValidationError,
        match="retry_characteristics_summary lacks required HTML columns",
    ):
        render_html_report(
            records=feedback_records(),
            overview_summary=overview_rows(),
            author_handoff_summary=author_handoff_rows(),
            retry_card_summary=retry_card_rows(),
            retry_characteristics_summary=rows,
            data_quality_summary=quality_rows(),
            repeated_attempt_source_consistency_summary=repeated_source_rows(),
            charts=charts(),
        )


def test_html_retry_timing_keeps_completed_and_unresolved_measures_distinct() -> None:
    """Show completed timing separately from unresolved cutoff durations."""
    html = render_html_report(
        records=feedback_records(),
        overview_summary=overview_rows(),
        author_handoff_summary=author_handoff_rows(),
        retry_card_summary=retry_card_rows(),
        retry_characteristics_summary=retry_characteristic_rows(),
        data_quality_summary=quality_rows(),
        repeated_attempt_source_consistency_summary=repeated_source_rows(),
        charts=charts(),
    )
    normalized = " ".join(html.split())

    assert "First attempt to completion end" in normalized
    assert "First to latest observed attempt" in normalized
    assert "Latest attempt to report-run cutoff" in normalized
    assert "First attempt to report-run cutoff" in normalized
    assert "1,440 minutes (n=2)" in normalized
    assert "1,485 minutes (n=2)" in normalized
    assert "\\N" in normalized
