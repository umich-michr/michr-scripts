# study-posting-audit-exploration

Validates and explores normalized output from `study-posting-audit-report`.

The program reads an existing normalized report without modifying it. It can
validate the report contract or atomically publish derived audit records,
aggregate CSV files, a JSON manifest, and a self-contained faculty-facing HTML
report.

## Faculty and LLM documentation

Use:

- the [Study Posting Audit inquiry guide](docs/inquiry-guide.md) to find the
  authoritative document for a question;
- the [data-lineage guide](docs/data-lineage.md) to trace source columns through
  normalized, derived, aggregate, and HTML outputs;
- generated `definitions/metric_definitions.csv` for exact aggregate-column
  definitions;
- generated `analysis_manifest.json` for source counts, output counts, and
  reproducibility settings.

## Input

The program accepts a report directory containing exactly these required source
files:

- `records.csv`
- `ai_assistance_metrics.csv`
- `readability_metrics.csv`
- `report_metadata.json`

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

### Summarize published data quality

~~~~bash
uv run study-posting-audit-exploration summarize-quality \
  --exploration output/study-posting-ai-audit-analysis/exploration
~~~~

This command reads only `quality/data_quality_summary.csv` and
`analysis_manifest.json`. It prints a deterministic, identifier-free summary of
fatal validation guarantees, warning checks, affected counts, denominators,
percentages, and analysis consequences.

Warnings do not fail the command by default. For warning-sensitive automation:

~~~~bash
uv run study-posting-audit-exploration summarize-quality \
  --exploration output/study-posting-ai-audit-analysis/exploration \
  --fail-on-warning
~~~~

`--fail-on-warning` prints the complete summary and then returns status 3 when
at least one warning check has affected attempts. Invalid or inconsistent
exploration output returns status 2.


### Normalized report metadata

`report_metadata.json` is required alongside the three normalized CSV files.
Exploration validates its exact version 1 shape:

- `report_generated_at_utc` is a timezone-aware UTC report-generation instant;
- `source_snapshot_as_of_utc` is nullable;
- `source_snapshot_provenance` is `REPORT_RUN_CUTOFF`, `UNAVAILABLE`, or
  `SOURCE_PROVIDED`;
- `UNAVAILABLE` requires a null snapshot;
- `SOURCE_PROVIDED` requires a timezone-aware snapshot no later than report
  generation;
- `REPORT_RUN_CUTOFF` requires a nonnull snapshot identical to the report
  generation timestamp after UTC normalization.

Report generation time is not automatically a source-query or observation-window
endpoint. Exploration does not infer a source snapshot from attempt, creation,
login, filesystem, or downstream publication timestamps. Follow-up-adjusted
no-completion-observed comparisons remain deferred unless provenance is
`SOURCE_PROVIDED` and a separate threshold policy is defined.

For no-completion-observed studies, the internal retry context now keeps three distinct durations when validated metadata provides `REPORT_RUN_CUTOFF`: first attempt to latest observed attempt, latest attempt to report-run cutoff, and first attempt to report-run cutoff. Legacy `UNAVAILABLE` metadata leaves the cutoff-based durations missing. By explicit project policy, no minimum follow-up threshold, follow-up-eligibility classification, or adjusted unresolved rate is planned.

The two published retry summaries include the count of unresolved studies with a validated report-run cutoff and median minutes from the latest attempt to cutoff and from the first attempt to cutoff. Completed rows keep these cutoff medians missing. The publication inventory remains exactly 36 files.

The faculty retry table labels completed timing, unresolved observed activity span, follow-up after the latest attempt, and total observation window separately. Cutoff medians display their contributing-study count. These are descriptive durations, not threshold-qualified outcomes.

Normalized `START_TIME` and `END_TIME` values are naive timestamps in `America/Detroit`. Exploration localizes them to that zone and converts them to UTC only for report-run cutoff calculations. Ambiguous or nonexistent daylight-saving transition times fail validation.

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

A successful `analyze` run atomically publishes exactly 36 files:
`report.html`, one JSON manifest, and 31 CSV files.

