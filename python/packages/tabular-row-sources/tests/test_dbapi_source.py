"""Tests for the generic schema-aware DB-API query source."""

from datetime import datetime, timedelta
from decimal import Decimal
import re
from typing import cast

import pytest

from tabular_row_sources import (
    ColumnSpec,
    ColumnType,
    DbApiQuerySource,
    QueryParameters,
    Row,
    RowSchema,
    RowSource,
    SourceConfigurationError,
    SourceExecutionError,
    SourceFormatError,
    ValueConversionError,
)

_NO_PARAMETERS = object()


class FakeCursor:
    """Configurable fake implementing the cursor behavior used by the source."""

    def __init__(
        self,
        *,
        description: object,
        batches: list[object] | None = None,
        execute_error: Exception | None = None,
        fetch_error: Exception | None = None,
    ) -> None:
        self.description = description
        self.arraysize = 1
        self.batches = list(batches or [])
        self.execute_error = execute_error
        self.fetch_error = fetch_error

        self.execute_calls: list[tuple[str, object]] = []
        self.fetch_sizes: list[int] = []
        self.closed = False

    def execute(
        self,
        operation: str,
        parameters: object = _NO_PARAMETERS,
    ) -> object:
        """Record one execution or raise the configured failure."""
        self.execute_calls.append((operation, parameters))

        if self.execute_error is not None:
            raise self.execute_error

        return self

    def fetchmany(self, size: int = 1) -> object:
        """Return the next configured batch."""
        self.fetch_sizes.append(size)

        if self.fetch_error is not None:
            raise self.fetch_error

        if self.batches:
            return self.batches.pop(0)

        return []

    def close(self) -> None:
        """Record cursor closure."""
        self.closed = True


class FakeFetchInfo:
    """Synthetic driver metadata object exposing a column name."""

    def __init__(self, name: object) -> None:
        self.name = name


class FakeConnection:
    """Configurable fake implementing the connection behavior used by source."""

    def __init__(
        self,
        *,
        cursor_value: object,
        cursor_error: Exception | None = None,
    ) -> None:
        self.cursor_value = cursor_value
        self.cursor_error = cursor_error
        self.cursor_calls = 0
        self.closed = False

    def cursor(self) -> object:
        """Return a cursor or raise the configured failure."""
        self.cursor_calls += 1

        if self.cursor_error is not None:
            raise self.cursor_error

        return self.cursor_value

    def close(self) -> None:
        """Record connection closure."""
        self.closed = True


class FakeConnect:
    """Zero-argument connection factory returning configured values."""

    def __init__(
        self,
        values: list[object],
        *,
        error: Exception | None = None,
    ) -> None:
        self.values = list(values)
        self.error = error
        self.calls = 0

    def __call__(self) -> object:
        """Return the next connection or raise the configured failure."""
        self.calls += 1

        if self.error is not None:
            raise self.error

        if not self.values:
            raise RuntimeError("No fake connection remains")

        return self.values.pop(0)


class InvalidConnection:
    """Object missing the required connection methods."""


class InvalidCursor:
    """Object missing the required cursor methods."""


def simple_schema() -> RowSchema:
    """Return a two-column schema."""
    return RowSchema(
        columns=(
            ColumnSpec(
                name="ID",
                data_type=ColumnType.INTEGER,
            ),
            ColumnSpec(
                name="TITLE",
                data_type=ColumnType.STRING,
            ),
        )
    )


def representative_schema() -> RowSchema:
    """Return a schema covering several canonical conversion types."""
    return RowSchema(
        columns=(
            ColumnSpec(
                name="ID",
                data_type=ColumnType.INTEGER,
            ),
            ColumnSpec(
                name="AMOUNT",
                data_type=ColumnType.DECIMAL,
            ),
            ColumnSpec(
                name="ACTIVE",
                data_type=ColumnType.BOOLEAN,
            ),
            ColumnSpec(
                name="CREATED_AT",
                data_type=ColumnType.DATETIME,
            ),
            ColumnSpec(
                name="PAYLOAD",
                data_type=ColumnType.JSON_OBJECT,
            ),
        )
    )


def description_for(*names: str) -> tuple[tuple[object, ...], ...]:
    """Return DB-API-style cursor description entries."""
    return tuple((name, None, None, None, None, None, None) for name in names)


def object_description_for(*names: str) -> tuple[FakeFetchInfo, ...]:
    """Return python-oracledb-style metadata objects."""
    return tuple(FakeFetchInfo(name) for name in names)


