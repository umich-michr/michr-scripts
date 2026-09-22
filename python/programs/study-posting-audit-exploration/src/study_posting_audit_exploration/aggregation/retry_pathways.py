"""Identifier-free aggregates for observed study retry pathways."""

from __future__ import annotations

from collections.abc import Callable
from typing import Final

import pandas as pd

from study_posting_audit_exploration.derivation.retry_pathways import (
    RETRY_PATHWAY_CATEGORIES,
    STUDY_RETRY_CONTEXT_COLUMNS,
)
from study_posting_audit_exploration.errors import ExplorationValidationError

COMPLETED: Final = "COMPLETED"
NO_COMPLETION_OBSERVED: Final = "NO_COMPLETION_OBSERVED"
AI: Final = "AI"
MANUAL: Final = "MANUAL"

STUDY_RETRY_PATHWAY_SUMMARY_COLUMNS: tuple[str, ...] = (
    "pathway_category",
    "pathway_sequence",
    "completion_state",
    "final_or_latest_mode",
    "study_count",
    "population_study_count",
    "study_percentage",
    "median_attempt_count",
    "percentile_75_attempt_count",
    "study_count_with_mode_change",
    "study_count_with_author_change",
    "study_count_with_ai_error",
    "study_count_with_user_dropped_attempt",
    "study_count_with_returned_result_ai",
    "source_comparison_eligible_study_count",
    "study_count_with_source_size_change",
    "study_count_with_reported_source_change",
    "study_count_with_input_method_change",
    "study_count_with_source_signature_change",
    "ai_exposed_study_count",
    "study_count_with_feedback_recorded",
    "study_count_with_completed_timing",
    "median_minutes_first_to_completion",
    "study_count_with_unresolved_observed_span",
    "median_minutes_first_to_last_observed_attempt",
    "timing_definition",
    "interpretation_note",
)

RETRY_CARD_SUMMARY_COLUMNS: tuple[str, ...] = (
    "retry_card_group",
    "study_count",
    "population_study_count",
    "study_percentage",
    "median_attempt_count",
    "ai_only_study_count",
    "manual_only_study_count",
    "both_modes_study_count",
)

RETRY_CHARACTERISTICS_SUMMARY_COLUMNS: tuple[str, ...] = (
    "study_outcome_group",
    "study_count",
    "median_attempt_count",
    "multiple_attempt_study_count",
    "percentage_with_multiple_attempts",
    "both_modes_study_count",
    "percentage_with_both_modes",
    "author_change_study_count",
    "percentage_with_author_change",
    "ai_error_study_count",
    "percentage_with_ai_error",
    "user_dropped_study_count",
    "percentage_with_user_dropped_attempt",
    "returned_result_ai_study_count",
    "percentage_with_returned_result_ai",
    "source_comparison_eligible_study_count",
    "source_signature_change_study_count",
    "percentage_with_source_signature_change_among_eligible",
    "ai_exposed_study_count",
    "feedback_recorded_study_count",
    "percentage_with_feedback_recorded_among_ai_exposed",
    "study_count_with_completed_timing",
    "median_minutes_first_to_completion",
    "study_count_with_unresolved_observed_span",
    "median_minutes_first_to_last_observed_attempt",
    "timing_definition",
    "interpretation_note",
)

OUTCOME_GROUP_ORDER: tuple[str, ...] = (
    "COMPLETED_AI",
    "COMPLETED_MANUAL",
    NO_COMPLETION_OBSERVED,
)

_PATHWAY_METADATA: dict[str, tuple[str, str]] = {
    "SINGLE_ATTEMPT_AI_COMPLETION": (COMPLETED, AI),
    "SINGLE_ATTEMPT_MANUAL_COMPLETION": (COMPLETED, MANUAL),
    "REPEATED_AI_ONLY_TO_AI_COMPLETION": (COMPLETED, AI),
    "REPEATED_MANUAL_ONLY_TO_MANUAL_COMPLETION": (COMPLETED, MANUAL),
    "AI_TO_MANUAL_COMPLETION": (COMPLETED, MANUAL),
    "MANUAL_TO_AI_COMPLETION": (COMPLETED, AI),
    "MIXED_OR_ALTERNATING_TO_AI_COMPLETION": (COMPLETED, AI),
    "MIXED_OR_ALTERNATING_TO_MANUAL_COMPLETION": (COMPLETED, MANUAL),
    "SINGLE_ATTEMPT_AI_NO_COMPLETION_OBSERVED": (
        NO_COMPLETION_OBSERVED,
        AI,
    ),
    "SINGLE_ATTEMPT_MANUAL_NO_COMPLETION_OBSERVED": (
        NO_COMPLETION_OBSERVED,
        MANUAL,
    ),
    "REPEATED_AI_ONLY_NO_COMPLETION_OBSERVED": (
        NO_COMPLETION_OBSERVED,
        AI,
    ),
    "REPEATED_MANUAL_ONLY_NO_COMPLETION_OBSERVED": (
        NO_COMPLETION_OBSERVED,
        MANUAL,
    ),
    "MIXED_MODES_NO_COMPLETION_OBSERVED": (
        NO_COMPLETION_OBSERVED,
        "MIXED",
    ),
}

