import pandas as pd
import pytest

from study_posting_audit_exploration import (
    ExplorationValidationError,
    build_field_edit_readability_cross_summary,
    build_field_readability_change_summary,
    build_selected_vs_unselected_readability_summary,
)
from study_posting_audit_exploration.input_contracts import (
    READABILITY_COLUMNS,
)


def suggestion_row(
    *,
    record_id: int,
    selected: str,
    grade: float,
    suggestion_index: int,
) -> dict[str, object]:
    """Return one synthetic readability suggestion row."""
    row: dict[str, object] = dict.fromkeys(READABILITY_COLUMNS, None)
    row.update(
        {
            "record_id": record_id,
            "attempt_type": "AI",
            "field_name": "title",
            "text_role": "SUGGESTED",
            "suggestion_kind": "title",
            "suggestion_index": suggestion_index,
            "selected": selected,
            "flesch_kincaid_grade": grade,
            "automated_readability_index": grade,
            "coleman_liau_index": grade,
            "gunning_fog": grade,
            "dale_chall_readability_score": grade,
            "estimated_reading_time_seconds": grade,
            "sentence_count": int(grade),
            "word_count": int(grade),
            "syllable_count": int(grade),
            "letter_count": int(grade),
            "polysyllable_count": int(grade),
        }
    )

    return row


def readability_pair(
    *,
    audit_record_id: int,
    field_name: str,
    measure_name: str,
    change: float,
    direction: str,
    consensus: str,
    category: str = "LIGHT_EDIT",
) -> dict[str, object]:
    """Return one synthetic selected/final readability-pair row."""
    return {
        "audit_record_id": audit_record_id,
        "field_name": field_name,
        "readability_measure_name": measure_name,
        "change_final_minus_selected": change,
        "readability_direction_category": direction,
        "consensus_grade_level_direction_category": consensus,
        "unchanged_absolute_tolerance": 0.1,
        "edit_intensity_category": category,
        "edit_intensity_threshold_scheme_name": ("EXPLORATORY_CHARACTER_RATIO_10_30"),
        "short_text_readability_caution": field_name == "title",
    }


def completed_field(
    *,
    audit_record_id: int,
    field_name: str,
    category: str,
) -> dict[str, object]:
    """Return one synthetic completed-AI field row."""
    return {
        "audit_record_id": audit_record_id,
        "field_name": field_name,
        "edit_intensity_category": category,
        "edit_intensity_threshold_scheme_name": ("EXPLORATORY_CHARACTER_RATIO_10_30"),
    }


def test_selected_vs_unselected_summary_uses_attempt_level_differences() -> None:
    readability = pd.DataFrame.from_records(
        [
            suggestion_row(
                record_id=1,
                selected="true",
                grade=8.0,
                suggestion_index=0,
            ),
            suggestion_row(
                record_id=1,
                selected="false",
                grade=6.0,
                suggestion_index=1,
            ),
            suggestion_row(
                record_id=1,
                selected="false",
                grade=10.0,
                suggestion_index=2,
            ),
            suggestion_row(
                record_id=2,
                selected="true",
                grade=7.0,
                suggestion_index=0,
            ),
            suggestion_row(
                record_id=2,
                selected="false",
                grade=8.0,
                suggestion_index=1,
            ),
        ],
        columns=list(READABILITY_COLUMNS),
    )

    summary = build_selected_vs_unselected_readability_summary(readability)
    grade = summary.loc[
        summary["readability_measure_name"].eq("flesch_kincaid_grade")
    ].iloc[0]

    assert (
        grade["completed_ai_attempt_count_with_selected_and_unselected_suggestions"]
        == 2
    )
    assert grade["minimum_selected_minus_mean_unselected_value"] == -1.0
    assert grade["median_selected_minus_mean_unselected_value"] == -0.5
    assert grade["average_selected_minus_mean_unselected_value"] == -0.5
    assert grade["maximum_selected_minus_mean_unselected_value"] == 0.0
    assert grade["attempt_count_selected_value_lower"] == 1
    assert grade["attempt_count_selected_value_equal_within_tolerance"] == 1
    assert grade["attempt_count_selected_value_higher"] == 0


def test_selected_vs_unselected_summary_skips_unpaired_attempts() -> None:
    readability = pd.DataFrame.from_records(
        [
            suggestion_row(
                record_id=1,
                selected="true",
                grade=8.0,
                suggestion_index=0,
            )
        ],
        columns=list(READABILITY_COLUMNS),
    )

    summary = build_selected_vs_unselected_readability_summary(readability)

    assert summary.empty
    assert "readability_measure_name" in summary.columns


