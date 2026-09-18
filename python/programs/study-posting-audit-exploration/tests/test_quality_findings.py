"""Tests for identifier-bearing internal data-quality findings."""

from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from study_posting_audit_exploration import (
    AppointmentQualityFinding,
    ExplorationInputConfig,
    ExplorationValidationError,
    LoadedAuditReport,
    derive_attempt_histories,
    load_audit_report,
)
from study_posting_audit_exploration.quality import (
    build_data_quality_summary,
)
from study_posting_audit_exploration.quality_findings import (
    DATA_QUALITY_FINDING_COLUMNS,
    build_data_quality_findings,
)


def _loaded_report(path: Path) -> LoadedAuditReport:
    """Return the synthetic normalized-report fixture."""
    return load_audit_report(
        ExplorationInputConfig(
            report_directory=path,
        )
    )


def test_empty_findings_have_stable_schema_and_dtypes(
    valid_report_directory: Path,
) -> None:
    """Return a stable header-only table when no warning is affected."""
    report = _loaded_report(valid_report_directory)

    findings = build_data_quality_findings(
        report=report,
        histories=derive_attempt_histories(report.records),
    )

    assert findings.empty
    assert tuple(findings.columns) == DATA_QUALITY_FINDING_COLUMNS
    assert str(findings["audit_record_id"].dtype) == "Int64"
    assert str(findings["finding_position"].dtype) == "Int64"


def test_attempt_after_completion_identifies_later_audit_record(
    valid_report_directory: Path,
) -> None:
    """Identify the exact attempt occurring after unique completion."""
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

    findings = build_data_quality_findings(
        report=report,
        histories=derive_attempt_histories(records),
    )
    row = findings.iloc[0]

    assert row["data_quality_check_name"] == "ATTEMPT_AFTER_COMPLETION"
    assert row["severity_level"] == "WARNING"
    assert row["audit_record_id"] == 999
    assert row["study_num"] == completed["STUDY_NUM"]
    assert row["attempt_author_user_name"] == "synthetic-later-author"
    assert row["finding_source"] == "ATTEMPT_HISTORY"
    assert pd.isna(row["finding_position"])
    assert row["finding_detail_code"] == ("ATTEMPT_STARTS_AFTER_UNIQUE_COMPLETION")


def test_creator_variation_identifies_every_attempt_in_study(
    valid_report_directory: Path,
) -> None:
    """Return each audit record in a creator-inconsistent study."""
    report = _loaded_report(valid_report_directory)
    records = report.records.copy()
    records.loc[0, "CREATED_BY_ID"] = 777
    report = replace(report, records=records)

    findings = build_data_quality_findings(
        report=report,
        histories=derive_attempt_histories(records),
    )

    assert (
        findings["data_quality_check_name"]
        .eq("CREATED_BY_ID_VARIES_WITHIN_STUDY")
        .all()
    )
    assert findings["audit_record_id"].tolist() == [1001, 1002]
    assert findings["finding_source"].eq("STUDY_CREATOR").all()
    assert findings["finding_position"].isna().all()
    assert (
        findings["finding_detail_code"]
        .eq("MULTIPLE_NONMISSING_CREATED_BY_IDS_WITHIN_STUDY")
        .all()
    )


def test_malformed_appointments_preserve_source_and_position(
    valid_report_directory: Path,
) -> None:
    """Return one row per malformed author or PI appointment entry."""
    report = _loaded_report(valid_report_directory)
    audit_id = int(report.records.iloc[0]["ID"])
    source_study = str(report.records.iloc[0]["STUDY_NUM"])
    source_author = str(report.records.iloc[0]["AUTHOR_USER_NAME"])
    appointment_findings = (
        AppointmentQualityFinding(
            audit_record_id=audit_id,
            appointment_source="PI",
            appointment_index=2,
            issue_name="MALFORMED_APPOINTMENT",
        ),
        AppointmentQualityFinding(
            audit_record_id=audit_id,
            appointment_source="AUTHOR",
            appointment_index=0,
            issue_name="MALFORMED_APPOINTMENT",
        ),
    )

    findings = build_data_quality_findings(
        report=report,
        histories=derive_attempt_histories(report.records),
        appointment_quality_findings=appointment_findings,
    )

    assert len(findings) == 2
    assert findings["audit_record_id"].tolist() == [audit_id, audit_id]
    assert findings["study_num"].eq(source_study).all()
    assert findings["attempt_author_user_name"].eq(source_author).all()
    assert findings["finding_source"].tolist() == [
        "AUTHOR_APPOINTMENT",
        "PI_APPOINTMENT",
    ]
    assert findings["finding_position"].tolist() == [0, 2]
    assert findings["finding_detail_code"].eq("MALFORMED_APPOINTMENT").all()
    assert "appointment_raw" not in findings.columns


