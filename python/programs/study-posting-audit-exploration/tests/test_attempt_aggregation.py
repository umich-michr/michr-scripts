from pathlib import Path

import pandas as pd
import pytest

from study_posting_audit_exploration import (
    ExplorationInputConfig,
    build_grouped_attempt_summary,
    derive_attempt_histories,
    load_audit_report,
)


def attempts_for(path: Path) -> pd.DataFrame:
    """Return derived attempt rows for one synthetic report."""
    report = load_audit_report(
        ExplorationInputConfig(
            report_directory=path,
        )
    )

    return derive_attempt_histories(report.records).study_attempt_author_history


def summary_row(
    summary: pd.DataFrame,
    *,
    dimension_1_name: str,
    dimension_1_value: str,
    dimension_2_name: str = "NONE",
    dimension_2_value: str = "NONE",
) -> pd.Series:
    """Return one grouped-attempt summary row."""
    return summary.loc[
        summary["grouping_dimension_1_name"].eq(dimension_1_name)
        & summary["grouping_dimension_1_value"].eq(dimension_1_value)
        & summary["grouping_dimension_2_name"].eq(dimension_2_name)
        & summary["grouping_dimension_2_value"].eq(dimension_2_value)
    ].iloc[0]


def test_grouped_attempt_summary_reports_counts_and_timing(
    valid_report_directory: Path,
) -> None:
    attempts = attempts_for(valid_report_directory)
    attempts["source_type"] = pd.Series(
        ["SYNTHETIC_TEXT", "SYNTHETIC_TEXT"],
        dtype="string",
    )
    attempts["study_content_source"] = pd.Series(
        ["Synthetic source", "Synthetic source"],
        dtype="string",
    )

    summary = build_grouped_attempt_summary(attempts)

    overall = summary_row(
        summary,
        dimension_1_name="ALL",
        dimension_1_value="ALL",
    )
    assert overall["attempt_count"] == 2
    assert overall["population_attempt_count"] == 2
    assert overall["attempt_percentage_within_population"] == 100.0
    assert overall["attempt_count_with_nonmissing_study_info_page_time"] == 2
    assert overall["median_study_info_page_minutes"] == pytest.approx(1.0 / 60.0)
    assert overall["attempt_count_with_nonmissing_total_attempt_time"] == 1
    assert overall["attempt_count_missing_total_attempt_time"] == 1
    assert overall["median_total_attempt_minutes"] == pytest.approx(1.0)

    complete = summary_row(
        summary,
        dimension_1_name="COMPLETION_GROUP",
        dimension_1_value="COMPLETE",
    )
    assert complete["attempt_count"] == 1
    assert complete["attempt_percentage_within_population"] == 50.0

    source = summary_row(
        summary,
        dimension_1_name="SOURCE_TYPE",
        dimension_1_value="SYNTHETIC_TEXT",
    )
    assert source["attempt_count"] == 2


def test_grouped_attempt_summary_includes_result_by_mode(
    valid_report_directory: Path,
) -> None:
    attempts = attempts_for(valid_report_directory)
    attempts["source_type"] = pd.Series([pd.NA, pd.NA], dtype="string")
    attempts["study_content_source"] = pd.Series(
        [pd.NA, pd.NA],
        dtype="string",
    )

    summary = build_grouped_attempt_summary(attempts)

    dropped_ai = summary_row(
        summary,
        dimension_1_name="ATTEMPT_RESULT",
        dimension_1_value="USER_DROPPED",
        dimension_2_name="AUTHORING_MODE",
        dimension_2_value="AI",
    )
    assert dropped_ai["attempt_count"] == 1
    assert dropped_ai["attempt_result"] == "USER_DROPPED"
    assert dropped_ai["attempt_authoring_mode"] == "AI"

    missing_source = summary_row(
        summary,
        dimension_1_name="SOURCE_TYPE",
        dimension_1_value="MISSING",
    )
    assert missing_source["attempt_count"] == 2
