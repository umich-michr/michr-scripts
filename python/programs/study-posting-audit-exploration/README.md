# study-posting-audit-exploration

Validates and explores normalized output from `study-posting-audit-report`.

The program reads an existing normalized report without modifying it. It can
validate the report contract or atomically publish derived audit records,
aggregate CSV files, a JSON manifest, and a self-contained faculty-facing HTML
report.

## Input

The program accepts a report directory containing exactly these required source
files:

- `records.csv`
- `ai_assistance_metrics.csv`
- `readability_metrics.csv`

The input report remains read-only.

## Commands

### Validate a normalized report

~~~~bash
uv run study-posting-audit-exploration validate \
  --input-report output/study-posting-ai-audit-analysis/report
~~~~

Successful validation prints counts only. It does not print usernames, study
numbers, payloads, or free text.

### Publish the current exploration outputs

The output directory must not already exist.

~~~~bash
uv run study-posting-audit-exploration analyze \
  --input-report output/study-posting-ai-audit-analysis/report \
  --output output/study-posting-ai-audit-analysis/exploration
~~~~

Publication uses a staging directory and atomically renames the completed
directory into place. If publication fails, the staging directory is removed
and the destination is not published.

## Validation

The current validation contract checks:

- required files and exact headers;
- canonical scalar and datetime values;
- unique audit IDs;
- metric-to-attempt joins;
- one or zero completed attempts per study;
- required completed-attempt values;
- completed-attempt author and creator consistency;
- supported AI-analysis types and match outcomes;
- unique AI-assistance audit-field identities;
- completed-AI ownership of AI-assistance rows;
- AI selection and match relationships;
- finite numeric metrics;
- readability text roles and selected markers;
- unique readability text-instance identities;
- completed-attempt ownership of readability rows;
- agreement between readability and record authoring modes;
- no more than one selected suggestion and final readability row per audit
  field;
- agreement between existing selected readability rows and AI-assistance picks.

`readability_metrics.csv` intentionally omits blank text. A completed assisted
field is therefore not required to have selected and final readability rows.
Readability pairs are derived only where both components exist. Missing pair
components reduce the paired sample rather than invalidating the report.

Validation errors must not expose usernames, study numbers, source payloads, or
free text.

## Analytical identities

- `records.csv.ID` is the audit attempt ID.
- Metric-file `record_id` values join to the audit attempt ID.
- Derived audit files rename the attempt identifier to `audit_record_id`.
- `STUDY_NUM` groups attempts for one study.
- `AUTHOR_USER_NAME` is the attempt-author identity and is used exactly as
  stored.
- `CREATED_BY_ID` is the created study's creator ID, not the author identity for
  preceding attempts.
- A study can have no more than one `COMPLETE` attempt.
- Attempts within a study are ordered by `START_TIME`, followed by audit ID as
  the deterministic tie-breaker.

`PRIOR_CREATED_COUNT` is interpreted as the number of studies created by the
attempt author before `START_TIME`. It is available for complete and incomplete
attempts and is analyzed as
`prior_studies_created_before_attempt_start_count`.

Query-time experience values are kept distinct from attempt-start experience.
They include total studies created, other-study memberships, distinct login
days, and login-history span as of the report query.

## Current output

A successful `analyze` run publishes 28 files: `report.html`, one JSON
manifest, and 26 CSV files.

~~~~text
exploration/
├── report.html
├── analysis_manifest.json
├── definitions/
│   └── metric_definitions.csv
├── analysis-audit-records/
│   ├── study_attempt_author_history.csv
│   ├── study_attempt_history.csv
│   ├── author_history.csv
│   ├── completed_ai_field_analysis.csv
│   └── completed_ai_readability_pairs.csv
├── overview/
│   ├── overview_summary.csv
│   ├── study_attempt_history_summary.csv
│   └── author_handoff_summary.csv
├── attempts/
│   ├── grouped_attempt_summary.csv
│   ├── content_source_concordance_summary.csv
│   └── content_source_concordance_matrix.csv
├── studies/
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
~~~~

### Metric definitions

`definitions/metric_definitions.csv` is an identifier-free data dictionary
covering every column in the current faculty-facing aggregate CSV files. It
records:

