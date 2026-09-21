"""Derive successful-generation source context and repeated-attempt paths."""

from dataclasses import dataclass
from typing import cast

import pandas as pd

from study_posting_audit_exploration.errors import ExplorationValidationError

_AI = "AI"
_COMPLETE = "COMPLETE"
_EXCLUDED_AI_RESULTS = frozenset(
    {
        "AI_ERROR",
        "AI_ERROR_WITHOUT_STACK_TRACE",
    }
)

SUCCESSFUL_AI_GENERATION_COLUMNS: tuple[str, ...] = (
    "study_num",
    "audit_record_id",
    "attempt_start_timestamp",
    "attempt_result",
    "attempt_completion_group",
    "is_completed_ai_attempt",
    "source_size_chars",
    "latency_ms",
    "source_type",
    "study_content_source",
    "llm_inferred_study_content_source",
    "study_content_source_other_value",
    "llm_inferred_study_content_source_other_value",
)

SUCCESSFUL_AI_TRANSITION_COLUMNS: tuple[str, ...] = (
    "study_num",
    "transition_sequence_number",
    "previous_audit_record_id",
    "current_audit_record_id",
    "current_is_completed_ai_attempt",
    "source_size_comparison",
    "reported_source_comparison",
    "input_method_comparison",
    "source_signature_comparison",
    "full_input_signature_comparison",
    "source_change_category",
    "input_method_change_category",
    "previous_source_size_chars",
    "current_source_size_chars",
    "source_size_change_chars",
    "absolute_source_size_change_chars",
    "relative_source_size_change",
    "previous_latency_ms",
    "current_latency_ms",
    "latency_change_ms",
)

COMPLETED_AI_SOURCE_PATHWAY_COLUMNS: tuple[str, ...] = (
    "study_num",
    "completed_attempt_audit_record_id",
    "preceding_attempt_count",
    "preceding_successful_ai_attempt_count",
    "successful_ai_generation_attempt_count",
    "comparable_successful_ai_transition_count",
    "source_size_change_count",
    "reported_source_change_count",
    "input_method_change_count",
    "source_signature_change_count",
    "any_source_size_change",
    "any_reported_source_change",
    "any_input_method_change",
    "any_source_signature_change",
    "distinct_source_size_count",
    "distinct_reported_source_count",
    "distinct_input_method_count",
    "distinct_source_signature_count",
    "completed_source_size_chars",
    "completed_latency_ms",
    "completed_source_type",
    "completed_study_content_source",
    "completed_llm_inferred_study_content_source",
    "first_to_completion_source_size_comparison",
    "first_to_completion_reported_source_comparison",
    "first_to_completion_input_method_comparison",
    "first_to_completion_source_signature_comparison",
    "first_to_completion_source_size_change_chars",
    "first_to_completion_latency_change_ms",
    "preceding_to_completion_source_size_comparison",
    "preceding_to_completion_reported_source_comparison",
    "preceding_to_completion_input_method_comparison",
    "preceding_to_completion_source_signature_comparison",
    "preceding_to_completion_source_size_change_chars",
    "preceding_to_completion_latency_change_ms",
)


@dataclass(frozen=True, slots=True)
class SourceContextTables:
    """In-memory source-context derivations with explicit grains."""

    successful_ai_generations: pd.DataFrame
    successful_ai_transitions: pd.DataFrame
    completed_ai_source_pathways: pd.DataFrame


def _is_missing(value: object) -> bool:
    """Return whether one trusted scalar is missing."""
    if value is None or value is pd.NA or value is pd.NaT:
        return True

    if isinstance(value, float):
        return bool(pd.isna(value))

    return False


def _nullable_int(value: object) -> int | None:
    """Return an integer or ``None``."""
    if _is_missing(value):
        return None

    return int(cast("int | float | str", value))


def _nullable_text(value: object) -> str | None:
    """Return stripped nonblank text or ``None``."""
    if not isinstance(value, str):
        return None

    stripped = value.strip()

    return stripped or None


