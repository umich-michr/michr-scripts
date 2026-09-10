"""Canonical value and row conversion for tabular sources.

CSV and database sources may receive different native representations. This
module converts those values into the canonical Python types declared by a
``RowSchema``.

Conversion is deliberately strict. It rejects ambiguous or lossy values rather
than silently guessing. Source adapters may perform source-specific extraction,
but they must use this shared layer for canonical conversion and nullability.
"""

from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import json
import math

from tabular_row_sources.errors import (
    SourceFormatError,
    ValueConversionError,
)
from tabular_row_sources.models import (
    ColumnSpec,
    ColumnType,
    Row,
    RowSchema,
)

_BOOLEAN_TEXT_VALUES: dict[str, bool] = {
    "true": True,
    "1": True,
    "false": False,
    "0": False,
}


def _value_context(
    column: ColumnSpec,
    *,
    row_number: int | None,
) -> str:
    """Return error-message context for one column value."""
    if row_number is None:
        return f"Column {column.name!r}"

    return f"Row {row_number}, column {column.name!r}"


def _row_context(row_number: int | None) -> str:
    """Return error-message context for one row."""
    if row_number is None:
        return "Source row"

    return f"Source row {row_number}"


def _conversion_error(
    column: ColumnSpec,
    value: object,
    *,
    row_number: int | None,
    detail: str | None = None,
) -> ValueConversionError:
    """Build a consistent value-conversion exception."""
    context = _value_context(column, row_number=row_number)
    message = f"{context} cannot convert {value!r} to {column.data_type.value}"

    if detail is not None:
        message = f"{message}: {detail}"

    return ValueConversionError(message)


def _convert_string(
    value: object,
    *,
    column: ColumnSpec,
    row_number: int | None,
) -> str:
    """Convert a value to the canonical string type."""
    if not isinstance(value, str):
        raise _conversion_error(
            column,
            value,
            row_number=row_number,
            detail="expected a string",
        )

    return value


def _convert_integer(
    value: object,
    *,
    column: ColumnSpec,
    row_number: int | None,
) -> int:
    """Convert a value to an integer without truncation."""
    if isinstance(value, bool):
        raise _conversion_error(
            column,
            value,
            row_number=row_number,
            detail="Boolean values are not integers",
        )

    if isinstance(value, int):
        return value

    if isinstance(value, Decimal):
        if not value.is_finite() or value != value.to_integral_value():
            raise _conversion_error(
                column,
                value,
                row_number=row_number,
                detail="decimal value is not a finite whole number",
            )

        return int(value)

    if isinstance(value, str):
        text = value.strip()

        if not text:
            raise _conversion_error(
                column,
                value,
                row_number=row_number,
                detail="empty text is not an integer",
            )

        try:
            return int(text, 10)
        except ValueError as error:
            raise _conversion_error(
                column,
                value,
                row_number=row_number,
                detail="expected base-10 integer text",
            ) from error

    raise _conversion_error(
        column,
        value,
        row_number=row_number,
        detail="expected an integer, integral Decimal, or integer text",
    )


def _decimal_from_text(
    text: str,
    *,
    column: ColumnSpec,
    original_value: object,
    row_number: int | None,
) -> Decimal:
    """Parse one finite decimal from text."""
    try:
        result = Decimal(text)
    except InvalidOperation as error:
        raise _conversion_error(
            column,
            original_value,
            row_number=row_number,
            detail="expected decimal text",
        ) from error

    if not result.is_finite():
        raise _conversion_error(
            column,
            original_value,
            row_number=row_number,
            detail="decimal value must be finite",
        )

    return result


def _convert_decimal(
    value: object,
    *,
    column: ColumnSpec,
    row_number: int | None,
) -> Decimal:
    """Convert a value to a finite ``Decimal``."""
    if isinstance(value, bool):
        raise _conversion_error(
            column,
            value,
            row_number=row_number,
            detail="Boolean values are not decimals",
        )

    if isinstance(value, Decimal):
        if not value.is_finite():
            raise _conversion_error(
                column,
                value,
                row_number=row_number,
                detail="decimal value must be finite",
            )

        return value

    if isinstance(value, int):
        return Decimal(value)

    if isinstance(value, float):
        if not math.isfinite(value):
            raise _conversion_error(
                column,
                value,
                row_number=row_number,
                detail="floating-point value must be finite",
            )

        # Converting through str avoids exposing the binary expansion of a
        # floating-point value such as 0.1.
        return Decimal(str(value))

    if isinstance(value, str):
        text = value.strip()

        if not text:
            raise _conversion_error(
                column,
                value,
                row_number=row_number,
                detail="empty text is not a decimal",
            )

        return _decimal_from_text(
            text,
            column=column,
            original_value=value,
            row_number=row_number,
        )

    raise _conversion_error(
        column,
        value,
        row_number=row_number,
        detail="expected a number or decimal text",
    )


