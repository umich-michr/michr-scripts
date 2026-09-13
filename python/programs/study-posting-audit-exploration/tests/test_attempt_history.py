from pathlib import Path
from typing import Any, cast

import pandas as pd
import pytest

from study_posting_audit_exploration import (
    ExplorationInputConfig,
    ExplorationValidationError,
    derive_attempt_histories,
    load_audit_report,
)


def loaded_records(path: Path) -> pd.DataFrame:
    """Load a fresh synthetic records DataFrame."""
    return load_audit_report(
        ExplorationInputConfig(
            report_directory=path,
        )
    ).records


def test_attempt_history_orders_and_marks_author_handoff(
    valid_report_directory: Path,
) -> None:
    records = loaded_records(valid_report_directory)

    tables = derive_attempt_histories(records)
    attempts = tables.study_attempt_author_history
    studies = tables.study_attempt_history
    authors = tables.author_history

    assert attempts["audit_record_id"].tolist() == [1001, 1002]
    assert attempts["attempt_sequence_number"].tolist() == [1, 2]
    assert attempts["same_author_as_completion_attempt"].tolist() == [
        False,
        True,
    ]
    assert attempts["author_changed_from_previous_attempt"].tolist() == [
        False,
        True,
    ]
    assert attempts["is_preceding_incomplete_attempt"].tolist() == [
        True,
        False,
    ]
    assert attempts["prior_studies_created_before_attempt_start_count"].astype(
        "Int64"
    ).tolist() == [0, 0]

    study = studies.iloc[0]

    assert study["study_num"] == "SYNTHETIC-STUDY-1"
    assert bool(study["study_is_completed"]) is True
    assert study["all_attempt_count"] == 2
    assert study["ai_attempt_count"] == 2
    assert study["manual_attempt_count"] == 0
    assert study["complete_attempt_count"] == 1
    assert study["incomplete_attempt_count"] == 1
    assert study["user_dropped_attempt_count"] == 1
    assert study["first_attempt_audit_record_id"] == 1001
    assert study["completed_attempt_audit_record_id"] == 1002
    assert study["distinct_attempt_author_count"] == 2
    assert bool(study["author_changed_between_attempts"]) is True
    assert bool(study["author_changed_before_completion"]) is True
    assert bool(study["first_attempt_author_matches_completion_author"]) is False
    assert (
        bool(study["immediately_preceding_author_matches_completion_author"]) is False
    )
    assert bool(study["completion_author_had_preceding_incomplete_attempt"]) is False
    assert bool(study["other_author_had_preceding_incomplete_attempt"]) is True
    assert study["preceding_incomplete_attempt_count"] == 1
    assert study["preceding_incomplete_attempt_count_by_completion_author"] == 0
    assert study["preceding_incomplete_attempt_count_by_other_authors"] == 1
    assert study["preceding_user_dropped_attempt_count"] == 1
    assert study["minutes_first_attempt_to_completion"] == pytest.approx(1_500.0)
    assert study["completed_attempt_study_info_page_minutes"] == pytest.approx(
        1.0 / 60.0
    )
    assert study["completed_attempt_total_duration_minutes"] == pytest.approx(1.0)
    assert bool(study["has_attempt_after_completion"]) is False

    assert set(authors["author_user_name"]) == {
        "first-author@example.edu",
        "completion-author@example.edu",
    }


def test_same_author_retry_is_distinguished_from_handoff(
    valid_report_directory: Path,
) -> None:
    records = loaded_records(valid_report_directory)
    records.loc[0, "AUTHOR_USER_NAME"] = records.loc[1, "AUTHOR_USER_NAME"]
    records.loc[0, "USER_ID"] = records.loc[1, "USER_ID"]

    study = derive_attempt_histories(records).study_attempt_history.iloc[0]

    assert bool(study["author_changed_before_completion"]) is False
    assert bool(study["completion_author_had_preceding_incomplete_attempt"]) is True
    assert bool(study["other_author_had_preceding_incomplete_attempt"]) is False
    assert study["preceding_incomplete_attempt_count_by_completion_author"] == 1


