"""Tests for reusable configuration parsers."""

from pathlib import Path
from typing import cast

import pytest

from program_configuration import (
    parse_boolean,
    parse_integer,
    parse_json_object,
    parse_nonblank_string,
    parse_path,
    parse_positive_integer,
)


@pytest.mark.parametrize(
    "value",
    ["text", " padded ", "\tvalue\n"],
    ids=["plain", "padded", "control-whitespace"],
)
def test_parse_nonblank_string_preserves_value(value: str) -> None:
    assert parse_nonblank_string(value) == value


@pytest.mark.parametrize(
    "value",
    ["", "   ", "\n\t", None, 42],
    ids=["empty", "spaces", "control-whitespace", "none", "integer"],
)
def test_parse_nonblank_string_rejects_invalid_value(value: object) -> None:
    with pytest.raises(
        ValueError,
        match="expected a nonblank string",
    ):
        parse_nonblank_string(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, True),
        (False, False),
        ("true", True),
        ("TRUE", True),
        (" 1 ", True),
        ("yes", True),
        ("ON", True),
        ("false", False),
        ("FALSE", False),
        (" 0 ", False),
        ("no", False),
        ("OFF", False),
    ],
    ids=[
        "true",
        "false",
        "true-text",
        "uppercase-true",
        "one",
        "yes",
        "on",
        "false-text",
        "uppercase-false",
        "zero",
        "no",
        "off",
    ],
)
def test_parse_boolean_accepts_explicit_values(
    value: object,
    expected: bool,
) -> None:
    assert parse_boolean(value) is expected


@pytest.mark.parametrize(
    "value",
    ["", "maybe", 1, 0, None, object()],
    ids=["empty", "word", "integer-one", "integer-zero", "none", "object"],
)
def test_parse_boolean_rejects_other_values(value: object) -> None:
    with pytest.raises(
        ValueError,
        match="expected a Boolean or one of",
    ):
        parse_boolean(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, 0),
        (7, 7),
        (-4, -4),
        ("0", 0),
        (" 12 ", 12),
        ("-8", -8),
        ("+3", 3),
        ("0012", 12),
    ],
    ids=[
        "zero",
        "positive",
        "negative",
        "zero-text",
        "padded-text",
        "negative-text",
        "positive-sign",
        "leading-zeroes",
    ],
)
def test_parse_integer_accepts_integer_values(
    value: object,
    expected: int,
) -> None:
    result = parse_integer(value)

    assert result == expected
    assert isinstance(result, int)
    assert not isinstance(result, bool)


@pytest.mark.parametrize(
    "value",
    [True, False],
    ids=["true", "false"],
)
def test_parse_integer_rejects_boolean(value: bool) -> None:
    with pytest.raises(
        TypeError,
        match="expected an integer, not a Boolean",
    ):
        parse_integer(value)


@pytest.mark.parametrize(
    "value",
    ["", "   "],
    ids=["empty", "spaces"],
)
def test_parse_integer_rejects_blank_text(value: str) -> None:
    with pytest.raises(
        ValueError,
        match="expected integer text",
    ):
        parse_integer(value)


@pytest.mark.parametrize(
    "value",
    ["1.5", "one"],
    ids=["fractional", "word"],
)
def test_parse_integer_rejects_invalid_text(value: str) -> None:
    with pytest.raises(
        ValueError,
        match="expected base-10 integer text",
    ):
        parse_integer(value)


@pytest.mark.parametrize(
    "value",
    [1.5, None, b"1", object()],
    ids=["float", "none", "bytes", "object"],
)
def test_parse_integer_rejects_invalid_type(value: object) -> None:
    with pytest.raises(
        ValueError,
        match="expected an integer or base-10 integer text",
    ):
        parse_integer(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1, 1),
        (42, 42),
        ("1", 1),
        (" 25 ", 25),
    ],
    ids=["one", "integer", "text-one", "padded-text"],
)
def test_parse_positive_integer_accepts_positive_values(
    value: object,
    expected: int,
) -> None:
    assert parse_positive_integer(value) == expected


@pytest.mark.parametrize(
    "value",
    [0, -1, "0", "-4"],
    ids=["zero", "negative", "zero-text", "negative-text"],
)
def test_parse_positive_integer_rejects_nonpositive_values(
    value: object,
) -> None:
    with pytest.raises(
        ValueError,
        match="expected a positive integer",
    ):
        parse_positive_integer(value)


def test_parse_path_preserves_path() -> None:
    value = Path("input/schema.json")

    assert parse_path(value) is value


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("input/schema.json", Path("input/schema.json")),
        (" padded/path ", Path(" padded/path ")),
    ],
    ids=["plain", "padded"],
)
def test_parse_path_accepts_nonblank_string(
    value: str,
    expected: Path,
) -> None:
    assert parse_path(value) == expected


@pytest.mark.parametrize(
    "value",
    ["", "   "],
    ids=["empty", "spaces"],
)
def test_parse_path_rejects_blank_string(value: str) -> None:
    with pytest.raises(
        ValueError,
        match="expected a nonblank path",
    ):
        parse_path(value)


@pytest.mark.parametrize(
    "value",
    [None, 42, object()],
    ids=["none", "integer", "object"],
)
def test_parse_path_rejects_invalid_type(value: object) -> None:
    with pytest.raises(
        ValueError,
        match="expected a string or Path",
    ):
        parse_path(value)


def test_parse_json_object_parses_text() -> None:
    result = parse_json_object('{"name":"example","count":2,"active":true}')

    assert result == {
        "name": "example",
        "count": 2,
        "active": True,
    }


def test_parse_json_object_copies_mapping() -> None:
    original: dict[str, object] = {
        "name": "example",
        "items": [1, 2],
    }

    result = parse_json_object(original)

    assert result == original
    assert result is not original


def test_parse_json_object_rejects_blank_text() -> None:
    with pytest.raises(
        ValueError,
        match="expected a nonblank JSON object",
    ):
        parse_json_object("   ")


def test_parse_json_object_reports_invalid_json() -> None:
    with pytest.raises(
        ValueError,
        match="invalid JSON at line 1, column 2",
    ):
        parse_json_object("{")


@pytest.mark.parametrize(
    "value",
    [
        "[]",
        '"text"',
        "42",
        "true",
        "null",
        [],
        42,
        None,
    ],
    ids=[
        "json-array",
        "json-string",
        "json-integer",
        "json-boolean",
        "json-null",
        "list",
        "integer",
        "none",
    ],
)
def test_parse_json_object_rejects_non_mapping(value: object) -> None:
    with pytest.raises(
        TypeError,
        match="expected a JSON object",
    ):
        parse_json_object(value)


def test_parse_json_object_rejects_non_string_key() -> None:
    value = cast(
        "dict[str, object]",
        {1: "value"},
    )

    with pytest.raises(
        TypeError,
        match="JSON object keys must be strings",
    ):
        parse_json_object(value)
