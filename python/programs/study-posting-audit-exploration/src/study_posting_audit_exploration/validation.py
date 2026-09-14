"""Validation of loaded normalized audit-report inputs."""

import math

import pandas as pd

from study_posting_audit_exploration.errors import ExplorationValidationError
from study_posting_audit_exploration.input_contracts import (
    AI_ASSISTANCE_FLOAT_COLUMNS,
    READABILITY_FLOAT_COLUMNS,
)
from study_posting_audit_exploration.models import (
    LoadedAuditReport,
    ValidationSummary,
)

_COMPLETE = "COMPLETE"
_AI = "AI"
_MANUAL = "MANUAL"

_AI_ANALYSIS_TYPES = frozenset(
    {
        "TEXT",
        "COMPENSATION",
        "LOOKUP",
    }
)
_AI_MATCH_TYPES = frozenset(
    {
        "EXACT",
        "COSMETIC_EQUIVALENT",
        "EDITED",
        "REMOVED",
        "UNASSISTED",
    }
)
_TEXT_ANALYSIS_TYPES = frozenset(
    {
        "TEXT",
        "COMPENSATION",
    }
)
_READABILITY_TEXT_ROLES = frozenset(
    {
        "SUGGESTED",
        "FINAL",
    }
)
_BOOLEAN_TEXT_VALUES = frozenset(
    {
        "true",
        "false",
    }
)


def _nonblank_mask(series: pd.Series) -> pd.Series:
    """Return whether nullable-string values are present and nonblank."""
    return series.notna() & series.str.strip().ne("")


def _normalized_strings(series: pd.Series) -> pd.Series:
    """Return lowercase string values while preserving nulls."""
    return series.astype("string").str.lower()


def _require_unique_attempt_ids(records: pd.DataFrame) -> None:
    """Require non-null, unique audit IDs."""
    if records["ID"].isna().any():
        raise ExplorationValidationError("records.csv contains a null audit ID")

    duplicate_count = int(records["ID"].duplicated(keep=False).sum())

    if duplicate_count:
        raise ExplorationValidationError(
            f"records.csv contains duplicate audit IDs: {duplicate_count} affected rows"
        )


def _require_study_and_author(records: pd.DataFrame) -> None:
    """Require study and attempt-author identity."""
    missing_studies = int((~_nonblank_mask(records["STUDY_NUM"])).sum())

    if missing_studies:
        raise ExplorationValidationError(
            "records.csv contains missing study numbers: "
            f"{missing_studies} affected rows"
        )

    missing_authors = int((~_nonblank_mask(records["AUTHOR_USER_NAME"])).sum())

    if missing_authors:
        raise ExplorationValidationError(
            "records.csv contains missing author usernames: "
            f"{missing_authors} affected rows"
        )


def _require_attempt_vocabularies(records: pd.DataFrame) -> None:
    """Require supported attempt modes and nonblank result values."""
    invalid_modes = sorted(
        str(value)
        for value in records.loc[
            ~records["ATTEMPT_TYPE"].isin((_AI, _MANUAL)),
            "ATTEMPT_TYPE",
        ]
        .dropna()
        .unique()
    )

    if invalid_modes or records["ATTEMPT_TYPE"].isna().any():
        raise ExplorationValidationError(
            f"records.csv contains unsupported attempt types: {invalid_modes!r}"
        )

    missing_results = int((~_nonblank_mask(records["ATTEMPT_RESULT"])).sum())

    if missing_results:
        raise ExplorationValidationError(
            "records.csv contains missing attempt results: "
            f"{missing_results} affected rows"
        )


def _require_unique_completion_per_study(records: pd.DataFrame) -> None:
    """Require at most one complete attempt for each study."""
    completed = records.loc[records["ATTEMPT_RESULT"].eq(_COMPLETE)]
    completion_counts = completed.groupby(
        "STUDY_NUM",
        dropna=False,
    ).size()
    violating_study_count = int((completion_counts > 1).sum())

    if violating_study_count:
        raise ExplorationValidationError(
            "records.csv contains studies with multiple completed attempts: "
            f"{violating_study_count} affected studies"
        )