def test_findings_use_stable_check_order(
    valid_report_directory: Path,
) -> None:
    """Order chronology, creator, and appointment findings deterministically."""
    report = _loaded_report(valid_report_directory)
    records = report.records.copy()
    completed = records.loc[records["ATTEMPT_RESULT"].eq("COMPLETE")].iloc[0]
    records.loc[0, "CREATED_BY_ID"] = 777
    later = records.iloc[[0]].copy()
    later["ID"] = 999
    later["STUDY_NUM"] = completed["STUDY_NUM"]
    later["START_TIME"] = completed["START_TIME"] + pd.Timedelta(minutes=5)
    records = pd.concat([records, later], ignore_index=True)
    report = replace(report, records=records)
    appointment_finding = AppointmentQualityFinding(
        audit_record_id=1001,
        appointment_source="AUTHOR",
        appointment_index=0,
        issue_name="MALFORMED_APPOINTMENT",
    )

    findings = build_data_quality_findings(
        report=report,
        histories=derive_attempt_histories(records),
        appointment_quality_findings=(appointment_finding,),
    )

    assert findings["data_quality_check_name"].tolist() == [
        "ATTEMPT_AFTER_COMPLETION",
        "CREATED_BY_ID_VARIES_WITHIN_STUDY",
        "CREATED_BY_ID_VARIES_WITHIN_STUDY",
        "CREATED_BY_ID_VARIES_WITHIN_STUDY",
        "MALFORMED_APPOINTMENT",
    ]


@pytest.mark.parametrize(
    ("appointment_source", "message"),
    [
        ("UNKNOWN", "unsupported source"),
    ],
)
def test_rejects_unsupported_appointment_source(
    valid_report_directory: Path,
    appointment_source: str,
    message: str,
) -> None:
    """Reject findings that cannot be mapped to a source field."""
    report = _loaded_report(valid_report_directory)
    finding = AppointmentQualityFinding(
        audit_record_id=int(report.records.iloc[0]["ID"]),
        appointment_source=appointment_source,
        appointment_index=0,
        issue_name="MALFORMED_APPOINTMENT",
    )

    with pytest.raises(
        ExplorationValidationError,
        match=message,
    ):
        build_data_quality_findings(
            report=report,
            histories=derive_attempt_histories(report.records),
            appointment_quality_findings=(finding,),
        )


def test_rejects_unknown_appointment_audit_record(
    valid_report_directory: Path,
) -> None:
    """Reject a finding that cannot be joined to source identity context."""
    report = _loaded_report(valid_report_directory)
    finding = AppointmentQualityFinding(
        audit_record_id=999999,
        appointment_source="AUTHOR",
        appointment_index=0,
        issue_name="MALFORMED_APPOINTMENT",
    )

    with pytest.raises(
        ExplorationValidationError,
        match="unknown audit record",
    ):
        build_data_quality_findings(
            report=report,
            histories=derive_attempt_histories(report.records),
            appointment_quality_findings=(finding,),
        )


def test_warning_aggregate_counts_match_distinct_finding_identities(
    valid_report_directory: Path,
) -> None:
    """Link warning aggregates to the restricted findings drill-down."""
    report = _loaded_report(valid_report_directory)
    records = report.records.copy()
    records.loc[0, "CREATED_BY_ID"] = 777
    report = replace(report, records=records)
    audit_id = int(records.iloc[0]["ID"])
    appointment_findings = (
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
    histories = derive_attempt_histories(records)
    details = build_data_quality_findings(
        report=report,
        histories=histories,
        appointment_quality_findings=appointment_findings,
    )
    summary = build_data_quality_summary(
        report=report,
        histories=histories,
        appointment_quality_findings=appointment_findings,
    )

    for check_name in (
        "CREATED_BY_ID_VARIES_WITHIN_STUDY",
        "MALFORMED_APPOINTMENT",
    ):
        aggregate = summary.loc[summary["data_quality_check_name"].eq(check_name)].iloc[
            0
        ]
        check_findings = details.loc[details["data_quality_check_name"].eq(check_name)]

        assert aggregate["affected_attempt_count"] == (
            check_findings["audit_record_id"].nunique()
        )
        assert aggregate["affected_distinct_study_count"] == (
            check_findings["study_num"].nunique()
        )
        assert aggregate["affected_distinct_author_count"] == (
            check_findings["attempt_author_user_name"].nunique()
        )

    malformed = details.loc[
        details["data_quality_check_name"].eq("MALFORMED_APPOINTMENT")
    ]
    assert len(malformed) == 2
    assert malformed["audit_record_id"].nunique() == 1


def test_exact_duplicate_appointment_findings_are_published_once(
    valid_report_directory: Path,
) -> None:
    """Deduplicate identical findings from repeated derivation paths."""
    report = _loaded_report(valid_report_directory)
    finding = AppointmentQualityFinding(
        audit_record_id=int(report.records.iloc[0]["ID"]),
        appointment_source="AUTHOR",
        appointment_index=0,
        issue_name="MALFORMED_APPOINTMENT",
    )

    findings = build_data_quality_findings(
        report=report,
        histories=derive_attempt_histories(report.records),
        appointment_quality_findings=(finding, finding),
    )

    assert len(findings) == 1
    assert findings.iloc[0]["audit_record_id"] == finding.audit_record_id
