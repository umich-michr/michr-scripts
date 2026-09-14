from pathlib import Path

import pandas as pd
import pytest

from study_posting_audit_exploration import ExplorationInputError
from study_posting_audit_exploration.publication import (
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
                "median_total_attempt_minutes": 3.0,
            },
            {
                "attempt_result": "ALL",
                "attempt_authoring_mode": "AI",
                "grouping_dimension_1_name": "AUTHORING_MODE",
                "grouping_dimension_2_name": "NONE",
                "attempt_count": 4,
                "median_total_attempt_minutes": 3.0,
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
                "median_minutes_first_attempt_to_completion": 12.0,
            },
            {
                "final_completion_authoring_mode": "MANUAL",
                "distinct_study_count": 3,
                "study_count_with_preceding_incomplete_attempts": 2,
                "median_minutes_first_attempt_to_completion": 18.0,
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


def charts() -> ExplorationCharts:
    """Return synthetic aggregate-only chart bundle."""
    return build_exploration_charts(
        grouped_attempt_summary=attempt_rows(),
        study_attempt_history_summary=study_history_rows(),
        author_handoff_summary=author_handoff_rows(),
        current_author_experience_summary=current_author_experience_rows(),
        grouped_study_summary=grouped_study_rows(),
        content_source_matrix=content_rows(),
    )


def test_html_report_is_self_contained_and_accessible() -> None:
    html = render_html_report(
        overview_summary=overview_rows(),
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
    assert "Median author experience at report query time: studies" in html
    assert "Median author experience at report query time: days" in html
    assert "They are not attempt-time snapshots" in normalized_html

    assert 'id="study-mix-heading"' in html
    assert "Participant and department mix" in html
    assert "Completed studies by participant type" in html
    assert "Completed studies by department" in html
    assert "Other and missing categories are retained" in normalized_html


def test_html_report_excludes_identifier_and_payload_values() -> None:
    html = render_html_report(
        overview_summary=overview_rows(),
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
            charts=charts(),
        )
