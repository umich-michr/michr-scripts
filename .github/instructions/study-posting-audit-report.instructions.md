---
applyTo: "python/programs/study-posting-audit-report/**"
---

# study-posting-audit-report instructions

This runnable program composes:

- `tabular-row-sources`;
- `study-posting-ai-analysis`;
- transitively, `text-post-edit-metrics`.

It owns source-column mapping, eligibility, record identity, error policy,
output serialization, atomic output files, CLI behavior, configuration, and
logging.

It must not duplicate row-source conversion or study-analysis logic.

Default successful outputs are:

- `records.csv`: one row per source record;
- `field_metrics.csv`: one row per analyzed field.

`field_metrics.record_id` joins to the configured source ID column in
`records.csv`.

Record IDs must be non-null and unique.

Free text remains excluded by default.

Use named CLI options. Do not log source JSON payloads, selected text, final
text, credentials, or secret-bearing connection strings.

Tests use synthetic rows and must not require a live database or credentials.
