from pathlib import Path

import pandas as pd
import pytest

from study_posting_audit_exploration import ExplorationInputError
from study_posting_audit_exploration.publication import (
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


def charts() -> object:
    """Return synthetic aggregate-only chart bundle."""
    return build_exploration_charts(
        grouped_attempt_summary=attempt_rows(),
        content_source_matrix=content_rows(),
    )


def test_html_report_is_self_contained_and_accessible() -> None:
    html = render_html_report(
        overview_summary=overview_rows(),
        charts=charts(),  # type: ignore[arg-type]
    )
    normalized_html = " ".join(html.split())

    assert html.startswith("<!doctype html>")
    assert '<html lang="en">' in html
    assert "<h1>Study Posting Audit Exploration</h1>" in html
    assert 'id="executive-overview-heading"' in html
    assert "Distinct studies" in html
    assert "10" in html
    assert "plotly.js" in html.lower()
    assert 'src="https://cdn.plot.ly' not in html
    assert "These descriptive results do not" in normalized_html
    assert "establish causality and must not be" in normalized_html
    assert "Readability formulas are indicators only" in normalized_html


def test_html_report_excludes_identifier_and_payload_values() -> None:
    html = render_html_report(
        overview_summary=overview_rows(),
        charts=charts(),  # type: ignore[arg-type]
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
        charts=charts(),  # type: ignore[arg-type]
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
            charts=charts(),  # type: ignore[arg-type]
        )