@pytest.mark.parametrize(
    "tolerance",
    [
        -0.1,
        float("inf"),
        float("nan"),
    ],
)
def test_selected_vs_unselected_summary_rejects_invalid_tolerance(
    tolerance: float,
) -> None:
    readability = pd.DataFrame(columns=list(READABILITY_COLUMNS))

    with pytest.raises(
        ExplorationValidationError,
        match="tolerance must be finite and nonnegative",
    ):
        build_selected_vs_unselected_readability_summary(
            readability,
            equality_tolerance=tolerance,
        )


def test_field_readability_change_summary_reports_directions() -> None:
    pairs = pd.DataFrame.from_records(
        [
            readability_pair(
                audit_record_id=1,
                field_name="title",
                measure_name="flesch_kincaid_grade",
                change=-1.0,
                direction="VALUE_DECREASED",
                consensus="CONSENSUS_GRADE_LEVEL_DECREASE",
            ),
            readability_pair(
                audit_record_id=2,
                field_name="title",
                measure_name="flesch_kincaid_grade",
                change=0.0,
                direction="NO_MATERIAL_CHANGE",
                consensus="NO_MATERIAL_CHANGE",
            ),
            readability_pair(
                audit_record_id=3,
                field_name="title",
                measure_name="flesch_kincaid_grade",
                change=1.0,
                direction="VALUE_INCREASED",
                consensus="CONSENSUS_GRADE_LEVEL_INCREASE",
            ),
        ]
    )

    row = build_field_readability_change_summary(pairs).iloc[0]

    assert row["paired_selected_final_attempt_count"] == 3
    assert row["median_change_final_minus_selected"] == 0.0
    assert row["attempt_count_value_decreased"] == 1
    assert row["attempt_count_no_material_change"] == 1
    assert row["attempt_count_value_increased"] == 1
    assert row["percentage_value_decreased"] == pytest.approx(100.0 / 3.0)
    assert bool(row["short_text_readability_caution"]) is True


def test_field_edit_readability_cross_summary_uses_field_population() -> None:
    pairs = pd.DataFrame.from_records(
        [
            readability_pair(
                audit_record_id=1,
                field_name="title",
                measure_name="flesch_kincaid_grade",
                change=-1.0,
                direction="VALUE_DECREASED",
                consensus="CONSENSUS_GRADE_LEVEL_DECREASE",
            ),
            readability_pair(
                audit_record_id=2,
                field_name="title",
                measure_name="flesch_kincaid_grade",
                change=0.0,
                direction="NO_MATERIAL_CHANGE",
                consensus="NO_MATERIAL_CHANGE",
            ),
        ]
    )
    fields = pd.DataFrame.from_records(
        [
            completed_field(
                audit_record_id=1,
                field_name="title",
                category="LIGHT_EDIT",
            ),
            completed_field(
                audit_record_id=2,
                field_name="title",
                category="LIGHT_EDIT",
            ),
            completed_field(
                audit_record_id=3,
                field_name="title",
                category="LIGHT_EDIT",
            ),
        ]
    )

    summary = build_field_edit_readability_cross_summary(
        pairs,
        fields,
    )
    decreased = summary.loc[
        summary["readability_direction_category"].eq("CONSENSUS_GRADE_LEVEL_DECREASE")
    ].iloc[0]

    assert decreased["completed_ai_attempt_count"] == 3
    assert decreased["completed_ai_attempt_count_with_selected_final_pair"] == 1
    assert decreased["percentage_within_edit_intensity_category"] == (
        pytest.approx(100.0 / 3.0)
    )
    assert decreased["median_flesch_kincaid_grade_change_final_minus_selected"] == -1.0
    assert decreased["median_consensus_grade_level_change"] == -1.0


def test_paired_readability_summaries_return_canonical_empty_frames() -> None:
    empty_pairs = pd.DataFrame(
        columns=[
            "audit_record_id",
            "field_name",
            "readability_measure_name",
            "change_final_minus_selected",
            "readability_direction_category",
            "consensus_grade_level_direction_category",
            "unchanged_absolute_tolerance",
            "edit_intensity_category",
            "edit_intensity_threshold_scheme_name",
            "short_text_readability_caution",
        ]
    )
    empty_fields = pd.DataFrame(
        columns=[
            "audit_record_id",
            "field_name",
            "edit_intensity_category",
            "edit_intensity_threshold_scheme_name",
        ]
    )

    changes = build_field_readability_change_summary(empty_pairs)
    cross = build_field_edit_readability_cross_summary(
        empty_pairs,
        empty_fields,
    )

    assert changes.empty
    assert "paired_selected_final_attempt_count" in changes.columns
    assert cross.empty
    assert "readability_direction_category" in cross.columns