- a plain-language label and analytical unit;
- calculation, numerator, and denominator definitions;
- measurement units and value-selection rules;
- missing-value treatment;
- source output filenames and column names;
- interpretation cautions.

The file is generated deterministically from the aggregate output schemas.
It does not include usernames, audit IDs, study numbers, source payloads,
selected text, or final text.

### HTML report

`report.html` is a self-contained faculty-facing report generated only from
aggregate analysis tables. It currently includes:

- executive key performance indicator cards;
- study completion pathways and author-handoff categories;
- attempt-start experience at author-attempt grain;
- query-time experience and activity at unique-author grain;
- effective author roles and author-level principal-investigator context;
- author and principal-investigator appointment-school context;
- completed-study participant-type and department mix;
- AI suggestion offers and selections by field;
- selected-suggestion retention and edit outcomes by field;
- suggestion selection by field, kind, and zero-based position;
- selected-to-final Flesch-Kincaid direction by field;
- observed final Flesch-Kincaid grade bands by field and mode;
- selected versus mean-unselected Flesch-Kincaid differences;
- edit-intensity and consensus grade-level direction relationships using
  aggregate attempt-and-field percentages;
- attempt outcomes by authoring mode;
- study-information-page and total-attempt timing distributions by authoring
  mode, including medians, interquartile ranges, 90th percentiles, and missing
  counts;
- reported-versus-inferred content-source concordance;
- privacy and interpretation cautions.

Appointment-school chart groups may overlap because an author or principal
investigator can have more than one appointment. Those chart values are not
intended to sum to 100 percent.

The author-experience section describes attempt authors, not PI-specific
experience unless the PI was also the attempt author. The attempt-start chart
counts author-attempt observations and can include one author more than once.
Query-time charts count each distinct author at most once per metric and
adoption group. Counts can differ across those charts because their analytical
grains differ and because missing metric values are excluded.

The field-adoption section uses completed AI attempt-and-field aggregates.
Offer and selection counts can have different field-specific populations.
Selection percentages use attempts with at least one offered suggestion as
their denominator. Selected-suggestion outcomes retain
`EDITED_UNCLASSIFIED` separately from `REPLACED`; they are descriptive and
do not establish writing quality or causal benefit.

The suggestion-choice section distinguishes two denominators.
Attempt-level selection is the percentage of completed AI attempts with at
least one offered suggestion that selected a suggestion. Suggestion-level
selection is the percentage of all offered suggestion instances that were
selected. Position charts use zero-based indices, so index 0 is the first
offered suggestion. These descriptive measures do not establish suggestion
quality or causal benefit.

The readability section uses aggregate Flesch-Kincaid summaries. Change
direction is final minus selected. Negative values indicate a lower final
formula value and positive values indicate a higher final formula value;
neither direction is automatically better. Final grade bands include only
observed nonblank final texts. Titles carry a short-text reliability
caution. Readability formulas do not establish comprehension, accuracy,
accessibility, usefulness, cultural appropriateness, or ethical adequacy.

The workflow-timing section separates study-information-page time from total
attempt time. It shows medians with 25th-to-75th-percentile error bars and
reports 90th percentiles and missing counts in hover text. The HTML does not
chart first-attempt-to-completion minimum-to-maximum ranges because long
calendar-time outliers compress typical values and can be misread as active
work duration. The underlying study-level timing aggregates remain available
in `overview/study_attempt_history_summary.csv`. Attempt timings do not
establish author effort, efficiency, quality, or a causal effect of authoring
mode.

The edit-intensity/readability chart uses
`field_edit_readability_cross_summary.csv` only. It shows consensus
grade-level direction percentages within each field and operational
edit-intensity category. The denominator is every completed AI
attempt-and-field row in that edit-intensity category, while only rows with
selected-and-final readability pairs contribute to a direction.
`EDITED_UNCLASSIFIED` remains distinct from `REPLACED`. The exploratory
edit-intensity scheme and readability directions do not establish writing
quality, comprehension, accessibility, usefulness, or causal benefit.

The report embeds its Plotly JavaScript and does not require an external script
service. It does not contain usernames, audit IDs, study numbers, source
payloads, selected text, or final text.

