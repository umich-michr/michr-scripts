"""Derive attempt-, study-, and author-grain audit histories."""

from datetime import date, datetime
from typing import cast

import pandas as pd

from study_posting_audit_exploration.derivation.roles import derive_role_columns
from study_posting_audit_exploration.errors import ExplorationValidationError
from study_posting_audit_exploration.models import AttemptHistoryTables

_COMPLETE = "COMPLETE"
_AI = "AI"
_MANUAL = "MANUAL"
_AI_ERROR = "AI_ERROR"
_AI_ERROR_WITHOUT_STACK_TRACE = "AI_ERROR_WITHOUT_STACK_TRACE"
_USER_DROPPED = "USER_DROPPED"
_MILLISECONDS_PER_MINUTE = 60_000.0

_ATTEMPT_HISTORY_COLUMNS: tuple[str, ...] = (
    "study_num",
    "attempt_sequence_number",
    "audit_record_id",
    "attempt_start_timestamp",
    "attempt_end_timestamp",
    "attempt_authoring_mode",
    "attempt_result",
    "attempt_completion_group",
    "attempt_author_user_name",
    "attempt_author_user_id",
    "study_created_by_user_id",
    "completion_author_user_name",
    "completion_author_user_id",
    "study_pi_user_name",
    "effective_attempt_author_role",
    "author_is_pi_by_eresearch_role",
    "author_is_pi_by_application_role",
    "author_matches_named_pi_user_name",
    "attempt_author_is_study_pi",
    "same_author_as_completion_attempt",
    "author_changed_from_previous_attempt",
    "author_appointments_raw",
    "pi_appointments_raw",
    "prior_studies_created_before_attempt_start_count",
    "total_studies_created_as_of_report_query_count",
    "other_study_memberships_as_of_report_query_count",
    "distinct_login_days_as_of_report_query_count",
    "first_login_timestamp_as_of_report_query",
    "latest_login_timestamp_as_of_report_query",
    "login_history_span_days_as_of_report_query",
    "study_info_page_minutes",
    "total_attempt_duration_minutes",
    "is_preceding_incomplete_attempt",
    "is_completed_attempt",
)

_STUDY_HISTORY_COLUMNS: tuple[str, ...] = (
    "study_num",
    "study_created_by_user_id",
    "study_pi_user_name",
    "study_is_completed",
    "all_attempt_count",
    "ai_attempt_count",
    "manual_attempt_count",
    "complete_attempt_count",
    "incomplete_attempt_count",
    "ai_error_attempt_count",
    "ai_error_without_stack_trace_attempt_count",
    "user_dropped_attempt_count",
    "first_attempt_audit_record_id",
    "first_attempt_author_user_name",
    "first_attempt_author_user_id",
    "first_attempt_start_timestamp",
    "first_attempt_authoring_mode",
    "first_attempt_result",
    "completed_attempt_audit_record_id",
    "completion_author_user_name",
    "completion_author_user_id",
    "completed_attempt_start_timestamp",
    "completed_attempt_end_timestamp",
    "completed_attempt_authoring_mode",
    "distinct_attempt_author_count",
    "author_changed_between_attempts",
    "author_changed_before_completion",
    "first_attempt_author_matches_completion_author",
    "immediately_preceding_author_matches_completion_author",
    "completion_author_had_preceding_incomplete_attempt",
    "other_author_had_preceding_incomplete_attempt",
    "preceding_incomplete_attempt_count",
    "preceding_incomplete_attempt_count_by_completion_author",
    "preceding_incomplete_attempt_count_by_other_authors",
    "preceding_ai_error_attempt_count",
    "preceding_ai_error_without_stack_trace_attempt_count",
    "preceding_user_dropped_attempt_count",
    "minutes_first_attempt_to_completion",
    "completed_attempt_study_info_page_minutes",
    "completed_attempt_total_duration_minutes",
    "has_attempt_after_completion",
)