def _normalized_category(value: object) -> str | None:
    """Return one normalized category for comparison."""
    text = _nullable_text(value)

    return None if text is None else text.casefold()


def _comparison(
    previous: object,
    current: object,
    *,
    normalize_text: bool = False,
) -> str:
    """Return SAME, CHANGED, or MISSING for two values."""
    if normalize_text:
        previous_value: object = _normalized_category(previous)
        current_value: object = _normalized_category(current)
    else:
        previous_value = None if _is_missing(previous) else previous
        current_value = None if _is_missing(current) else current

    if previous_value is None or current_value is None:
        return "MISSING"

    return "SAME" if previous_value == current_value else "CHANGED"


def _combined_comparison(
    *comparisons: str,
) -> str:
    """Return combined SAME, CHANGED, or MISSING state."""
    if "MISSING" in comparisons:
        return "MISSING"

    return "SAME" if all(value == "SAME" for value in comparisons) else "CHANGED"


def _source_change_category(
    *,
    size_comparison: str,
    source_comparison: str,
) -> str:
    """Return one mutually exclusive source-change category."""
    if "MISSING" in {
        size_comparison,
        source_comparison,
    }:
        return "SOURCE_COMPARISON_MISSING"

    if size_comparison == "SAME" and source_comparison == "SAME":
        return "SAME_SOURCE_SIGNATURE"

    if size_comparison == "CHANGED" and source_comparison == "SAME":
        return "SIZE_CHANGED_ONLY"

    if size_comparison == "SAME" and source_comparison == "CHANGED":
        return "REPORTED_SOURCE_CHANGED_ONLY"

    return "SIZE_AND_REPORTED_SOURCE_CHANGED"


def _numeric_change(
    previous: object,
    current: object,
) -> int | None:
    """Return current minus previous for two nullable integers."""
    previous_value = _nullable_int(previous)
    current_value = _nullable_int(current)

    if previous_value is None or current_value is None:
        return None

    return current_value - previous_value


def _relative_size_change(
    previous: object,
    current: object,
) -> float | None:
    """Return relative size change when the previous size is positive."""
    previous_value = _nullable_int(previous)
    current_value = _nullable_int(current)

    if previous_value is None or current_value is None or previous_value <= 0:
        return None

    return (current_value - previous_value) / previous_value


def _require_source_columns(records: pd.DataFrame) -> None:
    """Require the validated record columns used by derivation."""
    required = (
        "ID",
        "STUDY_NUM",
        "START_TIME",
        "ATTEMPT_TYPE",
        "ATTEMPT_RESULT",
        "SOURCE_SIZE_CHARS",
        "LATENCY_MS",
        "SOURCE_TYPE",
        "STUDY_CONTENT_SOURCE",
        "LLM_INFERRED_STUDY_CONTENT_SOURCE",
        "STUDY_CONTENT_SOURCE_OTHER_VALUE",
        "LLM_INFERRED_STUDY_CONTENT_SOURCE_OTHER_VALUE",
    )
    missing = tuple(column for column in required if column not in records.columns)

    if missing:
        raise ExplorationValidationError(
            f"source-context derivation lacks required columns: {missing!r}"
        )

    if records["ID"].isna().any() or records["ID"].duplicated().any():
        raise ExplorationValidationError(
            "source-context derivation requires unique non-null audit IDs"
        )

    if records["STUDY_NUM"].isna().any():
        raise ExplorationValidationError(
            "source-context derivation requires non-null study numbers"
        )


