from pathlib import Path

import pandas as pd
import pytest

from study_posting_audit_exploration import (
    ExplorationInputConfig,
    build_grouped_study_summary,
    derive_appointments,
    derive_attempt_histories,
    load_audit_report,
)


def study_inputs(
    path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return enriched study history and study-keyed appointments."""
    report = load_audit_report(
        ExplorationInputConfig(
            report_directory=path,
        )
    )
    histories = derive_attempt_histories(report.records)
    completed_source = report.records.loc[
        report.records["ATTEMPT_RESULT"].eq("COMPLETE"),
        [
            "ID",
            "STUDY_NUM",
            "STUDY_PARTICIPANT_TYPE",
            "STUDY_DEPARTMENT",
            "SOURCE_TYPE",
            "STUDY_CONTENT_SOURCE",
        ],
    ].rename(
        columns={
            "ID": "audit_record_id",
            "STUDY_NUM": "study_num",
            "STUDY_PARTICIPANT_TYPE": "study_participant_type",
            "STUDY_DEPARTMENT": "study_department",
            "SOURCE_TYPE": "source_type",
            "STUDY_CONTENT_SOURCE": "study_content_source",
        }
    )
    studies = histories.study_attempt_history.merge(
        completed_source.drop(columns=["audit_record_id"]),
        on="study_num",
        how="left",
        validate="one_to_one",
    )
    appointment_rows, findings = derive_appointments(report.records)

    assert findings == ()

    selected_attempts = completed_source.loc[
        :,
        [
            "audit_record_id",
            "study_num",
        ],
    ]
    appointments = selected_attempts.merge(
        appointment_rows,
        on="audit_record_id",
        how="inner",
        validate="one_to_many",
    )

    return studies, appointments


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
    studies, appointments = study_inputs(valid_report_directory)

    summary = build_grouped_study_summary(
        studies,
        appointments=appointments,
    )

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
    studies, appointments = study_inputs(valid_report_directory)

    summary = build_grouped_study_summary(
        studies,
        appointments=appointments,
    )

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


def test_grouped_study_summary_includes_appointment_dimensions(
    valid_report_directory: Path,
) -> None:
    studies, appointments = study_inputs(valid_report_directory)

    summary = build_grouped_study_summary(
        studies,
        appointments=appointments,
    )

    author_school = summary_row(
        summary,
        population_name="COMPLETED_STUDIES",
        completion_mode="AI",
        dimension_1_name="AUTHOR_APPOINTMENT_SCHOOL",
        dimension_1_value="Synthetic School",
    )
    assert author_school["distinct_study_count"] == 1
    assert bool(author_school["group_values_are_mutually_exclusive"]) is False

    pi_department = summary_row(
        summary,
        population_name="COMPLETED_STUDIES",
        completion_mode="AI",
        dimension_1_name="PI_APPOINTMENT_DEPARTMENT",
        dimension_1_value="Synthetic Department",
    )
    assert pi_department["distinct_study_count"] == 1
    assert bool(pi_department["group_values_are_mutually_exclusive"]) is False


def test_appointment_groups_do_not_double_count_one_study(
    valid_report_directory: Path,
) -> None:
    studies, appointments = study_inputs(valid_report_directory)
    duplicate = appointments.iloc[[0]].copy()
    duplicate["appointment_index"] = 99
    appointments = pd.concat(
        [
            appointments,
            duplicate,
        ],
        ignore_index=True,
    )

    summary = build_grouped_study_summary(
        studies,
        appointments=appointments,
    )

    author_school = summary_row(
        summary,
        population_name="COMPLETED_STUDIES",
        completion_mode="AI",
        dimension_1_name="AUTHOR_APPOINTMENT_SCHOOL",
        dimension_1_value="Synthetic School",
    )
    assert author_school["distinct_study_count"] == 1


def test_grouped_study_summary_preserves_missing_source_group(
    valid_report_directory: Path,
) -> None:
    studies, appointments = study_inputs(valid_report_directory)
    studies["source_type"] = pd.Series([pd.NA], dtype="string")
    studies["study_content_source"] = pd.Series([pd.NA], dtype="string")

    summary = build_grouped_study_summary(
        studies,
        appointments=appointments,
    )

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
    studies, _ = study_inputs(valid_report_directory)
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
