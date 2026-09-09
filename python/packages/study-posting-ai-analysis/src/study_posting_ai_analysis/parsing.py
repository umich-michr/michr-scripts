"""Decoding of JSON analysis inputs.

Analysis inputs arrive as JSON in practice, whether from a database column, a
CSV cell, or an HTTP payload. Decoding them here means every consumer produces
the same errors for the same malformed input, rather than reimplementing the
check.

A value that has already been decoded is passed through, so a caller holding
dictionaries need not serialize them first.
"""

import json
from typing import cast

from study_posting_ai_analysis.errors import InputParseError


def parse_json_object(value: object, *, name: str) -> dict[str, object]:
    """Decode a JSON object from text, bytes, or an existing mapping.

    Parameters
    ----------
    value
        A JSON string, UTF-8 bytes, or an already-decoded mapping.
    name
        Label for the input, used in error messages. Callers typically pass a
        column name such as ``"LLM_SUGGESTIONS"``.

    Returns
    -------
    dict[str, object]
        The decoded object.

    Raises
    ------
    InputParseError
        If the value is absent, blank, not valid UTF-8, not valid JSON, or
        decodes to a JSON value other than an object.

    Notes
    -----
    Bytes are decoded explicitly rather than left to ``json.loads``, which
    raises ``UnicodeDecodeError`` outside the ``JSONDecodeError`` hierarchy and
    infers the encoding from a byte-order mark. Being explicit keeps the UTF-8
    assumption visible and the exception type uniform.

    A blank value is reported before parsing, because an empty column is a
    distinct and expected condition rather than a syntax error at column 1.
    """
    if value is None:
        raise InputParseError(f"{name} is missing")

    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8")
        except UnicodeDecodeError as error:
            raise InputParseError(f"{name} is not valid UTF-8: {error}") from error

    if isinstance(value, str):
        if not value.strip():
            raise InputParseError(f"{name} is blank")

        try:
            value = json.loads(value)
        except json.JSONDecodeError as error:
            raise InputParseError(
                f"{name} contains invalid JSON at line {error.lineno}, "
                f"column {error.colno}: {error.msg}"
            ) from error

    if not isinstance(value, dict):
        raise InputParseError(
            f"{name} must contain a JSON object, received {type(value).__name__}"
        )

    # JSON object keys are always strings, so the narrowed dict is cast rather
    # than re-validated key by key. Field-level validation happens downstream in
    # validation.py, which is where a genuinely untrusted structure is checked.
    return cast("dict[str, object]", value)


def parse_analysis_inputs(
    suggested: object,
    selected: object,
    final: object,
    *,
    suggested_name: str = "suggested",
    selected_name: str = "selected",
    final_name: str = "final",
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    """Decode the three analysis inputs together.

    A convenience wrapper over :func:`parse_json_object` for the common case of
    decoding all three payloads before calling ``analyze_objects``.

    Parameters
    ----------
    suggested
        AI-generated suggestions payload.
    selected
        Suggestions the user selected or applied.
    final
        Values the user ultimately saved.
    suggested_name
        Label for the suggested payload in error messages. Callers reading a
        database typically pass the column name.
    selected_name
        Label for the selected payload.
    final_name
        Label for the final payload.

    Returns
    -------
    tuple[dict[str, object], dict[str, object], dict[str, object]]
        The three decoded objects, in the order accepted by ``analyze_objects``.

    Raises
    ------
    InputParseError
        If any payload cannot be decoded into a JSON object. The message names
        which payload failed.

    Examples
    --------
    >>> suggested, selected, final = parse_analysis_inputs(
    ...     '{"title": ["Offered title"]}',
    ...     '{"title": ["Offered title"]}',
    ...     '{"title": "Offered title"}',
    ... )
    >>> sorted(suggested)
    ['title']
    """
    return (
        parse_json_object(suggested, name=suggested_name),
        parse_json_object(selected, name=selected_name),
        parse_json_object(final, name=final_name),
    )