Output inventory:

    exploration/
    |-- report.html
    |-- analysis_manifest.json
    |-- definitions/
    |   `-- metric_definitions.csv
    |-- quality/
    |   `-- data_quality_summary.csv
    |-- analysis-audit-records/
    |   |-- data_quality_findings.csv
    |   |-- study_attempt_author_history.csv
    |   |-- study_attempt_history.csv
    |   |-- author_history.csv
    |   |-- completed_ai_field_analysis.csv
    |   `-- completed_ai_readability_pairs.csv
    |-- overview/
    |   |-- overview_summary.csv
    |   |-- study_attempt_history_summary.csv
    |   |-- author_handoff_summary.csv
    |   |-- study_retry_pathway_summary.csv
    |   |-- retry_characteristics_summary.csv
    |   `-- repeated_attempt_source_consistency_summary.csv
    |-- attempts/
    |   |-- grouped_attempt_summary.csv
    |   |-- source_context_distribution_summary.csv
    |   |-- source_size_latency_summary.csv
    |   |-- content_source_concordance_summary.csv
    |   `-- content_source_concordance_matrix.csv
    |-- studies/
    |   |-- completed_study_author_context_summary.csv
    |   `-- grouped_study_summary.csv
    |-- authors/
    |   |-- grouped_author_summary.csv
    |   |-- attempt_start_experience_summary.csv
    |   `-- current_author_experience_summary.csv
    |-- fields/
    |   |-- field_adoption_editing_summary.csv
    |   |-- nontext_field_adoption_summary.csv
    |   |-- suggestion_selection_summary.csv
    |   `-- compensation_analysis_summary.csv
    |-- readability/
    |   |-- selected_vs_unselected_readability_summary.csv
    |   |-- field_readability_change_summary.csv
    |   |-- field_readability_target_summary.csv
    |   |-- field_edit_readability_cross_summary.csv
    |   `-- final_text_metric_summary.csv
    `-- research/
        `-- candidate_research_questions.csv

### Retry pathways and observed workflow patterns

The internal retry derivation has one row per study. Attempts are ordered by
`START_TIME`, followed by audit ID. Completed-study pathways stop at the unique
completed attempt; attempts after completion remain visible through the
existing quality warning but do not redefine the completion pathway. Studies
without a completed attempt use every captured attempt.

The 13 stable pathway categories are exhaustive and mutually exclusive:

- single-attempt AI or manual completion;
- repeated AI-only or manual-only completion;
- one-direction AI-to-manual or manual-to-AI completion;
- mixed or alternating completion in AI or manual mode;
- single-attempt AI or manual no completion observed;
- repeated AI-only or manual-only no completion observed;
- mixed-mode no completion observed.

A one-direction pathway contains exactly one adjacent mode transition. For
example, AI then AI then manual completion belongs to the AI-to-manual
category. Sequences with at least two mode transitions are mixed or
alternating.

`overview/study_retry_pathway_summary.csv` always has one row for each of the
13 categories, including zero-count categories. Its percentage denominator is
all studies with captured attempts.

`overview/retry_characteristics_summary.csv` has exactly three rows: completed
with AI, completed manually, and no completion observed. General percentages
use all studies in the row; source-signature change percentages use
source-comparison-eligible studies; feedback percentages use AI-exposed
studies. A missing percentage means its denominator is zero.

A returned-result AI attempt excludes both recorded AI-error result categories;
eligible user-dropped AI attempts remain included. Source-signature equality is
an unchanged-source proxy based on source size and reported source, not proof
of identical text.

Faculty outputs contain aggregates only. Feedback contributes only count or
Boolean presence to retry analysis; feedback text does not enter retry tables
or charts.

Completed timing means first recorded attempt start to completed-attempt end.
Timing for no-completion-observed studies means first recorded attempt start to
latest observed attempt start. It is not follow-up time.

“No completion observed” means no `COMPLETE` attempt appears in the captured
report; completion may occur outside the observation window. These measures
must not be described as drop-off, abandonment, final outcomes, motivation,
satisfaction, or causal effects.

### Data quality

`quality/data_quality_summary.csv` is an identifier-free checklist of source
and derived quality conditions. It reports:

- the stable quality-check name and severity;
- affected attempt, distinct-study, and distinct-author counts;
- the eligible attempt denominator and affected percentage;
- a plain-language check definition;
- the consequence for analysis.

Checks marked `FATAL` are enforced before publication. Therefore, their
published affected counts are zero after a successful run; detection would
instead stop validation and prevent publication. These rows document the
guarantees that a successful analysis has already passed.

Checks marked `WARNING` may be nonzero in a successful run. Current warning
checks cover attempts after a study's unique completion, `CREATED_BY_ID`
variation within a study, and malformed appointment entries. Warning rows make
these retained conditions visible without exposing audit IDs, study numbers, or
usernames.

`affected_attempt_percentage` is the affected-attempt count divided by the
check's explicit eligible-attempt population. A missing percentage means the
eligible denominator is zero.

The manifest's `warning_count` is the sum of affected-attempt counts across
warning checks. It is a warning-occurrence total, not a distinct-attempt count;
one attempt affected by multiple warning checks can contribute more than once.

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

`report.html` is a self-contained faculty/development report.

Plotly charts consume only aggregate analysis tables. The final user-feedback
table is the narrow authorized exception and projects only `records.csv.ID` and
`records.csv.USER_FEEDBACK_COMMENTS`.

The report begins with:

- a table of contents with anchor links;
- a concise faculty summary;
- a captured-data overview;
- data-quality context.

Detailed sections use native HTML `details` and `summary` controls for
progressive disclosure. Executive, quality, pathway, and feedback sections are
open by default. Technical sections are collapsed by default. Print CSS exposes
all section content.

It currently includes:

- executive key performance indicator cards;
- a four-part completed/incomplete by AI/manual attempt-outcome chart;
- three completion-pathway callouts;
- study completion pathways and author-handoff categories;
- attempt-start experience at author-attempt grain;
- query-time experience and activity at unique-author grain;
- completed studies by final authoring mode and the completion author's
  study-specific effective role;
- completed studies by final authoring mode and the completion author's
  study-specific principal-investigator status;
- author and principal-investigator appointment school, department, and
  title context;
- completed-study participant-type and department mix;
- AI suggestion offers and selections by field;
- selected-suggestion retention and edit outcomes by field;
- suggestion selection by field, kind, and zero-based position;
- selected-to-final Flesch-Kincaid direction by field;
- observed final Flesch-Kincaid grade bands by field and mode;
- selected versus mean-unselected Flesch-Kincaid differences;
- edit-intensity and consensus grade-level direction relationships using
  aggregate attempt-and-field percentages;
- completed-attempt study-information-page and total-attempt timing by
  authoring mode, including medians, interquartile ranges, 90th percentiles,
  and missing counts;
- reported-versus-inferred content-source concordance;
- self-reported AI-usefulness feedback ordered by audit record ID;
- interpretation cautions beside relevant analyses.

The completed-study author-context charts use one unique completed study
as their analytical unit. Each completed study contributes exactly once through
its unique completed attempt. Final AI or manual mode, effective
completion-author role, and principal-investigator status all come from that
attempt.

Role and principal-investigator status are study-specific rather than permanent
classifications of a person. The same person may complete multiple studies,
have different roles across studies, and be a principal investigator for one
study but not another. Chart values count completed studies. Distinct
completion-author counts appear only as identifier-free hover context; no
completion-author identity is displayed. The report intentionally does not
reintroduce the removed author-level role or principal-investigator charts.

Appointment school, department, and title charts remain separate context.
Appointment values are parsed from comma-separated `Title:Department:School`
entries. Their groups may overlap because an author or principal investigator
can have more than one appointment. Each chart counts distinct attempt authors
represented in a group, and chart values are not intended to sum to 100
percent.

The report does not include cumulative lines, monthly trends, time-series
outputs, or dropdown filtering for completed-study author context.

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

### Suggestion index and prompt-assigned rank

For title, purpose, and about, the author-assistance prompt instructs the model
to rank suggestions from best to worst using accuracy, clarity, appeal without
hype, and conciseness. Zero-based index 0 is therefore the model's intended
highest-ranked suggestion for those fields.

This is prompt intent, not proof that the ranking is correct.

Selection-by-index analysis can describe whether authors selected earlier
prompt-ranked suggestions more often. It cannot independently establish
objective suggestion quality because:

- model rank is confounded with display position;
- later indices are not offered on every attempt;
- author selection reflects preference or practical fit;
- selection alone does not show retention or editing.

Use `selected_suggestion_count_at_index / suggestion_count_at_index`, not raw
selected counts.

Compensation must be analyzed by suggestion kind and within-kind index. The
prompt places specific suggestions before generic suggestions, so the six
display positions are not one unambiguous best-to-worst scale.

A stronger ranking study would preserve hidden model rank while randomizing
display order and obtaining blinded rubric ratings.

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

The selected-versus-unselected comparison has a narrower completed-AI
population than final-text charts. A field appears only when an attempt has
exactly one selected suggestion, at least one unselected suggestion, and usable
readability values for both. For each eligible attempt, the selected suggestion
is compared with the mean of its unselected suggestions. An omitted field means
no observations met every comparison requirement; it does not mean the field
was absent from the audit, lacked final text, or was omitted from other
readability analyses. Comparable-attempt counts are included in hover text.

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
edit-intensity category. Bar labels include the group sample size, and hover
text gives the edit rule, numerator, denominator, percentage, and median
Flesch-Kincaid final-minus-selected change.

The project-specific character-edit bands use 10% and 30% thresholds:
light edits are at or below 10%, moderate edits are above 10% and at or below
30%, and heavy edits are above 30%. The technical scheme ID is
`EXPLORATORY_CHARACTER_RATIO_10_30`. These exploratory categories describe
edit size and are not writing-quality standards.

The denominator is every completed AI attempt-and-field row in the field/edit
category, while only rows with selected-and-final readability pairs contribute
to a direction. An unfilled portion of a bar represents rows without a usable
pair. `EDITED_UNCLASSIFIED` remains distinct from `REPLACED`. Mixed formula
direction is not the same as no material change. Readability direction does not
establish writing quality, comprehension, accessibility, usefulness, or causal
benefit.

The report embeds its Plotly JavaScript and does not require an external script
service. It does not contain usernames, audit IDs, study numbers, source
payloads, selected text, or final text.

### Analysis audit records

These identifier-bearing files expose the derived rows used by aggregate
analysis:

- `data_quality_findings.csv` maps nonfatal warning findings to the exact audit
  record, study, and attempt author for authorized internal investigation. It
  records finding source, appointment position where applicable, structural
  detail code, and analysis consequence. It excludes raw appointment values,
  source text, and payloads. Use `audit_record_id` to locate the matching
  `records.csv` row or perform a targeted approved bind-variable lookup.

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

### Source-context outputs

- `source_context_distribution_summary.csv` separates all AI generations that
  returned a result from completed AI-assisted attempts. It reports
  measure-specific input-method and content-source counts plus source-size and
  latency distributions. “Returned a result” excludes both recorded AI-error
  categories, includes eligible user-dropped attempts, and does not mean that
  a study posting was created.
- `source_size_latency_summary.csv` reports source-size and latency summaries in
  deterministic quartile-ranked bands. Band edges are derived from all AI
  generations that returned a result and reused for completed AI-assisted
  attempts so the populations remain comparable.
- `repeated_attempt_source_consistency_summary.csv` keeps completed-study,
  all-transition, completed-path-transition, first-to-completion, and
  preceding-to-completion grains explicit. It reports dynamic contributing
  study counts, transition counts, comparable denominators, unavailable
  counts, and latency changes.

For consecutive-generation comparisons, changed and unchanged percentages use
transitions with usable values on both sides. Unavailable counts use all
completed-path transitions. One study may contribute multiple transitions.
Latency change is later minus earlier: positive means the later generation took
longer, negative means less time, and zero means no captured change.

Equal source size plus equal reported source is an unchanged-source proxy, not
proof of identical source text. Source and latency associations are descriptive
and do not establish causality.

### Study outputs

- `completed_study_author_context_summary.csv` reports completed-study counts
  by final AI or manual authoring mode and either the effective
  completion-author role or study-specific principal-investigator status. Each
  completed study contributes once through its unique completed attempt.
  Counts and percentages include explicit within-mode and all-completed-study
  denominators. The file includes an aggregate distinct-completion-author count
  but no usernames, study numbers, or audit IDs.
- `grouped_study_summary.csv` summarizes distinct-study populations, completion
  history, timing, participant type, department, appointments, source type, and
  content source.

The same completion author may contribute to multiple rows across studies
because role and principal-investigator status are evaluated separately for
each completed study. Appointment group counts are non-mutually-exclusive. A
study or author may be represented in more than one appointment group.

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
- published analysis row counts, including the data-quality and
  completed-study author-context summaries;
- output file count;
- configured edit-intensity scheme;
- readability tolerance;
- warning-occurrence count, calculated as the sum of affected-attempt
  counts across warning checks.

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

HTML charts are aggregate-only. The authorized feedback table is the narrow
exception and displays audit record ID plus `USER_FEEDBACK_COMMENTS`. It does not
display usernames, study numbers, analysis payloads, selected text, or final
text.

The report includes a table of contents, concise faculty summary, and native
collapsible sections. Print styling exposes collapsed content.

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
