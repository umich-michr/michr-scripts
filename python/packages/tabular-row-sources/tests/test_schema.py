"""Tests for schema JSON parsing and file loading."""

from pathlib import Path
import re

import pytest

from tabular_row_sources import (
    ColumnType,
    SchemaDefinitionError,
    SourceExecutionError,
    load_schema_json,
    parse_schema_json,
)

VALID_SCHEMA_JSON = """
{
  "columns": [
    {
      "name": "ID",
      "type": "integer",
      "nullable": false
    },
    {
      "name": "TITLE",
      "type": "string",
      "nullable": true
    },
    {
      "name": "CREATED_AT",
      "type": "datetime"
    }
  ]
}
"""


def test_parse_schema_json_preserves_column_order_and_types() -> None:
    schema = parse_schema_json(VALID_SCHEMA_JSON)

    assert schema.column_names == ("ID", "TITLE", "CREATED_AT")

    assert schema.columns[0].data_type is ColumnType.INTEGER
    assert schema.columns[0].nullable is False

    assert schema.columns[1].data_type is ColumnType.STRING
    assert schema.columns[1].nullable is True

    assert schema.columns[2].data_type is ColumnType.DATETIME
    assert schema.columns[2].nullable is False


def test_parse_schema_json_accepts_utf8_bytes() -> None:
    schema = parse_schema_json(VALID_SCHEMA_JSON.encode("utf-8"))

    assert schema.column_names == ("ID", "TITLE", "CREATED_AT")


def test_parse_schema_json_rejects_missing_input() -> None:
    with pytest.raises(
        SchemaDefinitionError,
        match="schema is missing",
    ):
        parse_schema_json(None)


@pytest.mark.parametrize(
    "value",
    ["", "   ", "\n\t"],
    ids=["empty", "spaces", "tabs-newlines"],
)
def test_parse_schema_json_rejects_blank_input(value: str) -> None:
    with pytest.raises(
        SchemaDefinitionError,
        match="schema is blank",
    ):
        parse_schema_json(value)


def test_parse_schema_json_rejects_non_text_input() -> None:
    with pytest.raises(
        SchemaDefinitionError,
        match="must be JSON text or UTF-8 bytes",
    ):
        parse_schema_json({"columns": []})


def test_parse_schema_json_rejects_invalid_utf8() -> None:
    with pytest.raises(
        SchemaDefinitionError,
        match="schema is not valid UTF-8",
    ):
        parse_schema_json(b"\xff\xfe{}")


def test_parse_schema_json_reports_invalid_json_location() -> None:
    with pytest.raises(
        SchemaDefinitionError,
        match="invalid JSON at line 1, column 2",
    ):
        parse_schema_json("{", source_name="schema")


@pytest.mark.parametrize(
    "value",
    ["[]", '"text"', "42", "true", "null"],
    ids=["array", "string", "integer", "boolean", "null"],
)
def test_parse_schema_json_requires_root_object(value: str) -> None:
    with pytest.raises(
        SchemaDefinitionError,
        match="schema must be a JSON object",
    ):
        parse_schema_json(value)


def test_parse_schema_json_requires_columns_field() -> None:
    expected = "missing required fields: ['columns']"

    with pytest.raises(
        SchemaDefinitionError,
        match=re.escape(expected),
    ):
        parse_schema_json("{}")


def test_parse_schema_json_rejects_unknown_root_fields() -> None:
    expected = "unknown fields: ['version']"

    with pytest.raises(
        SchemaDefinitionError,
        match=re.escape(expected),
    ):
        parse_schema_json(
            '{"columns": [{"name": "ID", "type": "integer"}], "version": 1}'
        )


def test_parse_schema_json_requires_columns_array() -> None:
    with pytest.raises(
        SchemaDefinitionError,
        match="schema columns must be a JSON array",
    ):
        parse_schema_json('{"columns": {}}')


def test_parse_schema_json_rejects_empty_columns() -> None:
    with pytest.raises(
        SchemaDefinitionError,
        match="must define at least one column",
    ):
        parse_schema_json('{"columns": []}')


def test_parse_schema_json_requires_column_object() -> None:
    with pytest.raises(
        SchemaDefinitionError,
        match="Schema column 1 must be a JSON object",
    ):
        parse_schema_json('{"columns": ["ID"]}')


