from collections.abc import Callable

import pandas as pd
import pytest

from study_posting_audit_exploration import (
    ExplorationValidationError,
    build_compensation_analysis_summary,
    build_compensation_offer_composition_summary,
)


def compensation_row(
    *,
    audit_record_id: int,
    counts: str,
    picked_kind: str | None,
    picked_index: int | None,
    category: str,
    ratio: float | None,
) -> dict[str, object]:
    """Return one synthetic completed-AI compensation row."""
    return {
        "audit_record_id": audit_record_id,
        "field_name": "compensation",
        "analysis_type": "COMPENSATION",
        "suggestion_counts_json": counts,
        "picked_kind": picked_kind,
        "picked_index": picked_index,
        "edit_intensity_category": category,
        "character_edit_ratio": ratio,
        "edit_intensity_threshold_scheme_name": ("EXPLORATORY_CHARACTER_RATIO_10_30"),
    }


def summary_row(
    summary: pd.DataFrame,
    suggestion_kind: str,
) -> pd.Series:
    """Return one compensation-kind summary row."""
    return summary.loc[
        summary["compensation_suggestion_kind"].eq(suggestion_kind)
    ].iloc[0]


def test_compensation_summary_reports_kind_selection_and_editing() -> None:
    fields = pd.DataFrame.from_records(
        [
            compensation_row(
                audit_record_id=1,
                counts='{"genericCompensation": 2, "specificCompensation": 1}',
                picked_kind="genericCompensation",
                picked_index=0,
                category="EXACT",
                ratio=0.0,
            ),
            compensation_row(
                audit_record_id=2,
                counts='{"genericCompensation": 1, "specificCompensation": 2}',
                picked_kind="specificCompensation",
                picked_index=1,
                category="MODERATE_EDIT",
                ratio=0.20,
            ),
            compensation_row(
                audit_record_id=3,
                counts='{"genericCompensation": 1, "specificCompensation": 0}',
                picked_kind=None,
                picked_index=None,
                category="UNASSISTED",
                ratio=None,
            ),
            compensation_row(
                audit_record_id=4,
                counts='{"genericCompensation": 1, "specificCompensation": 1}',
                picked_kind="specificCompensation",
                picked_index=0,
                category="EDITED_UNCLASSIFIED",
                ratio=None,
            ),
        ]
    )

    summary = build_compensation_analysis_summary(fields)
    generic = summary_row(summary, "genericCompensation")
    specific = summary_row(summary, "specificCompensation")

    assert generic["completed_ai_attempt_count_with_suggestion"] == 4
    assert generic["offered_suggestion_count"] == 5
    assert generic["selected_suggestion_count"] == 1
    assert generic["suggestion_selection_percentage"] == pytest.approx(20.0)
    assert generic["selected_suggestion_count_exactly_retained"] == 1
    assert generic["selected_suggestion_count_moderately_edited"] == 0
    assert generic["selected_suggestion_count_unclassified_edit"] == 0

    assert specific["completed_ai_attempt_count_with_suggestion"] == 3
    assert specific["offered_suggestion_count"] == 4
    assert specific["selected_suggestion_count"] == 2
    assert specific["suggestion_selection_percentage"] == pytest.approx(50.0)
    assert specific["selected_suggestion_count_moderately_edited"] == 1
    assert specific["selected_suggestion_count_unclassified_edit"] == 1
    assert specific["median_character_edit_ratio"] == pytest.approx(0.20)
    assert specific["average_character_edit_ratio"] == pytest.approx(0.20)


def test_compensation_summary_excludes_unclassified_edit_from_ratio_statistics() -> (
    None
):
    fields = pd.DataFrame.from_records(
        [
            compensation_row(
                audit_record_id=1,
                counts='{"genericCompensation": 1}',
                picked_kind="genericCompensation",
                picked_index=0,
                category="EDITED_UNCLASSIFIED",
                ratio=None,
            )
        ]
    )

    row = summary_row(
        build_compensation_analysis_summary(fields),
        "genericCompensation",
    )

    assert row["selected_suggestion_count"] == 1
    assert row["selected_suggestion_count_unclassified_edit"] == 1
    assert pd.isna(row["median_character_edit_ratio"])
    assert pd.isna(row["average_character_edit_ratio"])


