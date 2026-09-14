"""Compensation suggestion selection, editing, and readability summaries."""

import json
import math
from numbers import Real

import pandas as pd

from study_posting_audit_exploration.errors import ExplorationValidationError
from study_posting_audit_exploration.models import DescriptiveStatistics
from study_posting_audit_exploration.statistics import describe_numeric

_COMPENSATION_KINDS: tuple[str, ...] = (
    "genericCompensation",
    "specificCompensation",
)
_FLESCH_KINCAID_GRADE = "flesch_kincaid_grade"

_COMPENSATION_ANALYSIS_COLUMNS: tuple[str, ...] = (
    "compensation_suggestion_kind",
    "completed_ai_attempt_count_with_suggestion",
    "offered_suggestion_count",
    "selected_suggestion_count",
    "suggestion_selection_percentage",
    "selected_suggestion_count_exactly_retained",
    "selected_suggestion_count_cosmetically_changed",
    "selected_suggestion_count_lightly_edited",
    "selected_suggestion_count_moderately_edited",
    "selected_suggestion_count_heavily_edited",
    "selected_suggestion_count_unclassified_edit",
    "selected_suggestion_count_replaced",
    "median_character_edit_ratio",
    "average_character_edit_ratio",
    "paired_selected_final_readability_count",
    "median_flesch_kincaid_grade_change_final_minus_selected",
    "average_flesch_kincaid_grade_change_final_minus_selected",
    "count_consensus_grade_level_decrease",
    "count_no_material_change",
    "count_consensus_grade_level_increase",
    "count_mixed_formula_direction",
    "edit_intensity_threshold_scheme_name",
)

