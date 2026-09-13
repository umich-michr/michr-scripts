"""Atomic publication of exploration analysis-audit records."""

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
    AttemptHistoryTables,
    ExplorationPublication,
    LoadedAuditReport,
)
from study_posting_audit_exploration.publication.manifest import (
    manifest_filename,
    write_manifest,
)

_ANALYSIS_AUDIT_DIRECTORY = "analysis-audit-records"
_STUDY_ATTEMPT_AUTHOR_HISTORY_FILENAME = "study_attempt_author_history.csv"
_STUDY_ATTEMPT_HISTORY_FILENAME = "study_attempt_history.csv"
_AUTHOR_HISTORY_FILENAME = "author_history.csv"
_OUTPUT_FILE_COUNT = 4


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


def _write_staging_output(
    staging_directory: Path,
    *,
    config: ExplorationRunConfig,
    report: LoadedAuditReport,
    histories: AttemptHistoryTables,
) -> None:
    """Write all Batch 3 files into one staging directory."""
    audit_directory = staging_directory / _ANALYSIS_AUDIT_DIRECTORY
    audit_directory.mkdir()

    attempt_path = audit_directory / _STUDY_ATTEMPT_AUTHOR_HISTORY_FILENAME
    study_path = audit_directory / _STUDY_ATTEMPT_HISTORY_FILENAME
    author_path = audit_directory / _AUTHOR_HISTORY_FILENAME
    manifest_path = staging_directory / manifest_filename()

    _write_frame(
        histories.study_attempt_author_history,
        attempt_path,
    )
    _write_frame(
        histories.study_attempt_history,
        study_path,
    )
    _write_frame(
        histories.author_history,
        author_path,
    )
    write_manifest(
        manifest_path,
        config=config,
        report=report,
        histories=histories,
        output_file_count=_OUTPUT_FILE_COUNT,
        warning_count=0,
    )

    for path in (
        attempt_path,
        study_path,
        author_path,
        manifest_path,
    ):
        _sync_file(path)


def publish_exploration(
    *,
    config: ExplorationRunConfig,
    report: LoadedAuditReport,
    histories: AttemptHistoryTables,
) -> ExplorationPublication:
    """Atomically publish Batch 3 exploration outputs."""
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

    return ExplorationPublication(
        output_directory=destination,
        manifest_path=destination / manifest_filename(),
        study_attempt_author_history_path=(
            audit_directory / _STUDY_ATTEMPT_AUTHOR_HISTORY_FILENAME
        ),
        study_attempt_history_path=(audit_directory / _STUDY_ATTEMPT_HISTORY_FILENAME),
        author_history_path=audit_directory / _AUTHOR_HISTORY_FILENAME,
        output_file_count=_OUTPUT_FILE_COUNT,
    )