@pytest.mark.parametrize(
    ("column_json", "missing_field"),
    [
        ('{"type": "integer"}', "name"),
        ('{"name": "ID"}', "type"),
    ],
    ids=["missing-name", "missing-type"],
)
def test_parse_schema_json_requires_column_fields(
    column_json: str,
    missing_field: str,
) -> None:
    expected = f"missing required fields: ['{missing_field}']"

    with pytest.raises(
        SchemaDefinitionError,
        match=re.escape(expected),
    ):
        parse_schema_json(f'{{"columns": [{column_json}]}}')


def test_parse_schema_json_rejects_unknown_column_fields() -> None:
    expected = "unknown fields: ['format']"

    with pytest.raises(
        SchemaDefinitionError,
        match=re.escape(expected),
    ):
        parse_schema_json(
            """
            {
              "columns": [
                {
                  "name": "ID",
                  "type": "integer",
                  "format": "numeric"
                }
              ]
            }
            """
        )


def test_parse_schema_json_requires_string_column_name() -> None:
    with pytest.raises(
        SchemaDefinitionError,
        match="Schema column 1 name must be a string",
    ):
        parse_schema_json('{"columns": [{"name": 1, "type": "integer"}]}')


def test_parse_schema_json_rejects_blank_column_name() -> None:
    with pytest.raises(
        SchemaDefinitionError,
        match="Column name must not be blank",
    ):
        parse_schema_json('{"columns": [{"name": "  ", "type": "integer"}]}')


def test_parse_schema_json_requires_string_column_type() -> None:
    with pytest.raises(
        SchemaDefinitionError,
        match="Schema column 1 type must be a string",
    ):
        parse_schema_json('{"columns": [{"name": "ID", "type": 1}]}')


def test_parse_schema_json_rejects_unsupported_column_type() -> None:
    with pytest.raises(
        SchemaDefinitionError,
        match="unsupported type 'uuid'",
    ):
        parse_schema_json('{"columns": [{"name": "ID", "type": "uuid"}]}')


def test_parse_schema_json_requires_boolean_nullable() -> None:
    with pytest.raises(
        SchemaDefinitionError,
        match="nullable must be a Boolean",
    ):
        parse_schema_json(
            """
            {
              "columns": [
                {
                  "name": "ID",
                  "type": "integer",
                  "nullable": 1
                }
              ]
            }
            """
        )


def test_parse_schema_json_rejects_duplicate_names() -> None:
    with pytest.raises(
        SchemaDefinitionError,
        match="duplicate column name: 'ID'",
    ):
        parse_schema_json(
            """
            {
              "columns": [
                {"name": "ID", "type": "integer"},
                {"name": "ID", "type": "string"}
              ]
            }
            """
        )


def test_error_message_uses_source_name() -> None:
    expected = "audit.schema.json is blank"

    with pytest.raises(
        SchemaDefinitionError,
        match=re.escape(expected),
    ):
        parse_schema_json(
            "",
            source_name="audit.schema.json",
        )


def test_load_schema_json_reads_file(tmp_path: Path) -> None:
    path = tmp_path / "schema.json"
    path.write_text(VALID_SCHEMA_JSON, encoding="utf-8")

    schema = load_schema_json(path)

    assert schema.column_names == ("ID", "TITLE", "CREATED_AT")


def test_load_schema_json_accepts_string_path(tmp_path: Path) -> None:
    path = tmp_path / "schema.json"
    path.write_text(VALID_SCHEMA_JSON, encoding="utf-8")

    schema = load_schema_json(str(path))

    assert schema.column_names == ("ID", "TITLE", "CREATED_AT")


def test_load_schema_json_reports_missing_file(tmp_path: Path) -> None:
    path = tmp_path / "missing.json"

    with pytest.raises(
        SourceExecutionError,
        match="Could not read schema file",
    ):
        load_schema_json(path)


def test_load_schema_json_reports_unknown_encoding(
    tmp_path: Path,
) -> None:
    path = tmp_path / "schema.json"
    path.write_text(VALID_SCHEMA_JSON, encoding="utf-8")

    with pytest.raises(
        SourceExecutionError,
        match="Could not read schema file",
    ):
        load_schema_json(
            path,
            encoding="not-a-real-encoding",
        )


def test_load_schema_json_names_file_in_parse_error(
    tmp_path: Path,
) -> None:
    path = tmp_path / "schema.json"
    path.write_text("", encoding="utf-8")
    expected = f"{path} is blank"

    with pytest.raises(
        SchemaDefinitionError,
        match=re.escape(expected),
    ):
        load_schema_json(path)
