import pandas as pd
import pytest

from study_posting_audit_exploration import (
    ExplorationValidationError,
    build_nontext_field_adoption_summary,
)


def lookup_row(
    *,
    audit_record_id: int,
    field_name: str,
    picked_ids: str,
    saved_ids: str,
    similarity: float,
) -> dict[str, object]:
    """Return one synthetic lookup field row."""
    return {
        "audit_record_id": audit_record_id,
        "field_name": field_name,
        "analysis_type": "LOOKUP",
        "picked_ids": picked_ids,
        "saved_ids": saved_ids,
        "lookup_similarity": similarity,
        "flag_suggested": None,
        "flag_saved": None,
    }


def compensation_row(
    *,
    audit_record_id: int,
    suggested: str | None,
    saved: str | None,
) -> dict[str, object]:
    """Return one synthetic compensation row."""
    return {
        "audit_record_id": audit_record_id,
        "field_name": "compensation",
        "analysis_type": "COMPENSATION",
        "picked_ids": None,
        "saved_ids": None,
        "lookup_similarity": None,
        "flag_suggested": suggested,
        "flag_saved": saved,
    }


def test_lookup_summary_reports_set_outcomes() -> None:
    fields = pd.DataFrame.from_records(
        [
            lookup_row(
                audit_record_id=1,
                field_name="topics",
                picked_ids="[1, 2]",
                saved_ids="[1, 2]",
                similarity=1.0,
            ),
            lookup_row(
                audit_record_id=2,
                field_name="topics",
                picked_ids="[1, 2]",
                saved_ids="[2, 3]",
                similarity=1.0 / 3.0,
            ),
            lookup_row(
                audit_record_id=3,
                field_name="topics",
                picked_ids="[1]",
                saved_ids="[3]",
                similarity=0.0,
            ),
            lookup_row(
                audit_record_id=4,
                field_name="topics",
                picked_ids="[]",
                saved_ids="[]",
                similarity=0.0,
            ),
        ]
    )

    row = build_nontext_field_adoption_summary(fields).iloc[0]

    assert row["field_name"] == "topics"
    assert row["analysis_type"] == "LOOKUP"
    assert row["completed_ai_attempt_count"] == 4
    assert row["attempt_count_with_ai_value_selected"] == 3
    assert row["attempt_count_final_equal_to_selected"] == 1
    assert row["attempt_count_final_different_from_selected"] == 2
    assert row["attempt_count_final_missing"] == 1
    assert row["selection_percentage"] == pytest.approx(75.0)
    assert row["attempt_count_exact_set_match"] == 1
    assert row["attempt_count_partial_set_overlap"] == 1
    assert row["attempt_count_no_set_overlap"] == 1
    assert row["median_selected_final_lookup_similarity"] == pytest.approx(1.0 / 3.0)
    assert row["average_selected_final_lookup_similarity"] == pytest.approx(4.0 / 9.0)


def test_compensation_flag_summary_reports_boolean_outcomes() -> None:
    fields = pd.DataFrame.from_records(
        [
            compensation_row(
                audit_record_id=1,
                suggested="true",
                saved="true",
            ),
            compensation_row(
                audit_record_id=2,
                suggested="true",
                saved="false",
            ),
            compensation_row(
                audit_record_id=3,
                suggested=None,
                saved="false",
            ),
            compensation_row(
                audit_record_id=4,
                suggested="false",
                saved=None,
            ),
        ]
    )

    row = build_nontext_field_adoption_summary(fields).iloc[0]

    assert row["field_name"] == "offersCompensation"
    assert row["analysis_type"] == "BOOLEAN"
    assert row["completed_ai_attempt_count"] == 4
    assert row["attempt_count_with_ai_value_selected"] == 3
    assert row["attempt_count_final_equal_to_selected"] == 1
    assert row["attempt_count_final_different_from_selected"] == 1
    assert row["attempt_count_final_missing"] == 1
    assert row["selection_percentage"] == pytest.approx(75.0)
    assert row["final_equal_to_selected_percentage_among_selected"] == (
        pytest.approx(100.0 / 3.0)
    )
    assert row["attempt_count_exact_set_match"] is None


def test_nontext_summary_separates_lookup_fields() -> None:
    fields = pd.DataFrame.from_records(
        [
            lookup_row(
                audit_record_id=1,
                field_name="department",
                picked_ids="[1]",
                saved_ids="[1]",
                similarity=1.0,
            ),
            lookup_row(
                audit_record_id=1,
                field_name="topics",
                picked_ids="[2]",
                saved_ids="[2]",
                similarity=1.0,
            ),
        ]
    )

    summary = build_nontext_field_adoption_summary(fields)

    assert summary["field_name"].tolist() == [
        "department",
        "topics",
    ]


def test_nontext_summary_handles_empty_input() -> None:
    summary = build_nontext_field_adoption_summary(
        pd.DataFrame(
            columns=[
                "audit_record_id",
                "field_name",
                "analysis_type",
                "picked_ids",
                "saved_ids",
                "lookup_similarity",
                "flag_suggested",
                "flag_saved",
            ]
        )
    )

    assert summary.empty
    assert "field_name" in summary.columns
    assert "attempt_count_exact_set_match" in summary.columns


@pytest.mark.parametrize(
    ("column_name", "value", "message"),
    [
        ("picked_ids", "not-json", "contains invalid JSON"),
        ("saved_ids", '{"id": 1}', "must contain a JSON array"),
        ("picked_ids", "[true]", "non-integer identifier"),
    ],
)
def test_lookup_summary_rejects_invalid_serialized_sets(
    column_name: str,
    value: str,
    message: str,
) -> None:
    row = lookup_row(
        audit_record_id=1,
        field_name="topics",
        picked_ids="[1]",
        saved_ids="[1]",
        similarity=1.0,
    )
    row[column_name] = value

    with pytest.raises(
        ExplorationValidationError,
        match=message,
    ):
        build_nontext_field_adoption_summary(pd.DataFrame.from_records([row]))


def test_compensation_summary_rejects_invalid_boolean() -> None:
    fields = pd.DataFrame.from_records(
        [
            compensation_row(
                audit_record_id=1,
                suggested="SYNTHETIC_UNKNOWN",
                saved="true",
            )
        ]
    )

    with pytest.raises(
        ExplorationValidationError,
        match="invalid serialized value",
    ):
        build_nontext_field_adoption_summary(fields)
