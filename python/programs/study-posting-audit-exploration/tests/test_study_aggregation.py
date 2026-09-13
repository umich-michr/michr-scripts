from pathlib import Path

import pandas as pd
import pytest

from study_posting_audit_exploration import (
    ExplorationInputConfig,
    build_grouped_study_summary,
    derive_attempt_histories,
    load_audit_report,
)


def studies_for(path: Path) -> pd.DataFrame:
    """Return study history enriched with grouping dimensions."""
    report = load_audit_report(
        ExplorationInputConfig(
            report_directory=path,
        )
    )
    histories = derive_attempt_histories(report.records)
    completed_source = report.records.loc[
        report.records["ATTEMPT_RESULT"].eq("COMPLETE"),
        [
            "STUDY_NUM",
            "STUDY_PARTICIPANT_TYPE",
            "STUDY_DEPARTMENT",
            "SOURCE_TYPE",
            "STUDY_CONTENT_SOURCE",
        ],
    ].rename(
        columns={
            "STUDY_NUM": "study_num",
            "STUDY_PARTICIPANT_TYPE": "study_participant_type",
            "STUDY_DEPARTMENT": "study_department",
            "SOURCE_TYPE": "source_type",
            "STUDY_CONTENT_SOURCE": "study_content_source",
        }
    )

    return histories.study_attempt_history.merge(
        completed_source,
        on="study_num",
        how="left",
        validate="one_to_one",
    )


def summary_row(
    summary: pd.DataFrame,
    *,
    population_name: str,
    completion_mode: str,
    dimension_1_name: str,
    dimension_1_value: str,
    dimension_2_name: str = "NONE",
    dimension_2_value: str = "NONE",
) -> pd.Series:
    """Return one grouped study summary row."""
    return summary.loc[
        summary["study_population_name"].eq(population_name)
        & summary["final_completion_authoring_mode"].eq(completion_mode)
        & summary["grouping_dimension_1_name"].eq(dimension_1_name)
        & summary["grouping_dimension_1_value"].eq(dimension_1_value)
        & summary["grouping_dimension_2_name"].eq(dimension_2_name)
        & summary["grouping_dimension_2_value"].eq(dimension_2_value)
    ].iloc[0]


def test_grouped_study_summary_reports_base_population(
    valid_report_directory: Path,
) -> None:
    studies = studies_for(valid_report_directory)

    summary = build_grouped_study_summary(studies)

    all_studies = summary_row(
        summary,
        population_name="ALL_STUDIES_WITH_ATTEMPTS",
        completion_mode="ALL",
        dimension_1_name="ALL",
        dimension_1_value="ALL",
    )
    assert all_studies["distinct_study_count"] == 1
    assert all_studies["population_distinct_study_count"] == 1
    assert all_studies["distinct_study_percentage_within_population"] == 100.0
    assert all_studies["study_count_with_preceding_incomplete_attempts"] == 1
    assert all_studies["study_percentage_with_preceding_incomplete_attempts"] == 100.0
    assert all_studies["total_preceding_incomplete_attempt_count"] == 1
    assert all_studies["total_preceding_user_dropped_attempt_count"] == 1
    assert all_studies["median_preceding_incomplete_attempt_count"] == 1.0
    assert all_studies["median_minutes_first_attempt_to_completion"] == 1_500.0
    assert all_studies[
        "median_completed_attempt_study_info_page_minutes"
    ] == pytest.approx(1.0 / 60.0)


def test_grouped_study_summary_breaks_down_participant_and_department(
    valid_report_directory: Path,
) -> None:
    studies = studies_for(valid_report_directory)

    summary = build_grouped_study_summary(studies)

    participant = summary_row(
        summary,
        population_name="COMPLETED_STUDIES",
        completion_mode="AI",
        dimension_1_name="STUDY_PARTICIPANT_TYPE",
        dimension_1_value="HEALTHY",
    )
    assert participant["distinct_study_count"] == 1

    department = summary_row(
        summary,
        population_name="COMPLETED_STUDIES",
        completion_mode="AI",
        dimension_1_name="STUDY_DEPARTMENT",
        dimension_1_value="Synthetic Department",
    )
    assert department["distinct_study_count"] == 1

    combined = summary_row(
        summary,
        population_name="COMPLETED_STUDIES",
        completion_mode="AI",
        dimension_1_name="STUDY_PARTICIPANT_TYPE",
        dimension_1_value="HEALTHY",
        dimension_2_name="STUDY_DEPARTMENT",
        dimension_2_value="Synthetic Department",
    )
    assert combined["distinct_study_count"] == 1


def test_grouped_study_summary_preserves_missing_source_group(
    valid_report_directory: Path,
) -> None:
    studies = studies_for(valid_report_directory)
    studies["source_type"] = pd.Series([pd.NA], dtype="string")
    studies["study_content_source"] = pd.Series([pd.NA], dtype="string")

    summary = build_grouped_study_summary(studies)

    missing_source = summary_row(
        summary,
        population_name="ALL_STUDIES_WITH_ATTEMPTS",
        completion_mode="ALL",
        dimension_1_name="SOURCE_TYPE",
        dimension_1_value="MISSING",
    )
    assert missing_source["distinct_study_count"] == 1


def test_grouped_study_summary_uses_noncompleted_population(
    valid_report_directory: Path,
) -> None:
    studies = studies_for(valid_report_directory)
    studies.loc[:, "study_is_completed"] = False
    studies.loc[:, "completed_attempt_authoring_mode"] = pd.NA

    summary = build_grouped_study_summary(studies)

    not_completed = summary_row(
        summary,
        population_name="STUDIES_WITHOUT_COMPLETION",
        completion_mode="NOT_COMPLETED",
        dimension_1_name="ALL",
        dimension_1_value="ALL",
    )
    assert not_completed["distinct_study_count"] == 1