### Analysis audit records

These identifier-bearing files expose the derived rows used by aggregate
analysis:

- `study_attempt_author_history.csv` has one row per attempt with study,
  authorship, role, appointment, and available experience context.
- `study_attempt_history.csv` has one row per study with its attempt pathway,
  completion state, timing, and author-handoff indicators.
- `author_history.csv` has one row per exact `AUTHOR_USER_NAME` with observed
  adoption, activity, role, and query-time experience measures.
- `completed_ai_field_analysis.csv` has one row per completed AI attempt and
  analyzed field, including structural selection information, continuous edit
  measures, and the operational edit-intensity category.
- `completed_ai_readability_pairs.csv` has one row per completed AI
  selected-suggestion/final field pair and readability measure.

The completed field and readability-pair outputs do not contain selected or
final source text.

Analysis audit files contain identifiers needed for internal traceability.
Handle them as sensitive analysis data and do not publish them as
faculty-facing summaries.

### Overview outputs

- `overview_summary.csv` contains top-level attempt, study, author, PI, and
  completion-pathway counts with explicit denominators.
- `study_attempt_history_summary.csv` summarizes repeated attempts and time to
  completion.
- `author_handoff_summary.csv` distinguishes same-author retries from handoffs
  to other authors.

### Attempt outputs

- `grouped_attempt_summary.csv` summarizes attempt counts and timing by
  completion group, exact result, authoring mode, source type, and content
  source.
- `content_source_concordance_summary.csv` summarizes agreement between reported
  and inferred content-source values.
- `content_source_concordance_matrix.csv` contains reported-versus-inferred
  content-source counts and percentages.

### Study output

`grouped_study_summary.csv` summarizes distinct-study populations, completion
history, timing, participant type, department, appointments, source type, and
content source.

Appointment group counts are non-mutually-exclusive. A study or author may be
represented in more than one appointment group.

### Author outputs

- `grouped_author_summary.csv` reports distinct-author counts by completion,
  authoring mode, effective role, and appointment group.
- `attempt_start_experience_summary.csv` reports distributions of prior studies
  created before each attempt's `START_TIME`, grouped by author adoption,
  completion, and authoring mode.
- `current_author_experience_summary.csv` reports author-grain distributions for
  experience and activity values measured as of the report query.

Aggregate author files do not contain usernames or audit IDs. Identifier-bearing
author details remain in `analysis-audit-records/author_history.csv`.

### Field outputs

- `field_adoption_editing_summary.csv` reports text and compensation-field
  suggestion offers, selections, retention, edit-intensity categories, and
  continuous edit distributions. It includes explicit count and percentage
  columns for selected edits that could not be classified because usable
  character metrics were unavailable.
- `nontext_field_adoption_summary.csv` reports lookup-set and compensation
  Boolean outcomes separately from text-edit metrics.
- `suggestion_selection_summary.csv` reports offers and selections by field,
  suggestion kind, and zero-based suggestion index.
- `compensation_analysis_summary.csv` separates generic and specific
  compensation suggestions and includes selection, editing, and paired
  readability outcomes. It includes an explicit count for selected
  unclassified edits.

The operational edit-intensity scheme is
`EXPLORATORY_CHARACTER_RATIO_10_30`:

- `EXACT`;
- `COSMETIC`;
- `LIGHT_EDIT`, with a character edit ratio at or below 0.10;
- `MODERATE_EDIT`, above 0.10 and at or below 0.30;
- `HEAVY_EDIT`, above 0.30;
- `EDITED_UNCLASSIFIED`, when the upstream result is `EDITED` but usable
  character lengths or a character edit ratio are unavailable;
- `REPLACED`;
- `CLEARED`;
- `UNASSISTED`.

`EDITED_UNCLASSIFIED` is reported explicitly. It is not treated as `REPLACED`
and is excluded from character-ratio and Translation Edit Rate (TER)
distributions because no usable ratio is available. No edit ratio is inferred
or fabricated.

These are exploratory operational cutoffs, not literature-standard categories.

### Readability outputs

- `selected_vs_unselected_readability_summary.csv` compares each selected
  suggestion with the mean of unselected suggestions from the same attempt and
  field.
