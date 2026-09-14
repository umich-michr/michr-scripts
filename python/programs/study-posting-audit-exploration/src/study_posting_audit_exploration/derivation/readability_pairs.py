"""Selected-suggestion and final readability-pair derivation."""

import math
from numbers import Real
from typing import cast

import pandas as pd

from study_posting_audit_exploration.errors import ExplorationValidationError
from study_posting_audit_exploration.input_contracts import (
    READABILITY_FLOAT_COLUMNS,
    READABILITY_INTEGER_COLUMNS,
)

_GRADE_MEASURES: tuple[str, ...] = (
    "flesch_kincaid_grade",
    "automated_readability_index",
    "coleman_liau_index",
    "gunning_fog",
)
_ALL_MEASURES: tuple[str, ...] = (
    *READABILITY_FLOAT_COLUMNS,
    *(
        column_name
        for column_name in READABILITY_INTEGER_COLUMNS
        if column_name not in {"record_id", "suggestion_index"}
    ),
)
_DEFAULT_UNCHANGED_TOLERANCE = 0.1

_CONSENSUS_FORMULA_COUNT = 3

_READABILITY_PAIR_COLUMNS: tuple[str, ...] = (
    "audit_record_id",
    "study_num",
    "field_name",
    "suggestion_kind",
    "suggestion_index",
    "readability_measure_name",
    "selected_suggestion_metric_value",
    "final_metric_value",
    "change_final_minus_selected",
    "readability_direction_category",
    "consensus_grade_level_direction_category",
    "unchanged_absolute_tolerance",
    "edit_intensity_category",
    "edit_intensity_threshold_scheme_name",
    "short_text_readability_caution",
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


def _direction(
    change: float,
    *,
    tolerance: float,
) -> str:
    """Return the neutral direction category for one metric change."""
    if abs(change) <= tolerance:
        return "NO_MATERIAL_CHANGE"

    if change < 0:
        return "VALUE_DECREASED"

    return "VALUE_INCREASED"


def _consensus_direction(
    directions: dict[str, str],
) -> str:
    """Return consensus direction across four grade-level formulas."""
    grade_directions = [directions[measure] for measure in _GRADE_MEASURES]
    decreased = grade_directions.count("VALUE_DECREASED")
    unchanged = grade_directions.count("NO_MATERIAL_CHANGE")
    increased = grade_directions.count("VALUE_INCREASED")

    if unchanged == len(_GRADE_MEASURES):
        return "NO_MATERIAL_CHANGE"

    if decreased >= _CONSENSUS_FORMULA_COUNT and increased == 0:
        return "CONSENSUS_GRADE_LEVEL_DECREASE"

    if increased >= _CONSENSUS_FORMULA_COUNT and decreased == 0:
        return "CONSENSUS_GRADE_LEVEL_INCREASE"

    return "MIXED_FORMULA_DIRECTION"


def _selected_and_final(
    readability: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return selected suggestion and final readability rows."""
    selected_marker = readability["selected"].astype("string").str.lower()
    selected = readability.loc[
        readability["text_role"].eq("SUGGESTED") & selected_marker.eq("true")
    ]
    final = readability.loc[readability["text_role"].eq("FINAL")]

    return selected, final


def _pair_rows(
    pair: dict[str, object],
    *,
    tolerance: float,
) -> list[dict[str, object]]:
    """Return long-format measure rows for one selected/final field pair."""
    directions: dict[str, str] = {}
    measure_values: list[tuple[str, float, float, float]] = []

    for measure_name in _ALL_MEASURES:
        selected_value = _finite_number(
            pair[f"{measure_name}_selected"],
            value_name=f"{measure_name}_selected",
        )
        final_value = _finite_number(
            pair[f"{measure_name}_final"],
            value_name=f"{measure_name}_final",
        )
        change = final_value - selected_value
        directions[measure_name] = _direction(
            change,
            tolerance=tolerance,
        )
        measure_values.append(
            (
                measure_name,
                selected_value,
                final_value,
                change,
            )
        )

    consensus = _consensus_direction(directions)

    return [
        {
            "audit_record_id": pair["record_id"],
            "study_num": pair["study_num"],
            "field_name": pair["field_name"],
            "suggestion_kind": pair["suggestion_kind"],
            "suggestion_index": pair["suggestion_index"],
            "readability_measure_name": measure_name,
            "selected_suggestion_metric_value": selected_value,
            "final_metric_value": final_value,
            "change_final_minus_selected": change,
            "readability_direction_category": directions[measure_name],
            "consensus_grade_level_direction_category": consensus,
            "unchanged_absolute_tolerance": tolerance,
            "edit_intensity_category": pair["edit_intensity_category"],
            "edit_intensity_threshold_scheme_name": (
                pair["edit_intensity_threshold_scheme_name"]
            ),
            "short_text_readability_caution": (str(pair["field_name"]) == "title"),
        }
        for measure_name, selected_value, final_value, change in measure_values
    ]


def derive_completed_ai_readability_pairs(
    readability: pd.DataFrame,
    completed_ai_fields: pd.DataFrame,
    *,
    unchanged_absolute_tolerance: float = _DEFAULT_UNCHANGED_TOLERANCE,
) -> pd.DataFrame:
    """Return long-format selected-suggestion/final readability pairs."""
    if (
        not math.isfinite(unchanged_absolute_tolerance)
        or unchanged_absolute_tolerance < 0
    ):
        raise ExplorationValidationError(
            "readability unchanged tolerance must be finite and nonnegative"
        )

    selected, final = _selected_and_final(readability)
    identity_columns = [
        "record_id",
        "field_name",
    ]
    metric_columns = list(_ALL_MEASURES)
    paired = selected[
        [
            *identity_columns,
            "suggestion_kind",
            "suggestion_index",
            *metric_columns,
        ]
    ].merge(
        final[
            [
                *identity_columns,
                *metric_columns,
            ]
        ],
        on=identity_columns,
        how="inner",
        validate="one_to_one",
        suffixes=(
            "_selected",
            "_final",
        ),
    )
    field_context = completed_ai_fields[
        [
            "audit_record_id",
            "study_num",
            "field_name",
            "edit_intensity_category",
            "edit_intensity_threshold_scheme_name",
        ]
    ].rename(columns={"audit_record_id": "record_id"})
    paired = paired.merge(
        field_context,
        on=identity_columns,
        how="inner",
        validate="one_to_one",
    )
    pair_records = cast(
        "list[dict[str, object]]",
        paired.to_dict(orient="records"),
    )
    rows = [
        row
        for pair in pair_records
        for row in _pair_rows(
            pair,
            tolerance=unchanged_absolute_tolerance,
        )
    ]

    return pd.DataFrame.from_records(
        rows,
        columns=list(_READABILITY_PAIR_COLUMNS),
    )
