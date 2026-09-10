"""Atomic CSV output for study-posting audit reports.

A report is written into a temporary sibling directory. After source processing,
analysis, serialization, flushing, and file closure all succeed, that directory
is renamed to the requested output directory.

The requested output directory must not already exist. This permits the two
report files to be published together with one same-filesystem directory rename.

The current policy is fail-fast. Any source, row, analysis, serialization, or
write failure removes the temporary directory and publishes no report.
"""

import csv
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
from typing import TextIO, cast

from study_posting_ai_analysis import FLATTENED_COLUMNS
from study_posting_audit_report.config import AuditReportConfig
from study_posting_audit_report.errors import (
    AuditOutputError,
    AuditReportConfigurationError,
    AuditSourceError,
)
from study_posting_audit_report.models import (
    AuditCsvReport,
    AuditReportSummary,
)
from study_posting_audit_report.processing import (
    process_audit_rows,
    validate_source_schema,
)
from tabular_row_sources import (
    RowSource,
    RowSourceError,
)

RECORDS_FILENAME = "records.csv"
FIELD_METRICS_FILENAME = "field_metrics.csv"


def _require_nonblank_string(
    value: object,
    *,
    field_name: str,
) -> str:
    """Return a nonblank string configuration value."""
    if not isinstance(value, str) or not value.strip():
        raise AuditReportConfigurationError(f"{field_name} must be a nonblank string")

    return value


def _require_nonempty_string(
    value: object,
    *,
    field_name: str,
) -> str:
    r"""Return a string containing at least one character.

    Unlike a nonblank-string validator, this accepts whitespace characters.
    CSV line terminators such as ``"\n"`` and ``"\r\n"`` are whitespace by
    definition.
    """
    if not isinstance(value, str) or not value:
        raise AuditReportConfigurationError(f"{field_name} must be a nonempty string")

    return value


@dataclass(frozen=True, slots=True)
class CsvOutputOptions:
    """CSV output serialization options.

    Parameters
    ----------
    encoding
        Encoding for both output files.
    null_value
        Reserved CSV text representing Python ``None``.
    lineterminator
        CSV record terminator.
    """

    encoding: str = "utf-8"
    null_value: str = "\\N"
    lineterminator: str = "\n"

    def __post_init__(self) -> None:
        """Validate output options."""
        _require_nonblank_string(
            self.encoding,
            field_name="CSV output encoding",
        )
        _require_nonblank_string(
            self.null_value,
            field_name="CSV output null_value",
        )
        _require_nonempty_string(
            self.lineterminator,
            field_name="CSV output lineterminator",
        )


def _require_output_directory(value: object) -> Path:
    """Return a nonblank output-directory path."""
    if isinstance(value, str):
        if not value.strip():
            raise AuditReportConfigurationError("output_directory must not be blank")

        return Path(value)

    if isinstance(value, Path):
        return value

    raise AuditReportConfigurationError("output_directory must be a string or Path")


def _require_report_config(value: object) -> AuditReportConfig:
    """Return valid report configuration."""
    if not isinstance(value, AuditReportConfig):
        raise AuditReportConfigurationError("config must be an AuditReportConfig")

    return value


def _require_output_options(value: object) -> CsvOutputOptions:
    """Return valid CSV output options."""
    if not isinstance(value, CsvOutputOptions):
        raise AuditReportConfigurationError("output_options must be CsvOutputOptions")

    return value


def _serialize_json_object(
    value: dict[object, object],
    *,
    column_name: str,
) -> str:
    """Serialize one JSON-object value deterministically."""
    for key in value:
        if not isinstance(key, str):
            raise AuditOutputError(
                f"Column {column_name!r} contains a non-string JSON key"
            )

    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise AuditOutputError(
            f"Column {column_name!r} cannot be serialized as JSON: {error}"
        ) from error


def _serialize_string(
    value: str,
    *,
    column_name: str,
    null_value: str,
) -> str:
    """Serialize a string while protecting the reserved null marker."""
    if value == null_value:
        raise AuditOutputError(
            f"Column {column_name!r} contains the reserved null marker {null_value!r}"
        )

    return value


