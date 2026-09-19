"""Aggregate-only Plotly chart construction."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

import pandas as pd
import plotly.graph_objects as go

from study_posting_audit_exploration.errors import ExplorationValidationError

_ALL = "ALL"

_REQUIRED_OVERVIEW_COLUMNS: tuple[str, ...] = (
    "overview_metric_name",
    "overview_metric_label",
    "metric_count",
    "metric_denominator_count",
    "metric_percentage",
    "metric_denominator_definition",
)

_REQUIRED_ATTEMPT_COLUMNS: tuple[str, ...] = (
    "attempt_completion_group",
    "attempt_result",
    "attempt_authoring_mode",
    "grouping_dimension_1_name",
    "grouping_dimension_2_name",
    "attempt_count",
    "attempt_count_with_nonmissing_study_info_page_time",
    "attempt_count_missing_study_info_page_time",
    "percentile_25_study_info_page_minutes",
    "median_study_info_page_minutes",
    "percentile_75_study_info_page_minutes",
    "percentile_90_study_info_page_minutes",
    "attempt_count_with_nonmissing_total_attempt_time",
    "attempt_count_missing_total_attempt_time",
    "percentile_25_total_attempt_minutes",
    "median_total_attempt_minutes",
    "percentile_75_total_attempt_minutes",
    "percentile_90_total_attempt_minutes",
)

_REQUIRED_CONTENT_SOURCE_COLUMNS: tuple[str, ...] = (
    "attempt_completion_group",
    "reported_study_content_source",
    "inferred_study_content_source",
    "ai_attempt_count",
)

_REQUIRED_STUDY_HISTORY_COLUMNS: tuple[str, ...] = (
    "final_completion_authoring_mode",
    "distinct_study_count",
    "study_count_with_preceding_incomplete_attempts",
    "minimum_minutes_first_attempt_to_completion",
    "median_minutes_first_attempt_to_completion",
    "average_minutes_first_attempt_to_completion",
    "standard_deviation_minutes_first_attempt_to_completion",
    "maximum_minutes_first_attempt_to_completion",
)

_REQUIRED_AUTHOR_HANDOFF_COLUMNS: tuple[str, ...] = (
    "completed_attempt_authoring_mode",
    "author_handoff_category",
    "distinct_completed_study_count",
)

_REQUIRED_ATTEMPT_START_EXPERIENCE_COLUMNS: tuple[str, ...] = (
    "author_adoption_group",
    "attempt_completion_group",
    "attempt_authoring_mode",
    "experience_metric_name",
    "experience_metric_unit",
    "author_attempt_count_with_nonmissing_metric",
    "median_author_attempt_value",
)

_REQUIRED_CURRENT_AUTHOR_EXPERIENCE_COLUMNS: tuple[str, ...] = (
    "author_adoption_group",
    "experience_metric_name",
    "experience_metric_unit",
    "author_count_with_nonmissing_metric",
    "median_author_value",
)

_REQUIRED_GROUPED_STUDY_COLUMNS: tuple[str, ...] = (
    "study_population_name",
    "final_completion_authoring_mode",
    "grouping_dimension_1_name",
    "grouping_dimension_1_value",
    "grouping_dimension_2_name",
    "group_values_are_mutually_exclusive",
    "distinct_study_count",
    "population_distinct_study_count",
    "distinct_study_percentage_within_population",
)

_REQUIRED_COMPLETED_STUDY_AUTHOR_CONTEXT_COLUMNS: tuple[str, ...] = (
    "context_dimension_name",
    "context_dimension_value",
    "final_completion_authoring_mode",
    "completed_study_count",
    "mode_completed_study_count",
    "all_completed_study_count",
    "completed_study_percentage_within_mode",
    "completed_study_percentage_overall",
    "distinct_completion_author_count",
)

_REQUIRED_GROUPED_AUTHOR_COLUMNS: tuple[str, ...] = (
    "author_population_name",
    "attempt_completion_group",
    "attempt_authoring_mode",
    "effective_author_role",
    "grouping_dimension_name",
    "grouping_dimension_value",
    "group_values_are_mutually_exclusive",
    "distinct_author_count",
    "population_distinct_author_count",
    "distinct_author_percentage_within_population",
    "distinct_author_count_classified_as_pi",
)

_REQUIRED_FIELD_ADOPTION_COLUMNS: tuple[str, ...] = (
    "field_name",
    "analysis_type",
    "completed_ai_attempt_count",
    "completed_ai_attempt_count_with_suggestion_offered",
    "completed_ai_attempt_count_with_suggestion_selected",
    "completed_ai_attempt_count_selected_and_exactly_retained",
    "completed_ai_attempt_count_selected_and_cosmetically_changed",
    "completed_ai_attempt_count_selected_and_lightly_edited",
    "completed_ai_attempt_count_selected_and_moderately_edited",
    "completed_ai_attempt_count_selected_and_heavily_edited",
    "completed_ai_attempt_count_selected_and_unclassified_edit",
    "completed_ai_attempt_count_selected_and_replaced",
    "completed_ai_attempt_count_selected_then_cleared",
    "completed_ai_attempt_count_unassisted",
    "suggestion_selection_percentage_among_attempts_with_offer",
)

_REQUIRED_SUGGESTION_SELECTION_COLUMNS: tuple[str, ...] = (
    "field_name",
    "suggestion_kind",
    "suggestion_index",
    "offered_suggestion_count",
    "selected_suggestion_count",
    "completed_ai_attempt_count_with_at_least_one_suggestion",
    "completed_ai_attempt_count_with_selected_suggestion",
    "suggestion_level_selection_percentage",
    "attempt_level_selection_percentage",
    "suggestion_count_at_index",
    "selected_suggestion_count_at_index",
    "selection_percentage_at_index",
)

_REQUIRED_READABILITY_CHANGE_COLUMNS: tuple[str, ...] = (
    "field_name",
    "readability_measure_name",
    "paired_selected_final_attempt_count",
    "attempt_count_value_decreased",
    "attempt_count_no_material_change",
    "attempt_count_value_increased",
    "percentage_value_decreased",
    "percentage_no_material_change",
    "percentage_value_increased",
    "unchanged_absolute_tolerance",
    "short_text_readability_caution",
)

_REQUIRED_READABILITY_TARGET_COLUMNS: tuple[str, ...] = (
    "attempt_authoring_mode",
    "field_name",
    "readability_measure_name",
    "final_text_attempt_count",
    "attempt_count_at_or_below_grade_6",
    "attempt_count_above_grade_6_through_grade_8",
    "attempt_count_above_grade_8_through_grade_10",
    "attempt_count_above_grade_10",
    "percentage_at_or_below_grade_8",
    "short_text_readability_caution",
    "target_interpretation_note",
)

_REQUIRED_SELECTED_COMPARISON_COLUMNS: tuple[str, ...] = (
    "field_name",
    "readability_measure_name",
    "completed_ai_attempt_count_with_selected_and_unselected_suggestions",
    "median_selected_minus_mean_unselected_value",
    "attempt_count_selected_value_lower",
    "attempt_count_selected_value_equal_within_tolerance",
    "attempt_count_selected_value_higher",
    "equality_tolerance",
)

_REQUIRED_EDIT_READABILITY_CROSS_COLUMNS: tuple[str, ...] = (
    "field_name",
    "edit_intensity_threshold_scheme_name",
    "edit_intensity_category",
    "readability_direction_category",
    "completed_ai_attempt_count",
    "completed_ai_attempt_count_with_selected_final_pair",
    "percentage_within_edit_intensity_category",
    "median_flesch_kincaid_grade_change_final_minus_selected",
    "median_consensus_grade_level_change",
)

_ATTEMPT_OUTCOME_SPECS: tuple[
    tuple[str, str, str, str, str],
    ...,
] = (
    (
        "COMPLETE",
        "AI",
        "completed_ai_attempt_count",
        "Completed — AI",
        "AI complete",
    ),
    (
        "COMPLETE",
        "MANUAL",
        "completed_manual_attempt_count",
        "Completed — manual",
        "Manual complete",
    ),
    (
        "INCOMPLETE",
        "AI",
        "incomplete_ai_attempt_count",
        "Incomplete — AI",
        "AI incomplete",
    ),
    (
        "INCOMPLETE",
        "MANUAL",
        "incomplete_manual_attempt_count",
        "Incomplete — manual",
        "Manual incomplete",
    ),
)

_AUTHORING_MODE_ORDER: tuple[str, ...] = (
    "AI",
    "MANUAL",
)

_AUTHOR_HANDOFF_ORDER: tuple[str, ...] = (
    "NO_PRECEDING_ATTEMPT",
    "ALL_PRECEDING_ATTEMPTS_BY_COMPLETION_AUTHOR",
    "ALL_PRECEDING_ATTEMPTS_BY_OTHER_AUTHORS",
    "MIXED_COMPLETION_AND_OTHER_AUTHORS",
)

_AUTHOR_HANDOFF_LABELS: Mapping[str, str] = {
    "NO_PRECEDING_ATTEMPT": "No preceding attempt",
    "ALL_PRECEDING_ATTEMPTS_BY_COMPLETION_AUTHOR": (
        "All preceding attempts by completion author"
    ),
    "ALL_PRECEDING_ATTEMPTS_BY_OTHER_AUTHORS": (
        "All preceding attempts by other authors"
    ),
    "MIXED_COMPLETION_AND_OTHER_AUTHORS": "Mixed completion and other authors",
}

_AUTHOR_ADOPTION_GROUP_ORDER: tuple[str, ...] = (
    "ALL_AUTHORS",
    "AI_ONLY",
    "MANUAL_ONLY",
    "BOTH_AI_AND_MANUAL",
)

_AUTHOR_ADOPTION_GROUP_LABELS: Mapping[str, str] = {
    "ALL_AUTHORS": "All authors",
    "AI_ONLY": "AI only",
    "MANUAL_ONLY": "Manual only",
    "BOTH_AI_AND_MANUAL": "Both AI and manual",
}

_AUTHOR_EXPERIENCE_METRIC_LABELS: Mapping[str, str] = {
    "total_studies_created_as_of_report_query_count": "Total studies created",
    "other_study_memberships_as_of_report_query_count": ("Other study memberships"),
    "distinct_login_days_as_of_report_query_count": "Distinct login days",
    "login_history_span_days_as_of_report_query": "Login-history span",
}

_AUTHOR_EXPERIENCE_METRIC_DEFINITIONS: Mapping[str, str] = {
    "total_studies_created_as_of_report_query_count": (
        "Total studies created by the attempt author when the report query ran."
    ),
    "other_study_memberships_as_of_report_query_count": (
        "Other study memberships held by the attempt author when the report "
        "query ran, excluding the study being attempted."
    ),
    "distinct_login_days_as_of_report_query_count": (
        "Distinct calendar days with a successful login across the history "
        "available when the report query ran; multiple logins on one day count "
        "once."
    ),
    "login_history_span_days_as_of_report_query": (
        "Elapsed days between the earliest and latest successful login "
        "timestamps available when the report query ran; this is not the number "
        "of active login days."
    ),
}

_ATTEMPT_START_EXPERIENCE_METRIC = "prior_studies_created_before_attempt_start_count"
_ATTEMPT_START_EXPERIENCE_LABEL = "Studies created before attempt start"
_ATTEMPT_START_EXPERIENCE_DEFINITION = (
    "Other studies created by the attempt author before that attempt's "
    "START_TIME. One author may contribute multiple attempt observations."
)
_FIELD_DISPLAY_LABELS: Mapping[str, str] = {
    "title": "Title",
    "about": "About",
    "purpose": "Purpose",
    "description": "Description",
    "compensation": "Compensation",
}

_FLESCH_KINCAID_GRADE = "flesch_kincaid_grade"

_READABILITY_DIRECTION_SERIES: tuple[tuple[str, str], ...] = (
    (
        "attempt_count_value_decreased",
        "Final value decreased",
    ),
    (
        "attempt_count_no_material_change",
        "No material change",
    ),
    (
        "attempt_count_value_increased",
        "Final value increased",
    ),
)

_CONSENSUS_DIRECTION_ORDER: tuple[str, ...] = (
    "CONSENSUS_GRADE_LEVEL_DECREASE",
    "NO_MATERIAL_CHANGE",
    "CONSENSUS_GRADE_LEVEL_INCREASE",
    "MIXED_FORMULA_DIRECTION",
)

_CONSENSUS_DIRECTION_LABELS: Mapping[str, str] = {
    "CONSENSUS_GRADE_LEVEL_DECREASE": "Consensus grade-level decrease",
    "NO_MATERIAL_CHANGE": "No material change",
    "CONSENSUS_GRADE_LEVEL_INCREASE": "Consensus grade-level increase",
    "MIXED_FORMULA_DIRECTION": "Mixed formula direction",
}

_EDIT_INTENSITY_ORDER: tuple[str, ...] = (
    "EXACT",
    "COSMETIC",
    "LIGHT_EDIT",
    "MODERATE_EDIT",
    "HEAVY_EDIT",
    "EDITED_UNCLASSIFIED",
    "REPLACED",
    "CLEARED",
    "UNASSISTED",
)

_EDIT_INTENSITY_LABELS: Mapping[str, str] = {
    "EXACT": "Exact",
    "COSMETIC": "Cosmetic",
    "LIGHT_EDIT": "Light edit",
    "MODERATE_EDIT": "Moderate edit",
    "HEAVY_EDIT": "Heavy edit",
    "EDITED_UNCLASSIFIED": "Edited, unclassified",
    "REPLACED": "Replaced",
    "CLEARED": "Cleared",
    "UNASSISTED": "Unassisted",
}

_EDIT_INTENSITY_RULES: Mapping[str, str] = {
    "EXACT": "Final text exactly matched the selected suggestion",
    "COSMETIC": "Only cosmetic normalization changed",
    "LIGHT_EDIT": "Character edit ratio at or below 10%",
    "MODERATE_EDIT": "Character edit ratio above 10% and at or below 30%",
    "HEAVY_EDIT": "Character edit ratio above 30%",
    "EDITED_UNCLASSIFIED": (
        "Edited, but usable character measurements were unavailable"
    ),
    "REPLACED": "Final text replaced the selected suggestion",
    "CLEARED": "Selected suggestion was removed and final text was blank",
    "UNASSISTED": "No AI suggestion was selected",
}

_CONSENSUS_DIRECTION_EXPLANATIONS: Mapping[str, str] = {
    "CONSENSUS_GRADE_LEVEL_DECREASE": (
        "Grade-level formulas agreed on a downward direction"
    ),
    "NO_MATERIAL_CHANGE": ("Formula changes stayed within the configured tolerance"),
    "CONSENSUS_GRADE_LEVEL_INCREASE": (
        "Grade-level formulas agreed on an upward direction"
    ),
    "MIXED_FORMULA_DIRECTION": ("Grade-level formulas did not agree on direction"),
}

_CONSENSUS_DIRECTION_CAUTIONS: Mapping[str, str] = {
    "CONSENSUS_GRADE_LEVEL_DECREASE": (
        "A decrease is directional, not evidence of better writing"
    ),
    "NO_MATERIAL_CHANGE": (
        "No material formula change does not establish comprehension"
    ),
    "CONSENSUS_GRADE_LEVEL_INCREASE": (
        "An increase is directional, not evidence of worse writing"
    ),
    "MIXED_FORMULA_DIRECTION": (
        "Mixed direction is not the same as no material change"
    ),
}

_GRADE_BAND_SERIES: tuple[tuple[str, str], ...] = (
    (
        "attempt_count_at_or_below_grade_6",
        "At or below grade 6",
    ),
    (
        "attempt_count_above_grade_6_through_grade_8",
        "Above grade 6 through grade 8",
    ),
    (
        "attempt_count_above_grade_8_through_grade_10",
        "Above grade 8 through grade 10",
    ),
    (
        "attempt_count_above_grade_10",
        "Above grade 10",
    ),
)

_FIELD_EDIT_OUTCOMES: tuple[tuple[str, str], ...] = (
    (
        "completed_ai_attempt_count_selected_and_exactly_retained",
        "Exactly retained",
    ),
    (
        "completed_ai_attempt_count_selected_and_cosmetically_changed",
        "Cosmetically changed",
    ),
    (
        "completed_ai_attempt_count_selected_and_lightly_edited",
        "Light edit",
    ),
    (
        "completed_ai_attempt_count_selected_and_moderately_edited",
        "Moderate edit",
    ),
    (
        "completed_ai_attempt_count_selected_and_heavily_edited",
        "Heavy edit",
    ),
    (
        "completed_ai_attempt_count_selected_and_unclassified_edit",
        "Edited, unclassified",
    ),
    (
        "completed_ai_attempt_count_selected_and_replaced",
        "Replaced",
    ),
    (
        "completed_ai_attempt_count_selected_then_cleared",
        "Cleared",
    ),
)


@dataclass(frozen=True, slots=True)
class ExplorationChartInputs:
    """Aggregate-only DataFrames consumed by the HTML chart bundle."""

    overview_summary: pd.DataFrame
    grouped_attempt_summary: pd.DataFrame
    study_attempt_history_summary: pd.DataFrame
    author_handoff_summary: pd.DataFrame
    attempt_start_experience_summary: pd.DataFrame
    current_author_experience_summary: pd.DataFrame
    grouped_study_summary: pd.DataFrame
    completed_study_author_context_summary: pd.DataFrame
    grouped_author_summary: pd.DataFrame
    field_adoption_editing_summary: pd.DataFrame
    suggestion_selection_summary: pd.DataFrame
    field_readability_change_summary: pd.DataFrame
    field_readability_target_summary: pd.DataFrame
    selected_vs_unselected_readability_summary: pd.DataFrame
    field_edit_readability_cross_summary: pd.DataFrame
    content_source_matrix: pd.DataFrame


@dataclass(frozen=True, slots=True)
class ExplorationCharts:
    """Aggregate-only figures for the HTML report."""

    attempt_outcomes_by_mode: go.Figure
    attempt_timing_distribution_by_mode: go.Figure
    study_completion_pathways: go.Figure
    author_handoff_categories: go.Figure
    author_attempt_start_experience: go.Figure
    author_experience_studies: go.Figure
    author_experience_days: go.Figure
    completed_study_participant_mix: go.Figure
    completed_study_department_mix: go.Figure
    completed_studies_by_completion_author_role: go.Figure
    completed_studies_by_completion_author_pi_status: go.Figure
    author_appointment_schools: go.Figure
    pi_appointment_schools: go.Figure
    author_appointment_departments: go.Figure
    pi_appointment_departments: go.Figure
    author_appointment_titles: go.Figure
    pi_appointment_titles: go.Figure
    field_suggestion_adoption: go.Figure
    field_selected_outcomes: go.Figure
    suggestion_selection_by_kind: go.Figure
    suggestion_selection_by_index: go.Figure
    readability_change_direction: go.Figure
    final_grade_bands: go.Figure
    selected_vs_unselected_readability: go.Figure
    edit_readability_relationship: go.Figure
    content_source_concordance: go.Figure


def _require_columns(
    frame: pd.DataFrame,
    *,
    required: tuple[str, ...],
    frame_name: str,
) -> None:
    """Require the aggregate columns consumed by one chart."""
    missing = tuple(
        column_name for column_name in required if column_name not in frame.columns
    )

    if missing:
        raise ExplorationValidationError(
            f"{frame_name} lacks required chart columns: {missing!r}"
        )


def _empty_figure(
    *,
    title: str,
    message: str,
) -> go.Figure:
    """Return one accessible empty-state figure."""
    figure = go.Figure()
    figure.add_annotation(
        text=message,
        showarrow=False,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
    )
    figure.update_layout(
        title=title,
        template="plotly_white",
        xaxis={"visible": False},
        yaxis={"visible": False},
    )

    return figure


def _unique_overview_rows(
    overview_summary: pd.DataFrame,
) -> dict[str, dict[str, object]]:
    """Return unique overview rows keyed by metric name."""
    _require_columns(
        overview_summary,
        required=_REQUIRED_OVERVIEW_COLUMNS,
        frame_name="overview_summary",
    )
    rows_by_name: dict[str, dict[str, object]] = {}

    records = cast(
        "list[dict[str, object]]",
        overview_summary.to_dict(orient="records"),
    )

    for row in records:
        metric_name = str(row["overview_metric_name"])

        if metric_name in rows_by_name:
            raise ExplorationValidationError(
                f"overview_summary contains duplicate metric {metric_name!r}"
            )

        rows_by_name[metric_name] = row

    return rows_by_name


def _overview_count(
    rows_by_name: Mapping[str, Mapping[str, object]],
    metric_name: str,
) -> int:
    """Return one validated nonnegative overview count."""
    row = rows_by_name.get(metric_name)

    if row is None:
        raise ExplorationValidationError(
            f"overview_summary lacks required metric {metric_name!r}"
        )

    value = row["metric_count"]

    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ExplorationValidationError(
            f"overview metric {metric_name!r} count must be numeric"
        )

    converted = float(value)

    if not converted.is_integer() or converted < 0:
        raise ExplorationValidationError(
            f"overview metric {metric_name!r} count must be a nonnegative integer"
        )

    return int(converted)


def build_attempt_outcomes_chart(
    overview_summary: pd.DataFrame,
) -> go.Figure:
    """Return one four-part partition of all attempts."""
    rows_by_name = _unique_overview_rows(overview_summary)

    if not rows_by_name:
        return _empty_figure(
            title="How the captured attempts ended",
            message="No attempt outcome aggregates are available.",
        )

    all_attempt_count = _overview_count(rows_by_name, "all_attempt_count")
    complete_attempt_count = _overview_count(
        rows_by_name,
        "complete_attempt_count",
    )
    incomplete_attempt_count = _overview_count(
        rows_by_name,
        "incomplete_attempt_count",
    )
    completion_counts = {
        "COMPLETE": complete_attempt_count,
        "INCOMPLETE": incomplete_attempt_count,
    }
    outcome_counts = [
        _overview_count(rows_by_name, metric_name)
        for _, _, metric_name, _, _ in _ATTEMPT_OUTCOME_SPECS
    ]

    if complete_attempt_count + incomplete_attempt_count != all_attempt_count:
        raise ExplorationValidationError(
            "overview attempt completion counts do not partition all attempts"
        )

    completed_outcome_count = sum(outcome_counts[:2])
    incomplete_outcome_count = sum(outcome_counts[2:])

    if (
        completed_outcome_count != complete_attempt_count
        or incomplete_outcome_count != incomplete_attempt_count
    ):
        raise ExplorationValidationError(
            "overview AI/manual outcome counts do not partition their completion groups"
        )

    if sum(outcome_counts) != all_attempt_count:
        raise ExplorationValidationError(
            "overview AI/manual outcome counts do not partition all attempts"
        )

    figure = go.Figure()
    colors = {
        ("COMPLETE", "AI"): "#1f5a94",
        ("COMPLETE", "MANUAL"): "#2f855a",
        ("INCOMPLETE", "AI"): "#9ec5e5",
        ("INCOMPLETE", "MANUAL"): "#9fc9ad",
    }
    patterns = {
        "COMPLETE": "",
        "INCOMPLETE": "/",
    }

    for (
        completion_group,
        authoring_mode,
        metric_name,
        label,
        short_label,
    ), count in zip(
        _ATTEMPT_OUTCOME_SPECS,
        outcome_counts,
        strict=True,
    ):
        completion_count = completion_counts[completion_group]
        percentage_all = 100.0 * count / all_attempt_count if all_attempt_count else 0.0
        percentage_completion = (
            100.0 * count / completion_count if completion_count else 0.0
        )
        denominator_definition = str(
            rows_by_name[metric_name]["metric_denominator_definition"]
        )
        figure.add_bar(
            name=label,
            x=[count],
            y=["All attempts"],
            orientation="h",
            text=[f"{short_label}<br>{count:,} ({percentage_all:.1f}%)"],
            textposition="inside",
            textangle=0,
            insidetextanchor="middle",
            marker={
                "color": colors[(completion_group, authoring_mode)],
                "pattern": {"shape": patterns[completion_group]},
                "line": {
                    "color": "#ffffff",
                    "width": 1,
                },
            },
            customdata=[
                [
                    percentage_all,
                    completion_count,
                    percentage_completion,
                    denominator_definition,
                ]
            ],
            hovertemplate=(
                "Outcome: %{fullData.name}<br>"
                "Attempts: %{x}<br>"
                "Share of all attempts: %{customdata[0]:.1f}%<br>"
                "Share within completion group: %{x} of "
                "%{customdata[1]} (%{customdata[2]:.1f}%)<br>"
                "Published denominator: %{customdata[3]}"
                "<extra></extra>"
            ),
        )

    figure.update_layout(
        title="How the captured attempts ended",
        template="plotly_white",
        barmode="stack",
        xaxis_title="Attempt count",
        yaxis_title="",
        legend_title_text="Attempt outcome and authoring mode",
        height=420,
        margin={
            "l": 120,
            "r": 40,
            "t": 80,
            "b": 70,
        },
        uniformtext={
            "minsize": 10,
            "mode": "hide",
        },
    )

    return figure


def _completed_authoring_mode_rows(
    grouped_attempt_summary: pd.DataFrame,
) -> pd.DataFrame:
    """Return completed-attempt rows grouped by authoring mode."""
    return grouped_attempt_summary.loc[
        grouped_attempt_summary["attempt_result"].eq(_ALL)
        & grouped_attempt_summary["attempt_completion_group"].eq("COMPLETE")
        & grouped_attempt_summary["grouping_dimension_1_name"].eq("COMPLETION_GROUP")
        & grouped_attempt_summary["grouping_dimension_2_name"].eq("AUTHORING_MODE")
        & grouped_attempt_summary["attempt_authoring_mode"].isin(_AUTHORING_MODE_ORDER)
    ].copy()


def build_attempt_timing_chart(
    grouped_attempt_summary: pd.DataFrame,
) -> go.Figure:
    """Return attempt timing distributions by authoring mode and measure."""
    _require_columns(
        grouped_attempt_summary,
        required=_REQUIRED_ATTEMPT_COLUMNS,
        frame_name="grouped_attempt_summary",
    )
    rows = _completed_authoring_mode_rows(grouped_attempt_summary)

    timing_specs = (
        (
            "Study-information-page time",
            "attempt_count_with_nonmissing_study_info_page_time",
            "attempt_count_missing_study_info_page_time",
            "percentile_25_study_info_page_minutes",
            "median_study_info_page_minutes",
            "percentile_75_study_info_page_minutes",
            "percentile_90_study_info_page_minutes",
        ),
        (
            "Total attempt time",
            "attempt_count_with_nonmissing_total_attempt_time",
            "attempt_count_missing_total_attempt_time",
            "percentile_25_total_attempt_minutes",
            "median_total_attempt_minutes",
            "percentile_75_total_attempt_minutes",
            "percentile_90_total_attempt_minutes",
        ),
    )
    available = rows.dropna(
        subset=[
            "median_study_info_page_minutes",
            "median_total_attempt_minutes",
        ],
        how="all",
    )

    if available.empty:
        return _empty_figure(
            title="Completed-attempt timing by authoring mode",
            message="No attempt timing aggregates are available.",
        )

    rows_by_mode = {
        str(row["attempt_authoring_mode"]): row
        for row in available.to_dict(orient="records")
    }
    figure = go.Figure()

    for (
        label,
        nonmissing_column,
        missing_column,
        percentile_25_column,
        median_column,
        percentile_75_column,
        percentile_90_column,
    ) in timing_specs:
        modes: list[str] = []
        medians: list[float] = []
        lower_errors: list[float] = []
        upper_errors: list[float] = []
        customdata: list[list[object]] = []

        for mode in _AUTHORING_MODE_ORDER:
            row = rows_by_mode.get(mode)

            if row is None or pd.isna(row[median_column]):
                continue

            median = float(row[median_column])
            percentile_25 = (
                float(row[percentile_25_column])
                if not pd.isna(row[percentile_25_column])
                else median
            )
            percentile_75 = (
                float(row[percentile_75_column])
                if not pd.isna(row[percentile_75_column])
                else median
            )
            percentile_90 = (
                float(row[percentile_90_column])
                if not pd.isna(row[percentile_90_column])
                else None
            )
            modes.append(mode)
            medians.append(median)
            lower_errors.append(max(median - percentile_25, 0.0))
            upper_errors.append(max(percentile_75 - median, 0.0))
            customdata.append(
                [
                    int(row[nonmissing_column]),
                    int(row[missing_column]),
                    percentile_25,
                    percentile_75,
                    percentile_90,
                ]
            )

        if not modes:
            continue

        figure.add_bar(
            name=label,
            x=modes,
            y=medians,
            error_y={
                "type": "data",
                "symmetric": False,
                "array": upper_errors,
                "arrayminus": lower_errors,
                "visible": True,
            },
            customdata=customdata,
            hovertemplate=(
                "Authoring mode: %{x}<br>"
                "Timing measure: %{fullData.name}<br>"
                "Median minutes: %{y:.2f}<br>"
                "25th percentile: %{customdata[2]:.2f}<br>"
                "75th percentile: %{customdata[3]:.2f}<br>"
                "90th percentile: %{customdata[4]:.2f}<br>"
                "Attempts with timing value: %{customdata[0]}<br>"
                "Attempts missing timing value: %{customdata[1]}"
                "<extra></extra>"
            ),
        )

    if not figure.data:
        return _empty_figure(
            title="Completed-attempt timing by authoring mode",
            message="No attempt timing aggregates are available.",
        )

    figure.update_layout(
        title="Completed-attempt timing by authoring mode",
        template="plotly_white",
        barmode="group",
        height=460,
        margin={
            "l": 110,
            "r": 40,
            "t": 90,
            "b": 70,
        },
        xaxis_title="Authoring mode",
        yaxis_title="Median minutes",
        legend_title_text="Attempt timing measure",
    )

    return figure


def build_study_completion_pathways_chart(
    study_attempt_history_summary: pd.DataFrame,
) -> go.Figure:
    """Return completed-study pathway counts by final authoring mode."""
    _require_columns(
        study_attempt_history_summary,
        required=_REQUIRED_STUDY_HISTORY_COLUMNS,
        frame_name="study_attempt_history_summary",
    )
    rows = study_attempt_history_summary.loc[
        study_attempt_history_summary["final_completion_authoring_mode"].isin(
            _AUTHORING_MODE_ORDER
        )
    ]

    if rows.empty:
        return _empty_figure(
            title="Completed-study pathways by final authoring mode",
            message="No completed-study pathway aggregates are available.",
        )

    study_counts: Mapping[str, int] = {
        str(row["final_completion_authoring_mode"]): int(row["distinct_study_count"])
        for row in rows.to_dict(orient="records")
    }
    preceding_counts: Mapping[str, int] = {
        str(row["final_completion_authoring_mode"]): int(
            row["study_count_with_preceding_incomplete_attempts"]
        )
        for row in rows.to_dict(orient="records")
    }
    no_preceding_counts = {
        mode: max(study_counts.get(mode, 0) - preceding_counts.get(mode, 0), 0)
        for mode in _AUTHORING_MODE_ORDER
    }
    figure = go.Figure()
    figure.add_bar(
        name="No preceding incomplete attempt",
        x=list(_AUTHORING_MODE_ORDER),
        y=[no_preceding_counts[mode] for mode in _AUTHORING_MODE_ORDER],
        hovertemplate=(
            "Final mode: %{x}<br>Completed studies: %{y}<extra>%{fullData.name}</extra>"
        ),
    )
    figure.add_bar(
        name="One or more preceding incomplete attempts",
        x=list(_AUTHORING_MODE_ORDER),
        y=[preceding_counts.get(mode, 0) for mode in _AUTHORING_MODE_ORDER],
        hovertemplate=(
            "Final mode: %{x}<br>Completed studies: %{y}<extra>%{fullData.name}</extra>"
        ),
    )
    figure.update_layout(
        title="Completed-study pathways by final authoring mode",
        template="plotly_white",
        barmode="stack",
        xaxis_title="Final completion authoring mode",
        yaxis_title="Completed study count",
        legend_title_text="Attempt pathway",
    )

    return figure


def build_author_handoff_chart(
    author_handoff_summary: pd.DataFrame,
) -> go.Figure:
    """Return completed-study author-handoff categories by final mode."""
    _require_columns(
        author_handoff_summary,
        required=_REQUIRED_AUTHOR_HANDOFF_COLUMNS,
        frame_name="author_handoff_summary",
    )

    if author_handoff_summary.empty:
        return _empty_figure(
            title="Author handoffs before study completion",
            message="No completed-study author-handoff aggregates are available.",
        )

    grouped = (
        author_handoff_summary.groupby(
            [
                "completed_attempt_authoring_mode",
                "author_handoff_category",
            ],
            sort=True,
            dropna=False,
        )["distinct_completed_study_count"]
        .sum()
        .reset_index()
    )
    figure = go.Figure()

    for category in _AUTHOR_HANDOFF_ORDER:
        category_rows = grouped.loc[grouped["author_handoff_category"].eq(category)]
        values_by_mode: Mapping[str, int] = {
            str(row["completed_attempt_authoring_mode"]): int(
                row["distinct_completed_study_count"]
            )
            for row in category_rows.to_dict(orient="records")
        }
        figure.add_bar(
            name=_AUTHOR_HANDOFF_LABELS[category],
            x=list(_AUTHORING_MODE_ORDER),
            y=[values_by_mode.get(mode, 0) for mode in _AUTHORING_MODE_ORDER],
            hovertemplate=(
                "Final mode: %{x}<br>Completed studies: %{y}"
                "<extra>%{fullData.name}</extra>"
            ),
        )

    figure.update_layout(
        title="Author handoffs before study completion",
        template="plotly_white",
        barmode="stack",
        xaxis_title="Final completion authoring mode",
        yaxis_title="Completed study count",
        legend_title_text="Author pathway",
    )

    return figure


def build_author_attempt_start_experience_chart(
    attempt_start_experience_summary: pd.DataFrame,
) -> go.Figure:
    """Return median prior-study experience at attempt start."""
    _require_columns(
        attempt_start_experience_summary,
        required=_REQUIRED_ATTEMPT_START_EXPERIENCE_COLUMNS,
        frame_name="attempt_start_experience_summary",
    )
    rows = attempt_start_experience_summary.loc[
        attempt_start_experience_summary["author_adoption_group"].eq("ALL_AUTHORS")
        & attempt_start_experience_summary["attempt_completion_group"].eq(_ALL)
        & attempt_start_experience_summary["attempt_authoring_mode"].isin(
            _AUTHORING_MODE_ORDER
        )
        & attempt_start_experience_summary["experience_metric_name"].eq(
            _ATTEMPT_START_EXPERIENCE_METRIC
        )
    ].dropna(subset=["median_author_attempt_value"])

    title = "Median studies created before attempt start"

    if rows.empty:
        return _empty_figure(
            title=title,
            message="No attempt-start author experience aggregates are available.",
        )

    rows_by_mode = {
        str(row["attempt_authoring_mode"]): row
        for row in rows.to_dict(orient="records")
    }
    medians = [
        float(rows_by_mode[mode]["median_author_attempt_value"])
        if mode in rows_by_mode
        else 0.0
        for mode in _AUTHORING_MODE_ORDER
    ]
    observation_counts = [
        int(rows_by_mode[mode]["author_attempt_count_with_nonmissing_metric"])
        if mode in rows_by_mode
        else 0
        for mode in _AUTHORING_MODE_ORDER
    ]
    figure = go.Figure(
        data=[
            go.Bar(
                x=list(_AUTHORING_MODE_ORDER),
                y=medians,
                customdata=[
                    [
                        observation_count,
                        _ATTEMPT_START_EXPERIENCE_DEFINITION,
                    ]
                    for observation_count in observation_counts
                ],
                hovertemplate=(
                    "Attempt authoring mode: %{x}<br>"
                    "Median prior studies: %{y:.2f}<br>"
                    "Author-attempt observations with value: "
                    "%{customdata[0]}<br>"
                    "Unit: studies<br>"
                    "Definition: %{customdata[1]}"
                    "<extra></extra>"
                ),
            )
        ]
    )
    figure.update_layout(
        title=title,
        template="plotly_white",
        xaxis_title="Attempt authoring mode",
        yaxis_title="Median prior studies created",
        showlegend=False,
    )

    return figure


def build_author_experience_chart(
    current_author_experience_summary: pd.DataFrame,
    *,
    metric_unit: str,
) -> go.Figure:
    """Return query-time median author experience for one measurement unit."""
    _require_columns(
        current_author_experience_summary,
        required=_REQUIRED_CURRENT_AUTHOR_EXPERIENCE_COLUMNS,
        frame_name="current_author_experience_summary",
    )
    rows = current_author_experience_summary.loc[
        current_author_experience_summary["experience_metric_unit"].eq(metric_unit)
        & current_author_experience_summary["experience_metric_name"].isin(
            _AUTHOR_EXPERIENCE_METRIC_LABELS
        )
        & current_author_experience_summary["author_adoption_group"].isin(
            _AUTHOR_ADOPTION_GROUP_ORDER
        )
    ].dropna(subset=["median_author_value"])

    unit_label = "Studies" if metric_unit == "studies" else "Days"
    title = f"Median author experience at report query time: {unit_label.lower()}"

    if rows.empty:
        return _empty_figure(
            title=title,
            message=(
                f"No query-time author experience aggregates in {unit_label.lower()} "
                "are available."
            ),
        )

    figure = go.Figure()

    metric_names = tuple(
        str(value) for value in rows["experience_metric_name"].unique()
    )

    for metric_name in metric_names:
        metric_rows = rows.loc[rows["experience_metric_name"].eq(metric_name)]
        medians_by_group: Mapping[str, float] = {
            str(row["author_adoption_group"]): float(row["median_author_value"])
            for row in metric_rows.to_dict(orient="records")
        }
        counts_by_group: Mapping[str, int] = {
            str(row["author_adoption_group"]): int(
                row["author_count_with_nonmissing_metric"]
            )
            for row in metric_rows.to_dict(orient="records")
        }
        figure.add_bar(
            name=_AUTHOR_EXPERIENCE_METRIC_LABELS[metric_name],
            x=[
                _AUTHOR_ADOPTION_GROUP_LABELS[group]
                for group in _AUTHOR_ADOPTION_GROUP_ORDER
            ],
            y=[
                medians_by_group.get(group, 0.0)
                for group in _AUTHOR_ADOPTION_GROUP_ORDER
            ],
            customdata=[
                [
                    counts_by_group.get(group, 0),
                    unit_label.lower(),
                    _AUTHOR_EXPERIENCE_METRIC_DEFINITIONS[metric_name],
                ]
                for group in _AUTHOR_ADOPTION_GROUP_ORDER
            ],
            hovertemplate=(
                "Author adoption group: %{x}<br>"
                "Median: %{y:.2f}<br>"
                "Distinct authors with value: %{customdata[0]}<br>"
                "Unit: %{customdata[1]}<br>"
                "Definition: %{customdata[2]}"
                "<extra>%{fullData.name}</extra>"
            ),
        )

    figure.update_layout(
        title=title,
        template="plotly_white",
        barmode="group",
        xaxis_title="Author adoption group",
        yaxis_title=f"Median {unit_label.lower()}",
        legend_title_text="Query-time experience metric",
    )

    return figure


def build_completed_study_mix_chart(
    grouped_study_summary: pd.DataFrame,
    *,
    dimension_name: str,
    title: str,
) -> go.Figure:
    """Return one mutually exclusive completed-study category mix."""
    _require_columns(
        grouped_study_summary,
        required=_REQUIRED_GROUPED_STUDY_COLUMNS,
        frame_name="grouped_study_summary",
    )
    rows = grouped_study_summary.loc[
        grouped_study_summary["study_population_name"].eq("COMPLETED_STUDIES")
        & grouped_study_summary["final_completion_authoring_mode"].eq(_ALL)
        & grouped_study_summary["grouping_dimension_1_name"].eq(dimension_name)
        & grouped_study_summary["grouping_dimension_2_name"].eq("NONE")
    ].copy()

    if rows.empty:
        return _empty_figure(
            title=title,
            message="No completed-study category aggregates are available.",
        )

    if not rows["group_values_are_mutually_exclusive"].eq(True).all():
        raise ExplorationValidationError(
            f"completed-study chart dimension {dimension_name!r} "
            "must contain mutually exclusive groups"
        )

    rows = rows.sort_values(
        by=[
            "distinct_study_count",
            "grouping_dimension_1_value",
        ],
        ascending=[
            True,
            True,
        ],
        kind="stable",
    )
    values = [str(value) for value in rows["grouping_dimension_1_value"].tolist()]
    counts = [int(value) for value in rows["distinct_study_count"].tolist()]
    percentages = [
        float(value)
        for value in rows["distinct_study_percentage_within_population"].tolist()
    ]
    population_counts = [
        int(value) for value in rows["population_distinct_study_count"].tolist()
    ]
    figure = go.Figure(
        data=[
            go.Bar(
                x=counts,
                y=values,
                orientation="h",
                customdata=[
                    [
                        percentage,
                        population_count,
                    ]
                    for percentage, population_count in zip(
                        percentages,
                        population_counts,
                        strict=True,
                    )
                ],
                hovertemplate=(
                    "Category: %{y}<br>"
                    "Completed studies: %{x}<br>"
                    "Share: %{customdata[0]:.1f}%<br>"
                    "Population: %{customdata[1]}"
                    "<extra></extra>"
                ),
            )
        ]
    )
    category_count = len(rows)
    figure_height = max(420, 34 * category_count + 150)

    figure.update_layout(
        title=title,
        template="plotly_white",
        height=figure_height,
        margin={
            "l": 220,
            "r": 40,
            "t": 80,
            "b": 70,
        },
        xaxis_title="Completed study count",
        yaxis={
            "title": "Category",
            "tickmode": "array",
            "tickvals": values,
            "ticktext": values,
            "automargin": True,
        },
        showlegend=False,
    )

    return figure


def _completion_author_context_label(
    *,
    dimension_name: str,
    value: object,
) -> str:
    """Return one faculty-facing completion-author context label."""
    normalized = str(value)

    if dimension_name == "PI_STATUS":
        return {
            "PI": "PI for this study",
            "NON_PI": "Non-PI for this study",
        }.get(normalized, normalized)

    return normalized


def build_completed_study_author_context_chart(
    completed_study_author_context_summary: pd.DataFrame,
    *,
    dimension_name: str,
    title: str,
) -> go.Figure:
    """Return completed-study counts by mode and completion-author context."""
    _require_columns(
        completed_study_author_context_summary,
        required=_REQUIRED_COMPLETED_STUDY_AUTHOR_CONTEXT_COLUMNS,
        frame_name="completed_study_author_context_summary",
    )
    rows = completed_study_author_context_summary.loc[
        completed_study_author_context_summary["context_dimension_name"].eq(
            dimension_name
        )
        & completed_study_author_context_summary[
            "final_completion_authoring_mode"
        ].isin(_AUTHORING_MODE_ORDER)
    ].copy()

    if rows.empty:
        return _empty_figure(
            title=title,
            message="No completed-study completion-author context is available.",
        )

    context_values = sorted(
        str(value) for value in rows["context_dimension_value"].unique()
    )

    if dimension_name == "PI_STATUS":
        context_values = [
            value for value in ("PI", "NON_PI") if value in context_values
        ]

    figure = go.Figure()

    for context_value in context_values:
        value_rows = rows.loc[
            rows["context_dimension_value"].astype("string").eq(context_value)
        ]
        rows_by_mode = {
            str(row["final_completion_authoring_mode"]): row
            for row in value_rows.to_dict(orient="records")
        }
        counts: list[int] = []
        customdata: list[list[object]] = []

        for mode in _AUTHORING_MODE_ORDER:
            row = rows_by_mode.get(mode)

            if row is None:
                counts.append(0)
                customdata.append([0, 0, 0, 0.0, 0.0, 0])
                continue

            count = int(row["completed_study_count"])
            counts.append(count)
            customdata.append(
                [
                    count,
                    int(row["mode_completed_study_count"]),
                    int(row["all_completed_study_count"]),
                    float(row["completed_study_percentage_within_mode"]),
                    float(row["completed_study_percentage_overall"]),
                    int(row["distinct_completion_author_count"]),
                ]
            )

        label = _completion_author_context_label(
            dimension_name=dimension_name,
            value=context_value,
        )
        context_term = (
            "Completion-author PI status"
            if dimension_name == "PI_STATUS"
            else "Completion-author role"
        )
        figure.add_bar(
            name=label,
            x=counts,
            y=list(_AUTHORING_MODE_ORDER),
            orientation="h",
            customdata=customdata,
            hovertemplate=(
                "Final authoring mode: %{y}<br>"
                f"{context_term}: %{{fullData.name}}<br>"
                "Completed studies: %{x}<br>"
                "Share within mode: %{customdata[0]} of "
                "%{customdata[1]} (%{customdata[3]:.1f}%)<br>"
                "Share of all completed studies: %{customdata[0]} of "
                "%{customdata[2]} (%{customdata[4]:.1f}%)<br>"
                "Distinct completion authors represented: "
                "%{customdata[5]}<br>"
                "Unit: each completed study contributes once<br>"
                "Context source: unique completed attempt<br>"
                "One author may contribute multiple studies and may have "
                "different context across studies"
                "<extra></extra>"
            ),
        )

    figure.update_layout(
        title=title,
        template="plotly_white",
        barmode="stack",
        xaxis_title="Completed study count",
        yaxis_title="Final authoring mode",
        legend_title_text=(
            "PI status for this study"
            if dimension_name == "PI_STATUS"
            else "Completion-author role"
        ),
    )

    return figure


def _grouped_author_rows(
    grouped_author_summary: pd.DataFrame,
    *,
    dimension_name: str,
) -> pd.DataFrame:
    """Return all-author rows for one grouped-author dimension."""
    return grouped_author_summary.loc[
        grouped_author_summary["author_population_name"].eq("ALL_AUTHORS")
        & grouped_author_summary["attempt_completion_group"].eq(_ALL)
        & grouped_author_summary["attempt_authoring_mode"].eq(_ALL)
        & grouped_author_summary["grouping_dimension_name"].eq(dimension_name)
    ].copy()


def _appointment_dimension_label(dimension_name: str) -> str:
    """Return the faculty-facing appointment facet label."""
    if dimension_name.endswith("_SCHOOL"):
        return "Appointment school"

    if dimension_name.endswith("_DEPARTMENT"):
        return "Appointment department"

    if dimension_name.endswith("_TITLE"):
        return "Appointment title"

    raise ExplorationValidationError(
        f"unsupported appointment chart dimension {dimension_name!r}"
    )


def build_author_appointment_context_chart(
    grouped_author_summary: pd.DataFrame,
    *,
    dimension_name: str,
    title: str,
) -> go.Figure:
    """Return one non-mutually-exclusive appointment context chart."""
    _require_columns(
        grouped_author_summary,
        required=_REQUIRED_GROUPED_AUTHOR_COLUMNS,
        frame_name="grouped_author_summary",
    )
    dimension_label = _appointment_dimension_label(dimension_name)
    rows = _grouped_author_rows(
        grouped_author_summary,
        dimension_name=dimension_name,
    )

    if rows.empty:
        return _empty_figure(
            title=title,
            message="No appointment context aggregates are available.",
        )

    if not rows["group_values_are_mutually_exclusive"].eq(False).all():
        raise ExplorationValidationError(
            f"appointment chart dimension {dimension_name!r} "
            "must contain non-mutually-exclusive groups"
        )

    rows = rows.sort_values(
        by=[
            "distinct_author_count",
            "grouping_dimension_value",
        ],
        ascending=[
            True,
            True,
        ],
        kind="stable",
    )
    values = [str(value) for value in rows["grouping_dimension_value"].tolist()]
    figure = go.Figure(
        data=[
            go.Bar(
                x=[int(value) for value in rows["distinct_author_count"].tolist()],
                y=values,
                orientation="h",
                customdata=[
                    int(value)
                    for value in rows["population_distinct_author_count"].tolist()
                ],
                hovertemplate=(
                    f"{dimension_label}: %{{y}}<br>"
                    "Distinct authors represented: %{x}<br>"
                    "Author population: %{customdata}<br>"
                    "Groups may overlap"
                    "<extra></extra>"
                ),
            )
        ]
    )
    category_count = len(rows)
    figure_height = max(420, 34 * category_count + 150)

    figure.update_layout(
        title=title,
        template="plotly_white",
        height=figure_height,
        margin={
            "l": 220,
            "r": 40,
            "t": 80,
            "b": 70,
        },
        xaxis_title="Distinct authors represented",
        yaxis={
            "title": dimension_label,
            "tickmode": "array",
            "tickvals": values,
            "ticktext": values,
            "automargin": True,
        },
        showlegend=False,
    )

    return figure


def _field_label(field_name: object) -> str:
    """Return one faculty-facing field label."""
    normalized = str(field_name)

    return _FIELD_DISPLAY_LABELS.get(
        normalized,
        normalized.replace("_", " ").title(),
    )


def _ordered_field_rows(
    field_adoption_summary: pd.DataFrame,
) -> pd.DataFrame:
    """Return text-field rows in stable report order."""
    rows = field_adoption_summary.loc[
        field_adoption_summary["analysis_type"].isin(
            {
                "TEXT",
                "COMPENSATION",
            }
        )
    ].copy()
    order = {
        field_name: index for index, field_name in enumerate(_FIELD_DISPLAY_LABELS)
    }
    rows["_field_order"] = rows["field_name"].map(order).fillna(len(order))

    return rows.sort_values(
        by=[
            "_field_order",
            "field_name",
        ],
        kind="stable",
    )


def build_field_suggestion_adoption_chart(
    field_adoption_summary: pd.DataFrame,
) -> go.Figure:
    """Return offered and selected completed-AI attempt counts by field."""
    _require_columns(
        field_adoption_summary,
        required=_REQUIRED_FIELD_ADOPTION_COLUMNS,
        frame_name="field_adoption_editing_summary",
    )
    rows = _ordered_field_rows(field_adoption_summary)

    if rows.empty:
        return _empty_figure(
            title="AI suggestion offers and selections by field",
            message="No text-field adoption aggregates are available.",
        )

    field_labels = [_field_label(value) for value in rows["field_name"].tolist()]
    completed_counts = [
        int(value) for value in rows["completed_ai_attempt_count"].tolist()
    ]
    offered_counts = [
        int(value)
        for value in rows["completed_ai_attempt_count_with_suggestion_offered"].tolist()
    ]
    selected_counts = [
        int(value)
        for value in rows[
            "completed_ai_attempt_count_with_suggestion_selected"
        ].tolist()
    ]
    selection_percentages = [
        float(value) if not pd.isna(value) else None
        for value in rows[
            "suggestion_selection_percentage_among_attempts_with_offer"
        ].tolist()
    ]
    customdata = [
        [
            completed_count,
            offered_count,
            selected_count,
            selection_percentage,
        ]
        for (
            completed_count,
            offered_count,
            selected_count,
            selection_percentage,
        ) in zip(
            completed_counts,
            offered_counts,
            selected_counts,
            selection_percentages,
            strict=True,
        )
    ]
    figure = go.Figure()
    figure.add_bar(
        name="Attempts with suggestion offered",
        x=field_labels,
        y=offered_counts,
        customdata=customdata,
        hovertemplate=(
            "Field: %{x}<br>"
            "Completed AI attempts: %{customdata[0]}<br>"
            "Attempts with offer: %{customdata[1]}<br>"
            "Attempts with selection: %{customdata[2]}<br>"
            "Selection among attempts with offer: "
            "%{customdata[3]:.1f}%"
            "<extra>%{fullData.name}</extra>"
        ),
    )
    figure.add_bar(
        name="Attempts with suggestion selected",
        x=field_labels,
        y=selected_counts,
        customdata=customdata,
        hovertemplate=(
            "Field: %{x}<br>"
            "Completed AI attempts: %{customdata[0]}<br>"
            "Attempts with offer: %{customdata[1]}<br>"
            "Attempts with selection: %{customdata[2]}<br>"
            "Selection among attempts with offer: "
            "%{customdata[3]:.1f}%"
            "<extra>%{fullData.name}</extra>"
        ),
    )
    figure.update_layout(
        title="AI suggestion offers and selections by field",
        template="plotly_white",
        barmode="group",
        xaxis_title="Study-posting field",
        yaxis_title="Completed AI attempt count",
        legend_title_text="Adoption stage",
    )

    return figure


def build_field_selected_outcomes_chart(
    field_adoption_summary: pd.DataFrame,
) -> go.Figure:
    """Return selected-suggestion outcome counts by field."""
    _require_columns(
        field_adoption_summary,
        required=_REQUIRED_FIELD_ADOPTION_COLUMNS,
        frame_name="field_adoption_editing_summary",
    )
    rows = _ordered_field_rows(field_adoption_summary)

    if rows.empty:
        return _empty_figure(
            title="Selected AI suggestion outcomes by field",
            message="No text-field editing aggregates are available.",
        )

    field_labels = [_field_label(value) for value in rows["field_name"].tolist()]
    selected_counts = [
        int(value)
        for value in rows[
            "completed_ai_attempt_count_with_suggestion_selected"
        ].tolist()
    ]
    scheme_note = (
        "EXPLORATORY_CHARACTER_RATIO_10_30; edited-unclassified remains "
        "separate from replaced."
    )
    figure = go.Figure()

    for column_name, label in _FIELD_EDIT_OUTCOMES:
        outcome_counts = [int(value) for value in rows[column_name].tolist()]
        customdata = [
            [
                selected_count,
                scheme_note,
            ]
            for selected_count in selected_counts
        ]
        figure.add_bar(
            name=label,
            x=field_labels,
            y=outcome_counts,
            customdata=customdata,
            hovertemplate=(
                "Field: %{x}<br>"
                "Outcome: %{fullData.name}<br>"
                "Completed AI attempts: %{y}<br>"
                "Selected attempts for field: %{customdata[0]}<br>"
                "Edit scheme: %{customdata[1]}"
                "<extra></extra>"
            ),
        )

    figure.update_layout(
        title="Selected AI suggestion outcomes by field",
        template="plotly_white",
        barmode="stack",
        xaxis_title="Study-posting field",
        yaxis_title="Completed AI attempt count",
        legend_title_text="Selected-suggestion outcome",
    )

    return figure


def _suggestion_kind_label(value: object) -> str:
    """Return one faculty-facing suggestion-kind label."""
    text = str(value)
    aliases = {
        "genericCompensation": "Generic compensation",
        "specificCompensation": "Specific compensation",
    }

    return aliases.get(
        text,
        text.replace("_", " ").replace("-", " ").title(),
    )


def _suggestion_group_label(
    *,
    field_name: object,
    suggestion_kind: object,
) -> str:
    """Return one stable field and suggestion-kind label."""
    field_label = _field_label(field_name)
    kind_label = _suggestion_kind_label(suggestion_kind)

    if str(field_name) == str(suggestion_kind):
        return field_label

    return f"{field_label} — {kind_label}"


def _suggestion_kind_rows(
    suggestion_selection_summary: pd.DataFrame,
) -> pd.DataFrame:
    """Return one deduplicated aggregate row per field and kind."""
    ordered = suggestion_selection_summary.sort_values(
        by=[
            "field_name",
            "suggestion_kind",
            "suggestion_index",
        ],
        kind="stable",
    )

    return ordered.drop_duplicates(
        subset=[
            "field_name",
            "suggestion_kind",
        ],
        keep="first",
    )


def build_suggestion_selection_by_kind_chart(
    suggestion_selection_summary: pd.DataFrame,
) -> go.Figure:
    """Return attempt-level suggestion selection by field and kind."""
    _require_columns(
        suggestion_selection_summary,
        required=_REQUIRED_SUGGESTION_SELECTION_COLUMNS,
        frame_name="suggestion_selection_summary",
    )
    rows = _suggestion_kind_rows(suggestion_selection_summary)

    if rows.empty:
        return _empty_figure(
            title="Suggestion selection by field and kind",
            message="No suggestion-selection aggregates are available.",
        )

    labels = [
        _suggestion_group_label(
            field_name=row["field_name"],
            suggestion_kind=row["suggestion_kind"],
        )
        for row in rows.to_dict(orient="records")
    ]
    percentages = [
        float(value) if not pd.isna(value) else None
        for value in rows["attempt_level_selection_percentage"].tolist()
    ]
    customdata = [
        [
            int(attempts_with_offer),
            int(attempts_with_selection),
            int(offered_count),
            int(selected_count),
            (
                float(suggestion_percentage)
                if not pd.isna(suggestion_percentage)
                else None
            ),
        ]
        for (
            attempts_with_offer,
            attempts_with_selection,
            offered_count,
            selected_count,
            suggestion_percentage,
        ) in zip(
            rows["completed_ai_attempt_count_with_at_least_one_suggestion"].tolist(),
            rows["completed_ai_attempt_count_with_selected_suggestion"].tolist(),
            rows["offered_suggestion_count"].tolist(),
            rows["selected_suggestion_count"].tolist(),
            rows["suggestion_level_selection_percentage"].tolist(),
            strict=True,
        )
    ]
    figure = go.Figure(
        data=[
            go.Bar(
                x=labels,
                y=percentages,
                customdata=customdata,
                hovertemplate=(
                    "Field and suggestion kind: %{x}<br>"
                    "Attempt-level selection: %{y:.1f}%<br>"
                    "Attempts with one or more suggestions: "
                    "%{customdata[0]}<br>"
                    "Attempts with a selected suggestion: "
                    "%{customdata[1]}<br>"
                    "Suggestions offered: %{customdata[2]}<br>"
                    "Suggestions selected: %{customdata[3]}<br>"
                    "Suggestion-level selection: "
                    "%{customdata[4]:.1f}%"
                    "<extra></extra>"
                ),
            )
        ]
    )
    figure.update_layout(
        title="Suggestion selection by field and kind",
        template="plotly_white",
        xaxis_title="Study-posting field and suggestion kind",
        yaxis_title="Attempt-level selection percentage",
        showlegend=False,
    )

    return figure


def build_suggestion_selection_by_index_chart(
    suggestion_selection_summary: pd.DataFrame,
) -> go.Figure:
    """Return selection percentages by zero-based suggestion index."""
    _require_columns(
        suggestion_selection_summary,
        required=_REQUIRED_SUGGESTION_SELECTION_COLUMNS,
        frame_name="suggestion_selection_summary",
    )
    rows = suggestion_selection_summary.sort_values(
        by=[
            "field_name",
            "suggestion_kind",
            "suggestion_index",
        ],
        kind="stable",
    )

    if rows.empty:
        return _empty_figure(
            title="Selection by zero-based suggestion index",
            message="No suggestion-index aggregates are available.",
        )

    figure = go.Figure()

    for keys, group in rows.groupby(
        [
            "field_name",
            "suggestion_kind",
        ],
        sort=True,
        dropna=False,
    ):
        field_name, suggestion_kind = keys
        indices = [int(value) for value in group["suggestion_index"].tolist()]
        percentages = [
            float(value) if not pd.isna(value) else None
            for value in group["selection_percentage_at_index"].tolist()
        ]
        customdata = [
            [
                int(offered_count),
                int(selected_count),
            ]
            for offered_count, selected_count in zip(
                group["suggestion_count_at_index"].tolist(),
                group["selected_suggestion_count_at_index"].tolist(),
                strict=True,
            )
        ]
        figure.add_scatter(
            name=_suggestion_group_label(
                field_name=field_name,
                suggestion_kind=suggestion_kind,
            ),
            x=indices,
            y=percentages,
            customdata=customdata,
            mode="lines+markers",
            hovertemplate=(
                "Suggestion group: %{fullData.name}<br>"
                "Zero-based suggestion index: %{x}<br>"
                "Selection at index: %{y:.1f}%<br>"
                "Suggestions offered at index: %{customdata[0]}<br>"
                "Suggestions selected at index: %{customdata[1]}"
                "<extra></extra>"
            ),
        )

    figure.update_layout(
        title="Selection by zero-based suggestion index",
        template="plotly_white",
        xaxis_title="Zero-based suggestion index",
        yaxis_title="Selection percentage at index",
        legend_title_text="Field and suggestion kind",
    )
    figure.update_xaxes(
        dtick=1,
    )

    return figure


def build_readability_change_direction_chart(
    field_readability_change_summary: pd.DataFrame,
) -> go.Figure:
    """Return selected-to-final Flesch-Kincaid direction counts by field."""
    _require_columns(
        field_readability_change_summary,
        required=_REQUIRED_READABILITY_CHANGE_COLUMNS,
        frame_name="field_readability_change_summary",
    )
    rows = field_readability_change_summary.loc[
        field_readability_change_summary["readability_measure_name"].eq(
            _FLESCH_KINCAID_GRADE
        )
    ].copy()

    if rows.empty:
        return _empty_figure(
            title="Selected-to-final Flesch-Kincaid direction by field",
            message="No selected-to-final readability aggregates are available.",
        )

    rows["_field_label"] = rows["field_name"].map(_field_label)
    rows = rows.sort_values(
        by=[
            "_field_label",
        ],
        kind="stable",
    )
    field_labels = rows["_field_label"].astype(str).tolist()
    pair_counts = [
        int(value) for value in rows["paired_selected_final_attempt_count"].tolist()
    ]
    tolerances = [
        float(value) if not pd.isna(value) else None
        for value in rows["unchanged_absolute_tolerance"].tolist()
    ]
    short_text_cautions = [
        bool(value) for value in rows["short_text_readability_caution"].tolist()
    ]
    figure = go.Figure()

    for column_name, label in _READABILITY_DIRECTION_SERIES:
        values = [int(value) for value in rows[column_name].tolist()]
        customdata = [
            [
                pair_count,
                tolerance,
                (
                    "Short-text caution applies"
                    if caution
                    else "Standard interpretation caution applies"
                ),
            ]
            for pair_count, tolerance, caution in zip(
                pair_counts,
                tolerances,
                short_text_cautions,
                strict=True,
            )
        ]
        figure.add_bar(
            name=label,
            x=field_labels,
            y=values,
            customdata=customdata,
            hovertemplate=(
                "Field: %{x}<br>"
                "Direction: %{fullData.name}<br>"
                "Paired selected-final attempts: %{customdata[0]}<br>"
                "Attempts in direction: %{y}<br>"
                "No-material-change tolerance: ±%{customdata[1]}<br>"
                "%{customdata[2]}"
                "<extra></extra>"
            ),
        )

    figure.update_layout(
        title="Selected-to-final Flesch-Kincaid direction by field",
        template="plotly_white",
        barmode="stack",
        xaxis_title="Study-posting field",
        yaxis_title="Paired selected-final attempt count",
        legend_title_text="Final minus selected direction",
    )

    return figure


def build_final_grade_bands_chart(
    field_readability_target_summary: pd.DataFrame,
) -> go.Figure:
    """Return observed final Flesch-Kincaid grade bands by mode and field."""
    _require_columns(
        field_readability_target_summary,
        required=_REQUIRED_READABILITY_TARGET_COLUMNS,
        frame_name="field_readability_target_summary",
    )
    rows = field_readability_target_summary.loc[
        field_readability_target_summary["readability_measure_name"].eq(
            _FLESCH_KINCAID_GRADE
        )
        & field_readability_target_summary["attempt_authoring_mode"].isin(
            _AUTHORING_MODE_ORDER
        )
    ].copy()

    if rows.empty:
        return _empty_figure(
            title="Observed final Flesch-Kincaid grade bands",
            message="No observed final grade-band aggregates are available.",
        )

    rows["_group_label"] = [
        f"{_field_label(field_name)} — {mode}"
        for field_name, mode in zip(
            rows["field_name"],
            rows["attempt_authoring_mode"],
            strict=True,
        )
    ]
    rows = rows.sort_values(
        by=[
            "_group_label",
        ],
        kind="stable",
    )
    group_labels = rows["_group_label"].astype(str).tolist()
    final_counts = [int(value) for value in rows["final_text_attempt_count"].tolist()]
    percentages_at_or_below_8 = [
        float(value) if not pd.isna(value) else None
        for value in rows["percentage_at_or_below_grade_8"].tolist()
    ]
    short_text_cautions = [
        bool(value) for value in rows["short_text_readability_caution"].tolist()
    ]
    interpretation_notes = [
        str(value) for value in rows["target_interpretation_note"].tolist()
    ]
    figure = go.Figure()

    for column_name, label in _GRADE_BAND_SERIES:
        values = [int(value) for value in rows[column_name].tolist()]
        customdata = [
            [
                final_count,
                percentage,
                (
                    "Short-text caution applies"
                    if caution
                    else "Standard interpretation caution applies"
                ),
                note,
            ]
            for final_count, percentage, caution, note in zip(
                final_counts,
                percentages_at_or_below_8,
                short_text_cautions,
                interpretation_notes,
                strict=True,
            )
        ]
        figure.add_bar(
            name=label,
            x=group_labels,
            y=values,
            customdata=customdata,
            hovertemplate=(
                "Field and mode: %{x}<br>"
                "Grade band: %{fullData.name}<br>"
                "Observed nonblank final texts: %{customdata[0]}<br>"
                "Texts in band: %{y}<br>"
                "At or below grade 8: %{customdata[1]:.1f}%<br>"
                "%{customdata[2]}<br>"
                "%{customdata[3]}"
                "<extra></extra>"
            ),
        )

    figure.update_layout(
        title="Observed final Flesch-Kincaid grade bands",
        template="plotly_white",
        barmode="stack",
        xaxis_title="Study-posting field and authoring mode",
        yaxis_title="Observed nonblank final text count",
        legend_title_text="Grade-level indicator band",
    )

    return figure


def build_selected_vs_unselected_readability_chart(
    selected_vs_unselected_summary: pd.DataFrame,
) -> go.Figure:
    """Return selected-minus-mean-unselected Flesch-Kincaid medians."""
    _require_columns(
        selected_vs_unselected_summary,
        required=_REQUIRED_SELECTED_COMPARISON_COLUMNS,
        frame_name="selected_vs_unselected_readability_summary",
    )
    rows = selected_vs_unselected_summary.loc[
        selected_vs_unselected_summary["readability_measure_name"].eq(
            _FLESCH_KINCAID_GRADE
        )
    ].copy()

    if rows.empty:
        return _empty_figure(
            title=("Selected versus mean-unselected Flesch-Kincaid difference"),
            message=(
                "No selected-versus-unselected readability aggregates are available."
            ),
        )

    rows["_field_label"] = rows["field_name"].map(_field_label)
    rows = rows.sort_values(
        by=[
            "_field_label",
        ],
        kind="stable",
    )
    values = [
        float(value)
        for value in rows["median_selected_minus_mean_unselected_value"].tolist()
    ]
    customdata = [
        [
            int(attempt_count),
            int(lower_count),
            int(equal_count),
            int(higher_count),
            float(tolerance),
        ]
        for (
            attempt_count,
            lower_count,
            equal_count,
            higher_count,
            tolerance,
        ) in zip(
            rows[
                "completed_ai_attempt_count_with_selected_and_unselected_suggestions"
            ].tolist(),
            rows["attempt_count_selected_value_lower"].tolist(),
            rows["attempt_count_selected_value_equal_within_tolerance"].tolist(),
            rows["attempt_count_selected_value_higher"].tolist(),
            rows["equality_tolerance"].tolist(),
            strict=True,
        )
    ]
    figure = go.Figure(
        data=[
            go.Bar(
                x=rows["_field_label"].astype(str).tolist(),
                y=values,
                customdata=customdata,
                hovertemplate=(
                    "Field: %{x}<br>"
                    "Median selected minus mean unselected: %{y:.2f}<br>"
                    "Comparable completed AI attempts: "
                    "%{customdata[0]}<br>"
                    "Selected value lower: %{customdata[1]}<br>"
                    "Equal within tolerance: %{customdata[2]}<br>"
                    "Selected value higher: %{customdata[3]}<br>"
                    "Equality tolerance: ±%{customdata[4]}"
                    "<extra></extra>"
                ),
            )
        ]
    )
    figure.add_hline(
        y=0,
        line_dash="dash",
        line_color="#52606d",
    )
    figure.update_layout(
        title=("Selected versus mean-unselected Flesch-Kincaid difference"),
        template="plotly_white",
        xaxis_title="Study-posting field",
        yaxis_title="Median selected minus mean-unselected grade value",
        showlegend=False,
    )

    return figure


def _edit_intensity_group_label(
    *,
    field_name: object,
    edit_intensity_category: object,
    population_count: int,
) -> str:
    """Return one stable field, edit-intensity, and sample-size label."""
    category = str(edit_intensity_category)
    category_label = _EDIT_INTENSITY_LABELS.get(
        category,
        category.replace("_", " ").title(),
    )

    return f"{_field_label(field_name)} — {category_label} (N={population_count})"


def build_edit_readability_relationship_chart(
    field_edit_readability_cross_summary: pd.DataFrame,
) -> go.Figure:
    """Return readability-direction percentages by edit intensity."""
    _require_columns(
        field_edit_readability_cross_summary,
        required=_REQUIRED_EDIT_READABILITY_CROSS_COLUMNS,
        frame_name="field_edit_readability_cross_summary",
    )

    if field_edit_readability_cross_summary.empty:
        return _empty_figure(
            title="Edit intensity and consensus grade-level direction",
            message=(
                "No edit-intensity and readability-direction aggregates are available."
            ),
        )

    rows = field_edit_readability_cross_summary.copy()
    field_order = {
        field_name: index for index, field_name in enumerate(_FIELD_DISPLAY_LABELS)
    }
    intensity_order = {
        category: index for index, category in enumerate(_EDIT_INTENSITY_ORDER)
    }
    rows["_field_order"] = rows["field_name"].map(field_order).fillna(len(field_order))
    rows["_intensity_order"] = (
        rows["edit_intensity_category"]
        .map(intensity_order)
        .fillna(len(intensity_order))
    )
    rows = rows.sort_values(
        by=[
            "_field_order",
            "field_name",
            "_intensity_order",
            "edit_intensity_category",
            "readability_direction_category",
        ],
        kind="stable",
    )

    groups = (
        rows[
            [
                "field_name",
                "edit_intensity_category",
            ]
        ]
        .drop_duplicates()
        .to_dict(orient="records")
    )
    population_by_group = (
        rows.groupby(
            [
                "field_name",
                "edit_intensity_category",
            ],
            sort=False,
            dropna=False,
        )["completed_ai_attempt_count"]
        .first()
        .to_dict()
    )
    group_labels = [
        _edit_intensity_group_label(
            field_name=row["field_name"],
            edit_intensity_category=row["edit_intensity_category"],
            population_count=int(
                population_by_group[
                    (
                        row["field_name"],
                        row["edit_intensity_category"],
                    )
                ]
            ),
        )
        for row in groups
    ]
    rows_by_key = {
        (
            str(row["field_name"]),
            str(row["edit_intensity_category"]),
            str(row["readability_direction_category"]),
        ): row
        for row in rows.to_dict(orient="records")
    }
    figure = go.Figure()

    for direction in _CONSENSUS_DIRECTION_ORDER:
        percentages: list[float] = []
        customdata: list[list[object]] = []

        for group in groups:
            field_name = str(group["field_name"])
            intensity = str(group["edit_intensity_category"])
            row = rows_by_key.get(
                (
                    field_name,
                    intensity,
                    direction,
                )
            )

            if row is None:
                percentages.append(0.0)
                category_rule = _EDIT_INTENSITY_RULES.get(
                    intensity,
                    "See the report's edit-category definitions",
                )
                customdata.append(
                    [
                        _field_label(field_name),
                        _EDIT_INTENSITY_LABELS.get(
                            intensity,
                            intensity.replace("_", " ").title(),
                        ),
                        category_rule,
                        _CONSENSUS_DIRECTION_EXPLANATIONS[direction],
                        0,
                        0,
                        0.0,
                        None,
                        _CONSENSUS_DIRECTION_CAUTIONS[direction],
                    ]
                )
                continue

            percentage = row["percentage_within_edit_intensity_category"]
            percentages.append(float(percentage) if not pd.isna(percentage) else 0.0)
            population_count = int(row["completed_ai_attempt_count"])
            direction_count = int(
                row["completed_ai_attempt_count_with_selected_final_pair"]
            )
            customdata.append(
                [
                    _field_label(field_name),
                    _EDIT_INTENSITY_LABELS.get(
                        intensity,
                        intensity.replace("_", " ").title(),
                    ),
                    _EDIT_INTENSITY_RULES.get(
                        intensity,
                        "See the report's edit-category definitions",
                    ),
                    _CONSENSUS_DIRECTION_EXPLANATIONS[direction],
                    population_count,
                    direction_count,
                    (float(percentage) if not pd.isna(percentage) else None),
                    (
                        float(
                            row[
                                "median_flesch_kincaid_grade_change_"
                                "final_minus_selected"
                            ]
                        )
                        if not pd.isna(
                            row[
                                "median_flesch_kincaid_grade_change_"
                                "final_minus_selected"
                            ]
                        )
                        else None
                    ),
                    _CONSENSUS_DIRECTION_CAUTIONS[direction],
                ]
            )

        figure.add_bar(
            name=_CONSENSUS_DIRECTION_LABELS[direction],
            x=group_labels,
            y=percentages,
            customdata=customdata,
            hovertemplate=(
                "Field: %{customdata[0]}<br>"
                "Edit category: %{customdata[1]}<br>"
                "Edit rule: %{customdata[2]}<br>"
                "<br>"
                "Readability result: %{customdata[3]}<br>"
                "Fields in this group: %{customdata[4]}<br>"
                "Fields with this result: %{customdata[5]}<br>"
                "Share of this group: %{customdata[6]:.1f}% "
                "(%{customdata[5]} of %{customdata[4]})<br>"
                "<br>"
                "Median Flesch-Kincaid change: "
                "%{customdata[7]:.2f} grade levels<br>"
                "Calculation: final text minus selected suggestion<br>"
                "Interpretation: %{customdata[8]}"
                "<extra></extra>"
            ),
        )

    figure.update_layout(
        title="Edit intensity and consensus grade-level direction",
        template="plotly_white",
        barmode="stack",
        xaxis_title="Study-posting field and edit-intensity category",
        yaxis_title="Percentage within edit-intensity category",
        legend_title_text="Consensus grade-level direction",
    )

    return figure


def build_content_source_concordance_chart(
    content_source_matrix: pd.DataFrame,
) -> go.Figure:
    """Return an all-attempt reported-versus-inferred heatmap."""
    _require_columns(
        content_source_matrix,
        required=_REQUIRED_CONTENT_SOURCE_COLUMNS,
        frame_name="content_source_concordance_matrix",
    )
    rows = content_source_matrix.loc[
        content_source_matrix["attempt_completion_group"].eq(_ALL)
    ]

    if rows.empty:
        return _empty_figure(
            title="Reported versus inferred content source",
            message="No comparable content-source aggregates are available.",
        )

    reported_values = sorted(
        str(value) for value in rows["reported_study_content_source"].unique()
    )
    inferred_values = sorted(
        str(value) for value in rows["inferred_study_content_source"].unique()
    )
    counts = {
        (
            str(row["reported_study_content_source"]),
            str(row["inferred_study_content_source"]),
        ): int(row["ai_attempt_count"])
        for row in rows.to_dict(orient="records")
    }
    matrix = [
        [
            counts.get(
                (
                    reported,
                    inferred,
                ),
                0,
            )
            for inferred in inferred_values
        ]
        for reported in reported_values
    ]
    figure = go.Figure(
        data=[
            go.Heatmap(
                x=inferred_values,
                y=reported_values,
                z=matrix,
                colorbar={"title": "AI attempts"},
                hovertemplate=(
                    "Reported: %{y}<br>"
                    "Inferred: %{x}<br>"
                    "AI attempts: %{z}<extra></extra>"
                ),
            )
        ]
    )
    figure.update_layout(
        title="Reported versus inferred content source",
        template="plotly_white",
        xaxis_title="Inferred content source",
        yaxis_title="Reported content source",
    )

    return figure


def build_exploration_charts(
    inputs: ExplorationChartInputs,
) -> ExplorationCharts:
    """Return all aggregate-only exploration figures."""
    return ExplorationCharts(
        attempt_outcomes_by_mode=build_attempt_outcomes_chart(inputs.overview_summary),
        attempt_timing_distribution_by_mode=build_attempt_timing_chart(
            inputs.grouped_attempt_summary
        ),
        study_completion_pathways=build_study_completion_pathways_chart(
            inputs.study_attempt_history_summary
        ),
        author_handoff_categories=build_author_handoff_chart(
            inputs.author_handoff_summary
        ),
        author_attempt_start_experience=(
            build_author_attempt_start_experience_chart(
                inputs.attempt_start_experience_summary
            )
        ),
        author_experience_studies=build_author_experience_chart(
            inputs.current_author_experience_summary,
            metric_unit="studies",
        ),
        author_experience_days=build_author_experience_chart(
            inputs.current_author_experience_summary,
            metric_unit="days",
        ),
        completed_study_participant_mix=build_completed_study_mix_chart(
            inputs.grouped_study_summary,
            dimension_name="STUDY_PARTICIPANT_TYPE",
            title="Completed studies by participant type",
        ),
        completed_study_department_mix=build_completed_study_mix_chart(
            inputs.grouped_study_summary,
            dimension_name="STUDY_DEPARTMENT",
            title="Completed studies by department",
        ),
        completed_studies_by_completion_author_role=(
            build_completed_study_author_context_chart(
                inputs.completed_study_author_context_summary,
                dimension_name="EFFECTIVE_ROLE",
                title=(
                    "Completed studies by authoring mode and completion-author role"
                ),
            )
        ),
        completed_studies_by_completion_author_pi_status=(
            build_completed_study_author_context_chart(
                inputs.completed_study_author_context_summary,
                dimension_name="PI_STATUS",
                title=(
                    "Completed studies by authoring mode and "
                    "completion-author PI status"
                ),
            )
        ),
        author_appointment_schools=build_author_appointment_context_chart(
            inputs.grouped_author_summary,
            dimension_name="AUTHOR_APPOINTMENT_SCHOOL",
            title="Author appointment schools",
        ),
        pi_appointment_schools=build_author_appointment_context_chart(
            inputs.grouped_author_summary,
            dimension_name="PI_APPOINTMENT_SCHOOL",
            title="Principal-investigator appointment schools",
        ),
        author_appointment_departments=build_author_appointment_context_chart(
            inputs.grouped_author_summary,
            dimension_name="AUTHOR_APPOINTMENT_DEPARTMENT",
            title="Author appointment departments",
        ),
        pi_appointment_departments=build_author_appointment_context_chart(
            inputs.grouped_author_summary,
            dimension_name="PI_APPOINTMENT_DEPARTMENT",
            title="Principal-investigator appointment departments",
        ),
        author_appointment_titles=build_author_appointment_context_chart(
            inputs.grouped_author_summary,
            dimension_name="AUTHOR_APPOINTMENT_TITLE",
            title="Author appointment titles",
        ),
        pi_appointment_titles=build_author_appointment_context_chart(
            inputs.grouped_author_summary,
            dimension_name="PI_APPOINTMENT_TITLE",
            title="Principal-investigator appointment titles",
        ),
        field_suggestion_adoption=build_field_suggestion_adoption_chart(
            inputs.field_adoption_editing_summary
        ),
        field_selected_outcomes=build_field_selected_outcomes_chart(
            inputs.field_adoption_editing_summary
        ),
        suggestion_selection_by_kind=(
            build_suggestion_selection_by_kind_chart(
                inputs.suggestion_selection_summary
            )
        ),
        suggestion_selection_by_index=(
            build_suggestion_selection_by_index_chart(
                inputs.suggestion_selection_summary
            )
        ),
        readability_change_direction=build_readability_change_direction_chart(
            inputs.field_readability_change_summary
        ),
        final_grade_bands=build_final_grade_bands_chart(
            inputs.field_readability_target_summary
        ),
        selected_vs_unselected_readability=(
            build_selected_vs_unselected_readability_chart(
                inputs.selected_vs_unselected_readability_summary
            )
        ),
        edit_readability_relationship=(
            build_edit_readability_relationship_chart(
                inputs.field_edit_readability_cross_summary
            )
        ),
        content_source_concordance=build_content_source_concordance_chart(
            inputs.content_source_matrix
        ),
    )
