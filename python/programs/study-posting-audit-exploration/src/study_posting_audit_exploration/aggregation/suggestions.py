"""Suggestion availability, selection, and position summaries."""

import json
import math
from numbers import Integral, Real
from typing import cast

import pandas as pd

from study_posting_audit_exploration.errors import ExplorationValidationError

SUGGESTION_SELECTION_COLUMNS: tuple[str, ...] = (
    "field_name",
    "suggestion_kind",
    "suggestion_index",
    "offered_suggestion_count",
    "selected_suggestion_count",
    "unselected_suggestion_count",
    "completed_ai_attempt_count_with_at_least_one_suggestion",
    "completed_ai_attempt_count_with_selected_suggestion",
    "suggestion_level_selection_percentage",
    "attempt_level_selection_percentage",
    "suggestion_count_at_index",
    "selected_suggestion_count_at_index",
    "selection_percentage_at_index",
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


def _suggestion_counts(value: object) -> dict[str, int]:
    """Parse one serialized suggestion-count mapping."""
    if _is_missing_scalar(value):
        return {}

    if not isinstance(value, str):
        raise ExplorationValidationError(
            "suggestion_counts_json must contain a JSON object"
        )

    try:
        decoded = json.loads(value)
    except json.JSONDecodeError as error:
        raise ExplorationValidationError(
            "suggestion_counts_json contains invalid JSON"
        ) from error

    if not isinstance(decoded, dict):
        raise ExplorationValidationError(
            "suggestion_counts_json must contain a JSON object"
        )

    counts: dict[str, int] = {}

    for kind, count in cast("dict[object, object]", decoded).items():
        if not isinstance(kind, str) or not kind:
            raise ExplorationValidationError(
                "suggestion_counts_json contains an invalid suggestion kind"
            )

        if isinstance(count, bool) or not isinstance(count, Integral) or int(count) < 0:
            raise ExplorationValidationError(
                "suggestion_counts_json contains an invalid suggestion count"
            )

        counts[kind] = int(count)

    return counts


def _optional_index(value: object) -> int | None:
    """Return one optional nonnegative suggestion index."""
    if _is_missing_scalar(value):
        return None

    if isinstance(value, bool) or not isinstance(value, Real):
        raise ExplorationValidationError(
            "picked_index must contain a nonnegative integer or null"
        )

    converted = float(value)
    integer_value = int(converted)

    if not math.isfinite(converted) or converted != integer_value or integer_value < 0:
        raise ExplorationValidationError(
            "picked_index must contain a nonnegative integer or null"
        )

    return integer_value


def _optional_kind(value: object) -> str | None:
    """Return one optional nonblank suggestion kind."""
    if _is_missing_scalar(value):
        return None

    if not isinstance(value, str) or not value:
        raise ExplorationValidationError(
            "picked_kind must contain a nonblank string or null"
        )

    return value


def _expanded_suggestions(
    completed_ai_fields: pd.DataFrame,
) -> pd.DataFrame:
    """Return one row for every offered suggestion position."""
    rows: list[dict[str, object]] = []

    for source in completed_ai_fields.to_dict(orient="records"):
        field_name = str(source["field_name"])
        record_id = source["audit_record_id"]
        picked_kind = _optional_kind(source["picked_kind"])
        picked_index = _optional_index(source["picked_index"])

        for suggestion_kind, count in _suggestion_counts(
            source["suggestion_counts_json"]
        ).items():
            rows.extend(
                {
                    "audit_record_id": record_id,
                    "field_name": field_name,
                    "suggestion_kind": suggestion_kind,
                    "suggestion_index": suggestion_index,
                    "selected": (
                        picked_kind == suggestion_kind
                        and picked_index == suggestion_index
                    ),
                }
                for suggestion_index in range(count)
            )

    return pd.DataFrame.from_records(
        rows,
        columns=[
            "audit_record_id",
            "field_name",
            "suggestion_kind",
            "suggestion_index",
            "selected",
        ],
    )


def _selection_summary_row(
    group: pd.DataFrame,
    *,
    field_population: pd.DataFrame,
) -> dict[str, object]:
    """Return one field, kind, and index suggestion summary."""
    field_name = str(group["field_name"].iloc[0])
    suggestion_kind = str(group["suggestion_kind"].iloc[0])
    suggestion_index = int(group["suggestion_index"].iloc[0])
    offered_count = len(group)
    selected_count = int(group["selected"].sum())
    field_offers = field_population.loc[
        field_population["suggestion_kind"].eq(suggestion_kind)
    ]
    attempts_with_offer = int(field_offers["audit_record_id"].nunique(dropna=True))
    attempts_with_selection = int(
        field_offers.loc[
            field_offers["selected"],
            "audit_record_id",
        ].nunique(dropna=True)
    )

    return {
        "field_name": field_name,
        "suggestion_kind": suggestion_kind,
        "suggestion_index": suggestion_index,
        "offered_suggestion_count": len(field_offers),
        "selected_suggestion_count": int(field_offers["selected"].sum()),
        "unselected_suggestion_count": int(
            len(field_offers) - field_offers["selected"].sum()
        ),
        "completed_ai_attempt_count_with_at_least_one_suggestion": (
            attempts_with_offer
        ),
        "completed_ai_attempt_count_with_selected_suggestion": (
            attempts_with_selection
        ),
        "suggestion_level_selection_percentage": _percentage(
            int(field_offers["selected"].sum()),
            len(field_offers),
        ),
        "attempt_level_selection_percentage": _percentage(
            attempts_with_selection,
            attempts_with_offer,
        ),
        "suggestion_count_at_index": offered_count,
        "selected_suggestion_count_at_index": selected_count,
        "selection_percentage_at_index": _percentage(
            selected_count,
            offered_count,
        ),
    }


def build_suggestion_selection_summary(
    completed_ai_fields: pd.DataFrame,
) -> pd.DataFrame:
    """Return suggestion availability and selection summaries."""
    text_fields = completed_ai_fields.loc[
        completed_ai_fields["analysis_type"].isin(
            {
                "TEXT",
                "COMPENSATION",
            }
        )
    ]
    expanded = _expanded_suggestions(text_fields)
    rows: list[dict[str, object]] = []

    for keys, group in expanded.groupby(
        [
            "field_name",
            "suggestion_kind",
            "suggestion_index",
        ],
        sort=True,
        dropna=False,
    ):
        field_name, _, _ = keys
        field_population = expanded.loc[expanded["field_name"].eq(str(field_name))]
        rows.append(
            _selection_summary_row(
                group,
                field_population=field_population,
            )
        )

    return pd.DataFrame.from_records(
        rows,
        columns=list(SUGGESTION_SELECTION_COLUMNS),
    )
