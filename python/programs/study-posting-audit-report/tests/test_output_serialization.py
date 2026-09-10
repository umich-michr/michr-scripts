"""Tests for canonical report CSV serialization and output options."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import json
from typing import cast

import pytest

from study_posting_audit_report import (
    AuditOutputError,
    AuditReportConfigurationError,
    CsvOutputOptions,
    serialize_csv_value,
)

# ---------------------------------------------------------------------------
# Null and string serialization
# ---------------------------------------------------------------------------


def test_none_uses_configured_null_marker() -> None:
    assert (
        serialize_csv_value(
            None,
            column_name="VALUE",
            null_value="\\N",
        )
        == "\\N"
    )


@pytest.mark.parametrize(
    "value",
    ["", "text", "  padded  ", "NULL", "0"],
    ids=["empty", "text", "padded", "null-looking", "numeric-looking"],
)
def test_string_is_preserved(value: str) -> None:
    assert (
        serialize_csv_value(
            value,
            column_name="VALUE",
            null_value="\\N",
        )
        == value
    )


def test_string_equal_to_reserved_null_marker_is_rejected() -> None:
    with pytest.raises(
        AuditOutputError,
        match="contains the reserved null marker",
    ):
        serialize_csv_value(
            "\\N",
            column_name="VALUE",
            null_value="\\N",
        )


def test_reserved_null_marker_error_names_column() -> None:
    with pytest.raises(
        AuditOutputError,
        match="Column 'OPTIONAL_TEXT'",
    ):
        serialize_csv_value(
            "NULL",
            column_name="OPTIONAL_TEXT",
            null_value="NULL",
        )


# ---------------------------------------------------------------------------
# Boolean and integer serialization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, "true"),
        (False, "false"),
    ],
    ids=["true", "false"],
)
def test_boolean_uses_lowercase_json_style_text(
    value: bool,
    expected: str,
) -> None:
    assert (
        serialize_csv_value(
            value,
            column_name="ACTIVE",
            null_value="\\N",
        )
        == expected
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, "0"),
        (1, "1"),
        (-42, "-42"),
        (10**30, str(10**30)),
    ],
    ids=["zero", "one", "negative", "large"],
)
def test_integer_uses_decimal_text(
    value: int,
    expected: str,
) -> None:
    assert (
        serialize_csv_value(
            value,
            column_name="COUNT",
            null_value="\\N",
        )
        == expected
    )


def test_boolean_is_not_serialized_as_integer() -> None:
    assert (
        serialize_csv_value(
            True,
            column_name="ACTIVE",
            null_value="\\N",
        )
        == "true"
    )


# ---------------------------------------------------------------------------
# Decimal and float serialization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal(0), "0"),
        (Decimal("12.500"), "12.500"),
        (Decimal("-0.25"), "-0.25"),
        (Decimal("1E+3"), "1E+3"),
    ],
    ids=["zero", "trailing-zeroes", "negative", "exponent"],
)
def test_decimal_preserves_decimal_text(
    value: Decimal,
    expected: str,
) -> None:
    assert (
        serialize_csv_value(
            value,
            column_name="AMOUNT",
            null_value="\\N",
        )
        == expected
    )


@pytest.mark.parametrize(
    "value",
    [
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
    ],
    ids=["nan", "positive-infinity", "negative-infinity"],
)
def test_nonfinite_decimal_is_rejected(value: Decimal) -> None:
    with pytest.raises(
        AuditOutputError,
        match="contains a non-finite Decimal",
    ):
        serialize_csv_value(
            value,
            column_name="AMOUNT",
            null_value="\\N",
        )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.0, "0.0"),
        (0.75, "0.75"),
        (-1.25, "-1.25"),
        (1e20, "1e+20"),
    ],
    ids=["zero", "fraction", "negative", "exponent"],
)
def test_float_uses_repr(
    value: float,
    expected: str,
) -> None:
    assert (
        serialize_csv_value(
            value,
            column_name="SCORE",
            null_value="\\N",
        )
        == expected
    )


@pytest.mark.parametrize(
    "value",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
    ids=["nan", "positive-infinity", "negative-infinity"],
)
def test_nonfinite_float_is_rejected(value: float) -> None:
    with pytest.raises(
        AuditOutputError,
        match="contains a non-finite float",
    ):
        serialize_csv_value(
            value,
            column_name="SCORE",
            null_value="\\N",
        )


# ---------------------------------------------------------------------------
# Date and datetime serialization
# ---------------------------------------------------------------------------


def test_date_uses_iso_format() -> None:
    assert (
        serialize_csv_value(
            date(2026, 9, 9),
            column_name="CREATED_DATE",
            null_value="\\N",
        )
        == "2026-09-09"
    )


def test_naive_datetime_uses_iso_format_without_added_timezone() -> None:
    value = datetime.fromisoformat("2026-09-09T14:59:35.123456")

    assert (
        serialize_csv_value(
            value,
            column_name="CREATED_AT",
            null_value="\\N",
        )
        == "2026-09-09T14:59:35.123456"
    )


def test_aware_datetime_preserves_offset() -> None:
    value = datetime(
        2026,
        9,
        9,
        14,
        59,
        35,
        tzinfo=timezone(timedelta(hours=-4)),
    )

    assert (
        serialize_csv_value(
            value,
            column_name="CREATED_AT",
            null_value="\\N",
        )
        == "2026-09-09T14:59:35-04:00"
    )


def test_datetime_is_not_serialized_as_date() -> None:
    value = datetime.fromisoformat("2026-09-09T14:59:35")

    assert (
        serialize_csv_value(
            value,
            column_name="CREATED_AT",
            null_value="\\N",
        )
        == "2026-09-09T14:59:35"
    )


# ---------------------------------------------------------------------------
# JSON-object serialization
# ---------------------------------------------------------------------------


def test_json_object_is_serialized_deterministically() -> None:
    value: dict[str, object] = {
        "z": 1,
        "a": "café",
        "nested": {
            "b": True,
            "a": None,
        },
    }

    serialized = serialize_csv_value(
        value,
        column_name="PAYLOAD",
        null_value="\\N",
    )

    assert serialized == ('{"a":"café","nested":{"a":null,"b":true},"z":1}')


def test_json_object_round_trips_through_json() -> None:
    value: dict[str, object] = {
        "title": "Example",
        "ids": [1, 2],
        "active": True,
    }

    serialized = serialize_csv_value(
        value,
        column_name="PAYLOAD",
        null_value="\\N",
    )

    assert json.loads(serialized) == value


def test_json_object_with_non_string_key_is_rejected() -> None:
    value = cast(
        "dict[str, object]",
        {1: "value"},
    )

    with pytest.raises(
        AuditOutputError,
        match="contains a non-string JSON key",
    ):
        serialize_csv_value(
            value,
            column_name="PAYLOAD",
            null_value="\\N",
        )


def test_json_object_with_unsupported_nested_value_is_rejected() -> None:
    value: dict[str, object] = {
        "unsupported": object(),
    }

    with pytest.raises(
        AuditOutputError,
        match="cannot be serialized as JSON",
    ):
        serialize_csv_value(
            value,
            column_name="PAYLOAD",
            null_value="\\N",
        )


def test_json_object_with_nonfinite_float_is_rejected() -> None:
    value: dict[str, object] = {
        "score": float("nan"),
    }

    with pytest.raises(
        AuditOutputError,
        match="cannot be serialized as JSON",
    ):
        serialize_csv_value(
            value,
            column_name="PAYLOAD",
            null_value="\\N",
        )


# ---------------------------------------------------------------------------
# Unsupported output values
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        [],
        (),
        frozenset({1}),
        b"bytes",
        object(),
    ],
    ids=["list", "tuple", "frozenset", "bytes", "object"],
)
def test_unsupported_output_type_is_rejected(value: object) -> None:
    with pytest.raises(
        AuditOutputError,
        match="has unsupported output type",
    ):
        serialize_csv_value(
            value,
            column_name="VALUE",
            null_value="\\N",
        )


def test_unsupported_type_error_names_type() -> None:
    with pytest.raises(
        AuditOutputError,
        match="unsupported output type list",
    ):
        serialize_csv_value(
            [],
            column_name="VALUE",
            null_value="\\N",
        )


# ---------------------------------------------------------------------------
# CsvOutputOptions
# ---------------------------------------------------------------------------


def test_default_output_options_are_stable() -> None:
    options = CsvOutputOptions()

    assert options.encoding == "utf-8"
    assert options.null_value == "\\N"
    assert options.lineterminator == "\n"


def test_custom_output_options_are_preserved() -> None:
    options = CsvOutputOptions(
        encoding="utf-8-sig",
        null_value="NULL",
        lineterminator="\r\n",
    )

    assert options.encoding == "utf-8-sig"
    assert options.null_value == "NULL"
    assert options.lineterminator == "\r\n"


@pytest.mark.parametrize(
    ("field_name", "kwargs"),
    [
        ("encoding", {"encoding": ""}),
        ("encoding", {"encoding": "   "}),
        ("null_value", {"null_value": ""}),
        ("null_value", {"null_value": "   "}),
    ],
    ids=[
        "empty-encoding",
        "blank-encoding",
        "empty-null-marker",
        "blank-null-marker",
    ],
)
def test_output_options_require_nonblank_strings(
    field_name: str,
    kwargs: dict[str, object],
) -> None:
    with pytest.raises(
        AuditReportConfigurationError,
        match=rf"CSV output {field_name} must be a nonblank string",
    ):
        CsvOutputOptions(**kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field_name", "kwargs"),
    [
        ("encoding", {"encoding": 1}),
        ("null_value", {"null_value": None}),
    ],
    ids=[
        "integer-encoding",
        "none-null-marker",
    ],
)
def test_output_options_reject_non_strings(
    field_name: str,
    kwargs: dict[str, object],
) -> None:
    with pytest.raises(
        AuditReportConfigurationError,
        match=rf"CSV output {field_name} must be a nonblank string",
    ):
        CsvOutputOptions(**kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "value",
    [
        "",
        None,
        b"\n",
    ],
    ids=[
        "empty",
        "none",
        "bytes",
    ],
)
def test_output_lineterminator_requires_nonempty_string(
    value: object,
) -> None:
    invalid_value = cast("str", value)

    with pytest.raises(
        AuditReportConfigurationError,
        match="CSV output lineterminator must be a nonempty string",
    ):
        CsvOutputOptions(
            lineterminator=invalid_value,
        )
