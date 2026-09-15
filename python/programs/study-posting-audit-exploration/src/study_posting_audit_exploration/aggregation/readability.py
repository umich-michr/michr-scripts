"""Faculty-facing readability summaries."""

import math
from numbers import Real
from typing import cast

import pandas as pd

from study_posting_audit_exploration.errors import ExplorationValidationError
from study_posting_audit_exploration.input_contracts import (
    READABILITY_FLOAT_COLUMNS,
    READABILITY_INTEGER_COLUMNS,
)
from study_posting_audit_exploration.statistics import describe_numeric

_DEFAULT_EQUALITY_TOLERANCE = 0.1
_FLESCH_KINCAID_GRADE = "flesch_kincaid_grade"

_READABILITY_MEASURES: tuple[str, ...] = (
    *READABILITY_FLOAT_COLUMNS,
    *(
        column_name
        for column_name in READABILITY_INTEGER_COLUMNS
        if column_name not in {"record_id", "suggestion_index"}
    ),
)

SELECTED_VS_UNSELECTED_READABILITY_COLUMNS: tuple[str, ...] = (
    "field_name",
    "readability_measure_name",
    "completed_ai_attempt_count_with_selected_and_unselected_suggestions",
    "minimum_selected_minus_mean_unselected_value",
    "percentile_25_selected_minus_mean_unselected_value",
    "median_selected_minus_mean_unselected_value",
    "average_selected_minus_mean_unselected_value",
    "standard_deviation_selected_minus_mean_unselected_value",
    "percentile_75_selected_minus_mean_unselected_value",
    "maximum_selected_minus_mean_unselected_value",
    "attempt_count_selected_value_lower",
    "attempt_count_selected_value_equal_within_tolerance",
    "attempt_count_selected_value_higher",
    "equality_tolerance",
)

FIELD_READABILITY_CHANGE_COLUMNS: tuple[str, ...] = (
    "field_name",
    "readability_measure_name",
    "paired_selected_final_attempt_count",
    "minimum_change_final_minus_selected",
    "percentile_25_change_final_minus_selected",
    "median_change_final_minus_selected",
    "average_change_final_minus_selected",
    "standard_deviation_change_final_minus_selected",
    "percentile_75_change_final_minus_selected",
    "maximum_change_final_minus_selected",
    "attempt_count_value_decreased",
    "attempt_count_no_material_change",
    "attempt_count_value_increased",
    "percentage_value_decreased",
    "percentage_no_material_change",
    "percentage_value_increased",
    "unchanged_absolute_tolerance",
    "short_text_readability_caution",
)

FIELD_EDIT_READABILITY_CROSS_COLUMNS: tuple[str, ...] = (
    "field_name",
    "edit_intensity_threshold_scheme_name",
    "edit_intensity_category",
    "readability_direction_category",
    "completed_ai_attempt_count",
    "completed_ai_attempt_count_with_selected_final_pair",
    "percentage_within_edit_intensity_category",
    "median_flesch_kincaid_grade_change_final_minus_selected",
    "median_consensus_grade_level_change",
)

_CONSENSUS_NUMERIC_VALUES: dict[str, float] = {
    "CONSENSUS_GRADE_LEVEL_DECREASE": -1.0,
    "NO_MATERIAL_CHANGE": 0.0,
    "CONSENSUS_GRADE_LEVEL_INCREASE": 1.0,
    "MIXED_FORMULA_DIRECTION": 0.0,
}


def _percentage(
    numerator: int,
    denominator: int,
) -> float | None:
    """Return a percentage or ``None`` for an empty denominator."""
    if denominator == 0:
        return None

    return 100.0 * numerator / denominator


