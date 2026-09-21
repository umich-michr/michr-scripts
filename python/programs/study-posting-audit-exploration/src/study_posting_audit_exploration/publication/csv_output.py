"""Atomic publication of exploration outputs."""

import os
from pathlib import Path
import shutil
import tempfile

import pandas as pd

from study_posting_audit_exploration.aggregation import (
    AGGREGATE_OUTPUT_COLUMNS,
)
from study_posting_audit_exploration.config import ExplorationRunConfig
from study_posting_audit_exploration.definitions import (
    build_metric_definitions,
)
from study_posting_audit_exploration.errors import (
    ExplorationConfigurationError,
    ExplorationInputError,
)
from study_posting_audit_exploration.models import (
    ExplorationAnalysisTables,
    ExplorationPublication,
    LoadedAuditReport,
)
from study_posting_audit_exploration.publication.charts import (
    ExplorationChartInputs,
    build_exploration_charts,
)
from study_posting_audit_exploration.publication.html_report import (
    write_html_report,
)
from study_posting_audit_exploration.publication.manifest import (
    manifest_filename,
    write_manifest,
)
from study_posting_audit_exploration.research import (
    build_candidate_research_questions,
)

_REPORT_FILENAME = "report.html"

_DEFINITIONS_DIRECTORY = "definitions"
_QUALITY_DIRECTORY = "quality"
_ANALYSIS_AUDIT_DIRECTORY = "analysis-audit-records"
_OVERVIEW_DIRECTORY = "overview"
_ATTEMPTS_DIRECTORY = "attempts"
_STUDIES_DIRECTORY = "studies"
_AUTHORS_DIRECTORY = "authors"
_FIELDS_DIRECTORY = "fields"
_READABILITY_DIRECTORY = "readability"
_RESEARCH_DIRECTORY = "research"

_METRIC_DEFINITIONS_FILENAME = "metric_definitions.csv"
_DATA_QUALITY_SUMMARY_FILENAME = "data_quality_summary.csv"

_DATA_QUALITY_FINDINGS_FILENAME = "data_quality_findings.csv"
_STUDY_ATTEMPT_AUTHOR_HISTORY_FILENAME = "study_attempt_author_history.csv"
_STUDY_ATTEMPT_HISTORY_FILENAME = "study_attempt_history.csv"
_AUTHOR_HISTORY_FILENAME = "author_history.csv"
_COMPLETED_AI_FIELD_ANALYSIS_FILENAME = "completed_ai_field_analysis.csv"
_COMPLETED_AI_READABILITY_PAIRS_FILENAME = "completed_ai_readability_pairs.csv"

_OVERVIEW_SUMMARY_FILENAME = "overview_summary.csv"
_STUDY_ATTEMPT_HISTORY_SUMMARY_FILENAME = "study_attempt_history_summary.csv"
_AUTHOR_HANDOFF_SUMMARY_FILENAME = "author_handoff_summary.csv"
_REPEATED_ATTEMPT_SOURCE_CONSISTENCY_SUMMARY_FILENAME = (
    "repeated_attempt_source_consistency_summary.csv"
)

_GROUPED_ATTEMPT_SUMMARY_FILENAME = "grouped_attempt_summary.csv"
_SOURCE_CONTEXT_DISTRIBUTION_SUMMARY_FILENAME = (
    "source_context_distribution_summary.csv"
)
_SOURCE_SIZE_LATENCY_SUMMARY_FILENAME = "source_size_latency_summary.csv"
_CONTENT_SOURCE_CONCORDANCE_SUMMARY_FILENAME = "content_source_concordance_summary.csv"
_CONTENT_SOURCE_CONCORDANCE_MATRIX_FILENAME = "content_source_concordance_matrix.csv"

_COMPLETED_STUDY_AUTHOR_CONTEXT_SUMMARY_FILENAME = (
    "completed_study_author_context_summary.csv"
)
_GROUPED_STUDY_SUMMARY_FILENAME = "grouped_study_summary.csv"

_GROUPED_AUTHOR_SUMMARY_FILENAME = "grouped_author_summary.csv"
_ATTEMPT_START_EXPERIENCE_SUMMARY_FILENAME = "attempt_start_experience_summary.csv"
_CURRENT_AUTHOR_EXPERIENCE_SUMMARY_FILENAME = "current_author_experience_summary.csv"

