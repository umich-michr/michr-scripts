"""Tests for canonical value and row conversion."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import math
import re

import pytest

from tabular_row_sources import (
    ColumnSpec,
    ColumnType,
    RowSchema,
    SourceFormatError,
    ValueConversionError,
    convert_row,
    convert_value,
)


def column(
    data_type: ColumnType,
    *,
    name: str = "VALUE",
    nullable: bool = False,
) -> ColumnSpec:
    """Return a column definition for conversion tests."""
    return ColumnSpec(
        name=name,
        data_type=data_type,
        nullable=nullable,
    )


# ---------------------------------------------------------------------------
# Nullability
# ---------------------------------------------------------------------------


def test_nullable_column_accepts_none() -> None:
    result = convert_value(
        None,
        column=column(ColumnType.STRING, nullable=True),
    )

    assert result is None


def test_nonnullable_column_rejects_none() -> None:
    expected = "Column 'VALUE' is null but the schema column is not nullable"

    with pytest.raises(
        ValueConversionError,
        match=re.escape(expected),
    ):
        convert_value(
            None,
            column=column(ColumnType.STRING),
        )


def test_nullability_error_includes_row_number() -> None:
    expected = "Row 7, column 'VALUE' is null but the schema column is not nullable"

    with pytest.raises(
        ValueConversionError,
        match=re.escape(expected),
    ):
        convert_value(
            None,
            column=column(ColumnType.STRING),
            row_number=7,
        )


# ---------------------------------------------------------------------------
# String conversion
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    ["", "text", "  padded  ", "123"],
    ids=["empty", "text", "padded", "numeric-looking"],
)
def test_string_conversion_preserves_strings(value: str) -> None:
    result = convert_value(
        value,
        column=column(ColumnType.STRING),
    )

    assert result == value
    assert isinstance(result, str)


@pytest.mark.parametrize(
    "value",
    [1, True, b"text", Decimal("1.5")],
    ids=["integer", "boolean", "bytes", "decimal"],
)
def test_string_conversion_rejects_non_strings(value: object) -> None:
    with pytest.raises(
        ValueConversionError,
        match="expected a string",
    ):
        convert_value(
            value,
            column=column(ColumnType.STRING),
        )


# ---------------------------------------------------------------------------
# Integer conversion
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, 0),
        (-5, -5),
        (Decimal(12), 12),
        (Decimal("-0"), 0),
        ("42", 42),
        (" -17 ", -17),
        ("+8", 8),
        ("0012", 12),
    ],
    ids=[
        "zero",
        "negative-int",
        "integral-decimal",
        "negative-zero-decimal",
        "text",
        "padded-text",
        "positive-sign",
        "leading-zeroes",
    ],
)
def test_integer_conversion_accepts_exact_values(
    value: object,
    expected: int,
) -> None:
    result = convert_value(
        value,
        column=column(ColumnType.INTEGER),
    )

    assert result == expected
    assert isinstance(result, int)
    assert not isinstance(result, bool)


def test_integer_conversion_rejects_boolean() -> None:
    with pytest.raises(
        ValueConversionError,
        match="Boolean values are not integers",
    ):
        convert_value(
            True,
            column=column(ColumnType.INTEGER),
        )


@pytest.mark.parametrize(
    "value",
    [
        Decimal("1.5"),
        Decimal("Infinity"),
        Decimal("NaN"),
    ],
    ids=["fractional", "infinity", "nan"],
)
def test_integer_conversion_rejects_nonintegral_decimal(
    value: Decimal,
) -> None:
    with pytest.raises(
        ValueConversionError,
        match="not a finite whole number",
    ):
        convert_value(
            value,
            column=column(ColumnType.INTEGER),
        )


def test_integer_conversion_rejects_empty_text() -> None:
    with pytest.raises(
        ValueConversionError,
        match="empty text is not an integer",
    ):
        convert_value(
            "   ",
            column=column(ColumnType.INTEGER),
        )


@pytest.mark.parametrize(
    "value",
    ["1.5", "one"],
    ids=["fractional-text", "word"],
)
def test_integer_conversion_rejects_invalid_text(value: str) -> None:
    with pytest.raises(
        ValueConversionError,
        match="expected base-10 integer text",
    ):
        convert_value(
            value,
            column=column(ColumnType.INTEGER),
        )


@pytest.mark.parametrize(
    "value",
    [1.0, b"1", object()],
    ids=["float", "bytes", "object"],
)
def test_integer_conversion_rejects_other_types(value: object) -> None:
    with pytest.raises(
        ValueConversionError,
        match="expected an integer, integral Decimal, or integer text",
    ):
        convert_value(
            value,
            column=column(ColumnType.INTEGER),
        )


# ---------------------------------------------------------------------------
# Decimal conversion
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("1.25"), Decimal("1.25")),
        (5, Decimal(5)),
        (-3, Decimal(-3)),
        (0.1, Decimal("0.1")),
        ("12.500", Decimal("12.500")),
        (" -0.75 ", Decimal("-0.75")),
        ("1e3", Decimal("1e3")),
    ],
    ids=[
        "decimal",
        "integer",
        "negative-integer",
        "float-through-text",
        "text",
        "padded-text",
        "exponent-text",
    ],
)
def test_decimal_conversion_accepts_finite_values(
    value: object,
    expected: Decimal,
) -> None:
    result = convert_value(
        value,
        column=column(ColumnType.DECIMAL),
    )

    assert result == expected
    assert isinstance(result, Decimal)


def test_decimal_conversion_rejects_boolean() -> None:
    with pytest.raises(
        ValueConversionError,
        match="Boolean values are not decimals",
    ):
        convert_value(
            False,
            column=column(ColumnType.DECIMAL),
        )


@pytest.mark.parametrize(
    "value",
    [
        Decimal("Infinity"),
        Decimal("-Infinity"),
        Decimal("NaN"),
    ],
    ids=["positive-infinity", "negative-infinity", "nan"],
)
def test_decimal_conversion_rejects_nonfinite_decimal(
    value: Decimal,
) -> None:
    with pytest.raises(
        ValueConversionError,
        match="decimal value must be finite",
    ):
        convert_value(
            value,
            column=column(ColumnType.DECIMAL),
        )


@pytest.mark.parametrize(
    "value",
    [math.inf, -math.inf, math.nan],
    ids=["positive-infinity", "negative-infinity", "nan"],
)
def test_decimal_conversion_rejects_nonfinite_float(value: float) -> None:
    with pytest.raises(
        ValueConversionError,
        match="floating-point value must be finite",
    ):
        convert_value(
            value,
            column=column(ColumnType.DECIMAL),
        )


def test_decimal_conversion_rejects_empty_text() -> None:
    with pytest.raises(
        ValueConversionError,
        match="empty text is not a decimal",
    ):
        convert_value(
            " ",
            column=column(ColumnType.DECIMAL),
        )


@pytest.mark.parametrize(
    "value",
    ["not-a-number", "--1"],
    ids=["word", "invalid-sign"],
)
def test_decimal_conversion_rejects_invalid_text(value: str) -> None:
    with pytest.raises(
        ValueConversionError,
        match="expected decimal text",
    ):
        convert_value(
            value,
            column=column(ColumnType.DECIMAL),
        )


def test_decimal_conversion_rejects_nonfinite_text() -> None:
    with pytest.raises(
        ValueConversionError,
        match="decimal value must be finite",
    ):
        convert_value(
            "Infinity",
            column=column(ColumnType.DECIMAL),
        )


def test_decimal_conversion_rejects_other_type() -> None:
    with pytest.raises(
        ValueConversionError,
        match="expected a number or decimal text",
    ):
        convert_value(
            b"1.25",
            column=column(ColumnType.DECIMAL),
        )


# ---------------------------------------------------------------------------
# Float conversion
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1, 1.0),
        (-2, -2.0),
        (1.25, 1.25),
        (Decimal("2.5"), 2.5),
        ("3.75", 3.75),
        (" -0.5 ", -0.5),
        ("1e2", 100.0),
    ],
    ids=[
        "integer",
        "negative-integer",
        "float",
        "decimal",
        "text",
        "padded-text",
        "exponent-text",
    ],
)
def test_float_conversion_accepts_finite_values(
    value: object,
    expected: float,
) -> None:
    result = convert_value(
        value,
        column=column(ColumnType.FLOAT),
    )

    assert result == pytest.approx(expected)
    assert isinstance(result, float)


def test_float_conversion_rejects_boolean() -> None:
    with pytest.raises(
        ValueConversionError,
        match="Boolean values are not floats",
    ):
        convert_value(
            True,
            column=column(ColumnType.FLOAT),
        )


@pytest.mark.parametrize(
    "value",
    [
        math.inf,
        -math.inf,
        math.nan,
        Decimal("1e999999"),
        "Infinity",
        "NaN",
    ],
    ids=[
        "positive-infinity",
        "negative-infinity",
        "nan",
        "overflowing-decimal",
        "infinity-text",
        "nan-text",
    ],
)
def test_float_conversion_rejects_nonfinite_values(value: object) -> None:
    with pytest.raises(
        ValueConversionError,
        match="must be finite",
    ):
        convert_value(
            value,
            column=column(ColumnType.FLOAT),
        )


def test_float_conversion_rejects_empty_text() -> None:
    with pytest.raises(
        ValueConversionError,
        match="empty text is not a float",
    ):
        convert_value(
            " ",
            column=column(ColumnType.FLOAT),
        )


def test_float_conversion_rejects_invalid_text() -> None:
    with pytest.raises(
        ValueConversionError,
        match="expected floating-point text",
    ):
        convert_value(
            "not-a-float",
            column=column(ColumnType.FLOAT),
        )


def test_float_conversion_rejects_other_type() -> None:
    with pytest.raises(
        ValueConversionError,
        match="expected a number or floating-point text",
    ):
        convert_value(
            b"1.0",
            column=column(ColumnType.FLOAT),
        )


# ---------------------------------------------------------------------------
# Boolean conversion
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, True),
        (False, False),
        (1, True),
        (0, False),
        (Decimal(1), True),
        (Decimal(0), False),
        ("true", True),
        ("TRUE", True),
        (" false ", False),
        ("1", True),
        ("0", False),
    ],
    ids=[
        "true",
        "false",
        "integer-one",
        "integer-zero",
        "decimal-one",
        "decimal-zero",
        "true-text",
        "uppercase-true",
        "padded-false",
        "one-text",
        "zero-text",
    ],
)
def test_boolean_conversion_accepts_explicit_values(
    value: object,
    expected: bool,
) -> None:
    result = convert_value(
        value,
        column=column(ColumnType.BOOLEAN),
    )

    assert result is expected


@pytest.mark.parametrize(
    "value",
    [
        2,
        -1,
        Decimal(2),
        Decimal("NaN"),
        "yes",
        "",
        1.0,
        object(),
    ],
    ids=[
        "integer-two",
        "negative-integer",
        "decimal-two",
        "decimal-nan",
        "yes-text",
        "empty-text",
        "float-one",
        "object",
    ],
)
def test_boolean_conversion_rejects_ambiguous_values(value: object) -> None:
    with pytest.raises(
        ValueConversionError,
        match="accepted Boolean values are true, false, 1, and 0",
    ):
        convert_value(
            value,
            column=column(ColumnType.BOOLEAN),
        )


# ---------------------------------------------------------------------------
# Date conversion
# ---------------------------------------------------------------------------


def test_date_conversion_preserves_date() -> None:
    value = date(2026, 9, 9)

    result = convert_value(
        value,
        column=column(ColumnType.DATE),
    )

    assert result == value
    assert isinstance(result, date)
    assert not isinstance(result, datetime)


def test_date_conversion_parses_iso_text() -> None:
    result = convert_value(
        " 2026-09-09 ",
        column=column(ColumnType.DATE),
    )

    assert result == date(2026, 9, 9)


def test_date_conversion_rejects_datetime() -> None:
    with pytest.raises(
        ValueConversionError,
        match="datetime values are not accepted as dates",
    ):
        convert_value(
            datetime.fromisoformat("2026-09-09T12:30:00"),
            column=column(ColumnType.DATE),
        )


@pytest.mark.parametrize(
    "value",
    ["", "2026-13-40", "09/09/2026"],
    ids=["empty", "invalid-date", "non-iso"],
)
def test_date_conversion_rejects_invalid_text(value: str) -> None:
    with pytest.raises(
        ValueConversionError,
        match="expected an ISO 8601 date",
    ):
        convert_value(
            value,
            column=column(ColumnType.DATE),
        )


def test_date_conversion_rejects_other_type() -> None:
    with pytest.raises(
        ValueConversionError,
        match="expected a date or ISO 8601 date text",
    ):
        convert_value(
            20260909,
            column=column(ColumnType.DATE),
        )


# ---------------------------------------------------------------------------
# Datetime conversion
# ---------------------------------------------------------------------------


def test_datetime_conversion_preserves_naive_datetime() -> None:
    value = datetime.fromisoformat("2026-09-09T14:59:35")

    result = convert_value(
        value,
        column=column(ColumnType.DATETIME),
    )

    assert result == value
    assert isinstance(result, datetime)
    assert result.tzinfo is None


def test_datetime_conversion_preserves_timezone_aware_datetime() -> None:
    zone = timezone(timedelta(hours=-4))
    value = datetime(2026, 9, 9, 14, 59, 35, tzinfo=zone)

    result = convert_value(
        value,
        column=column(ColumnType.DATETIME),
    )

    assert result == value
    assert isinstance(result, datetime)
    assert result.utcoffset() == timedelta(hours=-4)


@pytest.mark.parametrize(
    "value",
    [
        "2026-09-09T14:59:35",
        " 2026-09-09T14:59:35 ",
    ],
    ids=["iso", "padded"],
)
def test_datetime_conversion_parses_naive_iso_text(value: str) -> None:
    result = convert_value(
        value,
        column=column(ColumnType.DATETIME),
    )

    assert result == datetime.fromisoformat("2026-09-09T14:59:35")
    assert isinstance(result, datetime)
    assert result.tzinfo is None


@pytest.mark.parametrize(
    "value",
    [
        "2026-09-09T14:59:35Z",
        "2026-09-09T14:59:35z",
        "2026-09-09T14:59:35+00:00",
    ],
    ids=["uppercase-z", "lowercase-z", "explicit-offset"],
)
def test_datetime_conversion_parses_utc_text(value: str) -> None:
    result = convert_value(
        value,
        column=column(ColumnType.DATETIME),
    )

    assert isinstance(result, datetime)
    assert result.utcoffset() == timedelta(0)


def test_datetime_conversion_preserves_text_offset() -> None:
    result = convert_value(
        "2026-09-09T14:59:35-04:00",
        column=column(ColumnType.DATETIME),
    )

    assert isinstance(result, datetime)
    assert result.utcoffset() == timedelta(hours=-4)


@pytest.mark.parametrize(
    "value",
    ["", "not-a-datetime", "2026-99-99T40:00:00"],
    ids=["empty", "word", "invalid-fields"],
)
def test_datetime_conversion_rejects_invalid_text(value: str) -> None:
    with pytest.raises(
        ValueConversionError,
        match="expected an ISO 8601 datetime",
    ):
        convert_value(
            value,
            column=column(ColumnType.DATETIME),
        )


@pytest.mark.parametrize(
    "value",
    [date(2026, 9, 9), 20260909],
    ids=["date", "integer"],
)
def test_datetime_conversion_rejects_other_types(value: object) -> None:
    with pytest.raises(
        ValueConversionError,
        match="expected a datetime or ISO 8601 datetime text",
    ):
        convert_value(
            value,
            column=column(ColumnType.DATETIME),
        )


# ---------------------------------------------------------------------------
# JSON-object conversion
# ---------------------------------------------------------------------------


def test_json_object_conversion_parses_text() -> None:
    result = convert_value(
        '{"title": "Example", "ids": [1, 2]}',
        column=column(ColumnType.JSON_OBJECT),
    )

    assert result == {
        "title": "Example",
        "ids": [1, 2],
    }


def test_json_object_conversion_parses_utf8_bytes() -> None:
    result = convert_value(
        b'{"title": "Example"}',
        column=column(ColumnType.JSON_OBJECT),
    )

    assert result == {"title": "Example"}


def test_json_object_conversion_copies_dictionary() -> None:
    original: dict[str, object] = {"title": "Example"}

    result = convert_value(
        original,
        column=column(ColumnType.JSON_OBJECT),
    )

    assert result == original
    assert result is not original


def test_json_object_conversion_rejects_invalid_utf8() -> None:
    with pytest.raises(
        ValueConversionError,
        match="JSON bytes are not valid UTF-8",
    ):
        convert_value(
            b"\xff\xfe{}",
            column=column(ColumnType.JSON_OBJECT),
        )


def test_json_object_conversion_rejects_empty_text() -> None:
    with pytest.raises(
        ValueConversionError,
        match="empty text is not a JSON object",
    ):
        convert_value(
            " ",
            column=column(ColumnType.JSON_OBJECT),
        )


def test_json_object_conversion_reports_invalid_json() -> None:
    with pytest.raises(
        ValueConversionError,
        match="invalid JSON at line 1, column 2",
    ):
        convert_value(
            "{",
            column=column(ColumnType.JSON_OBJECT),
        )


@pytest.mark.parametrize(
    "value",
    [
        "[]",
        '"text"',
        "42",
        "true",
        "null",
    ],
    ids=["array", "string", "integer", "boolean", "null"],
)
def test_json_object_conversion_rejects_non_object_json(
    value: str,
) -> None:
    with pytest.raises(
        ValueConversionError,
        match="JSON value must be an object",
    ):
        convert_value(
            value,
            column=column(ColumnType.JSON_OBJECT),
        )


def test_json_object_conversion_rejects_non_string_key() -> None:
    with pytest.raises(
        ValueConversionError,
        match="JSON object keys must be strings",
    ):
        convert_value(
            {1: "value"},
            column=column(ColumnType.JSON_OBJECT),
        )


# ---------------------------------------------------------------------------
# Row conversion
# ---------------------------------------------------------------------------


def representative_schema() -> RowSchema:
    """Return a schema covering every canonical data type."""
    return RowSchema(
        columns=(
            column(ColumnType.INTEGER, name="ID"),
            column(ColumnType.STRING, name="TITLE"),
            column(ColumnType.DECIMAL, name="AMOUNT"),
            column(ColumnType.FLOAT, name="SCORE"),
            column(ColumnType.BOOLEAN, name="ACTIVE"),
            column(ColumnType.DATE, name="CREATED_DATE"),
            column(ColumnType.DATETIME, name="CREATED_AT"),
            column(ColumnType.JSON_OBJECT, name="PAYLOAD"),
            column(
                ColumnType.STRING,
                name="OPTIONAL_TEXT",
                nullable=True,
            ),
        )
    )


def test_convert_row_produces_canonical_values_in_schema_order() -> None:
    source: dict[object, object] = {
        "ID": "42",
        "TITLE": "Example",
        "AMOUNT": "12.50",
        "SCORE": "0.75",
        "ACTIVE": "true",
        "CREATED_DATE": "2026-09-09",
        "CREATED_AT": "2026-09-09T14:59:35Z",
        "PAYLOAD": '{"name": "Example"}',
        "OPTIONAL_TEXT": None,
    }

    result = convert_row(
        source,
        schema=representative_schema(),
        row_number=3,
    )

    assert tuple(result) == (
        "ID",
        "TITLE",
        "AMOUNT",
        "SCORE",
        "ACTIVE",
        "CREATED_DATE",
        "CREATED_AT",
        "PAYLOAD",
        "OPTIONAL_TEXT",
    )

    assert result["ID"] == 42
    assert result["TITLE"] == "Example"
    assert result["AMOUNT"] == Decimal("12.50")
    assert result["SCORE"] == pytest.approx(0.75)
    assert result["ACTIVE"] is True
    assert result["CREATED_DATE"] == date(2026, 9, 9)

    created_at = result["CREATED_AT"]
    assert isinstance(created_at, datetime)
    assert created_at.utcoffset() == timedelta(0)

    assert result["PAYLOAD"] == {"name": "Example"}
    assert result["OPTIONAL_TEXT"] is None


def test_convert_row_returns_fresh_dictionary() -> None:
    source: dict[object, object] = {
        "ID": 1,
        "TITLE": "Example",
    }
    schema = RowSchema(
        columns=(
            column(ColumnType.INTEGER, name="ID"),
            column(ColumnType.STRING, name="TITLE"),
        )
    )

    result = convert_row(
        source,
        schema=schema,
    )

    assert result == source
    assert result is not source


def test_convert_row_rejects_wrong_column_order() -> None:
    source: dict[object, object] = {
        "TITLE": "Example",
        "ID": 1,
    }
    schema = RowSchema(
        columns=(
            column(ColumnType.INTEGER, name="ID"),
            column(ColumnType.STRING, name="TITLE"),
        )
    )
    expected = (
        "Source row columns do not match schema order: "
        "expected ('ID', 'TITLE'), received ('TITLE', 'ID')"
    )

    with pytest.raises(
        SourceFormatError,
        match=re.escape(expected),
    ):
        convert_row(
            source,
            schema=schema,
        )


def test_convert_row_rejects_missing_column() -> None:
    source: dict[object, object] = {"ID": 1}
    schema = RowSchema(
        columns=(
            column(ColumnType.INTEGER, name="ID"),
            column(ColumnType.STRING, name="TITLE"),
        )
    )

    with pytest.raises(
        SourceFormatError,
        match="columns do not match schema order",
    ):
        convert_row(
            source,
            schema=schema,
        )


def test_convert_row_rejects_unexpected_column() -> None:
    source: dict[object, object] = {
        "ID": 1,
        "TITLE": "Example",
        "EXTRA": "Unexpected",
    }
    schema = RowSchema(
        columns=(
            column(ColumnType.INTEGER, name="ID"),
            column(ColumnType.STRING, name="TITLE"),
        )
    )

    with pytest.raises(
        SourceFormatError,
        match="columns do not match schema order",
    ):
        convert_row(
            source,
            schema=schema,
        )


def test_convert_row_rejects_non_string_column_name() -> None:
    source: dict[object, object] = {1: "value"}
    schema = RowSchema(columns=(column(ColumnType.STRING, name="ID"),))

    with pytest.raises(
        SourceFormatError,
        match="column names must be strings",
    ):
        convert_row(
            source,
            schema=schema,
        )


def test_convert_row_rejects_blank_column_name() -> None:
    source: dict[object, object] = {"": "value"}
    schema = RowSchema(columns=(column(ColumnType.STRING, name="ID"),))

    with pytest.raises(
        SourceFormatError,
        match="contains a blank column name",
    ):
        convert_row(
            source,
            schema=schema,
        )


def test_convert_row_error_contains_row_and_column_context() -> None:
    source: dict[object, object] = {"ID": "not-an-integer"}
    schema = RowSchema(columns=(column(ColumnType.INTEGER, name="ID"),))

    with pytest.raises(
        ValueConversionError,
        match="Row 12, column 'ID'",
    ):
        convert_row(
            source,
            schema=schema,
            row_number=12,
        )


def test_convert_row_shape_error_contains_row_number() -> None:
    source: dict[object, object] = {"WRONG": 1}
    schema = RowSchema(columns=(column(ColumnType.INTEGER, name="ID"),))

    with pytest.raises(
        SourceFormatError,
        match="Source row 8 columns do not match schema order",
    ):
        convert_row(
            source,
            schema=schema,
            row_number=8,
        )
