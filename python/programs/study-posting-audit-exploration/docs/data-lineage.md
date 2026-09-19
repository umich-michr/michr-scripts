# Study Posting Audit data lineage

## Purpose

This document maps source concepts through normalized files, derived tables,
aggregate outputs, and the faculty-facing report.

Use it to answer:

- Where did this data point come from?
- What does this column mean?
- Which rows were eligible?
- Which code calculated the value?
- Where can the value be independently checked?

## End-to-end flow

```text
CSV export or Oracle query
        ↓
audit schema and canonical conversion
        ↓
study-posting-audit-report
        ↓
records.csv
ai_assistance_metrics.csv
readability_metrics.csv
        ↓
study-posting-audit-exploration validation and derivation
        ↓
analysis-audit records
aggregate CSV files
metric definitions
candidate research questions
report.html
```

## Source-layer ownership

| Layer | Owner |
|---|---|
| Operational SQL projection | `study-posting-audit-report/input/audit-rows.example.sql` |
| Canonical 39-column schema | `study-posting-audit-report/input/audit-schema.json` |
| Schema conversion rules | `tabular-row-sources/docs/schema-format.md` |
| Normalized report generation | `study-posting-audit-report` |
| Study field analysis | `study-posting-ai-analysis` |
| Generic post-edit calculations | `text-post-edit-metrics` |
| Generic readability calculations | `text-readability-metrics` |
| Exploration derivation and aggregates | `study-posting-audit-exploration` |

The committed SQL is a sanitized template. Local operational SQL is ignored and
must not be committed.

## Canonical `records.csv` column dictionary

The schema defines 39 columns. Meanings below are derived from the committed
sanitized SQL template and current analysis policy.

| Column | Type | Nullable | Source and meaning |
|---|---|---:|---|
| `ID` | integer | No | `study_posting_audit.id`; unique audit attempt ID |
| `START_TIME` | datetime | No | Attempt start time from the audit row |
| `END_TIME` | datetime | Yes | Attempt end time; null for incomplete attempts |
| `ATTEMPT_TYPE` | string | No | `AI` when generation-audit `source_type` is present; otherwise `MANUAL` |
| `ATTEMPT_RESULT` | string | No | Derived from stack trace, zero latency without stack trace, missing end time, or completion |
| `USER_TYPE` | string | No | `EXISTED` when the author matched the study-role join; otherwise `NON_EXISTENT` |
| `STUDY_NUM` | string | No | Study identifier used to group attempts |
| `CREATED_DATE` | datetime | Yes | Created study timestamp joined by study number |
| `CREATED_BY_ID` | integer | Yes | Application user ID that created the study |
| `PUBLISHABLE` | boolean | Yes | Study publishable flag |
| `STUDY_DEPARTMENT` | string | Yes | Study department lookup display value |
| `STUDY_PARTICIPANT_TYPE` | string | Yes | Derived category: `HEALTHY`, `CONDITION`, or `Both` |
| `USER_ID` | integer | Yes | Attempt author's application user ID from the study-role join |
| `AUTHOR_USER_NAME` | string | No | Exact attempt author username from the audit row |
| `AUTHOR_STUDY_TEAM_ROLE` | string | Yes | Attempt author's application study-team role |
| `AUTHOR_ERESEARCH_ROLE` | string | Yes | Attempt author's joined eResearch study role |
| `AUTHOR_APPOINTMENTS` | string | Yes | Appointments active at attempt start, serialized as `Title:Department:School` records separated by `~|APPOINTMENT|~` |
| `PI_USER_NAME` | string | Yes | Imported username of the study PI |
| `PI_APPOINTMENTS` | string | Yes | PI appointments active at attempt start using the explicit record separator |
| `PRIOR_CREATED_COUNT` | integer | Yes | Other studies created by the attempt author before `START_TIME` |
| `TOTAL_CREATED_COUNT` | integer | Yes | Total studies created by the attempt author at report-query time |
| `MEMBER_OF_OTHER_STUDIES_COUNT` | integer | Yes | Other memberships at report-query time, excluding the attempted study |
| `LOGIN_DAYS` | integer | Yes | Distinct calendar days with a successful login in available history |
| `MIN_LOGIN_TIME` | datetime | Yes | Earliest successful login in available history |
| `MAX_LOGIN_TIME` | datetime | Yes | Latest successful login in available history |
| `TIME_SPENT_ON_STUDY_INFO_PAGE_MS` | integer | Yes | Recorded study-information-page duration in milliseconds |
| `TIME_TO_FINISH_ADDING_STUDY_MS` | integer | Yes | `END_TIME - START_TIME` converted to milliseconds |
| `LATENCY_MS` | integer | Yes | Generation latency from the generation-audit row |
| `SOURCE_SIZE_CHARS` | integer | Yes | Character size of the generation source |
| `SOURCE_TYPE` | string | Yes | Generation source type; null for manual attempts under current SQL |
| `STUDY_CONTENT_SOURCE` | string | Yes | User-reported content-source lookup display text |
| `LLM_INFERRED_STUDY_CONTENT_SOURCE` | string | Yes | Model-suggested content-source lookup display text |
| `STUDY_CONTENT_SOURCE_OTHER_VALUE` | string | Yes | User free text when reported content source is Other |
| `LLM_INFERRED_STUDY_CONTENT_SOURCE_OTHER_VALUE` | string | Yes | Model-suggested free text for an Other source category |
| `USER_FEEDBACK_COMMENTS` | string | Yes | Self-reported feedback captured by generation audit |
| `LLM_SUGGESTIONS` | JSON object | Yes | Suggestions offered by the model |
| `SELECTED_SUGGESTIONS` | JSON object | Yes | Suggestions or values selected by the author |
| `FINAL_SUBMISSION` | JSON object | Yes | Final saved study-posting values |
| `LLM_METADATA` | JSON object | Yes | Model metadata captured by generation audit |

