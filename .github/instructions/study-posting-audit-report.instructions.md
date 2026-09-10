---
applyTo: "python/programs/study-posting-audit-report/**"
---

# study-posting-audit-report instructions

This runnable program composes:

- `tabular-row-sources`;
- `study-posting-ai-analysis`;
- transitively, `text-post-edit-metrics`;
- `program-configuration` for layered CLI, environment, dotenv, default, and
  prompt resolution.

It owns:

- source selection and source-column mapping;
- completed-AI analysis-selection policy;
- record identity and duplicate detection;
- per-record error policy;
- normalized report generation;
- output serialization and atomic publication;
- CLI behavior;
- program-specific configuration;
- database-driver selection and connection configuration;
- application logging when introduced.

It must not duplicate:

- generic configuration precedence and prompting;
- row-source schema conversion or streaming;
- study-analysis policy;
- generic post-edit metric calculations.

Default successful outputs are:

- `records.csv`: one row per source record;
- `field_metrics.csv`: one row per analyzed field.

`field_metrics.record_id` joins to the configured source ID column in
`records.csv`.

Record IDs must be non-null and unique. Manual and incomplete attempts remain in
`records.csv` without field metrics. Completed AI attempts require a non-null
end time and all three analysis payloads; inconsistent completed AI rows raise
`AuditRowError`.

Free text remains excluded by default.

Use named CLI options. Do not log source JSON payloads, selected text, final
text, credentials, passwords, or secret-bearing connection strings.

The CSV command must construct `CsvRowSource` and then call the existing report
API. It must not duplicate row conversion, record processing, or output logic.

Configuration precedence is owned by `program-configuration`:

```text
CLI → process environment → dotenv → default → prompt
```

The report program owns setting names, environment-variable names, workspace
defaults, and command-line syntax.

SQL bind values must be passed separately to the database driver. Never
construct SQL by interpolating configuration values.

Tests use synthetic rows and fake database connections. They must not require a
live database or credentials.

Oracle connection creation belongs in the report program. The generic
`tabular-row-sources` package receives only a zero-argument connection factory.

Use python-oracledb thin mode. Do not call `init_oracle_client()` unless a later
documented requirement explicitly introduces thick mode.

Do not include passwords in command-line options, representations, errors, or
logs. Oracle tests must use injected or monkeypatched connectors and must not
contact a live database.