_EDITED_CATEGORIES_WITH_USABLE_METRICS = frozenset(
    {
        "COSMETIC",
        "LIGHT_EDIT",
        "MODERATE_EDIT",
        "HEAVY_EDIT",
        "REPLACED",
    }
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


def _nonnegative_integer(
    value: object,
    *,
    value_name: str,
) -> int:
    """Return one nonnegative integral value."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ExplorationValidationError(
            f"{value_name} must contain a nonnegative integer"
        )

    converted = float(value)
    integer_value = int(converted)

    if not math.isfinite(converted) or converted != integer_value or integer_value < 0:
        raise ExplorationValidationError(
            f"{value_name} must contain a nonnegative integer"
        )

    return integer_value


def _optional_nonnegative_index(value: object) -> int | None:
    """Return one optional nonnegative suggestion index."""
    if _is_missing_scalar(value):
        return None

    return _nonnegative_integer(
        value,
        value_name="picked_index",
    )


def _suggestion_counts(value: object) -> dict[str, int]:
    """Decode suggestion counts using the validated JSON representation."""
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

    for kind in _COMPENSATION_KINDS:
        raw_count = decoded.get(kind, 0)
        counts[kind] = _nonnegative_integer(
            raw_count,
            value_name=f"suggestion count for {kind}",
        )

    return counts


def _category_count(
    selected: pd.DataFrame,
    category: str,
) -> int:
    """Return selected compensation rows in one edit category."""
    return int(selected["edit_intensity_category"].eq(category).sum())


def _scheme_name(fields: pd.DataFrame) -> str | None:
    """Return the unique configured threshold scheme."""
    values = (
        fields["edit_intensity_threshold_scheme_name"].dropna().astype(str).unique()
    )

    return str(values[0]) if len(values) == 1 else None


def _readability_values(
    readability_pairs: pd.DataFrame,
    *,
    suggestion_kind: str,
) -> tuple[pd.DataFrame, DescriptiveStatistics]:
    """Return one compensation kind's Flesch-Kincaid pair rows and statistics."""
    grade_pairs = readability_pairs.loc[
        readability_pairs["field_name"].eq("compensation")
        & readability_pairs["suggestion_kind"].eq(suggestion_kind)
        & readability_pairs["readability_measure_name"].eq(_FLESCH_KINCAID_GRADE)
    ]
    statistics = describe_numeric(
        grade_pairs["change_final_minus_selected"],
        metric_name=(f"{suggestion_kind}_flesch_kincaid_grade_change"),
    )

    return grade_pairs, statistics


def _compensation_summary_row(
    fields: pd.DataFrame,
    readability_pairs: pd.DataFrame,
    *,
    suggestion_kind: str,
) -> dict[str, object]:
    """Return one compensation-kind selection, editing, and readability row."""
    count_mappings = fields["suggestion_counts_json"].map(_suggestion_counts)
    offered_counts = count_mappings.map(lambda counts: counts[suggestion_kind])
    offered_attempts = offered_counts.gt(0)
    picked_indices = fields["picked_index"].map(_optional_nonnegative_index)
    selected_mask = fields["picked_kind"].eq(suggestion_kind) & picked_indices.notna()
    selected = fields.loc[selected_mask]
    edited_with_usable_metrics = selected.loc[
        selected["edit_intensity_category"].isin(_EDITED_CATEGORIES_WITH_USABLE_METRICS)
    ]
    character_statistics = describe_numeric(
        edited_with_usable_metrics["character_edit_ratio"],
        metric_name=f"{suggestion_kind}_character_edit_ratio",
    )
    grade_pairs, grade_statistics = _readability_values(
        readability_pairs,
        suggestion_kind=suggestion_kind,
    )
    consensus = grade_pairs["consensus_grade_level_direction_category"]
    offered_suggestion_count = int(offered_counts.sum())
    selected_count = len(selected)

    return {
        "compensation_suggestion_kind": suggestion_kind,
        "completed_ai_attempt_count_with_suggestion": int(
            fields.loc[
                offered_attempts,
                "audit_record_id",
            ].nunique(dropna=True)
        ),
        "offered_suggestion_count": offered_suggestion_count,
        "selected_suggestion_count": selected_count,
        "suggestion_selection_percentage": _percentage(
            selected_count,
            offered_suggestion_count,
        ),
        "selected_suggestion_count_exactly_retained": _category_count(
            selected,
            "EXACT",
        ),
        "selected_suggestion_count_cosmetically_changed": _category_count(
            selected,
            "COSMETIC",
        ),
        "selected_suggestion_count_lightly_edited": _category_count(
            selected,
            "LIGHT_EDIT",
        ),
        "selected_suggestion_count_moderately_edited": _category_count(
            selected,
            "MODERATE_EDIT",
        ),
        "selected_suggestion_count_heavily_edited": _category_count(
            selected,
            "HEAVY_EDIT",
        ),
        "selected_suggestion_count_unclassified_edit": _category_count(
            selected,
            "EDITED_UNCLASSIFIED",
        ),
        "selected_suggestion_count_replaced": _category_count(
            selected,
            "REPLACED",
        ),
        "median_character_edit_ratio": character_statistics.median,
        "average_character_edit_ratio": character_statistics.average,
        "paired_selected_final_readability_count": int(
            grade_pairs["audit_record_id"].nunique(dropna=True)
        ),
        "median_flesch_kincaid_grade_change_final_minus_selected": (
            grade_statistics.median
        ),
        "average_flesch_kincaid_grade_change_final_minus_selected": (
            grade_statistics.average
        ),
        "count_consensus_grade_level_decrease": int(
            consensus.eq("CONSENSUS_GRADE_LEVEL_DECREASE").sum()
        ),
        "count_no_material_change": int(consensus.eq("NO_MATERIAL_CHANGE").sum()),
        "count_consensus_grade_level_increase": int(
            consensus.eq("CONSENSUS_GRADE_LEVEL_INCREASE").sum()
        ),
        "count_mixed_formula_direction": int(
            consensus.eq("MIXED_FORMULA_DIRECTION").sum()
        ),
        "edit_intensity_threshold_scheme_name": _scheme_name(fields),
    }


def build_compensation_analysis_summary(
    completed_ai_fields: pd.DataFrame,
    readability_pairs: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Return compensation summaries by generic and specific suggestion kind."""
    compensation = completed_ai_fields.loc[
        completed_ai_fields["analysis_type"].eq("COMPENSATION")
    ]
    resolved_pairs = (
        pd.DataFrame(
            columns=[
                "audit_record_id",
                "field_name",
                "suggestion_kind",
                "readability_measure_name",
                "change_final_minus_selected",
                "consensus_grade_level_direction_category",
            ]
        )
        if readability_pairs is None
        else readability_pairs
    )

    if compensation.empty:
        rows: list[dict[str, object]] = []
    else:
        rows = [
            _compensation_summary_row(
                compensation,
                resolved_pairs,
                suggestion_kind=suggestion_kind,
            )
            for suggestion_kind in _COMPENSATION_KINDS
        ]

    return pd.DataFrame.from_records(
        rows,
        columns=list(_COMPENSATION_ANALYSIS_COLUMNS),
    )
