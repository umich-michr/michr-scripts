"""Tests for the study-posting-audit-report package contract."""

from pathlib import Path
from typing import cast

import pytest

import study_posting_audit_report as package
from study_posting_audit_report import (
    AI_ASSISTANCE_METRICS_FILENAME,
    READABILITY_COLUMNS,
    READABILITY_METRICS_FILENAME,
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
    ProcessedAuditRow,
    analyze_audit_row,
    extract_record_id,
    generate_csv_report,
    process_audit_rows,
    serialize_csv_value,
    validate_source_schema,
)
from tabular_row_sources import load_schema_json


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
        "END_TIME",
        "ATTEMPT_TYPE",
        "ATTEMPT_RESULT",
        "LLM_SUGGESTIONS",
        "SELECTED_SUGGESTIONS",
        "FINAL_SUBMISSION",
    )
    assert mapping.payload_columns == (
        "LLM_SUGGESTIONS",
        "SELECTED_SUGGESTIONS",
        "FINAL_SUBMISSION",
    )


def test_default_input_schema_matches_report_contract() -> None:
    package_file = package.__file__

    assert package_file is not None

    program_directory = Path(package_file).parents[2]
    schema_path = program_directory / "input" / "audit-schema.json"

    schema = load_schema_json(schema_path)
    required = AuditReportConfig().columns.required_columns

    assert len(schema.columns) == 39
    assert "STACK_TRACE" not in schema.column_names
    assert all(name in schema.column_names for name in required)


def test_default_report_config_excludes_free_text() -> None:
    config = AuditReportConfig()

    assert config.include_text is False


@pytest.mark.parametrize(
    "field_name",
    [
        "record_id",
        "end_time",
        "attempt_type",
        "attempt_result",
        "llm_suggestions",
        "selected_suggestions",
        "final_submission",
    ],
)
def test_column_mapping_rejects_blank_names(field_name: str) -> None:
    arguments = {
        "record_id": "ID",
        "end_time": "END_TIME",
        "attempt_type": "ATTEMPT_TYPE",
        "attempt_result": "ATTEMPT_RESULT",
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


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("record_id", None),
        ("end_time", 1),
        ("attempt_type", object()),
        ("attempt_result", False),
        ("llm_suggestions", []),
        ("selected_suggestions", {}),
        ("final_submission", 1.5),
    ],
    ids=[
        "record-id-none",
        "end-time-integer",
        "attempt-type-object",
        "attempt-result-boolean",
        "suggestions-list",
        "selections-dictionary",
        "final-float",
    ],
)
def test_column_mapping_rejects_non_string_names(
    field_name: str,
    value: object,
) -> None:
    arguments: dict[str, object] = {
        "record_id": "ID",
        "end_time": "END_TIME",
        "attempt_type": "ATTEMPT_TYPE",
        "attempt_result": "ATTEMPT_RESULT",
        "llm_suggestions": "LLM_SUGGESTIONS",
        "selected_suggestions": "SELECTED_SUGGESTIONS",
        "final_submission": "FINAL_SUBMISSION",
    }
    arguments[field_name] = value

    with pytest.raises(
        AuditReportConfigurationError,
        match=f"{field_name} must be a nonblank string",
    ):
        AuditColumnMapping(**arguments)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field_name", "duplicate_value"),
    [
        ("end_time", "ID"),
        ("attempt_type", "ID"),
        ("attempt_result", "ID"),
        ("llm_suggestions", "ID"),
        ("selected_suggestions", "ID"),
        ("final_submission", "ID"),
    ],
    ids=[
        "end-time",
        "attempt-type",
        "attempt-result",
        "suggestions",
        "selections",
        "final",
    ],
)
def test_column_mapping_rejects_duplicate_names(
    field_name: str,
    duplicate_value: str,
) -> None:
    arguments = {
        "record_id": "ID",
        "end_time": "END_TIME",
        "attempt_type": "ATTEMPT_TYPE",
        "attempt_result": "ATTEMPT_RESULT",
        "llm_suggestions": "LLM_SUGGESTIONS",
        "selected_suggestions": "SELECTED_SUGGESTIONS",
        "final_submission": "FINAL_SUBMISSION",
    }
    arguments[field_name] = duplicate_value

    with pytest.raises(
        AuditReportConfigurationError,
        match="must use unique source-column names",
    ):
        AuditColumnMapping(**arguments)


