# tabular-row-sources

Schema-aware, lazy sources of canonical tabular rows.

The package gives consuming programs one interface for rows obtained from CSV
files or DB-API queries:

```python
with source.open_rows() as rows:
    for row in rows:
        process(row)
```

Both source types use the same `RowSchema` and conversion layer.

## Responsibilities

The package owns:

- canonical row and schema models;
- schema JSON parsing and loading;
- value conversion and nullability validation;
- CSV parsing;
- DB-API query execution and lazy fetching;
- SQL-file loading;
- source-column validation;
- deterministic file, cursor, and connection cleanup;
- source-specific exceptions.

It does not own:

- application configuration precedence;
- credentials or database-driver selection;
- study-posting analysis;
- audit-row selection;
- aggregation;
- report writing;
- application logging;
- command-line behavior.

Database connection setup belongs to the consuming program. This package
accepts a zero-argument connection factory.

## Public API

Important exports include:

```python
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
    convert_row,
    convert_value,
    load_schema_json,
    parse_schema_json,
    read_sql_file,
)
```

Expected failures derive from `RowSourceError`.

## Row source protocol

Concrete sources satisfy the structural `RowSource` protocol:

```python
source.schema

with source.open_rows() as rows:
    for row in rows:
        process(row)
```

A source must:

- use a supplied `RowSchema`;
- stream rather than load an unbounded source;
- yield a fresh `dict[str, object]` for each row;
- produce canonical values;
- emit keys in schema order;
- enforce nullability;
- close owned resources after completion, failure, or early termination;
- return a new context manager for every `open_rows()` call.

Classes satisfy the protocol structurally and do not need to inherit from a
package base class.

## Schema contract

A schema is an ordered tuple of column definitions:

```python
from tabular_row_sources import (
    ColumnSpec,
    ColumnType,
    RowSchema,
)

schema = RowSchema(
    columns=(
        ColumnSpec(
            name="ID",
            data_type=ColumnType.INTEGER,
        ),
        ColumnSpec(
            name="CREATED_AT",
            data_type=ColumnType.DATETIME,
            nullable=True,
        ),
        ColumnSpec(
            name="PAYLOAD",
            data_type=ColumnType.JSON_OBJECT,
            nullable=True,
        ),
    )
)
```

Column names are case-sensitive, nonblank, and unique.

A source must provide exactly the schema's column names:

- source order may differ;
- missing columns are rejected;
- unexpected columns are rejected;
- blank or duplicate names are rejected;
- output rows always follow schema order.

Supported canonical types are:

| Schema type | Python type |
|---|---|
| `string` | `str` |
| `integer` | `int`, excluding `bool` |
| `decimal` | `decimal.Decimal` |
| `float` | `float` |
| `boolean` | `bool` |
| `date` | `datetime.date`, excluding `datetime.datetime` |
| `datetime` | `datetime.datetime` |
| `json_object` | `dict[str, object]` |

See the canonical
[schema-format documentation](docs/schema-format.md)
for JSON syntax, accepted source representations, datetime formats,
nullability, conversion rules, and schema evolution.

## Loading a schema

Load a JSON schema file:

```python
from tabular_row_sources import load_schema_json

schema = load_schema_json("input/audit-schema.json")
```

Or parse schema JSON directly:

```python
from tabular_row_sources import parse_schema_json

schema = parse_schema_json(schema_text)
```

Invalid definitions raise `SchemaDefinitionError`. File-reading failures raise
`SourceExecutionError`.

## CSV source

```python
from tabular_row_sources import (
    CsvRowSource,
    load_schema_json,
)

schema = load_schema_json("input/audit-schema.json")

source = CsvRowSource(
    path="input/audit.csv",
    schema=schema,
)

with source.open_rows() as rows:
    for row in rows:
        process(row)
```

`CsvRowSource`:

- validates the header against schema column names;
- accepts header columns in any order;
- reads logical CSV records lazily;
- associates values with their actual header names;
- emits rows in schema order;
- converts values through the shared conversion layer;
- closes the file when the context exits.

Default encoding is `utf-8-sig`, which accepts ordinary UTF-8 and removes an
optional UTF-8 byte-order mark.