_FIELD_ADOPTION_EDITING_SUMMARY_FILENAME = "field_adoption_editing_summary.csv"
_NONTEXT_FIELD_ADOPTION_SUMMARY_FILENAME = "nontext_field_adoption_summary.csv"
_SUGGESTION_SELECTION_SUMMARY_FILENAME = "suggestion_selection_summary.csv"
_COMPENSATION_ANALYSIS_SUMMARY_FILENAME = "compensation_analysis_summary.csv"

_SELECTED_VS_UNSELECTED_READABILITY_SUMMARY_FILENAME = (
    "selected_vs_unselected_readability_summary.csv"
)
_FIELD_READABILITY_CHANGE_SUMMARY_FILENAME = "field_readability_change_summary.csv"
_FIELD_READABILITY_TARGET_SUMMARY_FILENAME = "field_readability_target_summary.csv"
_FIELD_EDIT_READABILITY_CROSS_SUMMARY_FILENAME = (
    "field_edit_readability_cross_summary.csv"
)
_FINAL_TEXT_METRIC_SUMMARY_FILENAME = "final_text_metric_summary.csv"

_CANDIDATE_RESEARCH_QUESTIONS_FILENAME = "candidate_research_questions.csv"

_OUTPUT_FILE_COUNT = 34


def _write_frame(
    frame: pd.DataFrame,
    path: Path,
) -> None:
    """Write one DataFrame with stable null and line conventions."""
    frame.to_csv(
        path,
        index=False,
        encoding="utf-8",
        lineterminator="\n",
        na_rep="\\N",
    )


def _sync_file(path: Path) -> None:
    """Flush one completed file through the operating system."""
    with path.open(mode="rb") as handle:
        os.fsync(handle.fileno())


def _output_frames(
    *,
    tables: ExplorationAnalysisTables,
    staging_directory: Path,
) -> tuple[tuple[pd.DataFrame, Path], ...]:
    """Return every DataFrame and stable staging path."""
    quality_directory = staging_directory / _QUALITY_DIRECTORY
    audit_directory = staging_directory / _ANALYSIS_AUDIT_DIRECTORY
    overview_directory = staging_directory / _OVERVIEW_DIRECTORY
    attempts_directory = staging_directory / _ATTEMPTS_DIRECTORY
    studies_directory = staging_directory / _STUDIES_DIRECTORY
    authors_directory = staging_directory / _AUTHORS_DIRECTORY
    fields_directory = staging_directory / _FIELDS_DIRECTORY
    readability_directory = staging_directory / _READABILITY_DIRECTORY

    return (
        (
            tables.quality.data_quality_summary,
            quality_directory / _DATA_QUALITY_SUMMARY_FILENAME,
        ),
        (
            tables.quality.data_quality_findings,
            audit_directory / _DATA_QUALITY_FINDINGS_FILENAME,
        ),
        (
            tables.histories.study_attempt_author_history,
            audit_directory / _STUDY_ATTEMPT_AUTHOR_HISTORY_FILENAME,
        ),
        (
            tables.histories.study_attempt_history,
            audit_directory / _STUDY_ATTEMPT_HISTORY_FILENAME,
        ),
        (
            tables.histories.author_history,
            audit_directory / _AUTHOR_HISTORY_FILENAME,
        ),
        (
            tables.fields.completed_ai_field_analysis,
            audit_directory / _COMPLETED_AI_FIELD_ANALYSIS_FILENAME,
        ),
        (
            tables.readability.completed_ai_readability_pairs,
            audit_directory / _COMPLETED_AI_READABILITY_PAIRS_FILENAME,
        ),
        (
            tables.overview.overview_summary,
            overview_directory / _OVERVIEW_SUMMARY_FILENAME,
        ),
        (
            tables.overview.study_attempt_history_summary,
            overview_directory / _STUDY_ATTEMPT_HISTORY_SUMMARY_FILENAME,
        ),
        (
            tables.overview.author_handoff_summary,
            overview_directory / _AUTHOR_HANDOFF_SUMMARY_FILENAME,
        ),
        (
            tables.source_context.repeated_attempt_source_consistency_summary,
            overview_directory / _REPEATED_ATTEMPT_SOURCE_CONSISTENCY_SUMMARY_FILENAME,
        ),
        (
            tables.attempts.grouped_attempt_summary,
            attempts_directory / _GROUPED_ATTEMPT_SUMMARY_FILENAME,
        ),
        (
            tables.source_context.source_context_distribution_summary,
            attempts_directory / _SOURCE_CONTEXT_DISTRIBUTION_SUMMARY_FILENAME,
        ),
        (
            tables.source_context.source_size_latency_summary,
            attempts_directory / _SOURCE_SIZE_LATENCY_SUMMARY_FILENAME,
        ),
        (
            tables.attempts.content_source_concordance_summary,
            attempts_directory / _CONTENT_SOURCE_CONCORDANCE_SUMMARY_FILENAME,
        ),
        (
            tables.attempts.content_source_concordance_matrix,
            attempts_directory / _CONTENT_SOURCE_CONCORDANCE_MATRIX_FILENAME,
        ),
        (
            tables.studies.completed_study_author_context_summary,
            studies_directory / _COMPLETED_STUDY_AUTHOR_CONTEXT_SUMMARY_FILENAME,
        ),
        (
            tables.studies.grouped_study_summary,
            studies_directory / _GROUPED_STUDY_SUMMARY_FILENAME,
        ),
        (
            tables.authors.grouped_author_summary,
            authors_directory / _GROUPED_AUTHOR_SUMMARY_FILENAME,
        ),
        (
            tables.authors.attempt_start_experience_summary,
            authors_directory / _ATTEMPT_START_EXPERIENCE_SUMMARY_FILENAME,
        ),
        (
            tables.authors.current_author_experience_summary,
            authors_directory / _CURRENT_AUTHOR_EXPERIENCE_SUMMARY_FILENAME,
        ),
        (
            tables.fields.field_adoption_editing_summary,
            fields_directory / _FIELD_ADOPTION_EDITING_SUMMARY_FILENAME,
        ),
        (
            tables.fields.nontext_field_adoption_summary,
            fields_directory / _NONTEXT_FIELD_ADOPTION_SUMMARY_FILENAME,
        ),
        (
            tables.fields.suggestion_selection_summary,
            fields_directory / _SUGGESTION_SELECTION_SUMMARY_FILENAME,
        ),
        (
            tables.fields.compensation_analysis_summary,
            fields_directory / _COMPENSATION_ANALYSIS_SUMMARY_FILENAME,
        ),
        (
            tables.readability.selected_vs_unselected_readability_summary,
            readability_directory
            / _SELECTED_VS_UNSELECTED_READABILITY_SUMMARY_FILENAME,
        ),
        (
            tables.readability.field_readability_change_summary,
            readability_directory / _FIELD_READABILITY_CHANGE_SUMMARY_FILENAME,
        ),
        (
            tables.readability.field_readability_target_summary,
            readability_directory / _FIELD_READABILITY_TARGET_SUMMARY_FILENAME,
        ),
        (
            tables.readability.field_edit_readability_cross_summary,
            readability_directory / _FIELD_EDIT_READABILITY_CROSS_SUMMARY_FILENAME,
        ),
        (
            tables.readability.final_text_metric_summary,
            readability_directory / _FINAL_TEXT_METRIC_SUMMARY_FILENAME,
        ),
    )


