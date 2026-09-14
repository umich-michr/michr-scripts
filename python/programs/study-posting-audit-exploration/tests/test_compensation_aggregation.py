import pandas as pd
import pytest

from study_posting_audit_exploration import (
    ExplorationValidationError,
    build_compensation_analysis_summary,
)


def compensation_row(
    *,
    audit_record_id: int,
    counts: str,
    picked_kind: str | None,
    picked_index: int | None,
    category: str,
    ratio: float | None,
) -> dict[str, object]:
    """Return one synthetic completed-AI compensation row."""
    return {
        "audit_record_id": audit_record_id,
        "field_name": "compensation",
        "analysis_type": "COMPENSATION",
        "suggestion_counts_json": counts,
        "picked_kind": picked_kind,
        "picked_index": picked_index,
        "edit_intensity_category": category,
        "character_edit_ratio": ratio,
        "edit_intensity_threshold_scheme_name": ("EXPLORATORY_CHARACTER_RATIO_10_30"),
    }


def summary_row(
    summary: pd.DataFrame,
    suggestion_kind: str,
) -> pd.Series:
    """Return one compensation-kind summary row."""
    return summary.loc[
        summary["compensation_suggestion_kind"].eq(suggestion_kind)
    ].iloc[0]


def test_compensation_summary_reports_kind_selection_and_editing() -> None:
    fields = pd.DataFrame.from_records(
        [
            compensation_row(
                audit_record_id=1,
                counts=('{"genericCompensation": 2, "specificCompensation": 1}'),
                picked_kind="genericCompensation",
                picked_index=0,
                category="EXACT",
                ratio=0.0,
            ),
            compensation_row(
                audit_record_id=2,
                counts=('{"genericCompensation": 1, "specificCompensation": 2}'),
                picked_kind="specificCompensation",
                picked_index=1,
                category="MODERATE_EDIT",
                ratio=0.20,
            ),
            compensation_row(
                audit_record_id=3,
                counts=('{"genericCompensation": 1, "specificCompensation": 0}'),
                picked_kind=None,
                picked_index=None,
                category="UNASSISTED",
                ratio=None,
            ),
        ]
    )

    summary = build_compensation_analysis_summary(fields)
    generic = summary_row(summary, "genericCompensation")
    specific = summary_row(summary, "specificCompensation")

    assert generic["completed_ai_attempt_count_with_suggestion"] == 3
    assert generic["offered_suggestion_count"] == 4
    assert generic["selected_suggestion_count"] == 1
    assert generic["suggestion_selection_percentage"] == pytest.approx(25.0)
    assert generic["selected_suggestion_count_exactly_retained"] == 1
    assert generic["selected_suggestion_count_moderately_edited"] == 0

    assert specific["completed_ai_attempt_count_with_suggestion"] == 2
    assert specific["offered_suggestion_count"] == 3
    assert specific["selected_suggestion_count"] == 1
    assert specific["suggestion_selection_percentage"] == pytest.approx(100.0 / 3.0)
    assert specific["selected_suggestion_count_moderately_edited"] == 1
    assert specific["median_character_edit_ratio"] == pytest.approx(0.20)
    assert specific["average_character_edit_ratio"] == pytest.approx(0.20)


def test_compensation_summary_reports_zero_without_readability_pairs() -> None:
    fields = pd.DataFrame.from_records(
        [
            compensation_row(
                audit_record_id=1,
                counts='{"genericCompensation": 1}',
                picked_kind="genericCompensation",
                picked_index=0,
                category="LIGHT_EDIT",
                ratio=0.10,
            )
        ]
    )

    row = summary_row(
        build_compensation_analysis_summary(fields),
        "genericCompensation",
    )

    assert row["paired_selected_final_readability_count"] == 0
    assert pd.isna(row["median_flesch_kincaid_grade_change_final_minus_selected"])
    assert pd.isna(row["average_flesch_kincaid_grade_change_final_minus_selected"])
    assert row["count_consensus_grade_level_decrease"] == 0
    assert row["count_no_material_change"] == 0
    assert row["count_consensus_grade_level_increase"] == 0
    assert row["count_mixed_formula_direction"] == 0
    assert (
        row["edit_intensity_threshold_scheme_name"]
        == "EXPLORATORY_CHARACTER_RATIO_10_30"
    )


def test_compensation_summary_returns_canonical_empty_frame() -> None:
    summary = build_compensation_analysis_summary(
        pd.DataFrame(
            columns=[
                "audit_record_id",
                "analysis_type",
                "suggestion_counts_json",
                "picked_kind",
                "picked_index",
                "edit_intensity_category",
                "character_edit_ratio",
                "edit_intensity_threshold_scheme_name",
            ]
        )
    )

    assert summary.empty
    assert "compensation_suggestion_kind" in summary.columns
    assert "paired_selected_final_readability_count" in summary.columns


@pytest.mark.parametrize(
    ("counts", "message"),
    [
        ("not-json", "contains invalid JSON"),
        ("[]", "must contain a JSON object"),
        ('{"genericCompensation": -1}', "must contain a nonnegative integer"),
        ('{"genericCompensation": true}', "must contain a nonnegative integer"),
    ],
)
def test_compensation_summary_rejects_invalid_counts(
    counts: str,
    message: str,
) -> None:
    fields = pd.DataFrame.from_records(
        [
            compensation_row(
                audit_record_id=1,
                counts=counts,
                picked_kind=None,
                picked_index=None,
                category="UNASSISTED",
                ratio=None,
            )
        ]
    )

    with pytest.raises(
        ExplorationValidationError,
        match=message,
    ):
        build_compensation_analysis_summary(fields)


def test_compensation_summary_includes_readability_pairs() -> None:
    fields = pd.DataFrame.from_records(
        [
            compensation_row(
                audit_record_id=1,
                counts='{"genericCompensation": 1}',
                picked_kind="genericCompensation",
                picked_index=0,
                category="LIGHT_EDIT",
                ratio=0.10,
            ),
            compensation_row(
                audit_record_id=2,
                counts='{"genericCompensation": 1}',
                picked_kind="genericCompensation",
                picked_index=0,
                category="MODERATE_EDIT",
                ratio=0.20,
            ),
        ]
    )
    pairs = pd.DataFrame.from_records(
        [
            {
                "audit_record_id": 1,
                "field_name": "compensation",
                "suggestion_kind": "genericCompensation",
                "readability_measure_name": "flesch_kincaid_grade",
                "change_final_minus_selected": -1.0,
                "consensus_grade_level_direction_category": (
                    "CONSENSUS_GRADE_LEVEL_DECREASE"
                ),
            },
            {
                "audit_record_id": 2,
                "field_name": "compensation",
                "suggestion_kind": "genericCompensation",
                "readability_measure_name": "flesch_kincaid_grade",
                "change_final_minus_selected": 0.0,
                "consensus_grade_level_direction_category": ("NO_MATERIAL_CHANGE"),
            },
        ]
    )

    row = summary_row(
        build_compensation_analysis_summary(
            fields,
            pairs,
        ),
        "genericCompensation",
    )

    assert row["paired_selected_final_readability_count"] == 2
    assert row["median_flesch_kincaid_grade_change_final_minus_selected"] == -0.5
    assert row["average_flesch_kincaid_grade_change_final_minus_selected"] == -0.5
    assert row["count_consensus_grade_level_decrease"] == 1
    assert row["count_no_material_change"] == 1
    assert row["count_consensus_grade_level_increase"] == 0
    assert row["count_mixed_formula_direction"] == 0
