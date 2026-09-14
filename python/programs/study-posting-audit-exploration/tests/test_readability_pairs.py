import pandas as pd
import pytest

from study_posting_audit_exploration import ExplorationValidationError
from study_posting_audit_exploration.derivation import (
    derive_completed_ai_readability_pairs,
)
from study_posting_audit_exploration.input_contracts import (
    READABILITY_COLUMNS,
)


def readability_row(
    *,
    role: str,
    selected: str | None,
    values: tuple[float, float, float, float],
) -> dict[str, object]:
    """Return one synthetic selected or final readability row."""
    row: dict[str, object] = dict.fromkeys(READABILITY_COLUMNS, None)
    row.update(
        {
            "record_id": 1,
            "attempt_type": "AI",
            "field_name": "title",
            "text_role": role,
            "suggestion_kind": "title" if role == "SUGGESTED" else None,
            "suggestion_index": 0 if role == "SUGGESTED" else None,
            "selected": selected,
            "flesch_kincaid_grade": values[0],
            "automated_readability_index": values[1],
            "coleman_liau_index": values[2],
            "gunning_fog": values[3],
            "dale_chall_readability_score": 6.0,
            "estimated_reading_time_seconds": 1.0,
            "sentence_count": 1,
            "word_count": 5,
            "syllable_count": 7,
            "letter_count": 25,
            "polysyllable_count": 1,
        }
    )

    return row


def field_context() -> pd.DataFrame:
    """Return one synthetic completed-AI field-analysis row."""
    return pd.DataFrame.from_records(
        [
            {
                "audit_record_id": 1,
                "study_num": "SYNTHETIC-STUDY",
                "field_name": "title",
                "edit_intensity_category": "LIGHT_EDIT",
                "edit_intensity_threshold_scheme_name": (
                    "EXPLORATORY_CHARACTER_RATIO_10_30"
                ),
            }
        ]
    )


def test_readability_pairs_emit_every_measure_without_text() -> None:
    readability = pd.DataFrame.from_records(
        [
            readability_row(
                role="SUGGESTED",
                selected="true",
                values=(8.0, 8.0, 8.0, 8.0),
            ),
            readability_row(
                role="FINAL",
                selected=None,
                values=(7.0, 7.0, 7.0, 7.0),
            ),
        ],
        columns=list(READABILITY_COLUMNS),
    )

    pairs = derive_completed_ai_readability_pairs(
        readability,
        field_context(),
    )

    assert len(pairs) == 11
    assert set(pairs["readability_measure_name"]) == {
        "flesch_kincaid_grade",
        "automated_readability_index",
        "coleman_liau_index",
        "gunning_fog",
        "dale_chall_readability_score",
        "estimated_reading_time_seconds",
        "sentence_count",
        "word_count",
        "syllable_count",
        "letter_count",
        "polysyllable_count",
    }
    assert set(pairs["readability_direction_category"]) == {
        "NO_MATERIAL_CHANGE",
        "VALUE_DECREASED",
    }
    assert set(pairs["consensus_grade_level_direction_category"]) == {
        "CONSENSUS_GRADE_LEVEL_DECREASE"
    }
    assert pairs["short_text_readability_caution"].all()
    assert "selected_text" not in pairs.columns
    assert "final_text" not in pairs.columns


def test_readability_pairs_use_absolute_tolerance() -> None:
    readability = pd.DataFrame.from_records(
        [
            readability_row(
                role="SUGGESTED",
                selected="true",
                values=(8.0, 8.0, 8.0, 8.0),
            ),
            readability_row(
                role="FINAL",
                selected=None,
                values=(8.1, 7.9, 8.1001, 7.8999),
            ),
        ],
        columns=list(READABILITY_COLUMNS),
    )

    pairs = derive_completed_ai_readability_pairs(
        readability,
        field_context(),
        unchanged_absolute_tolerance=0.1,
    )
    directions = pairs.set_index("readability_measure_name")[
        "readability_direction_category"
    ]

    assert directions["flesch_kincaid_grade"] == "NO_MATERIAL_CHANGE"
    assert directions["automated_readability_index"] == "NO_MATERIAL_CHANGE"
    assert directions["coleman_liau_index"] == "VALUE_INCREASED"
    assert directions["gunning_fog"] == "VALUE_DECREASED"
    assert set(pairs["consensus_grade_level_direction_category"]) == {
        "MIXED_FORMULA_DIRECTION"
    }


def test_readability_pairs_report_consensus_increase() -> None:
    readability = pd.DataFrame.from_records(
        [
            readability_row(
                role="SUGGESTED",
                selected="true",
                values=(6.0, 6.0, 6.0, 6.0),
            ),
            readability_row(
                role="FINAL",
                selected=None,
                values=(7.0, 7.0, 7.0, 6.0),
            ),
        ],
        columns=list(READABILITY_COLUMNS),
    )

    pairs = derive_completed_ai_readability_pairs(
        readability,
        field_context(),
    )

    assert set(pairs["consensus_grade_level_direction_category"]) == {
        "CONSENSUS_GRADE_LEVEL_INCREASE"
    }


@pytest.mark.parametrize(
    "tolerance",
    [
        -0.1,
        float("inf"),
        float("nan"),
    ],
)
def test_readability_pairs_reject_invalid_tolerance(
    tolerance: float,
) -> None:
    readability = pd.DataFrame(columns=list(READABILITY_COLUMNS))

    with pytest.raises(
        ExplorationValidationError,
        match="tolerance must be finite and nonnegative",
    ):
        derive_completed_ai_readability_pairs(
            readability,
            field_context(),
            unchanged_absolute_tolerance=tolerance,
        )


def test_readability_pairs_return_canonical_empty_frame() -> None:
    readability = pd.DataFrame(columns=list(READABILITY_COLUMNS))

    pairs = derive_completed_ai_readability_pairs(
        readability,
        field_context(),
    )

    assert pairs.empty
    assert "readability_measure_name" in pairs.columns
    assert "change_final_minus_selected" in pairs.columns