### Source caveats

- The committed SQL is a sanitized example, not the operational query.
- Local table, view, database-link, and exclusion details can differ.
- `STACK_TRACE` helps derive attempt result but is not projected.
- Appointment records use the printable separator `~|APPOINTMENT|~`.
- Source joins must produce no more than one final row per audit `ID`.
- Total-created, membership, and login values are query-time context.
- Recorded durations are not direct measures of active cognitive work.

## Normalized report files

### `records.csv`

Grain: one audit attempt.

Key:

```text
ID
```

Important identity and grouping fields:

| Column | Meaning |
|---|---|
| `ID` | Application-assigned audit attempt ID |
| `STUDY_NUM` | Groups attempts belonging to one study |
| `AUTHOR_USER_NAME` | Exact attempt-author identity |
| `USER_ID` | Application user ID when present |
| `CREATED_BY_ID` | Creator of the completed study, not preceding-attempt author |
| `PI_USER_NAME` | Named study principal investigator |

Important workflow fields:

| Column | Meaning |
|---|---|
| `START_TIME` | Attempt start timestamp |
| `END_TIME` | Attempt completion timestamp when complete |
| `ATTEMPT_TYPE` | AI or manual authoring mode |
| `ATTEMPT_RESULT` | Complete or exact incomplete-result category |
| `TIME_SPENT_ON_STUDY_INFO_PAGE_MS` | Recorded study-information-page time |
| `TIME_TO_FINISH_ADDING_STUDY_MS` | Recorded total completed-attempt time |

Important source and content fields:

| Column | Meaning |
|---|---|
| `SOURCE_TYPE` | Uploaded or entered source format |
| `STUDY_CONTENT_SOURCE` | User-reported content source |
| `LLM_INFERRED_STUDY_CONTENT_SOURCE` | Model-inferred content source |
| `USER_FEEDBACK_COMMENTS` | Self-reported AI-usefulness feedback when supplied |
| `LLM_SUGGESTIONS` | Suggestions payload |
| `SELECTED_SUGGESTIONS` | User selections payload |
| `FINAL_SUBMISSION` | Final saved values payload |
| `LLM_METADATA` | Model metadata payload |

