"""Synthetic tests for study-level retry-pathway derivation."""

from __future__ import annotations

import pandas as pd
import pytest

from study_posting_audit_exploration import (
    RETRY_PATHWAY_CATEGORIES,
    ExplorationValidationError,
    classify_retry_pathway,
    derive_study_retry_tables,
)
from study_posting_audit_exploration.derivation.retry_pathways import (
    STUDY_RETRY_CONTEXT_COLUMNS,
)

CATEGORY_CASES = (
    (("AI",), True, "SINGLE_ATTEMPT_AI_COMPLETION"),
    (("MANUAL",), True, "SINGLE_ATTEMPT_MANUAL_COMPLETION"),
    (("AI", "AI"), True, "REPEATED_AI_ONLY_TO_AI_COMPLETION"),
    (
        ("MANUAL", "MANUAL"),
        True,
        "REPEATED_MANUAL_ONLY_TO_MANUAL_COMPLETION",
    ),
    (("AI", "AI", "MANUAL"), True, "AI_TO_MANUAL_COMPLETION"),
    (("MANUAL", "MANUAL", "AI"), True, "MANUAL_TO_AI_COMPLETION"),
    (
        ("MANUAL", "AI", "MANUAL", "AI"),
        True,
        "MIXED_OR_ALTERNATING_TO_AI_COMPLETION",
    ),
    (
        ("AI", "MANUAL", "AI", "MANUAL"),
        True,
        "MIXED_OR_ALTERNATING_TO_MANUAL_COMPLETION",
    ),
    (("AI",), False, "SINGLE_ATTEMPT_AI_NO_COMPLETION_OBSERVED"),
    (
        ("MANUAL",),
        False,
        "SINGLE_ATTEMPT_MANUAL_NO_COMPLETION_OBSERVED",
    ),
    (
        ("AI", "AI"),
        False,
        "REPEATED_AI_ONLY_NO_COMPLETION_OBSERVED",
    ),
    (
        ("MANUAL", "MANUAL"),
        False,
        "REPEATED_MANUAL_ONLY_NO_COMPLETION_OBSERVED",
    ),
    (
        ("AI", "MANUAL", "AI"),
        False,
        "MIXED_MODES_NO_COMPLETION_OBSERVED",
    ),
)


@pytest.mark.parametrize(("modes", "completed", "expected"), CATEGORY_CASES)
def test_classify_retry_pathway_covers_every_category(
    modes: tuple[str, ...],
    completed: bool,
    expected: str,
) -> None:
    """Classify every mutually exclusive contract branch."""
    assert classify_retry_pathway(modes, completed=completed) == expected


def test_classifier_contract_is_exhaustive_and_stably_ordered() -> None:
    """Keep the public category order aligned with all classification branches."""
    observed = tuple(expected for _, _, expected in CATEGORY_CASES)

    assert observed == RETRY_PATHWAY_CATEGORIES
    assert len(set(observed)) == len(observed)


@pytest.mark.parametrize("modes", [(), ("UNKNOWN",), ("AI", "UNKNOWN")])
def test_classifier_rejects_invalid_mode_sequences(
    modes: tuple[str, ...],
) -> None:
    """Fail rather than silently classifying malformed sequences."""
    with pytest.raises(ExplorationValidationError):
        classify_retry_pathway(modes, completed=False)


def _attempt_frame(
    rows: list[dict[str, object]],
) -> pd.DataFrame:
    """Return a minimal attempt-history-shaped synthetic frame."""
    frame = pd.DataFrame(rows)
    frame["attempt_start_timestamp"] = pd.to_datetime(frame["attempt_start_timestamp"])
    completed = frame["attempt_result"].eq("COMPLETE")
    frame["attempt_end_timestamp"] = pd.NaT
    frame.loc[
        completed,
        "attempt_end_timestamp",
    ] = frame.loc[completed, "attempt_start_timestamp"] + pd.Timedelta(minutes=5)

    return frame