def make_source(
    cursor: object,
    *,
    schema: RowSchema | None = None,
    sql: str = "SELECT ID, TITLE FROM RECORDS",
    parameters: QueryParameters | None = None,
    fetch_size: int = 2,
) -> tuple[DbApiQuerySource, FakeConnection, FakeConnect]:
    """Return a source and its fake resources."""
    connection = FakeConnection(cursor_value=cursor)
    connect = FakeConnect([connection])

    source = DbApiQuerySource(
        connect=connect,
        sql=sql,
        schema=schema or simple_schema(),
        parameters=parameters,
        fetch_size=fetch_size,
    )

    return source, connection, connect


def collect_rows(source: RowSource) -> list[Row]:
    """Consume a source through the public protocol."""
    with source.open_rows() as rows:
        return list(rows)


def enter_source(source: RowSource) -> None:
    """Enter and leave a source context without advancing its iterator."""
    with source.open_rows():
        pass


def consume_one_then_fail(source: RowSource) -> None:
    """Read one row, then simulate a consumer failure."""
    with source.open_rows() as rows:
        next(rows)
        raise RuntimeError("consumer failed")


# ---------------------------------------------------------------------------
# Basic query execution and conversion
# ---------------------------------------------------------------------------


def test_dbapi_source_satisfies_row_source_protocol() -> None:
    cursor = FakeCursor(
        description=description_for("ID", "TITLE"),
    )
    source, _, _ = make_source(cursor)

    assert isinstance(source, RowSource)


def test_query_source_streams_and_converts_rows_in_order() -> None:
    cursor = FakeCursor(
        description=description_for("ID", "TITLE"),
        batches=[
            [("1", "First"), ("2", "Second")],
            [("3", "Third")],
            [],
        ],
    )
    source, connection, connect = make_source(
        cursor,
        fetch_size=2,
    )

    rows = collect_rows(source)

    assert rows == [
        {"ID": 1, "TITLE": "First"},
        {"ID": 2, "TITLE": "Second"},
        {"ID": 3, "TITLE": "Third"},
    ]
    assert cursor.fetch_sizes == [2, 2, 2]
    assert cursor.arraysize == 2
    assert cursor.closed is True
    assert connection.closed is True
    assert connection.cursor_calls == 1
    assert connect.calls == 1


def test_reordered_result_columns_are_accepted_and_canonicalized() -> None:
    cursor = FakeCursor(
        description=description_for("TITLE", "ID"),
        batches=[
            [("First", "1"), ("Second", "2")],
            [],
        ],
    )
    source, _, _ = make_source(cursor)

    rows = collect_rows(source)

    assert rows == [
        {"ID": 1, "TITLE": "First"},
        {"ID": 2, "TITLE": "Second"},
    ]
    assert all(tuple(row) == simple_schema().column_names for row in rows)


def test_query_source_converts_database_native_values() -> None:
    timestamp = datetime.fromisoformat("2026-09-09T14:59:35-04:00")
    cursor = FakeCursor(
        description=description_for(
            "ID",
            "AMOUNT",
            "ACTIVE",
            "CREATED_AT",
            "PAYLOAD",
        ),
        batches=[
            [
                (
                    Decimal(42),
                    Decimal("12.50"),
                    1,
                    timestamp,
                    '{"title": "Example"}',
                )
            ],
            [],
        ],
    )
    source, _, _ = make_source(
        cursor,
        schema=representative_schema(),
    )

    row = collect_rows(source)[0]

    assert row["ID"] == 42
    assert row["AMOUNT"] == Decimal("12.50")
    assert row["ACTIVE"] is True
    assert row["CREATED_AT"] == timestamp
    assert row["PAYLOAD"] == {"title": "Example"}

    created_at = row["CREATED_AT"]
    assert isinstance(created_at, datetime)
    assert created_at.utcoffset() == timedelta(hours=-4)


def test_query_source_with_no_rows_returns_empty_list() -> None:
    cursor = FakeCursor(
        description=description_for("ID", "TITLE"),
        batches=[[]],
    )
    source, _, _ = make_source(cursor)

    assert collect_rows(source) == []


def test_rows_are_not_fetched_until_iterator_advances() -> None:
    cursor = FakeCursor(
        description=description_for("ID", "TITLE"),
        batches=[[("1", "First")], []],
    )
    source, connection, _ = make_source(cursor)

    with source.open_rows():
        assert cursor.execute_calls
        assert cursor.fetch_sizes == []

    assert cursor.closed is True
    assert connection.closed is True


