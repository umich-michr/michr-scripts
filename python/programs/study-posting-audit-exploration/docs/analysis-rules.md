# Study Posting Audit exploration rules

This document summarizes the durable analytical and presentation rules owned by
`study-posting-audit-exploration`.

For source-column lineage, see [`data-lineage.md`](data-lineage.md). For
study-field suggestion policy, see the
[study analysis specification](../../../packages/study-posting-ai-analysis/docs/analysis-specification.md).

## Analytical units

Keep these units distinct:

| Unit | Meaning |
|---|---|
| Attempt | One normalized `records.csv` row |
| Study | Attempts sharing `STUDY_NUM` |
| Attempt author | Exact author recorded on an attempt |
| Completed study | Study represented by its unique completed attempt |
| Attempt-field | One completed AI attempt and analyzed field |
| Suggestion instance | One attempt, field, kind, and zero-based index |
| Readability pair | One selected suggestion and final value for the same attempt and field |

Do not combine counts across units without an explicit join and denominator.

## Completion and AI exposure

Source attempt results use four precedence-ordered values:

1. `AI_ERROR`: linked generation stack trace;
2. `AI_ERROR_WITHOUT_STACK_TRACE`: zero latency without a stack trace, retained
   as a defensive anomaly;
3. `USER_DROPPED`: no completed workflow submission;
4. `COMPLETE`: completed Add Study workflow and posting creation.

A valid provider response with empty field suggestions is not a generation
error. Error evidence has precedence in the source result category.

- A study can have at most one `COMPLETE` attempt.
- The completed attempt creates the posting.
- A completed AI attempt therefore represents a completed study whose final
  authoring mode was AI.
- An incomplete AI attempt shows exposure or attempted AI use but does not
  create a posting.
- No completion observed means no completed attempt appears in the captured
  report. It does not prove abandonment or a final outcome.

## Attempt ordering and pathways

Attempts within a study are ordered by:

```text
START_TIME ascending, then audit ID ascending
```

Completed pathways stop at the unique completed attempt. No-completion-observed
pathways use all captured attempts.

AI-only and manual-only mean every recorded pathway attempt used that mode.
Both modes requires at least one AI and one manual attempt. A single attempt
never uses both modes.

Retry-pathway categories are mutually exclusive and exhaustive. Percentages use
all studies with captured attempts as denominator.

## Timing

Keep these measures distinct:

| Population | Measure |
|---|---|
| Completed attempt | Estimated time on its Study Information form, from when the form appeared until the user continued |
| Completed attempt | Total elapsed Add Study workflow time through Study Information, Inclusion/Exclusion Criteria, and posting creation |
| Completed study | First recorded attempt start to completed-attempt end |
| No completion observed | First attempt start to latest observed attempt start |
| No completion observed | Latest attempt start to report-run cutoff |
| No completion observed | First attempt start to report-run cutoff |

Each attempt keeps its own timing values. The analysis does not sum Study
Information form time or total workflow time across separate attempts for one
study. Completed-attempt timing distributions exclude incomplete attempts.

These are elapsed durations and may include pauses or inactive browser time.
They do not measure active attention or effort and do not define follow-up
eligibility, drop-off, abandonment, or final outcomes.

## Author experience

Attempt-start experience uses one author-attempt observation:

```text
PRIOR_CREATED_COUNT
```

Query-time experience uses one distinct-author value per metric and adoption
group:

- total studies created;
- other-study memberships;
- distinct login days;
- login-history span.

Distinct login days count calendar dates with at least one recorded successful
login. Login-history span is elapsed time from earliest to latest available
successful login.

Attempt-start and login summaries visibly show the 25th-to-75th-percentile
interval, median, and mean.

Study-count summaries visibly show the interval and median. Mean and P90 remain
available in hover.

Missing group-and-metric combinations are omitted rather than plotted as zero.

### Percentile-bin charts

`authors/current_author_experience_summary.csv` embeds one canonical,
identifier-free `author_activity_percentile_bins_json` payload.

The payload covers total studies created and other-study memberships.

