"""Tests for successful-generation content-source concordance."""

import pandas as pd

from study_posting_audit_exploration import (
    build_content_source_concordance_matrix,
    build_content_source_concordance_summary,
)


def successful_generations() -> pd.DataFrame:
    """Return synthetic successful-generation source rows."""
    rows: list[dict[str, object]] = [
        {
            "attempt_completion_group": "INCOMPLETE",
            "study_content_source": "Study Protocol",
            "llm_inferred_study_content_source": " study protocol ",
            "study_content_source_other_value": None,
            "llm_inferred_study_content_source_other_value": None,
        },
        {
            "attempt_completion_group": "COMPLETE",
            "study_content_source": "Study Protocol",
            "llm_inferred_study_content_source": "Informed Consent",
            "study_content_source_other_value": "Synthetic other",
            "llm_inferred_study_content_source_other_value": ("synthetic OTHER"),
        },
    ]

    return pd.DataFrame.from_records(rows)


def population_row(
    summary: pd.DataFrame,
    completion_group: str,
) -> pd.Series:
    """Return one successful-generation population row."""
    return summary.loc[summary["attempt_completion_group"].eq(completion_group)].iloc[0]


def test_content_source_summary_separates_completion_groups() -> None:
    summary = build_content_source_concordance_summary(successful_generations())

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
            "ai_attempt_percentage_with_different_content_source_"
            "among_comparable_attempts"
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


def test_content_source_matrix_uses_normalized_values() -> None:
    matrix = build_content_source_concordance_matrix(successful_generations())
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


def test_missing_comparable_values_produce_null_percentage() -> None:
    attempts = successful_generations()
    attempts["study_content_source"] = pd.Series(
        [pd.NA, pd.NA],
        dtype="string",
    )

    summary = build_content_source_concordance_summary(attempts)
    all_row = population_row(summary, "ALL")

    assert all_row["ai_attempt_count_with_both_content_source_values"] == 0
    assert pd.isna(
        all_row[
            "ai_attempt_percentage_with_different_content_source_"
            "among_comparable_attempts"
        ]
    )