def _write_staging_output(
    staging_directory: Path,
    *,
    config: ExplorationRunConfig,
    report: LoadedAuditReport,
    tables: ExplorationAnalysisTables,
) -> None:
    """Write all current exploration files into one staging directory."""
    for directory_name in (
        _DEFINITIONS_DIRECTORY,
        _QUALITY_DIRECTORY,
        _ANALYSIS_AUDIT_DIRECTORY,
        _OVERVIEW_DIRECTORY,
        _ATTEMPTS_DIRECTORY,
        _STUDIES_DIRECTORY,
        _AUTHORS_DIRECTORY,
        _FIELDS_DIRECTORY,
        _READABILITY_DIRECTORY,
        _RESEARCH_DIRECTORY,
    ):
        (staging_directory / directory_name).mkdir()

    output_frames = _output_frames(
        tables=tables,
        staging_directory=staging_directory,
    )
    metric_definitions_path = (
        staging_directory / _DEFINITIONS_DIRECTORY / _METRIC_DEFINITIONS_FILENAME
    )
    manifest_path = staging_directory / manifest_filename()
    report_path = staging_directory / _REPORT_FILENAME
    candidate_questions_path = (
        staging_directory / _RESEARCH_DIRECTORY / _CANDIDATE_RESEARCH_QUESTIONS_FILENAME
    )

    _write_frame(
        build_metric_definitions(AGGREGATE_OUTPUT_COLUMNS),
        metric_definitions_path,
    )
    _write_frame(
        build_candidate_research_questions(),
        candidate_questions_path,
    )

    for frame, path in output_frames:
        _write_frame(
            frame,
            path,
        )

    charts = build_exploration_charts(
        ExplorationChartInputs(
            overview_summary=(tables.overview.overview_summary),
            grouped_attempt_summary=(tables.attempts.grouped_attempt_summary),
            study_attempt_history_summary=(
                tables.overview.study_attempt_history_summary
            ),
            author_handoff_summary=(tables.overview.author_handoff_summary),
            attempt_start_experience_summary=(
                tables.authors.attempt_start_experience_summary
            ),
            current_author_experience_summary=(
                tables.authors.current_author_experience_summary
            ),
            grouped_study_summary=(tables.studies.grouped_study_summary),
            completed_study_author_context_summary=(
                tables.studies.completed_study_author_context_summary
            ),
            grouped_author_summary=(tables.authors.grouped_author_summary),
            field_adoption_editing_summary=(
                tables.fields.field_adoption_editing_summary
            ),
            suggestion_selection_summary=(tables.fields.suggestion_selection_summary),
            field_readability_change_summary=(
                tables.readability.field_readability_change_summary
            ),
            field_readability_target_summary=(
                tables.readability.field_readability_target_summary
            ),
            selected_vs_unselected_readability_summary=(
                tables.readability.selected_vs_unselected_readability_summary
            ),
            field_edit_readability_cross_summary=(
                tables.readability.field_edit_readability_cross_summary
            ),
            content_source_matrix=(tables.attempts.content_source_concordance_matrix),
            source_context_distribution_summary=(
                tables.source_context.source_context_distribution_summary
            ),
            source_size_latency_summary=(
                tables.source_context.source_size_latency_summary
            ),
            repeated_attempt_source_consistency_summary=(
                tables.source_context.repeated_attempt_source_consistency_summary
            ),
        )
    )

    write_html_report(
        report_path,
        records=report.records,
        overview_summary=tables.overview.overview_summary,
        author_handoff_summary=tables.overview.author_handoff_summary,
        data_quality_summary=tables.quality.data_quality_summary,
        charts=charts,
    )
    write_manifest(
        manifest_path,
        config=config,
        report=report,
        tables=tables,
        output_file_count=_OUTPUT_FILE_COUNT,
    )

    _sync_file(metric_definitions_path)
    _sync_file(candidate_questions_path)

    for _, path in output_frames:
        _sync_file(path)

    _sync_file(report_path)
    _sync_file(manifest_path)


