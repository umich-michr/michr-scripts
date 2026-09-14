"""Edit-intensity derivation for completed AI field-analysis rows."""

import math
from numbers import Real

import pandas as pd

from study_posting_audit_exploration.errors import ExplorationValidationError

EDIT_INTENSITY_THRESHOLD_SCHEME = "EXPLORATORY_CHARACTER_RATIO_10_30"

_LIGHT_EDIT_MAXIMUM = 0.10
_MODERATE_EDIT_MAXIMUM = 0.30

_EDIT_INTENSITY_COLUMNS: tuple[str, ...] = (
    "audit_record_id",
    "study_num",
    "field_name",
    "analysis_type",
    "match_type",
    "suggestion_count_total",
    "picked_kind",
    "picked_index",
    "character_edit_distance",
    "suggestion_character_count",
    "final_character_count",
    "character_edit_ratio",
    "ter_rate",
    "soft_word_edit_distance",
    "policy_adjusted_effort_saved",
    "estimated_characters_saved",
    "edit_intensity_category",
    "edit_intensity_threshold_scheme_name",
    "lookup_similarity",
    "flag_suggested",
    "flag_saved",
    "flag_accepted",
    "flag_changed",
)

_REQUIRED_METRIC_COLUMNS: tuple[str, ...] = (
    "record_id",
    "field_name",
    "analysis_type",
    "match_type",
    "suggestion_count_total",
    "picked_kind",
    "picked_index",
    "character_edit_distance",
    "suggestion_character_count",
    "final_character_count",
    "ter_rate",
    "soft_word_edit_distance",
    "policy_adjusted_effort_saved",
    "estimated_characters_saved",
    "lookup_similarity",
    "flag_suggested",
    "flag_saved",
    "flag_accepted",
    "flag_changed",
)

_DIRECT_EDIT_CATEGORIES: dict[str, str] = {
    "EXACT": "EXACT",
    "COSMETIC_EQUIVALENT": "COSMETIC",
    "REMOVED": "CLEARED",
    "UNASSISTED": "UNASSISTED",
}


def _optional_finite_number(
    value: object,
    *,
    value_name: str,
) -> float | None:
    """Return one optional finite numeric value."""
    if value is None or value is pd.NA or value is pd.NaT:
        return None

    if isinstance(value, bool) or not isinstance(value, Real):
        raise ExplorationValidationError(
            f"AI-assistance {value_name} must be numeric or null"
        )

    converted = float(value)

    if not math.isfinite(converted):
        raise ExplorationValidationError(f"AI-assistance {value_name} must be finite")

    return converted


def _optional_nonnegative_integer(
    value: object,
    *,
    value_name: str,
) -> int | None:
    """Return one optional nonnegative integer."""
    converted = _optional_finite_number(
        value,
        value_name=value_name,
    )

    if converted is None:
        return None

    integer_value = int(converted)

    if converted != integer_value or integer_value < 0:
        raise ExplorationValidationError(
            f"AI-assistance {value_name} must be a nonnegative integer"
        )

    return integer_value


def _character_edit_ratio(
    *,
    edit_distance: object,
    suggestion_length: object,
    final_length: object,
) -> float | None:
    """Return normalized character edit distance when all inputs exist."""
    converted_distance = _optional_finite_number(
        edit_distance,
        value_name="character_edit_distance",
    )
    converted_suggestion_length = _optional_nonnegative_integer(
        suggestion_length,
        value_name="suggestion_character_count",
    )
    converted_final_length = _optional_nonnegative_integer(
        final_length,
        value_name="final_character_count",
    )

    if (
        converted_distance is None
        or converted_suggestion_length is None
        or converted_final_length is None
    ):
        return None

    if converted_distance < 0:
        raise ExplorationValidationError(
            "AI-assistance character_edit_distance must be nonnegative"
        )

    denominator = max(
        converted_suggestion_length,
        converted_final_length,
        1,
    )

    return converted_distance / denominator


def _classify_edited(
    *,
    character_edit_ratio: float | None,
    suggestion_character_count: int | None,
    final_character_count: int | None,
) -> str:
    """Return the category for one upstream EDITED result."""
    if suggestion_character_count is None or suggestion_character_count <= 0:
        if final_character_count is not None and final_character_count > 0:
            return "REPLACED"

        raise ExplorationValidationError(
            "edited AI-assistance row lacks usable character lengths"
        )

    if character_edit_ratio is None:
        raise ExplorationValidationError(
            "edited AI-assistance row lacks a character edit ratio"
        )

    if character_edit_ratio <= _LIGHT_EDIT_MAXIMUM:
        return "LIGHT_EDIT"

    if character_edit_ratio <= _MODERATE_EDIT_MAXIMUM:
        return "MODERATE_EDIT"

    return "HEAVY_EDIT"