def test_compensation_summary_reports_zero_without_readability_pairs() -> None:
    fields = pd.DataFrame.from_records(
        [
            compensation_row(
                audit_record_id=1,
                counts='{"genericCompensation": 1}',
                picked_kind="genericCompensation",
                picked_index=0,
                category="LIGHT_EDIT",
                ratio=0.10,
            )
        ]
    )

    row = summary_row(
        build_compensation_analysis_summary(fields),
        "genericCompensation",
    )

    assert row["paired_selected_final_readability_count"] == 0
    assert pd.isna(row["median_flesch_kincaid_grade_change_final_minus_selected"])
    assert pd.isna(row["average_flesch_kincaid_grade_change_final_minus_selected"])
    assert row["count_consensus_grade_level_decrease"] == 0
    assert row["count_no_material_change"] == 0
    assert row["count_consensus_grade_level_increase"] == 0
    assert row["count_mixed_formula_direction"] == 0
    assert (
        row["edit_intensity_threshold_scheme_name"]
        == "EXPLORATORY_CHARACTER_RATIO_10_30"
    )


def test_compensation_summary_returns_canonical_empty_frame() -> None:
    summary = build_compensation_analysis_summary(
        pd.DataFrame(
            columns=[
                "audit_record_id",
                "analysis_type",
                "suggestion_counts_json",
                "picked_kind",
                "picked_index",
                "edit_intensity_category",
                "character_edit_ratio",
                "edit_intensity_threshold_scheme_name",
            ]
        )
    )

    assert summary.empty
    assert "compensation_suggestion_kind" in summary.columns
    assert "selected_suggestion_count_unclassified_edit" in summary.columns
    assert "paired_selected_final_readability_count" in summary.columns


@pytest.mark.parametrize(
    ("counts", "message"),
    [
        ("not-json", "contains invalid JSON"),
        ("[]", "must contain a JSON object"),
        ('{"genericCompensation": -1}', "must contain a nonnegative integer"),
        ('{"genericCompensation": true}', "must contain a nonnegative integer"),
    ],
)
def test_compensation_summary_rejects_invalid_counts(
    counts: str,
    message: str,
) -> None:
    fields = pd.DataFrame.from_records(
        [
            compensation_row(
                audit_record_id=1,
                counts=counts,
                picked_kind=None,
                picked_index=None,
                category="UNASSISTED",
                ratio=None,
            )
        ]
    )

    with pytest.raises(
        ExplorationValidationError,
        match=message,
    ):
        build_compensation_analysis_summary(fields)


def test_compensation_summary_includes_readability_pairs() -> None:
    fields = pd.DataFrame.from_records(
        [
            compensation_row(
                audit_record_id=1,
                counts='{"genericCompensation": 1}',
                picked_kind="genericCompensation",
                picked_index=0,
                category="LIGHT_EDIT",
                ratio=0.10,
            ),
            compensation_row(
                audit_record_id=2,
                counts='{"genericCompensation": 1}',
                picked_kind="genericCompensation",
                picked_index=0,
                category="MODERATE_EDIT",
                ratio=0.20,
            ),
        ]
    )
    pairs = pd.DataFrame.from_records(
        [
            {
                "audit_record_id": 1,
                "field_name": "compensation",
                "suggestion_kind": "genericCompensation",
                "readability_measure_name": "flesch_kincaid_grade",
                "change_final_minus_selected": -1.0,
                "consensus_grade_level_direction_category": (
                    "CONSENSUS_GRADE_LEVEL_DECREASE"
                ),
            },
            {
                "audit_record_id": 2,
                "field_name": "compensation",
                "suggestion_kind": "genericCompensation",
                "readability_measure_name": "flesch_kincaid_grade",
                "change_final_minus_selected": 0.0,
                "consensus_grade_level_direction_category": ("NO_MATERIAL_CHANGE"),
            },
        ]
    )

    row = summary_row(
        build_compensation_analysis_summary(
            fields,
            pairs,
        ),
        "genericCompensation",
    )

    assert row["paired_selected_final_readability_count"] == 2
    assert row["median_flesch_kincaid_grade_change_final_minus_selected"] == -0.5
    assert row["average_flesch_kincaid_grade_change_final_minus_selected"] == -0.5
    assert row["count_consensus_grade_level_decrease"] == 1
    assert row["count_no_material_change"] == 1
    assert row["count_consensus_grade_level_increase"] == 0
    assert row["count_mixed_formula_direction"] == 0


