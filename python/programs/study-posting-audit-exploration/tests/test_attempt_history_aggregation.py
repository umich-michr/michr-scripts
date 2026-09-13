from pathlib import Path

import pandas as pd

from study_posting_audit_exploration import (
    AttemptHistoryTables,
    ExplorationInputConfig,
    derive_attempt_histories,
    load_audit_report,
)
from study_posting_audit_exploration.aggregation import (
    build_author_handoff_summary,
    build_study_attempt_history_summary,
)


def histories_for(path: Path) -> AttemptHistoryTables:
    """Return derived histories for one synthetic report."""
    report = load_audit_report(
        ExplorationInputConfig(
            report_directory=path,
        )
    )

    return derive_attempt_histories(report.records)


def population_row(
    summary: pd.DataFrame,
    mode: str,
) -> pd.Series:
    """Return one study-history population row."""
    return summary.loc[summary["final_completion_authoring_mode"].eq(mode)].iloc[0]


def test_study_history_summary_has_four_explicit_populations(
    valid_report_directory: Path,
) -> None:
    histories = histories_for(valid_report_directory)

    summary = build_study_attempt_history_summary(histories.study_attempt_history)

    assert summary["final_completion_authoring_mode"].tolist() == [
        "ALL",
        "AI",
        "MANUAL",
        "NOT_COMPLETED",
    ]

    all_row = population_row(summary, "ALL")
    assert all_row["distinct_study_count"] == 1
    assert all_row["study_count_with_no_completed_attempt"] == 0
    assert all_row["study_count_with_preceding_incomplete_attempts"] == 1
    assert all_row["study_percentage_with_preceding_incomplete_attempts"] == 100.0
    assert all_row["total_preceding_incomplete_attempt_count"] == 1
    assert all_row["total_preceding_user_dropped_attempt_count"] == 1
    assert all_row["median_preceding_incomplete_attempt_count"] == 1.0
    assert all_row["median_minutes_first_attempt_to_completion"] == 1_500.0
    assert all_row["study_count_with_author_change_before_completion"] == 1

    ai_row = population_row(summary, "AI")
    assert ai_row["distinct_study_count"] == 1

    manual_row = population_row(summary, "MANUAL")
    assert manual_row["distinct_study_count"] == 0
    assert pd.isna(manual_row["study_percentage_with_preceding_incomplete_attempts"])

    not_completed_row = population_row(summary, "NOT_COMPLETED")
    assert not_completed_row["distinct_study_count"] == 0


def test_author_handoff_summary_describes_immediate_preceding_path(
    valid_report_directory: Path,
) -> None:
    histories = histories_for(valid_report_directory)

    summary = build_author_handoff_summary(
        attempts=histories.study_attempt_author_history,
        studies=histories.study_attempt_history,
    )

    assert len(summary) == 1

    row = summary.iloc[0]
    assert row["completed_attempt_authoring_mode"] == "AI"
    assert row["preceding_attempt_authoring_mode"] == "AI"
    assert row["preceding_attempt_result"] == "USER_DROPPED"
    assert row["author_handoff_category"] == "ALL_PRECEDING_ATTEMPTS_BY_OTHER_AUTHORS"
    assert row["distinct_completed_study_count"] == 1
    assert row["population_distinct_completed_study_count"] == 1
    assert row["distinct_completed_study_percentage"] == 100.0
    assert row["median_minutes_first_attempt_to_completion"] == 1_500.0


def test_handoff_summary_classifies_no_preceding_attempt(
    valid_report_directory: Path,
) -> None:
    histories = histories_for(valid_report_directory)
    attempts = histories.study_attempt_author_history.loc[
        histories.study_attempt_author_history["is_completed_attempt"].eq(True)
    ].copy()
    studies = histories.study_attempt_history.copy()
    studies.loc[:, "preceding_incomplete_attempt_count"] = 0
    studies.loc[
        :,
        "preceding_incomplete_attempt_count_by_completion_author",
    ] = 0
    studies.loc[
        :,
        "preceding_incomplete_attempt_count_by_other_authors",
    ] = 0

    summary = build_author_handoff_summary(
        attempts=attempts,
        studies=studies,
    )

    row = summary.iloc[0]
    assert row["preceding_attempt_authoring_mode"] == "NONE"
    assert row["preceding_attempt_result"] == "NONE"
    assert row["author_handoff_category"] == "NO_PRECEDING_ATTEMPT"


def test_handoff_summary_empty_when_no_studies_are_complete(
    valid_report_directory: Path,
) -> None:
    histories = histories_for(valid_report_directory)
    studies = histories.study_attempt_history.copy()
    studies.loc[:, "study_is_completed"] = False

    summary = build_author_handoff_summary(
        attempts=histories.study_attempt_author_history,
        studies=studies,
    )

    assert summary.empty
