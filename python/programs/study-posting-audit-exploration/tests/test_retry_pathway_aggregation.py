"""Tests for identifier-free retry-pathway aggregates."""

from __future__ import annotations

import pandas as pd
import pytest

from study_posting_audit_exploration import (
    RETRY_PATHWAY_CATEGORIES,
    ExplorationValidationError,
    build_retry_card_summary,
    build_retry_characteristics_summary,
    build_study_retry_pathway_summary,
)
from study_posting_audit_exploration.aggregation.retry_pathways import (
    RETRY_CHARACTERISTICS_SUMMARY_COLUMNS,
    STUDY_RETRY_PATHWAY_SUMMARY_COLUMNS,
)
from study_posting_audit_exploration.derivation.retry_pathways import (
    STUDY_RETRY_CONTEXT_COLUMNS,
)

FORBIDDEN_AGGREGATE_COLUMNS = {
    "study_num",
    "audit_record_id",
    "attempt_author_user_name",
    "feedback_text",
    "study_content_source_other_value",
    "llm_inferred_study_content_source_other_value",
}


def _integer_override(
    overrides: dict[str, object],
    key: str,
) -> int:
    """Return one checked integer synthetic override."""
    value = overrides.pop(key, 0)

    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{key} must be an integer")

    return value


def _nullable_float_override(
    overrides: dict[str, object],
    key: str,
) -> float | None:
    """Return one checked nullable-float synthetic override."""
    value = overrides.pop(key, None)

    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{key} must be numeric or None")

    return float(value)


def _retry_row(
    *,
    study_num: str,
    pathway_category: str,
    completion_state: str,
    final_mode: str,
    attempt_count: int,
    **overrides: object,
) -> dict[str, object]:
    """Return one complete synthetic internal retry-context row."""
    ai_count = _integer_override(overrides, "ai_count")
    manual_count = _integer_override(overrides, "manual_count")
    author_changed = bool(overrides.pop("author_changed", False))
    has_ai_error = bool(overrides.pop("has_ai_error", False))
    has_user_dropped = bool(overrides.pop("has_user_dropped", False))
    returned_result_ai = bool(overrides.pop("returned_result_ai", False))
    source_eligible = bool(overrides.pop("source_eligible", False))
    signature_eligible = bool(overrides.pop("signature_eligible", False))
    signature_changed = bool(overrides.pop("signature_changed", False))
    feedback_recorded = bool(overrides.pop("feedback_recorded", False))
    completion_minutes = _nullable_float_override(
        overrides,
        "completion_minutes",
    )
    unresolved_minutes = _nullable_float_override(
        overrides,
        "unresolved_minutes",
    )

    if overrides:
        raise AssertionError(
            f"unsupported synthetic retry overrides: {sorted(overrides)!r}"
        )

    row: dict[str, object] = dict.fromkeys(
        STUDY_RETRY_CONTEXT_COLUMNS,
        False,
    )
    row.update(
        {
            "study_num": study_num,
            "pathway_category": pathway_category,
            "completion_state": completion_state,
            "attempt_frequency": (
                "SINGLE_ATTEMPT" if attempt_count == 1 else "MULTIPLE_ATTEMPTS"
            ),
            "all_attempt_count": attempt_count,
            "ai_attempt_count": ai_count,
            "manual_attempt_count": manual_count,
            "mode_exposure": (
                "BOTH"
                if ai_count and manual_count
                else "AI_ONLY"
                if ai_count
                else "MANUAL_ONLY"
            ),
            "first_mode": "AI" if ai_count else "MANUAL",
            "final_or_latest_mode": final_mode,
            "mode_transition_count": 1 if ai_count and manual_count else 0,
            "mode_changed": bool(ai_count and manual_count),
            "distinct_author_count": 2 if author_changed else 1,
            "author_changed": author_changed,
            "ai_error_attempt_count": int(has_ai_error),
            "has_ai_error": has_ai_error,
            "user_dropped_attempt_count": int(has_user_dropped),
            "has_user_dropped_attempt": has_user_dropped,
            "returned_result_ai_attempt_count": int(returned_result_ai),
            "has_returned_result_ai": returned_result_ai,
            "source_comparison_eligible": source_eligible,
            "source_size_comparison_eligible": source_eligible,
            "reported_source_comparison_eligible": source_eligible,
            "input_method_comparison_eligible": source_eligible,
            "source_signature_comparison_eligible": signature_eligible,
            "any_source_size_change": signature_changed,
            "any_reported_source_change": False,
            "any_input_method_change": False,
            "any_source_signature_change": signature_changed,
            "ai_feedback_record_count": int(feedback_recorded),
            "feedback_recorded_on_any_ai_attempt": feedback_recorded,
            "first_attempt_timestamp": pd.Timestamp("2026-01-01T09:00:00"),
            "latest_observed_attempt_timestamp": pd.Timestamp("2026-01-01T10:00:00"),
            "completed_timestamp": (
                pd.Timestamp("2026-01-01T10:00:00")
                if completion_state == "COMPLETED"
                else None
            ),
            "report_run_cutoff_timestamp": (
                pd.Timestamp("2026-01-02T10:00:00")
                if unresolved_minutes is not None
                else None
            ),
            "minutes_first_attempt_to_completion": completion_minutes,
            "minutes_first_attempt_to_last_observed_attempt": (unresolved_minutes),
            "minutes_latest_attempt_to_report_run_cutoff": (
                1_440.0 if unresolved_minutes is not None else None
            ),
            "minutes_first_attempt_to_report_run_cutoff": (
                1_440.0 + unresolved_minutes if unresolved_minutes is not None else None
            ),
        }
    )

    return row