_COMPLETED_TIMING_DEFINITION = (
    "First recorded attempt start to completed attempt end, in minutes."
)
_UNRESOLVED_TIMING_DEFINITION = (
    "First recorded attempt start to latest observed attempt start, in minutes; "
    "this is not follow-up time or a final outcome."
)
_MIXED_TIMING_DEFINITION = (
    "Completed groups use first attempt to completion; the no-completion-observed "
    "group uses first attempt to latest observed attempt."
)
_INTERPRETATION_NOTE = (
    "Observed retry patterns are descriptive and may support qualitative follow-up; "
    "they do not establish motivation, satisfaction, causality, abandonment, or a "
    "final unresolved outcome."
)


def _require_retry_context(studies: pd.DataFrame) -> None:
    """Require the complete internal study retry contract."""
    missing = tuple(
        column
        for column in STUDY_RETRY_CONTEXT_COLUMNS
        if column not in studies.columns
    )

    if missing:
        raise ExplorationValidationError(
            f"study retry context lacks required aggregate columns: {missing!r}"
        )

    if studies["study_num"].isna().any() or studies["study_num"].duplicated().any():
        raise ExplorationValidationError(
            "study retry context requires one non-null row per study"
        )

    invalid_categories = set(studies["pathway_category"]).difference(
        RETRY_PATHWAY_CATEGORIES
    )
    if invalid_categories:
        raise ExplorationValidationError(
            f"study retry context has invalid pathway categories: "
            f"{sorted(invalid_categories)!r}"
        )

    invalid_states = set(studies["completion_state"]).difference(
        {COMPLETED, NO_COMPLETION_OBSERVED}
    )
    if invalid_states:
        raise ExplorationValidationError(
            f"study retry context has invalid completion states: "
            f"{sorted(invalid_states)!r}"
        )

    for category, group in studies.groupby(
        "pathway_category",
        sort=False,
        dropna=False,
    ):
        expected_state, expected_mode = _PATHWAY_METADATA[str(category)]

        if not group["completion_state"].eq(expected_state).all():
            raise ExplorationValidationError(
                f"pathway category {category!r} contradicts completion state"
            )

        if (
            expected_mode != "MIXED"
            and not group["final_or_latest_mode"].eq(expected_mode).all()
        ):
            raise ExplorationValidationError(
                f"pathway category {category!r} contradicts final/latest mode"
            )


def _percentage(
    numerator: int,
    denominator: int,
) -> float | None:
    """Return percentage or missing for a zero denominator."""
    if denominator == 0:
        return None

    return 100.0 * numerator / denominator


def _count_true(
    rows: pd.DataFrame,
    column: str,
) -> int:
    """Return the number of rows with an explicitly true flag."""
    return int(rows[column].eq(True).sum())


def _median(
    rows: pd.DataFrame,
    column: str,
) -> float | None:
    """Return a nullable numeric median."""
    values = pd.to_numeric(rows[column], errors="coerce").dropna()

    if values.empty:
        return None

    return float(values.median())


def _percentile_75(
    rows: pd.DataFrame,
    column: str,
) -> float | None:
    """Return a nullable 75th percentile."""
    values = pd.to_numeric(rows[column], errors="coerce").dropna()

    if values.empty:
        return None

    return float(values.quantile(0.75))


