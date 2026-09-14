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

_REQUIRED_CURRENT_AUTHOR_EXPERIENCE_COLUMNS: tuple[str, ...] = (
    "author_adoption_group",
    "experience_metric_name",
    "experience_metric_unit",
    "author_count_with_nonmissing_metric",
    "median_author_value",
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


@dataclass(frozen=True, slots=True)
class ExplorationCharts:
    """Aggregate-only figures for the HTML report."""

    attempt_outcomes_by_mode: go.Figure
    median_attempt_time_by_mode: go.Figure
    study_completion_pathways: go.Figure
    author_handoff_categories: go.Figure
    author_experience_studies: go.Figure
    author_experience_days: go.Figure
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
                counts_by_group.get(group, 0) for group in _AUTHOR_ADOPTION_GROUP_ORDER
            ],
            hovertemplate=(
                "Adoption group: %{x}<br>"
                "Median: %{y:.2f}<br>"
                "Authors with value: %{customdata}"
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
    current_author_experience_summary: pd.DataFrame,
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
        author_experience_studies=build_author_experience_chart(
            current_author_experience_summary,
            metric_unit="studies",
        ),
        author_experience_days=build_author_experience_chart(
            current_author_experience_summary,
            metric_unit="days",
        ),
        content_source_concordance=(
            build_content_source_concordance_chart(content_source_matrix)
        ),
    )