def _publication_result(
    destination: Path,
) -> ExplorationPublication:
    """Return stable paths for a successfully published exploration."""
    definitions_directory = destination / _DEFINITIONS_DIRECTORY
    quality_directory = destination / _QUALITY_DIRECTORY
    audit_directory = destination / _ANALYSIS_AUDIT_DIRECTORY
    overview_directory = destination / _OVERVIEW_DIRECTORY
    attempts_directory = destination / _ATTEMPTS_DIRECTORY
    studies_directory = destination / _STUDIES_DIRECTORY
    authors_directory = destination / _AUTHORS_DIRECTORY
    fields_directory = destination / _FIELDS_DIRECTORY
    readability_directory = destination / _READABILITY_DIRECTORY
    research_directory = destination / _RESEARCH_DIRECTORY

    return ExplorationPublication(
        output_directory=destination,
        manifest_path=destination / manifest_filename(),
        report_path=destination / _REPORT_FILENAME,
        metric_definitions_path=(definitions_directory / _METRIC_DEFINITIONS_FILENAME),
        data_quality_summary_path=(quality_directory / _DATA_QUALITY_SUMMARY_FILENAME),
        data_quality_findings_path=(audit_directory / _DATA_QUALITY_FINDINGS_FILENAME),
        study_attempt_author_history_path=(
            audit_directory / _STUDY_ATTEMPT_AUTHOR_HISTORY_FILENAME
        ),
        study_attempt_history_path=(audit_directory / _STUDY_ATTEMPT_HISTORY_FILENAME),
        author_history_path=audit_directory / _AUTHOR_HISTORY_FILENAME,
        completed_ai_field_analysis_path=(
            audit_directory / _COMPLETED_AI_FIELD_ANALYSIS_FILENAME
        ),
        completed_ai_readability_pairs_path=(
            audit_directory / _COMPLETED_AI_READABILITY_PAIRS_FILENAME
        ),
        overview_summary_path=overview_directory / _OVERVIEW_SUMMARY_FILENAME,
        study_attempt_history_summary_path=(
            overview_directory / _STUDY_ATTEMPT_HISTORY_SUMMARY_FILENAME
        ),
        author_handoff_summary_path=(
            overview_directory / _AUTHOR_HANDOFF_SUMMARY_FILENAME
        ),
        repeated_attempt_source_consistency_summary_path=(
            overview_directory / _REPEATED_ATTEMPT_SOURCE_CONSISTENCY_SUMMARY_FILENAME
        ),
        grouped_attempt_summary_path=(
            attempts_directory / _GROUPED_ATTEMPT_SUMMARY_FILENAME
        ),
        source_context_distribution_summary_path=(
            attempts_directory / _SOURCE_CONTEXT_DISTRIBUTION_SUMMARY_FILENAME
        ),
        source_size_latency_summary_path=(
            attempts_directory / _SOURCE_SIZE_LATENCY_SUMMARY_FILENAME
        ),
        content_source_concordance_summary_path=(
            attempts_directory / _CONTENT_SOURCE_CONCORDANCE_SUMMARY_FILENAME
        ),
        content_source_concordance_matrix_path=(
            attempts_directory / _CONTENT_SOURCE_CONCORDANCE_MATRIX_FILENAME
        ),
        completed_study_author_context_summary_path=(
            studies_directory / _COMPLETED_STUDY_AUTHOR_CONTEXT_SUMMARY_FILENAME
        ),
        grouped_study_summary_path=(
            studies_directory / _GROUPED_STUDY_SUMMARY_FILENAME
        ),
        grouped_author_summary_path=(
            authors_directory / _GROUPED_AUTHOR_SUMMARY_FILENAME
        ),
        attempt_start_experience_summary_path=(
            authors_directory / _ATTEMPT_START_EXPERIENCE_SUMMARY_FILENAME
        ),
        current_author_experience_summary_path=(
            authors_directory / _CURRENT_AUTHOR_EXPERIENCE_SUMMARY_FILENAME
        ),
        field_adoption_editing_summary_path=(
            fields_directory / _FIELD_ADOPTION_EDITING_SUMMARY_FILENAME
        ),
        nontext_field_adoption_summary_path=(
            fields_directory / _NONTEXT_FIELD_ADOPTION_SUMMARY_FILENAME
        ),
        suggestion_selection_summary_path=(
            fields_directory / _SUGGESTION_SELECTION_SUMMARY_FILENAME
        ),
        compensation_analysis_summary_path=(
            fields_directory / _COMPENSATION_ANALYSIS_SUMMARY_FILENAME
        ),
        selected_vs_unselected_readability_summary_path=(
            readability_directory / _SELECTED_VS_UNSELECTED_READABILITY_SUMMARY_FILENAME
        ),
        field_readability_change_summary_path=(
            readability_directory / _FIELD_READABILITY_CHANGE_SUMMARY_FILENAME
        ),
        field_readability_target_summary_path=(
            readability_directory / _FIELD_READABILITY_TARGET_SUMMARY_FILENAME
        ),
        field_edit_readability_cross_summary_path=(
            readability_directory / _FIELD_EDIT_READABILITY_CROSS_SUMMARY_FILENAME
        ),
        final_text_metric_summary_path=(
            readability_directory / _FINAL_TEXT_METRIC_SUMMARY_FILENAME
        ),
        candidate_research_questions_path=(
            research_directory / _CANDIDATE_RESEARCH_QUESTIONS_FILENAME
        ),
        output_file_count=_OUTPUT_FILE_COUNT,
    )


def publish_exploration(
    *,
    config: ExplorationRunConfig,
    report: LoadedAuditReport,
    tables: ExplorationAnalysisTables,
) -> ExplorationPublication:
    """Atomically publish current exploration outputs."""
    destination = config.output_directory

    if destination.exists():
        raise ExplorationConfigurationError(
            f"Output directory already exists: {destination}"
        )

    parent = destination.parent

    try:
        parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        staging_directory = Path(
            tempfile.mkdtemp(
                prefix=f".{destination.name}.",
                dir=parent,
            )
        )
    except OSError as error:
        raise ExplorationInputError(
            f"Could not create exploration staging directory: {error}"
        ) from error

    try:
        try:
            _write_staging_output(
                staging_directory,
                config=config,
                report=report,
                tables=tables,
            )
            staging_directory.replace(destination)
        except OSError as error:
            raise ExplorationInputError(
                f"Could not publish exploration output: {error}"
            ) from error
    except Exception:
        shutil.rmtree(
            staging_directory,
            ignore_errors=True,
        )
        raise

    return _publication_result(destination)
