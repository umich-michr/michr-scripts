---
applyTo: "python/packages/tabular-row-sources/**"
---

# tabular-row-sources instructions

## Contract

This package provides context-managed, lazy sources of tabular rows:

```python
with source.open_rows() as rows:
    for row in rows:
        process(row)
```

Rows are `dict[str, object]`.

## Invariants

Every source must:

- accept source columns in any order;
- emit row dictionaries in canonical schema order;
- require nonblank, unique string column names;
- yield fresh row dictionaries;
- stream rather than load unbounded input;
- close resources on success, failure, and early termination;
- raise package exceptions for expected source failures.

CSV and database sources share a row interface, not guaranteed Python value
types.

## Scope

This package may own CSV, DB-API, and optional database adapters.

It must not contain:

- study-posting policy;
- audit eligibility;
- source-to-analysis column mapping;
- aggregation;
- report writing;
- application CLI or logging.

Credentials and SQL may be accepted as inputs, but configuration-source policy
belongs to consuming programs.

## Testing

Use synthetic data, temporary files, and fake database objects.

Default tests must not require:

- network access;
- live databases;
- credentials;
- Oracle client installation.

## Schema contract

Every concrete source requires a `RowSchema`.

The schema controls:

- exact case-sensitive column names;
- canonical output column order;
- canonical Python value types;
- nullability.

Schema JSON parsing and loading belong to this package.

Strict name matching is the default. Accept source columns in any order, then
reorder them to schema order. Do not silently ignore, add, or drop columns.

CSV and database sources must use the same conversion layer so the same schema
produces compatible canonical values.
