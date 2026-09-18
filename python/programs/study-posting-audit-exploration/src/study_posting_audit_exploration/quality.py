"""Identifier-free data-quality summary for validated exploration input."""

from dataclasses import dataclass

import pandas as pd

from study_posting_audit_exploration.models import (
    AppointmentQualityFinding,
    AttemptHistoryTables,
    LoadedAuditReport,
)

DATA_QUALITY_SUMMARY_COLUMNS: tuple[str, ...] = (
    "data_quality_check_name",
    "severity_level",
    "affected_attempt_count",
    "affected_distinct_study_count",
    "affected_distinct_author_count",
    "eligible_attempt_count",
    "affected_attempt_percentage",
    "check_definition",
    "analysis_consequence",
)

_FATAL = "FATAL"
_WARNING = "WARNING"
_COMPLETE = "COMPLETE"


@dataclass(frozen=True, slots=True)
class _QualityCheck:
    """One ordered quality-check definition."""

    name: str
    severity: str
    definition: str
    consequence: str


_CHECKS: tuple[_QualityCheck, ...] = (
    _QualityCheck(
        "DUPLICATE_AUDIT_ID",
        _FATAL,
        "Audit attempt IDs must be unique and nonmissing.",
        "Any detected case stops validation and prevents publication.",
    ),
    _QualityCheck(
        "MISSING_STUDY_NUMBER",
        _FATAL,
        "Every audit attempt must have a nonblank study number.",
        "Any detected case stops validation and prevents study-grain analysis.",
    ),
    _QualityCheck(
        "MISSING_AUTHOR_USERNAME",
        _FATAL,
        "Every audit attempt must have a nonblank attempt-author username.",
        "Any detected case stops validation and prevents author-grain analysis.",
    ),
    _QualityCheck(
        "MULTIPLE_COMPLETE_ATTEMPTS_PER_STUDY",
        _FATAL,
        "A study may have no more than one completed attempt.",
        "Any detected case stops validation and prevents unique-completion analysis.",
    ),
    _QualityCheck(
        "ATTEMPT_AFTER_COMPLETION",
        _WARNING,
        "An attempt starts after the same study's unique completed attempt.",
        "Affected attempts are retained, but study histories require review.",
    ),
    _QualityCheck(
        "COMPLETED_ATTEMPT_MISSING_END_TIME",
        _FATAL,
        "Every completed attempt must have an end timestamp.",
        "Any detected case stops validation and prevents publication.",
    ),
    _QualityCheck(
        "COMPLETED_ATTEMPT_MISSING_CREATED_BY_ID",
        _FATAL,
        "Every completed attempt must identify the created-study user.",
        "Any detected case stops validation and prevents publication.",
    ),
    _QualityCheck(
        "COMPLETED_ATTEMPT_MISSING_CREATED_DATE",
        _FATAL,
        "Every completed attempt must have a created date.",
        "Any detected case stops validation and prevents publication.",
    ),
    _QualityCheck(
        "COMPLETED_ATTEMPT_MISSING_STUDY_DEPARTMENT",
        _FATAL,
        "Every completed attempt must have a nonblank study department.",
        "Any detected case stops validation and prevents publication.",
    ),
    _QualityCheck(
        "COMPLETED_ATTEMPT_CREATOR_MISMATCH",
        _FATAL,
        "A completed attempt's USER_ID must equal its CREATED_BY_ID when comparable.",
        "Any detected case stops validation and prevents publication.",
    ),
    _QualityCheck(
        "CREATED_BY_ID_VARIES_WITHIN_STUDY",
        _WARNING,
        "Nonmissing CREATED_BY_ID values should remain constant within a study.",
        (
            "Affected studies are retained, but creator-linked interpretation "
            "requires review."
        ),
    ),
    _QualityCheck(
        "ORPHAN_AI_ASSISTANCE_METRIC_ROW",
        _FATAL,
        "Every AI-assistance metric row must reference an existing audit attempt.",
        "Any detected case stops validation and prevents publication.",
    ),
    _QualityCheck(
        "ORPHAN_READABILITY_METRIC_ROW",
        _FATAL,
        "Every readability metric row must reference an existing audit attempt.",
        "Any detected case stops validation and prevents publication.",
    ),
    _QualityCheck(
        "MALFORMED_APPOINTMENT",
        _WARNING,
        "Appointment entries must parse as Title:Department:School.",
        "Malformed entries are excluded from parsed appointment groups.",
    ),
    _QualityCheck(
        "NONFINITE_METRIC",
        _FATAL,
        "Every nonmissing numeric metric must be finite.",
        "Any detected case stops validation and prevents publication.",
    ),
    _QualityCheck(
        "SELECTED_MARKER_INCONSISTENCY",
        _FATAL,
        "Readability selected markers must agree with text role and AI picks.",
        "Any detected case stops validation and prevents publication.",
    ),
)


def _percentage(numerator: int, denominator: int) -> float | None:
    """Return a percentage or None for an empty denominator."""
    if denominator == 0:
        return None

    return 100.0 * numerator / denominator


