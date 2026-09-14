import pandas as pd

from study_posting_audit_exploration import (
    build_field_readability_target_summary,
    build_final_text_metric_summary,
)
from study_posting_audit_exploration.input_contracts import (
    READABILITY_COLUMNS,
)


def final_row(
    *,
    record_id: int,
    mode: str,
    field_name: str,
    grade: float,
) -> dict[str, object]:
    """Return one synthetic final readability row."""
    row: dict[str, object] = dict.fromkeys(READABILITY_COLUMNS, None)
    row.update(
        {
            "record_id": record_id,
            "attempt_type": mode,
            "field_name": field_name,
            "text_role": "FINAL",
            "flesch_kincaid_grade": grade,
            "automated_readability_index": grade,
            "coleman_liau_index": grade,
            "gunning_fog": grade,
            "dale_chall_readability_score": 6.0,
            "estimated_reading_time_seconds": 2.0,
            "sentence_count": 2,
            "word_count": 20,
            "syllable_count": 30,
            "letter_count": 100,
            "polysyllable_count": 3,
        }
    )

    return row


def test_field_readability_target_summary_reports_bands_by_mode() -> None:
    readability = pd.DataFrame.from_records(
        [
            final_row(
                record_id=1,
                mode="AI",
                field_name="title",
                grade=6.0,
            ),
            final_row(
                record_id=2,
                mode="AI",
                field_name="title",
                grade=7.0,
            ),
            final_row(
                record_id=3,
                mode="AI",
                field_name="title",
                grade=9.0,
            ),
            final_row(
                record_id=4,
                mode="AI",
                field_name="title",
                grade=11.0,
            ),
            final_row(
                record_id=5,
                mode="MANUAL",
                field_name="title",
                grade=8.0,
            ),
        ],
        columns=list(READABILITY_COLUMNS),
    )

    summary = build_field_readability_target_summary(readability)
    ai_grade = summary.loc[
        summary["attempt_authoring_mode"].eq("AI")
        & summary["field_name"].eq("title")
        & summary["readability_measure_name"].eq("flesch_kincaid_grade")
    ].iloc[0]

    assert ai_grade["final_text_attempt_count"] == 4
    assert ai_grade["attempt_count_at_or_below_grade_6"] == 1
    assert ai_grade["attempt_count_above_grade_6_through_grade_8"] == 1
    assert ai_grade["attempt_count_above_grade_8_through_grade_10"] == 1
    assert ai_grade["attempt_count_above_grade_10"] == 1
    assert ai_grade["percentage_at_or_below_grade_8"] == 50.0
    assert bool(ai_grade["short_text_readability_caution"]) is True
    assert "do not establish comprehension" in (ai_grade["target_interpretation_note"])

    assert set(summary["attempt_authoring_mode"]) == {
        "AI",
        "MANUAL",
    }


def test_final_text_metric_summary_reports_observed_values() -> None:
    readability = pd.DataFrame.from_records(
        [
            final_row(
                record_id=1,
                mode="AI",
                field_name="description",
                grade=7.0,
            ),
            final_row(
                record_id=2,
                mode="AI",
                field_name="description",
                grade=9.0,
            ),
        ],
        columns=list(READABILITY_COLUMNS),
    )
    fields = pd.DataFrame(
        columns=[
            "audit_record_id",
            "field_name",
            "picked_kind",
        ]
    )

    summary = build_final_text_metric_summary(
        readability,
        fields,
    )
    grade = summary.loc[
        summary["attempt_authoring_mode"].eq("AI")
        & summary["field_name"].eq("description")
        & summary["metric_name"].eq("flesch_kincaid_grade")
    ].iloc[0]

    assert grade["metric_unit"] == "score"
    assert grade["final_text_attempt_count_with_metric"] == 2
    assert pd.isna(grade["final_text_attempt_count_missing_or_blank"])
    assert grade["minimum_final_metric_value"] == 7.0
    assert grade["median_final_metric_value"] == 8.0
    assert grade["average_final_metric_value"] == 8.0
    assert grade["maximum_final_metric_value"] == 9.0


def test_final_text_metric_summary_preserves_compensation_kind() -> None:
    readability = pd.DataFrame.from_records(
        [
            final_row(
                record_id=1,
                mode="AI",
                field_name="compensation",
                grade=7.0,
            )
        ],
        columns=list(READABILITY_COLUMNS),
    )
    fields = pd.DataFrame.from_records(
        [
            {
                "audit_record_id": 1,
                "field_name": "compensation",
                "picked_kind": "specificCompensation",
            }
        ]
    )

    summary = build_final_text_metric_summary(
        readability,
        fields,
    )

    assert set(summary["compensation_selected_suggestion_kind"]) == {
        "specificCompensation"
    }


def test_final_readability_summaries_return_canonical_empty_frames() -> None:
    readability = pd.DataFrame(columns=list(READABILITY_COLUMNS))
    fields = pd.DataFrame(
        columns=[
            "audit_record_id",
            "field_name",
            "picked_kind",
        ]
    )

    target = build_field_readability_target_summary(readability)
    metrics = build_final_text_metric_summary(
        readability,
        fields,
    )

    assert target.empty
    assert "target_interpretation_note" in target.columns
    assert metrics.empty
    assert "final_text_attempt_count_missing_or_blank" in metrics.columns
