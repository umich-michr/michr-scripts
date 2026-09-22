"""Typed loading of normalized audit-report CSV files."""

from collections.abc import Iterable
from datetime import UTC, datetime
import json
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError, ParserError

from study_posting_audit_exploration.config import ExplorationInputConfig
from study_posting_audit_exploration.errors import ExplorationInputError
from study_posting_audit_exploration.input_contracts import (
    AI_ASSISTANCE_COLUMNS,
    AI_ASSISTANCE_FLOAT_COLUMNS,
    AI_ASSISTANCE_INTEGER_COLUMNS,
    AI_ASSISTANCE_METRICS_FILENAME,
    READABILITY_COLUMNS,
    READABILITY_FLOAT_COLUMNS,
    READABILITY_INTEGER_COLUMNS,
    READABILITY_METRICS_FILENAME,
    RECORD_COLUMNS,
    RECORD_DATETIME_COLUMNS,
    RECORD_INTEGER_COLUMNS,
    RECORDS_FILENAME,
    REPORT_METADATA_FILENAME,
    REPORT_METADATA_KEYS,
    REPORT_METADATA_SCHEMA_VERSION,
    SOURCE_SNAPSHOT_PROVENANCE_SOURCE_PROVIDED,
    SOURCE_SNAPSHOT_PROVENANCE_UNAVAILABLE,
)
from study_posting_audit_exploration.models import (
    LoadedAuditReport,
    NormalizedReportMetadata,
)

_NULL_VALUES: tuple[str, ...] = ("\\N",)


def _read_csv(
    path: Path,
    *,
    expected_columns: tuple[str, ...],
) -> pd.DataFrame:
    """Read one CSV as nullable strings and require exact columns."""
    try:
        frame = pd.read_csv(
            path,
            dtype="string",
            keep_default_na=False,
            na_values=list(_NULL_VALUES),
        )
    except FileNotFoundError as error:
        raise ExplorationInputError(
            f"Required input file does not exist: {path}"
        ) from error
    except IsADirectoryError as error:
        raise ExplorationInputError(
            f"Input file path is a directory: {path}"
        ) from error
    except PermissionError as error:
        raise ExplorationInputError(f"Input file cannot be read: {path}") from error
    except (EmptyDataError, ParserError, UnicodeError, OSError) as error:
        raise ExplorationInputError(
            f"Could not read input file {path}: {error}"
        ) from error

    actual_columns = tuple(str(column) for column in frame.columns)

    if actual_columns != expected_columns:
        raise ExplorationInputError(
            f"Input columns do not match {path.name}: "
            f"expected {expected_columns!r}, received {actual_columns!r}"
        )

    return frame


def _convert_integer_columns(
    frame: pd.DataFrame,
    *,
    column_names: Iterable[str],
    file_name: str,
) -> None:
    """Convert selected columns to nullable integers in place."""
    for column_name in column_names:
        try:
            frame[column_name] = pd.to_numeric(
                frame[column_name],
                errors="raise",
            ).astype("Int64")
        except (TypeError, ValueError) as error:
            raise ExplorationInputError(
                f"{file_name} column {column_name!r} contains an invalid integer"
            ) from error


def _convert_float_columns(
    frame: pd.DataFrame,
    *,
    column_names: Iterable[str],
    file_name: str,
) -> None:
    """Convert selected columns to nullable floats in place."""
    for column_name in column_names:
        try:
            frame[column_name] = pd.to_numeric(
                frame[column_name],
                errors="raise",
            ).astype("Float64")
        except (TypeError, ValueError) as error:
            raise ExplorationInputError(
                f"{file_name} column {column_name!r} contains an invalid number"
            ) from error


def _convert_datetime_columns(
    frame: pd.DataFrame,
    *,
    column_names: Iterable[str],
    file_name: str,
) -> None:
    """Convert selected columns to nullable datetimes in place."""
    for column_name in column_names:
        try:
            frame[column_name] = pd.to_datetime(
                frame[column_name],
                errors="raise",
                format="ISO8601",
            )
        except (TypeError, ValueError) as error:
            raise ExplorationInputError(
                f"{file_name} column {column_name!r} contains an invalid datetime"
            ) from error


def _load_records(path: Path) -> pd.DataFrame:
    """Load and convert records.csv."""
    frame = _read_csv(
        path,
        expected_columns=RECORD_COLUMNS,
    )
    _convert_integer_columns(
        frame,
        column_names=RECORD_INTEGER_COLUMNS,
        file_name=RECORDS_FILENAME,
    )
    _convert_datetime_columns(
        frame,
        column_names=RECORD_DATETIME_COLUMNS,
        file_name=RECORDS_FILENAME,
    )

    return frame