_AUTHOR_HISTORY_COLUMNS: tuple[str, ...] = (
    "author_user_name",
    "author_user_id",
    "author_adoption_group",
    "first_observed_audit_record_id",
    "latest_observed_audit_record_id",
    "first_attempt_start_timestamp",
    "latest_attempt_start_timestamp",
    "effective_author_role_at_latest_attempt",
    "author_is_pi_on_any_attempt",
    "author_appointments_at_latest_attempt",
    "total_studies_created_as_of_report_query_count",
    "other_study_memberships_as_of_report_query_count",
    "distinct_login_days_as_of_report_query_count",
    "first_login_timestamp_as_of_report_query",
    "latest_login_timestamp_as_of_report_query",
    "login_history_span_days_as_of_report_query",
    "distinct_study_count_with_any_attempt",
    "distinct_completed_study_count_authored",
    "distinct_study_count_eventually_created",
    "distinct_study_count_with_any_ai_attempt",
    "distinct_study_count_with_any_manual_attempt",
    "distinct_study_count_with_both_modes",
    "completed_ai_study_count_authored",
    "completed_manual_study_count_authored",
    "all_attempt_count",
    "ai_attempt_count",
    "manual_attempt_count",
    "ai_error_attempt_count",
    "ai_error_without_stack_trace_attempt_count",
    "user_dropped_attempt_count",
)


def _is_missing_scalar(value: object) -> bool:
    """Return whether one trusted DataFrame scalar is missing."""
    if value is None or value is pd.NA or value is pd.NaT:
        return True

    if isinstance(value, float):
        return pd.isna(value)

    return False


def _nullable_int(value: object) -> int | None:
    """Return a Python integer or ``None``."""
    if _is_missing_scalar(value):
        return None

    return int(cast("int | float | str", value))


def _nullable_timestamp(value: object) -> pd.Timestamp | None:
    """Return a timestamp or ``None``."""
    if _is_missing_scalar(value):
        return None

    timestamp_value = cast(
        "str | int | float | date | datetime | pd.Timestamp",
        value,
    )

    return pd.Timestamp(timestamp_value)


def _login_span_days(
    minimum_login_time: object,
    maximum_login_time: object,
) -> float | None:
    """Return elapsed login-history days."""
    minimum = _nullable_timestamp(minimum_login_time)
    maximum = _nullable_timestamp(maximum_login_time)

    if minimum is None or maximum is None:
        return None

    return (maximum - minimum).total_seconds() / 86_400.0


def _minutes_from_milliseconds(value: object) -> float | None:
    """Return minutes from a nullable millisecond value."""
    if _is_missing_scalar(value):
        return None

    return float(cast("int | float | str", value)) / (_MILLISECONDS_PER_MINUTE)


def _require_validated_records(records: pd.DataFrame) -> None:
    """Require assumptions established by input validation."""
    if records["ID"].isna().any() or records["ID"].duplicated().any():
        raise ExplorationValidationError(
            "attempt-history derivation requires unique non-null audit IDs"
        )

    if records["STUDY_NUM"].isna().any():
        raise ExplorationValidationError(
            "attempt-history derivation requires non-null study numbers"
        )

    if records["AUTHOR_USER_NAME"].isna().any():
        raise ExplorationValidationError(
            "attempt-history derivation requires non-null author usernames"
        )

    complete_counts = (
        records.loc[records["ATTEMPT_RESULT"].eq(_COMPLETE)].groupby("STUDY_NUM").size()
    )

    if bool((complete_counts > 1).any()):
        raise ExplorationValidationError(
            "attempt-history derivation requires at most one complete attempt per study"
        )


def _ordered_records(records: pd.DataFrame) -> pd.DataFrame:
    """Return records ordered within study by start time and audit ID."""
    return records.sort_values(
        by=["STUDY_NUM", "START_TIME", "ID"],
        kind="stable",
        na_position="last",
    ).reset_index(drop=True)


def _completion_context(records: pd.DataFrame) -> pd.DataFrame:
    """Return one completion context per completed study."""
    return records.loc[
        records["ATTEMPT_RESULT"].eq(_COMPLETE),
        [
            "STUDY_NUM",
            "START_TIME",
            "AUTHOR_USER_NAME",
            "USER_ID",
        ],
    ].rename(
        columns={
            "START_TIME": "completion_start_timestamp",
            "AUTHOR_USER_NAME": "completion_author_user_name",
            "USER_ID": "completion_author_user_id",
        }
    )


