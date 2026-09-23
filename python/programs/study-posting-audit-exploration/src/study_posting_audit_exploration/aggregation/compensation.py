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
_EXPECTED_SUGGESTION_COUNT_PER_KIND = 3

COMPENSATION_ANALYSIS_COLUMNS: tuple[str, ...] = (
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


COMPENSATION_OFFER_COMPOSITION_COLUMNS: tuple[str, ...] = (
    "summary_grain",
    "population_name",
    "offer_composition_category",
    "generic_suggestion_count",
    "specific_suggestion_count",
    "attempt_count",
    "population_attempt_count",
    "attempt_percentage",
    "is_exact_three_plus_three",
    "consistency_category",
)

_COMPOSITION_POPULATIONS: tuple[str, ...] = (
    "ALL_COMPLETED_AI_ATTEMPTS",
    "FINAL_COMPENSATION_YES",
)
_COMPOSITION_CATEGORIES: tuple[str, ...] = (
    "BOTH_KINDS",
    "GENERIC_ONLY",
    "SPECIFIC_ONLY",
    "NEITHER",
)
_CONSISTENCY_CATEGORIES: tuple[str, ...] = (
    "AI_NO_WITH_TEXT_OFFERS",
    "AI_YES_WITH_NO_TEXT_OFFERS",
    "FINAL_YES_WITH_NO_TEXT_OFFERS",
    "FINAL_YES_WITH_ONE_KIND_ONLY",
    "FINAL_YES_WITH_NON_3_PLUS_3",
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


def _serialized_boolean(
    value: object,
    *,
    value_name: str,
) -> bool | None:
    """Return one optional Boolean serialized by normalized report CSV."""
    if _is_missing_scalar(value):
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        normalized = value.strip().lower()

        if normalized == "true":
            return True

        if normalized == "false":
            return False

    raise ExplorationValidationError(f"{value_name} must contain true, false, or null")


def _offer_composition(
    *,
    generic_count: int,
    specific_count: int,
) -> str:
    """Return one mutually exclusive compensation offer composition."""
    if generic_count > 0 and specific_count > 0:
        return "BOTH_KINDS"

    if generic_count > 0:
        return "GENERIC_ONLY"

    if specific_count > 0:
        return "SPECIFIC_ONLY"

    return "NEITHER"


def _compensation_attempt_context(
    compensation: pd.DataFrame,
) -> pd.DataFrame:
    """Return one validated aggregate-safe row per completed AI attempt."""
    required = (
        "audit_record_id",
        "suggestion_counts_json",
        "flag_suggested",
        "flag_saved",
    )
    missing = [column for column in required if column not in compensation.columns]

    if missing:
        raise ExplorationValidationError(
            "completed AI compensation rows lack required composition columns: "
            + ", ".join(missing)
        )

    if compensation["audit_record_id"].duplicated(keep=False).any():
        raise ExplorationValidationError(
            "completed AI compensation rows must contain at most one row per "
            "audit record"
        )

    rows: list[dict[str, object]] = []

    for row in compensation.to_dict(orient="records"):
        counts = _suggestion_counts(row["suggestion_counts_json"])
        generic_count = counts["genericCompensation"]
        specific_count = counts["specificCompensation"]
        rows.append(
            {
                "audit_record_id": row["audit_record_id"],
                "generic_suggestion_count": generic_count,
                "specific_suggestion_count": specific_count,
                "offer_composition_category": _offer_composition(
                    generic_count=generic_count,
                    specific_count=specific_count,
                ),
                "flag_suggested": _serialized_boolean(
                    row["flag_suggested"],
                    value_name="flag_suggested",
                ),
                "flag_saved": _serialized_boolean(
                    row["flag_saved"],
                    value_name="flag_saved",
                ),
            }
        )

    return pd.DataFrame.from_records(
        rows,
        columns=[
            "audit_record_id",
            "generic_suggestion_count",
            "specific_suggestion_count",
            "offer_composition_category",
            "flag_suggested",
            "flag_saved",
        ],
    )


def _population_rows(
    context: pd.DataFrame,
    *,
    population_name: str,
) -> pd.DataFrame:
    """Return rows for one explicit completed-AI compensation population."""
    if population_name == "ALL_COMPLETED_AI_ATTEMPTS":
        return context

    if population_name == "FINAL_COMPENSATION_YES":
        return context.loc[context["flag_saved"].eq(True)]

    raise AssertionError(f"Unhandled compensation population: {population_name}")


def _composition_rows(
    context: pd.DataFrame,
) -> list[dict[str, object]]:
    """Return mutually exclusive offer-composition rows."""
    rows: list[dict[str, object]] = []

    for population_name in _COMPOSITION_POPULATIONS:
        population = _population_rows(
            context,
            population_name=population_name,
        )
        population_count = int(population["audit_record_id"].nunique(dropna=True))

        for category in _COMPOSITION_CATEGORIES:
            count = int(
                population.loc[
                    population["offer_composition_category"].eq(category),
                    "audit_record_id",
                ].nunique(dropna=True)
            )
            rows.append(
                {
                    "summary_grain": "OFFER_COMPOSITION",
                    "population_name": population_name,
                    "offer_composition_category": category,
                    "generic_suggestion_count": None,
                    "specific_suggestion_count": None,
                    "attempt_count": count,
                    "population_attempt_count": population_count,
                    "attempt_percentage": _percentage(count, population_count),
                    "is_exact_three_plus_three": None,
                    "consistency_category": None,
                }
            )

    return rows


def _count_pair_rows(
    context: pd.DataFrame,
) -> list[dict[str, object]]:
    """Return observed joint generic/specific suggestion-count rows."""
    rows: list[dict[str, object]] = []

    for population_name in _COMPOSITION_POPULATIONS:
        population = _population_rows(
            context,
            population_name=population_name,
        )
        population_count = int(population["audit_record_id"].nunique(dropna=True))

        for keys, group in population.groupby(
            [
                "offer_composition_category",
                "generic_suggestion_count",
                "specific_suggestion_count",
            ],
            sort=True,
            dropna=False,
        ):
            category, generic_value, specific_value = keys
            generic_count = _nonnegative_integer(
                generic_value,
                value_name="generic_suggestion_count",
            )
            specific_count = _nonnegative_integer(
                specific_value,
                value_name="specific_suggestion_count",
            )
            count = int(group["audit_record_id"].nunique(dropna=True))
            rows.append(
                {
                    "summary_grain": "OFFER_COUNT_PAIR",
                    "population_name": population_name,
                    "offer_composition_category": str(category),
                    "generic_suggestion_count": generic_count,
                    "specific_suggestion_count": specific_count,
                    "attempt_count": count,
                    "population_attempt_count": population_count,
                    "attempt_percentage": _percentage(count, population_count),
                    "is_exact_three_plus_three": (
                        generic_count == _EXPECTED_SUGGESTION_COUNT_PER_KIND
                        and specific_count == _EXPECTED_SUGGESTION_COUNT_PER_KIND
                    ),
                    "consistency_category": None,
                }
            )

    return rows


def _consistency_rows(
    context: pd.DataFrame,
) -> list[dict[str, object]]:
    """Return descriptive compensation workflow-consistency counts."""
    has_text_offers = context["generic_suggestion_count"].gt(0) | context[
        "specific_suggestion_count"
    ].gt(0)
    has_no_text_offers = ~has_text_offers
    one_kind_only = context["offer_composition_category"].isin(
        {"GENERIC_ONLY", "SPECIFIC_ONLY"}
    )
    exact_three_plus_three = context["generic_suggestion_count"].eq(3) & context[
        "specific_suggestion_count"
    ].eq(3)
    masks = {
        "AI_NO_WITH_TEXT_OFFERS": context["flag_suggested"].eq(False) & has_text_offers,
        "AI_YES_WITH_NO_TEXT_OFFERS": context["flag_suggested"].eq(True)
        & has_no_text_offers,
        "FINAL_YES_WITH_NO_TEXT_OFFERS": context["flag_saved"].eq(True)
        & has_no_text_offers,
        "FINAL_YES_WITH_ONE_KIND_ONLY": context["flag_saved"].eq(True) & one_kind_only,
        "FINAL_YES_WITH_NON_3_PLUS_3": context["flag_saved"].eq(True)
        & ~exact_three_plus_three,
    }
    ai_value_available = context["flag_suggested"].notna()
    final_yes = context["flag_saved"].eq(True)
    denominators = {
        "AI_NO_WITH_TEXT_OFFERS": (
            "AI_VALUE_AVAILABLE_COMPLETED_AI_ATTEMPTS",
            ai_value_available,
        ),
        "AI_YES_WITH_NO_TEXT_OFFERS": (
            "AI_VALUE_AVAILABLE_COMPLETED_AI_ATTEMPTS",
            ai_value_available,
        ),
        "FINAL_YES_WITH_NO_TEXT_OFFERS": (
            "FINAL_COMPENSATION_YES",
            final_yes,
        ),
        "FINAL_YES_WITH_ONE_KIND_ONLY": (
            "FINAL_COMPENSATION_YES",
            final_yes,
        ),
        "FINAL_YES_WITH_NON_3_PLUS_3": (
            "FINAL_COMPENSATION_YES",
            final_yes,
        ),
    }
    rows: list[dict[str, object]] = []

    for category in _CONSISTENCY_CATEGORIES:
        population_name, denominator_mask = denominators[category]
        count = int(
            context.loc[masks[category], "audit_record_id"].nunique(dropna=True)
        )
        population_count = int(
            context.loc[
                denominator_mask,
                "audit_record_id",
            ].nunique(dropna=True)
        )
        rows.append(
            {
                "summary_grain": "WORKFLOW_CONSISTENCY",
                "population_name": population_name,
                "offer_composition_category": None,
                "generic_suggestion_count": None,
                "specific_suggestion_count": None,
                "attempt_count": count,
                "population_attempt_count": population_count,
                "attempt_percentage": _percentage(count, population_count),
                "is_exact_three_plus_three": None,
                "consistency_category": category,
            }
        )

    return rows


def build_compensation_offer_composition_summary(
    completed_ai_fields: pd.DataFrame,
) -> pd.DataFrame:
    """Return offer composition, count pairs, and workflow consistency.

    Offer-composition categories are mutually exclusive within each population.
    Offer-count pairs are their joint count distribution. Workflow-consistency
    categories are separate descriptive checks that may overlap and must not be
    summed as though they partition a population.
    """
    compensation = completed_ai_fields.loc[
        completed_ai_fields["analysis_type"].eq("COMPENSATION")
    ]

    if compensation.empty:
        rows: list[dict[str, object]] = []
    else:
        context = _compensation_attempt_context(compensation)
        rows = [
            *_composition_rows(context),
            *_count_pair_rows(context),
            *_consistency_rows(context),
        ]

    return pd.DataFrame.from_records(
        rows,
        columns=list(COMPENSATION_OFFER_COMPOSITION_COLUMNS),
    )


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
        columns=list(COMPENSATION_ANALYSIS_COLUMNS),
    )