### CSV options

```python
from tabular_row_sources import CsvReadOptions

options = CsvReadOptions(
    delimiter=",",
    quotechar='"',
    escapechar=None,
    doublequote=True,
    skipinitialspace=False,
    strict=True,
)

source = CsvRowSource(
    path="input/audit.csv",
    schema=schema,
    options=options,
)
```

### Null markers

An empty CSV field remains `""` unless explicitly configured as null.

```python
source = CsvRowSource(
    path="input/audit.csv",
    schema=schema,
    null_values=frozenset({"", "\\N"}),
)
```

Only exact configured markers become `None`. The schema then determines whether
`None` is permitted for that column.

Null-marker policy belongs to the consumer because different exports represent
null values differently.

## DB-API query source

`DbApiQuerySource` accepts a zero-argument connection factory:

```python
from tabular_row_sources import DbApiQuerySource

source = DbApiQuerySource(
    connect=connection_factory,
    sql=("SELECT ID, TITLE FROM SYNTHETIC_RECORDS WHERE STATUS = :status"),
    parameters={
        "status": "ACTIVE",
    },
    schema=schema,
    fetch_size=500,
)

with source.open_rows() as rows:
    for row in rows:
        process(row)
```

The query source:

- creates a connection and cursor for each `open_rows()` call;
- passes bind parameters separately from SQL;
- reads column names from standard DB-API description sequences or compatible
  driver metadata objects exposing a `name` attribute;
- validates result-column names against the schema;
- accepts result columns in any order;
- calls `fetchmany()` rather than `fetchall()`;
- converts rows through the shared conversion layer;
- closes the cursor and connection when the context exits.
- materializes driver-provided CLOB or BLOB objects exposing `read()` before
  canonical conversion;

Large-object materialization happens one field at a time while its row is being
processed. The row stream remains lazy, although an individual CLOB or BLOB
field is read completely before canonical conversion.

The source owns connections returned by its connection factory.

It does not own:

- credentials;
- DSNs;
- wallets;
- dotenv or environment-variable policy;
- database-driver selection.

## SQL files

Load SQL explicitly:

```python
from tabular_row_sources import read_sql_file

sql = read_sql_file("input/report.sql")
```

`read_sql_file()`:

- reads text using an explicit encoding;
- rejects blank SQL;
- preserves SQL after decoding;
- does not execute, interpolate, parse, split, normalize, or remove comments.

Bind values must remain separate from SQL text.

## Canonical conversion

The shared conversion API is available independently:

```python
from tabular_row_sources import (
    convert_row,
    convert_value,
)
```

Conversion is strict. It rejects ambiguous or lossy values, including:

- Booleans used as numeric values;
- fractional values converted to integers;
- datetimes silently converted to dates;
- non-finite decimal or float values;
- JSON arrays or scalars where an object is required;
- unsupported arbitrary objects.

`convert_row()` accepts source mappings in any column order and returns a fresh
dictionary in schema order.

Detailed conversion behavior is authoritative in
[`docs/schema-format.md`](docs/schema-format.md).

## Exceptions

| Exception | Meaning |
|---|---|
| `SchemaDefinitionError` | Schema JSON or schema objects are invalid |
| `SourceConfigurationError` | Source options are invalid |
| `SourceFormatError` | Source names, row shape, or result metadata are invalid |
| `ValueConversionError` | A value cannot be converted or violates nullability |
| `SourceExecutionError` | A file or query cannot be opened, executed, fetched, decoded, or read |

`ValueConversionError` is a subtype of `SourceFormatError`. All expected source
failures derive from `RowSourceError`.

## Security

- Pass SQL bind values separately from SQL text.
- Do not log source rows, credentials, or secret-bearing connection strings.
- Do not embed database credentials or driver policy in this package.
- Use synthetic rows and fake database objects in tests.
- Default tests require no network access, database, credentials, or Oracle
  client installation.

## Development

Run from the repository root:

```bash
make test PACKAGE=tabular-row-sources
make coverage PACKAGE=tabular-row-sources
make check
```

See the [root README](../../../README.md) for workspace-wide guidance.

## License

MIT
