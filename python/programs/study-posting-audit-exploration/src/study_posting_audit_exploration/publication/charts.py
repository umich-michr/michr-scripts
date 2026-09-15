"""Aggregate-only Plotly chart construction."""

from collections.abc import Mapping
from dataclasses import dataclass

import pandas as pd
import plotly.graph_objects as go

from study_posting_audit_exploration.errors import ExplorationValidationError

_ALL = "ALL"

_REQUIRED_ATTEMPT_COLUMNS: tuple[str, ...] = (
    "attempt_result",
    "attempt_authoring_mode",
    "grouping_dimension_1_name",
    "grouping_dimension_2_name",
    "attempt_count",
    "median_total_attempt_minutes",
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
    "median_minutes_first_attempt_to_completion",
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

_ATTEMPT_RESULT_ORDER: tuple[str, ...] = (
    "COMPLETE",
    "AI_ERROR",
    "AI_ERROR_WITHOUT_STACK_TRACE",
    "USER_DROPPED",
    "OTHER_INCOMPLETE_RESULT",
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


@dataclass(frozen=True, slots=True)
class ExplorationCharts:
    """Aggregate-only figures for the HTML report."""

    attempt_outcomes_by_mode: go.Figure
    median_attempt_time_by_mode: go.Figure
    study_completion_pathways: go.Figure
    author_handoff_categories: go.Figure
    author_attempt_start_experience: go.Figure
    author_experience_studies: go.Figure
    author_experience_days: go.Figure
    completed_study_participant_mix: go.Figure
    completed_study_department_mix: go.Figure
    effective_author_roles: go.Figure
    author_pi_context: go.Figure
    author_appointment_schools: go.Figure
    pi_appointment_schools: go.Figure
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


def build_attempt_outcomes_chart(
    grouped_attempt_summary: pd.DataFrame,
) -> go.Figure:
    """Return stacked attempt-result counts by authoring mode."""
    _require_columns(
        grouped_attempt_summary,
        required=_REQUIRED_ATTEMPT_COLUMNS,
        frame_name="grouped_attempt_summary",
    )
    rows = grouped_attempt_summary.loc[
        grouped_attempt_summary["grouping_dimension_1_name"].eq("ATTEMPT_RESULT")
        & grouped_attempt_summary["grouping_dimension_2_name"].eq("AUTHORING_MODE")
        & grouped_attempt_summary["attempt_result"].ne(_ALL)
        & grouped_attempt_summary["attempt_authoring_mode"].ne(_ALL)
    ]

    if rows.empty:
        return _empty_figure(
            title="Attempt outcomes by authoring mode",
            message="No attempt outcome aggregates are available.",
        )

    figure = go.Figure()

    for result in _ATTEMPT_RESULT_ORDER:
        result_rows = rows.loc[rows["attempt_result"].eq(result)]
        values_by_mode: Mapping[str, int] = {
            str(row["attempt_authoring_mode"]): int(row["attempt_count"])
            for row in result_rows.to_dict(orient="records")
        }
        figure.add_bar(
            name=result.replace("_", " ").title(),
            x=list(_AUTHORING_MODE_ORDER),
            y=[values_by_mode.get(mode, 0) for mode in _AUTHORING_MODE_ORDER],
            hovertemplate=(
                "Mode: %{x}<br>Attempts: %{y}<extra>%{fullData.name}</extra>"
            ),
        )

    figure.update_layout(
        title="Attempt outcomes by authoring mode",
        template="plotly_white",
        barmode="stack",
        xaxis_title="Authoring mode",
        yaxis_title="Attempt count",
        legend_title_text="Attempt result",
    )

    return figure


def build_attempt_timing_chart(
    grouped_attempt_summary: pd.DataFrame,
) -> go.Figure:
    """Return median total attempt time by authoring mode."""
    _require_columns(
        grouped_attempt_summary,
        required=_REQUIRED_ATTEMPT_COLUMNS,
        frame_name="grouped_attempt_summary",
    )
    rows = grouped_attempt_summary.loc[
        grouped_attempt_summary["grouping_dimension_1_name"].eq("AUTHORING_MODE")
        & grouped_attempt_summary["attempt_authoring_mode"].ne(_ALL)
    ]
    rows = rows.dropna(subset=["median_total_attempt_minutes"])

    if rows.empty:
        return _empty_figure(
            title="Median total attempt time by authoring mode",
            message="No attempt timing aggregates are available.",
        )

    values_by_mode: Mapping[str, float] = {
        str(row["attempt_authoring_mode"]): float(row["median_total_attempt_minutes"])
        for row in rows.to_dict(orient="records")
    }
    figure = go.Figure(
        data=[
            go.Bar(
                x=list(_AUTHORING_MODE_ORDER),
                y=[values_by_mode.get(mode, 0.0) for mode in _AUTHORING_MODE_ORDER],
                hovertemplate=("Mode: %{x}<br>Median minutes: %{y:.2f}<extra></extra>"),
            )
        ]
    )
    figure.update_layout(
        title="Median total attempt time by authoring mode",
        template="plotly_white",
        xaxis_title="Authoring mode",
        yaxis_title="Median total attempt minutes",
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
    figure.update_layout(
        title=title,
        template="plotly_white",
        xaxis_title="Completed study count",
        yaxis_title="Category",
        showlegend=False,
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


def build_effective_author_role_chart(
    grouped_author_summary: pd.DataFrame,
) -> go.Figure:
    """Return mutually exclusive effective author-role counts."""
    _require_columns(
        grouped_author_summary,
        required=_REQUIRED_GROUPED_AUTHOR_COLUMNS,
        frame_name="grouped_author_summary",
    )
    rows = _grouped_author_rows(
        grouped_author_summary,
        dimension_name="EFFECTIVE_AUTHOR_ROLE",
    )

    if rows.empty:
        return _empty_figure(
            title="Distinct authors by effective role",
            message="No effective author-role aggregates are available.",
        )

    if not rows["group_values_are_mutually_exclusive"].eq(True).all():
        raise ExplorationValidationError(
            "effective author-role groups must be mutually exclusive"
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
    figure = go.Figure(
        data=[
            go.Bar(
                x=[int(value) for value in rows["distinct_author_count"].tolist()],
                y=[str(value) for value in rows["grouping_dimension_value"].tolist()],
                orientation="h",
                customdata=[
                    [
                        float(percentage),
                        int(population_count),
                    ]
                    for percentage, population_count in zip(
                        rows["distinct_author_percentage_within_population"].tolist(),
                        rows["population_distinct_author_count"].tolist(),
                        strict=True,
                    )
                ],
                hovertemplate=(
                    "Effective role: %{y}<br>"
                    "Distinct authors: %{x}<br>"
                    "Share: %{customdata[0]:.1f}%<br>"
                    "Author population: %{customdata[1]}"
                    "<extra></extra>"
                ),
            )
        ]
    )
    figure.update_layout(
        title="Distinct authors by effective role",
        template="plotly_white",
        xaxis_title="Distinct author count",
        yaxis_title="Effective author role",
        showlegend=False,
    )

    return figure


def build_author_pi_context_chart(
    grouped_author_summary: pd.DataFrame,
) -> go.Figure:
    """Return author-level principal-investigator classification counts."""
    _require_columns(
        grouped_author_summary,
        required=_REQUIRED_GROUPED_AUTHOR_COLUMNS,
        frame_name="grouped_author_summary",
    )
    rows = _grouped_author_rows(
        grouped_author_summary,
        dimension_name="ALL",
    )
    rows = rows.loc[rows["grouping_dimension_value"].eq(_ALL)]

    if rows.empty:
        return _empty_figure(
            title="Authors classified as study principal investigators",
            message="No author principal-investigator aggregates are available.",
        )

    if len(rows) != 1:
        raise ExplorationValidationError(
            "author principal-investigator context requires exactly one "
            "all-author aggregate row"
        )

    row = rows.iloc[0]
    population_count = int(row["population_distinct_author_count"])
    pi_count = int(row["distinct_author_count_classified_as_pi"])

    if population_count < 0:
        raise ExplorationValidationError(
            "all-author population count must be nonnegative"
        )

    if pi_count < 0 or pi_count > population_count:
        raise ExplorationValidationError(
            "authors classified as principal investigators must be between "
            "zero and the all-author population count"
        )

    non_pi_count = population_count - pi_count
    figure = go.Figure(
        data=[
            go.Bar(
                x=[
                    "Classified as PI",
                    "Not classified as PI",
                ],
                y=[
                    pi_count,
                    non_pi_count,
                ],
                customdata=[
                    population_count,
                    population_count,
                ],
                hovertemplate=(
                    "Classification: %{x}<br>"
                    "Distinct authors: %{y}<br>"
                    "Author population: %{customdata}"
                    "<extra></extra>"
                ),
            )
        ]
    )
    figure.update_layout(
        title="Authors classified as study principal investigators",
        template="plotly_white",
        xaxis_title="Author-level classification",
        yaxis_title="Distinct author count",
        showlegend=False,
    )

    return figure


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
    figure = go.Figure(
        data=[
            go.Bar(
                x=[int(value) for value in rows["distinct_author_count"].tolist()],
                y=[str(value) for value in rows["grouping_dimension_value"].tolist()],
                orientation="h",
                customdata=[
                    int(value)
                    for value in rows["population_distinct_author_count"].tolist()
                ],
                hovertemplate=(
                    "Appointment school: %{y}<br>"
                    "Distinct authors represented: %{x}<br>"
                    "Author population: %{customdata}<br>"
                    "Groups may overlap"
                    "<extra></extra>"
                ),
            )
        ]
    )
    figure.update_layout(
        title=title,
        template="plotly_white",
        xaxis_title="Distinct authors represented",
        yaxis_title="Appointment school",
        showlegend=False,
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
    *,
    grouped_attempt_summary: pd.DataFrame,
    study_attempt_history_summary: pd.DataFrame,
    author_handoff_summary: pd.DataFrame,
    attempt_start_experience_summary: pd.DataFrame,
    current_author_experience_summary: pd.DataFrame,
    grouped_study_summary: pd.DataFrame,
    grouped_author_summary: pd.DataFrame,
    content_source_matrix: pd.DataFrame,
) -> ExplorationCharts:
    """Return all aggregate-only exploration figures."""
    return ExplorationCharts(
        attempt_outcomes_by_mode=build_attempt_outcomes_chart(grouped_attempt_summary),
        median_attempt_time_by_mode=build_attempt_timing_chart(grouped_attempt_summary),
        study_completion_pathways=build_study_completion_pathways_chart(
            study_attempt_history_summary
        ),
        author_handoff_categories=build_author_handoff_chart(author_handoff_summary),
        author_attempt_start_experience=(
            build_author_attempt_start_experience_chart(
                attempt_start_experience_summary
            )
        ),
        author_experience_studies=build_author_experience_chart(
            current_author_experience_summary,
            metric_unit="studies",
        ),
        author_experience_days=build_author_experience_chart(
            current_author_experience_summary,
            metric_unit="days",
        ),
        completed_study_participant_mix=build_completed_study_mix_chart(
            grouped_study_summary,
            dimension_name="STUDY_PARTICIPANT_TYPE",
            title="Completed studies by participant type",
        ),
        completed_study_department_mix=build_completed_study_mix_chart(
            grouped_study_summary,
            dimension_name="STUDY_DEPARTMENT",
            title="Completed studies by department",
        ),
        effective_author_roles=build_effective_author_role_chart(
            grouped_author_summary
        ),
        author_pi_context=build_author_pi_context_chart(grouped_author_summary),
        author_appointment_schools=build_author_appointment_context_chart(
            grouped_author_summary,
            dimension_name="AUTHOR_APPOINTMENT_SCHOOL",
            title="Author appointment schools",
        ),
        pi_appointment_schools=build_author_appointment_context_chart(
            grouped_author_summary,
            dimension_name="PI_APPOINTMENT_SCHOOL",
            title="Principal-investigator appointment schools",
        ),
        content_source_concordance=(
            build_content_source_concordance_chart(content_source_matrix)
        ),
    )