def test_study_without_completion_has_null_completion_context(
    valid_report_directory: Path,
) -> None:
    records = loaded_records(valid_report_directory)
    records = records.loc[records["ID"].eq(1001)].copy()

    tables = derive_attempt_histories(records)
    attempt = tables.study_attempt_author_history.iloc[0]
    study = tables.study_attempt_history.iloc[0]

    assert pd.isna(attempt["completion_author_user_name"])
    assert bool(attempt["same_author_as_completion_attempt"]) is False
    assert bool(attempt["is_preceding_incomplete_attempt"]) is False

    assert bool(study["study_is_completed"]) is False
    assert pd.isna(study["completed_attempt_audit_record_id"])
    assert study["minutes_first_attempt_to_completion"] is None
    assert study["immediately_preceding_author_matches_completion_author"] is None


def test_author_history_reports_mode_adoption_and_eventual_creation(
    valid_report_directory: Path,
) -> None:
    records = loaded_records(valid_report_directory)
    records.loc[0, "ATTEMPT_TYPE"] = "MANUAL"

    authors = derive_attempt_histories(records).author_history
    first = authors.loc[
        authors["author_user_name"].eq("first-author@example.edu")
    ].iloc[0]
    completion = authors.loc[
        authors["author_user_name"].eq("completion-author@example.edu")
    ].iloc[0]

    assert first["author_adoption_group"] == "MANUAL_ONLY"
    assert first["distinct_completed_study_count_authored"] == 0
    assert first["distinct_study_count_eventually_created"] == 1
    assert first["manual_attempt_count"] == 1

    assert completion["author_adoption_group"] == "AI_ONLY"
    assert completion["distinct_completed_study_count_authored"] == 1
    assert completion["completed_ai_study_count_authored"] == 1


def test_author_using_both_modes_is_classified_once(
    valid_report_directory: Path,
    report_rows: dict[str, Any],
) -> None:
    records = loaded_records(valid_report_directory)
    options_type = cast("Any", report_rows["RecordRowOptions"])
    record_builder = cast("Any", report_rows["record_row"])
    frame_builder = cast("Any", report_rows["loaded_record_frame"])
    extra = record_builder(
        options_type(
            audit_id=2001,
            study_num="SYNTHETIC-STUDY-2",
            author_user_name="completion-author@example.edu",
            attempt_type="MANUAL",
            attempt_result="USER_DROPPED",
            start_time="2026-07-01T10:00:00",
            end_time=None,
            user_id=202,
            created_by_id=None,
            created_date=None,
            department=None,
        )
    )
    records = pd.concat(
        [
            records,
            frame_builder([extra]),
        ],
        ignore_index=True,
    )

    authors = derive_attempt_histories(records).author_history
    author = authors.loc[
        authors["author_user_name"].eq("completion-author@example.edu")
    ].iloc[0]

    assert author["author_adoption_group"] == "BOTH_AI_AND_MANUAL"
    assert author["ai_attempt_count"] == 1
    assert author["manual_attempt_count"] == 1
    assert author["distinct_study_count_with_both_modes"] == 0


def test_attempt_history_rejects_duplicate_ids(
    valid_report_directory: Path,
) -> None:
    records = loaded_records(valid_report_directory)
    records.loc[1, "ID"] = records.loc[0, "ID"]

    with pytest.raises(
        ExplorationValidationError,
        match="requires unique non-null audit IDs",
    ):
        derive_attempt_histories(records)


def test_attempt_history_rejects_multiple_completions(
    valid_report_directory: Path,
) -> None:
    records = loaded_records(valid_report_directory)
    records.loc[0, "ATTEMPT_RESULT"] = "COMPLETE"
    records.loc[0, "END_TIME"] = pd.Timestamp("2026-06-01T09:01:00")

    with pytest.raises(
        ExplorationValidationError,
        match="at most one complete attempt per study",
    ):
        derive_attempt_histories(records)