For each metric, boundaries are derived across all distinct authors with
observed values and reused for every adoption group:

1. value at or below P50;
2. value above P50 through P75;
3. value above P75 through P90;
4. value above P90.

Boundary ties stay in the lower adjacent bin. Zero-count bins remain explicit.

Each horizontal bar represents 100% of authors in the group with an observed
metric value. Missing authors are excluded from the bar and reported separately.

Counts must reconcile to the observed denominator. Unrounded percentages must
reconcile to 100%.

The study summaries and both binned charts appear inside the collapsed native
disclosure titled:

```text
Additional study-creation and membership context
```

Login context remains visible outside that disclosure. Print styling expands
collapsed content.

## Field adoption and editing

Field analysis uses completed AI attempt-and-field rows.

- Offer and selection populations may differ by field.
- Selection percentages use attempts with at least one offered suggestion.
- Selected outcomes preserve exact, cosmetic, light, moderate, heavy,
  edited-unclassified, replaced, and cleared categories.
- `EDITED_UNCLASSIFIED` remains separate from `REPLACED`.

The operational character-edit bands are:

| Category | Character edit ratio |
|---|---:|
| Light | At or below 0.10 |
| Moderate | Above 0.10 through 0.30 |
| Heavy | Above 0.30 |

Scheme:

```text
EXPLORATORY_CHARACTER_RATIO_10_30
```

These are project-specific descriptive bands, not writing-quality standards.

## Suggestion index

For title, purpose, and about, the prompt intends earlier indices to be ranked
more highly. Index `0` is first. Returned order is preserved.

The audit stores complete generated text and the latest selected text. The
selected index is derived by exact text matching against the ordered suggestion
list. Selecting another suggestion before submission replaces the previous
selection; selection-click history is not captured.

A field may return fewer than the requested maximum or no suggestions. An empty
field suggestion list in a valid response is not a generation error.

This is prompt intent, not proof of objective quality. Order was not randomized,
so selection is confounded with model ranking, display position, and
opportunity. Index associations do not identify a visual-position effect.

Use selected-at-index divided by offered-at-index. Controlled vocabularies are
set comparisons rather than ordinary free-text rank analyses. Analyze
compensation within suggestion kind because generic and specific suggestions
have separate position semantics.

## Readability

Readability change is:

```text
final value - selected-suggestion value
```

Lower and higher are neutral directions, not better and worse.

Short text, especially titles, has limited reliability. Formula values do not
establish comprehension, accuracy, accessibility, usefulness, cultural
appropriateness, or writing quality.

Selected-versus-unselected comparison requires exactly one selected suggestion,
at least one unselected suggestion, and usable readability values for both.
Omission means no rows met every requirement.

## Source and latency

Returned-result AI attempts exclude recorded AI-error categories and may include
eligible incomplete attempts. Returning a result does not mean a posting was
created.

Source-size bands derive from all returned-result AI generations and are reused
for completed AI attempts.

Equal source size and reported source form an unchanged-source proxy, not proof
of identical text.

Latency and source associations are descriptive and do not establish causality.

## Audit-write boundary

Latest selection and optional feedback, final saved values, and form timing are
submitted through separate updates. They are not one atomic capture. Missing or
stale values in one component therefore do not by themselves prove that another
component was unavailable.

## Missing values

Published CSV files use:

- UTF-8;
- LF line endings;
- stable declared column order;
- `\N` for missing values.

A zero denominator produces a missing percentage, not a fabricated zero.

Blank final text is absent from readability metrics. The current normalized
contract cannot distinguish every blank, unavailable, and not-applicable case,
so missing/blank final-text rates are not inferred.

## Privacy and interpretation

Faculty-facing charts use aggregates only.

Restricted `analysis-audit-records/` files contain identifiers for authorized
internal investigation.

Do not infer:

- causal effects;
- author productivity or tenure;
- user motivation or satisfaction;
- suggestion quality from selection;
- writing quality from edit size or readability;
- source identity from proxy equality;
- abandonment from no completion observed.

Software verification establishes agreement with documented rules. It does not
scientifically validate the measures.