def _pathway_row(
    studies: pd.DataFrame,
    *,
    category: str,
    sequence: int,
    population_count: int,
) -> dict[str, object]:
    """Return one stable identifier-free pathway row."""
    rows = studies.loc[studies["pathway_category"].eq(category)]
    completion_state, final_or_latest_mode = _PATHWAY_METADATA[category]
    completed_timing_count = int(
        rows["minutes_first_attempt_to_completion"].notna().sum()
    )
    unresolved_span_count = int(
        rows["minutes_first_attempt_to_last_observed_attempt"].notna().sum()
    )

    timing_definition = (
        _COMPLETED_TIMING_DEFINITION
        if completion_state == COMPLETED
        else _UNRESOLVED_TIMING_DEFINITION
    )

    return {
        "pathway_category": category,
        "pathway_sequence": sequence,
        "completion_state": completion_state,
        "final_or_latest_mode": final_or_latest_mode,
        "study_count": len(rows),
        "population_study_count": population_count,
        "study_percentage": _percentage(len(rows), population_count),
        "median_attempt_count": _median(rows, "all_attempt_count"),
        "percentile_75_attempt_count": _percentile_75(
            rows,
            "all_attempt_count",
        ),
        "study_count_with_mode_change": _count_true(rows, "mode_changed"),
        "study_count_with_author_change": _count_true(rows, "author_changed"),
        "study_count_with_ai_error": _count_true(rows, "has_ai_error"),
        "study_count_with_user_dropped_attempt": _count_true(
            rows,
            "has_user_dropped_attempt",
        ),
        "study_count_with_returned_result_ai": _count_true(
            rows,
            "has_returned_result_ai",
        ),
        "source_comparison_eligible_study_count": _count_true(
            rows,
            "source_comparison_eligible",
        ),
        "study_count_with_source_size_change": _count_true(
            rows,
            "any_source_size_change",
        ),
        "study_count_with_reported_source_change": _count_true(
            rows,
            "any_reported_source_change",
        ),
        "study_count_with_input_method_change": _count_true(
            rows,
            "any_input_method_change",
        ),
        "study_count_with_source_signature_change": _count_true(
            rows,
            "any_source_signature_change",
        ),
        "ai_exposed_study_count": int(rows["ai_attempt_count"].gt(0).sum()),
        "study_count_with_feedback_recorded": _count_true(
            rows,
            "feedback_recorded_on_any_ai_attempt",
        ),
        "study_count_with_completed_timing": completed_timing_count,
        "median_minutes_first_to_completion": _median(
            rows,
            "minutes_first_attempt_to_completion",
        ),
        "study_count_with_unresolved_observed_span": unresolved_span_count,
        "median_minutes_first_to_last_observed_attempt": _median(
            rows,
            "minutes_first_attempt_to_last_observed_attempt",
        ),
        "timing_definition": timing_definition,
        "interpretation_note": _INTERPRETATION_NOTE,
    }


_RETRY_CARD_GROUPS: tuple[tuple[str, str, str], ...] = (
    ("SINGLE_ATTEMPT_COMPLETED", COMPLETED, "SINGLE_ATTEMPT"),
    ("MULTIPLE_ATTEMPTS_COMPLETED", COMPLETED, "MULTIPLE_ATTEMPTS"),
    (
        "SINGLE_ATTEMPT_NO_COMPLETION_OBSERVED",
        NO_COMPLETION_OBSERVED,
        "SINGLE_ATTEMPT",
    ),
    (
        "MULTIPLE_ATTEMPTS_NO_COMPLETION_OBSERVED",
        NO_COMPLETION_OBSERVED,
        "MULTIPLE_ATTEMPTS",
    ),
)


def build_retry_card_summary(
    studies: pd.DataFrame,
) -> pd.DataFrame:
    """Return four identifier-free card rows with study-level medians."""
    _require_retry_context(studies)
    population_count = len(studies)
    rows: list[dict[str, object]] = []

    for group_name, completion_state, attempt_frequency in _RETRY_CARD_GROUPS:
        group = studies.loc[
            studies["completion_state"].eq(completion_state)
            & studies["attempt_frequency"].eq(attempt_frequency)
        ]
        study_count = len(group)
        rows.append(
            {
                "retry_card_group": group_name,
                "study_count": study_count,
                "population_study_count": population_count,
                "study_percentage": _percentage(
                    study_count,
                    population_count,
                ),
                "median_attempt_count": _median(
                    group,
                    "all_attempt_count",
                ),
                "ai_only_study_count": int(group["mode_exposure"].eq("AI_ONLY").sum()),
                "manual_only_study_count": int(
                    group["mode_exposure"].eq("MANUAL_ONLY").sum()
                ),
                "both_modes_study_count": int(group["mode_exposure"].eq("BOTH").sum()),
            }
        )

    return pd.DataFrame.from_records(
        rows,
        columns=list(RETRY_CARD_SUMMARY_COLUMNS),
    )


def build_study_retry_pathway_summary(
    studies: pd.DataFrame,
) -> pd.DataFrame:
    """Return all retry pathways in stable order, including zero-count rows."""
    _require_retry_context(studies)
    population_count = len(studies)
    rows = [
        _pathway_row(
            studies,
            category=category,
            sequence=sequence,
            population_count=population_count,
        )
        for sequence, category in enumerate(
            RETRY_PATHWAY_CATEGORIES,
            start=1,
        )
    ]

    return pd.DataFrame.from_records(
        rows,
        columns=list(STUDY_RETRY_PATHWAY_SUMMARY_COLUMNS),
    )