def _derive_attempt_history(records: pd.DataFrame) -> pd.DataFrame:
    """Return one enriched row per audit attempt."""
    ordered = _ordered_records(records)
    enriched = ordered.merge(
        _completion_context(ordered),
        on="STUDY_NUM",
        how="left",
        validate="many_to_one",
    ).merge(
        derive_role_columns(ordered),
        left_on="ID",
        right_on="audit_record_id",
        how="left",
        validate="one_to_one",
    )
    enriched["attempt_sequence_number"] = (
        enriched.groupby("STUDY_NUM").cumcount() + 1
    ).astype("Int64")
    enriched["is_completed_attempt"] = enriched["ATTEMPT_RESULT"].eq(_COMPLETE)
    enriched["attempt_completion_group"] = (
        enriched["is_completed_attempt"]
        .map({True: "COMPLETE", False: "INCOMPLETE"})
        .astype("string")
    )
    enriched["same_author_as_completion_attempt"] = (
        enriched["completion_author_user_name"].notna()
        & enriched["AUTHOR_USER_NAME"].eq(enriched["completion_author_user_name"])
    ).astype("boolean")
    enriched["author_changed_from_previous_attempt"] = (
        enriched.groupby("STUDY_NUM")["AUTHOR_USER_NAME"]
        .transform(lambda values: values.ne(values.shift()))
        .fillna(False)
        .astype("boolean")
    )
    enriched["is_preceding_incomplete_attempt"] = (
        enriched["completion_start_timestamp"].notna()
        & enriched["START_TIME"].lt(enriched["completion_start_timestamp"])
        & ~enriched["is_completed_attempt"]
    ).astype("boolean")

    prior_created = enriched["PRIOR_CREATED_COUNT"]

    output = pd.DataFrame(
        {
            "study_num": enriched["STUDY_NUM"],
            "attempt_sequence_number": enriched["attempt_sequence_number"],
            "audit_record_id": enriched["ID"],
            "attempt_start_timestamp": enriched["START_TIME"],
            "attempt_end_timestamp": enriched["END_TIME"],
            "attempt_authoring_mode": enriched["ATTEMPT_TYPE"],
            "attempt_result": enriched["ATTEMPT_RESULT"],
            "attempt_completion_group": enriched["attempt_completion_group"],
            "attempt_author_user_name": enriched["AUTHOR_USER_NAME"],
            "attempt_author_user_id": enriched["USER_ID"],
            "study_created_by_user_id": enriched["CREATED_BY_ID"],
            "completion_author_user_name": enriched["completion_author_user_name"],
            "completion_author_user_id": enriched["completion_author_user_id"],
            "study_pi_user_name": enriched["PI_USER_NAME"],
            "effective_attempt_author_role": enriched["effective_attempt_author_role"],
            "author_is_pi_by_eresearch_role": enriched[
                "author_is_pi_by_eresearch_role"
            ],
            "author_is_pi_by_application_role": enriched[
                "author_is_pi_by_application_role"
            ],
            "author_matches_named_pi_user_name": enriched[
                "author_matches_named_pi_user_name"
            ],
            "attempt_author_is_study_pi": enriched["attempt_author_is_study_pi"],
            "same_author_as_completion_attempt": enriched[
                "same_author_as_completion_attempt"
            ],
            "author_changed_from_previous_attempt": enriched[
                "author_changed_from_previous_attempt"
            ],
            "author_appointments_raw": enriched["AUTHOR_APPOINTMENTS"],
            "pi_appointments_raw": enriched["PI_APPOINTMENTS"],
            "prior_studies_created_before_attempt_start_count": prior_created,
            "total_studies_created_as_of_report_query_count": enriched[
                "TOTAL_CREATED_COUNT"
            ],
            "other_study_memberships_as_of_report_query_count": enriched[
                "MEMBER_OF_OTHER_STUDIES_COUNT"
            ],
            "distinct_login_days_as_of_report_query_count": enriched["LOGIN_DAYS"],
            "first_login_timestamp_as_of_report_query": enriched["MIN_LOGIN_TIME"],
            "latest_login_timestamp_as_of_report_query": enriched["MAX_LOGIN_TIME"],
            "login_history_span_days_as_of_report_query": [
                _login_span_days(minimum, maximum)
                for minimum, maximum in zip(
                    enriched["MIN_LOGIN_TIME"],
                    enriched["MAX_LOGIN_TIME"],
                    strict=True,
                )
            ],
            "study_info_page_minutes": [
                _minutes_from_milliseconds(value)
                for value in enriched["TIME_SPENT_ON_STUDY_INFO_PAGE_MS"]
            ],
            "total_attempt_duration_minutes": [
                _minutes_from_milliseconds(value)
                for value in enriched["TIME_TO_FINISH_ADDING_STUDY_MS"]
            ],
            "is_preceding_incomplete_attempt": enriched[
                "is_preceding_incomplete_attempt"
            ],
            "is_completed_attempt": enriched["is_completed_attempt"],
        }
    )

    return output.loc[:, list(_ATTEMPT_HISTORY_COLUMNS)]