def _contexts() -> pd.DataFrame:
    """Return three synthetic studies spanning all outcome groups."""
    return pd.DataFrame.from_records(
        [
            _retry_row(
                study_num="SYNTHETIC-A",
                pathway_category="REPEATED_AI_ONLY_TO_AI_COMPLETION",
                completion_state="COMPLETED",
                final_mode="AI",
                attempt_count=3,
                ai_count=3,
                manual_count=0,
                author_changed=True,
                has_ai_error=True,
                has_user_dropped=True,
                returned_result_ai=True,
                source_eligible=True,
                signature_eligible=True,
                signature_changed=True,
                feedback_recorded=True,
                completion_minutes=30.0,
            ),
            _retry_row(
                study_num="SYNTHETIC-B",
                pathway_category="AI_TO_MANUAL_COMPLETION",
                completion_state="COMPLETED",
                final_mode="MANUAL",
                attempt_count=2,
                ai_count=1,
                manual_count=1,
                returned_result_ai=True,
                feedback_recorded=False,
                completion_minutes=20.0,
            ),
            _retry_row(
                study_num="SYNTHETIC-C",
                pathway_category=("REPEATED_MANUAL_ONLY_NO_COMPLETION_OBSERVED"),
                completion_state="NO_COMPLETION_OBSERVED",
                final_mode="MANUAL",
                attempt_count=2,
                ai_count=0,
                manual_count=2,
                has_user_dropped=True,
                unresolved_minutes=45.0,
            ),
        ],
        columns=list(STUDY_RETRY_CONTEXT_COLUMNS),
    )


def test_pathway_summary_is_stable_exhaustive_and_identifier_free() -> None:
    """Publish every category exactly once without study-level fields."""
    summary = build_study_retry_pathway_summary(_contexts())

    assert tuple(summary.columns) == STUDY_RETRY_PATHWAY_SUMMARY_COLUMNS
    assert summary["pathway_category"].tolist() == list(RETRY_PATHWAY_CATEGORIES)
    assert summary["pathway_sequence"].tolist() == list(range(1, 14))
    assert len(summary) == 13
    assert FORBIDDEN_AGGREGATE_COLUMNS.isdisjoint(summary.columns)
    assert summary["study_count"].sum() == 3
    assert summary["population_study_count"].eq(3).all()
    assert summary["study_percentage"].sum() == pytest.approx(100.0)