def _serialize_decimal(
    value: Decimal,
    *,
    column_name: str,
) -> str:
    """Serialize one finite decimal value."""
    if not value.is_finite():
        raise AuditOutputError(f"Column {column_name!r} contains a non-finite Decimal")

    return str(value)


def _serialize_float(
    value: float,
    *,
    column_name: str,
) -> str:
    """Serialize one finite floating-point value."""
    if not math.isfinite(value):
        raise AuditOutputError(f"Column {column_name!r} contains a non-finite float")

    return repr(value)


def _serialize_scalar(
    value: object,
    *,
    column_name: str,
) -> str:
    """Serialize one supported non-null, non-string scalar value."""
    if type(value) is bool:
        return "true" if value else "false"

    if isinstance(value, int):
        return str(value)

    if isinstance(value, Decimal):
        return _serialize_decimal(
            value,
            column_name=column_name,
        )

    if isinstance(value, float):
        return _serialize_float(
            value,
            column_name=column_name,
        )

    # datetime must be checked before date because datetime subclasses date.
    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, date):
        return value.isoformat()

    raise AuditOutputError(
        f"Column {column_name!r} has unsupported output type {type(value).__name__}"
    )


def serialize_csv_value(
    value: object,
    *,
    column_name: str,
    null_value: str,
) -> str:
    """Serialize one canonical value for CSV output.

    Parameters
    ----------
    value
        Canonical source or metric value.
    column_name
        Column name used in error messages.
    null_value
        Reserved text used for ``None``.

    Returns
    -------
    str
        Canonical CSV field text.

    Raises
    ------
    AuditOutputError
        If the value cannot be serialized without ambiguity or data loss.
    """
    if value is None:
        return null_value

    if isinstance(value, str):
        return _serialize_string(
            value,
            column_name=column_name,
            null_value=null_value,
        )

    if isinstance(value, dict):
        mapping = cast("dict[object, object]", value)

        return _serialize_json_object(
            mapping,
            column_name=column_name,
        )

    return _serialize_scalar(
        value,
        column_name=column_name,
    )


def _serialize_row(
    row: dict[str, object],
    *,
    columns: tuple[str, ...],
    null_value: str,
) -> dict[str, str]:
    """Serialize one complete output row in canonical column order."""
    actual_columns = tuple(row)

    if actual_columns != columns:
        raise AuditOutputError(
            "Output row columns do not match expected order: "
            f"expected {columns!r}, received {actual_columns!r}"
        )

    return {
        column: serialize_csv_value(
            row[column],
            column_name=column,
            null_value=null_value,
        )
        for column in columns
    }


def _open_csv_output(
    path: Path,
    *,
    encoding: str,
    lineterminator: str,
    columns: tuple[str, ...],
) -> tuple[TextIO, csv.DictWriter[str]]:
    """Open one output file and write its header."""
    handle = path.open(
        mode="w",
        encoding=encoding,
        newline="",
    )
    writer = csv.DictWriter(
        handle,
        fieldnames=columns,
        extrasaction="raise",
        lineterminator=lineterminator,
    )
    writer.writeheader()

    return handle, writer


def _flush_and_sync(handle: TextIO) -> None:
    """Flush Python and operating-system file buffers."""
    handle.flush()
    os.fsync(handle.fileno())


