"""Lookup and compensation-flag adoption summaries."""

import json
import math
from numbers import Integral, Real
from typing import cast

import pandas as pd

from study_posting_audit_exploration.errors import ExplorationValidationError
from study_posting_audit_exploration.statistics import describe_numeric

NONTEXT_FIELD_ADOPTION_COLUMNS: tuple[str, ...] = (
    "field_name",
    "analysis_type",
    "completed_ai_attempt_count",
    "attempt_count_with_ai_value_selected",
    "attempt_count_final_equal_to_selected",
    "attempt_count_final_different_from_selected",
    "attempt_count_final_missing",
    "selection_percentage",
    "final_equal_to_selected_percentage_among_selected",
    "final_different_from_selected_percentage_among_selected",
    "attempt_count_exact_set_match",
    "attempt_count_partial_set_overlap",
    "attempt_count_no_set_overlap",
    "median_selected_final_lookup_similarity",
    "average_selected_final_lookup_similarity",
)


def _percentage(
    numerator: int,
    denominator: int,
) -> float | None:
    """Return a percentage or ``None`` for an empty denominator."""
    if denominator == 0:
        return None

    return 100.0 * numerator / denominator


def _is_missing_scalar(value: object) -> bool:
    """Return whether one scalar represents a missing value."""
    if value is None or value is pd.NA or value is pd.NaT:
        return True

    return isinstance(value, Real) and math.isnan(float(value))


def _boolean_value(value: object) -> bool | None:
    """Return one nullable serialized Boolean."""
    if _is_missing_scalar(value):
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        normalized = value.lower()

        if normalized == "true":
            return True

        if normalized == "false":
            return False

    raise ExplorationValidationError(
        "compensation Boolean field contains an invalid serialized value"
    )


def _integer_set(
    value: object,
    *,
    column_name: str,
) -> frozenset[int]:
    """Parse one serialized lookup identifier set."""
    if _is_missing_scalar(value):
        return frozenset()

    if not isinstance(value, str):
        raise ExplorationValidationError(
            f"lookup column {column_name!r} must contain a JSON array"
        )

    try:
        decoded = json.loads(value)
    except json.JSONDecodeError as error:
        raise ExplorationValidationError(
            f"lookup column {column_name!r} contains invalid JSON"
        ) from error

    if not isinstance(decoded, list):
        raise ExplorationValidationError(
            f"lookup column {column_name!r} must contain a JSON array"
        )

    identifiers: set[int] = set()

    for item in cast("list[object]", decoded):
        if isinstance(item, bool) or not isinstance(item, Integral):
            raise ExplorationValidationError(
                f"lookup column {column_name!r} contains a non-integer identifier"
            )

        identifiers.add(int(item))

    return frozenset(identifiers)


