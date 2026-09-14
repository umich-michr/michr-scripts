"""Atomic publication of exploration outputs."""

import os
from pathlib import Path
import shutil
import tempfile

import pandas as pd

from study_posting_audit_exploration.config import ExplorationRunConfig
from study_posting_audit_exploration.errors import (
    ExplorationConfigurationError,
    ExplorationInputError,
)
from study_posting_audit_exploration.models import (
    AttemptAnalysisTables,
    AttemptHistoryTables,
    AuthorAnalysisTables,
    ExplorationAnalysisTables,
    ExplorationPublication,
    FieldAnalysisTables,
    LoadedAuditReport,
    OverviewTables,
    StudyAnalysisTables,
)
from study_posting_audit_exploration.publication.manifest import (
    manifest_filename,
    write_manifest,
)

_ANALYSIS_AUDIT_DIRECTORY = "analysis-audit-records"
_OVERVIEW_DIRECTORY = "overview"
_ATTEMPTS_DIRECTORY = "attempts"
_STUDIES_DIRECTORY = "studies"
_AUTHORS_DIRECTORY = "authors"
_FIELDS_DIRECTORY = "fields"

_STUDY_ATTEMPT_AUTHOR_HISTORY_FILENAME = "study_attempt_author_history.csv"
_STUDY_ATTEMPT_HISTORY_FILENAME = "study_attempt_history.csv"
_AUTHOR_HISTORY_FILENAME = "author_history.csv"
_COMPLETED_AI_FIELD_ANALYSIS_FILENAME = "completed_ai_field_analysis.csv"

_OVERVIEW_SUMMARY_FILENAME = "overview_summary.csv"
_STUDY_ATTEMPT_HISTORY_SUMMARY_FILENAME = "study_attempt_history_summary.csv"
_AUTHOR_HANDOFF_SUMMARY_FILENAME = "author_handoff_summary.csv"

_GROUPED_ATTEMPT_SUMMARY_FILENAME = "grouped_attempt_summary.csv"
_CONTENT_SOURCE_CONCORDANCE_SUMMARY_FILENAME = "content_source_concordance_summary.csv"
_CONTENT_SOURCE_CONCORDANCE_MATRIX_FILENAME = "content_source_concordance_matrix.csv"

_GROUPED_STUDY_SUMMARY_FILENAME = "grouped_study_summary.csv"

_GROUPED_AUTHOR_SUMMARY_FILENAME = "grouped_author_summary.csv"
_ATTEMPT_START_EXPERIENCE_SUMMARY_FILENAME = "attempt_start_experience_summary.csv"
_CURRENT_AUTHOR_EXPERIENCE_SUMMARY_FILENAME = "current_author_experience_summary.csv"

_FIELD_ADOPTION_EDITING_SUMMARY_FILENAME = "field_adoption_editing_summary.csv"
_NONTEXT_FIELD_ADOPTION_SUMMARY_FILENAME = "nontext_field_adoption_summary.csv"
_SUGGESTION_SELECTION_SUMMARY_FILENAME = "suggestion_selection_summary.csv"
_COMPENSATION_ANALYSIS_SUMMARY_FILENAME = "compensation_analysis_summary.csv"

_OUTPUT_FILE_COUNT = 19


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
    audit_directory = staging_directory / _ANALYSIS_AUDIT_DIRECTORY
    overview_directory = staging_directory / _OVERVIEW_DIRECTORY
    attempts_directory = staging_directory / _ATTEMPTS_DIRECTORY
    studies_directory = staging_directory / _STUDIES_DIRECTORY
    authors_directory = staging_directory / _AUTHORS_DIRECTORY
    fields_directory = staging_directory / _FIELDS_DIRECTORY

    return (
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
            tables.attempts.grouped_attempt_summary,
            attempts_directory / _GROUPED_ATTEMPT_SUMMARY_FILENAME,
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
        _ANALYSIS_AUDIT_DIRECTORY,
        _OVERVIEW_DIRECTORY,
        _ATTEMPTS_DIRECTORY,
        _STUDIES_DIRECTORY,
        _AUTHORS_DIRECTORY,
        _FIELDS_DIRECTORY,
    ):
        (staging_directory / directory_name).mkdir()

    output_frames = _output_frames(
        tables=tables,
        staging_directory=staging_directory,
    )
    manifest_path = staging_directory / manifest_filename()

    for frame, path in output_frames:
        _write_frame(
            frame,
            path,
        )

    write_manifest(
        manifest_path,
        config=config,
        report=report,
        tables=tables,
        output_file_count=_OUTPUT_FILE_COUNT,
    )

    for _, path in output_frames:
        _sync_file(path)

    _sync_file(manifest_path)


def _publication_result(
    destination: Path,
) -> ExplorationPublication:
    """Return stable paths for a successfully published exploration."""
    audit_directory = destination / _ANALYSIS_AUDIT_DIRECTORY
    overview_directory = destination / _OVERVIEW_DIRECTORY
    attempts_directory = destination / _ATTEMPTS_DIRECTORY
    studies_directory = destination / _STUDIES_DIRECTORY
    authors_directory = destination / _AUTHORS_DIRECTORY
    fields_directory = destination / _FIELDS_DIRECTORY

    return ExplorationPublication(
        output_directory=destination,
        manifest_path=destination / manifest_filename(),
        study_attempt_author_history_path=(
            audit_directory / _STUDY_ATTEMPT_AUTHOR_HISTORY_FILENAME
        ),
        study_attempt_history_path=(audit_directory / _STUDY_ATTEMPT_HISTORY_FILENAME),
        author_history_path=audit_directory / _AUTHOR_HISTORY_FILENAME,
        overview_summary_path=overview_directory / _OVERVIEW_SUMMARY_FILENAME,
        study_attempt_history_summary_path=(
            overview_directory / _STUDY_ATTEMPT_HISTORY_SUMMARY_FILENAME
        ),
        author_handoff_summary_path=(
            overview_directory / _AUTHOR_HANDOFF_SUMMARY_FILENAME
        ),
        grouped_attempt_summary_path=(
            attempts_directory / _GROUPED_ATTEMPT_SUMMARY_FILENAME
        ),
        content_source_concordance_summary_path=(
            attempts_directory / _CONTENT_SOURCE_CONCORDANCE_SUMMARY_FILENAME
        ),
        content_source_concordance_matrix_path=(
            attempts_directory / _CONTENT_SOURCE_CONCORDANCE_MATRIX_FILENAME
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
        completed_ai_field_analysis_path=(
            audit_directory / _COMPLETED_AI_FIELD_ANALYSIS_FILENAME
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
        output_file_count=_OUTPUT_FILE_COUNT,
    )


def publish_exploration(
    *,
    config: ExplorationRunConfig,
    report: LoadedAuditReport,
    histories: AttemptHistoryTables,
    overview_tables: OverviewTables,
    attempt_tables: AttemptAnalysisTables,
    study_tables: StudyAnalysisTables,
    author_tables: AuthorAnalysisTables,
    field_tables: FieldAnalysisTables,
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

    tables = ExplorationAnalysisTables(
        histories=histories,
        overview=overview_tables,
        attempts=attempt_tables,
        studies=study_tables,
        authors=author_tables,
        fields=field_tables,
    )

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
