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


@dataclass(frozen=True, slots=True)
class ExplorationCharts:
    """Initial aggregate-only figures for the HTML report."""

    attempt_outcomes_by_mode: go.Figure
    median_attempt_time_by_mode: go.Figure
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
    content_source_matrix: pd.DataFrame,
) -> ExplorationCharts:
    """Return all initial aggregate-only exploration figures."""
    return ExplorationCharts(
        attempt_outcomes_by_mode=build_attempt_outcomes_chart(grouped_attempt_summary),
        median_attempt_time_by_mode=build_attempt_timing_chart(grouped_attempt_summary),
        content_source_concordance=(
            build_content_source_concordance_chart(content_source_matrix)
        ),
    )
