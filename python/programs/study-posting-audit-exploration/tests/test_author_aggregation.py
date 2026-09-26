import json
from pathlib import Path

import pandas as pd
import pytest

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
    assert all_attempts["percentile_25_author_attempt_value"] == 3.0
    assert all_attempts["median_author_attempt_value"] == 4.0
    assert all_attempts["average_author_attempt_value"] == 4.0
    assert all_attempts["percentile_75_author_attempt_value"] == 5.0
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
    assert all_authors["percentile_25_author_value"] == 2.0
    assert all_authors["median_author_value"] == 3.0
    assert all_authors["average_author_value"] == 3.0
    assert all_authors["percentile_75_author_value"] == 4.0
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


def test_current_author_experience_embeds_deterministic_percentile_bins() -> None:
    """Embed one canonical identifier-free aggregate payload on every row."""
    authors = pd.DataFrame.from_records(
        [
            {
                "author_user_name": f"forbidden-author-{index}@example.edu",
                "author_adoption_group": group,
                "total_studies_created_as_of_report_query_count": total,
                "other_study_memberships_as_of_report_query_count": membership,
                "distinct_login_days_as_of_report_query_count": index + 1,
                "login_history_span_days_as_of_report_query": 10 * (index + 1),
            }
            for index, (group, total, membership) in enumerate(
                (
                    ("AI_ONLY", 1, 0),
                    ("AI_ONLY", 2, 1),
                    ("MANUAL_ONLY", 3, 1),
                    ("MANUAL_ONLY", 4, 2),
                    ("BOTH_AI_AND_MANUAL", 20, 10),
                )
            )
        ]
    )

    first = build_current_author_experience_summary(authors)
    second = build_current_author_experience_summary(authors)

    assert first["author_activity_percentile_bins_json"].nunique() == 1
    assert (
        first["author_activity_percentile_bins_json"].iloc[0]
        == second["author_activity_percentile_bins_json"].iloc[0]
    )

    payload = first["author_activity_percentile_bins_json"].iloc[0]
    assert isinstance(payload, str)
    assert "forbidden-author" not in payload
    assert "author_user_name" not in payload
    assert "NaN" not in payload

    rows = json.loads(payload)
    assert len(rows) == 2 * 4 * 4
    assert {row["metric_name"] for row in rows} == {
        "total_studies_created_as_of_report_query_count",
        "other_study_memberships_as_of_report_query_count",
    }
    assert {row["binning_scheme"] for row in rows} == {
        "OVERALL_AUTHOR_PERCENTILES_50_75_90"
    }


def test_current_author_percentile_bins_share_boundaries_and_reconcile() -> None:
    """Use overall boundaries for every group and reconcile every denominator."""
    authors = pd.DataFrame.from_records(
        [
            {
                "author_adoption_group": group,
                "total_studies_created_as_of_report_query_count": total,
                "other_study_memberships_as_of_report_query_count": membership,
                "distinct_login_days_as_of_report_query_count": 1,
                "login_history_span_days_as_of_report_query": 1,
            }
            for group, total, membership in (
                ("AI_ONLY", 1, 0),
                ("AI_ONLY", 2, 1),
                ("MANUAL_ONLY", 3, 1),
                ("MANUAL_ONLY", 4, 2),
                ("BOTH_AI_AND_MANUAL", 20, None),
            )
        ]
    )

    summary = build_current_author_experience_summary(authors)
    rows = json.loads(summary["author_activity_percentile_bins_json"].iloc[0])

    for metric_name in {row["metric_name"] for row in rows}:
        metric_rows = [row for row in rows if row["metric_name"] == metric_name]
        boundaries_by_group = {
            row["author_adoption_group"]: tuple(
                (
                    item["lower_bound"],
                    item["upper_bound"],
                    item["lower_bound_inclusive"],
                    item["upper_bound_inclusive"],
                )
                for item in metric_rows
                if item["author_adoption_group"] == row["author_adoption_group"]
            )
            for row in metric_rows
        }
        assert len(set(boundaries_by_group.values())) == 1

        for group in {row["author_adoption_group"] for row in metric_rows}:
            group_rows = [
                row for row in metric_rows if row["author_adoption_group"] == group
            ]
            denominator = group_rows[0]["observed_value_denominator"]
            assert sum(row["author_count"] for row in group_rows) == denominator
            percentages = [
                row["author_percentage"]
                for row in group_rows
                if row["author_percentage"] is not None
            ]
            if denominator:
                assert sum(percentages) == pytest.approx(100.0)
            else:
                assert percentages == []


