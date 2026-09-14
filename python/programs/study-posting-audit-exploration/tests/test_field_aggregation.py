import pandas as pd
import pytest

from study_posting_audit_exploration import (
    build_field_adoption_editing_summary,
)


def field_row(
    *,
    audit_record_id: int,
    field_name: str,
    category: str,
    suggestion_count: int = 1,
    picked_index: int | None = 0,
    ratio: float | None = None,
    ter_rate: float | None = None,
    analysis_type: str = "TEXT",
) -> dict[str, object]:
    """Return one synthetic completed-AI field-analysis row."""
    return {
        "audit_record_id": audit_record_id,
        "field_name": field_name,
        "analysis_type": analysis_type,
        "suggestion_count_total": suggestion_count,
        "picked_index": picked_index,
        "character_edit_ratio": ratio,
        "ter_rate": ter_rate,
        "edit_intensity_category": category,
        "edit_intensity_threshold_scheme_name": ("EXPLORATORY_CHARACTER_RATIO_10_30"),
    }


def test_field_adoption_summary_counts_each_outcome() -> None:
    fields = pd.DataFrame.from_records(
        [
            field_row(
                audit_record_id=1,
                field_name="title",
                category="EXACT",
                ratio=0.0,
                ter_rate=0.0,
            ),
            field_row(
                audit_record_id=2,
                field_name="title",
                category="COSMETIC",
                ratio=0.01,
                ter_rate=0.0,
            ),
            field_row(
                audit_record_id=3,
                field_name="title",
                category="LIGHT_EDIT",
                ratio=0.10,
                ter_rate=0.10,
            ),
            field_row(
                audit_record_id=4,
                field_name="title",
                category="MODERATE_EDIT",
                ratio=0.20,
                ter_rate=0.20,
            ),
            field_row(
                audit_record_id=5,
                field_name="title",
                category="HEAVY_EDIT",
                ratio=0.50,
                ter_rate=0.50,
            ),
            field_row(
                audit_record_id=6,
                field_name="title",
                category="EDITED_UNCLASSIFIED",
                ratio=None,
                ter_rate=None,
            ),
            field_row(
                audit_record_id=7,
                field_name="title",
                category="REPLACED",
                ratio=None,
                ter_rate=None,
            ),
            field_row(
                audit_record_id=8,
                field_name="title",
                category="CLEARED",
                ratio=None,
                ter_rate=None,
            ),
            field_row(
                audit_record_id=9,
                field_name="title",
                category="UNASSISTED",
                suggestion_count=1,
                picked_index=None,
                ratio=None,
                ter_rate=None,
            ),
        ]
    )

    summary = build_field_adoption_editing_summary(fields)
    row = summary.iloc[0]

    assert row["completed_ai_attempt_count"] == 9
    assert row["completed_ai_attempt_count_with_suggestion_offered"] == 9
    assert row["completed_ai_attempt_count_with_suggestion_selected"] == 8
    assert row["completed_ai_attempt_count_selected_and_exactly_retained"] == 1
    assert row["completed_ai_attempt_count_selected_and_cosmetically_changed"] == 1
    assert row["completed_ai_attempt_count_selected_and_lightly_edited"] == 1
    assert row["completed_ai_attempt_count_selected_and_moderately_edited"] == 1
    assert row["completed_ai_attempt_count_selected_and_heavily_edited"] == 1
    assert row["completed_ai_attempt_count_selected_and_unclassified_edit"] == 1
    assert row["completed_ai_attempt_count_selected_and_replaced"] == 1
    assert row["completed_ai_attempt_count_selected_then_cleared"] == 1
    assert row["completed_ai_attempt_count_unassisted"] == 1
    assert row[
        "suggestion_selection_percentage_among_attempts_with_offer"
    ] == pytest.approx(100.0 * 8.0 / 9.0)
    assert row["exact_retention_percentage_among_selected_attempts"] == (
        pytest.approx(12.5)
    )
    assert row["unclassified_edit_percentage_among_selected_attempts"] == (
        pytest.approx(12.5)
    )


def test_field_adoption_summary_describes_only_edits_with_usable_metrics() -> None:
    fields = pd.DataFrame.from_records(
        [
            field_row(
                audit_record_id=1,
                field_name="description",
                category="LIGHT_EDIT",
                ratio=0.10,
                ter_rate=0.20,
            ),
            field_row(
                audit_record_id=2,
                field_name="description",
                category="HEAVY_EDIT",
                ratio=0.50,
                ter_rate=0.60,
            ),
            field_row(
                audit_record_id=3,
                field_name="description",
                category="EDITED_UNCLASSIFIED",
                ratio=None,
                ter_rate=None,
            ),
        ]
    )

    row = build_field_adoption_editing_summary(fields).iloc[0]

    assert row["completed_ai_attempt_count_selected_and_unclassified_edit"] == 1
    assert row["median_character_edit_ratio_among_edited_attempts"] == (
        pytest.approx(0.30)
    )
    assert row["average_character_edit_ratio_among_edited_attempts"] == (
        pytest.approx(0.30)
    )
    assert row["median_ter_rate_among_edited_attempts"] == pytest.approx(0.40)
    assert row["average_ter_rate_among_edited_attempts"] == pytest.approx(0.40)


def test_field_adoption_summary_separates_fields_and_analysis_types() -> None:
    fields = pd.DataFrame.from_records(
        [
            field_row(
                audit_record_id=1,
                field_name="title",
                category="EXACT",
            ),
            field_row(
                audit_record_id=1,
                field_name="compensation",
                category="EXACT",
                analysis_type="COMPENSATION",
            ),
            field_row(
                audit_record_id=1,
                field_name="topics",
                category="EXACT",
                analysis_type="LOOKUP",
            ),
        ]
    )

    summary = build_field_adoption_editing_summary(fields)

    assert summary[
        [
            "field_name",
            "analysis_type",
        ]
    ].to_records(index=False).tolist() == [
        ("compensation", "COMPENSATION"),
        ("title", "TEXT"),
    ]


def test_field_adoption_summary_handles_empty_input() -> None:
    summary = build_field_adoption_editing_summary(
        pd.DataFrame(
            columns=[
                "audit_record_id",
                "field_name",
                "analysis_type",
                "suggestion_count_total",
                "picked_index",
                "character_edit_ratio",
                "ter_rate",
                "edit_intensity_category",
                "edit_intensity_threshold_scheme_name",
            ]
        )
    )

    assert summary.empty
    assert "field_name" in summary.columns
    assert "completed_ai_attempt_count" in summary.columns
    assert (
        "completed_ai_attempt_count_selected_and_unclassified_edit" in summary.columns
    )
    assert "unclassified_edit_percentage_among_selected_attempts" in summary.columns
