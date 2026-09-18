"""Tests for completed-study completion-author context aggregates."""

import pandas as pd
import pandas.testing as pdt
import pytest

from study_posting_audit_exploration.aggregation.completed_study_context import (
    COMPLETED_STUDY_AUTHOR_CONTEXT_COLUMNS,
    build_completed_study_author_context_summary,
)


def _attempt_history() -> pd.DataFrame:
    """Return synthetic attempts with four uniquely completed studies."""
    return pd.DataFrame(
        {
            "study_num": pd.Series(
                ["STUDY-1", "STUDY-1", "STUDY-2", "STUDY-3", "STUDY-4"],
                dtype="string",
            ),
            "attempt_authoring_mode": pd.Series(
                ["MANUAL", "AI", "AI", "MANUAL", "MANUAL"],
                dtype="string",
            ),
            "attempt_author_user_name": pd.Series(
                ["author-a", "author-a", "author-a", "author-b", "author-a"],
                dtype="string",
            ),
            "effective_attempt_author_role": pd.Series(
                ["COORDINATOR", "PI", "COORDINATOR", "PI", "COORDINATOR"],
                dtype="string",
            ),
            "attempt_author_is_study_pi": pd.Series(
                [False, True, False, True, False],
                dtype="boolean",
            ),
            "is_completed_attempt": pd.Series(
                [False, True, True, True, True],
                dtype="boolean",
            ),
        }
    )


def test_build_completed_study_author_context_summary() -> None:
    """Count studies once while allowing repeated and changing authors."""
    result = build_completed_study_author_context_summary(_attempt_history())

    expected = pd.DataFrame.from_records(
        [
            {
                "context_dimension_name": "EFFECTIVE_ROLE",
                "context_dimension_value": "COORDINATOR",
                "final_completion_authoring_mode": "AI",
                "completed_study_count": 1,
                "mode_completed_study_count": 2,
                "all_completed_study_count": 4,
                "completed_study_percentage_within_mode": 50.0,
                "completed_study_percentage_overall": 25.0,
                "distinct_completion_author_count": 1,
            },
            {
                "context_dimension_name": "EFFECTIVE_ROLE",
                "context_dimension_value": "PI",
                "final_completion_authoring_mode": "AI",
                "completed_study_count": 1,
                "mode_completed_study_count": 2,
                "all_completed_study_count": 4,
                "completed_study_percentage_within_mode": 50.0,
                "completed_study_percentage_overall": 25.0,
                "distinct_completion_author_count": 1,
            },
            {
                "context_dimension_name": "EFFECTIVE_ROLE",
                "context_dimension_value": "COORDINATOR",
                "final_completion_authoring_mode": "MANUAL",
                "completed_study_count": 1,
                "mode_completed_study_count": 2,
                "all_completed_study_count": 4,
                "completed_study_percentage_within_mode": 50.0,
                "completed_study_percentage_overall": 25.0,
                "distinct_completion_author_count": 1,
            },
            {
                "context_dimension_name": "EFFECTIVE_ROLE",
                "context_dimension_value": "PI",
                "final_completion_authoring_mode": "MANUAL",
                "completed_study_count": 1,
                "mode_completed_study_count": 2,
                "all_completed_study_count": 4,
                "completed_study_percentage_within_mode": 50.0,
                "completed_study_percentage_overall": 25.0,
                "distinct_completion_author_count": 1,
            },
            {
                "context_dimension_name": "PI_STATUS",
                "context_dimension_value": "NON_PI",
                "final_completion_authoring_mode": "AI",
                "completed_study_count": 1,
                "mode_completed_study_count": 2,
                "all_completed_study_count": 4,
                "completed_study_percentage_within_mode": 50.0,
                "completed_study_percentage_overall": 25.0,
                "distinct_completion_author_count": 1,
            },
            {
                "context_dimension_name": "PI_STATUS",
                "context_dimension_value": "PI",
                "final_completion_authoring_mode": "AI",
                "completed_study_count": 1,
                "mode_completed_study_count": 2,
                "all_completed_study_count": 4,
                "completed_study_percentage_within_mode": 50.0,
                "completed_study_percentage_overall": 25.0,
                "distinct_completion_author_count": 1,
            },
            {
                "context_dimension_name": "PI_STATUS",
                "context_dimension_value": "NON_PI",
                "final_completion_authoring_mode": "MANUAL",
                "completed_study_count": 1,
                "mode_completed_study_count": 2,
                "all_completed_study_count": 4,
                "completed_study_percentage_within_mode": 50.0,
                "completed_study_percentage_overall": 25.0,
                "distinct_completion_author_count": 1,
            },
            {
                "context_dimension_name": "PI_STATUS",
                "context_dimension_value": "PI",
                "final_completion_authoring_mode": "MANUAL",
                "completed_study_count": 1,
                "mode_completed_study_count": 2,
                "all_completed_study_count": 4,
                "completed_study_percentage_within_mode": 50.0,
                "completed_study_percentage_overall": 25.0,
                "distinct_completion_author_count": 1,
            },
        ],
        columns=list(COMPLETED_STUDY_AUTHOR_CONTEXT_COLUMNS),
    )

    pdt.assert_frame_equal(result, expected)