def test_query_source_can_be_opened_repeatedly() -> None:
    first_cursor = FakeCursor(
        description=description_for("ID", "TITLE"),
        batches=[[("1", "First")], []],
    )
    second_cursor = FakeCursor(
        description=description_for("ID", "TITLE"),
        batches=[[("2", "Second")], []],
    )
    first_connection = FakeConnection(cursor_value=first_cursor)
    second_connection = FakeConnection(cursor_value=second_cursor)
    connect = FakeConnect([first_connection, second_connection])

    source = DbApiQuerySource(
        connect=connect,
        sql="SELECT ID, TITLE FROM RECORDS",
        schema=simple_schema(),
    )

    assert collect_rows(source) == [{"ID": 1, "TITLE": "First"}]
    assert collect_rows(source) == [{"ID": 2, "TITLE": "Second"}]

    assert connect.calls == 2
    assert first_connection.closed is True
    assert second_connection.closed is True


# ---------------------------------------------------------------------------
# SQL and bind parameters
# ---------------------------------------------------------------------------


def test_query_without_parameters_calls_execute_with_sql_only() -> None:
    cursor = FakeCursor(
        description=description_for("ID", "TITLE"),
        batches=[[]],
    )
    source, _, _ = make_source(cursor)

    collect_rows(source)

    assert len(cursor.execute_calls) == 1

    operation, parameters = cursor.execute_calls[0]

    assert operation == "SELECT ID, TITLE FROM RECORDS"
    assert parameters is _NO_PARAMETERS


def test_mapping_parameters_are_passed_to_execute() -> None:
    cursor = FakeCursor(
        description=description_for("ID", "TITLE"),
        batches=[[]],
    )
    parameters: dict[str, object] = {"status": "ACTIVE"}
    source, _, _ = make_source(
        cursor,
        sql="SELECT ID, TITLE FROM RECORDS WHERE STATUS = :status",
        parameters=parameters,
    )

    collect_rows(source)

    assert cursor.execute_calls == [
        (
            "SELECT ID, TITLE FROM RECORDS WHERE STATUS = :status",
            {"status": "ACTIVE"},
        )
    ]


def test_mapping_parameters_are_defensively_copied() -> None:
    cursor = FakeCursor(
        description=description_for("ID", "TITLE"),
        batches=[[]],
    )
    parameters: dict[str, object] = {"status": "ACTIVE"}
    source, _, _ = make_source(
        cursor,
        parameters=parameters,
    )

    parameters["status"] = "CHANGED"

    assert source.parameters == {"status": "ACTIVE"}

    returned = source.parameters
    assert isinstance(returned, dict)

    returned["status"] = "MUTATED"

    assert source.parameters == {"status": "ACTIVE"}


def test_positional_parameters_are_copied_to_tuple() -> None:
    cursor = FakeCursor(
        description=description_for("ID", "TITLE"),
        batches=[[]],
    )
    parameters: list[object] = ["ACTIVE", 10]
    source, _, _ = make_source(
        cursor,
        parameters=parameters,
    )

    parameters.append("LATER")

    assert source.parameters == ("ACTIVE", 10)

    collect_rows(source)

    assert cursor.execute_calls == [
        (
            "SELECT ID, TITLE FROM RECORDS",
            ("ACTIVE", 10),
        )
    ]


def test_source_exposes_configuration() -> None:
    cursor = FakeCursor(
        description=description_for("ID", "TITLE"),
    )
    schema = simple_schema()
    source, _, _ = make_source(
        cursor,
        schema=schema,
        sql="SELECT * FROM RECORDS",
        parameters={"status": "ACTIVE"},
        fetch_size=25,
    )

    assert source.schema is schema
    assert source.sql == "SELECT * FROM RECORDS"
    assert source.parameters == {"status": "ACTIVE"}
    assert source.fetch_size == 25


# ---------------------------------------------------------------------------
# Configuration validation
# ---------------------------------------------------------------------------


def test_connect_must_be_callable() -> None:
    with pytest.raises(
        SourceConfigurationError,
        match="DB-API connect must be callable",
    ):
        DbApiQuerySource(
            connect=None,  # type: ignore[arg-type]
            sql="SELECT ID FROM RECORDS",
            schema=simple_schema(),
        )


