"""Study-posting authoring audit-report program.

This program composes schema-aware row sources with study-posting analysis and
writes normalized source-record and field-metric CSV outputs.
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
    AuditCsvReport,
    AuditReportSummary,
    MetricRow,
    ProcessedAuditRow,
)
from study_posting_audit_report.output import (
    FIELD_METRICS_FILENAME,
    RECORDS_FILENAME,
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

__version__ = "0.1.0"

__all__ = [
    "FIELD_METRICS_FILENAME",
    "RECORDS_FILENAME",
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
    "MetricRow",
    "ProcessedAuditRow",
    "RecordId",
    "__version__",
    "analyze_audit_row",
    "extract_record_id",
    "generate_csv_report",
    "process_audit_rows",
    "serialize_csv_value",
    "validate_source_schema",
]