def _derive(
    attempts: pd.DataFrame,
    *,
    generations: pd.DataFrame | None = None,
    transitions: pd.DataFrame | None = None,
    feedback: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build study history and derive retry context from synthetic attempts."""
    study_rows = []

    for study_num, group in attempts.groupby("study_num", sort=True):
        study_rows.append(
            {
                "study_num": study_num,
                "study_is_completed": bool(
                    group["attempt_result"].eq("COMPLETE").any()
                ),
                "all_attempt_count": len(group),
            }
        )

    generation_columns = ["study_num", "audit_record_id"]
    transition_columns = [
        "study_num",
        "previous_audit_record_id",
        "current_audit_record_id",
        "source_size_comparison",
        "reported_source_comparison",
        "input_method_comparison",
        "source_signature_comparison",
    ]

    return derive_study_retry_tables(
        study_attempt_author_history=attempts,
        study_attempt_history=pd.DataFrame(study_rows),
        successful_ai_generations=(
            pd.DataFrame(columns=generation_columns)
            if generations is None
            else generations
        ),
        successful_ai_transitions=(
            pd.DataFrame(columns=transition_columns)
            if transitions is None
            else transitions
        ),
        ai_feedback_records=feedback,
    ).study_retry_context


def test_retry_context_derives_observed_characteristics_and_timing() -> None:
    """Derive workflow, source, feedback, and distinct timing semantics."""
    attempts = _attempt_frame(
        [
            {
                "study_num": "SYNTHETIC-A",
                "audit_record_id": 1,
                "attempt_start_timestamp": "2026-01-01T09:00:00",
                "attempt_authoring_mode": "AI",
                "attempt_result": "AI_ERROR",
                "attempt_author_user_name": "synthetic-author-a",
            },
            {
                "study_num": "SYNTHETIC-A",
                "audit_record_id": 2,
                "attempt_start_timestamp": "2026-01-01T09:10:00",
                "attempt_authoring_mode": "AI",
                "attempt_result": "USER_DROPPED",
                "attempt_author_user_name": "synthetic-author-a",
            },
            {
                "study_num": "SYNTHETIC-A",
                "audit_record_id": 3,
                "attempt_start_timestamp": "2026-01-01T09:20:00",
                "attempt_authoring_mode": "AI",
                "attempt_result": "USER_DROPPED",
                "attempt_author_user_name": "synthetic-author-b",
            },
            {
                "study_num": "SYNTHETIC-A",
                "audit_record_id": 4,
                "attempt_start_timestamp": "2026-01-01T09:30:00",
                "attempt_authoring_mode": "MANUAL",
                "attempt_result": "COMPLETE",
                "attempt_author_user_name": "synthetic-author-b",
            },
            {
                "study_num": "SYNTHETIC-B",
                "audit_record_id": 5,
                "attempt_start_timestamp": "2026-01-02T10:00:00",
                "attempt_authoring_mode": "MANUAL",
                "attempt_result": "USER_DROPPED",
                "attempt_author_user_name": "synthetic-author-c",
            },
            {
                "study_num": "SYNTHETIC-B",
                "audit_record_id": 6,
                "attempt_start_timestamp": "2026-01-02T10:45:00",
                "attempt_authoring_mode": "AI",
                "attempt_result": "USER_DROPPED",
                "attempt_author_user_name": "synthetic-author-c",
            },
        ]
    )
    generations = pd.DataFrame(
        [
            {"study_num": "SYNTHETIC-A", "audit_record_id": 2},
            {"study_num": "SYNTHETIC-A", "audit_record_id": 3},
            {"study_num": "SYNTHETIC-B", "audit_record_id": 6},
        ]
    )
    transitions = pd.DataFrame(
        [
            {
                "study_num": "SYNTHETIC-A",
                "previous_audit_record_id": 2,
                "current_audit_record_id": 3,
                "source_size_comparison": "CHANGED",
                "reported_source_comparison": "SAME",
                "input_method_comparison": "CHANGED",
                "source_signature_comparison": "CHANGED",
            }
        ]
    )
    feedback = pd.DataFrame(
        [
            {
                "study_num": "SYNTHETIC-A",
                "audit_record_id": 2,
                "feedback_recorded": True,
            },
            {
                "study_num": "SYNTHETIC-A",
                "audit_record_id": 3,
                "feedback_recorded": False,
            },
        ]
    )

    derived = _derive(
        attempts,
        generations=generations,
        transitions=transitions,
        feedback=feedback,
    )
    completed = derived.loc[derived["study_num"].eq("SYNTHETIC-A")].iloc[0]
    unresolved = derived.loc[derived["study_num"].eq("SYNTHETIC-B")].iloc[0]

    assert completed["pathway_category"] == "AI_TO_MANUAL_COMPLETION"
    assert completed["mode_exposure"] == "BOTH"
    assert completed["mode_transition_count"] == 1
    assert bool(completed["author_changed"]) is True
    assert completed["ai_error_attempt_count"] == 1
    assert completed["user_dropped_attempt_count"] == 2
    assert completed["returned_result_ai_attempt_count"] == 2
    assert bool(completed["source_comparison_eligible"]) is True
    assert bool(completed["any_source_size_change"]) is True
    assert bool(completed["any_reported_source_change"]) is False
    assert bool(completed["any_input_method_change"]) is True
    assert bool(completed["any_source_signature_change"]) is True
    assert completed["ai_feedback_record_count"] == 1
    assert completed["completed_timestamp"] == pd.Timestamp("2026-01-01T09:35:00")
    assert completed["minutes_first_attempt_to_completion"] == pytest.approx(35.0)
    assert pd.isna(completed["minutes_first_attempt_to_last_observed_attempt"])

    assert unresolved["pathway_category"] == "MIXED_MODES_NO_COMPLETION_OBSERVED"
    assert unresolved["minutes_first_attempt_to_last_observed_attempt"] == (
        pytest.approx(45.0)
    )
    assert pd.isna(unresolved["minutes_first_attempt_to_completion"])


def test_retry_context_detects_source_changes_and_changes_back() -> None:
    """Any eligible adjacent change remains observable after a later reversal."""
    attempts = _attempt_frame(
        [
            {
                "study_num": "SYNTHETIC-C",
                "audit_record_id": audit_id,
                "attempt_start_timestamp": f"2026-02-01T09:{minute:02d}:00",
                "attempt_authoring_mode": "AI",
                "attempt_result": ("COMPLETE" if audit_id == 3 else "USER_DROPPED"),
                "attempt_author_user_name": "synthetic-author",
            }
            for audit_id, minute in ((1, 0), (2, 10), (3, 20))
        ]
    )
    generations = pd.DataFrame(
        [
            {"study_num": "SYNTHETIC-C", "audit_record_id": audit_id}
            for audit_id in (1, 2, 3)
        ]
    )
    transitions = pd.DataFrame(
        [
            {
                "study_num": "SYNTHETIC-C",
                "previous_audit_record_id": 1,
                "current_audit_record_id": 2,
                "source_size_comparison": "CHANGED",
                "reported_source_comparison": "CHANGED",
                "input_method_comparison": "SAME",
                "source_signature_comparison": "CHANGED",
            },
            {
                "study_num": "SYNTHETIC-C",
                "previous_audit_record_id": 2,
                "current_audit_record_id": 3,
                "source_size_comparison": "CHANGED",
                "reported_source_comparison": "CHANGED",
                "input_method_comparison": "SAME",
                "source_signature_comparison": "CHANGED",
            },
        ]
    )

    row = _derive(
        attempts,
        generations=generations,
        transitions=transitions,
    ).iloc[0]

    assert row["pathway_category"] == "REPEATED_AI_ONLY_TO_AI_COMPLETION"
    assert bool(row["any_source_size_change"]) is True
    assert bool(row["any_reported_source_change"]) is True
    assert bool(row["any_input_method_change"]) is False
    assert bool(row["any_source_signature_change"]) is True


def test_retry_context_stops_at_completion() -> None:
    """Post-completion warning rows do not redefine the completion pathway."""
    attempts = _attempt_frame(
        [
            {
                "study_num": "SYNTHETIC-D",
                "audit_record_id": 1,
                "attempt_start_timestamp": "2026-03-01T09:00:00",
                "attempt_authoring_mode": "AI",
                "attempt_result": "COMPLETE",
                "attempt_author_user_name": "synthetic-author-a",
            },
            {
                "study_num": "SYNTHETIC-D",
                "audit_record_id": 2,
                "attempt_start_timestamp": "2026-03-01T09:10:00",
                "attempt_authoring_mode": "MANUAL",
                "attempt_result": "USER_DROPPED",
                "attempt_author_user_name": "synthetic-author-b",
            },
        ]
    )

    row = _derive(attempts).iloc[0]

    assert row["pathway_category"] == "SINGLE_ATTEMPT_AI_COMPLETION"
    assert row["all_attempt_count"] == 1
    assert row["final_or_latest_mode"] == "AI"
    assert bool(row["author_changed"]) is False


def test_empty_retry_context_has_stable_schema() -> None:
    """Return stable columns for an empty validated population."""
    attempts = pd.DataFrame(
        columns=[
            "study_num",
            "audit_record_id",
            "attempt_start_timestamp",
            "attempt_end_timestamp",
            "attempt_authoring_mode",
            "attempt_result",
            "attempt_author_user_name",
        ]
    )
    studies = pd.DataFrame(
        columns=["study_num", "study_is_completed", "all_attempt_count"]
    )
    generations = pd.DataFrame(columns=["study_num", "audit_record_id"])
    transitions = pd.DataFrame(
        columns=[
            "study_num",
            "previous_audit_record_id",
            "current_audit_record_id",
            "source_size_comparison",
            "reported_source_comparison",
            "input_method_comparison",
            "source_signature_comparison",
        ]
    )

    result = derive_study_retry_tables(
        study_attempt_author_history=attempts,
        study_attempt_history=studies,
        successful_ai_generations=generations,
        successful_ai_transitions=transitions,
    ).study_retry_context

    assert result.empty
    assert tuple(result.columns) == STUDY_RETRY_CONTEXT_COLUMNS


def test_retry_context_rejects_mismatched_study_population() -> None:
    """Fail fast when attempt and study histories disagree."""
    attempts = _attempt_frame(
        [
            {
                "study_num": "SYNTHETIC-E",
                "audit_record_id": 1,
                "attempt_start_timestamp": "2026-04-01T09:00:00",
                "attempt_authoring_mode": "AI",
                "attempt_result": "USER_DROPPED",
                "attempt_author_user_name": "synthetic-author",
            }
        ]
    )

    with pytest.raises(
        ExplorationValidationError,
        match="matching attempt and study populations",
    ):
        derive_study_retry_tables(
            study_attempt_author_history=attempts,
            study_attempt_history=pd.DataFrame(
                columns=["study_num", "study_is_completed", "all_attempt_count"]
            ),
            successful_ai_generations=pd.DataFrame(
                columns=["study_num", "audit_record_id"]
            ),
            successful_ai_transitions=pd.DataFrame(
                columns=[
                    "study_num",
                    "previous_audit_record_id",
                    "current_audit_record_id",
                    "source_size_comparison",
                    "reported_source_comparison",
                    "input_method_comparison",
                    "source_signature_comparison",
                ]
            ),
        )


def _minimal_retry_inputs() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """Return one valid unresolved retry input set."""
    attempts = _attempt_frame(
        [
            {
                "study_num": "SYNTHETIC-VALIDATION",
                "audit_record_id": 1,
                "attempt_start_timestamp": "2026-05-01T09:00:00",
                "attempt_authoring_mode": "AI",
                "attempt_result": "USER_DROPPED",
                "attempt_author_user_name": "synthetic-author",
            }
        ]
    )
    studies = pd.DataFrame.from_records(
        [
            {
                "study_num": "SYNTHETIC-VALIDATION",
                "study_is_completed": False,
                "all_attempt_count": 1,
            }
        ]
    )
    generations = pd.DataFrame(columns=["study_num", "audit_record_id"])
    transitions = pd.DataFrame(
        columns=[
            "study_num",
            "previous_audit_record_id",
            "current_audit_record_id",
            "source_size_comparison",
            "reported_source_comparison",
            "input_method_comparison",
            "source_signature_comparison",
        ]
    )

    return attempts, studies, generations, transitions


def _derive_validation_inputs(
    *,
    attempts: pd.DataFrame,
    studies: pd.DataFrame,
    generations: pd.DataFrame,
    transitions: pd.DataFrame,
    feedback: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Run retry derivation from one explicit validation fixture."""
    return derive_study_retry_tables(
        study_attempt_author_history=attempts,
        study_attempt_history=studies,
        successful_ai_generations=generations,
        successful_ai_transitions=transitions,
        ai_feedback_records=feedback,
    ).study_retry_context


def test_retry_context_rejects_missing_required_column() -> None:
    """Fail fast when an upstream derivation lacks its schema."""
    attempts, studies, generations, transitions = _minimal_retry_inputs()

    with pytest.raises(
        ExplorationValidationError,
        match="lacks required retry-pathway columns",
    ):
        _derive_validation_inputs(
            attempts=attempts.drop(columns=["attempt_result"]),
            studies=studies,
            generations=generations,
            transitions=transitions,
        )


def test_retry_context_rejects_study_history_without_attempts() -> None:
    """Reject nonempty study history paired with no attempts."""
    attempts, studies, generations, transitions = _minimal_retry_inputs()

    with pytest.raises(
        ExplorationValidationError,
        match="study histories without attempts",
    ):
        _derive_validation_inputs(
            attempts=attempts.iloc[0:0],
            studies=studies,
            generations=generations,
            transitions=transitions,
        )


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("study_num", None, "non-null study numbers"),
        ("audit_record_id", None, "unique non-null audit IDs"),
    ],
)
def test_retry_context_rejects_null_attempt_keys(
    column: str,
    value: object,
    message: str,
) -> None:
    """Reject null study and audit identities."""
    attempts, studies, generations, transitions = _minimal_retry_inputs()
    replacement = attempts[column].astype("object").copy()
    replacement.iloc[:] = value
    attempts = attempts.assign(**{column: replacement})

    with pytest.raises(ExplorationValidationError, match=message):
        _derive_validation_inputs(
            attempts=attempts,
            studies=studies,
            generations=generations,
            transitions=transitions,
        )


