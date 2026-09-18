"""Tests for identifier-free data-quality summaries."""

from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from study_posting_audit_exploration import (
    AppointmentQualityFinding,
    ExplorationInputConfig,
    LoadedAuditReport,
    derive_attempt_histories,
    load_audit_report,
)
from study_posting_audit_exploration.quality import (
    DATA_QUALITY_SUMMARY_COLUMNS,
    build_data_quality_summary,
)


def _loaded_report(path: Path) -> LoadedAuditReport:
    """Return the synthetic validated-report fixture."""
    return load_audit_report(
        ExplorationInputConfig(
            report_directory=path,
        )
    )


def _row(summary: pd.DataFrame, check_name: str) -> pd.Series:
    """Return one named quality row."""
    return summary.loc[summary["data_quality_check_name"].eq(check_name)].iloc[0]


def test_quality_summary_has_stable_order_and_schema(
    valid_report_directory: Path,
) -> None:
    """Publish every required quality check in deterministic order."""
    report = _loaded_report(valid_report_directory)
    summary = build_data_quality_summary(
        report=report,
        histories=derive_attempt_histories(report.records),
    )

    assert tuple(summary.columns) == DATA_QUALITY_SUMMARY_COLUMNS
    assert summary["data_quality_check_name"].tolist() == [
        "DUPLICATE_AUDIT_ID",
        "MISSING_STUDY_NUMBER",
        "MISSING_AUTHOR_USERNAME",
        "MULTIPLE_COMPLETE_ATTEMPTS_PER_STUDY",
        "ATTEMPT_AFTER_COMPLETION",
        "COMPLETED_ATTEMPT_MISSING_END_TIME",
        "COMPLETED_ATTEMPT_MISSING_CREATED_BY_ID",
        "COMPLETED_ATTEMPT_MISSING_CREATED_DATE",
        "COMPLETED_ATTEMPT_MISSING_STUDY_DEPARTMENT",
        "COMPLETED_ATTEMPT_CREATOR_MISMATCH",
        "CREATED_BY_ID_VARIES_WITHIN_STUDY",
        "ORPHAN_AI_ASSISTANCE_METRIC_ROW",
        "ORPHAN_READABILITY_METRIC_ROW",
        "MALFORMED_APPOINTMENT",
        "NONFINITE_METRIC",
        "SELECTED_MARKER_INCONSISTENCY",
    ]
    assert set(summary["severity_level"]) == {"FATAL", "WARNING"}


def test_fatal_checks_are_zero_after_successful_validation(
    valid_report_directory: Path,
) -> None:
    """Represent fail-fast guarantees as zero rows in published output."""
    report = _loaded_report(valid_report_directory)
    summary = build_data_quality_summary(
        report=report,
        histories=derive_attempt_histories(report.records),
    )
    fatal = summary.loc[summary["severity_level"].eq("FATAL")]

    assert fatal["affected_attempt_count"].eq(0).all()
    assert fatal["affected_distinct_study_count"].eq(0).all()
    assert fatal["affected_distinct_author_count"].eq(0).all()
    assert fatal["analysis_consequence"].str.contains("stops validation").all()


def test_attempt_after_completion_counts_affected_attempts(
    valid_report_directory: Path,
) -> None:
    """Count each attempt occurring after the unique completed attempt."""
    report = _loaded_report(valid_report_directory)
    records = report.records.copy()
    completed = records.loc[records["ATTEMPT_RESULT"].eq("COMPLETE")].iloc[0]
    later = records.iloc[[0]].copy()
    later["ID"] = 999
    later["STUDY_NUM"] = completed["STUDY_NUM"]
    later["AUTHOR_USER_NAME"] = "synthetic-later-author"
    later["START_TIME"] = completed["START_TIME"] + pd.Timedelta(minutes=5)
    records = pd.concat([records, later], ignore_index=True)
    report = replace(report, records=records)

    summary = build_data_quality_summary(
        report=report,
        histories=derive_attempt_histories(records),
    )
    row = _row(summary, "ATTEMPT_AFTER_COMPLETION")

    assert row["affected_attempt_count"] == 1
    assert row["affected_distinct_study_count"] == 1
    assert row["affected_distinct_author_count"] == 1
    assert row["eligible_attempt_count"] == 3
    assert row["affected_attempt_percentage"] == pytest.approx(100.0 / 3.0)