def _lookup_summary_row(
    fields: pd.DataFrame,
) -> dict[str, object]:
    """Return one lookup-field adoption summary."""
    completed_count = int(fields["audit_record_id"].nunique(dropna=True))
    picked_sets = [
        _integer_set(value, column_name="picked_ids") for value in fields["picked_ids"]
    ]
    saved_sets = [
        _integer_set(value, column_name="saved_ids") for value in fields["saved_ids"]
    ]
    selected_mask = pd.Series(
        [bool(values) for values in picked_sets],
        index=fields.index,
        dtype="boolean",
    )
    final_missing_mask = pd.Series(
        [not values for values in saved_sets],
        index=fields.index,
        dtype="boolean",
    )
    selected_count = int(
        fields.loc[selected_mask, "audit_record_id"].nunique(dropna=True)
    )
    comparable = [
        (picked, saved)
        for picked, saved in zip(
            picked_sets,
            saved_sets,
            strict=True,
        )
        if picked
    ]
    exact_count = sum(picked == saved for picked, saved in comparable)
    different_count = len(comparable) - exact_count
    partial_overlap_count = sum(
        picked != saved and bool(picked & saved) for picked, saved in comparable
    )
    no_overlap_count = sum(
        picked != saved and not bool(picked & saved) for picked, saved in comparable
    )
    missing_count = int(
        fields.loc[final_missing_mask, "audit_record_id"].nunique(dropna=True)
    )
    similarity_statistics = describe_numeric(
        fields.loc[selected_mask, "lookup_similarity"],
        metric_name="lookup_similarity",
    )

    return {
        "field_name": str(fields["field_name"].iloc[0]),
        "analysis_type": "LOOKUP",
        "completed_ai_attempt_count": completed_count,
        "attempt_count_with_ai_value_selected": selected_count,
        "attempt_count_final_equal_to_selected": exact_count,
        "attempt_count_final_different_from_selected": different_count,
        "attempt_count_final_missing": missing_count,
        "selection_percentage": _percentage(
            selected_count,
            completed_count,
        ),
        "final_equal_to_selected_percentage_among_selected": _percentage(
            exact_count,
            selected_count,
        ),
        "final_different_from_selected_percentage_among_selected": _percentage(
            different_count,
            selected_count,
        ),
        "attempt_count_exact_set_match": exact_count,
        "attempt_count_partial_set_overlap": partial_overlap_count,
        "attempt_count_no_set_overlap": no_overlap_count,
        "median_selected_final_lookup_similarity": similarity_statistics.median,
        "average_selected_final_lookup_similarity": similarity_statistics.average,
    }


def _compensation_flag_summary_row(
    fields: pd.DataFrame,
) -> dict[str, object]:
    """Return compensation Boolean recommendation outcomes."""
    completed_count = int(fields["audit_record_id"].nunique(dropna=True))
    suggested = fields["flag_suggested"].map(_boolean_value)
    saved = fields["flag_saved"].map(_boolean_value)
    selected = suggested.notna()
    comparable = selected & saved.notna()
    equal = comparable & suggested.eq(saved)
    different = comparable & suggested.ne(saved)
    final_missing = saved.isna()

    selected_count = int(fields.loc[selected, "audit_record_id"].nunique(dropna=True))
    equal_count = int(fields.loc[equal, "audit_record_id"].nunique(dropna=True))
    different_count = int(fields.loc[different, "audit_record_id"].nunique(dropna=True))
    missing_count = int(
        fields.loc[final_missing, "audit_record_id"].nunique(dropna=True)
    )

    return {
        "field_name": "offersCompensation",
        "analysis_type": "BOOLEAN",
        "completed_ai_attempt_count": completed_count,
        "attempt_count_with_ai_value_selected": selected_count,
        "attempt_count_final_equal_to_selected": equal_count,
        "attempt_count_final_different_from_selected": different_count,
        "attempt_count_final_missing": missing_count,
        "selection_percentage": _percentage(
            selected_count,
            completed_count,
        ),
        "final_equal_to_selected_percentage_among_selected": _percentage(
            equal_count,
            selected_count,
        ),
        "final_different_from_selected_percentage_among_selected": _percentage(
            different_count,
            selected_count,
        ),
        "attempt_count_exact_set_match": None,
        "attempt_count_partial_set_overlap": None,
        "attempt_count_no_set_overlap": None,
        "median_selected_final_lookup_similarity": None,
        "average_selected_final_lookup_similarity": None,
    }


def build_nontext_field_adoption_summary(
    completed_ai_fields: pd.DataFrame,
) -> pd.DataFrame:
    """Return lookup and compensation-flag adoption summaries."""
    lookup_fields = completed_ai_fields.loc[
        completed_ai_fields["analysis_type"].eq("LOOKUP")
    ]
    rows = [
        _lookup_summary_row(group)
        for _, group in lookup_fields.groupby(
            "field_name",
            sort=True,
            dropna=False,
        )
    ]
    compensation = completed_ai_fields.loc[
        completed_ai_fields["analysis_type"].eq("COMPENSATION")
    ]

    if not compensation.empty:
        rows.append(_compensation_flag_summary_row(compensation))

    return pd.DataFrame.from_records(
        rows,
        columns=list(NONTEXT_FIELD_ADOPTION_COLUMNS),
    )
