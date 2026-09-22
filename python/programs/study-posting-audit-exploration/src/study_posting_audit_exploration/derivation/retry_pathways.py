"""Derive one-row-per-study retry contexts from validated histories."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from itertools import pairwise
from typing import Final, cast

import pandas as pd

from study_posting_audit_exploration.errors import ExplorationValidationError

AI: Final = "AI"
MANUAL: Final = "MANUAL"
COMPLETE: Final = "COMPLETE"
AI_ERROR_RESULTS: Final = frozenset(
    {
        "AI_ERROR",
        "AI_ERROR_WITHOUT_STACK_TRACE",
    }
)
CHANGED: Final = "CHANGED"
COMPARABLE_STATES: Final = frozenset({"SAME", CHANGED})
MINIMUM_ALTERNATING_TRANSITION_COUNT: Final = 2

RETRY_PATHWAY_CATEGORIES: tuple[str, ...] = (
    "SINGLE_ATTEMPT_AI_COMPLETION",
    "SINGLE_ATTEMPT_MANUAL_COMPLETION",
    "REPEATED_AI_ONLY_TO_AI_COMPLETION",
    "REPEATED_MANUAL_ONLY_TO_MANUAL_COMPLETION",
    "AI_TO_MANUAL_COMPLETION",
    "MANUAL_TO_AI_COMPLETION",
    "MIXED_OR_ALTERNATING_TO_AI_COMPLETION",
    "MIXED_OR_ALTERNATING_TO_MANUAL_COMPLETION",
    "SINGLE_ATTEMPT_AI_NO_COMPLETION_OBSERVED",
    "SINGLE_ATTEMPT_MANUAL_NO_COMPLETION_OBSERVED",
    "REPEATED_AI_ONLY_NO_COMPLETION_OBSERVED",
    "REPEATED_MANUAL_ONLY_NO_COMPLETION_OBSERVED",
    "MIXED_MODES_NO_COMPLETION_OBSERVED",
)

STUDY_RETRY_CONTEXT_COLUMNS: tuple[str, ...] = (
    "study_num",
    "pathway_category",
    "completion_state",
    "attempt_frequency",
    "all_attempt_count",
    "ai_attempt_count",
    "manual_attempt_count",
    "mode_exposure",
    "first_mode",
    "final_or_latest_mode",
    "mode_transition_count",
    "mode_changed",
    "distinct_author_count",
    "author_changed",
    "ai_error_attempt_count",
    "has_ai_error",
    "user_dropped_attempt_count",
    "has_user_dropped_attempt",
    "returned_result_ai_attempt_count",
    "has_returned_result_ai",
    "source_comparison_eligible",
    "source_size_comparison_eligible",
    "reported_source_comparison_eligible",
    "input_method_comparison_eligible",
    "source_signature_comparison_eligible",
    "any_source_size_change",
    "any_reported_source_change",
    "any_input_method_change",
    "any_source_signature_change",
    "ai_feedback_record_count",
    "feedback_recorded_on_any_ai_attempt",
    "first_attempt_timestamp",
    "latest_observed_attempt_timestamp",
    "completed_timestamp",
    "report_run_cutoff_timestamp",
    "minutes_first_attempt_to_completion",
    "minutes_first_attempt_to_last_observed_attempt",
    "minutes_latest_attempt_to_report_run_cutoff",
    "minutes_first_attempt_to_report_run_cutoff",
)


@dataclass(frozen=True, slots=True)
class StudyRetryTables:
    """Internal retry derivations with an explicit one-row-per-study grain."""

    study_retry_context: pd.DataFrame


def _is_missing(value: object) -> bool:
    """Return whether one trusted scalar is missing."""
    if value is None or value is pd.NA or value is pd.NaT:
        return True

    if isinstance(value, float):
        return bool(pd.isna(value))

    return False


def _timestamp(value: object) -> pd.Timestamp | None:
    """Return one nullable timestamp."""
    if _is_missing(value):
        return None

    return pd.Timestamp(
        cast("str | int | float | date | datetime | pd.Timestamp", value)
    )


def _require_columns(
    frame: pd.DataFrame,
    required: tuple[str, ...],
    *,
    frame_name: str,
) -> None:
    """Require columns consumed from one trusted derivation."""
    missing = tuple(column for column in required if column not in frame.columns)

    if missing:
        raise ExplorationValidationError(
            f"{frame_name} lacks required retry-pathway columns: {missing!r}"
        )


def _mode_transition_count(modes: tuple[str, ...]) -> int:
    """Return adjacent mode changes in one nonempty ordered sequence."""
    return sum(previous != current for previous, current in pairwise(modes))


def _single_attempt_category(
    *,
    mode: str,
    completed: bool,
) -> str:
    """Return one single-attempt pathway category."""
    completion_suffix = "COMPLETION" if completed else "NO_COMPLETION_OBSERVED"

    return f"SINGLE_ATTEMPT_{mode}_{completion_suffix}"


def _unresolved_repeated_category(
    modes: tuple[str, ...],
) -> str:
    """Return one repeated no-completion-observed pathway category."""
    distinct_modes = frozenset(modes)

    if distinct_modes == {AI}:
        return "REPEATED_AI_ONLY_NO_COMPLETION_OBSERVED"

    if distinct_modes == {MANUAL}:
        return "REPEATED_MANUAL_ONLY_NO_COMPLETION_OBSERVED"

    return "MIXED_MODES_NO_COMPLETION_OBSERVED"


def _completed_repeated_category(
    modes: tuple[str, ...],
) -> str:
    """Return one repeated completed pathway category."""
    distinct_modes = frozenset(modes)

    if distinct_modes == {AI}:
        return "REPEATED_AI_ONLY_TO_AI_COMPLETION"

    if distinct_modes == {MANUAL}:
        return "REPEATED_MANUAL_ONLY_TO_MANUAL_COMPLETION"

    transition_count = _mode_transition_count(modes)

    single_transition_categories = {
        (AI, MANUAL): "AI_TO_MANUAL_COMPLETION",
        (MANUAL, AI): "MANUAL_TO_AI_COMPLETION",
    }
    if transition_count == 1:
        return single_transition_categories[(modes[0], modes[-1])]

    if transition_count < MINIMUM_ALTERNATING_TRANSITION_COUNT:
        raise ExplorationValidationError(
            f"retry-pathway classification could not classify modes: {modes!r}"
        )

    return (
        "MIXED_OR_ALTERNATING_TO_AI_COMPLETION"
        if modes[-1] == AI
        else "MIXED_OR_ALTERNATING_TO_MANUAL_COMPLETION"
    )


def classify_retry_pathway(
    modes: tuple[str, ...],
    *,
    completed: bool,
) -> str:
    """Return one deterministic, exhaustive retry-pathway category."""
    if not modes:
        raise ExplorationValidationError(
            "retry-pathway classification requires at least one attempt mode"
        )

    invalid = tuple(mode for mode in modes if mode not in {AI, MANUAL})

    if invalid:
        raise ExplorationValidationError(
            f"retry-pathway classification found unsupported modes: {invalid!r}"
        )

    if len(modes) == 1:
        return _single_attempt_category(
            mode=modes[0],
            completed=completed,
        )

    if not completed:
        return _unresolved_repeated_category(modes)

    return _completed_repeated_category(modes)


def _ordered_applicable_attempts(group: pd.DataFrame) -> pd.DataFrame:
    """Return captured attempts through completion, or all unresolved attempts."""
    ordered = group.sort_values(
        by=["attempt_start_timestamp", "audit_record_id"],
        kind="stable",
        na_position="last",
    ).reset_index(drop=True)
    completed_positions = ordered.index[ordered["attempt_result"].eq(COMPLETE)].tolist()

    if len(completed_positions) > 1:
        raise ExplorationValidationError(
            "retry-pathway derivation requires at most one complete attempt per study"
        )

    if not completed_positions:
        return ordered

    return ordered.iloc[: completed_positions[0] + 1].reset_index(drop=True)


def _comparison_summary(
    transitions: pd.DataFrame,
    *,
    column: str,
) -> tuple[bool, bool]:
    """Return comparison eligibility and whether any eligible pair changed."""
    comparable = transitions[column].isin(COMPARABLE_STATES)

    return bool(comparable.any()), bool(
        transitions.loc[comparable, column].eq(CHANGED).any()
    )


def _feedback_counts_by_study(
    ai_feedback_records: pd.DataFrame | None,
) -> dict[str, int]:
    """Return study-keyed AI feedback record counts without retaining text."""
    if ai_feedback_records is None:
        return {}

    _require_columns(
        ai_feedback_records,
        ("study_num", "audit_record_id"),
        frame_name="ai_feedback_records",
    )

    if "feedback_recorded" in ai_feedback_records.columns:
        recorded = ai_feedback_records.loc[
            ai_feedback_records["feedback_recorded"].eq(True)
        ]
    else:
        recorded = ai_feedback_records

    if recorded.empty:
        return {}

    if recorded["study_num"].isna().any():
        raise ExplorationValidationError(
            "ai_feedback_records requires non-null study numbers"
        )

    if recorded["audit_record_id"].isna().any():
        raise ExplorationValidationError(
            "ai_feedback_records requires non-null audit IDs"
        )

    return {
        str(study_num): int(group["audit_record_id"].nunique())
        for study_num, group in recorded.groupby(
            "study_num",
            sort=False,
            dropna=False,
        )
    }


def _study_row(
    group: pd.DataFrame,
    *,
    successful_ai_generations: pd.DataFrame,
    successful_ai_transitions: pd.DataFrame,
    feedback_count: int,
    report_run_cutoff_timestamp: pd.Timestamp | None,
) -> dict[str, object]:
    """Return one internal retry-context row."""
    applicable = _ordered_applicable_attempts(group)
    study_num = str(applicable.iloc[0]["study_num"])
    completed = bool(applicable["attempt_result"].eq(COMPLETE).any())
    modes = tuple(str(value) for value in applicable["attempt_authoring_mode"])
    transition_count = _mode_transition_count(modes)

    applicable_ids = frozenset(
        int(value) for value in applicable["audit_record_id"].tolist()
    )
    returned_result = successful_ai_generations.loc[
        successful_ai_generations["study_num"].astype("string").eq(study_num)
        & successful_ai_generations["audit_record_id"].isin(applicable_ids)
    ]
    returned_ids = frozenset(
        int(value) for value in returned_result["audit_record_id"].tolist()
    )
    transitions = successful_ai_transitions.loc[
        successful_ai_transitions["study_num"].astype("string").eq(study_num)
        & successful_ai_transitions["previous_audit_record_id"].isin(returned_ids)
        & successful_ai_transitions["current_audit_record_id"].isin(returned_ids)
    ]

    size_eligible, size_changed = _comparison_summary(
        transitions,
        column="source_size_comparison",
    )
    reported_eligible, reported_changed = _comparison_summary(
        transitions,
        column="reported_source_comparison",
    )
    input_eligible, input_changed = _comparison_summary(
        transitions,
        column="input_method_comparison",
    )
    signature_eligible, signature_changed = _comparison_summary(
        transitions,
        column="source_signature_comparison",
    )

    first_timestamp = _timestamp(applicable.iloc[0]["attempt_start_timestamp"])
    latest_timestamp = _timestamp(applicable.iloc[-1]["attempt_start_timestamp"])
    completed_rows = applicable.loc[applicable["attempt_result"].eq(COMPLETE)]
    completed_timestamp = (
        None
        if completed_rows.empty
        else _timestamp(completed_rows.iloc[0]["attempt_end_timestamp"])
    )

    if completed and completed_timestamp is None:
        raise ExplorationValidationError(
            "retry-pathway completion timing requires completed attempt end time"
        )

    completed_start = (
        None
        if completed_rows.empty
        else _timestamp(completed_rows.iloc[0]["attempt_start_timestamp"])
    )

    if (
        completed_timestamp is not None
        and completed_start is not None
        and completed_timestamp < completed_start
    ):
        raise ExplorationValidationError(
            "retry-pathway completion end time must not precede attempt start"
        )

    completion_minutes = (
        None
        if first_timestamp is None or completed_timestamp is None
        else (completed_timestamp - first_timestamp).total_seconds() / 60.0
    )
    observed_minutes = (
        None
        if completed or first_timestamp is None or latest_timestamp is None
        else (latest_timestamp - first_timestamp).total_seconds() / 60.0
    )
    unresolved_cutoff = None if completed else report_run_cutoff_timestamp

    if (
        unresolved_cutoff is not None
        and latest_timestamp is not None
        and unresolved_cutoff < latest_timestamp
    ):
        raise ExplorationValidationError(
            "report-run cutoff must not precede the latest observed attempt"
        )

    latest_to_cutoff_minutes = (
        None
        if unresolved_cutoff is None or latest_timestamp is None
        else (unresolved_cutoff - latest_timestamp).total_seconds() / 60.0
    )
    first_to_cutoff_minutes = (
        None
        if unresolved_cutoff is None or first_timestamp is None
        else (unresolved_cutoff - first_timestamp).total_seconds() / 60.0
    )

    ai_count = int(sum(mode == AI for mode in modes))
    manual_count = int(sum(mode == MANUAL for mode in modes))
    author_count = int(applicable["attempt_author_user_name"].nunique())

    if ai_count and manual_count:
        mode_exposure = "BOTH"
    elif ai_count:
        mode_exposure = "AI_ONLY"
    else:
        mode_exposure = "MANUAL_ONLY"

    ai_error_count = int(applicable["attempt_result"].isin(AI_ERROR_RESULTS).sum())
    user_dropped_count = int(applicable["attempt_result"].eq("USER_DROPPED").sum())

    return {
        "study_num": study_num,
        "pathway_category": classify_retry_pathway(
            modes,
            completed=completed,
        ),
        "completion_state": ("COMPLETED" if completed else "NO_COMPLETION_OBSERVED"),
        "attempt_frequency": (
            "SINGLE_ATTEMPT" if len(applicable) == 1 else "MULTIPLE_ATTEMPTS"
        ),
        "all_attempt_count": len(applicable),
        "ai_attempt_count": ai_count,
        "manual_attempt_count": manual_count,
        "mode_exposure": mode_exposure,
        "first_mode": modes[0],
        "final_or_latest_mode": modes[-1],
        "mode_transition_count": transition_count,
        "mode_changed": transition_count > 0,
        "distinct_author_count": author_count,
        "author_changed": author_count > 1,
        "ai_error_attempt_count": ai_error_count,
        "has_ai_error": ai_error_count > 0,
        "user_dropped_attempt_count": user_dropped_count,
        "has_user_dropped_attempt": user_dropped_count > 0,
        "returned_result_ai_attempt_count": len(returned_result),
        "has_returned_result_ai": not returned_result.empty,
        "source_comparison_eligible": len(transitions) > 0,
        "source_size_comparison_eligible": size_eligible,
        "reported_source_comparison_eligible": reported_eligible,
        "input_method_comparison_eligible": input_eligible,
        "source_signature_comparison_eligible": signature_eligible,
        "any_source_size_change": size_changed,
        "any_reported_source_change": reported_changed,
        "any_input_method_change": input_changed,
        "any_source_signature_change": signature_changed,
        "ai_feedback_record_count": feedback_count,
        "feedback_recorded_on_any_ai_attempt": feedback_count > 0,
        "first_attempt_timestamp": first_timestamp,
        "latest_observed_attempt_timestamp": latest_timestamp,
        "completed_timestamp": completed_timestamp,
        "report_run_cutoff_timestamp": unresolved_cutoff,
        "minutes_first_attempt_to_completion": completion_minutes,
        "minutes_first_attempt_to_last_observed_attempt": observed_minutes,
        "minutes_latest_attempt_to_report_run_cutoff": (latest_to_cutoff_minutes),
        "minutes_first_attempt_to_report_run_cutoff": (first_to_cutoff_minutes),
    }


def derive_study_retry_tables(
    *,
    study_attempt_author_history: pd.DataFrame,
    study_attempt_history: pd.DataFrame,
    successful_ai_generations: pd.DataFrame,
    successful_ai_transitions: pd.DataFrame,
    ai_feedback_records: pd.DataFrame | None = None,
    report_run_cutoff_timestamp: pd.Timestamp | None = None,
) -> StudyRetryTables:
    """Return deterministic one-row-per-study retry contexts."""
    attempt_columns = (
        "study_num",
        "audit_record_id",
        "attempt_start_timestamp",
        "attempt_end_timestamp",
        "attempt_authoring_mode",
        "attempt_result",
        "attempt_author_user_name",
    )
    study_columns = (
        "study_num",
        "study_is_completed",
        "all_attempt_count",
    )
    generation_columns = (
        "study_num",
        "audit_record_id",
    )
    transition_columns = (
        "study_num",
        "previous_audit_record_id",
        "current_audit_record_id",
        "source_size_comparison",
        "reported_source_comparison",
        "input_method_comparison",
        "source_signature_comparison",
    )
    _require_columns(
        study_attempt_author_history,
        attempt_columns,
        frame_name="study_attempt_author_history",
    )
    _require_columns(
        study_attempt_history,
        study_columns,
        frame_name="study_attempt_history",
    )
    _require_columns(
        successful_ai_generations,
        generation_columns,
        frame_name="successful_ai_generations",
    )
    _require_columns(
        successful_ai_transitions,
        transition_columns,
        frame_name="successful_ai_transitions",
    )

    if study_attempt_author_history.empty:
        if not study_attempt_history.empty:
            raise ExplorationValidationError(
                "retry-pathway derivation found study histories without attempts"
            )

        return StudyRetryTables(
            study_retry_context=pd.DataFrame(columns=list(STUDY_RETRY_CONTEXT_COLUMNS))
        )

    if study_attempt_author_history["study_num"].isna().any():
        raise ExplorationValidationError(
            "retry-pathway derivation requires non-null study numbers"
        )

    if (
        study_attempt_author_history["audit_record_id"].isna().any()
        or study_attempt_author_history["audit_record_id"].duplicated().any()
    ):
        raise ExplorationValidationError(
            "retry-pathway derivation requires unique non-null audit IDs"
        )

    attempts_by_study = {
        str(study_num): len(group)
        for study_num, group in study_attempt_author_history.groupby(
            "study_num",
            sort=False,
            dropna=False,
        )
    }
    histories_by_study = {
        str(row["study_num"]): row for _, row in study_attempt_history.iterrows()
    }

    if set(attempts_by_study) != set(histories_by_study):
        raise ExplorationValidationError(
            "retry-pathway derivation requires matching attempt and study populations"
        )

    for study_num, attempt_count in attempts_by_study.items():
        history = histories_by_study[study_num]
        if int(history["all_attempt_count"]) != attempt_count:
            raise ExplorationValidationError(
                "retry-pathway derivation found an attempt-count mismatch"
            )

        completed_count = int(
            study_attempt_author_history.loc[
                study_attempt_author_history["study_num"]
                .astype("string")
                .eq(study_num),
                "attempt_result",
            ]
            .eq(COMPLETE)
            .sum()
        )
        if bool(history["study_is_completed"]) != (completed_count == 1):
            raise ExplorationValidationError(
                "retry-pathway derivation found a completion-state mismatch"
            )

    feedback_counts = _feedback_counts_by_study(ai_feedback_records)
    unknown_feedback_studies = set(feedback_counts).difference(attempts_by_study)

    if unknown_feedback_studies:
        raise ExplorationValidationError(
            "ai_feedback_records contains studies outside the attempt population"
        )

    rows = [
        _study_row(
            group.reset_index(drop=True),
            successful_ai_generations=successful_ai_generations,
            successful_ai_transitions=successful_ai_transitions,
            feedback_count=feedback_counts.get(str(study_num), 0),
            report_run_cutoff_timestamp=report_run_cutoff_timestamp,
        )
        for study_num, group in study_attempt_author_history.groupby(
            "study_num",
            sort=True,
            dropna=False,
        )
    ]
    output = pd.DataFrame.from_records(
        rows,
        columns=list(STUDY_RETRY_CONTEXT_COLUMNS),
    )

    if len(output) != output["study_num"].nunique():
        raise ExplorationValidationError(
            "retry-pathway derivation must return exactly one row per study"
        )

    invalid_categories = set(output["pathway_category"]).difference(
        RETRY_PATHWAY_CATEGORIES
    )
    if invalid_categories:
        raise ExplorationValidationError(
            f"retry-pathway derivation produced invalid categories: "
            f"{sorted(invalid_categories)!r}"
        )

    return StudyRetryTables(study_retry_context=output)
