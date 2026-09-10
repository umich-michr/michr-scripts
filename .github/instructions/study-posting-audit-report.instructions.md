---
applyTo: "python/programs/study-posting-audit-report/**"
---

# study-posting-audit-report instructions

This runnable program composes:

- `tabular-row-sources`;
- `study-posting-ai-analysis`;
- transitively, `text-post-edit-metrics`;
- the shared configuration-resolution package when command-line configuration
  is added.

It owns:

- source selection and source-column mapping;
- payload-state policy;
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

Record IDs must be non-null and unique. Rows with three null analysis payloads
remain in `records.csv` without field metrics. Rows with partial payload
presence raise `AuditRowError`.

Free text remains excluded by default.

Use named CLI options. Do not log source JSON payloads, selected text, final
text, credentials, passwords, or secret-bearing connection strings.

SQL bind values must be passed separately to the database driver. Never
construct SQL by interpolating configuration values.

Tests use synthetic rows and fake database connections. They must not require a
live database or credentials.