- `field_readability_change_summary.csv` summarizes selected-to-final changes
  by field and readability measure.
- `field_readability_target_summary.csv` reports observed final grade-level
  bands by AI or manual authoring mode.
- `field_edit_readability_cross_summary.csv` crosses edit intensity with
  consensus grade-level direction.
- `final_text_metric_summary.csv` summarizes observed nonblank final
  readability, reading-time, and length metrics.

The readability-pair direction is final value minus selected-suggestion value.
Machine-readable categories use neutral wording:

- `VALUE_DECREASED`;
- `NO_MATERIAL_CHANGE`;
- `VALUE_INCREASED`.

Consensus across Flesch-Kincaid grade, Automated Readability Index,
Coleman-Liau Index, and Gunning Fog uses:

- `CONSENSUS_GRADE_LEVEL_DECREASE`;
- `NO_MATERIAL_CHANGE`;
- `CONSENSUS_GRADE_LEVEL_INCREASE`;
- `MIXED_FORMULA_DIRECTION`.

Dale-Chall is summarized separately because it uses a different scale. Titles
carry a short-text reliability caution.

Readability formulas are indicators only. They do not establish comprehension,
accuracy, cultural appropriateness, layout quality, accessibility, usefulness,
or ethical adequacy.

### Missing and blank final-text limitation

`readability_metrics.csv` contains final rows only for observed nonblank text.
The normalized report does not currently distinguish a blank field from a field
that was not applicable or not covered by extraction policy.

Therefore:

- `final_text_metric_summary.csv` summarizes observed nonblank final values;
- `final_text_attempt_count_missing_or_blank` is published as missing (`\N`);
- the exploration program does not inspect `FINAL_SUBMISSION` to infer field
  presence;
- missing or blank final-text rates require a future non-sensitive field-presence
  indicator in the normalized report contract.

### Candidate research questions

`research/candidate_research_questions.csv` is a deterministic, identifier-free
catalog of descriptive questions supported by the published aggregate outputs.
It records:

- a stable research-question ID and plain-language question;
- the primary analytical unit;
- the comparison or grouping;
- the outcome or measure;
- supporting published output files;
- interpretation cautions;
- a priority tier and readiness status.

The catalog is generated from code rather than inferred from source records.
It is not an aggregate metric table and is therefore not included in
`definitions/metric_definitions.csv`. Questions marked `DESCRIPTIVE_READY`
identify analyses supported by current outputs; they do not imply causal,
inferential, or individual-level conclusions.

### Manifest

`analysis_manifest.json` records:

- the analysis program version;
- generation time;
- source report path and filenames;
- source row counts;
- the metric-definition row count;
- the candidate-research-question row count;
- published analysis row counts;
- output file count;
- configured edit-intensity scheme;
- readability tolerance;
- warning count.

The manifest contains no source payload text.

## Missing values and stable output

CSV files use:

- UTF-8 encoding;
- LF line endings;
- stable declared column order;
- `\N` for missing values.

Published aggregate percentages use explicit denominators. Empty denominators
produce missing percentages rather than misleading zero percentages.

## Privacy and interpretation

The aggregate outputs and HTML report are intended for exploratory analysis.
Counts, percentages, timing distributions, experience measures, post-edit
measures, and readability indicators must not be interpreted as causal findings
or evaluations of an individual author.

Do not place real audit records, source payload text, credentials, connection
values, or operational SQL in tests, documentation, commits, or issue reports.
Use synthetic data for development.

## Boundary

This program owns exploratory derivation, aggregation, validation, and
publication.

It does not recreate:

- source extraction;
- study-field analysis;
- post-edit metric calculation;
- readability metric calculation;
- database or Oracle connectivity.

The normalized report remains the source contract.

## Development

Run focused checks from the repository root:

~~~~bash
make format
make lint
make typecheck
make test PACKAGE=study-posting-audit-exploration
make coverage PACKAGE=study-posting-audit-exploration
git diff --check
~~~~

Before committing a completed increment, run the full repository gates:

~~~~bash
make docs-check
make check
make hooks-run
~~~~

## License

MIT