@pytest.mark.parametrize(
    "sql",
    ["", "   ", "\n\t"],
    ids=["empty", "spaces", "tabs-newlines"],
)
def test_sql_must_be_nonblank(sql: str) -> None:
    with pytest.raises(
        SourceConfigurationError,
        match="DB-API SQL must be a nonblank string",
    ):
        DbApiQuerySource(
            connect=object,
            sql=sql,
            schema=simple_schema(),
        )


def test_sql_must_be_string() -> None:
    with pytest.raises(
        SourceConfigurationError,
        match="DB-API SQL must be a nonblank string",
    ):
        DbApiQuerySource(
            connect=object,
            sql=42,  # type: ignore[arg-type]
            schema=simple_schema(),
        )


def test_schema_must_be_row_schema() -> None:
    with pytest.raises(
        SourceConfigurationError,
        match="DB-API schema must be a RowSchema",
    ):
        DbApiQuerySource(
            connect=object,
            sql="SELECT ID FROM RECORDS",
            schema=None,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "fetch_size",
    [0, -1, True, 1.5, "10"],
    ids=["zero", "negative", "boolean", "float", "string"],
)
def test_fetch_size_must_be_positive_integer(
    fetch_size: object,
) -> None:
    with pytest.raises(
        SourceConfigurationError,
        match="fetch_size must be a positive integer",
    ):
        DbApiQuerySource(
            connect=object,
            sql="SELECT ID FROM RECORDS",
            schema=simple_schema(),
            fetch_size=fetch_size,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "parameters",
    ["text", b"bytes", 42, object()],
    ids=["string", "bytes", "integer", "object"],
)
def test_parameters_must_be_mapping_sequence_or_none(
    parameters: object,
) -> None:
    with pytest.raises(
        SourceConfigurationError,
        match="parameters must be a mapping",
    ):
        DbApiQuerySource(
            connect=object,
            sql="SELECT ID FROM RECORDS",
            schema=simple_schema(),
            parameters=cast("QueryParameters", parameters),
        )


def test_mapping_parameter_names_must_be_strings() -> None:
    # Deliberately bypass the static contract to verify runtime validation at
    # the untyped DB-API boundary.
    parameters = cast(
        "QueryParameters",
        {1: "ACTIVE"},
    )

    with pytest.raises(
        SourceConfigurationError,
        match="mapping parameter names must be strings",
    ):
        DbApiQuerySource(
            connect=object,
            sql="SELECT ID FROM RECORDS",
            schema=simple_schema(),
            parameters=parameters,
        )


# ---------------------------------------------------------------------------
# Connection, cursor, and execution failures
# ---------------------------------------------------------------------------


def test_connection_factory_failure_is_wrapped() -> None:
    connect = FakeConnect(
        [],
        error=RuntimeError("connection unavailable"),
    )
    source = DbApiQuerySource(
        connect=connect,
        sql="SELECT ID, TITLE FROM RECORDS",
        schema=simple_schema(),
    )

    with pytest.raises(
        SourceExecutionError,
        match="Could not open DB-API connection",
    ):
        enter_source(source)


def test_invalid_connection_is_rejected() -> None:
    source = DbApiQuerySource(
        connect=FakeConnect([InvalidConnection()]),
        sql="SELECT ID, TITLE FROM RECORDS",
        schema=simple_schema(),
    )

    with pytest.raises(
        SourceExecutionError,
        match="connection must provide callable cursor",
    ):
        enter_source(source)


def test_cursor_creation_failure_is_wrapped() -> None:
    connection = FakeConnection(
        cursor_value=object(),
        cursor_error=RuntimeError("cursor unavailable"),
    )
    source = DbApiQuerySource(
        connect=FakeConnect([connection]),
        sql="SELECT ID, TITLE FROM RECORDS",
        schema=simple_schema(),
    )

    with pytest.raises(
        SourceExecutionError,
        match="Could not create DB-API cursor",
    ):
        enter_source(source)

    assert connection.closed is True


def test_invalid_cursor_is_rejected_and_connection_closes() -> None:
    connection = FakeConnection(cursor_value=InvalidCursor())
    source = DbApiQuerySource(
        connect=FakeConnect([connection]),
        sql="SELECT ID, TITLE FROM RECORDS",
        schema=simple_schema(),
    )

    with pytest.raises(
        SourceExecutionError,
        match="cursor must provide callable execute",
    ):
        enter_source(source)

    assert connection.closed is True