def test_pathway_summary_counts_characteristics_and_distinct_timing() -> None:
    """Keep completed and unresolved timing measures separate."""
    summary = build_study_retry_pathway_summary(_contexts())
    completed = summary.loc[
        summary["pathway_category"].eq("REPEATED_AI_ONLY_TO_AI_COMPLETION")
    ].iloc[0]
    unresolved = summary.loc[
        summary["pathway_category"].eq("REPEATED_MANUAL_ONLY_NO_COMPLETION_OBSERVED")
    ].iloc[0]

    assert completed["study_count"] == 1
    assert completed["study_count_with_author_change"] == 1
    assert completed["study_count_with_ai_error"] == 1
    assert completed["source_comparison_eligible_study_count"] == 1
    assert completed["study_count_with_source_signature_change"] == 1
    assert completed["ai_exposed_study_count"] == 1
    assert completed["study_count_with_feedback_recorded"] == 1
    assert completed["median_minutes_first_to_completion"] == 30.0
    assert pd.isna(completed["median_minutes_first_to_last_observed_attempt"])

    assert unresolved["median_minutes_first_to_last_observed_attempt"] == 45.0
    assert unresolved["study_count_with_report_run_cutoff"] == 1
    assert unresolved["median_minutes_latest_attempt_to_report_run_cutoff"] == 1_440.0
    assert unresolved["median_minutes_first_attempt_to_report_run_cutoff"] == 1_485.0
    assert pd.isna(unresolved["median_minutes_first_to_completion"])
    assert "not follow-up time" in unresolved["timing_definition"]


def test_retry_characteristics_has_explicit_denominators() -> None:
    """Use group, source-eligible, and AI-exposed denominators explicitly."""
    summary = build_retry_characteristics_summary(_contexts())

    assert tuple(summary.columns) == RETRY_CHARACTERISTICS_SUMMARY_COLUMNS
    assert summary["study_outcome_group"].tolist() == [
        "COMPLETED_AI",
        "COMPLETED_MANUAL",
        "NO_COMPLETION_OBSERVED",
    ]
    assert FORBIDDEN_AGGREGATE_COLUMNS.isdisjoint(summary.columns)

    completed_ai = summary.loc[summary["study_outcome_group"].eq("COMPLETED_AI")].iloc[
        0
    ]
    completed_manual = summary.loc[
        summary["study_outcome_group"].eq("COMPLETED_MANUAL")
    ].iloc[0]
    unresolved = summary.loc[
        summary["study_outcome_group"].eq("NO_COMPLETION_OBSERVED")
    ].iloc[0]

    assert completed_ai["study_count"] == 1
    assert completed_ai["percentage_with_multiple_attempts"] == 100.0
    assert completed_ai["source_comparison_eligible_study_count"] == 1
    assert (
        completed_ai["percentage_with_source_signature_change_among_eligible"] == 100.0
    )
    assert completed_ai["ai_exposed_study_count"] == 1
    assert completed_ai["percentage_with_feedback_recorded_among_ai_exposed"] == 100.0

    assert completed_manual["ai_exposed_study_count"] == 1
    assert completed_manual["percentage_with_feedback_recorded_among_ai_exposed"] == 0.0
    assert pd.isna(
        completed_manual["percentage_with_source_signature_change_among_eligible"]
    )

    assert unresolved["study_count"] == 1
    assert unresolved["ai_exposed_study_count"] == 0
    assert pd.isna(unresolved["percentage_with_feedback_recorded_among_ai_exposed"])
    assert unresolved["median_minutes_first_to_last_observed_attempt"] == 45.0
    assert unresolved["study_count_with_report_run_cutoff"] == 1
    assert unresolved["median_minutes_latest_attempt_to_report_run_cutoff"] == 1_440.0
    assert unresolved["median_minutes_first_attempt_to_report_run_cutoff"] == 1_485.0
    assert "final unresolved outcome" in unresolved["interpretation_note"]


