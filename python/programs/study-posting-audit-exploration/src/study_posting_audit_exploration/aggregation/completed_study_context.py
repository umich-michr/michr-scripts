"""Completed-study counts by completion-author context."""

import pandas as pd

_AI = "AI"
_MANUAL = "MANUAL"
_EFFECTIVE_ROLE = "EFFECTIVE_ROLE"
_PI_STATUS = "PI_STATUS"
_PI = "PI"
_NON_PI = "NON_PI"

COMPLETED_STUDY_AUTHOR_CONTEXT_COLUMNS: tuple[str, ...] = (
    "context_dimension_name",
    "context_dimension_value",
    "final_completion_authoring_mode",
    "completed_study_count",
    "mode_completed_study_count",
    "all_completed_study_count",
    "completed_study_percentage_within_mode",
    "completed_study_percentage_overall",
    "distinct_completion_author_count",
)

_REQUIRED_COLUMNS: tuple[str, ...] = (
    "study_num",
    "attempt_authoring_mode",
    "attempt_author_user_name",
    "effective_attempt_author_role",
    "attempt_author_is_study_pi",
    "is_completed_attempt",
)


def _empty_summary() -> pd.DataFrame:
    """Return a stable empty result with the public column contract."""
    return pd.DataFrame(columns=list(COMPLETED_STUDY_AUTHOR_CONTEXT_COLUMNS))


def _percentage(numerator: int, denominator: int) -> float | None:
    """Return a percentage or None for an empty denominator."""
    if denominator == 0:
        return None

    return 100.0 * numerator / denominator


def _require_columns(attempts: pd.DataFrame) -> None:
    """Require the completed-attempt context columns."""
    missing_columns = [
        column for column in _REQUIRED_COLUMNS if column not in attempts.columns
    ]

    if missing_columns:
        joined_columns = ", ".join(missing_columns)
        raise ValueError(
            f"Completed-study author context requires columns: {joined_columns}."
        )


def _completed_attempts(attempts: pd.DataFrame) -> pd.DataFrame:
    """Return one validated row per completed study."""
    completed = attempts.loc[
        attempts["is_completed_attempt"].eq(True),
        list(_REQUIRED_COLUMNS),
    ].copy()

    if completed.empty:
        return completed

    duplicate_studies = completed["study_num"].duplicated(keep=False)

    if duplicate_studies.any():
        raise ValueError(
            "Completed-study author context requires exactly one completed "
            "attempt per completed study."
        )

    invalid_modes = ~completed["attempt_authoring_mode"].isin([_AI, _MANUAL])

    if invalid_modes.any():
        raise ValueError(
            "Completed-study author context requires completed attempts to "
            "use AI or MANUAL authoring mode."
        )

    missing_roles = completed["effective_attempt_author_role"].isna() | completed[
        "effective_attempt_author_role"
    ].astype("string").str.strip().eq("")

    if missing_roles.any():
        raise ValueError(
            "Completed-study author context requires a nonblank effective "
            "completion-author role."
        )

    pi_status = completed["attempt_author_is_study_pi"]

    if pi_status.isna().any() or not pi_status.isin([True, False]).all():
        raise ValueError(
            "Completed-study author context requires Boolean PI status for "
            "every completed attempt."
        )

    return completed


def _summary_rows(
    completed: pd.DataFrame,
    *,
    dimension_name: str,
    value_column: str,
) -> list[dict[str, object]]:
    """Return rows for one completion-author context dimension."""
    all_completed_count = int(completed["study_num"].nunique())
    rows: list[dict[str, object]] = []

    for mode in (_AI, _MANUAL):
        mode_attempts = completed.loc[completed["attempt_authoring_mode"].eq(mode)]

        if mode_attempts.empty:
            continue

        mode_count = int(mode_attempts["study_num"].nunique())

        for value in sorted(
            str(item) for item in mode_attempts[value_column].drop_duplicates().tolist()
        ):
            group = mode_attempts.loc[
                mode_attempts[value_column].astype("string").eq(value)
            ]
            study_count = int(group["study_num"].nunique())

            rows.append(
                {
                    "context_dimension_name": dimension_name,
                    "context_dimension_value": value,
                    "final_completion_authoring_mode": mode,
                    "completed_study_count": study_count,
                    "mode_completed_study_count": mode_count,
                    "all_completed_study_count": all_completed_count,
                    "completed_study_percentage_within_mode": _percentage(
                        study_count,
                        mode_count,
                    ),
                    "completed_study_percentage_overall": _percentage(
                        study_count,
                        all_completed_count,
                    ),
                    "distinct_completion_author_count": int(
                        group["attempt_author_user_name"].nunique(dropna=True)
                    ),
                }
            )

    return rows


def build_completed_study_author_context_summary(
    study_attempt_author_history: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize completed studies by final mode, role, and study-specific PI status.

    Each completed study contributes exactly once through its unique completed
    attempt. Author identity is used only to calculate distinct-author counts
    and is not published in the returned aggregate.
    """
    _require_columns(study_attempt_author_history)
    completed = _completed_attempts(study_attempt_author_history)

    if completed.empty:
        return _empty_summary()

    completed["completion_author_pi_status"] = completed[
        "attempt_author_is_study_pi"
    ].map({True: _PI, False: _NON_PI})

    rows = [
        *_summary_rows(
            completed,
            dimension_name=_EFFECTIVE_ROLE,
            value_column="effective_attempt_author_role",
        ),
        *_summary_rows(
            completed,
            dimension_name=_PI_STATUS,
            value_column="completion_author_pi_status",
        ),
    ]

    return pd.DataFrame.from_records(
        rows,
        columns=list(COMPLETED_STUDY_AUTHOR_CONTEXT_COLUMNS),
    )
