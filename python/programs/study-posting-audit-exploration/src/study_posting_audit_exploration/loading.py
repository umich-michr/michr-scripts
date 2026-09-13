"""Typed loading of normalized audit-report CSV files."""

from collections.abc import Iterable
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
)
from study_posting_audit_exploration.models import LoadedAuditReport

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


def load_audit_report(
    config: ExplorationInputConfig,
) -> LoadedAuditReport:
    """Load all three normalized report files."""
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
    )