def test_retry_context_rejects_duplicate_audit_ids() -> None:
    """Require one row per audit attempt."""
    attempts, studies, generations, transitions = _minimal_retry_inputs()
    attempts = pd.concat([attempts, attempts], ignore_index=True)
    studies = studies.copy()
    studies.loc[:, "all_attempt_count"] = 2

    with pytest.raises(
        ExplorationValidationError,
        match="unique non-null audit IDs",
    ):
        _derive_validation_inputs(
            attempts=attempts,
            studies=studies,
            generations=generations,
            transitions=transitions,
        )


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("all_attempt_count", 2, "attempt-count mismatch"),
        ("study_is_completed", True, "completion-state mismatch"),
    ],
)
def test_retry_context_rejects_study_history_contradictions(
    field_name: str,
    value: int | bool,
    message: str,
) -> None:
    """Reject study-history counts or states that contradict attempts."""
    attempts, studies, generations, transitions = _minimal_retry_inputs()
    replacement = studies[field_name].astype("object").copy()
    replacement.iloc[:] = value
    studies = studies.assign(**{field_name: replacement})

    with pytest.raises(ExplorationValidationError, match=message):
        _derive_validation_inputs(
            attempts=attempts,
            studies=studies,
            generations=generations,
            transitions=transitions,
        )


