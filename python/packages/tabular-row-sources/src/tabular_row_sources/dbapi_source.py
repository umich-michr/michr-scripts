"""Lazy, schema-aware DB-API query row source.

The source accepts a connection factory rather than database credentials or a
specific driver. This keeps query streaming reusable across DB-API-compatible
drivers.

The source owns each connection and cursor it creates. Query results are fetched
in batches, validated against a ``RowSchema``, converted through the shared
canonical conversion layer, and yielded one row at a time.

This module does not read SQL files, obtain credentials, configure logging, or
implement application-specific query policy.
"""

from collections import Counter
from collections.abc import (
    Callable,
    Generator,
    Iterator,
    Mapping,
    Sequence,
)
from contextlib import AbstractContextManager, contextmanager
from typing import Protocol, cast

from tabular_row_sources.conversion import convert_row
from tabular_row_sources.errors import (
    SourceConfigurationError,
    SourceExecutionError,
    SourceFormatError,
)
from tabular_row_sources.models import Row, RowSchema

type QueryParameters = Mapping[str, object] | Sequence[object]


class _CursorProtocol(Protocol):
    """Minimal cursor behavior used by the query source.

    Values returned by a database driver are typed as ``object`` and validated
    at runtime. This prevents static annotations from making trust-boundary
    validation appear redundant.
    """

    description: object
    arraysize: int

    def execute(
        self,
        operation: str,
        parameters: object = ...,
    ) -> object:
        """Execute one operation."""
        ...

    def fetchmany(
        self,
        size: int = ...,
    ) -> object:
        """Fetch the next driver-provided batch."""
        ...

    def close(self) -> None:
        """Close the cursor."""
        ...


class _ConnectionProtocol(Protocol):
    """Minimal connection behavior used by the query source."""

    def cursor(self) -> object:
        """Create a cursor."""
        ...

    def close(self) -> None:
        """Close the connection."""
        ...


def _require_schema(value: object) -> RowSchema:
    """Return a valid row schema."""
    if not isinstance(value, RowSchema):
        raise SourceConfigurationError("DB-API schema must be a RowSchema")

    return value


def _require_connect(
    value: object,
) -> Callable[[], object]:
    """Return a callable connection factory."""
    if not callable(value):
        raise SourceConfigurationError("DB-API connect must be callable")

    return value


def _require_sql(value: object) -> str:
    """Return nonblank SQL text."""
    if not isinstance(value, str) or not value.strip():
        raise SourceConfigurationError("DB-API SQL must be a nonblank string")

    return value


def _require_fetch_size(value: object) -> int:
    """Return a positive fetch size."""
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise SourceConfigurationError("DB-API fetch_size must be a positive integer")

    return value


def _copy_parameters(
    value: object,
) -> dict[str, object] | tuple[object, ...] | None:
    """Validate and defensively copy optional query bind parameters."""
    if value is None:
        return None

    if isinstance(value, Mapping):
        mapping = cast("Mapping[object, object]", value)
        parameters: dict[str, object] = {}

        for key, item in mapping.items():
            if not isinstance(key, str):
                raise SourceConfigurationError(
                    "DB-API mapping parameter names must be strings"
                )

            parameters[key] = item

        return parameters

    if isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    ):
        sequence = cast("Sequence[object]", value)

        return tuple(sequence)

    raise SourceConfigurationError(
        "DB-API parameters must be a mapping, a non-string sequence, or None"
    )


def _require_connection(value: object) -> _ConnectionProtocol:
    """Validate minimal connection behavior."""
    cursor_method = getattr(value, "cursor", None)
    close_method = getattr(value, "close", None)

    if not callable(cursor_method) or not callable(close_method):
        raise SourceExecutionError(
            "DB-API connection must provide callable cursor() and close() methods"
        )

    return cast("_ConnectionProtocol", value)


def _require_cursor(value: object) -> _CursorProtocol:
    """Validate minimal cursor behavior."""
    execute_method = getattr(value, "execute", None)
    fetchmany_method = getattr(value, "fetchmany", None)
    close_method = getattr(value, "close", None)

    if (
        not callable(execute_method)
        or not callable(fetchmany_method)
        or not callable(close_method)
    ):
        raise SourceExecutionError(
            "DB-API cursor must provide callable execute(), fetchmany(), "
            "and close() methods"
        )

    return cast("_CursorProtocol", value)


def _column_names_from_description(
    description: object,
) -> tuple[str, ...]:
    """Extract ordered column names from DB-API cursor metadata."""
    if description is None:
        raise SourceFormatError("DB-API query did not return a result-set description")

    if not isinstance(description, Sequence) or isinstance(
        description,
        (str, bytes, bytearray),
    ):
        raise SourceFormatError("DB-API result-set description must be a sequence")

    description_items = cast("Sequence[object]", description)
    names: list[str] = []

    for position, item in enumerate(description_items, start=1):
        if not isinstance(item, Sequence) or isinstance(
            item,
            (str, bytes, bytearray),
        ):
            raise SourceFormatError(
                f"DB-API description item {position} must be a sequence"
            )

        description_item = cast("Sequence[object]", item)

        if not description_item:
            raise SourceFormatError(f"DB-API description item {position} is empty")

        name = description_item[0]

        if not isinstance(name, str):
            raise SourceFormatError(f"DB-API column name {position} must be a string")

        if not name.strip():
            raise SourceFormatError(f"DB-API column name {position} must not be blank")

        names.append(name)

    duplicates = sorted(name for name, count in Counter(names).items() if count > 1)

    if duplicates:
        raise SourceFormatError(
            f"DB-API result contains duplicate column names: {duplicates}"
        )

    return tuple(names)