def _convert_float(
    value: object,
    *,
    column: ColumnSpec,
    row_number: int | None,
) -> float:
    """Convert a value to a finite floating-point number."""
    if isinstance(value, bool):
        raise _conversion_error(
            column,
            value,
            row_number=row_number,
            detail="Boolean values are not floats",
        )

    if isinstance(value, (int, float, Decimal)):
        try:
            result = float(value)
        except (OverflowError, ValueError) as error:
            raise _conversion_error(
                column,
                value,
                row_number=row_number,
                detail="numeric value cannot be represented as a float",
            ) from error

    elif isinstance(value, str):
        text = value.strip()

        if not text:
            raise _conversion_error(
                column,
                value,
                row_number=row_number,
                detail="empty text is not a float",
            )

        try:
            result = float(text)
        except ValueError as error:
            raise _conversion_error(
                column,
                value,
                row_number=row_number,
                detail="expected floating-point text",
            ) from error

    else:
        raise _conversion_error(
            column,
            value,
            row_number=row_number,
            detail="expected a number or floating-point text",
        )

    if not math.isfinite(result):
        raise _conversion_error(
            column,
            value,
            row_number=row_number,
            detail="floating-point value must be finite",
        )

    return result


def _convert_boolean(
    value: object,
    *,
    column: ColumnSpec,
    row_number: int | None,
) -> bool:
    """Convert a value using an explicit Boolean mapping."""
    if type(value) is bool:
        return value

    if isinstance(value, int) and value in {0, 1}:
        return value == 1

    if (
        isinstance(value, Decimal)
        and value.is_finite()
        and value in {Decimal(0), Decimal(1)}
    ):
        return value == Decimal(1)

    if isinstance(value, str):
        normalized = value.strip().casefold()

        if normalized in _BOOLEAN_TEXT_VALUES:
            return _BOOLEAN_TEXT_VALUES[normalized]

    raise _conversion_error(
        column,
        value,
        row_number=row_number,
        detail="accepted Boolean values are true, false, 1, and 0",
    )


def _convert_date(
    value: object,
    *,
    column: ColumnSpec,
    row_number: int | None,
) -> date:
    """Convert a value to ``date`` but never silently accept ``datetime``."""
    if isinstance(value, datetime):
        raise _conversion_error(
            column,
            value,
            row_number=row_number,
            detail="datetime values are not accepted as dates",
        )

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        text = value.strip()

        try:
            return date.fromisoformat(text)
        except ValueError as error:
            raise _conversion_error(
                column,
                value,
                row_number=row_number,
                detail="expected an ISO 8601 date",
            ) from error

    raise _conversion_error(
        column,
        value,
        row_number=row_number,
        detail="expected a date or ISO 8601 date text",
    )


def _convert_datetime(
    value: object,
    *,
    column: ColumnSpec,
    row_number: int | None,
) -> datetime:
    """Convert a value to ``datetime`` while preserving timezone information."""
    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        text = value.strip()

        # Normalize the common UTC designator explicitly. This keeps behavior
        # clear even if runtime parsing rules change.
        if text.endswith(("Z", "z")):
            text = f"{text[:-1]}+00:00"

        try:
            return datetime.fromisoformat(text)
        except ValueError as error:
            raise _conversion_error(
                column,
                value,
                row_number=row_number,
                detail="expected an ISO 8601 datetime",
            ) from error

    raise _conversion_error(
        column,
        value,
        row_number=row_number,
        detail="expected a datetime or ISO 8601 datetime text",
    )


def _validate_json_object(
    value: dict[object, object],
    *,
    column: ColumnSpec,
    original_value: object,
    row_number: int | None,
) -> dict[str, object]:
    """Validate JSON-object keys and return a fresh dictionary."""
    result: dict[str, object] = {}

    for key, item in value.items():
        if not isinstance(key, str):
            raise _conversion_error(
                column,
                original_value,
                row_number=row_number,
                detail="JSON object keys must be strings",
            )

        result[key] = item

    return result


