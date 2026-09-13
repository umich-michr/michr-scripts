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
    ExplorationPublication,
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

_STUDY_ATTEMPT_AUTHOR_HISTORY_FILENAME = "study_attempt_author_history.csv"
_STUDY_ATTEMPT_HISTORY_FILENAME = "study_attempt_history.csv"
_AUTHOR_HISTORY_FILENAME = "author_history.csv"

_OVERVIEW_SUMMARY_FILENAME = "overview_summary.csv"
_STUDY_ATTEMPT_HISTORY_SUMMARY_FILENAME = "study_attempt_history_summary.csv"
_AUTHOR_HANDOFF_SUMMARY_FILENAME = "author_handoff_summary.csv"

_GROUPED_ATTEMPT_SUMMARY_FILENAME = "grouped_attempt_summary.csv"
_CONTENT_SOURCE_CONCORDANCE_SUMMARY_FILENAME = "content_source_concordance_summary.csv"
_CONTENT_SOURCE_CONCORDANCE_MATRIX_FILENAME = "content_source_concordance_matrix.csv"

_GROUPED_STUDY_SUMMARY_FILENAME = "grouped_study_summary.csv"

_OUTPUT_FILE_COUNT = 11


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
    histories: AttemptHistoryTables,
    overview_tables: OverviewTables,
    attempt_tables: AttemptAnalysisTables,
    study_tables: StudyAnalysisTables,
    audit_directory: Path,
    overview_directory: Path,
    attempts_directory: Path,
    studies_directory: Path,
) -> tuple[tuple[pd.DataFrame, Path], ...]:
    """Return every DataFrame and stable staging path."""
    return (
        (
            histories.study_attempt_author_history,
            audit_directory / _STUDY_ATTEMPT_AUTHOR_HISTORY_FILENAME,
        ),
        (
            histories.study_attempt_history,
            audit_directory / _STUDY_ATTEMPT_HISTORY_FILENAME,
        ),
        (
            histories.author_history,
            audit_directory / _AUTHOR_HISTORY_FILENAME,
        ),
        (
            overview_tables.overview_summary,
            overview_directory / _OVERVIEW_SUMMARY_FILENAME,
        ),
        (
            overview_tables.study_attempt_history_summary,
            overview_directory / _STUDY_ATTEMPT_HISTORY_SUMMARY_FILENAME,
        ),
        (
            overview_tables.author_handoff_summary,
            overview_directory / _AUTHOR_HANDOFF_SUMMARY_FILENAME,
        ),
        (
            attempt_tables.grouped_attempt_summary,
            attempts_directory / _GROUPED_ATTEMPT_SUMMARY_FILENAME,
        ),
        (
            attempt_tables.content_source_concordance_summary,
            attempts_directory / _CONTENT_SOURCE_CONCORDANCE_SUMMARY_FILENAME,
        ),
        (
            attempt_tables.content_source_concordance_matrix,
            attempts_directory / _CONTENT_SOURCE_CONCORDANCE_MATRIX_FILENAME,
        ),
        (
            study_tables.grouped_study_summary,
            studies_directory / _GROUPED_STUDY_SUMMARY_FILENAME,
        ),
    )


def _write_staging_output(
    staging_directory: Path,
    *,
    config: ExplorationRunConfig,
    report: LoadedAuditReport,
    histories: AttemptHistoryTables,
    overview_tables: OverviewTables,
    attempt_tables: AttemptAnalysisTables,
    study_tables: StudyAnalysisTables,
) -> None:
    """Write all current exploration files into one staging directory."""
    audit_directory = staging_directory / _ANALYSIS_AUDIT_DIRECTORY
    overview_directory = staging_directory / _OVERVIEW_DIRECTORY
    attempts_directory = staging_directory / _ATTEMPTS_DIRECTORY
    studies_directory = staging_directory / _STUDIES_DIRECTORY

    for directory in (
        audit_directory,
        overview_directory,
        attempts_directory,
        studies_directory,
    ):
        directory.mkdir()

    output_frames = _output_frames(
        histories=histories,
        overview_tables=overview_tables,
        attempt_tables=attempt_tables,
        study_tables=study_tables,
        audit_directory=audit_directory,
        overview_directory=overview_directory,
        attempts_directory=attempts_directory,
        studies_directory=studies_directory,
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
        histories=histories,
        overview_tables=overview_tables,
        attempt_tables=attempt_tables,
        study_tables=study_tables,
        output_file_count=_OUTPUT_FILE_COUNT,
    )

    for _, path in output_frames:
        _sync_file(path)

    _sync_file(manifest_path)


def publish_exploration(
    *,
    config: ExplorationRunConfig,
    report: LoadedAuditReport,
    histories: AttemptHistoryTables,
    overview_tables: OverviewTables,
    attempt_tables: AttemptAnalysisTables,
    study_tables: StudyAnalysisTables,
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
                histories=histories,
                overview_tables=overview_tables,
                attempt_tables=attempt_tables,
                study_tables=study_tables,
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

    audit_directory = destination / _ANALYSIS_AUDIT_DIRECTORY
    overview_directory = destination / _OVERVIEW_DIRECTORY
    attempts_directory = destination / _ATTEMPTS_DIRECTORY
    studies_directory = destination / _STUDIES_DIRECTORY

    return ExplorationPublication(
        output_directory=destination,
        manifest_path=destination / manifest_filename(),
        study_attempt_author_history_path=(
            audit_directory / _STUDY_ATTEMPT_AUTHOR_HISTORY_FILENAME
        ),
        study_attempt_history_path=(audit_directory / _STUDY_ATTEMPT_HISTORY_FILENAME),
        author_history_path=audit_directory / _AUTHOR_HISTORY_FILENAME,
        overview_summary_path=(overview_directory / _OVERVIEW_SUMMARY_FILENAME),
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
        output_file_count=_OUTPUT_FILE_COUNT,
    )
