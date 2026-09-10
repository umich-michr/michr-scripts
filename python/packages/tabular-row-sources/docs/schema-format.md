# Tabular Row Schema Format

**Status:** Canonical schema-format documentation for
`tabular-row-sources`.

A row schema defines:

- exact case-sensitive column names;
- canonical output column order;
- canonical Python value types;
- nullability.

CSV and database sources use the same schema so they can produce compatible
rows for downstream processing.

---

## 1. Schema document

A schema is a JSON object containing one `columns` array:

```json
{
  "columns": [
    {
      "name": "ID",
      "type": "integer",
      "nullable": false
    },
    {
      "name": "STUDY_NUM",
      "type": "string",
      "nullable": true
    },
    {
      "name": "CREATED_AT",
      "type": "datetime",
      "nullable": true
    },
    {
      "name": "LLM_SUGGESTIONS",
      "type": "json_object",
      "nullable": false
    }
  ]
}
```

The root object accepts only the `columns` field.

`columns` must be a nonempty JSON array.

---

## 2. Column definition

Each column object accepts:

| Field | Required | Meaning |
|---|---|---|
| `name` | Yes | Nonblank, case-sensitive column name |
| `type` | Yes | Canonical value type |
| `nullable` | No | Whether the canonical value may be `None`; defaults to `false` |

Unknown fields are rejected so misspelled or unsupported configuration cannot be
silently ignored.

Column names must be unique.

Column order is significant.

---

## 3. Supported types

| Schema value | Canonical Python type |
|---|---|
| `string` | `str` |
| `integer` | `int`, excluding `bool` |
| `decimal` | `decimal.Decimal` |
| `float` | `float` |
| `boolean` | `bool` |
| `date` | `datetime.date`, excluding `datetime.datetime` |
| `datetime` | `datetime.datetime` |
| `json_object` | `dict[str, object]` |

Type names are lowercase and case-sensitive.

A source may receive a different native representation, but it must convert the
value to the canonical Python type before yielding the row.

---

## 4. Column matching

Source implementations use strict name matching.

A source must provide:

- every schema column;
- no unexpected columns;
- no duplicate columns;
- the exact case-sensitive names.

Source columns may appear in a different order. Each source associates values
with the actual source column names and then emits canonical row dictionaries in
schema order.

This prevents changed queries or CSV exports from silently shifting values into
the wrong columns while allowing harmless source-column reordering.

A projection mode that ignores missing or unexpected columns is not supported.

---

## 5. Nullability

A canonical value may be `None` only when its column declares:

```json
"nullable": true
```

Database `NULL` values normally arrive as Python `None`.

An empty CSV field is not automatically null. Empty string and null are distinct
values.

A future CSV source will preserve `""` unless the caller explicitly configures
one or more null markers.

For example:

```python
CsvRowSource(
    path="export.csv",
    schema=schema,
    null_values=frozenset({"NULL", "\\N"}),
)
```

Only explicitly configured markers should become `None`.

---

## 6. Date and datetime values

CSV datetime values may use ISO 8601 or the audit-report export formats:

```text
MM/DD/YYYY HH:MM:SS
MM/DD/YYYY HH:MM:SS.ffffff
```

Examples:

2026-09-09T14:59:35
2026-09-09T14:59:35-04:00
05/15/2026 11:29:54
05/15/2026 11:29:54.702864

The report format requires exactly six fractional digits when a fraction ispresent. Values with greater precision are rejected rather than truncated.
Timezone-aware values remain aware. Naive values remain naive. The package doesnot silently assign a timezone.

---

## 7. Decimal and float values

Canonical `decimal` values use `decimal.Decimal`.

This avoids binary floating-point precision loss.

Canonical `float` values use Python `float`.

Boolean values must not be accepted as integers, decimals, or floats merely
because Python treats `bool` as a subclass of `int`.

Non-finite float and decimal handling will be defined by the conversion
contract before concrete sources are implemented.

---

## 8. Boolean values

Canonical Boolean values use Python `bool`.

Accepted source representations will be defined explicitly by each source and
the shared conversion layer.

The conversion layer must not rely on Python truthiness. For example:

```python
bool("false") is True
```

Therefore, textual Boolean parsing must use an explicit accepted-value mapping.

---

## 9. JSON object values

A `json_object` value becomes:

```python
dict[str, object]
```

Valid JSON values that decode to any other type are rejected, including:

- arrays;
- strings;
- numbers;
- Booleans;
- null.

Already-decoded dictionaries may be accepted after validation.

---

## 10. Parsing and loading

Parse schema JSON text:

```python
from tabular_row_sources import parse_schema_json

schema = parse_schema_json(schema_text)
```

Load a schema file:

```python
from tabular_row_sources import load_schema_json

schema = load_schema_json("audit-records.schema.json")
```

Both functions return the same immutable `RowSchema`.

Malformed definitions raise `SchemaDefinitionError`.

File-read failures raise `SourceExecutionError`.

---

## 11. Schema evolution

Schema changes can alter:

- accepted source columns;
- canonical Python types;
- downstream output;
- null handling;
- report compatibility.

Treat schema changes as public-contract changes.

When a schema changes:

1. update the schema file;
2. update affected source tests;
3. update consuming-program tests;
4. update output documentation;
5. review backward compatibility.

---

## 12. Canonical conversion

All concrete sources use the same conversion layer.

### Accepted source representations

| Schema type | Accepted source values |
|---|---|
| `string` | `str` |
| `integer` | `int`, integral finite `Decimal`, base-10 integer text |
| `decimal` | finite `Decimal`, integer, finite float, decimal text |
| `float` | finite integer, float, `Decimal`, floating-point text |
| `boolean` | Boolean, integer/Decimal `0` or `1`, text `true`, `false`, `0`, `1` |
| `date` | `date` excluding `datetime`, ISO 8601 date text |
| `datetime` | `datetime`, ISO 8601 datetime text, trailing `Z` or `z`, or `MM/DD/YYYY HH:MM:SS[.ffffff]` |
| `json_object` | dictionary, JSON text, UTF-8 JSON bytes |

Conversion rejects ambiguous or lossy values.

Examples:

- a fractional decimal is not converted to integer;
- a datetime is not silently converted to date;
- arbitrary objects are not converted with `str()`;
- Booleans are not accepted as numeric values;
- non-finite numeric values are rejected;
- JSON arrays and scalar values are not accepted as JSON objects.

### Boolean text

Boolean conversion is explicit and case-insensitive.

Accepted text values:

```text
true
false
1
0
```

Python truthiness is not used.

### Numeric finiteness

Canonical decimal and float values must be finite.

Rejected examples include:

```text
NaN
Infinity
-Infinity
```

### Row conversion

`convert_row()` requires exact source-column-name agreement with the schema:

- same names;
- same case;
- no missing columns;
- no extra columns.

Input order may differ. The function returns a fresh dictionary whose keys
follow schema order and whose values use canonical Python types.

Optional row numbers may be supplied for error reporting.