def test_current_author_percentile_bins_preserve_tied_empty_bins() -> None:
    """Keep four deterministic bins when percentile boundaries are tied."""
    authors = pd.DataFrame.from_records(
        [
            {
                "author_adoption_group": "AI_ONLY",
                "total_studies_created_as_of_report_query_count": 2,
                "other_study_memberships_as_of_report_query_count": 0,
                "distinct_login_days_as_of_report_query_count": 1,
                "login_history_span_days_as_of_report_query": 1,
            }
            for _ in range(4)
        ]
    )

    summary = build_current_author_experience_summary(authors)
    rows = [
        row
        for row in json.loads(summary["author_activity_percentile_bins_json"].iloc[0])
        if row["metric_name"] == "total_studies_created_as_of_report_query_count"
        and row["author_adoption_group"] == "ALL_AUTHORS"
    ]

    assert [row["bin_sequence"] for row in rows] == [1, 2, 3, 4]
    assert [row["author_count"] for row in rows] == [4, 0, 0, 0]
    assert [row["upper_bound"] for row in rows[:3]] == [2.0, 2.0, 2.0]


def test_current_author_percentile_bins_handle_all_missing_metrics() -> None:
    """Publish an empty payload when both binned metrics have no values."""
    authors = pd.DataFrame.from_records(
        [
            {
                "author_adoption_group": "AI_ONLY",
                "total_studies_created_as_of_report_query_count": None,
                "other_study_memberships_as_of_report_query_count": None,
                "distinct_login_days_as_of_report_query_count": 1,
                "login_history_span_days_as_of_report_query": 1,
            }
        ]
    )

    summary = build_current_author_experience_summary(authors)

    assert json.loads(summary["author_activity_percentile_bins_json"].iloc[0]) == []


@pytest.mark.parametrize(
    ("value", "error_type", "message"),
    [
        ("not-a-count", TypeError, "contains nonnumeric"),
        (-1, ValueError, "must be nonnegative"),
        (1.5, ValueError, "must be integral"),
        (float("inf"), ValueError, "must be finite"),
    ],
)
def test_current_author_percentile_bins_reject_invalid_values(
    value: object,
    error_type: type[Exception],
    message: str,
) -> None:
    """Reject invalid author-count values rather than publishing bad bins."""
    authors = pd.DataFrame.from_records(
        [
            {
                "author_adoption_group": "AI_ONLY",
                "total_studies_created_as_of_report_query_count": value,
                "other_study_memberships_as_of_report_query_count": 0,
                "distinct_login_days_as_of_report_query_count": 1,
                "login_history_span_days_as_of_report_query": 1,
            }
        ]
    )

    with pytest.raises(error_type, match=message):
        build_current_author_experience_summary(authors)


def test_current_author_percentile_bins_treat_only_missing_as_missing() -> None:
    """Exclude true missing values while retaining valid zero counts."""
    authors = pd.DataFrame.from_records(
        [
            {
                "author_adoption_group": "AI_ONLY",
                "total_studies_created_as_of_report_query_count": None,
                "other_study_memberships_as_of_report_query_count": 0,
                "distinct_login_days_as_of_report_query_count": 1,
                "login_history_span_days_as_of_report_query": 1,
            },
            {
                "author_adoption_group": "MANUAL_ONLY",
                "total_studies_created_as_of_report_query_count": 0,
                "other_study_memberships_as_of_report_query_count": None,
                "distinct_login_days_as_of_report_query_count": 1,
                "login_history_span_days_as_of_report_query": 1,
            },
        ]
    )

    summary = build_current_author_experience_summary(authors)
    rows = [
        row
        for row in json.loads(summary["author_activity_percentile_bins_json"].iloc[0])
        if row["metric_name"] == "total_studies_created_as_of_report_query_count"
        and row["author_adoption_group"] == "ALL_AUTHORS"
    ]

    assert rows[0]["author_count"] == 1
    assert rows[0]["observed_value_denominator"] == 1
    assert rows[0]["missing_author_count"] == 1
