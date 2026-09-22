"""Study-posting authoring audit-report program.

This program composes schema-aware row sources with study-posting analysis and
writes normalized source-record and AI-assistance metrics CSV outputs.
"""

from study_posting_audit_report.config import (
    AuditColumnMapping,
    AuditReportConfig,
)
from study_posting_audit_report.errors import (
    AuditOutputError,
    AuditReportConfigurationError,
    AuditReportError,
    AuditRowError,
    AuditSourceError,
    RecordId,
)
from study_posting_audit_report.models import (
    AiAssistanceRow,
    AuditCsvReport,
    AuditReportSummary,
    ProcessedAuditRow,
)
from study_posting_audit_report.output import (
    AI_ASSISTANCE_METRICS_FILENAME,
    READABILITY_METRICS_FILENAME,
    RECORDS_FILENAME,
    REPORT_METADATA_FILENAME,
    REPORT_METADATA_SCHEMA_VERSION,
    SOURCE_SNAPSHOT_PROVENANCE_UNAVAILABLE,
    CsvOutputOptions,
    generate_csv_report,
    serialize_csv_value,
)
from study_posting_audit_report.processing import (
    analyze_audit_row,
    extract_record_id,
    process_audit_rows,
    validate_source_schema,
)
from study_posting_audit_report.readability import (
    READABILITY_COLUMNS,
    ReadabilityAnalyzer,
    ReadabilityResultLike,
    ReadabilityRow,
    analyze_readability_for_row,
)

__version__ = "0.1.0"

__all__ = [
    "AI_ASSISTANCE_METRICS_FILENAME",
    "READABILITY_COLUMNS",
    "READABILITY_METRICS_FILENAME",
    "RECORDS_FILENAME",
    "REPORT_METADATA_FILENAME",
    "REPORT_METADATA_SCHEMA_VERSION",
    "SOURCE_SNAPSHOT_PROVENANCE_UNAVAILABLE",
    "AiAssistanceRow",
    "AuditColumnMapping",
    "AuditCsvReport",
    "AuditOutputError",
    "AuditReportConfig",
    "AuditReportConfigurationError",
    "AuditReportError",
    "AuditReportSummary",
    "AuditRowError",
    "AuditSourceError",
    "CsvOutputOptions",
    "ProcessedAuditRow",
    "ReadabilityAnalyzer",
    "ReadabilityResultLike",
    "ReadabilityRow",
    "RecordId",
    "__version__",
    "analyze_audit_row",
    "analyze_readability_for_row",
    "extract_record_id",
    "generate_csv_report",
    "process_audit_rows",
    "serialize_csv_value",
    "validate_source_schema",
]