def _mode_count(group: pd.DataFrame, *, mode: str) -> int:
    """Return attempts using one authoring mode."""
    return int(group["attempt_authoring_mode"].eq(mode).sum())


def _result_count(group: pd.DataFrame, *, result: str) -> int:
    """Return attempts with one exact result."""
    return int(group["attempt_result"].eq(result).sum())


def _study_history_row(group: pd.DataFrame) -> dict[str, object]:
    """Return one study-level history row."""
    first = group.iloc[0]
    completed = group.loc[group["is_completed_attempt"]]
    completed_row = None if completed.empty else completed.iloc[0]
    preceding = group.loc[group["is_preceding_incomplete_attempt"]]
    same_author_preceding = preceding.loc[
        preceding["same_author_as_completion_attempt"].eq(True)
    ]
    other_author_preceding = preceding.loc[
        preceding["same_author_as_completion_attempt"].eq(False)
    ]
    immediately_preceding = (
        None if completed_row is None or preceding.empty else preceding.iloc[-1]
    )
    first_start = _nullable_timestamp(first["attempt_start_timestamp"])
    completion_start = (
        None
        if completed_row is None
        else _nullable_timestamp(completed_row["attempt_start_timestamp"])
    )
    minutes_to_completion = (
        None
        if first_start is None or completion_start is None
        else (completion_start - first_start).total_seconds() / 60.0
    )

    return {
        "study_num": first["study_num"],
        "study_created_by_user_id": _nullable_int(first["study_created_by_user_id"]),
        "study_pi_user_name": first["study_pi_user_name"],
        "study_is_completed": completed_row is not None,
        "all_attempt_count": len(group),
        "ai_attempt_count": _mode_count(group, mode=_AI),
        "manual_attempt_count": _mode_count(group, mode=_MANUAL),
        "complete_attempt_count": _result_count(group, result=_COMPLETE),
        "incomplete_attempt_count": int(
            group["attempt_completion_group"].eq("INCOMPLETE").sum()
        ),
        "ai_error_attempt_count": _result_count(group, result=_AI_ERROR),
        "ai_error_without_stack_trace_attempt_count": _result_count(
            group,
            result=_AI_ERROR_WITHOUT_STACK_TRACE,
        ),
        "user_dropped_attempt_count": _result_count(
            group,
            result=_USER_DROPPED,
        ),
        "first_attempt_audit_record_id": int(first["audit_record_id"]),
        "first_attempt_author_user_name": first["attempt_author_user_name"],
        "first_attempt_author_user_id": _nullable_int(first["attempt_author_user_id"]),
        "first_attempt_start_timestamp": first["attempt_start_timestamp"],
        "first_attempt_authoring_mode": first["attempt_authoring_mode"],
        "first_attempt_result": first["attempt_result"],
        "completed_attempt_audit_record_id": (
            None if completed_row is None else int(completed_row["audit_record_id"])
        ),
        "completion_author_user_name": (
            None if completed_row is None else completed_row["attempt_author_user_name"]
        ),
        "completion_author_user_id": (
            None
            if completed_row is None
            else _nullable_int(completed_row["attempt_author_user_id"])
        ),
        "completed_attempt_start_timestamp": (
            None if completed_row is None else completed_row["attempt_start_timestamp"]
        ),
        "completed_attempt_end_timestamp": (
            None if completed_row is None else completed_row["attempt_end_timestamp"]
        ),
        "completed_attempt_authoring_mode": (
            None if completed_row is None else completed_row["attempt_authoring_mode"]
        ),
        "distinct_attempt_author_count": int(
            group["attempt_author_user_name"].nunique()
        ),
        "author_changed_between_attempts": bool(
            group["author_changed_from_previous_attempt"].any()
        ),
        "author_changed_before_completion": bool(len(other_author_preceding)),
        "first_attempt_author_matches_completion_author": (
            None
            if completed_row is None
            else bool(first["same_author_as_completion_attempt"])
        ),
        "immediately_preceding_author_matches_completion_author": (
            None
            if immediately_preceding is None
            else bool(immediately_preceding["same_author_as_completion_attempt"])
        ),
        "completion_author_had_preceding_incomplete_attempt": bool(
            len(same_author_preceding)
        ),
        "other_author_had_preceding_incomplete_attempt": bool(
            len(other_author_preceding)
        ),
        "preceding_incomplete_attempt_count": len(preceding),
        "preceding_incomplete_attempt_count_by_completion_author": len(
            same_author_preceding
        ),
        "preceding_incomplete_attempt_count_by_other_authors": len(
            other_author_preceding
        ),
        "preceding_ai_error_attempt_count": _result_count(
            preceding,
            result=_AI_ERROR,
        ),
        "preceding_ai_error_without_stack_trace_attempt_count": _result_count(
            preceding,
            result=_AI_ERROR_WITHOUT_STACK_TRACE,
        ),
        "preceding_user_dropped_attempt_count": _result_count(
            preceding,
            result=_USER_DROPPED,
        ),
        "minutes_first_attempt_to_completion": minutes_to_completion,
        "completed_attempt_study_info_page_minutes": (
            None if completed_row is None else completed_row["study_info_page_minutes"]
        ),
        "completed_attempt_total_duration_minutes": (
            None
            if completed_row is None
            else completed_row["total_attempt_duration_minutes"]
        ),
        "has_attempt_after_completion": (
            False
            if completed_row is None
            else bool(
                group["attempt_start_timestamp"]
                .gt(completed_row["attempt_start_timestamp"])
                .any()
            )
        ),
    }