def test_execute_failure_is_wrapped_and_resources_close() -> None:
    cursor = FakeCursor(
        description=description_for("ID", "TITLE"),
        execute_error=RuntimeError("query failed"),
    )
    source, connection, _ = make_source(cursor)

    with pytest.raises(
        SourceExecutionError,
        match="Could not execute DB-API query",
    ):
        enter_source(source)

    assert cursor.closed is True
    assert connection.closed is True


def test_fetch_failure_is_wrapped_with_progress() -> None:
    cursor = FakeCursor(
        description=description_for("ID", "TITLE"),
        fetch_error=RuntimeError("fetch failed"),
    )
    source, connection, _ = make_source(cursor)

    with pytest.raises(
        SourceExecutionError,
        match="Could not fetch DB-API query results after row 0",
    ):
        collect_rows(source)

    assert cursor.closed is True
    assert connection.closed is True


def test_fetch_failure_after_batch_reports_rows_already_yielded() -> None:
    class FailingAfterFirstBatchCursor(FakeCursor):
        """Return one batch and then fail."""

        def fetchmany(self, size: int = 1) -> object:
            self.fetch_sizes.append(size)

            if len(self.fetch_sizes) == 1:
                return [("1", "First"), ("2", "Second")]

            raise RuntimeError("later fetch failed")

    cursor = FailingAfterFirstBatchCursor(
        description=description_for("ID", "TITLE"),
    )
    source, _, _ = make_source(cursor)

    with pytest.raises(
        SourceExecutionError,
        match="after row 2",
    ):
        collect_rows(source)


# ---------------------------------------------------------------------------
# Result metadata validation
# ---------------------------------------------------------------------------


def metadata_failure(
    description: object,
) -> None:
    """Enter a source with the specified invalid metadata."""
    cursor = FakeCursor(description=description)
    source, _, _ = make_source(cursor)

    enter_source(source)


def test_description_is_required() -> None:
    with pytest.raises(
        SourceFormatError,
        match="did not return a result-set description",
    ):
        metadata_failure(None)


@pytest.mark.parametrize(
    "description",
    ["ID", b"ID", 42, object()],
    ids=["string", "bytes", "integer", "object"],
)
def test_description_must_be_sequence(description: object) -> None:
    with pytest.raises(
        SourceFormatError,
        match="description must be a sequence",
    ):
        metadata_failure(description)


@pytest.mark.parametrize(
    "item",
    ["ID", b"ID", 42, object()],
    ids=["string", "bytes", "integer", "object"],
)
def test_description_item_must_be_sequence_or_expose_name(
    item: object,
) -> None:
    with pytest.raises(
        SourceFormatError,
        match="description item 1 must be a sequence or expose a name attribute",
    ):
        metadata_failure([item])


def test_description_item_must_not_be_empty() -> None:
    with pytest.raises(
        SourceFormatError,
        match="description item 1 is empty",
    ):
        metadata_failure([()])


def test_description_column_name_must_be_string() -> None:
    with pytest.raises(
        SourceFormatError,
        match="column name 1 must be a string",
    ):
        metadata_failure([(1, None)])


def test_description_column_name_must_not_be_blank() -> None:
    with pytest.raises(
        SourceFormatError,
        match="column name 1 must not be blank",
    ):
        metadata_failure([("   ", None)])


def test_duplicate_result_column_names_are_rejected() -> None:
    with pytest.raises(
        SourceFormatError,
        match="duplicate column names",
    ):
        metadata_failure(description_for("ID", "ID"))


@pytest.mark.parametrize(
    "description",
    [
        description_for("ID"),
        description_for("ID", "TITLE", "EXTRA"),
        description_for("id", "TITLE"),
    ],
    ids=["missing", "extra", "wrong-case"],
)
def test_result_column_names_must_match_schema(
    description: object,
) -> None:
    with pytest.raises(
        SourceFormatError,
        match="result columns do not match schema names",
    ):
        metadata_failure(description)


def test_description_accepts_objects_with_name_attributes() -> None:
    cursor = FakeCursor(
        description=object_description_for("ID", "TITLE"),
        batches=[
            [("1", "First")],
            [],
        ],
    )
    source, _, _ = make_source(cursor)

    assert collect_rows(source) == [
        {
            "ID": 1,
            "TITLE": "First",
        }
    ]


def test_object_description_column_name_must_be_string() -> None:
    with pytest.raises(
        SourceFormatError,
        match="column name 1 must be a string",
    ):
        metadata_failure(
            (
                FakeFetchInfo(42),
                FakeFetchInfo("TITLE"),
            )
        )


