from collections.abc import Callable

import pandas as pd
import pytest

from study_posting_audit_exploration import (
    ExplorationValidationError,
)
from study_posting_audit_exploration.derivation import (
    EDIT_INTENSITY_THRESHOLD_SCHEME,
    classify_edit_intensity,
    derive_completed_ai_field_analysis,
)
from study_posting_audit_exploration.input_contracts import (
    AI_ASSISTANCE_COLUMNS,
    RECORD_COLUMNS,
)


@pytest.mark.parametrize(
    ("match_type", "ratio", "suggestion_count", "final_count", "expected"),
    [
        ("EXACT", 0.0, 100, 100, "EXACT"),
        ("COSMETIC_EQUIVALENT", 0.05, 100, 100, "COSMETIC"),
        ("EDITED", 0.0, 100, 100, "LIGHT_EDIT"),
        ("EDITED", 0.10, 100, 100, "LIGHT_EDIT"),
        ("EDITED", 0.100001, 100, 100, "MODERATE_EDIT"),
        ("EDITED", 0.30, 100, 100, "MODERATE_EDIT"),
        ("EDITED", 0.300001, 100, 100, "HEAVY_EDIT"),
        ("EDITED", None, None, 100, "REPLACED"),
        ("REMOVED", None, None, None, "CLEARED"),
        ("UNASSISTED", None, None, None, "UNASSISTED"),
    ],
)
def test_classify_edit_intensity(
    match_type: str,
    ratio: float | None,
    suggestion_count: int | None,
    final_count: int | None,
    expected: str,
) -> None:
    assert (
        classify_edit_intensity(
            match_type=match_type,
            character_edit_ratio=ratio,
            suggestion_character_count=suggestion_count,
            final_character_count=final_count,
        )
        == expected
    )


def test_classify_edit_intensity_rejects_unknown_match_type() -> None:
    with pytest.raises(
        ExplorationValidationError,
        match="unsupported AI-assistance match type",
    ):
        classify_edit_intensity(
            match_type="SYNTHETIC_UNKNOWN",
            character_edit_ratio=None,
            suggestion_character_count=None,
            final_character_count=None,
        )


def test_edited_row_requires_usable_metrics() -> None:
    with pytest.raises(
        ExplorationValidationError,
        match="lacks usable character lengths",
    ):
        classify_edit_intensity(
            match_type="EDITED",
            character_edit_ratio=None,
            suggestion_character_count=None,
            final_character_count=None,
        )


def _metric_row(
    *,
    record_id: int,
    field_name: str,
    match_type: str,
    edit_distance: int | None,
    suggestion_count: int | None,
    final_count: int | None,
) -> dict[str, object]:
    """Return one complete synthetic AI-assistance row."""
    row: dict[str, object] = dict.fromkeys(AI_ASSISTANCE_COLUMNS, None)
    row.update(
        {
            "record_id": record_id,
            "field_name": field_name,
            "analysis_type": "TEXT",
            "match_type": match_type,
            "suggestion_count_total": 1,
            "suggestion_counts_json": '{"title": 1}',
            "picked_kind": field_name,
            "picked_index": 0,
            "character_edit_distance": edit_distance,
            "suggestion_character_count": suggestion_count,
            "final_character_count": final_count,
            "ter_rate": 0.25,
            "soft_word_edit_distance": 1.0,
            "policy_adjusted_effort_saved": 0.75,
            "estimated_characters_saved": 10.0,
            "offered_ids": "[1, 2]",
            "picked_ids": "[1]",
            "saved_ids": "[1, 3]",
            "kept_ids": "[1]",
            "dropped_ids": "[]",
            "added_ids": "[3]",
            "saved_not_offered_ids": "[3]",
            "flag_suggested": "true",
            "flag_saved": "false",
            "flag_accepted": "false",
            "flag_changed": "true",
            "compensation_text_required": "false",
        }
    )

    return row


def _record_row(
    *,
    record_id: int,
    study_num: str,
    attempt_type: str,
    attempt_result: str,
) -> dict[str, object]:
    """Return the record columns consumed by edit derivation."""
    row: dict[str, object] = dict.fromkeys(RECORD_COLUMNS, None)
    row.update(
        {
            "ID": record_id,
            "STUDY_NUM": study_num,
            "ATTEMPT_TYPE": attempt_type,
            "ATTEMPT_RESULT": attempt_result,
        }
    )

    return row


