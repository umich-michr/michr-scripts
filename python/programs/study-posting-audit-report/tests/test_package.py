"""Tests for the study-posting-audit-report package contract."""

from pathlib import Path
from typing import cast

import pytest

import study_posting_audit_report as package
from study_posting_audit_report import (
    FIELD_METRICS_FILENAME,
    RECORDS_FILENAME,
    AuditColumnMapping,
    AuditCsvReport,
    AuditOutputError,
    AuditReportConfig,
    AuditReportConfigurationError,
    AuditReportError,
    AuditReportSummary,
    AuditRowError,
    AuditSourceError,
    CsvOutputOptions,
    PayloadState,
    ProcessedAuditRow,
    analyze_audit_row,
    classify_payload_state,
    extract_record_id,
    generate_csv_report,
    process_audit_rows,
    serialize_csv_value,
    validate_source_schema,
)


def test_package_is_not_an_implicit_namespace() -> None:
    assert package.__file__ is not None


def test_package_exposes_version_and_typing_marker() -> None:
    assert package.__version__ == "0.1.0"
    assert "__version__" in package.__all__
    assert package.__file__ is not None

    package_directory = Path(package.__file__).parent

    assert (package_directory / "py.typed").is_file()


def test_default_column_mapping_matches_audit_export() -> None:
    mapping = AuditColumnMapping()

    assert mapping.required_columns == (
        "ID",
        "LLM_SUGGESTIONS",
        "SELECTED_SUGGESTIONS",
        "FINAL_SUBMISSION",
    )
    assert mapping.payload_columns == (
        "LLM_SUGGESTIONS",
        "SELECTED_SUGGESTIONS",
        "FINAL_SUBMISSION",
    )


def test_default_report_config_excludes_free_text() -> None:
    config = AuditReportConfig()

    assert config.include_text is False


@pytest.mark.parametrize(
    "field_name",
    [
        "record_id",
        "llm_suggestions",
        "selected_suggestions",
        "final_submission",
    ],
)
def test_column_mapping_rejects_blank_names(field_name: str) -> None:
    arguments = {
        "record_id": "ID",
        "llm_suggestions": "LLM_SUGGESTIONS",
        "selected_suggestions": "SELECTED_SUGGESTIONS",
        "final_submission": "FINAL_SUBMISSION",
    }
    arguments[field_name] = " "

    with pytest.raises(
        AuditReportConfigurationError,
        match=f"{field_name} must be a nonblank string",
    ):
        AuditColumnMapping(**arguments)


def test_column_mapping_rejects_duplicate_names() -> None:
    with pytest.raises(
        AuditReportConfigurationError,
        match="must use unique source-column names",
    ):
        AuditColumnMapping(
            record_id="ID",
            llm_suggestions="ID",
        )


def test_report_config_rejects_non_boolean_include_text() -> None:
    with pytest.raises(
        AuditReportConfigurationError,
        match="include_text must be a Boolean",
    ):
        AuditReportConfig(
            include_text=1,  # type: ignore[arg-type]
        )


def test_report_summary_preserves_counts() -> None:
    summary = AuditReportSummary(
        source_rows=10,
        analyzable_rows=4,
        analyzed_rows=3,
        skipped_rows=6,
        failed_rows=1,
        metric_rows=36,
    )

    assert summary.source_rows == 10
    assert summary.analyzable_rows == 4
    assert summary.analyzed_rows == 3
    assert summary.skipped_rows == 6
    assert summary.failed_rows == 1
    assert summary.metric_rows == 36


def test_program_exceptions_share_one_base_class() -> None:
    assert issubclass(
        AuditReportConfigurationError,
        AuditReportError,
    )
    assert issubclass(AuditRowError, AuditReportError)
    assert issubclass(AuditOutputError, AuditReportError)
    assert issubclass(AuditSourceError, AuditReportError)


def test_report_config_rejects_invalid_column_mapping() -> None:
    invalid_columns = cast(
        "AuditColumnMapping",
        object(),
    )

    with pytest.raises(
        AuditReportConfigurationError,
        match="columns must be an AuditColumnMapping",
    ):
        AuditReportConfig(columns=invalid_columns)


def test_payload_state_values_are_stable() -> None:
    assert PayloadState.ANALYZABLE.value == "analyzable"
    assert PayloadState.SKIPPED.value == "skipped"


def test_public_api_exports_processing_contract() -> None:
    assert package.PayloadState is PayloadState
    assert package.ProcessedAuditRow is ProcessedAuditRow
    assert package.analyze_audit_row is analyze_audit_row
    assert package.classify_payload_state is classify_payload_state
    assert package.extract_record_id is extract_record_id
    assert package.process_audit_rows is process_audit_rows
    assert package.validate_source_schema is validate_source_schema


def test_removed_eligibility_api_is_not_exported() -> None:
    assert "EligibilityPolicy" not in package.__all__
    assert "analyze_eligible_row" not in package.__all__
    assert "is_eligible_row" not in package.__all__

    assert not hasattr(package, "EligibilityPolicy")
    assert not hasattr(package, "analyze_eligible_row")
    assert not hasattr(package, "is_eligible_row")


def test_public_api_exports_output_serialization() -> None:
    assert package.CsvOutputOptions is CsvOutputOptions
    assert package.serialize_csv_value is serialize_csv_value


def test_public_api_exports_report_generation() -> None:
    assert package.AuditCsvReport is AuditCsvReport
    assert package.AuditSourceError is AuditSourceError
    assert package.FIELD_METRICS_FILENAME == FIELD_METRICS_FILENAME
    assert package.RECORDS_FILENAME == RECORDS_FILENAME
    assert package.generate_csv_report is generate_csv_report
