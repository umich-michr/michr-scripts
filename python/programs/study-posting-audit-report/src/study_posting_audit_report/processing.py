"""Pure transformation of canonical audit rows into field-level metrics.

This module owns analysis selection, source-column mapping, record-ID
validation, duplicate detection, and composition with
``study-posting-ai-analysis``.

Every valid source row is preserved. Completed AI attempts are analyzed. Manual
and incomplete attempts are preserved without field metrics.

It performs no database access, file I/O, logging, aggregation, or output
writing.
"""

from collections.abc import Iterable, Iterator, Mapping
from typing import cast

from study_posting_ai_analysis import (
    analyze_objects,
    flatten_analysis_results,
    parse_analysis_inputs,
)
from study_posting_audit_report.config import AuditReportConfig
from study_posting_audit_report.errors import AuditRowError, RecordId
from study_posting_audit_report.models import ProcessedAuditRow
from tabular_row_sources import Row, RowSchema

_ANALYZED_ATTEMPT_TYPE = "AI"
_ANALYZED_ATTEMPT_RESULT = "COMPLETE"


def validate_source_schema(
    schema: RowSchema,
    *,
    config: AuditReportConfig,
) -> None:
    """Require every configured audit column in the source schema.

    Extra source columns are permitted and preserved in ``records.csv``.
    Required columns may appear anywhere in the source schema.

    Parameters
    ----------
    schema
        Canonical schema produced by the configured row source.
    config
        Audit-report behavior configuration.

    Raises
    ------
    AuditRowError
        If one or more required source columns are absent.
    """
    available = set(schema.column_names)
    missing = [
        name for name in config.columns.required_columns if name not in available
    ]

    if missing:
        raise AuditRowError(f"source schema is missing required columns: {missing}")


def _require_source_row(
    value: object,
    *,
    row_number: int,
) -> Mapping[str, object]:
    """Return a string-keyed source-row mapping."""
    if not isinstance(value, Mapping):
        raise AuditRowError(
            "source value must be a row mapping",
            row_number=row_number,
        )

    untyped_mapping = cast("Mapping[object, object]", value)
    row: dict[str, object] = {}

    for key, item in untyped_mapping.items():
        if not isinstance(key, str):
            raise AuditRowError(
                "source row column names must be strings",
                row_number=row_number,
            )

        row[key] = item

    return row


def _required_value(
    row: Mapping[str, object],
    *,
    column_name: str,
    row_number: int,
    record_id: RecordId | None = None,
) -> object:
    """Return a required source value."""
    if column_name not in row:
        raise AuditRowError(
            f"source row is missing required column {column_name!r}",
            row_number=row_number,
            record_id=record_id,
        )

    return row[column_name]


def extract_record_id(
    row: Mapping[str, object],
    *,
    config: AuditReportConfig,
    row_number: int,
) -> RecordId:
    """Extract and validate one source record identifier.

    Accepted identifiers are nonblank strings and non-Boolean integers.

    Parameters
    ----------
    row
        Canonical source row.
    config
        Audit-report behavior configuration.
    row_number
        One-based source-row position.

    Returns
    -------
    RecordId
        Validated identifier.

    Raises
    ------
    AuditRowError
        If the configured ID column is absent, null, blank, Boolean, or another
        unsupported type.
    """
    value = _required_value(
        row,
        column_name=config.columns.record_id,
        row_number=row_number,
    )

    if isinstance(value, bool):
        raise AuditRowError(
            f"record ID column {config.columns.record_id!r} must not contain a Boolean",
            row_number=row_number,
        )

    if isinstance(value, int):
        return value

    if isinstance(value, str):
        if value.strip():
            return value

        raise AuditRowError(
            f"record ID column {config.columns.record_id!r} must not be blank",
            row_number=row_number,
        )

    if value is None:
        raise AuditRowError(
            f"record ID column {config.columns.record_id!r} must not be null",
            row_number=row_number,
        )

    raise AuditRowError(
        f"record ID column {config.columns.record_id!r} "
        "must contain a string or integer",
        row_number=row_number,
    )


