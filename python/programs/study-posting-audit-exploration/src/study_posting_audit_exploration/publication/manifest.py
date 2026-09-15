"""Minimal JSON manifest for exploration publication."""

from datetime import UTC, datetime
import json
from pathlib import Path

from study_posting_audit_exploration.aggregation import (
    AGGREGATE_OUTPUT_COLUMNS,
)
from study_posting_audit_exploration.config import ExplorationRunConfig
from study_posting_audit_exploration.definitions import (
    build_metric_definitions,
)
from study_posting_audit_exploration.models import (
    ExplorationAnalysisTables,
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
    tables: ExplorationAnalysisTables,
    output_file_count: int,
) -> None:
    """Write the minimal deterministic-shape analysis manifest."""
    histories = tables.histories
    overview_tables = tables.overview
    attempt_tables = tables.attempts
    study_tables = tables.studies
    author_tables = tables.authors
    field_tables = tables.fields
    readability_tables = tables.readability
    metric_definitions = build_metric_definitions(AGGREGATE_OUTPUT_COLUMNS)

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
        "definition_row_counts": {
            "metric_definitions": len(metric_definitions),
        },
        "analysis_audit_record_row_counts": {
            "study_attempt_author_history": len(histories.study_attempt_author_history),
            "study_attempt_history": len(histories.study_attempt_history),
            "author_history": len(histories.author_history),
            "completed_ai_field_analysis": len(
                field_tables.completed_ai_field_analysis
            ),
            "completed_ai_readability_pairs": len(
                readability_tables.completed_ai_readability_pairs
            ),
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
        "author_analysis_row_counts": {
            "grouped_author_summary": len(author_tables.grouped_author_summary),
            "attempt_start_experience_summary": len(
                author_tables.attempt_start_experience_summary
            ),
            "current_author_experience_summary": len(
                author_tables.current_author_experience_summary
            ),
        },
        "field_analysis_row_counts": {
            "field_adoption_editing_summary": len(
                field_tables.field_adoption_editing_summary
            ),
            "nontext_field_adoption_summary": len(
                field_tables.nontext_field_adoption_summary
            ),
            "suggestion_selection_summary": len(
                field_tables.suggestion_selection_summary
            ),
            "compensation_analysis_summary": len(
                field_tables.compensation_analysis_summary
            ),
        },
        "readability_analysis_row_counts": {
            "selected_vs_unselected_readability_summary": len(
                readability_tables.selected_vs_unselected_readability_summary
            ),
            "field_readability_change_summary": len(
                readability_tables.field_readability_change_summary
            ),
            "field_readability_target_summary": len(
                readability_tables.field_readability_target_summary
            ),
            "field_edit_readability_cross_summary": len(
                readability_tables.field_edit_readability_cross_summary
            ),
            "final_text_metric_summary": len(
                readability_tables.final_text_metric_summary
            ),
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
