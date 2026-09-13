"""Minimal JSON manifest for exploration publication."""

from datetime import UTC, datetime
import json
from pathlib import Path

from study_posting_audit_exploration.config import ExplorationRunConfig
from study_posting_audit_exploration.models import (
    AttemptAnalysisTables,
    AttemptHistoryTables,
    LoadedAuditReport,
    OverviewTables,
    StudyAnalysisTables,
)

_MANIFEST_FILENAME = "analysis_manifest.json"
_PROGRAM_VERSION = "0.1.0"


def manifest_filename() -> str:
    """Return the stable manifest filename."""
    return _MANIFEST_FILENAME


def write_manifest(
    path: Path,
    *,
    config: ExplorationRunConfig,
    report: LoadedAuditReport,
    histories: AttemptHistoryTables,
    overview_tables: OverviewTables,
    attempt_tables: AttemptAnalysisTables,
    study_tables: StudyAnalysisTables,
    output_file_count: int,
) -> None:
    """Write the minimal deterministic-shape analysis manifest."""
    content = {
        "analysis_program_version": _PROGRAM_VERSION,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source_report_directory": str(config.input_report_directory),
        "source_files": {
            "records": "records.csv",
            "ai_assistance_metrics": "ai_assistance_metrics.csv",
            "readability_metrics": "readability_metrics.csv",
        },
        "source_row_counts": {
            "records": len(report.records),
            "ai_assistance_metrics": len(report.ai_assistance_metrics),
            "readability_metrics": len(report.readability_metrics),
        },
        "analysis_audit_record_row_counts": {
            "study_attempt_author_history": len(histories.study_attempt_author_history),
            "study_attempt_history": len(histories.study_attempt_history),
            "author_history": len(histories.author_history),
        },
        "overview_row_counts": {
            "overview_summary": len(overview_tables.overview_summary),
            "study_attempt_history_summary": len(
                overview_tables.study_attempt_history_summary
            ),
            "author_handoff_summary": len(overview_tables.author_handoff_summary),
        },
        "attempt_analysis_row_counts": {
            "grouped_attempt_summary": len(attempt_tables.grouped_attempt_summary),
            "content_source_concordance_summary": len(
                attempt_tables.content_source_concordance_summary
            ),
            "content_source_concordance_matrix": len(
                attempt_tables.content_source_concordance_matrix
            ),
        },
        "study_analysis_row_counts": {
            "grouped_study_summary": len(study_tables.grouped_study_summary),
        },
        "output_file_count": output_file_count,
        "edit_intensity_threshold_scheme": (config.edit_intensity_threshold_scheme),
        "readability_unchanged_tolerance": (config.readability_unchanged_tolerance),
        "warning_count": len(study_tables.appointment_quality_findings),
    }
    path.write_text(
        json.dumps(
            content,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