def _successful_ai_generations(
    records: pd.DataFrame,
) -> pd.DataFrame:
    """Return one row per successful AI generation attempt."""
    successful = records.loc[
        records["ATTEMPT_TYPE"].eq(_AI)
        & ~records["ATTEMPT_RESULT"].isin(_EXCLUDED_AI_RESULTS)
    ].sort_values(
        by=[
            "STUDY_NUM",
            "START_TIME",
            "ID",
        ],
        kind="stable",
        na_position="last",
    )

    completed = successful["ATTEMPT_RESULT"].eq(_COMPLETE)

    return pd.DataFrame(
        {
            "study_num": successful["STUDY_NUM"],
            "audit_record_id": successful["ID"],
            "attempt_start_timestamp": successful["START_TIME"],
            "attempt_result": successful["ATTEMPT_RESULT"],
            "attempt_completion_group": completed.map(
                {
                    True: "COMPLETE",
                    False: "INCOMPLETE",
                }
            ),
            "is_completed_ai_attempt": completed,
            "source_size_chars": successful["SOURCE_SIZE_CHARS"],
            "latency_ms": successful["LATENCY_MS"],
            "source_type": successful["SOURCE_TYPE"],
            "study_content_source": successful["STUDY_CONTENT_SOURCE"],
            "llm_inferred_study_content_source": successful[
                "LLM_INFERRED_STUDY_CONTENT_SOURCE"
            ],
            "study_content_source_other_value": successful[
                "STUDY_CONTENT_SOURCE_OTHER_VALUE"
            ],
            "llm_inferred_study_content_source_other_value": successful[
                "LLM_INFERRED_STUDY_CONTENT_SOURCE_OTHER_VALUE"
            ],
        },
        columns=list(SUCCESSFUL_AI_GENERATION_COLUMNS),
    ).reset_index(drop=True)


def _transition_row(
    *,
    study_num: str,
    sequence_number: int,
    previous: pd.Series,
    current: pd.Series,
) -> dict[str, object]:
    """Return one consecutive successful-generation transition."""
    size_comparison = _comparison(
        previous["source_size_chars"],
        current["source_size_chars"],
    )
    source_comparison = _comparison(
        previous["study_content_source"],
        current["study_content_source"],
        normalize_text=True,
    )
    input_method_comparison = _comparison(
        previous["source_type"],
        current["source_type"],
        normalize_text=True,
    )
    source_signature_comparison = _combined_comparison(
        size_comparison,
        source_comparison,
    )
    full_signature_comparison = _combined_comparison(
        size_comparison,
        source_comparison,
        input_method_comparison,
    )
    size_change = _numeric_change(
        previous["source_size_chars"],
        current["source_size_chars"],
    )

    return {
        "study_num": study_num,
        "transition_sequence_number": sequence_number,
        "previous_audit_record_id": previous["audit_record_id"],
        "current_audit_record_id": current["audit_record_id"],
        "current_is_completed_ai_attempt": current["is_completed_ai_attempt"],
        "source_size_comparison": size_comparison,
        "reported_source_comparison": source_comparison,
        "input_method_comparison": input_method_comparison,
        "source_signature_comparison": source_signature_comparison,
        "full_input_signature_comparison": full_signature_comparison,
        "source_change_category": _source_change_category(
            size_comparison=size_comparison,
            source_comparison=source_comparison,
        ),
        "input_method_change_category": input_method_comparison,
        "previous_source_size_chars": previous["source_size_chars"],
        "current_source_size_chars": current["source_size_chars"],
        "source_size_change_chars": size_change,
        "absolute_source_size_change_chars": (
            None if size_change is None else abs(size_change)
        ),
        "relative_source_size_change": _relative_size_change(
            previous["source_size_chars"],
            current["source_size_chars"],
        ),
        "previous_latency_ms": previous["latency_ms"],
        "current_latency_ms": current["latency_ms"],
        "latency_change_ms": _numeric_change(
            previous["latency_ms"],
            current["latency_ms"],
        ),
    }


def _successful_ai_transitions(
    attempts: pd.DataFrame,
) -> pd.DataFrame:
    """Return one row per consecutive successful AI generation pair."""
    rows: list[dict[str, object]] = []

    for study_num, group in attempts.groupby(
        "study_num",
        sort=True,
        dropna=False,
    ):
        ordered = group.sort_values(
            by=[
                "attempt_start_timestamp",
                "audit_record_id",
            ],
            kind="stable",
            na_position="last",
        ).reset_index(drop=True)

        rows.extend(
            _transition_row(
                study_num=str(study_num),
                sequence_number=current_position,
                previous=ordered.iloc[current_position - 1],
                current=ordered.iloc[current_position],
            )
            for current_position in range(1, len(ordered))
        )

    return pd.DataFrame.from_records(
        rows,
        columns=list(SUCCESSFUL_AI_TRANSITION_COLUMNS),
    )


