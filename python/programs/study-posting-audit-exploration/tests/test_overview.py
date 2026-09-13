from pathlib import Path

import pandas as pd

from study_posting_audit_exploration import (
    ExplorationInputConfig,
    derive_attempt_histories,
    load_audit_report,
)
from study_posting_audit_exploration.aggregation import (
    build_overview_summary,
)


def overview_for(path: Path) -> pd.DataFrame:
    """Return overview metrics for one synthetic report."""
    report = load_audit_report(
        ExplorationInputConfig(
            report_directory=path,
        )
    )
    histories = derive_attempt_histories(report.records)

    return build_overview_summary(
        attempts=histories.study_attempt_author_history,
        studies=histories.study_attempt_history,
        authors=histories.author_history,
    )


def metric_row(
    overview: pd.DataFrame,
    metric_name: str,
) -> pd.Series:
    """Return one overview metric row."""
    return overview.loc[overview["overview_metric_name"].eq(metric_name)].iloc[0]


def test_overview_reports_attempt_study_and_author_counts(
    valid_report_directory: Path,
) -> None:
    overview = overview_for(valid_report_directory)

    assert metric_row(overview, "all_attempt_count")["metric_count"] == 2
    assert metric_row(overview, "complete_attempt_count")["metric_count"] == 1
    assert metric_row(overview, "incomplete_attempt_count")["metric_count"] == 1
    assert metric_row(overview, "user_dropped_attempt_count")["metric_count"] == 1

    completed = metric_row(
        overview,
        "distinct_completed_study_count",
    )
    assert completed["metric_count"] == 1
    assert completed["metric_denominator_count"] == 1
    assert completed["metric_percentage"] == 100.0

    assert (
        metric_row(
            overview,
            "distinct_completed_study_count_with_preceding_incomplete_attempts",
        )["metric_count"]
        == 1
    )
    assert (
        metric_row(
            overview,
            "distinct_author_count_with_any_attempt",
        )["metric_count"]
        == 2
    )
    assert (
        metric_row(
            overview,
            "distinct_author_count_with_any_ai_attempt",
        )["metric_count"]
        == 2
    )
    assert (
        metric_row(
            overview,
            "distinct_author_count_with_both_ai_and_manual_attempts",
        )["metric_count"]
        == 0
    )


def test_overview_uses_explicit_denominators(
    valid_report_directory: Path,
) -> None:
    overview = overview_for(valid_report_directory)

    completed_ai = metric_row(
        overview,
        "completed_ai_attempt_count",
    )
    assert completed_ai["metric_count"] == 1
    assert completed_ai["metric_denominator_count"] == 1
    assert completed_ai["metric_percentage"] == 100.0
    assert (
        completed_ai["metric_denominator_definition"]
        == "All attempts with ATTEMPT_RESULT equal to COMPLETE."
    )

    user_dropped = metric_row(
        overview,
        "user_dropped_attempt_count",
    )
    assert user_dropped["metric_count"] == 1
    assert user_dropped["metric_denominator_count"] == 1
    assert user_dropped["metric_percentage"] == 100.0


def test_named_pi_and_classified_pi_are_separate_metrics(
    valid_report_directory: Path,
) -> None:
    overview = overview_for(valid_report_directory)

    named = metric_row(overview, "distinct_named_pi_count")
    classified = metric_row(
        overview,
        "distinct_author_count_classified_as_pi",
    )

    assert named["overview_section_name"] == "PI_IDENTITIES"
    assert named["metric_count"] == 1
    assert classified["overview_section_name"] == "PI_IDENTITIES"
    assert classified["metric_count"] == 0