def _finite_number(
    value: object,
    *,
    value_name: str,
) -> float:
    """Return one finite numeric value."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ExplorationValidationError(
            f"readability value {value_name!r} must be numeric"
        )

    converted = float(value)

    if not math.isfinite(converted):
        raise ExplorationValidationError(
            f"readability value {value_name!r} must be finite"
        )

    return converted


def _selected_marker(readability: pd.DataFrame) -> pd.Series:
    """Return lowercase nullable selected-marker values."""
    return readability["selected"].astype("string").str.lower()


def _attempt_measure_differences(
    readability: pd.DataFrame,
) -> pd.DataFrame:
    """Return selected minus mean-unselected values per attempt and field."""
    suggestions = readability.loc[readability["text_role"].eq("SUGGESTED")].copy()
    suggestions["selected_normalized"] = _selected_marker(suggestions)
    rows: list[dict[str, object]] = []

    for keys, group in suggestions.groupby(
        [
            "record_id",
            "field_name",
        ],
        sort=True,
        dropna=False,
    ):
        selected = group.loc[group["selected_normalized"].eq("true")]
        unselected = group.loc[group["selected_normalized"].eq("false")]

        if len(selected) != 1 or unselected.empty:
            continue

        record_id, field_name = keys
        selected_row = cast(
            "dict[str, object]",
            selected.iloc[0].to_dict(),
        )

        for measure_name in _READABILITY_MEASURES:
            selected_value = _finite_number(
                selected_row[measure_name],
                value_name=measure_name,
            )
            unselected_values = [
                _finite_number(
                    value,
                    value_name=measure_name,
                )
                for value in unselected[measure_name]
            ]
            mean_unselected = sum(unselected_values) / len(unselected_values)
            rows.append(
                {
                    "record_id": record_id,
                    "field_name": field_name,
                    "readability_measure_name": measure_name,
                    "selected_minus_mean_unselected_value": (
                        selected_value - mean_unselected
                    ),
                }
            )

    return pd.DataFrame.from_records(
        rows,
        columns=[
            "record_id",
            "field_name",
            "readability_measure_name",
            "selected_minus_mean_unselected_value",
        ],
    )


def _selected_comparison_summary_row(
    group: pd.DataFrame,
    *,
    equality_tolerance: float,
) -> dict[str, object]:
    """Return one field and measure selected-comparison summary."""
    values = group["selected_minus_mean_unselected_value"]
    statistics = describe_numeric(
        values,
        metric_name="selected_minus_mean_unselected_value",
    )
    lower_count = int(values.lt(-equality_tolerance).sum())
    equal_count = int(values.abs().le(equality_tolerance).sum())
    higher_count = int(values.gt(equality_tolerance).sum())

    return {
        "field_name": str(group["field_name"].iloc[0]),
        "readability_measure_name": str(group["readability_measure_name"].iloc[0]),
        "completed_ai_attempt_count_with_selected_and_unselected_suggestions": (
            int(group["record_id"].nunique(dropna=True))
        ),
        "minimum_selected_minus_mean_unselected_value": statistics.minimum,
        "percentile_25_selected_minus_mean_unselected_value": (
            statistics.percentile_25
        ),
        "median_selected_minus_mean_unselected_value": statistics.median,
        "average_selected_minus_mean_unselected_value": statistics.average,
        "standard_deviation_selected_minus_mean_unselected_value": (
            statistics.standard_deviation
        ),
        "percentile_75_selected_minus_mean_unselected_value": (
            statistics.percentile_75
        ),
        "maximum_selected_minus_mean_unselected_value": statistics.maximum,
        "attempt_count_selected_value_lower": lower_count,
        "attempt_count_selected_value_equal_within_tolerance": equal_count,
        "attempt_count_selected_value_higher": higher_count,
        "equality_tolerance": equality_tolerance,
    }


def build_selected_vs_unselected_readability_summary(
    readability: pd.DataFrame,
    *,
    equality_tolerance: float = _DEFAULT_EQUALITY_TOLERANCE,
) -> pd.DataFrame:
    """Compare selected suggestions with mean unselected suggestions."""
    if not math.isfinite(equality_tolerance) or equality_tolerance < 0:
        raise ExplorationValidationError(
            "readability equality tolerance must be finite and nonnegative"
        )

    differences = _attempt_measure_differences(readability)
    rows = [
        _selected_comparison_summary_row(
            group,
            equality_tolerance=equality_tolerance,
        )
        for _, group in differences.groupby(
            [
                "field_name",
                "readability_measure_name",
            ],
            sort=True,
            dropna=False,
        )
    ]

    return pd.DataFrame.from_records(
        rows,
        columns=list(SELECTED_VS_UNSELECTED_READABILITY_COLUMNS),
    )


def _change_summary_row(
    group: pd.DataFrame,
) -> dict[str, object]:
    """Return one selected-to-final change summary."""
    values = group["change_final_minus_selected"]
    statistics = describe_numeric(
        values,
        metric_name="change_final_minus_selected",
    )
    direction = group["readability_direction_category"]
    pair_count = int(group["audit_record_id"].nunique(dropna=True))
    decreased_count = int(direction.eq("VALUE_DECREASED").sum())
    unchanged_count = int(direction.eq("NO_MATERIAL_CHANGE").sum())
    increased_count = int(direction.eq("VALUE_INCREASED").sum())
    tolerances = group["unchanged_absolute_tolerance"].dropna().unique()
    tolerance = float(tolerances[0]) if len(tolerances) == 1 else None

    return {
        "field_name": str(group["field_name"].iloc[0]),
        "readability_measure_name": str(group["readability_measure_name"].iloc[0]),
        "paired_selected_final_attempt_count": pair_count,
        "minimum_change_final_minus_selected": statistics.minimum,
        "percentile_25_change_final_minus_selected": statistics.percentile_25,
        "median_change_final_minus_selected": statistics.median,
        "average_change_final_minus_selected": statistics.average,
        "standard_deviation_change_final_minus_selected": (
            statistics.standard_deviation
        ),
        "percentile_75_change_final_minus_selected": statistics.percentile_75,
        "maximum_change_final_minus_selected": statistics.maximum,
        "attempt_count_value_decreased": decreased_count,
        "attempt_count_no_material_change": unchanged_count,
        "attempt_count_value_increased": increased_count,
        "percentage_value_decreased": _percentage(
            decreased_count,
            pair_count,
        ),
        "percentage_no_material_change": _percentage(
            unchanged_count,
            pair_count,
        ),
        "percentage_value_increased": _percentage(
            increased_count,
            pair_count,
        ),
        "unchanged_absolute_tolerance": tolerance,
        "short_text_readability_caution": bool(
            group["short_text_readability_caution"].iloc[0]
        ),
    }


def build_field_readability_change_summary(
    readability_pairs: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize selected-suggestion-to-final readability changes."""
    rows = [
        _change_summary_row(group)
        for _, group in readability_pairs.groupby(
            [
                "field_name",
                "readability_measure_name",
            ],
            sort=True,
            dropna=False,
        )
    ]

    return pd.DataFrame.from_records(
        rows,
        columns=list(FIELD_READABILITY_CHANGE_COLUMNS),
    )