def _derive_study_history(attempt_history: pd.DataFrame) -> pd.DataFrame:
    """Return one history row per study."""
    rows = [
        _study_history_row(group.reset_index(drop=True))
        for _, group in attempt_history.groupby(
            "study_num",
            sort=False,
            dropna=False,
        )
    ]

    return pd.DataFrame.from_records(
        rows,
        columns=list(_STUDY_HISTORY_COLUMNS),
    )


def _adoption_group(group: pd.DataFrame) -> str:
    """Return one author's mutually exclusive mode-adoption group."""
    has_ai = bool(group["attempt_authoring_mode"].eq(_AI).any())
    has_manual = bool(group["attempt_authoring_mode"].eq(_MANUAL).any())

    if has_ai and has_manual:
        return "BOTH_AI_AND_MANUAL"

    return "AI_ONLY" if has_ai else "MANUAL_ONLY"


def _latest_nonmissing(values: pd.Series) -> object:
    """Return the latest non-null value or ``None``."""
    nonmissing = values.dropna()

    return None if nonmissing.empty else nonmissing.iloc[-1]


def _author_history_row(
    group: pd.DataFrame,
    *,
    completed_studies: frozenset[str],
) -> dict[str, object]:
    """Return one author-level history row."""
    ordered = group.sort_values(
        by=["attempt_start_timestamp", "audit_record_id"],
        kind="stable",
    )
    first = ordered.iloc[0]
    latest = ordered.iloc[-1]
    authored_completed = ordered.loc[ordered["is_completed_attempt"]]
    study_modes = {
        str(study_num): frozenset(
            str(value) for value in study_group["attempt_authoring_mode"]
        )
        for study_num, study_group in ordered.groupby(
            "study_num",
            sort=False,
            dropna=False,
        )
    }

    return {
        "author_user_name": first["attempt_author_user_name"],
        "author_user_id": _nullable_int(
            _latest_nonmissing(ordered["attempt_author_user_id"])
        ),
        "author_adoption_group": _adoption_group(ordered),
        "first_observed_audit_record_id": int(first["audit_record_id"]),
        "latest_observed_audit_record_id": int(latest["audit_record_id"]),
        "first_attempt_start_timestamp": first["attempt_start_timestamp"],
        "latest_attempt_start_timestamp": latest["attempt_start_timestamp"],
        "effective_author_role_at_latest_attempt": latest[
            "effective_attempt_author_role"
        ],
        "author_is_pi_on_any_attempt": bool(
            ordered["attempt_author_is_study_pi"].any()
        ),
        "author_appointments_at_latest_attempt": latest["author_appointments_raw"],
        "total_studies_created_as_of_report_query_count": _nullable_int(
            _latest_nonmissing(
                ordered["total_studies_created_as_of_report_query_count"]
            )
        ),
        "other_study_memberships_as_of_report_query_count": _nullable_int(
            _latest_nonmissing(
                ordered["other_study_memberships_as_of_report_query_count"]
            )
        ),
        "distinct_login_days_as_of_report_query_count": _nullable_int(
            _latest_nonmissing(ordered["distinct_login_days_as_of_report_query_count"])
        ),
        "first_login_timestamp_as_of_report_query": _latest_nonmissing(
            ordered["first_login_timestamp_as_of_report_query"]
        ),
        "latest_login_timestamp_as_of_report_query": _latest_nonmissing(
            ordered["latest_login_timestamp_as_of_report_query"]
        ),
        "login_history_span_days_as_of_report_query": _latest_nonmissing(
            ordered["login_history_span_days_as_of_report_query"]
        ),
        "distinct_study_count_with_any_attempt": int(ordered["study_num"].nunique()),
        "distinct_completed_study_count_authored": int(
            authored_completed["study_num"].nunique()
        ),
        "distinct_study_count_eventually_created": len(
            {str(value) for value in ordered["study_num"]} & completed_studies
        ),
        "distinct_study_count_with_any_ai_attempt": int(
            sum(_AI in modes for modes in study_modes.values())
        ),
        "distinct_study_count_with_any_manual_attempt": int(
            sum(_MANUAL in modes for modes in study_modes.values())
        ),
        "distinct_study_count_with_both_modes": int(
            sum(_AI in modes and _MANUAL in modes for modes in study_modes.values())
        ),
        "completed_ai_study_count_authored": int(
            authored_completed["attempt_authoring_mode"].eq(_AI).sum()
        ),
        "completed_manual_study_count_authored": int(
            authored_completed["attempt_authoring_mode"].eq(_MANUAL).sum()
        ),
        "all_attempt_count": len(ordered),
        "ai_attempt_count": _mode_count(ordered, mode=_AI),
        "manual_attempt_count": _mode_count(ordered, mode=_MANUAL),
        "ai_error_attempt_count": _result_count(
            ordered,
            result=_AI_ERROR,
        ),
        "ai_error_without_stack_trace_attempt_count": _result_count(
            ordered,
            result=_AI_ERROR_WITHOUT_STACK_TRACE,
        ),
        "user_dropped_attempt_count": _result_count(
            ordered,
            result=_USER_DROPPED,
        ),
    }


def _derive_author_history(
    attempt_history: pd.DataFrame,
    study_history: pd.DataFrame,
) -> pd.DataFrame:
    """Return one history row per exact source author username."""
    completed_studies = frozenset(
        str(value)
        for value in study_history.loc[
            study_history["study_is_completed"].eq(True),
            "study_num",
        ]
    )
    rows = [
        _author_history_row(
            group,
            completed_studies=completed_studies,
        )
        for _, group in attempt_history.groupby(
            "attempt_author_user_name",
            sort=False,
            dropna=False,
        )
    ]

    return pd.DataFrame.from_records(
        rows,
        columns=list(_AUTHOR_HISTORY_COLUMNS),
    )


def derive_attempt_histories(
    records: pd.DataFrame,
) -> AttemptHistoryTables:
    """Derive attempt-, study-, and author-grain audit histories."""
    _require_validated_records(records)
    attempt_history = _derive_attempt_history(records)
    study_history = _derive_study_history(attempt_history)
    author_history = _derive_author_history(
        attempt_history,
        study_history,
    )

    return AttemptHistoryTables(
        study_attempt_author_history=attempt_history,
        study_attempt_history=study_history,
        author_history=author_history,
    )
