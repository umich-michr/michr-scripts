"""Identifier-bearing warning findings for authorized internal investigation."""

import pandas as pd

from study_posting_audit_exploration.errors import ExplorationValidationError
from study_posting_audit_exploration.models import (
    AppointmentQualityFinding,
    AttemptHistoryTables,
    LoadedAuditReport,
)
from study_posting_audit_exploration.quality import (
    DATA_QUALITY_ANALYSIS_CONSEQUENCES,
    DATA_QUALITY_CHECK_SEVERITIES,
)

DATA_QUALITY_FINDING_COLUMNS: tuple[str, ...] = (
    "data_quality_check_name",
    "severity_level",
    "audit_record_id",
    "study_num",
    "attempt_author_user_name",
    "finding_source",
    "finding_position",
    "finding_detail_code",
    "analysis_consequence",
)

_ATTEMPT_AFTER_COMPLETION = "ATTEMPT_AFTER_COMPLETION"
_CREATOR_VARIATION = "CREATED_BY_ID_VARIES_WITHIN_STUDY"
_MALFORMED_APPOINTMENT = "MALFORMED_APPOINTMENT"

_CHECK_ORDER: dict[str, int] = {
    _ATTEMPT_AFTER_COMPLETION: 0,
    _CREATOR_VARIATION: 1,
    _MALFORMED_APPOINTMENT: 2,
}

_FINDING_DTYPES: dict[str, str] = {
    "data_quality_check_name": "string",
    "severity_level": "string",
    "audit_record_id": "Int64",
    "study_num": "string",
    "attempt_author_user_name": "string",
    "finding_source": "string",
    "finding_position": "Int64",
    "finding_detail_code": "string",
    "analysis_consequence": "string",
}


def _empty_findings() -> pd.DataFrame:
    """Return an empty findings table with stable columns and dtypes."""
    return pd.DataFrame(columns=list(DATA_QUALITY_FINDING_COLUMNS)).astype(
        _FINDING_DTYPES
    )


def _warning_row(
    *,
    check_name: str,
    audit_record_id: int,
    study_num: object,
    author_user_name: object,
    finding_source: str,
    finding_position: int | None,
    finding_detail_code: str,
) -> dict[str, object]:
    """Return one warning finding row."""
    severity = DATA_QUALITY_CHECK_SEVERITIES[check_name]

    if severity != "WARNING":
        raise ExplorationValidationError(
            f"Data-quality finding check {check_name!r} must be a warning"
        )

    return {
        "data_quality_check_name": check_name,
        "severity_level": severity,
        "audit_record_id": audit_record_id,
        "study_num": study_num,
        "attempt_author_user_name": author_user_name,
        "finding_source": finding_source,
        "finding_position": finding_position,
        "finding_detail_code": finding_detail_code,
        "analysis_consequence": DATA_QUALITY_ANALYSIS_CONSEQUENCES[check_name],
    }


def _attempt_after_completion_rows(
    report: LoadedAuditReport,
    histories: AttemptHistoryTables,
) -> list[dict[str, object]]:
    """Return one finding per attempt after unique study completion."""
    completed_studies = histories.study_attempt_history.loc[
        histories.study_attempt_history["has_attempt_after_completion"].eq(True),
        [
            "study_num",
            "completed_attempt_start_timestamp",
        ],
    ]

    if completed_studies.empty:
        return []

    affected = report.records.merge(
        completed_studies,
        left_on="STUDY_NUM",
        right_on="study_num",
        how="inner",
        validate="many_to_one",
    ).loc[
        lambda frame: frame["START_TIME"].gt(frame["completed_attempt_start_timestamp"])
    ]

    return [
        _warning_row(
            check_name=_ATTEMPT_AFTER_COMPLETION,
            audit_record_id=int(row["ID"]),
            study_num=row["STUDY_NUM"],
            author_user_name=row["AUTHOR_USER_NAME"],
            finding_source="ATTEMPT_HISTORY",
            finding_position=None,
            finding_detail_code="ATTEMPT_STARTS_AFTER_UNIQUE_COMPLETION",
        )
        for row in affected.to_dict(orient="records")
    ]