def _distinct_nonmissing_count(values: pd.Series) -> int:
    """Return distinct nonmissing values under normalized comparison."""
    normalized = {
        value
        for value in (_normalized_category(item) for item in values)
        if value is not None
    }

    return len(normalized)


def _distinct_signature_count(group: pd.DataFrame) -> int:
    """Return distinct comparable size and reported-source signatures."""
    signatures = {
        (
            _nullable_int(size),
            _normalized_category(source),
        )
        for size, source in zip(
            group["source_size_chars"],
            group["study_content_source"],
            strict=True,
        )
        if _nullable_int(size) is not None and _normalized_category(source) is not None
    }

    return len(signatures)


def _comparison_columns(
    previous: pd.Series | None,
    current: pd.Series,
    *,
    prefix: str,
) -> dict[str, object]:
    """Return source and latency comparison columns for one pair."""
    if previous is None:
        return {
            f"{prefix}_source_size_comparison": "MISSING",
            f"{prefix}_reported_source_comparison": "MISSING",
            f"{prefix}_input_method_comparison": "MISSING",
            f"{prefix}_source_signature_comparison": "MISSING",
            f"{prefix}_source_size_change_chars": None,
            f"{prefix}_latency_change_ms": None,
        }

    size_comparison = _comparison(
        previous["source_size_chars"],
        current["source_size_chars"],
    )
    source_comparison = _comparison(
        previous["study_content_source"],
        current["study_content_source"],
        normalize_text=True,
    )
    input_method_comparison = _comparison(
        previous["source_type"],
        current["source_type"],
        normalize_text=True,
    )

    return {
        f"{prefix}_source_size_comparison": size_comparison,
        f"{prefix}_reported_source_comparison": source_comparison,
        f"{prefix}_input_method_comparison": input_method_comparison,
        f"{prefix}_source_signature_comparison": _combined_comparison(
            size_comparison,
            source_comparison,
        ),
        f"{prefix}_source_size_change_chars": _numeric_change(
            previous["source_size_chars"],
            current["source_size_chars"],
        ),
        f"{prefix}_latency_change_ms": _numeric_change(
            previous["latency_ms"],
            current["latency_ms"],
        ),
    }