def _load_ai_assistance(path: Path) -> pd.DataFrame:
    """Load and convert ai_assistance_metrics.csv."""
    frame = _read_csv(
        path,
        expected_columns=AI_ASSISTANCE_COLUMNS,
    )
    _convert_integer_columns(
        frame,
        column_names=AI_ASSISTANCE_INTEGER_COLUMNS,
        file_name=AI_ASSISTANCE_METRICS_FILENAME,
    )
    _convert_float_columns(
        frame,
        column_names=AI_ASSISTANCE_FLOAT_COLUMNS,
        file_name=AI_ASSISTANCE_METRICS_FILENAME,
    )

    return frame


def _load_readability(path: Path) -> pd.DataFrame:
    """Load and convert readability_metrics.csv."""
    frame = _read_csv(
        path,
        expected_columns=READABILITY_COLUMNS,
    )
    _convert_integer_columns(
        frame,
        column_names=READABILITY_INTEGER_COLUMNS,
        file_name=READABILITY_METRICS_FILENAME,
    )
    _convert_float_columns(
        frame,
        column_names=READABILITY_FLOAT_COLUMNS,
        file_name=READABILITY_METRICS_FILENAME,
    )

    return frame


def _metadata_datetime(
    value: object,
    *,
    field_name: str,
) -> datetime:
    """Return one timezone-aware UTC metadata datetime."""
    if not isinstance(value, str):
        raise ExplorationInputError(
            f"Report metadata field {field_name!r} must be an RFC 3339 string"
        )

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ExplorationInputError(
            f"Report metadata field {field_name!r} must be a valid RFC 3339 timestamp"
        ) from error

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ExplorationInputError(
            f"Report metadata field {field_name!r} must be timezone-aware"
        )

    return parsed.astimezone(UTC)


def _read_report_metadata(path: Path) -> NormalizedReportMetadata:
    """Read and validate normalized report metadata."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ExplorationInputError(
            f"Required input file does not exist: {path}"
        ) from error
    except IsADirectoryError as error:
        raise ExplorationInputError(
            f"Input file path is a directory: {path}"
        ) from error
    except PermissionError as error:
        raise ExplorationInputError(f"Input file cannot be read: {path}") from error
    except (UnicodeError, OSError, json.JSONDecodeError) as error:
        raise ExplorationInputError(f"Could not read input file {path}") from error

    if not isinstance(raw, dict):
        raise ExplorationInputError("Report metadata must contain one JSON object")

    keys = frozenset(str(key) for key in raw)

    if keys != REPORT_METADATA_KEYS:
        raise ExplorationInputError(
            "Report metadata keys do not match the normalized contract"
        )

    schema_version = raw["schema_version"]

    if (
        isinstance(schema_version, bool)
        or not isinstance(schema_version, int)
        or schema_version != REPORT_METADATA_SCHEMA_VERSION
    ):
        raise ExplorationInputError("Report metadata schema_version is unsupported")

    generated = _metadata_datetime(
        raw["report_generated_at_utc"],
        field_name="report_generated_at_utc",
    )
    provenance = raw["source_snapshot_provenance"]

    if provenance not in {
        SOURCE_SNAPSHOT_PROVENANCE_UNAVAILABLE,
        SOURCE_SNAPSHOT_PROVENANCE_SOURCE_PROVIDED,
    }:
        raise ExplorationInputError(
            "Report metadata source_snapshot_provenance is unsupported"
        )

    source_value = raw["source_snapshot_as_of_utc"]

    if provenance == SOURCE_SNAPSHOT_PROVENANCE_UNAVAILABLE:
        if source_value is not None:
            raise ExplorationInputError(
                "UNAVAILABLE source snapshot provenance requires a null timestamp"
            )

        source_snapshot = None
    else:
        source_snapshot = _metadata_datetime(
            source_value,
            field_name="source_snapshot_as_of_utc",
        )

        if source_snapshot > generated:
            raise ExplorationInputError(
                "Source snapshot timestamp must not be after report generation"
            )

    return NormalizedReportMetadata(
        schema_version=schema_version,
        report_generated_at_utc=generated,
        source_snapshot_as_of_utc=source_snapshot,
        source_snapshot_provenance=str(provenance),
    )


def load_audit_report(
    config: ExplorationInputConfig,
) -> LoadedAuditReport:
    """Load all four normalized report files."""
    directory = config.report_directory

    if not directory.exists():
        raise ExplorationInputError(
            f"Input report directory does not exist: {directory}"
        )

    if not directory.is_dir():
        raise ExplorationInputError(
            f"Input report path is not a directory: {directory}"
        )

    return LoadedAuditReport(
        records=_load_records(directory / RECORDS_FILENAME),
        ai_assistance_metrics=_load_ai_assistance(
            directory / AI_ASSISTANCE_METRICS_FILENAME
        ),
        readability_metrics=_load_readability(directory / READABILITY_METRICS_FILENAME),
        metadata=_read_report_metadata(directory / REPORT_METADATA_FILENAME),
    )