def classify_edit_intensity(
    *,
    match_type: str,
    character_edit_ratio: float | None,
    suggestion_character_count: int | None,
    final_character_count: int | None,
) -> str:
    """Return the operational edit-intensity category."""
    direct_category = _DIRECT_EDIT_CATEGORIES.get(match_type)

    if direct_category is not None:
        return direct_category

    if match_type == "EDITED":
        return _classify_edited(
            character_edit_ratio=character_edit_ratio,
            suggestion_character_count=suggestion_character_count,
            final_character_count=final_character_count,
        )

    raise ExplorationValidationError(
        f"unsupported AI-assistance match type for edit intensity: {match_type!r}"
    )


def _require_columns(
    frame: pd.DataFrame,
    *,
    column_names: tuple[str, ...],
    frame_name: str,
) -> None:
    """Require the columns consumed by this derivation."""
    missing = tuple(
        column_name for column_name in column_names if column_name not in frame.columns
    )

    if missing:
        raise ExplorationValidationError(
            f"{frame_name} lacks required columns: {missing!r}"
        )


def derive_completed_ai_field_analysis(
    ai_assistance_metrics: pd.DataFrame,
    records: pd.DataFrame,
    *,
    threshold_scheme_name: str = EDIT_INTENSITY_THRESHOLD_SCHEME,
) -> pd.DataFrame:
    """Return one derived row per completed AI field analysis."""
    _require_columns(
        ai_assistance_metrics,
        column_names=_REQUIRED_METRIC_COLUMNS,
        frame_name="ai_assistance_metrics",
    )
    _require_columns(
        records,
        column_names=(
            "ID",
            "STUDY_NUM",
            "ATTEMPT_TYPE",
            "ATTEMPT_RESULT",
        ),
        frame_name="records",
    )

    context = records.loc[
        records["ATTEMPT_TYPE"].eq("AI") & records["ATTEMPT_RESULT"].eq("COMPLETE"),
        [
            "ID",
            "STUDY_NUM",
        ],
    ].rename(
        columns={
            "ID": "record_id",
            "STUDY_NUM": "study_num",
        }
    )
    joined = ai_assistance_metrics.loc[
        :,
        list(_REQUIRED_METRIC_COLUMNS),
    ].merge(
        context,
        on="record_id",
        how="inner",
        validate="many_to_one",
    )
    rows: list[dict[str, object]] = []

    for source in joined.to_dict(orient="records"):
        suggestion_character_count = _optional_nonnegative_integer(
            source["suggestion_character_count"],
            value_name="suggestion_character_count",
        )
        final_character_count = _optional_nonnegative_integer(
            source["final_character_count"],
            value_name="final_character_count",
        )
        ratio = _character_edit_ratio(
            edit_distance=source["character_edit_distance"],
            suggestion_length=suggestion_character_count,
            final_length=final_character_count,
        )
        category = classify_edit_intensity(
            match_type=str(source["match_type"]),
            character_edit_ratio=ratio,
            suggestion_character_count=suggestion_character_count,
            final_character_count=final_character_count,
        )
        rows.append(
            {
                "audit_record_id": source["record_id"],
                "study_num": source["study_num"],
                "field_name": source["field_name"],
                "analysis_type": source["analysis_type"],
                "match_type": source["match_type"],
                "suggestion_count_total": source["suggestion_count_total"],
                "picked_kind": source["picked_kind"],
                "picked_index": source["picked_index"],
                "character_edit_distance": source["character_edit_distance"],
                "suggestion_character_count": suggestion_character_count,
                "final_character_count": final_character_count,
                "character_edit_ratio": ratio,
                "ter_rate": source["ter_rate"],
                "soft_word_edit_distance": source["soft_word_edit_distance"],
                "policy_adjusted_effort_saved": (
                    source["policy_adjusted_effort_saved"]
                ),
                "estimated_characters_saved": source["estimated_characters_saved"],
                "edit_intensity_category": category,
                "edit_intensity_threshold_scheme_name": threshold_scheme_name,
                "lookup_similarity": source["lookup_similarity"],
                "flag_suggested": source["flag_suggested"],
                "flag_saved": source["flag_saved"],
                "flag_accepted": source["flag_accepted"],
                "flag_changed": source["flag_changed"],
            }
        )

    return pd.DataFrame.from_records(
        rows,
        columns=list(_EDIT_INTENSITY_COLUMNS),
    )
