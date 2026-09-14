"""Field adoption and edit-intensity summaries."""

import pandas as pd

from study_posting_audit_exploration.statistics import describe_numeric

_TEXT_ANALYSIS_TYPES = frozenset(
    {
        "TEXT",
        "COMPENSATION",
    }
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

_FIELD_ADOPTION_EDITING_COLUMNS: tuple[str, ...] = (
    "field_name",
    "analysis_type",
    "completed_ai_attempt_count",
    "completed_ai_attempt_count_with_suggestion_offered",
    "completed_ai_attempt_count_with_suggestion_selected",
    "completed_ai_attempt_count_selected_and_exactly_retained",
    "completed_ai_attempt_count_selected_and_cosmetically_changed",
    "completed_ai_attempt_count_selected_and_lightly_edited",
    "completed_ai_attempt_count_selected_and_moderately_edited",
    "completed_ai_attempt_count_selected_and_heavily_edited",
    "completed_ai_attempt_count_selected_and_unclassified_edit",
    "completed_ai_attempt_count_selected_and_replaced",
    "completed_ai_attempt_count_selected_then_cleared",
    "completed_ai_attempt_count_unassisted",
    "suggestion_selection_percentage_among_attempts_with_offer",
    "exact_retention_percentage_among_selected_attempts",
    "cosmetic_change_percentage_among_selected_attempts",
    "light_edit_percentage_among_selected_attempts",
    "moderate_edit_percentage_among_selected_attempts",
    "heavy_edit_percentage_among_selected_attempts",
    "unclassified_edit_percentage_among_selected_attempts",
    "replacement_percentage_among_selected_attempts",
    "cleared_percentage_among_selected_attempts",
    "median_character_edit_ratio_among_edited_attempts",
    "average_character_edit_ratio_among_edited_attempts",
    "median_ter_rate_among_edited_attempts",
    "average_ter_rate_among_edited_attempts",
    "edit_intensity_threshold_scheme_name",
)


def _percentage(
    numerator: int,
    denominator: int,
) -> float | None:
    """Return a percentage or ``None`` for an empty denominator."""
    if denominator == 0:
        return None

    return 100.0 * numerator / denominator


def _attempt_count(
    fields: pd.DataFrame,
    mask: pd.Series,
) -> int:
    """Return distinct attempts satisfying one row-level condition."""
    return int(fields.loc[mask, "audit_record_id"].nunique(dropna=True))


def _category_attempt_count(
    fields: pd.DataFrame,
    category: str,
) -> int:
    """Return distinct attempts assigned one edit-intensity category."""
    return _attempt_count(
        fields,
        fields["edit_intensity_category"].eq(category),
    )


def _field_summary_row(
    fields: pd.DataFrame,
) -> dict[str, object]:
    """Return one text-field adoption and editing summary."""
    offered = fields["suggestion_count_total"].fillna(0).gt(0)
    selected = fields["picked_index"].notna()
    completed_count = int(fields["audit_record_id"].nunique(dropna=True))
    offered_count = _attempt_count(fields, offered)
    selected_count = _attempt_count(fields, selected)

    exact_count = _category_attempt_count(fields, "EXACT")
    cosmetic_count = _category_attempt_count(fields, "COSMETIC")
    light_count = _category_attempt_count(fields, "LIGHT_EDIT")
    moderate_count = _category_attempt_count(fields, "MODERATE_EDIT")
    heavy_count = _category_attempt_count(fields, "HEAVY_EDIT")
    unclassified_count = _category_attempt_count(fields, "EDITED_UNCLASSIFIED")
    replaced_count = _category_attempt_count(fields, "REPLACED")
    cleared_count = _category_attempt_count(fields, "CLEARED")
    unassisted_count = _category_attempt_count(fields, "UNASSISTED")

    edited_with_usable_metrics = fields.loc[
        fields["edit_intensity_category"].isin(_EDITED_CATEGORIES_WITH_USABLE_METRICS)
    ]
    character_statistics = describe_numeric(
        edited_with_usable_metrics["character_edit_ratio"],
        metric_name="character_edit_ratio",
    )
    ter_statistics = describe_numeric(
        edited_with_usable_metrics["ter_rate"],
        metric_name="ter_rate",
    )
    scheme_values = (
        fields["edit_intensity_threshold_scheme_name"].dropna().astype(str).unique()
    )
    scheme_name = str(scheme_values[0]) if len(scheme_values) == 1 else None

    return {
        "field_name": str(fields["field_name"].iloc[0]),
        "analysis_type": str(fields["analysis_type"].iloc[0]),
        "completed_ai_attempt_count": completed_count,
        "completed_ai_attempt_count_with_suggestion_offered": offered_count,
        "completed_ai_attempt_count_with_suggestion_selected": selected_count,
        "completed_ai_attempt_count_selected_and_exactly_retained": exact_count,
        "completed_ai_attempt_count_selected_and_cosmetically_changed": (
            cosmetic_count
        ),
        "completed_ai_attempt_count_selected_and_lightly_edited": light_count,
        "completed_ai_attempt_count_selected_and_moderately_edited": (moderate_count),
        "completed_ai_attempt_count_selected_and_heavily_edited": heavy_count,
        "completed_ai_attempt_count_selected_and_unclassified_edit": (
            unclassified_count
        ),
        "completed_ai_attempt_count_selected_and_replaced": replaced_count,
        "completed_ai_attempt_count_selected_then_cleared": cleared_count,
        "completed_ai_attempt_count_unassisted": unassisted_count,
        "suggestion_selection_percentage_among_attempts_with_offer": (
            _percentage(
                selected_count,
                offered_count,
            )
        ),
        "exact_retention_percentage_among_selected_attempts": _percentage(
            exact_count,
            selected_count,
        ),
        "cosmetic_change_percentage_among_selected_attempts": _percentage(
            cosmetic_count,
            selected_count,
        ),
        "light_edit_percentage_among_selected_attempts": _percentage(
            light_count,
            selected_count,
        ),
        "moderate_edit_percentage_among_selected_attempts": _percentage(
            moderate_count,
            selected_count,
        ),
        "heavy_edit_percentage_among_selected_attempts": _percentage(
            heavy_count,
            selected_count,
        ),
        "unclassified_edit_percentage_among_selected_attempts": _percentage(
            unclassified_count,
            selected_count,
        ),
        "replacement_percentage_among_selected_attempts": _percentage(
            replaced_count,
            selected_count,
        ),
        "cleared_percentage_among_selected_attempts": _percentage(
            cleared_count,
            selected_count,
        ),
        "median_character_edit_ratio_among_edited_attempts": (
            character_statistics.median
        ),
        "average_character_edit_ratio_among_edited_attempts": (
            character_statistics.average
        ),
        "median_ter_rate_among_edited_attempts": ter_statistics.median,
        "average_ter_rate_among_edited_attempts": ter_statistics.average,
        "edit_intensity_threshold_scheme_name": scheme_name,
    }


def build_field_adoption_editing_summary(
    completed_ai_fields: pd.DataFrame,
) -> pd.DataFrame:
    """Return adoption and edit-intensity summaries for text fields."""
    text_fields = completed_ai_fields.loc[
        completed_ai_fields["analysis_type"].isin(_TEXT_ANALYSIS_TYPES)
    ]
    rows = [
        _field_summary_row(group)
        for _, group in text_fields.groupby(
            [
                "field_name",
                "analysis_type",
            ],
            sort=True,
            dropna=False,
        )
    ]

    return pd.DataFrame.from_records(
        rows,
        columns=list(_FIELD_ADOPTION_EDITING_COLUMNS),
    )