def _require_completed_values(records: pd.DataFrame) -> None:
    """Require values implied by completed study creation."""
    completed = records.loc[records["ATTEMPT_RESULT"].eq(_COMPLETE)]

    requirements = (
        ("END_TIME", "completion time"),
        ("CREATED_BY_ID", "created-by ID"),
        ("CREATED_DATE", "created date"),
    )

    for column_name, label in requirements:
        missing_count = int(completed[column_name].isna().sum())

        if missing_count:
            raise ExplorationValidationError(
                f"completed attempts contain missing {label}: "
                f"{missing_count} affected rows"
            )

    missing_department_count = int(
        (~_nonblank_mask(completed["STUDY_DEPARTMENT"])).sum()
    )

    if missing_department_count:
        raise ExplorationValidationError(
            "completed attempts contain missing study department: "
            f"{missing_department_count} affected rows"
        )

    comparable = completed.loc[
        completed["USER_ID"].notna() & completed["CREATED_BY_ID"].notna()
    ]
    mismatch_count = int(comparable["USER_ID"].ne(comparable["CREATED_BY_ID"]).sum())

    if mismatch_count:
        raise ExplorationValidationError(
            "completed attempts contain USER_ID and CREATED_BY_ID mismatches: "
            f"{mismatch_count} affected rows"
        )


def _require_metric_joins(
    records: pd.DataFrame,
    metrics: pd.DataFrame,
    *,
    file_name: str,
) -> None:
    """Require every metric row to reference an existing audit ID."""
    if metrics["record_id"].isna().any():
        raise ExplorationValidationError(f"{file_name} contains a null audit record ID")

    known_ids = set(records["ID"].dropna().astype(int))
    metric_ids = set(metrics["record_id"].dropna().astype(int))
    orphan_count = len(metric_ids - known_ids)

    if orphan_count:
        raise ExplorationValidationError(
            f"{file_name} contains audit IDs absent from records.csv: "
            f"{orphan_count} distinct IDs"
        )


def _require_finite_columns(
    frame: pd.DataFrame,
    *,
    column_names: tuple[str, ...],
    file_name: str,
) -> None:
    """Require every non-null metric number to be finite."""
    for column_name in column_names:
        non_null = frame[column_name].dropna()
        invalid_count = int(
            non_null.map(
                lambda value: not math.isfinite(float(value)),
            ).sum()
        )

        if invalid_count:
            raise ExplorationValidationError(
                f"{file_name} column {column_name!r} contains non-finite values: "
                f"{invalid_count} affected rows"
            )


def _require_supported_values(
    frame: pd.DataFrame,
    *,
    column_name: str,
    allowed_values: frozenset[str],
    file_name: str,
) -> None:
    """Require one non-null categorical column to use supported values."""
    values = frame[column_name]
    invalid_values = sorted(
        str(value)
        for value in values.loc[~values.isin(allowed_values)].dropna().unique()
    )

    if invalid_values or values.isna().any():
        raise ExplorationValidationError(
            f"{file_name} contains unsupported {column_name} values: {invalid_values!r}"
        )


def _require_ai_assistance_identity(ai_assistance: pd.DataFrame) -> None:
    """Require one named AI-assistance row per audit attempt and field."""
    missing_fields = int((~_nonblank_mask(ai_assistance["field_name"])).sum())

    if missing_fields:
        raise ExplorationValidationError(
            "ai_assistance_metrics.csv contains missing field names: "
            f"{missing_fields} affected rows"
        )

    duplicate_count = int(
        ai_assistance.duplicated(
            subset=[
                "record_id",
                "field_name",
            ],
            keep=False,
        ).sum()
    )

    if duplicate_count:
        raise ExplorationValidationError(
            "ai_assistance_metrics.csv contains duplicate audit-field identities: "
            f"{duplicate_count} affected rows"
        )


