"""Tests for the tabular-row-sources package contract."""

from collections.abc import Generator, Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path

import tabular_row_sources as package
from tabular_row_sources import (
    ColumnSpec,
    ColumnType,
    CsvReadOptions,
    CsvRowSource,
    DbApiQuerySource,
    QueryParameters,
    Row,
    RowSchema,
    RowSource,
    RowSourceError,
    SchemaDefinitionError,
    SourceConfigurationError,
    SourceExecutionError,
    SourceFormatError,
    ValueConversionError,
    convert_row,
    convert_value,
    load_schema_json,
    parse_schema_json,
    read_sql_file,
)


class InMemoryRowSource:
    """Structural implementation used to verify ``RowSource``."""

    def __init__(
        self,
        *,
        schema: RowSchema,
        rows: list[Row],
    ) -> None:
        self._schema = schema
        self._rows = rows

    @property
    def schema(self) -> RowSchema:
        """Return the source schema."""
        return self._schema

    def open_rows(
        self,
    ) -> AbstractContextManager[Iterator[Row]]:
        """Return a new context manager of fresh rows."""
        return self._open_rows()

    @contextmanager
    def _open_rows(self) -> Generator[Iterator[Row]]:
        """Yield fresh dictionaries without external resources."""
        yield iter(dict(row) for row in self._rows)


def make_schema() -> RowSchema:
    """Return a one-column schema."""
    return RowSchema(
        columns=(
            ColumnSpec(
                name="ID",
                data_type=ColumnType.INTEGER,
            ),
        )
    )


def consume_rows(source: RowSource) -> list[Row]:
    """Consume rows through the public protocol."""
    with source.open_rows() as rows:
        return list(rows)


def test_package_is_not_an_implicit_namespace() -> None:
    assert package.__file__ is not None


def test_package_exposes_its_version() -> None:
    assert package.__version__ == "0.1.0"
    assert "__version__" in package.__all__


def test_package_ships_typing_marker() -> None:
    assert package.__file__ is not None

    package_directory = Path(package.__file__).parent

    assert (package_directory / "py.typed").is_file()


def test_source_protocol_accepts_structural_implementation() -> None:
    schema = make_schema()
    original: list[Row] = [{"ID": 1}, {"ID": 2}]
    source = InMemoryRowSource(
        schema=schema,
        rows=original,
    )

    assert isinstance(source, RowSource)
    assert source.schema is schema
    assert consume_rows(source) == original


def test_source_yields_fresh_row_dictionaries() -> None:
    original: Row = {"ID": 1}
    source = InMemoryRowSource(
        schema=make_schema(),
        rows=[original],
    )

    first = consume_rows(source)[0]
    second = consume_rows(source)[0]

    assert first == second
    assert first is not second
    assert first is not original


def test_source_exceptions_share_one_base_class() -> None:
    assert issubclass(SchemaDefinitionError, RowSourceError)
    assert issubclass(SourceConfigurationError, RowSourceError)
    assert issubclass(SourceFormatError, RowSourceError)
    assert issubclass(ValueConversionError, SourceFormatError)
    assert issubclass(SourceExecutionError, RowSourceError)


def test_public_api_exports_the_contract() -> None:
    assert package.ColumnSpec is ColumnSpec
    assert package.ColumnType is ColumnType
    assert package.Row is Row
    assert package.RowSchema is RowSchema
    assert package.RowSource is RowSource
    assert package.RowSourceError is RowSourceError
    assert package.SchemaDefinitionError is SchemaDefinitionError
    assert package.SourceConfigurationError is SourceConfigurationError
    assert package.SourceExecutionError is SourceExecutionError
    assert package.SourceFormatError is SourceFormatError
    assert package.ValueConversionError is ValueConversionError


def test_public_api_exports_schema_functions() -> None:
    assert package.parse_schema_json is parse_schema_json
    assert package.load_schema_json is load_schema_json


def test_public_api_exports_conversion_functions() -> None:
    assert package.convert_row is convert_row
    assert package.convert_value is convert_value


def test_public_api_exports_csv_source() -> None:
    assert package.CsvReadOptions is CsvReadOptions
    assert package.CsvRowSource is CsvRowSource


def test_public_api_exports_dbapi_source() -> None:
    assert package.DbApiQuerySource is DbApiQuerySource
    assert package.QueryParameters is QueryParameters


def test_public_api_exports_sql_loader() -> None:
    assert package.read_sql_file is read_sql_file