def test_report_config_rejects_non_boolean_include_text() -> None:
    with pytest.raises(
        AuditReportConfigurationError,
        match="include_text must be a Boolean",
    ):
        AuditReportConfig(
            include_text=1,  # type: ignore[arg-type]
        )


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


def test_report_summary_preserves_counts() -> None:
    summary = AuditReportSummary(
        source_rows=10,
        analyzable_rows=4,
        analyzed_rows=3,
        skipped_rows=6,
        failed_rows=1,
        ai_assistance_rows=36,
        readability_rows=20,
    )

    assert summary.source_rows == 10
    assert summary.analyzable_rows == 4
    assert summary.analyzed_rows == 3
    assert summary.skipped_rows == 6
    assert summary.failed_rows == 1
    assert summary.ai_assistance_rows == 36
    assert summary.readability_rows == 20


def test_program_exceptions_share_one_base_class() -> None:
    assert issubclass(
        AuditReportConfigurationError,
        AuditReportError,
    )
    assert issubclass(AuditRowError, AuditReportError)
    assert issubclass(AuditOutputError, AuditReportError)
    assert issubclass(AuditSourceError, AuditReportError)


def test_public_api_exports_processing_contract() -> None:
    assert package.ProcessedAuditRow is ProcessedAuditRow
    assert package.analyze_audit_row is analyze_audit_row
    assert package.extract_record_id is extract_record_id
    assert package.process_audit_rows is process_audit_rows
    assert package.validate_source_schema is validate_source_schema


def test_removed_payload_state_api_is_not_exported() -> None:
    assert "PayloadState" not in package.__all__
    assert "classify_payload_state" not in package.__all__

    assert not hasattr(package, "PayloadState")
    assert not hasattr(package, "classify_payload_state")


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
    assert package.AI_ASSISTANCE_METRICS_FILENAME == AI_ASSISTANCE_METRICS_FILENAME
    assert package.RECORDS_FILENAME == RECORDS_FILENAME
    assert package.generate_csv_report is generate_csv_report


def test_ai_assistance_output_vocabulary_is_public_contract() -> None:
    assert "AI_ASSISTANCE_METRICS_FILENAME" in package.__all__
    assert "AiAssistanceRow" in package.__all__

    assert hasattr(package, "AI_ASSISTANCE_METRICS_FILENAME")
    assert hasattr(package, "AiAssistanceRow")

    assert "FIELD_METRICS_FILENAME" not in package.__all__
    assert "MetricRow" not in package.__all__

    assert not hasattr(package, "FIELD_METRICS_FILENAME")
    assert not hasattr(package, "MetricRow")

    assert "ai_assistance_rows" in ProcessedAuditRow.__annotations__
    assert "metric_rows" not in ProcessedAuditRow.__annotations__

    assert "ai_assistance_rows" in AuditReportSummary.__annotations__
    assert "metric_rows" not in AuditReportSummary.__annotations__

    assert "ai_assistance_metrics_path" in AuditCsvReport.__annotations__
    assert "field_metrics_path" not in AuditCsvReport.__annotations__


def test_readability_output_vocabulary_is_public_contract() -> None:
    assert package.READABILITY_METRICS_FILENAME == READABILITY_METRICS_FILENAME
    assert package.READABILITY_COLUMNS == READABILITY_COLUMNS

    assert READABILITY_METRICS_FILENAME == "readability_metrics.csv"
    assert tuple(READABILITY_COLUMNS) == (
        "record_id",
        "attempt_type",
        "field_name",
        "text_role",
        "suggestion_kind",
        "suggestion_index",
        "selected",
        "flesch_kincaid_grade",
        "automated_readability_index",
        "coleman_liau_index",
        "gunning_fog",
        "dale_chall_readability_score",
        "estimated_reading_time_seconds",
        "sentence_count",
        "word_count",
        "syllable_count",
        "letter_count",
        "polysyllable_count",
    )

    assert "readability_rows" in AuditReportSummary.__annotations__
    assert "readability_metrics_path" in AuditCsvReport.__annotations__
