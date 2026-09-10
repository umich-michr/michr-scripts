# tabular-row-sources

Schema-aware, lazy sources of canonical tabular rows.

A consuming program can process rows from CSV files and, later, database queries
through one interface while receiving the same:

- case-sensitive column names;
- column order;
- canonical Python value types;
- nullability behavior.

---

## Basic usage

Load a schema and stream a CSV file:

```python
from tabular_row_sources import (
    CsvRowSource,
    load_schema_json,
)

schema = load_schema_json("audit-records.schema.json")

source = CsvRowSource(
    path="audit-export.csv",
    schema=schema,
)

with source.open_rows() as rows:
    for row in rows:
        process(row)
```

A source owns its resources. Always use `open_rows()` in a `with` statement so
files, cursors, and connections close after:

- normal completion;
- early termination;
- conversion failure;
- consumer failure.

---

## Row contract

A canonical row is:

```python
type Row = dict[str, object]
```

Every source must:

- use a supplied `RowSchema`;
- preserve schema column order;
- require exact schema-column matching;
- yield a fresh dictionary for every row;
- convert values to canonical Python types;
- enforce nullability;
- stream rather than load an unbounded source;
- close resources deterministically.

---

## Schema contract

A schema is an ordered tuple of `ColumnSpec` values:

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
            nullable=False,
        ),
        ColumnSpec(
            name="STUDY_NUM",
            data_type=ColumnType.STRING,
            nullable=True,
        ),
        ColumnSpec(
            name="CREATED_AT",
            data_type=ColumnType.DATETIME,
            nullable=True,
        ),
    )
)
```

Column names are:

- case-sensitive;
- nonblank;
- unique;
- ordered.

Sources must provide exactly the schema columns in schema order. Missing,
unexpected, reordered, blank, and duplicate columns are rejected.

A relaxed projection mode is not supported.

---

## Schema JSON

Schemas may be parsed from JSON text:

```python
from tabular_row_sources import parse_schema_json

schema = parse_schema_json(
    """
    {
      "columns": [
        {
          "name": "ID",
          "type": "integer",
          "nullable": false
        },
        {
          "name": "PAYLOAD",
          "type": "json_object",
          "nullable": false
        }
      ]
    }
    """
)
```

Or loaded from a JSON file:

```python
from tabular_row_sources import load_schema_json

schema = load_schema_json("audit-records.schema.json")
```

See the canonical
[schema-format documentation](docs/schema-format.md)
for the JSON format, supported types, nullability, conversion policy, and schema
evolution guidance.

---

## Canonical value types

| Schema type | Canonical Python type |
|---|---|
| `string` | `str` |
| `integer` | `int`, excluding `bool` |
| `decimal` | `decimal.Decimal` |
| `float` | `float` |
| `boolean` | `bool` |
| `date` | `datetime.date`, excluding `datetime.datetime` |
| `datetime` | `datetime.datetime` |
| `json_object` | `dict[str, object]` |

A shared schema lets CSV and database sources expose both the same row shape and
the same canonical value types.

Without conversion:

- CSV values are strings;
- database drivers may return integers, decimals, dates, datetimes, bytes,
  strings, or driver-specific objects.

---

## Canonical conversion

Concrete sources use the same conversion functions:

```python
from tabular_row_sources import (
    convert_row,
    convert_value,
)
```

`convert_value()` converts one value according to a `ColumnSpec`.

`convert_row()`:

- requires exact column names and order;
- validates every value;
- enforces nullability;
- returns a fresh dictionary in schema order;
- may include a source row number in errors.

The conversion layer rejects ambiguous or lossy conversions. For example:

- Booleans are not accepted as numeric values;
- fractional values are not truncated to integers;
- datetimes are not silently converted to dates;
- arbitrary objects are not converted with `str()`;
- non-finite numeric values are rejected;
- JSON arrays and scalar values are not accepted as JSON objects.

---

## CSV source

`CsvRowSource`:

- requires a header row;
- requires exact header agreement with the schema;
- validates blank and duplicate headers;
- reads logical CSV records lazily;
- converts values through the shared conversion layer;
- supports configurable CSV parsing options;
- supports explicit null markers;
- removes an optional UTF-8 byte-order mark by default;
- closes the file when the context exits.

### Empty fields and null markers

An empty CSV field remains `""` by default. Empty string and null are distinct.

Configure explicit null markers when an export uses them:

```python
source = CsvRowSource(
    path="audit-export.csv",
    schema=schema,
    null_values=frozenset({"NULL", "\\N"}),
)
```

Only exact configured markers become `None`.

A resulting `None` is accepted only when the schema column is nullable.

### CSV parser options

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
    path="audit-export.csv",
    schema=schema,
    options=options,
)
```