def test_retry_context_rejects_multiple_completions() -> None:
    """Require at most one applicable completion per study."""
    attempts, studies, generations, transitions = _minimal_retry_inputs()
    second = attempts.copy()
    second.loc[:, "audit_record_id"] = 2
    second.loc[:, "attempt_start_timestamp"] = pd.Timestamp("2026-05-01T09:10:00")
    attempts = pd.concat([attempts, second], ignore_index=True)
    attempts.loc[:, "attempt_result"] = "COMPLETE"
    studies = studies.assign(
        study_is_completed=True,
        all_attempt_count=2,
    )

    with pytest.raises(
        ExplorationValidationError,
        match="completion-state mismatch",
    ):
        _derive_validation_inputs(
            attempts=attempts,
            studies=studies,
            generations=generations,
            transitions=transitions,
        )


@pytest.mark.parametrize(
    ("feedback", "message"),
    [
        (
            pd.DataFrame.from_records([{"study_num": None, "audit_record_id": 1}]),
            "non-null study numbers",
        ),
        (
            pd.DataFrame.from_records(
                [
                    {
                        "study_num": "SYNTHETIC-VALIDATION",
                        "audit_record_id": None,
                    }
                ]
            ),
            "non-null audit IDs",
        ),
        (
            pd.DataFrame.from_records(
                [
                    {
                        "study_num": "SYNTHETIC-UNKNOWN",
                        "audit_record_id": 99,
                    }
                ]
            ),
            "outside the attempt population",
        ),
    ],
)
def test_retry_context_rejects_invalid_feedback_keys(
    feedback: pd.DataFrame,
    message: str,
) -> None:
    """Validate count-only feedback joins without exposing text."""
    attempts, studies, generations, transitions = _minimal_retry_inputs()

    with pytest.raises(ExplorationValidationError, match=message):
        _derive_validation_inputs(
            attempts=attempts,
            studies=studies,
            generations=generations,
            transitions=transitions,
            feedback=feedback,
        )


