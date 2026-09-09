"""Runtime validation helpers for values arriving from decoded JSON.

Pure functions only.

Public analysis functions annotate their parameters with the types they
document, but the values ultimately originate from JSON columns and carry no
static guarantee. These helpers accept ``object`` so that ``isinstance``
narrowing is genuine rather than statically redundant, and so that the raised
exception type and message are defined in one place.

Container validators inspect every element and return a newly constructed,
correctly typed container. Narrowing alone would leave element types unknown,
so returning the original object would be statically unsound.

Do not replace these checks with truthiness tests. ``None`` must raise
``TypeError`` rather than ``AttributeError``, and the declared exception type
for each failure is part of the tested contract.
"""

from typing import cast


def require_string(value: object, *, parameter_name: str) -> str:
    """Return the value when it is a string.

    An empty string is permitted: a form field initialized empty is valid input.

    Raises
    ------
    TypeError
        If the value is not a string.
    """
    if not isinstance(value, str):
        raise TypeError(f"{parameter_name} must be a string")

    return value


def require_non_blank_string(value: object, *, parameter_name: str) -> str:
    """Return the value when it is a string containing non-whitespace text.

    Raises
    ------
    ValueError
        If the value is not a string, or contains only whitespace.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{parameter_name} must be a non-empty string")

    return value


def require_object(value: object, *, parameter_name: str) -> dict[str, object]:
    """Return a mapping with string keys, built from a JSON object.

    Raises
    ------
    TypeError
        If the value is not a dictionary, or has a non-string key.
    """
    if not isinstance(value, dict):
        raise TypeError(f"{parameter_name} must be a dictionary (JSON object)")

    # Annotated explicitly: isinstance narrowing leaves key and value types
    # unknown, so they are checked rather than assumed.
    mapping: dict[object, object] = value

    validated: dict[str, object] = {}

    for key, item in mapping.items():
        if not isinstance(key, str):
            raise TypeError(f"{parameter_name} keys must be strings")

        validated[key] = item

    return validated


def require_string_list(value: object, *, parameter_name: str) -> list[str]:
    """Return a list of strings, treating an absent value as empty.

    Raises
    ------
    TypeError
        If the value is neither ``None`` nor a list of strings.
    """
    if value is None:
        return []

    if not isinstance(value, list):
        raise TypeError(f"{parameter_name} must be a list of strings")

    items = cast(list[object], value)

    strings: list[str] = []

    for item in items:
        if not isinstance(item, str):
            raise TypeError(f"{parameter_name} must contain strings only")

        strings.append(item)

    return strings


def require_optional_boolean(value: object, *, parameter_name: str) -> bool | None:
    """Return a Boolean that may be absent.

    The type is checked with ``type(value) is not bool`` rather than
    ``isinstance``, because ``bool`` is a subclass of ``int`` and an integer
    must not be silently accepted as a Boolean.

    Raises
    ------
    TypeError
        If the value is neither ``None`` nor a Boolean.
    """
    if value is None:
        return None

    if type(value) is not bool:
        raise TypeError(f"{parameter_name} must be True, False, or None")

    return value


def require_integer_set(value: object, *, field: str) -> frozenset[int]:
    """Return a frozen set of integer identifiers.

    Booleans are rejected explicitly, because ``bool`` subclasses ``int`` and
    ``True`` would otherwise be accepted as the identifier ``1``.

    Raises
    ------
    TypeError
        If the value is not a list, or contains a non-integer or a Boolean.
    """
    if value is None:
        return frozenset()

    if not isinstance(value, list):
        raise TypeError(f"{field}: must be a list of integer IDs")

    items = cast(list[object], value)

    identifiers: list[int] = []

    for item in items:
        if not isinstance(item, int) or isinstance(item, bool):
            raise TypeError(f"{field}: must contain integer IDs only")

        identifiers.append(item)

    return frozenset(identifiers)
