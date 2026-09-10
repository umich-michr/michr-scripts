"""Pure transformation of canonical audit rows into field-level metrics.

This module owns payload-state classification, source-column mapping, record-ID
validation, duplicate detection, and composition with
``study-posting-ai-analysis``.

It performs no database access, file I/O, logging, aggregation, or output
writing.
"""

from collections.abc import Iterable, Iterator, Mapping
from enum import Enum
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


class PayloadState(Enum):
    """Valid presence states for one row's three analysis payloads."""

    ANALYZABLE = "analyzable"
    SKIPPED = "skipped"


def validate_source_schema(
    schema: RowSchema,
    *,
    config: AuditReportConfig,
) -> None:
    """Require every configured audit column in the source schema.

    Extra source columns are permitted and preserved in ``records.csv``.
    Required analysis columns may appear anywhere in the source schema.

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

    # Runtime validation establishes the outer mapping shape. The cast changes
    # source element types from Unknown to object so keys can be narrowed.
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


def classify_payload_state(
    row: Mapping[str, object],
    *,
    config: AuditReportConfig,
    row_number: int,
    record_id: RecordId,
) -> PayloadState:
    """Classify the presence of one row's three analysis payloads.

    All three null payloads produce ``PayloadState.SKIPPED``. All three
    non-null payloads produce ``PayloadState.ANALYZABLE``. A mixture of null
    and non-null payloads is an inconsistent source row.

    Raises
    ------
    AuditRowError
        If a configured payload column is absent or payload presence is
        partial.
    """
    payloads = {
        column_name: _required_value(
            row,
            column_name=column_name,
            row_number=row_number,
            record_id=record_id,
        )
        for column_name in config.columns.payload_columns
    }
    null_columns = [
        column_name for column_name, value in payloads.items() if value is None
    ]

    if len(null_columns) == len(payloads):
        return PayloadState.SKIPPED

    if not null_columns:
        return PayloadState.ANALYZABLE

    present_columns = [
        column_name for column_name, value in payloads.items() if value is not None
    ]

    raise AuditRowError(
        "analysis payloads must be either all null or all present; "
        f"null columns: {null_columns}; present columns: {present_columns}",
        row_number=row_number,
        record_id=record_id,
    )


def analyze_audit_row(
    row: Mapping[str, object],
    *,
    config: AuditReportConfig,
    row_number: int,
    record_id: RecordId,
) -> tuple[dict[str, object], ...]:
    """Analyze one row whose three payloads are present.

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
        If required analysis payloads are absent, malformed, or violate
        study-posting policy.
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

    Every source row produces one ``ProcessedAuditRow``. Rows with three null
    payloads retain their source record but contain no metric rows. Rows with
    three present payloads contain one metric row per analyzed study-posting
    field. Partial payload presence is rejected.

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
        If a row is malformed, a record ID is invalid or duplicated, payload
        presence is partial, or an analyzable row cannot be analyzed.
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

        payload_state = classify_payload_state(
            row,
            config=config,
            row_number=row_number,
            record_id=record_id,
        )
        analyzed = payload_state is PayloadState.ANALYZABLE

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