def test_empty_retry_aggregates_have_stable_rows_and_missing_percentages() -> None:
    """Represent zero denominators as missing, never zero percentages."""
    empty = pd.DataFrame(columns=list(STUDY_RETRY_CONTEXT_COLUMNS))

    pathways = build_study_retry_pathway_summary(empty)
    characteristics = build_retry_characteristics_summary(empty)

    assert len(pathways) == 13
    assert pathways["study_count"].eq(0).all()
    assert pathways["population_study_count"].eq(0).all()
    assert pathways["study_percentage"].isna().all()
    assert pathways["median_attempt_count"].isna().all()

    assert len(characteristics) == 3
    assert characteristics["study_count"].eq(0).all()
    percentage_columns = [
        column for column in characteristics.columns if column.startswith("percentage_")
    ]
    assert characteristics[percentage_columns].isna().all().all()


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("study_num", None, "one non-null row per study"),
        ("pathway_category", "UNKNOWN", "invalid pathway categories"),
        (
            "completion_state",
            "NO_COMPLETION_OBSERVED",
            "contradicts completion state",
        ),
        (
            "final_or_latest_mode",
            "MANUAL",
            "contradicts final/latest mode",
        ),
    ],
)
def test_retry_aggregates_fail_fast_on_invalid_internal_context(
    column: str,
    value: object,
    message: str,
) -> None:
    """Reject contradictory internal study-level rows."""
    studies = _contexts()
    replacement = studies[column].astype("object").copy()
    replacement.iloc[0] = value
    studies = studies.assign(**{column: replacement})

    with pytest.raises(ExplorationValidationError, match=message):
        build_study_retry_pathway_summary(studies)


def test_retry_aggregates_reject_invalid_completion_state() -> None:
    """Reject completion-state values outside the stable contract."""
    studies = _contexts()
    studies["completion_state"] = studies["completion_state"].astype("object")
    studies.at[0, "completion_state"] = "UNKNOWN"

    with pytest.raises(
        ExplorationValidationError,
        match="invalid completion states",
    ):
        build_retry_characteristics_summary(studies)


def test_retry_card_summary_uses_true_study_level_median() -> None:
    """Compute card medians from studies rather than pathway medians."""
    studies = _contexts()
    additional = pd.DataFrame.from_records(
        [
            _retry_row(
                study_num="SYNTHETIC-D",
                pathway_category="REPEATED_AI_ONLY_TO_AI_COMPLETION",
                completion_state="COMPLETED",
                final_mode="AI",
                attempt_count=9,
                ai_count=9,
                manual_count=0,
                completion_minutes=90.0,
            ),
            _retry_row(
                study_num="SYNTHETIC-E",
                pathway_category="AI_TO_MANUAL_COMPLETION",
                completion_state="COMPLETED",
                final_mode="MANUAL",
                attempt_count=4,
                ai_count=2,
                manual_count=2,
                completion_minutes=40.0,
            ),
        ],
        columns=list(STUDY_RETRY_CONTEXT_COLUMNS),
    )
    studies = pd.concat([studies, additional], ignore_index=True)

    cards = build_retry_card_summary(studies)
    repeated_completed = cards.loc[
        cards["retry_card_group"].eq("MULTIPLE_ATTEMPTS_COMPLETED")
    ].iloc[0]

    assert repeated_completed["study_count"] == 4
    assert repeated_completed["median_attempt_count"] == 3.5
    assert repeated_completed["ai_only_study_count"] == 2
    assert repeated_completed["both_modes_study_count"] == 2
    assert repeated_completed["manual_only_study_count"] == 0


def test_completed_retry_aggregate_cutoff_values_are_missing() -> None:
    """Keep unresolved cutoff measures out of completed rows."""
    summary = build_retry_characteristics_summary(_contexts())
    completed = summary.loc[
        summary["study_outcome_group"].isin(["COMPLETED_AI", "COMPLETED_MANUAL"])
    ]

    assert completed["study_count_with_report_run_cutoff"].eq(0).all()
    assert completed["median_minutes_latest_attempt_to_report_run_cutoff"].isna().all()
    assert completed["median_minutes_first_attempt_to_report_run_cutoff"].isna().all()


def test_empty_retry_cutoff_aggregates_are_missing() -> None:
    """Use missing medians and zero contributing counts for empty input."""
    empty = pd.DataFrame(columns=list(STUDY_RETRY_CONTEXT_COLUMNS))

    pathways = build_study_retry_pathway_summary(empty)
    characteristics = build_retry_characteristics_summary(empty)

    assert pathways["study_count_with_report_run_cutoff"].eq(0).all()
    assert pathways["median_minutes_latest_attempt_to_report_run_cutoff"].isna().all()
    assert characteristics["study_count_with_report_run_cutoff"].eq(0).all()
    assert (
        characteristics["median_minutes_first_attempt_to_report_run_cutoff"]
        .isna()
        .all()
    )
