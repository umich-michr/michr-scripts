"""Synthetic report fixtures for exploration tests."""

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from study_posting_audit_exploration.input_contracts import (
    AI_ASSISTANCE_COLUMNS,
    AI_ASSISTANCE_METRICS_FILENAME,
    READABILITY_COLUMNS,
    READABILITY_METRICS_FILENAME,
    RECORD_COLUMNS,
    RECORDS_FILENAME,
)


def write_csv(
    path: Path,
    *,
    columns: tuple[str, ...],
    rows: list[dict[str, object]],
) -> None:
    """Write one synthetic CSV using the report null marker."""
    with path.open(
        mode="w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=columns,
            lineterminator="\n",
        )
        writer.writeheader()

        for row in rows:
            writer.writerow(
                {
                    column: "\\N" if row.get(column) is None else row.get(column, "")
                    for column in columns
                }
            )


@dataclass(frozen=True, slots=True)
class RecordRowOptions:
    """Synthetic values used to construct one records.csv row."""

    audit_id: int
    study_num: str
    author_user_name: str
    attempt_type: str
    attempt_result: str
    start_time: str
    end_time: str | None
    user_id: int | None
    created_by_id: int | None
    created_date: str | None
    department: str | None


def record_row(
    options: RecordRowOptions,
) -> dict[str, object]:
    """Return one complete synthetic records.csv row mapping."""
    row: dict[str, object] = dict.fromkeys(RECORD_COLUMNS, None)
    row.update(
        {
            "ID": options.audit_id,
            "START_TIME": options.start_time,
            "END_TIME": options.end_time,
            "ATTEMPT_TYPE": options.attempt_type,
            "ATTEMPT_RESULT": options.attempt_result,
            "USER_TYPE": "SYNTHETIC",
            "STUDY_NUM": options.study_num,
            "CREATED_DATE": options.created_date,
            "CREATED_BY_ID": options.created_by_id,
            "PUBLISHABLE": "true",
            "STUDY_DEPARTMENT": options.department,
            "STUDY_PARTICIPANT_TYPE": "HEALTHY",
            "USER_ID": options.user_id,
            "AUTHOR_USER_NAME": options.author_user_name,
            "AUTHOR_STUDY_TEAM_ROLE": "TEAM_MEMBER",
            "AUTHOR_ERESEARCH_ROLE": None,
            "AUTHOR_APPOINTMENTS": (
                "Synthetic Title:Synthetic Department:Synthetic School"
            ),
            "PI_USER_NAME": "synthetic-pi@example.edu",
            "PI_APPOINTMENTS": (
                "Synthetic PI Title:Synthetic Department:Synthetic School"
            ),
            "PRIOR_CREATED_COUNT": 0,
            "TOTAL_CREATED_COUNT": 1,
            "MEMBER_OF_OTHER_STUDIES_COUNT": 0,
            "LOGIN_DAYS": 10,
            "MIN_LOGIN_TIME": "2026-01-01T09:00:00",
            "MAX_LOGIN_TIME": "2026-07-01T09:00:00",
            "TIME_SPENT_ON_STUDY_INFO_PAGE_MS": 1000,
            "TIME_TO_FINISH_ADDING_STUDY_MS": (
                60000 if options.attempt_result == "COMPLETE" else None
            ),
            "LATENCY_MS": 500 if options.attempt_type == "AI" else None,
            "SOURCE_SIZE_CHARS": 100 if options.attempt_type == "AI" else None,
            "SOURCE_TYPE": ("SYNTHETIC_TEXT" if options.attempt_type == "AI" else None),
            "STUDY_CONTENT_SOURCE": (
                "Synthetic source" if options.attempt_type == "AI" else None
            ),
            "LLM_INFERRED_STUDY_CONTENT_SOURCE": (
                "Synthetic source" if options.attempt_type == "AI" else None
            ),
        }
    )

    return row