def _affected_counts(
    affected: pd.DataFrame,
) -> tuple[int, int, int]:
    """Return distinct affected attempts, studies, and authors."""
    return (
        int(affected["ID"].nunique(dropna=True)),
        int(affected["STUDY_NUM"].nunique(dropna=True)),
        int(affected["AUTHOR_USER_NAME"].nunique(dropna=True)),
    )


def _attempts_after_completion(
    records: pd.DataFrame,
    histories: AttemptHistoryTables,
) -> pd.DataFrame:
    """Return source attempts occurring after their study's completion."""
    affected_studies = histories.study_attempt_history.loc[
        histories.study_attempt_history["has_attempt_after_completion"].eq(True),
        [
            "study_num",
            "completed_attempt_start_timestamp",
        ],
    ]

    if affected_studies.empty:
        return records.iloc[0:0]

    return records.merge(
        affected_studies,
        left_on="STUDY_NUM",
        right_on="study_num",
        how="inner",
        validate="many_to_one",
    ).loc[
        lambda frame: frame["START_TIME"].gt(frame["completed_attempt_start_timestamp"])
    ]


def _creator_variation_attempts(records: pd.DataFrame) -> pd.DataFrame:
    """Return all attempts in studies with varying nonmissing creator IDs."""
    creator_counts = records.groupby(
        "STUDY_NUM",
        dropna=False,
    )["CREATED_BY_ID"].nunique(dropna=True)
    affected_studies = creator_counts.loc[creator_counts.gt(1)].index

    return records.loc[records["STUDY_NUM"].isin(affected_studies)]


def _malformed_appointment_attempts(
    records: pd.DataFrame,
    findings: tuple[AppointmentQualityFinding, ...],
) -> pd.DataFrame:
    """Return attempts represented by malformed appointment findings."""
    affected_ids = {finding.audit_record_id for finding in findings}

    return records.loc[records["ID"].isin(affected_ids)]


def _eligible_attempt_count(
    check_name: str,
    report: LoadedAuditReport,
) -> int:
    """Return the attempt-level denominator for one quality check."""
    records = report.records
    completed_count = int(records["ATTEMPT_RESULT"].eq(_COMPLETE).sum())

    if check_name.startswith("COMPLETED_ATTEMPT_"):
        return completed_count

    if check_name == "ORPHAN_AI_ASSISTANCE_METRIC_ROW":
        return int(report.ai_assistance_metrics["record_id"].nunique(dropna=True))

    if check_name in {
        "ORPHAN_READABILITY_METRIC_ROW",
        "SELECTED_MARKER_INCONSISTENCY",
    }:
        return int(report.readability_metrics["record_id"].nunique(dropna=True))

    if check_name == "NONFINITE_METRIC":
        metric_ids = pd.concat(
            [
                report.ai_assistance_metrics["record_id"],
                report.readability_metrics["record_id"],
            ],
            ignore_index=True,
        )
        return int(metric_ids.nunique(dropna=True))

    return len(records)


def _affected_attempts(
    check_name: str,
    *,
    report: LoadedAuditReport,
    histories: AttemptHistoryTables,
    appointment_quality_findings: tuple[AppointmentQualityFinding, ...],
) -> pd.DataFrame:
    """Return affected source attempts for one check on validated input."""
    if check_name == "ATTEMPT_AFTER_COMPLETION":
        return _attempts_after_completion(report.records, histories)

    if check_name == "CREATED_BY_ID_VARIES_WITHIN_STUDY":
        return _creator_variation_attempts(report.records)

    if check_name == "MALFORMED_APPOINTMENT":
        return _malformed_appointment_attempts(
            report.records,
            appointment_quality_findings,
        )

    return report.records.iloc[0:0]


def build_data_quality_summary(
    *,
    report: LoadedAuditReport,
    histories: AttemptHistoryTables,
    appointment_quality_findings: tuple[AppointmentQualityFinding, ...] = (),
) -> pd.DataFrame:
    """Return deterministic identifier-free quality rows for validated input."""
    rows: list[dict[str, object]] = []

    for check in _CHECKS:
        affected = _affected_attempts(
            check.name,
            report=report,
            histories=histories,
            appointment_quality_findings=appointment_quality_findings,
        )
        attempt_count, study_count, author_count = _affected_counts(affected)
        eligible_count = _eligible_attempt_count(check.name, report)

        rows.append(
            {
                "data_quality_check_name": check.name,
                "severity_level": check.severity,
                "affected_attempt_count": attempt_count,
                "affected_distinct_study_count": study_count,
                "affected_distinct_author_count": author_count,
                "eligible_attempt_count": eligible_count,
                "affected_attempt_percentage": _percentage(
                    attempt_count,
                    eligible_count,
                ),
                "check_definition": check.definition,
                "analysis_consequence": check.consequence,
            }
        )

    return pd.DataFrame.from_records(
        rows,
        columns=list(DATA_QUALITY_SUMMARY_COLUMNS),
    )