def composition_row(
    summary: pd.DataFrame,
    *,
    population: str,
    category: str,
) -> pd.Series:
    """Return one offer-composition row."""
    return summary.loc[
        summary["summary_grain"].eq("OFFER_COMPOSITION")
        & summary["population_name"].eq(population)
        & summary["offer_composition_category"].eq(category)
    ].iloc[0]


def test_compensation_offer_composition_reports_populations_and_pairs() -> None:
    """Summarize all completed AI attempts and the final-Yes subset."""
    rows = [
        compensation_row(
            audit_record_id=index,
            counts=counts,
            picked_kind=None,
            picked_index=None,
            category="UNASSISTED",
            ratio=None,
        )
        | {
            "flag_suggested": suggested,
            "flag_saved": saved,
        }
        for index, counts, suggested, saved in (
            (
                1,
                '{"genericCompensation": 3, "specificCompensation": 3}',
                "true",
                "true",
            ),
            (
                2,
                '{"genericCompensation": 3, "specificCompensation": 3}',
                "true",
                "true",
            ),
            (
                3,
                '{"genericCompensation": 1, "specificCompensation": 0}',
                "true",
                "true",
            ),
            (
                4,
                '{"genericCompensation": 2, "specificCompensation": 0}',
                "false",
                "true",
            ),
            (
                5,
                '{"genericCompensation": 0, "specificCompensation": 3}',
                "false",
                "true",
            ),
            (
                6,
                '{"genericCompensation": 0, "specificCompensation": 0}',
                "true",
                "true",
            ),
            (
                7,
                '{"genericCompensation": 1, "specificCompensation": 1}',
                "false",
                "false",
            ),
            (
                8,
                '{"genericCompensation": 0, "specificCompensation": 0}',
                "false",
                "false",
            ),
        )
    ]
    summary = build_compensation_offer_composition_summary(
        pd.DataFrame.from_records(rows)
    )

    all_both = composition_row(
        summary,
        population="ALL_COMPLETED_AI_ATTEMPTS",
        category="BOTH_KINDS",
    )
    final_yes_both = composition_row(
        summary,
        population="FINAL_COMPENSATION_YES",
        category="BOTH_KINDS",
    )
    final_yes_generic = composition_row(
        summary,
        population="FINAL_COMPENSATION_YES",
        category="GENERIC_ONLY",
    )
    final_yes_specific = composition_row(
        summary,
        population="FINAL_COMPENSATION_YES",
        category="SPECIFIC_ONLY",
    )
    final_yes_neither = composition_row(
        summary,
        population="FINAL_COMPENSATION_YES",
        category="NEITHER",
    )

    assert all_both["attempt_count"] == 3
    assert all_both["population_attempt_count"] == 8
    assert all_both["attempt_percentage"] == pytest.approx(37.5)
    assert final_yes_both["attempt_count"] == 2
    assert final_yes_both["population_attempt_count"] == 6
    assert final_yes_generic["attempt_count"] == 2
    assert final_yes_specific["attempt_count"] == 1
    assert final_yes_neither["attempt_count"] == 1

    pair = summary.loc[
        summary["summary_grain"].eq("OFFER_COUNT_PAIR")
        & summary["population_name"].eq("FINAL_COMPENSATION_YES")
        & summary["generic_suggestion_count"].eq(3)
        & summary["specific_suggestion_count"].eq(3)
    ].iloc[0]
    assert pair["attempt_count"] == 2
    assert pair["is_exact_three_plus_three"]