def test_object_description_column_name_must_not_be_blank() -> None:
    with pytest.raises(
        SourceFormatError,
        match="column name 1 must not be blank",
    ):
        metadata_failure(
            (
                FakeFetchInfo("   "),
                FakeFetchInfo("TITLE"),
            )
        )


# ---------------------------------------------------------------------------
# Result batch and row validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "batch",
    ["row", b"row", 42, object()],
    ids=["string", "bytes", "integer", "object"],
)
def test_fetchmany_must_return_sequence(batch: object) -> None:
    cursor = FakeCursor(
        description=description_for("ID", "TITLE"),
        batches=[batch],
    )
    source, _, _ = make_source(cursor)
    expected = "fetchmany() must return a sequence"

    with pytest.raises(
        SourceFormatError,
        match=re.escape(expected),
    ):
        collect_rows(source)


@pytest.mark.parametrize(
    "row",
    ["row", b"row", 42, object()],
    ids=["string", "bytes", "integer", "object"],
)
def test_result_row_must_be_sequence(row: object) -> None:
    cursor = FakeCursor(
        description=description_for("ID", "TITLE"),
        batches=[[row]],
    )
    source, _, _ = make_source(cursor)

    with pytest.raises(
        SourceFormatError,
        match="result row 1 must be a sequence",
    ):
        collect_rows(source)


@pytest.mark.parametrize(
    "row",
    [(1,), (1, "Title", "Extra")],
    ids=["too-few", "too-many"],
)
def test_result_row_must_have_schema_value_count(
    row: tuple[object, ...],
) -> None:
    cursor = FakeCursor(
        description=description_for("ID", "TITLE"),
        batches=[[row]],
    )
    source, _, _ = make_source(cursor)

    with pytest.raises(
        SourceFormatError,
        match="result row 1 has",
    ):
        collect_rows(source)


def test_value_conversion_failure_reports_row_and_column() -> None:
    cursor = FakeCursor(
        description=description_for("ID", "TITLE"),
        batches=[[("not-an-integer", "Example")]],
    )
    source, _, _ = make_source(cursor)

    with pytest.raises(
        ValueConversionError,
        match="Row 1, column 'ID'",
    ):
        collect_rows(source)


# ---------------------------------------------------------------------------
# Resource lifecycle
# ---------------------------------------------------------------------------


def test_resources_close_after_normal_completion() -> None:
    cursor = FakeCursor(
        description=description_for("ID", "TITLE"),
        batches=[[("1", "First")], []],
    )
    source, connection, _ = make_source(cursor)

    assert collect_rows(source) == [{"ID": 1, "TITLE": "First"}]
    assert cursor.closed is True
    assert connection.closed is True


def test_resources_close_after_early_termination() -> None:
    cursor = FakeCursor(
        description=description_for("ID", "TITLE"),
        batches=[[("1", "First"), ("2", "Second")], []],
    )
    source, connection, _ = make_source(cursor)

    with source.open_rows() as rows:
        assert next(rows) == {"ID": 1, "TITLE": "First"}

    assert cursor.closed is True
    assert connection.closed is True


def test_resources_close_after_conversion_failure() -> None:
    cursor = FakeCursor(
        description=description_for("ID", "TITLE"),
        batches=[[("invalid", "Example")]],
    )
    source, connection, _ = make_source(cursor)

    with pytest.raises(ValueConversionError):
        collect_rows(source)

    assert cursor.closed is True
    assert connection.closed is True


def test_resources_close_after_consumer_failure() -> None:
    cursor = FakeCursor(
        description=description_for("ID", "TITLE"),
        batches=[[("1", "First")], []],
    )
    source, connection, _ = make_source(cursor)

    with pytest.raises(RuntimeError, match="consumer failed"):
        consume_one_then_fail(source)

    assert cursor.closed is True
    assert connection.closed is True


def test_connection_closes_when_cursor_creation_fails() -> None:
    connection = FakeConnection(
        cursor_value=object(),
        cursor_error=RuntimeError("cursor failed"),
    )
    source = DbApiQuerySource(
        connect=FakeConnect([connection]),
        sql="SELECT ID, TITLE FROM RECORDS",
        schema=simple_schema(),
    )

    with pytest.raises(SourceExecutionError):
        enter_source(source)

    assert connection.closed is True