def _outcome_mask(
    studies: pd.DataFrame,
    outcome_group: str,
) -> pd.Series:
    """Return the study population for one stable outcome group."""
    if outcome_group == "COMPLETED_AI":
        return studies["completion_state"].eq(COMPLETED) & studies[
            "final_or_latest_mode"
        ].eq(AI)

    if outcome_group == "COMPLETED_MANUAL":
        return studies["completion_state"].eq(COMPLETED) & studies[
            "final_or_latest_mode"
        ].eq(MANUAL)

    return studies["completion_state"].eq(NO_COMPLETION_OBSERVED)


def _characteristic(
    rows: pd.DataFrame,
    *,
    predicate: Callable[[pd.DataFrame], pd.Series],
) -> tuple[int, float | None]:
    """Return count and percentage among all studies in a group."""
    count = int(predicate(rows).sum())

    return count, _percentage(count, len(rows))


def _characteristics_row(
    studies: pd.DataFrame,
    *,
    outcome_group: str,
) -> dict[str, object]:
    """Return one identifier-free outcome-group row."""
    rows = studies.loc[_outcome_mask(studies, outcome_group)]
    multiple_count, multiple_percentage = _characteristic(
        rows,
        predicate=lambda frame: frame["all_attempt_count"].gt(1),
    )
    both_count, both_percentage = _characteristic(
        rows,
        predicate=lambda frame: frame["mode_exposure"].eq("BOTH"),
    )
    author_count, author_percentage = _characteristic(
        rows,
        predicate=lambda frame: frame["author_changed"].eq(True),
    )
    error_count, error_percentage = _characteristic(
        rows,
        predicate=lambda frame: frame["has_ai_error"].eq(True),
    )
    dropped_count, dropped_percentage = _characteristic(
        rows,
        predicate=lambda frame: frame["has_user_dropped_attempt"].eq(True),
    )
    returned_count, returned_percentage = _characteristic(
        rows,
        predicate=lambda frame: frame["has_returned_result_ai"].eq(True),
    )
    eligible = rows.loc[rows["source_signature_comparison_eligible"].eq(True)]
    signature_change_count = _count_true(
        eligible,
        "any_source_signature_change",
    )
    ai_exposed = rows.loc[rows["ai_attempt_count"].gt(0)]
    feedback_count = _count_true(
        ai_exposed,
        "feedback_recorded_on_any_ai_attempt",
    )
    completed_timing_count = int(
        rows["minutes_first_attempt_to_completion"].notna().sum()
    )
    unresolved_span_count = int(
        rows["minutes_first_attempt_to_last_observed_attempt"].notna().sum()
    )

    timing_definition = (
        _UNRESOLVED_TIMING_DEFINITION
        if outcome_group == NO_COMPLETION_OBSERVED
        else _COMPLETED_TIMING_DEFINITION
    )

    return {
        "study_outcome_group": outcome_group,
        "study_count": len(rows),
        "median_attempt_count": _median(rows, "all_attempt_count"),
        "multiple_attempt_study_count": multiple_count,
        "percentage_with_multiple_attempts": multiple_percentage,
        "both_modes_study_count": both_count,
        "percentage_with_both_modes": both_percentage,
        "author_change_study_count": author_count,
        "percentage_with_author_change": author_percentage,
        "ai_error_study_count": error_count,
        "percentage_with_ai_error": error_percentage,
        "user_dropped_study_count": dropped_count,
        "percentage_with_user_dropped_attempt": dropped_percentage,
        "returned_result_ai_study_count": returned_count,
        "percentage_with_returned_result_ai": returned_percentage,
        "source_comparison_eligible_study_count": len(eligible),
        "source_signature_change_study_count": signature_change_count,
        "percentage_with_source_signature_change_among_eligible": _percentage(
            signature_change_count,
            len(eligible),
        ),
        "ai_exposed_study_count": len(ai_exposed),
        "feedback_recorded_study_count": feedback_count,
        "percentage_with_feedback_recorded_among_ai_exposed": _percentage(
            feedback_count,
            len(ai_exposed),
        ),
        "study_count_with_completed_timing": completed_timing_count,
        "median_minutes_first_to_completion": _median(
            rows,
            "minutes_first_attempt_to_completion",
        ),
        "study_count_with_unresolved_observed_span": unresolved_span_count,
        "median_minutes_first_to_last_observed_attempt": _median(
            rows,
            "minutes_first_attempt_to_last_observed_attempt",
        ),
        "timing_definition": timing_definition,
        "interpretation_note": _INTERPRETATION_NOTE,
    }


def build_retry_characteristics_summary(
    studies: pd.DataFrame,
) -> pd.DataFrame:
    """Return stable retry characteristics for three observed outcome groups."""
    _require_retry_context(studies)
    rows = [
        _characteristics_row(
            studies,
            outcome_group=outcome_group,
        )
        for outcome_group in OUTCOME_GROUP_ORDER
    ]

    return pd.DataFrame.from_records(
        rows,
        columns=list(RETRY_CHARACTERISTICS_SUMMARY_COLUMNS),
    )