def test_derive_completed_ai_field_analysis_adds_ratio_and_context() -> None:
    metrics = pd.DataFrame.from_records(
        [
            _metric_row(
                record_id=1,
                field_name="title",
                match_type="EDITED",
                edit_distance=20,
                suggestion_count=100,
                final_count=80,
            )
        ],
        columns=list(AI_ASSISTANCE_COLUMNS),
    )
    records = pd.DataFrame.from_records(
        [
            _record_row(
                record_id=1,
                study_num="SYNTHETIC-STUDY",
                attempt_type="AI",
                attempt_result="COMPLETE",
            )
        ],
        columns=list(RECORD_COLUMNS),
    )

    derived = derive_completed_ai_field_analysis(
        metrics,
        records,
    )

    assert len(derived) == 1
    row = derived.iloc[0]
    assert row["audit_record_id"] == 1
    assert row["study_num"] == "SYNTHETIC-STUDY"
    assert row["character_edit_ratio"] == pytest.approx(0.20)
    assert row["edit_intensity_category"] == "MODERATE_EDIT"
    assert (
        row["edit_intensity_threshold_scheme_name"] == EDIT_INTENSITY_THRESHOLD_SCHEME
    )
    assert row["suggestion_counts_json"] == '{"title": 1}'
    assert row["picked_ids"] == "[1]"
    assert row["saved_ids"] == "[1, 3]"
    assert row["compensation_text_required"] == "false"
    assert "selected_text" not in derived.columns
    assert "final_text" not in derived.columns


def test_derive_completed_ai_field_analysis_filters_attempt_context() -> None:
    metrics = pd.DataFrame.from_records(
        [
            _metric_row(
                record_id=1,
                field_name="title",
                match_type="EXACT",
                edit_distance=0,
                suggestion_count=20,
                final_count=20,
            ),
            _metric_row(
                record_id=2,
                field_name="purpose",
                match_type="EXACT",
                edit_distance=0,
                suggestion_count=20,
                final_count=20,
            ),
        ],
        columns=list(AI_ASSISTANCE_COLUMNS),
    )
    records = pd.DataFrame.from_records(
        [
            _record_row(
                record_id=1,
                study_num="SYNTHETIC-COMPLETE",
                attempt_type="AI",
                attempt_result="COMPLETE",
            ),
            _record_row(
                record_id=2,
                study_num="SYNTHETIC-INCOMPLETE",
                attempt_type="AI",
                attempt_result="USER_DROPPED",
            ),
        ],
        columns=list(RECORD_COLUMNS),
    )

    derived = derive_completed_ai_field_analysis(
        metrics,
        records,
    )

    assert derived["audit_record_id"].tolist() == [1]


def test_derive_completed_ai_field_analysis_uses_larger_text_length() -> None:
    metrics = pd.DataFrame.from_records(
        [
            _metric_row(
                record_id=1,
                field_name="description",
                match_type="EDITED",
                edit_distance=30,
                suggestion_count=50,
                final_count=100,
            )
        ],
        columns=list(AI_ASSISTANCE_COLUMNS),
    )
    records = pd.DataFrame.from_records(
        [
            _record_row(
                record_id=1,
                study_num="SYNTHETIC-STUDY",
                attempt_type="AI",
                attempt_result="COMPLETE",
            )
        ],
        columns=list(RECORD_COLUMNS),
    )

    derived = derive_completed_ai_field_analysis(
        metrics,
        records,
    )

    assert derived.loc[0, "character_edit_ratio"] == pytest.approx(0.30)
    assert derived.loc[0, "edit_intensity_category"] == "MODERATE_EDIT"


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda frame: frame.drop(columns=["match_type"]),
            "ai_assistance_metrics lacks required columns",
        ),
        (
            lambda frame: frame.drop(columns=["ATTEMPT_RESULT"]),
            "records lacks required columns",
        ),
    ],
)
def test_derive_completed_ai_field_analysis_requires_columns(
    mutate: Callable[[pd.DataFrame], pd.DataFrame],
    message: str,
) -> None:
    metrics = pd.DataFrame.from_records(
        [
            _metric_row(
                record_id=1,
                field_name="title",
                match_type="EXACT",
                edit_distance=0,
                suggestion_count=20,
                final_count=20,
            )
        ],
        columns=list(AI_ASSISTANCE_COLUMNS),
    )
    records = pd.DataFrame.from_records(
        [
            _record_row(
                record_id=1,
                study_num="SYNTHETIC-STUDY",
                attempt_type="AI",
                attempt_result="COMPLETE",
            )
        ],
        columns=list(RECORD_COLUMNS),
    )

    if message.startswith("ai_assistance"):
        metrics = mutate(metrics)
    else:
        records = mutate(records)

    with pytest.raises(
        ExplorationValidationError,
        match=message,
    ):
        derive_completed_ai_field_analysis(
            metrics,
            records,
        )
