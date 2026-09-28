# tabular-row-sources

Schema-aware, lazy sources of canonical tabular rows.

```python
with source.open_rows() as rows:
    for row in rows:
        process(row)
```

CSV and DB-API sources use the same `RowSchema` and conversion layer.

## Basic schema

```python
from tabular_row_sources import ColumnSpec, ColumnType, RowSchema

schema = RowSchema(
    columns=(
        ColumnSpec(name="ID", data_type=ColumnType.INTEGER),
        ColumnSpec(
            name="CREATED_AT",
            data_type=ColumnType.DATETIME,
            nullable=True,
        ),
    )
)
```

Column names are case-sensitive, nonblank, and unique. Source columns may arrive
in any order but must match the schema exactly. Yielded dictionaries follow
schema order.

See [`docs/schema-format.md`](docs/schema-format.md) for the JSON format,
conversion rules, null handling, datetime formats, and evolution policy.

## CSV

```python
from tabular_row_sources import CsvRowSource

source = CsvRowSource(
    path="input/audit.csv",
    schema=schema,
    null_values=frozenset({"", "\\N"}),
)
```

CSV rows are streamed. Default encoding is `utf-8-sig`.

Empty fields remain strings unless configured as exact null markers.

## DB-API

```python
from tabular_row_sources import DbApiQuerySource

source = DbApiQuerySource(
    connect=connection_factory,
    sql="SELECT ID, CREATED_AT FROM RECORDS WHERE STATUS = :status",
    parameters={"status": "ACTIVE"},
    schema=schema,
    fetch_size=500,
)
```

The source opens one connection and cursor per context, uses `fetchmany()`, and
closes resources on completion, failure, or early exit.

Database driver, credentials, DSN, and configuration policy belong to the
consumer.

## SQL files

```python
from tabular_row_sources import read_sql_file

sql = read_sql_file("input/report.sql")
```

The function reads and validates nonblank SQL. It does not interpolate, execute,
split, or normalize it.

## Conversion

`convert_value()` and `convert_row()` are available independently.

Supported canonical types include strings, integers, decimals, floats,
Booleans, dates, datetimes, and JSON objects.

Conversion rejects ambiguous or lossy values such as:

- Booleans used as numbers;
- fractional integers;
- non-finite numbers;
- datetimes silently converted to dates;
- JSON arrays where an object is required;
- arbitrary objects coerced with `str()`.

## Scope

The package owns schema models, parsing, conversion, CSV/DB-API streaming, SQL
file loading, column validation, resource cleanup, and source exceptions.

It does not own application configuration, credentials, database-driver
selection, study policy, aggregation, reporting, CLI behavior, or logging.

## Exceptions

Expected failures derive from `RowSourceError`:

- `SchemaDefinitionError`;
- `SourceConfigurationError`;
- `SourceFormatError`;
- `ValueConversionError`;
- `SourceExecutionError`.

## Development

```bash
make test PACKAGE=tabular-row-sources
make coverage PACKAGE=tabular-row-sources
make check
```

## License

MIT
