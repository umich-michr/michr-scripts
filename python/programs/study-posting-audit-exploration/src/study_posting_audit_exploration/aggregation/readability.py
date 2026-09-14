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

_READABILITY_MEASURES: tuple[str, ...] = (
    *READABILITY_FLOAT_COLUMNS,
    *(
        column_name
        for column_name in READABILITY_INTEGER_COLUMNS
        if column_name not in {"record_id", "suggestion_index"}
    ),
)

_SELECTED_VS_UNSELECTED_COLUMNS: tuple[str, ...] = (
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


def _summary_row(
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
        _summary_row(
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
        columns=list(_SELECTED_VS_UNSELECTED_COLUMNS),
    )