def _completed_ai_source_pathways(
    *,
    records: pd.DataFrame,
    successful_attempts: pd.DataFrame,
    transitions: pd.DataFrame,
) -> pd.DataFrame:
    """Return one source pathway row per completed AI study."""
    completed = successful_attempts.loc[
        successful_attempts["is_completed_ai_attempt"].eq(True)
    ]
    ordered_all = records.sort_values(
        by=[
            "STUDY_NUM",
            "START_TIME",
            "ID",
        ],
        kind="stable",
        na_position="last",
    )
    rows: list[dict[str, object]] = []

    for _, completion in completed.iterrows():
        study_num = str(completion["study_num"])
        completion_id = int(completion["audit_record_id"])
        all_study_attempts = ordered_all.loc[
            ordered_all["STUDY_NUM"].astype("string").eq(study_num)
        ]
        completion_position = all_study_attempts.index[
            all_study_attempts["ID"].eq(completion_id)
        ]

        if len(completion_position) != 1:
            raise ExplorationValidationError(
                "completed AI source pathway requires one matching completion attempt"
            )

        completion_start = completion["attempt_start_timestamp"]
        preceding_all = all_study_attempts.loc[
            all_study_attempts["START_TIME"].lt(completion_start)
            | (
                all_study_attempts["START_TIME"].eq(completion_start)
                & all_study_attempts["ID"].lt(completion_id)
            )
        ]
        successful_study = successful_attempts.loc[
            successful_attempts["study_num"].astype("string").eq(study_num)
            & (
                successful_attempts["attempt_start_timestamp"].lt(completion_start)
                | (
                    successful_attempts["attempt_start_timestamp"].eq(completion_start)
                    & successful_attempts["audit_record_id"].le(completion_id)
                )
            )
        ].sort_values(
            by=[
                "attempt_start_timestamp",
                "audit_record_id",
            ],
            kind="stable",
        )
        preceding_successful = successful_study.loc[
            ~successful_study["audit_record_id"].eq(completion_id)
        ]
        study_attempt_ids = frozenset(
            int(value) for value in successful_study["audit_record_id"]
        )
        study_transitions = transitions.loc[
            transitions["study_num"].astype("string").eq(study_num)
            & transitions["previous_audit_record_id"].isin(study_attempt_ids)
            & transitions["current_audit_record_id"].isin(study_attempt_ids)
        ]

        first = None if preceding_successful.empty else preceding_successful.iloc[0]
        preceding = (
            None if preceding_successful.empty else preceding_successful.iloc[-1]
        )

        size_change_count = int(
            study_transitions["source_size_comparison"].eq("CHANGED").sum()
        )
        source_change_count = int(
            study_transitions["reported_source_comparison"].eq("CHANGED").sum()
        )
        input_change_count = int(
            study_transitions["input_method_comparison"].eq("CHANGED").sum()
        )
        signature_change_count = int(
            study_transitions["source_signature_comparison"].eq("CHANGED").sum()
        )

        row: dict[str, object] = {
            "study_num": study_num,
            "completed_attempt_audit_record_id": completion_id,
            "preceding_attempt_count": len(preceding_all),
            "preceding_successful_ai_attempt_count": len(preceding_successful),
            "successful_ai_generation_attempt_count": len(successful_study),
            "comparable_successful_ai_transition_count": len(study_transitions),
            "source_size_change_count": size_change_count,
            "reported_source_change_count": source_change_count,
            "input_method_change_count": input_change_count,
            "source_signature_change_count": signature_change_count,
            "any_source_size_change": size_change_count > 0,
            "any_reported_source_change": source_change_count > 0,
            "any_input_method_change": input_change_count > 0,
            "any_source_signature_change": signature_change_count > 0,
            "distinct_source_size_count": int(
                successful_study["source_size_chars"].dropna().nunique()
            ),
            "distinct_reported_source_count": _distinct_nonmissing_count(
                successful_study["study_content_source"]
            ),
            "distinct_input_method_count": _distinct_nonmissing_count(
                successful_study["source_type"]
            ),
            "distinct_source_signature_count": _distinct_signature_count(
                successful_study
            ),
            "completed_source_size_chars": completion["source_size_chars"],
            "completed_latency_ms": completion["latency_ms"],
            "completed_source_type": completion["source_type"],
            "completed_study_content_source": completion["study_content_source"],
            "completed_llm_inferred_study_content_source": completion[
                "llm_inferred_study_content_source"
            ],
            **_comparison_columns(
                first,
                completion,
                prefix="first_to_completion",
            ),
            **_comparison_columns(
                preceding,
                completion,
                prefix="preceding_to_completion",
            ),
        }
        rows.append(row)

    return pd.DataFrame.from_records(
        rows,
        columns=list(COMPLETED_AI_SOURCE_PATHWAY_COLUMNS),
    )


def derive_source_context_tables(
    records: pd.DataFrame,
) -> SourceContextTables:
    """Return source-context attempt, transition, and completion-pathway tables."""
    _require_source_columns(records)
    successful = _successful_ai_generations(records)
    transitions = _successful_ai_transitions(successful)
    pathways = _completed_ai_source_pathways(
        records=records,
        successful_attempts=successful,
        transitions=transitions,
    )

    return SourceContextTables(
        successful_ai_generations=successful,
        successful_ai_transitions=transitions,
        completed_ai_source_pathways=pathways,
    )