def _require_ai_assistance_ownership(
    records: pd.DataFrame,
    ai_assistance: pd.DataFrame,
) -> None:
    """Require metric rows to belong to completed AI attempts."""
    attempt_context = records.loc[
        :,
        [
            "ID",
            "ATTEMPT_TYPE",
            "ATTEMPT_RESULT",
        ],
    ].rename(columns={"ID": "record_id"})
    joined = ai_assistance.merge(
        attempt_context,
        on="record_id",
        how="left",
        validate="many_to_one",
    )
    invalid_count = int(
        (
            ~joined["ATTEMPT_TYPE"].eq(_AI) | ~joined["ATTEMPT_RESULT"].eq(_COMPLETE)
        ).sum()
    )

    if invalid_count:
        raise ExplorationValidationError(
            "ai_assistance_metrics.csv rows must belong to completed AI attempts: "
            f"{invalid_count} affected rows"
        )


def _require_boolean_text(
    frame: pd.DataFrame,
    *,
    column_name: str,
) -> None:
    """Require nullable lowercase-compatible Boolean text."""
    non_null = frame[column_name].notna()
    normalized = _normalized_strings(frame[column_name])
    invalid_count = int((non_null & ~normalized.isin(_BOOLEAN_TEXT_VALUES)).sum())

    if invalid_count:
        raise ExplorationValidationError(
            "ai_assistance_metrics.csv column "
            f"{column_name!r} must contain true, false, or null: "
            f"{invalid_count} affected rows"
        )


def _require_ai_assistance_relationships(ai_assistance: pd.DataFrame) -> None:
    """Require analysis-type, selection, and outcome relationships."""
    _require_supported_values(
        ai_assistance,
        column_name="analysis_type",
        allowed_values=_AI_ANALYSIS_TYPES,
        file_name="ai_assistance_metrics.csv",
    )
    _require_supported_values(
        ai_assistance,
        column_name="match_type",
        allowed_values=_AI_MATCH_TYPES,
        file_name="ai_assistance_metrics.csv",
    )

    for column_name in (
        "flag_suggested",
        "flag_saved",
        "flag_accepted",
        "flag_changed",
        "compensation_text_required",
    ):
        _require_boolean_text(
            ai_assistance,
            column_name=column_name,
        )

    text_rows = ai_assistance["analysis_type"].isin(_TEXT_ANALYSIS_TYPES)
    lookup_rows = ai_assistance["analysis_type"].eq("LOOKUP")
    unassisted = ai_assistance["match_type"].eq("UNASSISTED")
    assisted_text = text_rows & ~unassisted

    invalid_assisted_count = int(
        (
            assisted_text
            & (
                ai_assistance["picked_kind"].isna()
                | ai_assistance["picked_index"].isna()
            )
        ).sum()
    )

    if invalid_assisted_count:
        raise ExplorationValidationError(
            "assisted text AI metrics require picked_kind and picked_index: "
            f"{invalid_assisted_count} affected rows"
        )

    invalid_unassisted_count = int(
        (
            text_rows
            & unassisted
            & (
                ai_assistance["picked_kind"].notna()
                | ai_assistance["picked_index"].notna()
            )
        ).sum()
    )

    if invalid_unassisted_count:
        raise ExplorationValidationError(
            "unassisted text AI metrics must not contain a picked suggestion: "
            f"{invalid_unassisted_count} affected rows"
        )

    negative_picked_index_count = int(
        (
            ai_assistance["picked_index"].notna() & ai_assistance["picked_index"].lt(0)
        ).sum()
    )

    if negative_picked_index_count:
        raise ExplorationValidationError(
            "ai_assistance_metrics.csv contains negative picked indices: "
            f"{negative_picked_index_count} affected rows"
        )

    invalid_lookup_pick_count = int(
        (
            lookup_rows
            & (
                ai_assistance["picked_kind"].notna()
                | ai_assistance["picked_index"].notna()
            )
        ).sum()
    )

    if invalid_lookup_pick_count:
        raise ExplorationValidationError(
            "lookup AI metrics must not contain text suggestion picks: "
            f"{invalid_lookup_pick_count} affected rows"
        )