def test_retry_context_accepts_feedback_rows_without_boolean_column() -> None:
    """Treat each supplied row as recorded when no Boolean column is present."""
    attempts, studies, generations, transitions = _minimal_retry_inputs()
    feedback = pd.DataFrame.from_records(
        [
            {
                "study_num": "SYNTHETIC-VALIDATION",
                "audit_record_id": 1,
            }
        ]
    )

    result = _derive_validation_inputs(
        attempts=attempts,
        studies=studies,
        generations=generations,
        transitions=transitions,
        feedback=feedback,
    )

    assert result.iloc[0]["ai_feedback_record_count"] == 1
    assert bool(result.iloc[0]["feedback_recorded_on_any_ai_attempt"]) is True


def test_retry_context_handles_missing_attempt_timestamps() -> None:
    """Keep timing missing when applicable timestamps are unavailable."""
    attempts, studies, generations, transitions = _minimal_retry_inputs()
    attempts = attempts.copy()
    attempts.loc[:, "attempt_start_timestamp"] = pd.NaT

    row = _derive_validation_inputs(
        attempts=attempts,
        studies=studies,
        generations=generations,
        transitions=transitions,
    ).iloc[0]

    assert pd.isna(row["first_attempt_timestamp"])
    assert pd.isna(row["minutes_first_attempt_to_last_observed_attempt"])
