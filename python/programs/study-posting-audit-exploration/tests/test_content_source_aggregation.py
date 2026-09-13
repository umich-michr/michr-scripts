from pathlib import Path

import pandas as pd

from study_posting_audit_exploration import (
    ExplorationInputConfig,
    build_content_source_concordance_matrix,
    build_content_source_concordance_summary,
    derive_attempt_histories,
    load_audit_report,
)


def attempts_for(path: Path) -> pd.DataFrame:
    """Return derived attempts with source-comparison columns."""
    report = load_audit_report(
        ExplorationInputConfig(
            report_directory=path,
        )
    )
    attempts = derive_attempt_histories(report.records).study_attempt_author_history
    attempts["study_content_source"] = pd.Series(
        ["Study Protocol", "Study Protocol"],
        dtype="string",
    )
    attempts["llm_inferred_study_content_source"] = pd.Series(
        [" study protocol ", "Informed Consent"],
        dtype="string",
    )
    attempts["study_content_source_other_value"] = pd.Series(
        [pd.NA, "Synthetic other"],
        dtype="string",
    )
    attempts["llm_inferred_study_content_source_other_value"] = pd.Series(
        [pd.NA, "synthetic OTHER"],
        dtype="string",
    )

    return attempts


def population_row(
    summary: pd.DataFrame,
    completion_group: str,
) -> pd.Series:
    """Return one concordance population row."""
    return summary.loc[summary["attempt_completion_group"].eq(completion_group)].iloc[0]


def test_content_source_summary_separates_completion_groups(
    valid_report_directory: Path,
) -> None:
    attempts = attempts_for(valid_report_directory)

    summary = build_content_source_concordance_summary(attempts)

    assert summary["attempt_completion_group"].tolist() == [
        "ALL",
        "COMPLETE",
        "INCOMPLETE",
    ]

    all_row = population_row(summary, "ALL")
    assert all_row["ai_attempt_count"] == 2
    assert all_row["ai_attempt_count_with_both_content_source_values"] == 2
    assert all_row["ai_attempt_count_with_matching_content_source"] == 1
    assert all_row["ai_attempt_count_with_different_content_source"] == 1
    assert (
        all_row[
            "ai_attempt_percentage_with_different_content_source_among_comparable_attempts"
        ]
        == 50.0
    )
    assert all_row["ai_attempt_count_with_both_other_text_values"] == 1
    assert all_row["ai_attempt_count_with_matching_other_text_value"] == 1
    assert all_row["ai_attempt_count_with_different_other_text_value"] == 0

    complete = population_row(summary, "COMPLETE")
    assert complete["ai_attempt_count"] == 1
    assert complete["ai_attempt_count_with_different_content_source"] == 1

    incomplete = population_row(summary, "INCOMPLETE")
    assert incomplete["ai_attempt_count"] == 1
    assert incomplete["ai_attempt_count_with_matching_content_source"] == 1


def test_content_source_matrix_uses_normalized_values(
    valid_report_directory: Path,
) -> None:
    attempts = attempts_for(valid_report_directory)

    matrix = build_content_source_concordance_matrix(attempts)
    all_rows = matrix.loc[matrix["attempt_completion_group"].eq("ALL")]

    assert set(all_rows["reported_study_content_source"]) == {"study protocol"}
    assert set(all_rows["inferred_study_content_source"]) == {
        "study protocol",
        "informed consent",
    }
    assert all_rows["reported_source_attempt_count"].tolist() == [2, 2]
    assert sorted(all_rows["attempt_percentage_within_reported_source"].tolist()) == [
        50.0,
        50.0,
    ]


def test_missing_comparable_values_produce_null_percentage(
    valid_report_directory: Path,
) -> None:
    attempts = attempts_for(valid_report_directory)
    attempts["study_content_source"] = pd.Series(
        [pd.NA, pd.NA],
        dtype="string",
    )

    summary = build_content_source_concordance_summary(attempts)
    all_row = population_row(summary, "ALL")

    assert all_row["ai_attempt_count_with_both_content_source_values"] == 0
    assert pd.isna(
        all_row[
            "ai_attempt_percentage_with_different_content_source_among_comparable_attempts"
        ]
    )