def _require_ai_assistance_contract(
    records: pd.DataFrame,
    ai_assistance: pd.DataFrame,
) -> None:
    """Require identities and relationships needed by field aggregation."""
    _require_ai_assistance_identity(ai_assistance)
    _require_ai_assistance_ownership(
        records,
        ai_assistance,
    )
    _require_ai_assistance_relationships(ai_assistance)


def _require_readability_contract(readability: pd.DataFrame) -> None:
    """Require valid text roles and selected-marker relationships."""
    invalid_roles = sorted(
        str(value)
        for value in readability.loc[
            ~readability["text_role"].isin(_READABILITY_TEXT_ROLES),
            "text_role",
        ]
        .dropna()
        .unique()
    )

    if invalid_roles or readability["text_role"].isna().any():
        raise ExplorationValidationError(
            "readability_metrics.csv contains unsupported text roles: "
            f"{invalid_roles!r}"
        )

    suggested = readability["text_role"].eq("SUGGESTED")
    final = readability["text_role"].eq("FINAL")
    selected_non_null = readability["selected"].notna()
    selected_values = set(
        _normalized_strings(readability.loc[selected_non_null, "selected"])
    )

    if not selected_values.issubset(_BOOLEAN_TEXT_VALUES):
        raise ExplorationValidationError(
            "readability_metrics.csv selected values must be true, false, or null"
        )

    invalid_suggested = int((suggested & ~selected_non_null).sum())

    if invalid_suggested:
        raise ExplorationValidationError(
            "readability suggestion rows require selected markers: "
            f"{invalid_suggested} affected rows"
        )

    invalid_final = int((final & selected_non_null).sum())

    if invalid_final:
        raise ExplorationValidationError(
            "readability final rows must not contain selected markers: "
            f"{invalid_final} affected rows"
        )

    duplicate_identity_count = int(
        readability.duplicated(
            subset=[
                "record_id",
                "field_name",
                "text_role",
                "suggestion_kind",
                "suggestion_index",
            ],
            keep=False,
        ).sum()
    )

    if duplicate_identity_count:
        raise ExplorationValidationError(
            "readability_metrics.csv contains duplicate text-instance identities: "
            f"{duplicate_identity_count} affected rows"
        )


def validate_audit_report(
    report: LoadedAuditReport,
) -> ValidationSummary:
    """Validate one loaded report and return non-sensitive counts."""
    records = report.records
    ai_assistance = report.ai_assistance_metrics
    readability = report.readability_metrics

    _require_unique_attempt_ids(records)
    _require_study_and_author(records)
    _require_attempt_vocabularies(records)
    _require_unique_completion_per_study(records)
    _require_completed_values(records)
    _require_metric_joins(
        records,
        ai_assistance,
        file_name="ai_assistance_metrics.csv",
    )
    _require_metric_joins(
        records,
        readability,
        file_name="readability_metrics.csv",
    )
    _require_finite_columns(
        ai_assistance,
        column_names=AI_ASSISTANCE_FLOAT_COLUMNS,
        file_name="ai_assistance_metrics.csv",
    )
    _require_finite_columns(
        readability,
        column_names=READABILITY_FLOAT_COLUMNS,
        file_name="readability_metrics.csv",
    )
    _require_ai_assistance_contract(
        records,
        ai_assistance,
    )
    _require_readability_contract(readability)

    completed_count = int(records["ATTEMPT_RESULT"].eq(_COMPLETE).sum())

    return ValidationSummary(
        record_attempt_count=len(records),
        distinct_study_count=int(records["STUDY_NUM"].nunique(dropna=True)),
        completed_attempt_count=completed_count,
        incomplete_attempt_count=len(records) - completed_count,
        ai_assistance_metric_row_count=len(ai_assistance),
        readability_metric_row_count=len(readability),
    )