def test_compensation_offer_composition_reports_consistency_states() -> None:
    """Count descriptive contradictions and final-Yes incompleteness."""
    rows = [
        compensation_row(
            audit_record_id=index,
            counts=counts,
            picked_kind=None,
            picked_index=None,
            category="UNASSISTED",
            ratio=None,
        )
        | {
            "flag_suggested": suggested,
            "flag_saved": saved,
        }
        for index, counts, suggested, saved in (
            (
                1,
                '{"genericCompensation": 3, "specificCompensation": 3}',
                "true",
                "true",
            ),
            (
                2,
                '{"genericCompensation": 1, "specificCompensation": 0}',
                "false",
                "true",
            ),
            (
                3,
                '{"genericCompensation": 0, "specificCompensation": 0}',
                "true",
                "true",
            ),
            (
                4,
                '{"genericCompensation": 1, "specificCompensation": 1}',
                "false",
                "false",
            ),
        )
    ]
    summary = build_compensation_offer_composition_summary(
        pd.DataFrame.from_records(rows)
    )
    consistency = summary.loc[
        summary["summary_grain"].eq("WORKFLOW_CONSISTENCY")
    ].set_index("consistency_category")

    assert consistency.loc["AI_NO_WITH_TEXT_OFFERS", "attempt_count"] == 2
    assert (
        consistency.loc[
            "AI_NO_WITH_TEXT_OFFERS",
            "population_name",
        ]
        == "AI_VALUE_AVAILABLE_COMPLETED_AI_ATTEMPTS"
    )
    assert (
        consistency.loc[
            "AI_NO_WITH_TEXT_OFFERS",
            "population_attempt_count",
        ]
        == 4
    )
    assert consistency.loc["AI_YES_WITH_NO_TEXT_OFFERS", "attempt_count"] == 1
    assert consistency.loc["FINAL_YES_WITH_NO_TEXT_OFFERS", "attempt_count"] == 1
    assert (
        consistency.loc[
            "FINAL_YES_WITH_NO_TEXT_OFFERS",
            "population_name",
        ]
        == "FINAL_COMPENSATION_YES"
    )
    assert (
        consistency.loc[
            "FINAL_YES_WITH_NO_TEXT_OFFERS",
            "population_attempt_count",
        ]
        == 3
    )
    assert consistency.loc["FINAL_YES_WITH_ONE_KIND_ONLY", "attempt_count"] == 1
    assert consistency.loc["FINAL_YES_WITH_NON_3_PLUS_3", "attempt_count"] == 2


def test_compensation_offer_composition_returns_canonical_empty_frame() -> None:
    """Return stable columns when no compensation rows are available."""
    summary = build_compensation_offer_composition_summary(
        pd.DataFrame(
            columns=[
                "analysis_type",
                "audit_record_id",
                "suggestion_counts_json",
                "flag_suggested",
                "flag_saved",
            ]
        )
    )

    assert summary.empty
    assert tuple(summary.columns) == (
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


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda frame: frame.drop(columns=["flag_saved"]),
            "lack required composition columns",
        ),
        (
            lambda frame: pd.concat([frame, frame], ignore_index=True),
            "at most one row per audit record",
        ),
        (
            lambda frame: frame.assign(flag_suggested="SYNTHETIC_UNKNOWN"),
            "flag_suggested must contain true, false, or null",
        ),
        (
            lambda frame: frame.assign(flag_saved=1),
            "flag_saved must contain true, false, or null",
        ),
    ],
)
def test_compensation_offer_composition_rejects_invalid_context(
    mutate: Callable[[pd.DataFrame], pd.DataFrame],
    message: str,
) -> None:
    """Reject incomplete, duplicate, and invalid Boolean attempt rows."""
    base = pd.DataFrame.from_records(
        [
            compensation_row(
                audit_record_id=1,
                counts='{"genericCompensation": 3, "specificCompensation": 3}',
                picked_kind=None,
                picked_index=None,
                category="UNASSISTED",
                ratio=None,
            )
            | {
                "flag_suggested": "true",
                "flag_saved": "true",
            }
        ]
    )

    with pytest.raises(ExplorationValidationError, match=message):
        build_compensation_offer_composition_summary(mutate(base))


def test_compensation_offer_composition_accepts_boolean_and_missing_flags() -> None:
    """Accept native Booleans and preserve unavailable values."""
    rows = [
        compensation_row(
            audit_record_id=1,
            counts='{"genericCompensation": 3, "specificCompensation": 3}',
            picked_kind=None,
            picked_index=None,
            category="UNASSISTED",
            ratio=None,
        )
        | {
            "flag_suggested": True,
            "flag_saved": True,
        },
        compensation_row(
            audit_record_id=2,
            counts='{"genericCompensation": 0, "specificCompensation": 0}',
            picked_kind=None,
            picked_index=None,
            category="UNASSISTED",
            ratio=None,
        )
        | {
            "flag_suggested": None,
            "flag_saved": None,
        },
    ]

    summary = build_compensation_offer_composition_summary(
        pd.DataFrame.from_records(rows)
    )
    final_yes = summary.loc[
        summary["summary_grain"].eq("OFFER_COMPOSITION")
        & summary["population_name"].eq("FINAL_COMPENSATION_YES")
    ]

    assert set(final_yes["population_attempt_count"]) == {1}
    assert final_yes["attempt_count"].sum() == 1