def _creator_variation_rows(
    report: LoadedAuditReport,
) -> list[dict[str, object]]:
    """Return one finding per attempt in a creator-inconsistent study."""
    records = report.records
    creator_counts = records.groupby(
        "STUDY_NUM",
        dropna=False,
    )["CREATED_BY_ID"].nunique(dropna=True)
    affected_studies = creator_counts.loc[creator_counts.gt(1)].index
    affected = records.loc[records["STUDY_NUM"].isin(affected_studies)]

    return [
        _warning_row(
            check_name=_CREATOR_VARIATION,
            audit_record_id=int(row["ID"]),
            study_num=row["STUDY_NUM"],
            author_user_name=row["AUTHOR_USER_NAME"],
            finding_source="STUDY_CREATOR",
            finding_position=None,
            finding_detail_code=("MULTIPLE_NONMISSING_CREATED_BY_IDS_WITHIN_STUDY"),
        )
        for row in affected.to_dict(orient="records")
    ]


def _appointment_finding_rows(
    report: LoadedAuditReport,
    findings: tuple[AppointmentQualityFinding, ...],
) -> list[dict[str, object]]:
    """Return one finding per malformed appointment entry."""
    if not findings:
        return []

    record_context = report.records.loc[
        :,
        [
            "ID",
            "STUDY_NUM",
            "AUTHOR_USER_NAME",
        ],
    ]
    context_by_id = {
        int(row["ID"]): row for row in record_context.to_dict(orient="records")
    }
    rows: list[dict[str, object]] = []

    for finding in findings:
        context = context_by_id.get(finding.audit_record_id)

        if context is None:
            raise ExplorationValidationError(
                "Appointment quality finding references an unknown audit record"
            )

        source = {
            "AUTHOR": "AUTHOR_APPOINTMENT",
            "PI": "PI_APPOINTMENT",
        }.get(finding.appointment_source)

        if source is None:
            raise ExplorationValidationError(
                "Appointment quality finding has an unsupported source"
            )

        rows.append(
            _warning_row(
                check_name=_MALFORMED_APPOINTMENT,
                audit_record_id=finding.audit_record_id,
                study_num=context["STUDY_NUM"],
                author_user_name=context["AUTHOR_USER_NAME"],
                finding_source=source,
                finding_position=finding.appointment_index,
                finding_detail_code=finding.issue_name,
            )
        )

    return rows


def build_data_quality_findings(
    *,
    report: LoadedAuditReport,
    histories: AttemptHistoryTables,
    appointment_quality_findings: tuple[AppointmentQualityFinding, ...] = (),
) -> pd.DataFrame:
    """Return deterministic identifier-bearing findings for warning checks."""
    rows = [
        *_attempt_after_completion_rows(report, histories),
        *_creator_variation_rows(report),
        *_appointment_finding_rows(
            report,
            appointment_quality_findings,
        ),
    ]

    if not rows:
        return _empty_findings()

    output = pd.DataFrame.from_records(
        rows,
        columns=list(DATA_QUALITY_FINDING_COLUMNS),
    ).astype(_FINDING_DTYPES)
    output = output.drop_duplicates(
        subset=[
            "data_quality_check_name",
            "audit_record_id",
            "finding_source",
            "finding_position",
            "finding_detail_code",
        ],
        keep="first",
    )
    output["_check_order"] = output["data_quality_check_name"].map(_CHECK_ORDER)

    return (
        output.sort_values(
            by=[
                "_check_order",
                "audit_record_id",
                "finding_source",
                "finding_position",
                "finding_detail_code",
            ],
            kind="stable",
            na_position="last",
        )
        .drop(columns=["_check_order"])
        .reset_index(drop=True)
    )
