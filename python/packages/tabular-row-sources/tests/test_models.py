"""Tests for schema and row models."""

import pytest

from tabular_row_sources import (
    ColumnSpec,
    ColumnType,
    RowSchema,
    SchemaDefinitionError,
)


def make_schema() -> RowSchema:
    """Return a representative ordered schema."""
    return RowSchema(
        columns=(
            ColumnSpec(
                name="ID",
                data_type=ColumnType.INTEGER,
                nullable=False,
            ),
            ColumnSpec(
                name="TITLE",
                data_type=ColumnType.STRING,
                nullable=True,
            ),
        )
    )


def test_column_type_values_are_stable() -> None:
    assert {column_type.value for column_type in ColumnType} == {
        "string",
        "integer",
        "decimal",
        "float",
        "boolean",
        "date",
        "datetime",
        "json_object",
    }


def test_column_spec_preserves_definition() -> None:
    column = ColumnSpec(
        name="ID",
        data_type=ColumnType.INTEGER,
        nullable=False,
    )

    assert column.name == "ID"
    assert column.data_type is ColumnType.INTEGER
    assert column.nullable is False


@pytest.mark.parametrize(
    "name",
    ["", "   ", "\n\t"],
    ids=["empty", "spaces", "tabs-newlines"],
)
def test_blank_column_name_is_rejected(name: str) -> None:
    with pytest.raises(
        SchemaDefinitionError,
        match="Column name must not be blank",
    ):
        ColumnSpec(
            name=name,
            data_type=ColumnType.STRING,
        )


def test_non_string_column_name_is_rejected() -> None:
    with pytest.raises(
        SchemaDefinitionError,
        match="Column name must be a string",
    ):
        ColumnSpec(
            name=1,  # type: ignore[arg-type]
            data_type=ColumnType.INTEGER,
        )


def test_non_enum_column_type_is_rejected() -> None:
    with pytest.raises(
        SchemaDefinitionError,
        match="data_type must be a ColumnType",
    ):
        ColumnSpec(
            name="ID",
            data_type="integer",  # type: ignore[arg-type]
        )


def test_non_boolean_nullable_is_rejected() -> None:
    with pytest.raises(
        SchemaDefinitionError,
        match="nullable must be a Boolean",
    ):
        ColumnSpec(
            name="ID",
            data_type=ColumnType.INTEGER,
            nullable=1,  # type: ignore[arg-type]
        )


def test_schema_preserves_column_order() -> None:
    schema = make_schema()

    assert schema.column_names == ("ID", "TITLE")
    assert tuple(schema.columns_by_name) == ("ID", "TITLE")


def test_schema_reports_its_length() -> None:
    assert len(make_schema()) == 2


def test_empty_schema_is_rejected() -> None:
    with pytest.raises(
        SchemaDefinitionError,
        match="must define at least one column",
    ):
        RowSchema(columns=())


def test_schema_requires_a_tuple() -> None:
    with pytest.raises(
        SchemaDefinitionError,
        match="Schema columns must be a tuple",
    ):
        RowSchema(
            columns=[],  # type: ignore[arg-type]
        )


def test_schema_rejects_non_column_values() -> None:
    with pytest.raises(
        SchemaDefinitionError,
        match="must contain ColumnSpec values only",
    ):
        RowSchema(
            columns=("ID",),  # type: ignore[arg-type]
        )


def test_schema_rejects_duplicate_column_names() -> None:
    with pytest.raises(
        SchemaDefinitionError,
        match="duplicate column name: 'ID'",
    ):
        RowSchema(
            columns=(
                ColumnSpec(
                    name="ID",
                    data_type=ColumnType.INTEGER,
                ),
                ColumnSpec(
                    name="ID",
                    data_type=ColumnType.STRING,
                ),
            )
        )


def test_column_names_are_case_sensitive() -> None:
    schema = RowSchema(
        columns=(
            ColumnSpec(
                name="ID",
                data_type=ColumnType.INTEGER,
            ),
            ColumnSpec(
                name="id",
                data_type=ColumnType.INTEGER,
            ),
        )
    )

    assert schema.column_names == ("ID", "id")


def test_schema_models_are_immutable() -> None:
    schema = make_schema()

    with pytest.raises(AttributeError):
        schema.columns = ()  # type: ignore[misc]
