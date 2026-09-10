"""Result and output models for study-posting audit reports."""

from dataclasses import dataclass
from pathlib import Path

from study_posting_audit_report.errors import RecordId
from tabular_row_sources import Row

#: One flattened study field-metric row.
type MetricRow = dict[str, object]


@dataclass(frozen=True, slots=True)
class ProcessedAuditRow:
    """Result of processing one source audit row.

    Attributes
    ----------
    source_row_number
        One-based position of the source row.
    record_id
        Validated source record identifier.
    record
        Fresh copy of the complete canonical source row.
     analyzed
        Whether the row was a completed AI attempt and was successfully
        analyzed.
    metric_rows
        Flattened field-metric rows. Empty for manual and incomplete attempts.
    """

    source_row_number: int
    record_id: RecordId
    record: Row
    analyzed: bool
    metric_rows: tuple[MetricRow, ...]


@dataclass(frozen=True, slots=True)
class AuditReportSummary:
    """Counts produced by a completed report run.

    Attributes
    ----------
    source_rows
        Total source rows read.
    analyzable_rows
        Completed AI rows selected for analysis.
    analyzed_rows
        Analyzable rows successfully analyzed.
    skipped_rows
        Manual and incomplete rows preserved without analysis.
    failed_rows
        Analyzable rows that failed under a non-fail-fast policy. This remains
        zero while the program uses fail-fast processing.
    metric_rows
        Field-level metric rows produced.
    """

    source_rows: int
    analyzable_rows: int
    analyzed_rows: int
    skipped_rows: int
    failed_rows: int
    metric_rows: int


@dataclass(frozen=True, slots=True)
class AuditCsvReport:
    """Successfully published CSV report.

    Attributes
    ----------
    output_directory
        Published report directory.
    records_path
        Canonical source-record CSV.
    field_metrics_path
        Long-format field-metrics CSV.
    summary
        Counts produced by the completed run.
    """

    output_directory: Path
    records_path: Path
    field_metrics_path: Path
    summary: AuditReportSummary