def test_creator_variation_counts_all_attempts_in_affected_study(
    valid_report_directory: Path,
) -> None:
    """Flag every attempt in a study with inconsistent creator IDs."""
    report = _loaded_report(valid_report_directory)
    records = report.records.copy()
    records.loc[0, "CREATED_BY_ID"] = 777
    report = replace(report, records=records)

    summary = build_data_quality_summary(
        report=report,
        histories=derive_attempt_histories(records),
    )
    row = _row(summary, "CREATED_BY_ID_VARIES_WITHIN_STUDY")

    assert row["affected_attempt_count"] == 2
    assert row["affected_distinct_study_count"] == 1
    assert row["affected_distinct_author_count"] == 2
    assert row["eligible_attempt_count"] == 2
    assert row["affected_attempt_percentage"] == 100.0


def test_malformed_appointments_deduplicate_attempts(
    valid_report_directory: Path,
) -> None:
    """Count one attempt once even when it has several malformed entries."""
    report = _loaded_report(valid_report_directory)
    audit_id = int(report.records.iloc[0]["ID"])
    findings = (
        AppointmentQualityFinding(
            audit_record_id=audit_id,
            appointment_source="AUTHOR",
            appointment_index=0,
            issue_name="MALFORMED_APPOINTMENT",
        ),
        AppointmentQualityFinding(
            audit_record_id=audit_id,
            appointment_source="PI",
            appointment_index=1,
            issue_name="MALFORMED_APPOINTMENT",
        ),
    )

    summary = build_data_quality_summary(
        report=report,
        histories=derive_attempt_histories(report.records),
        appointment_quality_findings=findings,
    )
    row = _row(summary, "MALFORMED_APPOINTMENT")

    assert row["affected_attempt_count"] == 1
    assert row["affected_distinct_study_count"] == 1
    assert row["affected_distinct_author_count"] == 1
    assert row["eligible_attempt_count"] == 2
    assert row["affected_attempt_percentage"] == 50.0


def test_quality_summary_is_identifier_free(
    valid_report_directory: Path,
) -> None:
    """Never publish source identity columns or values."""
    report = _loaded_report(valid_report_directory)
    summary = build_data_quality_summary(
        report=report,
        histories=derive_attempt_histories(report.records),
    )
    published = summary.to_csv(index=False, lineterminator="\n")

    for forbidden_column in (
        "audit_record_id",
        "study_num",
        "author_user_name",
    ):
        assert forbidden_column not in summary.columns

    for forbidden_value in (
        str(report.records.iloc[0]["STUDY_NUM"]),
        str(report.records.iloc[0]["AUTHOR_USER_NAME"]),
    ):
        assert forbidden_value not in published


def test_warning_occurrence_count_sums_warning_affected_attempts(
    valid_report_directory: Path,
) -> None:
    """Define manifest warning count as summed warning-check occurrences."""
    report = _loaded_report(valid_report_directory)
    records = report.records.copy()
    records.loc[0, "CREATED_BY_ID"] = 777
    report = replace(report, records=records)
    audit_id = int(records.iloc[0]["ID"])
    findings = (
        AppointmentQualityFinding(
            audit_record_id=audit_id,
            appointment_source="AUTHOR",
            appointment_index=0,
            issue_name="MALFORMED_APPOINTMENT",
        ),
    )
    summary = build_data_quality_summary(
        report=report,
        histories=derive_attempt_histories(records),
        appointment_quality_findings=findings,
    )

    warning_occurrences = int(
        summary.loc[
            summary["severity_level"].eq("WARNING"),
            "affected_attempt_count",
        ].sum()
    )

    assert warning_occurrences == 3