def ai_assistance_row(
    *,
    audit_id: int,
    field_name: str = "title",
) -> dict[str, object]:
    """Return one synthetic AI-assistance metric row."""
    row: dict[str, object] = dict.fromkeys(AI_ASSISTANCE_COLUMNS, None)
    row.update(
        {
            "record_id": audit_id,
            "field_name": field_name,
            "analysis_type": "TEXT",
            "match_type": "EXACT",
            "suggestion_count_total": 1,
            "suggestion_counts_json": '{"title":1}',
            "picked_kind": "title",
            "picked_index": 0,
            "ter_rate": 0.0,
            "ter_effort_saved_raw": 1.0,
            "ter_effort_saved": 1.0,
            "policy_adjusted_effort_saved": 1.0,
            "character_edit_distance": 0,
            "character_effort_saved_raw": 1.0,
            "character_effort_saved": 1.0,
            "soft_word_edit_distance": 0.0,
            "soft_word_effort_saved_raw": 1.0,
            "soft_word_effort_saved": 1.0,
            "estimated_characters_saved": 20.0,
            "suggestion_character_count": 20,
            "final_character_count": 20,
            "suggestion_word_count": 3,
            "final_word_count": 3,
        }
    )

    return row


def readability_rows(
    *,
    audit_id: int,
) -> list[dict[str, object]]:
    """Return one selected suggestion and matching final readability row."""
    common = {
        "record_id": audit_id,
        "attempt_type": "AI",
        "field_name": "title",
        "flesch_kincaid_grade": 7.0,
        "automated_readability_index": 7.5,
        "coleman_liau_index": 8.0,
        "gunning_fog": 8.5,
        "dale_chall_readability_score": 6.0,
        "estimated_reading_time_seconds": 1.0,
        "sentence_count": 1,
        "word_count": 5,
        "syllable_count": 7,
        "letter_count": 25,
        "polysyllable_count": 1,
    }

    return [
        {
            **common,
            "text_role": "SUGGESTED",
            "suggestion_kind": "title",
            "suggestion_index": 0,
            "selected": "true",
        },
        {
            **common,
            "text_role": "FINAL",
            "suggestion_kind": None,
            "suggestion_index": None,
            "selected": None,
        },
    ]


@pytest.fixture
def valid_report_directory(tmp_path: Path) -> Path:
    """Write one valid synthetic normalized report directory."""
    directory = tmp_path / "report"
    directory.mkdir()

    records = [
        record_row(
            RecordRowOptions(
                audit_id=1001,
                study_num="SYNTHETIC-STUDY-1",
                author_user_name="first-author@example.edu",
                attempt_type="AI",
                attempt_result="USER_DROPPED",
                start_time="2026-06-01T09:00:00",
                end_time=None,
                user_id=101,
                created_by_id=202,
                created_date="2026-06-02T10:01:00",
                department="Synthetic Department",
            )
        ),
        record_row(
            RecordRowOptions(
                audit_id=1002,
                study_num="SYNTHETIC-STUDY-1",
                author_user_name="completion-author@example.edu",
                attempt_type="AI",
                attempt_result="COMPLETE",
                start_time="2026-06-02T10:00:00",
                end_time="2026-06-02T10:01:00",
                user_id=202,
                created_by_id=202,
                created_date="2026-06-02T10:01:00",
                department="Synthetic Department",
            )
        ),
    ]

    write_csv(
        directory / RECORDS_FILENAME,
        columns=RECORD_COLUMNS,
        rows=records,
    )
    write_csv(
        directory / AI_ASSISTANCE_METRICS_FILENAME,
        columns=AI_ASSISTANCE_COLUMNS,
        rows=[ai_assistance_row(audit_id=1002)],
    )
    write_csv(
        directory / READABILITY_METRICS_FILENAME,
        columns=READABILITY_COLUMNS,
        rows=readability_rows(audit_id=1002),
    )

    return directory


@pytest.fixture
def report_rows() -> dict[str, Any]:
    """Expose synthetic row builders for focused mutation tests."""
    return {
        "record_row": record_row,
        "ai_assistance_row": ai_assistance_row,
        "readability_rows": readability_rows,
        "write_csv": write_csv,
        "RecordRowOptions": RecordRowOptions,
    }
