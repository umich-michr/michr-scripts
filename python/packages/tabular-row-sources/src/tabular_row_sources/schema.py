"""Parsing and loading of tabular row schemas.

Schema definitions use a small JSON format containing an ordered ``columns``
array. Parsing validates the complete document and produces an immutable
``RowSchema``.

This module performs schema-file I/O only. It does not read data rows, execute
SQL, infer source types, or apply application-specific policy.
"""

import json
from pathlib import Path

from tabular_row_sources.errors import (
    SchemaDefinitionError,
    SourceExecutionError,
)
from tabular_row_sources.models import (
    ColumnSpec,
    ColumnType,
    RowSchema,
)

_ROOT_FIELDS = frozenset({"columns"})
_COLUMN_FIELDS = frozenset({"name", "type", "nullable"})
_REQUIRED_COLUMN_FIELDS = frozenset({"name", "type"})


def _require_mapping(
    value: object,
    *,
    context: str,
) -> dict[object, object]:
    """Return a dictionary or raise a schema-definition error."""
    if not isinstance(value, dict):
        raise SchemaDefinitionError(f"{context} must be a JSON object")

    return value


def _require_list(
    value: object,
    *,
    context: str,
) -> list[object]:
    """Return a list with statically known element type."""
    if not isinstance(value, list):
        raise SchemaDefinitionError(f"{context} must be a JSON array")

    items: list[object] = value

    return items


def _require_exact_fields(
    mapping: dict[object, object],
    *,
    allowed: frozenset[str],
    required: frozenset[str],
    context: str,
) -> None:
    """Validate string keys, required fields, and unknown fields."""
    keys: set[str] = set()

    for key in mapping:
        if not isinstance(key, str):
            raise SchemaDefinitionError(f"{context} field names must be strings")

        keys.add(key)

    missing = required - keys

    if missing:
        raise SchemaDefinitionError(
            f"{context} is missing required fields: {sorted(missing)}"
        )

    unknown = keys - allowed

    if unknown:
        raise SchemaDefinitionError(
            f"{context} contains unknown fields: {sorted(unknown)}"
        )


def _parse_column_type(
    value: object,
    *,
    column_position: int,
) -> ColumnType:
    """Parse one JSON column-type value."""
    if not isinstance(value, str):
        raise SchemaDefinitionError(
            f"Schema column {column_position} type must be a string"
        )

    try:
        return ColumnType(value)
    except ValueError as error:
        supported = ", ".join(repr(column_type.value) for column_type in ColumnType)
        raise SchemaDefinitionError(
            f"Schema column {column_position} has unsupported type "
            f"{value!r}; supported types are: {supported}"
        ) from error


def _parse_nullable(
    value: object,
    *,
    column_position: int,
) -> bool:
    """Parse one optional JSON nullable value."""
    if type(value) is not bool:
        raise SchemaDefinitionError(
            f"Schema column {column_position} nullable must be a Boolean"
        )

    return value


def _parse_column(
    value: object,
    *,
    column_position: int,
) -> ColumnSpec:
    """Parse one column definition from a decoded JSON value."""
    context = f"Schema column {column_position}"
    mapping = _require_mapping(value, context=context)

    _require_exact_fields(
        mapping,
        allowed=_COLUMN_FIELDS,
        required=_REQUIRED_COLUMN_FIELDS,
        context=context,
    )

    name = mapping["name"]

    if not isinstance(name, str):
        raise SchemaDefinitionError(
            f"Schema column {column_position} name must be a string"
        )

    data_type = _parse_column_type(
        mapping["type"],
        column_position=column_position,
    )

    nullable = _parse_nullable(
        mapping.get("nullable", False),
        column_position=column_position,
    )

    return ColumnSpec(
        name=name,
        data_type=data_type,
        nullable=nullable,
    )


def parse_schema_json(
    value: object,
    *,
    source_name: str = "schema",
) -> RowSchema:
    """Parse a row schema from JSON text or UTF-8 bytes.

    Parameters
    ----------
    value
        JSON text or UTF-8 bytes containing the schema document.
    source_name
        Label used in error messages, such as a schema filename.

    Returns
    -------
    RowSchema
        Validated immutable row schema.

    Raises
    ------
    SchemaDefinitionError
        If the input is missing, blank, not text or bytes, not valid UTF-8,
        malformed JSON, or does not match the schema-document format.
    """
    if value is None:
        raise SchemaDefinitionError(f"{source_name} is missing")

    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8")
        except UnicodeDecodeError as error:
            raise SchemaDefinitionError(
                f"{source_name} is not valid UTF-8: {error}"
            ) from error

    if not isinstance(value, str):
        raise SchemaDefinitionError(f"{source_name} must be JSON text or UTF-8 bytes")

    if not value.strip():
        raise SchemaDefinitionError(f"{source_name} is blank")

    try:
        decoded: object = json.loads(value)
    except json.JSONDecodeError as error:
        raise SchemaDefinitionError(
            f"{source_name} contains invalid JSON at line {error.lineno}, "
            f"column {error.colno}: {error.msg}"
        ) from error

    root = _require_mapping(decoded, context=source_name)

    _require_exact_fields(
        root,
        allowed=_ROOT_FIELDS,
        required=_ROOT_FIELDS,
        context=source_name,
    )

    column_values = _require_list(
        root["columns"],
        context=f"{source_name} columns",
    )

    columns = tuple(
        _parse_column(
            column_value,
            column_position=position,
        )
        for position, column_value in enumerate(
            column_values,
            start=1,
        )
    )

    return RowSchema(columns=columns)


def load_schema_json(
    path: str | Path,
    *,
    encoding: str = "utf-8",
) -> RowSchema:
    """Load and parse a row schema from a JSON file.

    Parameters
    ----------
    path
        Path to the schema file.
    encoding
        Text encoding used to read the file. Defaults to UTF-8.

    Returns
    -------
    RowSchema
        Validated immutable row schema.

    Raises
    ------
    SourceExecutionError
        If the schema file cannot be read or the requested encoding is unknown.
    SchemaDefinitionError
        If the file contents do not define a valid schema.
    """
    schema_path = Path(path)

    try:
        text = schema_path.read_text(encoding=encoding)
    except (LookupError, OSError) as error:
        raise SourceExecutionError(
            f"Could not read schema file {schema_path}: {error}"
        ) from error

    return parse_schema_json(
        text,
        source_name=str(schema_path),
    )
