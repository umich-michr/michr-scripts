"""Minimal JSON manifest for exploration publication."""

from datetime import UTC, datetime
import json
from pathlib import Path

from study_posting_audit_exploration.config import ExplorationRunConfig
from study_posting_audit_exploration.models import (
    AttemptHistoryTables,
    LoadedAuditReport,
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
    output_file_count: int,
    warning_count: int,
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
        "output_file_count": output_file_count,
        "edit_intensity_threshold_scheme": (config.edit_intensity_threshold_scheme),
        "readability_unchanged_tolerance": (config.readability_unchanged_tolerance),
        "warning_count": warning_count,
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
