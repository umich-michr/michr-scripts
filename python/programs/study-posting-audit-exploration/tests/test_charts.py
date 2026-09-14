from collections.abc import Callable

import pandas as pd
import plotly.graph_objects as go
import pytest

from study_posting_audit_exploration import (
    ExplorationValidationError,
)
from study_posting_audit_exploration.publication import (
    ExplorationCharts,
    build_attempt_outcomes_chart,
    build_attempt_timing_chart,
    build_author_experience_chart,
    build_author_handoff_chart,
    build_content_source_concordance_chart,
    build_exploration_charts,
    build_study_completion_pathways_chart,
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
                "median_total_attempt_minutes": 3.0,
            },
            {
                "attempt_result": "USER_DROPPED",
                "attempt_authoring_mode": "AI",
                "grouping_dimension_1_name": "ATTEMPT_RESULT",
                "grouping_dimension_2_name": "AUTHORING_MODE",
                "attempt_count": 2,
                "median_total_attempt_minutes": 1.0,
            },
            {
                "attempt_result": "COMPLETE",
                "attempt_authoring_mode": "MANUAL",
                "grouping_dimension_1_name": "ATTEMPT_RESULT",
                "grouping_dimension_2_name": "AUTHORING_MODE",
                "attempt_count": 3,
                "median_total_attempt_minutes": 5.0,
            },
            {
                "attempt_result": "ALL",
                "attempt_authoring_mode": "AI",
                "grouping_dimension_1_name": "AUTHORING_MODE",
                "grouping_dimension_2_name": "NONE",
                "attempt_count": 6,
                "median_total_attempt_minutes": 2.5,
            },
            {
                "attempt_result": "ALL",
                "attempt_authoring_mode": "MANUAL",
                "grouping_dimension_1_name": "AUTHORING_MODE",
                "grouping_dimension_2_name": "NONE",
                "attempt_count": 3,
                "median_total_attempt_minutes": 5.0,
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
            "median_minutes_first_attempt_to_completion": 20.0,
        },
        {
            "final_completion_authoring_mode": "AI",
            "distinct_study_count": 6,
            "study_count_with_preceding_incomplete_attempts": 2,
            "median_minutes_first_attempt_to_completion": 15.0,
        },
        {
            "final_completion_authoring_mode": "MANUAL",
            "distinct_study_count": 4,
            "study_count_with_preceding_incomplete_attempts": 2,
            "median_minutes_first_attempt_to_completion": 30.0,
        },
        {
            "final_completion_authoring_mode": "NOT_COMPLETED",
            "distinct_study_count": 2,
            "study_count_with_preceding_incomplete_attempts": 2,
            "median_minutes_first_attempt_to_completion": None,
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


def test_attempt_outcomes_chart_uses_aggregate_counts() -> None:
    figure = build_attempt_outcomes_chart(grouped_attempt_rows())

    assert figure.layout.title.text == "Attempt outcomes by authoring mode"
    assert figure.layout.barmode == "stack"
    assert list(figure.data[0].x) == ["AI", "MANUAL"]
    assert list(figure.data[0].y) == [4, 3]


def test_attempt_timing_chart_uses_authoring_mode_medians() -> None:
    figure = build_attempt_timing_chart(grouped_attempt_rows())

    assert figure.layout.title.text == "Median total attempt time by authoring mode"
    assert list(figure.data[0].x) == ["AI", "MANUAL"]
    assert list(figure.data[0].y) == [2.5, 5.0]


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


def test_content_source_chart_uses_all_attempt_population() -> None:
    figure = build_content_source_concordance_chart(content_source_rows())
    heatmap = figure.data[0]

    assert figure.layout.title.text == "Reported versus inferred content source"
    assert list(heatmap.x) == ["other", "registry"]
    assert list(heatmap.y) == ["registry"]
    assert [list(row) for row in heatmap.z] == [[1, 3]]


def test_chart_bundle_contains_all_figures() -> None:
    charts = build_exploration_charts(
        grouped_attempt_summary=grouped_attempt_rows(),
        study_attempt_history_summary=study_history_rows(),
        author_handoff_summary=author_handoff_rows(),
        current_author_experience_summary=current_author_experience_rows(),
        content_source_matrix=content_source_rows(),
    )

    assert isinstance(charts, ExplorationCharts)
    assert charts.attempt_outcomes_by_mode.data
    assert charts.median_attempt_time_by_mode.data
    assert charts.study_completion_pathways.data
    assert charts.author_handoff_categories.data
    assert charts.author_experience_studies.data
    assert charts.author_experience_days.data
    assert charts.content_source_concordance.data


def test_charts_return_accessible_empty_states() -> None:
    attempt_columns = grouped_attempt_rows().columns
    study_columns = study_history_rows().columns
    handoff_columns = author_handoff_rows().columns
    experience_columns = current_author_experience_rows().columns
    content_columns = content_source_rows().columns

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

    assert attempt_figure.layout.annotations[0].text
    assert study_figure.layout.annotations[0].text
    assert handoff_figure.layout.annotations[0].text
    assert experience_figure.layout.annotations[0].text
    assert content_figure.layout.annotations[0].text


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