def _validate_result_columns(
    actual: tuple[str, ...],
    *,
    schema: RowSchema,
) -> None:
    """Require exact result-column agreement with the schema."""
    expected = schema.column_names

    if actual != expected:
        raise SourceFormatError(
            "DB-API result columns do not match schema order: "
            f"expected {expected!r}, received {actual!r}"
        )


def _require_result_batch(
    value: object,
    *,
    rows_fetched: int,
) -> Sequence[object]:
    """Return a non-string sequence of driver-provided result rows."""
    if not isinstance(value, Sequence) or isinstance(
        value,
        (str, bytes, bytearray),
    ):
        raise SourceFormatError(
            "DB-API fetchmany() must return a sequence of rows "
            f"after row {rows_fetched}"
        )

    return cast("Sequence[object]", value)


def _require_result_row(
    value: object,
    *,
    row_number: int,
) -> Sequence[object]:
    """Return a non-string result-row sequence."""
    if not isinstance(value, Sequence) or isinstance(
        value,
        (str, bytes, bytearray),
    ):
        raise SourceFormatError(f"DB-API result row {row_number} must be a sequence")

    return cast("Sequence[object]", value)


def _iter_query_rows(
    cursor: _CursorProtocol,
    *,
    schema: RowSchema,
    fetch_size: int,
) -> Iterator[Row]:
    """Fetch, validate, and convert query rows lazily."""
    row_number = 0
    expected_count = len(schema)

    while True:
        try:
            batch_value = cursor.fetchmany(fetch_size)
        except Exception as error:
            raise SourceExecutionError(
                f"Could not fetch DB-API query results after row {row_number}: {error}"
            ) from error

        batch = _require_result_batch(
            batch_value,
            rows_fetched=row_number,
        )

        if not batch:
            return

        for raw_row in batch:
            row_number += 1
            values = _require_result_row(
                raw_row,
                row_number=row_number,
            )

            if len(values) != expected_count:
                raise SourceFormatError(
                    f"DB-API result row {row_number} has {len(values)} "
                    f"values; expected {expected_count}"
                )

            source_row: dict[object, object] = dict(
                zip(
                    schema.column_names,
                    values,
                    strict=True,
                )
            )

            yield convert_row(
                source_row,
                schema=schema,
                row_number=row_number,
            )


class DbApiQuerySource:
    """Lazy query source for DB-API-compatible connections.

    Parameters
    ----------
    connect
        Zero-argument callable returning a new DB-API connection. The source
        owns and closes that connection.
    sql
        Nonblank SQL text.
    schema
        Exact schema required of result columns and values.
    parameters
        Optional mapping or positional sequence of bind parameters.
    fetch_size
        Number of rows requested per ``fetchmany()`` call.

    Notes
    -----
    The source executes SQL text only. Reading SQL from a file belongs to a
    separate helper or consuming program.

    A new connection and cursor are created for every ``open_rows()`` call.
    """

    def __init__(
        self,
        *,
        connect: Callable[[], object],
        sql: str,
        schema: RowSchema,
        parameters: QueryParameters | None = None,
        fetch_size: int = 500,
    ) -> None:
        self._connect = _require_connect(connect)
        self._sql = _require_sql(sql)
        self._schema = _require_schema(schema)
        self._parameters = _copy_parameters(parameters)
        self._fetch_size = _require_fetch_size(fetch_size)

    @property
    def schema(self) -> RowSchema:
        """Return the canonical output schema."""
        return self._schema

    @property
    def sql(self) -> str:
        """Return configured SQL text."""
        return self._sql

    @property
    def parameters(
        self,
    ) -> dict[str, object] | tuple[object, ...] | None:
        """Return a defensive copy of query parameters."""
        if isinstance(self._parameters, dict):
            return dict(self._parameters)

        return self._parameters

    @property
    def fetch_size(self) -> int:
        """Return the configured fetch size."""
        return self._fetch_size

    def open_rows(
        self,
    ) -> AbstractContextManager[Iterator[Row]]:
        """Return a new query-result context manager."""
        return self._open_rows()

    @contextmanager
    def _open_rows(self) -> Generator[Iterator[Row]]:
        """Open, execute, and lazily yield canonical query rows."""
        connection: _ConnectionProtocol | None = None
        cursor: _CursorProtocol | None = None

        try:
            try:
                connection_value = self._connect()
            except Exception as error:
                raise SourceExecutionError(
                    f"Could not open DB-API connection: {error}"
                ) from error

            connection = _require_connection(connection_value)

            try:
                cursor_value = connection.cursor()
            except Exception as error:
                raise SourceExecutionError(
                    f"Could not create DB-API cursor: {error}"
                ) from error

            cursor = _require_cursor(cursor_value)
            cursor.arraysize = self._fetch_size

            try:
                if self._parameters is None:
                    cursor.execute(self._sql)
                else:
                    cursor.execute(
                        self._sql,
                        self._parameters,
                    )
            except Exception as error:
                raise SourceExecutionError(
                    f"Could not execute DB-API query: {error}"
                ) from error

            column_names = _column_names_from_description(cursor.description)
            _validate_result_columns(
                column_names,
                schema=self._schema,
            )

            yield _iter_query_rows(
                cursor,
                schema=self._schema,
                fetch_size=self._fetch_size,
            )
        finally:
            if cursor is not None:
                cursor.close()

            if connection is not None:
                connection.close()