def _write_staged_report(
    *,
    source: RowSource,
    staging_directory: Path,
    config: AuditReportConfig,
    options: CsvOutputOptions,
) -> AuditReportSummary:
    """Process one source and write both staged CSV files."""
    validate_source_schema(
        source.schema,
        config=config,
    )

    records_path = staging_directory / RECORDS_FILENAME
    metrics_path = staging_directory / FIELD_METRICS_FILENAME

    record_columns = source.schema.column_names
    metric_columns = tuple(FLATTENED_COLUMNS)

    records_handle, records_writer = _open_csv_output(
        records_path,
        encoding=options.encoding,
        lineterminator=options.lineterminator,
        columns=record_columns,
    )
    metrics_handle, metrics_writer = _open_csv_output(
        metrics_path,
        encoding=options.encoding,
        lineterminator=options.lineterminator,
        columns=metric_columns,
    )

    source_rows = 0
    analyzable_rows = 0
    analyzed_rows = 0
    skipped_rows = 0
    metric_rows = 0

    try:
        with source.open_rows() as rows:
            for outcome in process_audit_rows(
                rows,
                config=config,
            ):
                source_rows += 1

                records_writer.writerow(
                    _serialize_row(
                        outcome.record,
                        columns=record_columns,
                        null_value=options.null_value,
                    )
                )

                if outcome.analyzed:
                    analyzable_rows += 1
                    analyzed_rows += 1
                else:
                    skipped_rows += 1

                for metric_row in outcome.metric_rows:
                    metrics_writer.writerow(
                        _serialize_row(
                            metric_row,
                            columns=metric_columns,
                            null_value=options.null_value,
                        )
                    )
                    metric_rows += 1

        _flush_and_sync(records_handle)
        _flush_and_sync(metrics_handle)
    finally:
        records_handle.close()
        metrics_handle.close()

    return AuditReportSummary(
        source_rows=source_rows,
        analyzable_rows=analyzable_rows,
        analyzed_rows=analyzed_rows,
        skipped_rows=skipped_rows,
        failed_rows=0,
        metric_rows=metric_rows,
    )


def generate_csv_report(
    source: RowSource,
    *,
    output_directory: str | Path,
    config: AuditReportConfig | None = None,
    output_options: CsvOutputOptions | None = None,
) -> AuditCsvReport:
    """Generate and atomically publish a two-file CSV report.

    Parameters
    ----------
    source
        Schema-aware canonical row source.
    output_directory
        New directory that will contain ``records.csv`` and
        ``field_metrics.csv``. It must not already exist.
    config
        Audit-report configuration. Defaults to ``AuditReportConfig()``.
    output_options
        CSV serialization options. Defaults to ``CsvOutputOptions()``.

    Returns
    -------
    AuditCsvReport
        Published paths and run summary.

    Raises
    ------
    AuditReportConfigurationError
        If arguments are invalid or the output directory already exists.
    AuditSourceError
        If the row source fails.
    AuditRowError
        If a source row cannot be processed.
    AuditOutputError
        If serialization, writing, flushing, or publication fails.

    Notes
    -----
    The output directory is published with a same-filesystem rename after both
    files are complete. Existing output directories are never overwritten.
    """
    destination = _require_output_directory(output_directory)
    report_config = (
        AuditReportConfig() if config is None else _require_report_config(config)
    )
    options = (
        CsvOutputOptions()
        if output_options is None
        else _require_output_options(output_options)
    )

    if destination.exists():
        raise AuditReportConfigurationError(
            f"Output directory already exists: {destination}"
        )

    parent = destination.parent

    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise AuditOutputError(
            f"Could not create output parent directory {parent}: {error}"
        ) from error

    try:
        staging_path = Path(
            tempfile.mkdtemp(
                prefix=f".{destination.name}.",
                dir=parent,
            )
        )
    except OSError as error:
        raise AuditOutputError(
            f"Could not create staging directory in {parent}: {error}"
        ) from error

    try:
        try:
            summary = _write_staged_report(
                source=source,
                staging_directory=staging_path,
                config=report_config,
                options=options,
            )
        except RowSourceError as error:
            raise AuditSourceError(f"Could not read audit source: {error}") from error
        except AuditOutputError:
            raise
        except (OSError, csv.Error) as error:
            raise AuditOutputError(f"Could not write CSV report: {error}") from error

        try:
            staging_path.replace(destination)
        except OSError as error:
            raise AuditOutputError(
                f"Could not publish report directory {destination}: {error}"
            ) from error
    except Exception:
        shutil.rmtree(
            staging_path,
            ignore_errors=True,
        )
        raise

    return AuditCsvReport(
        output_directory=destination,
        records_path=destination / RECORDS_FILENAME,
        field_metrics_path=destination / FIELD_METRICS_FILENAME,
        summary=summary,
    )