---

## Source protocol

Concrete sources implement the structural `RowSource` protocol:

```python
with source.open_rows() as rows:
    for row in rows:
        process(row)
```

The source exposes:

```python
source.schema
```

and returns a new context manager from each `open_rows()` call.

A class satisfies the protocol structurally; it does not need to inherit from a
package base class.

---

## Nullability

Database `NULL` values normally arrive as Python `None`.

CSV fields become `None` only through explicit null-marker configuration.

For every source:

- `None` is retained when the schema column is nullable;
- `None` is rejected when the schema column is not nullable.

The package does not silently treat an empty string as null.

---

## Exceptions

All expected package failures derive from `RowSourceError`.

| Exception | Meaning |
|---|---|
| `SchemaDefinitionError` | Schema JSON or schema objects are invalid |
| `SourceConfigurationError` | Source options are invalid |
| `SourceFormatError` | Source columns or row shape do not match the schema |
| `ValueConversionError` | A value cannot be converted or violates nullability |
| `SourceExecutionError` | A file or query cannot be opened, executed, fetched, decoded, or read |

`ValueConversionError` is a subtype of `SourceFormatError`.

---

## Scope

This package owns:

- schema models and validation;
- schema JSON parsing and loading;
- canonical value conversion;
- exact column and row-shape validation;
- lazy CSV reading;
- future lazy DB-API query reading;
- future optional database adapters;
- source resource lifecycle;
- source exceptions.

It does not own:

- study-posting analysis;
- audit-record eligibility;
- source-to-analysis field mapping;
- aggregation;
- report generation;
- output CSV writing;
- application configuration policy;
- application logging;
- application CLI behavior.

Those responsibilities belong to consuming programs.

---

## Implementation status

Available:

- schema models and validation;
- schema JSON parsing and loading;
- canonical value and row conversion;
- lazy CSV row source;
- generic lazy DB-API query source;
- package exception hierarchy.

Planned:

1. SQL-file loading helper;
2. optional Oracle connection adapter.

The default test suite does not require network access, credentials, a live
database, or Oracle client software.

## DB-API query source

`DbApiQuerySource` accepts a zero-argument connection factory:

```python
from tabular_row_sources import DbApiQuerySource

source = DbApiQuerySource(
    connect=connection_factory,
    sql="SELECT ID, TITLE FROM RECORDS WHERE STATUS = :status",
    parameters={"status": "ACTIVE"},
    schema=schema,
    fetch_size=500,
)

with source.open_rows() as rows:
    for row in rows:
        process(row)
```

The query source:

- creates a new connection and cursor for each `open_rows()` call;
- passes bind parameters separately from SQL;
- validates result metadata against the schema;
- sets cursor `arraysize`;
- calls `fetchmany()` rather than `fetchall()`;
- converts values through the shared conversion layer;
- closes cursor and connection when the context exits.

The source owns connections returned by its connection factory.

Credentials, DSNs, environment variables, and SQL-file selection belong to
adapters or consuming programs.

## SQL files

`DbApiQuerySource` accepts SQL text. It does not guess whether a string is SQL or
a path.

Load a version-controlled SQL file explicitly:

```python
from tabular_row_sources import (
    DbApiQuerySource,
    read_sql_file,
)

sql = read_sql_file("queries/report.sql")

source = DbApiQuerySource(
    connect=connection_factory,
    sql=sql,
    schema=schema,
)
```

`read_sql_file()` preserves the SQL text after decoding. It does not interpolate,
parse, split, normalize, or execute SQL.

---

## Development

Run commands from the repository root.

```bash
make test PACKAGE=tabular-row-sources
make coverage PACKAGE=tabular-row-sources
make check
```

Shared setup and workspace guidance are documented in the
[root README](../../../README.md).

---

## License

MIT