def _should_analyze_row(
    row: Mapping[str, object],
    *,
    config: AuditReportConfig,
    row_number: int,
    record_id: RecordId,
) -> bool:
    """Return whether one source row must be analyzed.

    Manual attempts and incomplete AI attempts are skipped without inspecting
    their analysis payloads. A completed AI attempt must have a non-null end
    time and all three non-null analysis payloads.
    """
    attempt_type = _required_value(
        row,
        column_name=config.columns.attempt_type,
        row_number=row_number,
        record_id=record_id,
    )

    if attempt_type != _ANALYZED_ATTEMPT_TYPE:
        return False

    attempt_result = _required_value(
        row,
        column_name=config.columns.attempt_result,
        row_number=row_number,
        record_id=record_id,
    )

    if attempt_result != _ANALYZED_ATTEMPT_RESULT:
        return False

    end_time = _required_value(
        row,
        column_name=config.columns.end_time,
        row_number=row_number,
        record_id=record_id,
    )

    if end_time is None:
        raise AuditRowError(
            f"completed AI row requires non-null column {config.columns.end_time!r}",
            row_number=row_number,
            record_id=record_id,
        )

    null_payload_columns = [
        column_name
        for column_name in config.columns.payload_columns
        if _required_value(
            row,
            column_name=column_name,
            row_number=row_number,
            record_id=record_id,
        )
        is None
    ]

    if null_payload_columns:
        raise AuditRowError(
            "completed AI row requires all analysis payloads; "
            f"null columns: {null_payload_columns}",
            row_number=row_number,
            record_id=record_id,
        )

    return True


def analyze_audit_row(
    row: Mapping[str, object],
    *,
    config: AuditReportConfig,
    row_number: int,
    record_id: RecordId,
) -> tuple[dict[str, object], ...]:
    """Analyze one selected completed AI row.

    Parameters
    ----------
    row
        Canonical source row.
    config
        Audit-report behavior configuration.
    row_number
        One-based source-row position.
    record_id
        Validated source identifier.

    Returns
    -------
    tuple[dict[str, object], ...]
        One flattened row per analyzed study-posting field.

    Raises
    ------
    AuditRowError
        If required payloads are absent, malformed, or violate study-posting
        policy.
    """
    suggested_value = _required_value(
        row,
        column_name=config.columns.llm_suggestions,
        row_number=row_number,
        record_id=record_id,
    )
    selected_value = _required_value(
        row,
        column_name=config.columns.selected_suggestions,
        row_number=row_number,
        record_id=record_id,
    )
    final_value = _required_value(
        row,
        column_name=config.columns.final_submission,
        row_number=row_number,
        record_id=record_id,
    )

    try:
        suggested, selected, final = parse_analysis_inputs(
            suggested_value,
            selected_value,
            final_value,
            suggested_name=config.columns.llm_suggestions,
            selected_name=config.columns.selected_suggestions,
            final_name=config.columns.final_submission,
        )

        results = analyze_objects(
            suggested,
            selected,
            final,
        )

        flattened = flatten_analysis_results(
            results,
            record_id=record_id,
            include_text=config.include_text,
        )
    except (TypeError, ValueError) as error:
        raise AuditRowError(
            f"analysis failed: {error}",
            row_number=row_number,
            record_id=record_id,
        ) from error

    return tuple(dict(metric_row) for metric_row in flattened)


def process_audit_rows(
    rows: Iterable[Row],
    *,
    config: AuditReportConfig,
) -> Iterator[ProcessedAuditRow]:
    """Process canonical source rows lazily.

    Every source row produces one ``ProcessedAuditRow``. Manual and incomplete
    attempts retain their source records but contain no metric rows. Completed
    AI attempts contain one metric row per analyzed study-posting field.

    Record identifiers must be unique across the input stream.

    Parameters
    ----------
    rows
        Canonical rows from a row source.
    config
        Audit-report behavior configuration.

    Yields
    ------
    ProcessedAuditRow
        One processing result per source row.

    Raises
    ------
    AuditRowError
        If a row is malformed, a record ID is invalid or duplicated, or a
        completed AI row is inconsistent or cannot be analyzed.
    """
    seen_record_ids: set[RecordId] = set()

    for row_number, raw_row in enumerate(rows, start=1):
        row = _require_source_row(
            raw_row,
            row_number=row_number,
        )
        record_id = extract_record_id(
            row,
            config=config,
            row_number=row_number,
        )

        if record_id in seen_record_ids:
            raise AuditRowError(
                "duplicate record ID",
                row_number=row_number,
                record_id=record_id,
            )

        seen_record_ids.add(record_id)

        analyzed = _should_analyze_row(
            row,
            config=config,
            row_number=row_number,
            record_id=record_id,
        )

        metric_rows = (
            analyze_audit_row(
                row,
                config=config,
                row_number=row_number,
                record_id=record_id,
            )
            if analyzed
            else ()
        )

        yield ProcessedAuditRow(
            source_row_number=row_number,
            record_id=record_id,
            record=dict(row),
            analyzed=analyzed,
            metric_rows=metric_rows,
        )
