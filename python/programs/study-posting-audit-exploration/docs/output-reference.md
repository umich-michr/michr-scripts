# Study Posting Audit exploration outputs

A successful analysis atomically publishes exactly 36 files:

```text
exploration/
├── report.html
├── analysis_manifest.json
├── definitions/
│   └── metric_definitions.csv
├── quality/
│   └── data_quality_summary.csv
├── analysis-audit-records/
│   ├── data_quality_findings.csv
│   ├── study_attempt_author_history.csv
│   ├── study_attempt_history.csv
│   ├── author_history.csv
│   ├── completed_ai_field_analysis.csv
│   └── completed_ai_readability_pairs.csv
├── overview/
│   ├── overview_summary.csv
│   ├── study_attempt_history_summary.csv
│   ├── author_handoff_summary.csv
│   ├── study_retry_pathway_summary.csv
│   ├── retry_characteristics_summary.csv
│   └── repeated_attempt_source_consistency_summary.csv
├── attempts/
│   ├── grouped_attempt_summary.csv
│   ├── source_context_distribution_summary.csv
│   ├── source_size_latency_summary.csv
│   ├── content_source_concordance_summary.csv
│   └── content_source_concordance_matrix.csv
├── studies/
│   ├── completed_study_author_context_summary.csv
│   └── grouped_study_summary.csv
├── authors/
│   ├── grouped_author_summary.csv
│   ├── attempt_start_experience_summary.csv
│   └── current_author_experience_summary.csv
├── fields/
│   ├── field_adoption_editing_summary.csv
│   ├── nontext_field_adoption_summary.csv
│   ├── suggestion_selection_summary.csv
│   └── compensation_analysis_summary.csv
├── readability/
│   ├── selected_vs_unselected_readability_summary.csv
│   ├── field_readability_change_summary.csv
│   ├── field_readability_target_summary.csv
│   ├── field_edit_readability_cross_summary.csv
│   └── final_text_metric_summary.csv
└── research/
    └── candidate_research_questions.csv
```

## Faculty-facing outputs

### `report.html`

Self-contained HTML with embedded Plotly.

Charts consume aggregate tables only. The final feedback table is the narrow
authorized exception and displays audit record ID with
`USER_FEEDBACK_COMMENTS`.

The report uses semantic navigation, native disclosure controls, keyboard
accessibility, and print expansion.

### Aggregate CSV files

Directories `overview/`, `attempts/`, `studies/`, `authors/`, `fields/`,
`readability/`, and `quality/` contain identifier-free aggregates.

Every percentage has an explicit denominator. Missing percentages represent
empty denominators.

### `definitions/metric_definitions.csv`

Identifier-free data dictionary covering every faculty-facing aggregate CSV
column.

It records:

- label and analytical unit;
- calculation, numerator, and denominator definitions;
- measurement unit;
- value-selection and missing-value rules;
- source output and column;
- interpretation notes.

### `analysis_manifest.json`

Records:

- program version;
- generation time;
- normalized source path and filenames;
- source and output row counts;
- output file count;
- configured analytical settings;
- warning-occurrence count.

It contains no source payload text.

### `research/candidate_research_questions.csv`

Deterministic catalog of descriptive questions supported by current aggregate
outputs. It is not a metric table and does not imply causal or inferential
readiness.

## Restricted traceability outputs

Files under `analysis-audit-records/` contain identifiers needed for authorized
internal investigation.

| File | Grain | Purpose |
|---|---|---|
| `data_quality_findings.csv` | Warning finding | Trace nonfatal warnings to affected records |
| `study_attempt_author_history.csv` | Attempt | Ordered study and author context |
| `study_attempt_history.csv` | Study | Pathway, completion, timing, and handoff derivation |
| `author_history.csv` | Author | Adoption, activity, role, and query-time experience |
| `completed_ai_field_analysis.csv` | Attempt-field | Selection, outcome, edit measures, and intensity |
| `completed_ai_readability_pairs.csv` | Attempt-field-measure | Selected-to-final readability pairs |

These files are not faculty-facing. Handle them as sensitive analysis data.

## Aggregate directories

### `overview/`

Top-level attempt, study, completion, author, pathway, retry, handoff, timing,
and repeated-source summaries.

### `attempts/`

Attempt counts, workflow timing, source context, source-size/latency bands, and
reported-versus-inferred source concordance.

### `studies/`

Completed-study author role/PI context and grouped study characteristics.

Each completed study contributes once through its unique completed attempt for
completed-study author context.

### `authors/`

Distinct-author context plus attempt-start and query-time experience
distributions.

`current_author_experience_summary.csv` includes the identifier-free embedded
percentile-bin payload used by the two 100% stacked study-activity charts.

### `fields/`

Suggestion offers, selections, selected outcomes, lookup/Boolean outcomes,
suggestion positions, compensation composition, and edit distributions.

### `readability/`

Selected-to-final change, final grade bands, selected-versus-unselected
comparisons, edit/readability cross summaries, and observed nonblank final-text
metrics.

## Quality output

`quality/data_quality_summary.csv` contains stable fatal and warning checks.

Fatal conditions stop publication, so their published affected counts are zero
after a successful run.

Warnings may be nonzero. Warning counts are occurrence totals and may count one
attempt in more than one warning category.

## Publication guarantees

- Output inventory is exact and tested.
- CSV schemas and column order are stable and tested.
- Publication uses staging and atomic rename.
- Existing destinations are not overwritten.
- Generated output must not be committed.
