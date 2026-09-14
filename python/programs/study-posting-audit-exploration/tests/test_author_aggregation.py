from pathlib import Path

import pandas as pd

from study_posting_audit_exploration import (
    ExplorationInputConfig,
    build_attempt_start_experience_summary,
    build_author_analysis_tables,
    build_current_author_experience_summary,
    build_grouped_author_summary,
    derive_appointments,
    derive_attempt_histories,
    load_audit_report,
)


def author_inputs(
    path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return attempts, authors, and appointment rows."""
    report = load_audit_report(
        ExplorationInputConfig(
            report_directory=path,
        )
    )
    histories = derive_attempt_histories(report.records)
    appointments, findings = derive_appointments(report.records)

    assert findings == ()

    return (
        histories.study_attempt_author_history,
        histories.author_history,
        appointments,
    )


def grouped_row(
    summary: pd.DataFrame,
    *,
    completion_group: str,
    authoring_mode: str,
    dimension_name: str,
    dimension_value: str,
) -> pd.Series:
    """Return one grouped-author summary row."""
    return summary.loc[
        summary["attempt_completion_group"].eq(completion_group)
        & summary["attempt_authoring_mode"].eq(authoring_mode)
        & summary["grouping_dimension_name"].eq(dimension_name)
        & summary["grouping_dimension_value"].eq(dimension_value)
    ].iloc[0]


def test_grouped_author_summary_reports_completion_and_mode(
    valid_report_directory: Path,
) -> None:
    attempts, _, appointments = author_inputs(valid_report_directory)

    summary = build_grouped_author_summary(
        attempts,
        appointments=appointments,
    )

    all_authors = grouped_row(
        summary,
        completion_group="ALL",
        authoring_mode="ALL",
        dimension_name="ALL",
        dimension_value="ALL",
    )
    assert all_authors["distinct_author_count"] == 2
    assert all_authors["population_distinct_author_count"] == 2
    assert all_authors["distinct_author_percentage_within_population"] == 100.0
    assert all_authors["distinct_author_count_with_any_ai_attempt"] == 2
    assert all_authors["distinct_author_count_with_any_manual_attempt"] == 0
    assert all_authors["distinct_author_count_with_completed_attempt"] == 1
    assert all_authors["distinct_author_count_with_incomplete_attempt"] == 1

    completed_ai = grouped_row(
        summary,
        completion_group="COMPLETE",
        authoring_mode="AI",
        dimension_name="ALL",
        dimension_value="ALL",
    )
    assert completed_ai["distinct_author_count"] == 1


def test_grouped_author_summary_includes_role_and_appointments(
    valid_report_directory: Path,
) -> None:
    attempts, _, appointments = author_inputs(valid_report_directory)

    summary = build_grouped_author_summary(
        attempts,
        appointments=appointments,
    )

    role = grouped_row(
        summary,
        completion_group="ALL",
        authoring_mode="ALL",
        dimension_name="EFFECTIVE_AUTHOR_ROLE",
        dimension_value="TEAM_MEMBER",
    )
    assert role["distinct_author_count"] == 2

    school = grouped_row(
        summary,
        completion_group="ALL",
        authoring_mode="ALL",
        dimension_name="AUTHOR_APPOINTMENT_SCHOOL",
        dimension_value="Synthetic School",
    )
    assert school["distinct_author_count"] == 2
    assert bool(school["group_values_are_mutually_exclusive"]) is False

    pi_department = grouped_row(
        summary,
        completion_group="ALL",
        authoring_mode="ALL",
        dimension_name="PI_APPOINTMENT_DEPARTMENT",
        dimension_value="Synthetic Department",
    )
    assert pi_department["distinct_author_count"] == 2


def test_attempt_start_experience_summary_uses_attempt_grain(
    valid_report_directory: Path,
) -> None:
    attempts, authors, _ = author_inputs(valid_report_directory)
    attempts.loc[0, "prior_studies_created_before_attempt_start_count"] = 2
    attempts.loc[1, "prior_studies_created_before_attempt_start_count"] = 6

    summary = build_attempt_start_experience_summary(
        attempts,
        authors,
    )
    all_attempts = summary.loc[
        summary["author_adoption_group"].eq("ALL_AUTHORS")
        & summary["attempt_completion_group"].eq("ALL")
        & summary["attempt_authoring_mode"].eq("ALL")
    ].iloc[0]

    assert (
        all_attempts["experience_metric_name"]
        == "prior_studies_created_before_attempt_start_count"
    )
    assert all_attempts["author_attempt_count_with_nonmissing_metric"] == 2
    assert all_attempts["author_attempt_count_missing_metric"] == 0
    assert all_attempts["minimum_author_attempt_value"] == 2.0
    assert all_attempts["median_author_attempt_value"] == 4.0
    assert all_attempts["maximum_author_attempt_value"] == 6.0


def test_current_author_experience_summary_uses_author_grain(
    valid_report_directory: Path,
) -> None:
    _, authors, _ = author_inputs(valid_report_directory)
    authors.loc[
        :,
        "total_studies_created_as_of_report_query_count",
    ] = [1, 5]

    summary = build_current_author_experience_summary(authors)
    all_authors = summary.loc[
        summary["author_adoption_group"].eq("ALL_AUTHORS")
        & summary["experience_metric_name"].eq(
            "total_studies_created_as_of_report_query_count"
        )
    ].iloc[0]

    assert all_authors["author_count_with_nonmissing_metric"] == 2
    assert all_authors["author_count_missing_metric"] == 0
    assert all_authors["minimum_author_value"] == 1.0
    assert all_authors["median_author_value"] == 3.0
    assert all_authors["maximum_author_value"] == 5.0


def test_author_analysis_tables_compose_all_outputs(
    valid_report_directory: Path,
) -> None:
    attempts, authors, appointments = author_inputs(valid_report_directory)

    tables = build_author_analysis_tables(
        attempts=attempts,
        authors=authors,
        appointments=appointments,
    )

    assert not tables.grouped_author_summary.empty
    assert not tables.attempt_start_experience_summary.empty
    assert not tables.current_author_experience_summary.empty
