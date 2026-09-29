# Normalized Study Posting Audit report

A successful `study-posting-audit-report` run atomically publishes four files.

```text
report/
├── records.csv
├── ai_assistance_metrics.csv
├── readability_metrics.csv
└── report_metadata.json
```

The destination must not already exist. Publication uses a staging directory;
a failed run removes staging output and does not publish a partial report.

## `records.csv`

Grain: one successfully processed source attempt.

The file preserves manual, incomplete AI, and completed AI attempts in canonical
schema order.

Key:

```text
configured record ID column
```

The default is `ID`, which must be nonmissing and unique.

The file may contain sensitive identifiers, payloads, metadata, and free text.
It is not a faculty-facing aggregate.

Important source classifications are:

- `ATTEMPT_TYPE`: `AI` when a generation-audit source input method is present;
  otherwise `MANUAL`;
- `ATTEMPT_RESULT`, in source-query precedence:
  `AI_ERROR`, `AI_ERROR_WITHOUT_STACK_TRACE`, `USER_DROPPED`, or `COMPLETE`;
- `USER_TYPE`: `EXISTED` when the author matched an application study-team
  relationship for that study; otherwise `NON_EXISTENT`.

`AI_ERROR_WITHOUT_STACK_TRACE` is a defensive anomaly category. Empty
suggestion arrays in a valid response are not an error.

`SOURCE_TYPE` is the source input method, such as directly entered text or text
extracted in the browser from a supported file. It is distinct from the
user-reported and model-inferred content-source categories.

`TIME_SPENT_ON_STUDY_INFO_PAGE_MS` estimates time on the Study Information form
during one attempt, from display until the user continues. It may include
pauses. `TIME_TO_FINISH_ADDING_STUDY_MS` measures the completed Add Study
workflow through the Study Information and Inclusion/Exclusion Criteria steps
and posting creation. Timing values are not summed across separate attempts.

Generated suggestions, the latest selected suggestions, and final saved values
are separate complete-text payloads. Selection position is derived later by
exact text matching against the ordered generated list. Selection-click history
is not available.

Selection/feedback, final-value, and timing updates are separate writes. One
component can therefore be unavailable even when another was saved. See the
[feature and audit model](feature-and-audit-model.md) for lifecycle details.

## `ai_assistance_metrics.csv`

Grain: one analyzed field from a completed AI attempt.

Join:

```text
ai_assistance_metrics.record_id = records.ID
```

Rows follow `study_posting_ai_analysis.FLATTENED_COLUMNS`.

Only completed AI attempts produce these rows. Selected and final text are
excluded by default. Enabling `--include-text` affects this flattened file only;
it does not remove payloads from `records.csv`.

## `readability_metrics.csv`

Grain: one eligible, nonblank text instance.

Join:

```text
readability_metrics.record_id = records.ID
```

Completed AI attempts contribute offered suggestions and final values.
Completed manual attempts contribute final values. Incomplete attempts
contribute no readability rows.

The file contains metric values and labels, not source text. Blank text is
omitted, so absence of a row does not prove that a field was absent from the
source.

## `report_metadata.json`

Grain: one normalized-report run.

Schema version is currently `1`.

Fields:

| Field | Meaning |
|---|---|
| `schema_version` | Metadata schema version |
| `report_generated_at_utc` | UTC instant captured once for report generation |
| `source_snapshot_as_of_utc` | Report-run cutoff for new reports |
| `source_snapshot_provenance` | `REPORT_RUN_CUTOFF` for new reports |

New reports reuse one captured UTC instant for report generation and source
cutoff. The cutoff is not inferred from attempt, completion, creation, login,
filesystem, or downstream publication timestamps.

## Analysis eligibility

A row is selected for field analysis when:

```text
ATTEMPT_TYPE = AI
ATTEMPT_RESULT = COMPLETE
```

The comparison is exact and case-sensitive.

An eligible row must also have:

- nonmissing `END_TIME`;
- `LLM_SUGGESTIONS`;
- `SELECTED_SUGGESTIONS`;
- `FINAL_SUBMISSION`.

Missing required values raise `AuditRowError`.

Manual and incomplete attempts remain in `records.csv` without field metrics.

## Summary invariants

The program is fail-fast.

For a successful report:

```text
analyzable_rows = analyzed_rows
failed_rows = 0
source_rows = analyzed_rows + skipped_rows
```

`skipped_rows` are all source attempts outside the exact
`ATTEMPT_TYPE = AI` and `ATTEMPT_RESULT = COMPLETE` analysis population. They
are preserved without study-field analysis.

## Serialization

CSV output uses:

- UTF-8;
- canonical declared column order;
- the configured missing-value representation;
- atomic publication through staging.

The source schema is
`input/audit-schema.json`. The exact source-column dictionary and downstream
lineage are maintained in the exploration
[data-lineage guide](../../study-posting-audit-exploration/docs/data-lineage.md).

## Privacy

Treat the normalized report as sensitive institutional data.

- Do not commit it.
- Do not attach it to issues or public discussions.
- Do not log payloads, free text, or identifiers.
- Keep flattened text disabled unless required.
- Store and process it only in approved environments.

Faculty-facing output is produced later by the exploration program from
aggregate tables, except for its narrowly authorized feedback display.