Source semantics should be checked against the sanitized SQL template and schema,
then against the report README.

### `ai_assistance_metrics.csv`

Grain: one analyzed field for a completed AI attempt.

Join:

```text
ai_assistance_metrics.record_id = records.ID
```

Contains:

- field identity and analysis type;
- offer and selection structure;
- match classification;
- post-edit metrics;
- compensation Boolean results;
- lookup sets and similarity.

Selected and final text are excluded by default.

### `readability_metrics.csv`

Grain: one nonblank text instance.

Join:

```text
readability_metrics.record_id = records.ID
```

Contains offered suggestions and final values according to attempt type and
completion policy. It contains metric values and labels but not source text.

Blank text is omitted. Absence of a row does not necessarily mean a field was
absent from the source.

## Core eligibility rules

Field-level AI assistance analysis requires:

```text
ATTEMPT_TYPE = AI
ATTEMPT_RESULT = COMPLETE
```

Completed AI rows also require:

- nonmissing `END_TIME`;
- `LLM_SUGGESTIONS`;
- `SELECTED_SUGGESTIONS`;
- `FINAL_SUBMISSION`.

Manual and incomplete attempts remain in `records.csv`.

Readability:

- completed AI attempts contribute offered suggestions and final values;
- completed manual attempts contribute final values;
- incomplete attempts contribute no readability rows;
- blank text is skipped.

## Derived analysis-audit records

| File | Grain | Purpose |
|---|---|---|
| `study_attempt_author_history.csv` | Attempt | Study ordering, author context, roles, appointments, experience |
| `study_attempt_history.csv` | Study | Completion pathway, retries, timing, handoff indicators |
| `author_history.csv` | Author | Adoption, activity, roles, query-time experience |
| `completed_ai_field_analysis.csv` | Attempt-field | Selection, match, editing metrics, edit-intensity category |
| `completed_ai_readability_pairs.csv` | Attempt-field-measure | Selected-to-final readability pairing |
| `data_quality_findings.csv` | Warning finding | Restricted traceability for nonfatal warnings |

These are published for traceability and are not mandatory disk-to-disk pipeline
hops. Aggregates are calculated from the same validated in-memory tables.

## Aggregate-to-report map

| Report question | Aggregate source | HTML section |
|---|---|---|
| How many attempts, studies, completions, and authors? | `overview/overview_summary.csv` | Captured data at a glance |
| How did attempts end by AI/manual mode? | `overview/overview_summary.csv` | Captured data at a glance |
| Were there retries or handoffs? | `overview/study_attempt_history_summary.csv`, `overview/author_handoff_summary.csv` | Study pathways and author handoffs |
| How long did completed attempts take? | `attempts/grouped_attempt_summary.csv` | Captured data at a glance |
| What quality warnings apply? | `quality/data_quality_summary.csv` | Data quality |
| What was author experience? | `authors/attempt_start_experience_summary.csv`, `authors/current_author_experience_summary.csv` | Author experience and activity |
| What was the completion author's role or PI status? | `studies/completed_study_author_context_summary.csv` | Completed-study author context |
| What participant and department categories appear? | `studies/grouped_study_summary.csv` | Participant and department mix |
| Which fields received and selected suggestions? | `fields/field_adoption_editing_summary.csv` | AI field adoption and editing |
| Which suggestion indices were selected? | `fields/suggestion_selection_summary.csv` | Suggestion choice |
| How were selected suggestions edited? | `fields/field_adoption_editing_summary.csv` | AI field adoption and editing |
| How did readability indicators change? | `readability/*.csv` | Readability indicators |
| Did reported and inferred content source agree? | `attempts/content_source_concordance_matrix.csv` | Content-source concordance |
| What feedback did users provide? | In-memory projection of `records.ID` and `records.USER_FEEDBACK_COMMENTS` | User feedback on AI assistance |

## Important derived definitions

### Attempt ordering

Within a study:

```text
START_TIME ascending, then ID ascending
```

A preceding attempt occurs before the unique completed attempt in that order.