def _convert_json_object(
    value: object,
    *,
    column: ColumnSpec,
    row_number: int | None,
) -> dict[str, object]:
    """Convert JSON text, UTF-8 bytes, or a dictionary to a fresh object."""
    original_value = value

    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8")
        except UnicodeDecodeError as error:
            raise _conversion_error(
                column,
                original_value,
                row_number=row_number,
                detail="JSON bytes are not valid UTF-8",
            ) from error

    if isinstance(value, str):
        if not value.strip():
            raise _conversion_error(
                column,
                original_value,
                row_number=row_number,
                detail="empty text is not a JSON object",
            )

        try:
            value = json.loads(value)
        except json.JSONDecodeError as error:
            raise _conversion_error(
                column,
                original_value,
                row_number=row_number,
                detail=(
                    f"invalid JSON at line {error.lineno}, "
                    f"column {error.colno}: {error.msg}"
                ),
            ) from error

    if not isinstance(value, dict):
        raise _conversion_error(
            column,
            original_value,
            row_number=row_number,
            detail="JSON value must be an object",
        )

    mapping: dict[object, object] = value

    return _validate_json_object(
        mapping,
        column=column,
        original_value=original_value,
        row_number=row_number,
    )


def convert_value(
    value: object,
    *,
    column: ColumnSpec,
    row_number: int | None = None,
) -> object:
    """Convert one source value to its canonical schema type.

    Parameters
    ----------
    value
        Native source value.
    column
        Column definition controlling conversion and nullability.
    row_number
        Optional one-based source row number used in error messages.

    Returns
    -------
    object
        Value in the canonical Python type declared by ``column``.

    Raises
    ------
    ValueConversionError
        If nullability is violated or conversion fails.
    """
    if value is None:
        if column.nullable:
            return None

        context = _value_context(column, row_number=row_number)
        raise ValueConversionError(
            f"{context} is null but the schema column is not nullable"
        )

    converters = {
        ColumnType.STRING: _convert_string,
        ColumnType.INTEGER: _convert_integer,
        ColumnType.DECIMAL: _convert_decimal,
        ColumnType.FLOAT: _convert_float,
        ColumnType.BOOLEAN: _convert_boolean,
        ColumnType.DATE: _convert_date,
        ColumnType.DATETIME: _convert_datetime,
        ColumnType.JSON_OBJECT: _convert_json_object,
    }

    converter = converters[column.data_type]

    return converter(
        value,
        column=column,
        row_number=row_number,
    )


def _validate_mapping_keys(
    source_row: Mapping[object, object],
    *,
    row_number: int | None,
) -> tuple[str, ...]:
    """Validate source-row keys and preserve their order."""
    names: list[str] = []

    for key in source_row:
        if not isinstance(key, str):
            raise SourceFormatError(
                f"{_row_context(row_number)} column names must be strings"
            )

        if not key.strip():
            raise SourceFormatError(
                f"{_row_context(row_number)} contains a blank column name"
            )

        names.append(key)

    return tuple(names)


def convert_row(
    source_row: Mapping[object, object],
    *,
    schema: RowSchema,
    row_number: int | None = None,
) -> Row:
    """Validate and convert one mapping-shaped source row.

    Source columns must have exactly the schema's case-sensitive names. Source
    order may differ; the returned row always follows schema order.

    Parameters
    ----------
    source_row
        Mapping of source column names to native values.
    schema
        Canonical output schema.
    row_number
        Optional one-based source row number used in error messages.

    Returns
    -------
    Row
        Fresh dictionary containing canonical values in schema order.

    Raises
    ------
    SourceFormatError
        If source columns differ from the schema.
    ValueConversionError
        If a value violates nullability or cannot be converted.
    """
    actual_names = _validate_mapping_keys(
        source_row,
        row_number=row_number,
    )
    expected_names = schema.column_names
    actual_name_set = set(actual_names)
    expected_name_set = set(expected_names)

    missing = [name for name in expected_names if name not in actual_name_set]
    unexpected = [name for name in actual_names if name not in expected_name_set]

    if missing or unexpected:
        raise SourceFormatError(
            f"{_row_context(row_number)} columns do not match schema names: "
            f"missing {missing!r}; unexpected {unexpected!r}"
        )

    result: Row = {}

    for column in schema.columns:
        result[column.name] = convert_value(
            source_row[column.name],
            column=column,
            row_number=row_number,
        )

    return result