def _cross_summary_row(
    group: pd.DataFrame,
    *,
    population_count: int,
) -> dict[str, object]:
    """Return one edit-intensity and readability-direction cross row."""
    changes = describe_numeric(
        group["change_final_minus_selected"],
        metric_name="flesch_kincaid_grade_change_final_minus_selected",
    )
    consensus_values = group["consensus_grade_level_direction_category"].map(
        _CONSENSUS_NUMERIC_VALUES
    )
    consensus_statistics = describe_numeric(
        consensus_values,
        metric_name="consensus_grade_level_change",
    )
    pair_count = int(group["audit_record_id"].nunique(dropna=True))

    return {
        "field_name": str(group["field_name"].iloc[0]),
        "edit_intensity_threshold_scheme_name": str(
            group["edit_intensity_threshold_scheme_name"].iloc[0]
        ),
        "edit_intensity_category": str(group["edit_intensity_category"].iloc[0]),
        "readability_direction_category": str(
            group["consensus_grade_level_direction_category"].iloc[0]
        ),
        "completed_ai_attempt_count": population_count,
        "completed_ai_attempt_count_with_selected_final_pair": pair_count,
        "percentage_within_edit_intensity_category": _percentage(
            pair_count,
            population_count,
        ),
        "median_flesch_kincaid_grade_change_final_minus_selected": (changes.median),
        "median_consensus_grade_level_change": consensus_statistics.median,
    }


def build_field_edit_readability_cross_summary(
    readability_pairs: pd.DataFrame,
    completed_ai_fields: pd.DataFrame,
) -> pd.DataFrame:
    """Cross edit intensity with consensus grade-level direction."""
    grade_pairs = readability_pairs.loc[
        readability_pairs["readability_measure_name"].eq(_FLESCH_KINCAID_GRADE)
    ]
    population_counts = (
        completed_ai_fields.groupby(
            [
                "field_name",
                "edit_intensity_threshold_scheme_name",
                "edit_intensity_category",
            ],
            sort=True,
            dropna=False,
        )["audit_record_id"]
        .nunique(dropna=True)
        .to_dict()
    )
    rows: list[dict[str, object]] = []

    for keys, group in grade_pairs.groupby(
        [
            "field_name",
            "edit_intensity_threshold_scheme_name",
            "edit_intensity_category",
            "consensus_grade_level_direction_category",
        ],
        sort=True,
        dropna=False,
    ):
        field_name, scheme_name, category, _ = keys
        population_key = (
            field_name,
            scheme_name,
            category,
        )
        population_count = int(population_counts.get(population_key, 0))
        rows.append(
            _cross_summary_row(
                group,
                population_count=population_count,
            )
        )

    return pd.DataFrame.from_records(
        rows,
        columns=list(FIELD_EDIT_READABILITY_CROSS_COLUMNS),
    )