### Author handoff

A completed study has an author handoff when a preceding attempt's
`AUTHOR_USER_NAME` differs from the completion attempt's author.

### Attempt-start experience

```text
PRIOR_CREATED_COUNT
→ prior_studies_created_before_attempt_start_count
```

This is evaluated at attempt start.

### Query-time experience

The following are query-time values, not historical attempt snapshots:

- `TOTAL_CREATED_COUNT`;
- `MEMBER_OF_OTHER_STUDIES_COUNT`;
- `LOGIN_DAYS`;
- `MIN_LOGIN_TIME`;
- `MAX_LOGIN_TIME`.

### Timing units

Source timing values are milliseconds. Exploration timing summaries convert
them to minutes.

Incomplete attempts have no total completed-attempt time distribution.

### Edit intensity

For upstream `EDITED` rows:

```text
character_edit_ratio =
    character_edit_distance
    / max(suggestion_character_count, final_character_count, 1)
```

Categories:

- `LIGHT_EDIT`: ratio at or below 0.10;
- `MODERATE_EDIT`: above 0.10 and at or below 0.30;
- `HEAVY_EDIT`: above 0.30;
- `EDITED_UNCLASSIFIED`: usable character measurements unavailable.

Direct outcomes remain distinct:

- exact;
- cosmetic;
- replaced;
- cleared;
- unassisted.

The 10% and 30% thresholds are exploratory project rules, not
literature-standard cutoffs.

### Readability direction

```text
change = final value - selected-suggestion value
```

Neutral categories are used. Lower and higher are not automatically better or
worse.

## Missing-value conventions

Published exploration CSV files use:

- UTF-8;
- LF line endings;
- `\N` for missing values;
- stable declared column order.

A zero denominator produces a missing percentage, not a fabricated zero.

## Implementation and verification map

| Concern | Implementation | Focused verification |
|---|---|---|
| Canonical source conversion | `python/packages/tabular-row-sources/src/tabular_row_sources/` | `python/packages/tabular-row-sources/tests/` |
| Normalized report selection and publication | `python/programs/study-posting-audit-report/src/study_posting_audit_report/` | `python/programs/study-posting-audit-report/tests/` |
| Study field policy | `python/packages/study-posting-ai-analysis/src/study_posting_ai_analysis/` | `python/packages/study-posting-ai-analysis/tests/` |
| TER, character, and soft-word metrics | `python/packages/text-post-edit-metrics/src/text_post_edit_metrics/metrics.py` | `python/packages/text-post-edit-metrics/tests/` |
| Metric normalization | `python/packages/text-post-edit-metrics/src/text_post_edit_metrics/normalization.py` | `test_normalization.py` |
| Readability adapter | `python/packages/text-readability-metrics/src/text_readability_metrics/metrics.py` | `python/packages/text-readability-metrics/tests/test_metrics.py` |
| Exploration histories and derived rows | `study_posting_audit_exploration/derivation/` | Exploration derivation tests |
| Exploration aggregates | `study_posting_audit_exploration/aggregation/` | Exploration aggregation tests |
| HTML charts and tables | `study_posting_audit_exploration/publication/` | `test_charts.py`, `test_html_report.py` |
| Atomic publication and inventory | `publication/csv_output.py` | `test_publication.py`, CLI tests |

Paths beginning with `study_posting_audit_exploration/` are under:

```text
python/programs/study-posting-audit-exploration/src/
```

## How to verify one report number

1. Identify the report section and chart.
2. Read its hover denominator and analytical unit.
3. Locate the aggregate CSV named in this document.
4. Locate the column definition in
   `definitions/metric_definitions.csv`.
5. Trace contributing rows through the corresponding analysis-audit file.
6. Confirm normalized source fields in `records.csv` or metric files.
7. Check implementation under
   `study_posting_audit_exploration/aggregation` or `derivation`.
8. Check focused tests for formulas, filters, and boundary cases.
9. Record the Git revision and manifest counts.

Do not paste operational rows or payload text into external tools while
performing verification.