def test_counts_distinct_completion_authors_within_each_study_group() -> None:
    """Use author identity only for a distinct aggregate count."""
    history = _attempt_history()
    additional = history.iloc[[2]].copy()
    additional["study_num"] = "STUDY-5"
    additional["attempt_author_user_name"] = "author-c"
    history = pd.concat([history, additional], ignore_index=True)

    result = build_completed_study_author_context_summary(history)

    role_row = result.loc[
        result["context_dimension_name"].eq("EFFECTIVE_ROLE")
        & result["context_dimension_value"].eq("COORDINATOR")
        & result["final_completion_authoring_mode"].eq("AI")
    ].iloc[0]

    assert role_row["completed_study_count"] == 2
    assert role_row["mode_completed_study_count"] == 3
    assert role_row["all_completed_study_count"] == 5
    assert role_row["completed_study_percentage_within_mode"] == pytest.approx(
        200.0 / 3.0
    )
    assert role_row["completed_study_percentage_overall"] == 40.0
    assert role_row["distinct_completion_author_count"] == 2
    assert "attempt_author_user_name" not in result.columns
    assert "study_num" not in result.columns


def test_empty_input_has_stable_columns() -> None:
    """Return the exact schema when no completed studies exist."""
    history = _attempt_history()
    history["is_completed_attempt"] = False

    result = build_completed_study_author_context_summary(history)

    assert result.empty
    assert tuple(result.columns) == COMPLETED_STUDY_AUTHOR_CONTEXT_COLUMNS


def test_rejects_multiple_completed_attempts_for_one_study() -> None:
    """Protect the one-completed-attempt-per-study analytical contract."""
    history = _attempt_history()
    history.loc[0, "is_completed_attempt"] = True

    with pytest.raises(
        ValueError,
        match="exactly one completed attempt per completed study",
    ):
        build_completed_study_author_context_summary(history)


def test_rejects_missing_required_columns() -> None:
    """Fail clearly when the explicit history input contract is incomplete."""
    history = _attempt_history().drop(columns=["effective_attempt_author_role"])

    with pytest.raises(
        ValueError,
        match="effective_attempt_author_role",
    ):
        build_completed_study_author_context_summary(history)


def test_rejects_nonboolean_pi_status() -> None:
    """Prevent unexpected PI values from disappearing during grouping."""
    history = _attempt_history().astype({"attempt_author_is_study_pi": "object"})
    history.loc[1, "attempt_author_is_study_pi"] = "PI"

    with pytest.raises(
        ValueError,
        match="Boolean PI status",
    ):
        build_completed_study_author_context_summary(history)
