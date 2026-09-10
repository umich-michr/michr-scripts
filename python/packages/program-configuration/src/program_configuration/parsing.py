"""Reusable parsers for raw program-configuration values."""

from collections.abc import Mapping
import json
from pathlib import Path
from typing import cast

_BOOLEAN_TEXT: dict[str, bool] = {
    "true": True,
    "1": True,
    "yes": True,
    "on": True,
    "false": False,
    "0": False,
    "no": False,
    "off": False,
}


def parse_nonblank_string(value: object) -> str:
    """Parse a nonblank string without removing surrounding whitespace."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("expected a nonblank string")

    return value


def parse_boolean(value: object) -> bool:
    """Parse an exact Boolean or an explicit Boolean text value."""
    if type(value) is bool:
        return value

    if isinstance(value, str):
        normalized = value.strip().casefold()

        if normalized in _BOOLEAN_TEXT:
            return _BOOLEAN_TEXT[normalized]

    raise ValueError(
        "expected a Boolean or one of: true, false, 1, 0, yes, no, on, off"
    )


def parse_integer(value: object) -> int:
    """Parse an integer without accepting Booleans or fractional values."""
    if isinstance(value, bool):
        raise TypeError("expected an integer, not a Boolean")

    if isinstance(value, int):
        return value

    if isinstance(value, str):
        text = value.strip()

        if not text:
            raise ValueError("expected integer text")

        try:
            return int(text, 10)
        except ValueError as error:
            raise ValueError("expected base-10 integer text") from error

    raise ValueError("expected an integer or base-10 integer text")


def parse_positive_integer(value: object) -> int:
    """Parse an integer greater than zero."""
    result = parse_integer(value)

    if result <= 0:
        raise ValueError("expected a positive integer")

    return result


def parse_path(value: object) -> Path:
    """Parse a nonblank string or existing ``Path`` object."""
    if isinstance(value, Path):
        return value

    if isinstance(value, str):
        if not value.strip():
            raise ValueError("expected a nonblank path")

        return Path(value)

    raise ValueError("expected a string or Path")


def parse_json_object(value: object) -> dict[str, object]:
    """Parse a JSON object from text or copy a string-keyed mapping."""
    decoded: object = value

    if isinstance(value, str):
        if not value.strip():
            raise ValueError("expected a nonblank JSON object")

        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"invalid JSON at line {error.lineno}, "
                f"column {error.colno}: {error.msg}"
            ) from error

    if not isinstance(decoded, Mapping):
        raise TypeError("expected a JSON object")

    mapping = cast("Mapping[object, object]", decoded)
    result: dict[str, object] = {}

    for key, item in mapping.items():
        if not isinstance(key, str):
            raise TypeError("JSON object keys must be strings")

        result[key] = item

    return result
