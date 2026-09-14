import pandas as pd
import pytest

from study_posting_audit_exploration import (
    ExplorationValidationError,
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
