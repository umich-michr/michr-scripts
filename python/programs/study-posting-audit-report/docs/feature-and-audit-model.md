# AI-assisted Study Posting feature and audit model

This document explains the product flow, domain relationships, and captured
audit information used by the Study Posting Audit programs.

It is a conceptual map, not a source-system schema or operational SQL
specification. Exact normalized columns are documented in the exploration
[data-lineage guide](../../study-posting-audit-exploration/docs/data-lineage.md).

## Domain concepts

### Study

A study is the research record associated with one or more study-posting
authoring attempts.

Attempts sharing `STUDY_NUM` belong to the same study.

A study may have multiple incomplete attempts but no more than one completed
attempt in the normalized audit contract. The completed attempt creates the
posting.

### Attempt

An attempt is one captured authoring session.

It records:

- start time;
- optional completion time;
- AI or manual authoring mode;
- result category;
- study and author context;
- recorded timing;
- optional AI source and response information.

An incomplete AI attempt shows AI exposure or attempted use. It does not show
that a posting was created.

### Attempt author

The attempt author is the exact account recorded on that attempt.

An author's role is study-specific. The same person may participate in several
studies and may hold different roles across them.

### Principal investigator

The named principal investigator belongs to the study context. The PI may or
may not be the attempt author.

PI status and author role must not be treated as permanent person-level
classifications.

### Study team

A study may contain a principal investigator and other team members. A person
can author attempts for more than one study and can be a PI for one study but
not another.

## User flow

### Manual authoring

1. The user begins a study-posting attempt.
2. The user enters or revises posting fields directly.
3. The attempt may be completed or may end without completion.
4. A completed attempt creates the posting and stores final values.

Manual attempts remain important context even though they do not have
AI-suggestion analysis.

### AI-assisted authoring

1. The user begins an AI authoring attempt.
2. The user provides source material, such as pasted text or an uploaded file.
3. The application requests AI assistance.
4. The AI may return:
   - text suggestions;
   - contact values;
   - lookup IDs;
   - content-source classification;
   - compensation text;
   - a compensation yes/no recommendation.
5. The user may select, ignore, edit, replace, or clear offered values.
6. The user may complete the posting or leave the attempt incomplete.
7. The final submission stores the values saved on completion.

An AI request can fail or return a result without the attempt completing.
These states are distinct from completed AI use.

## Captured audit information

The source audit export can contain the following concept groups.

### Attempt and study identity

- audit attempt ID;
- study number;
- start and end times;
- authoring mode;
- result category;
- study creation context.

### Author and team context

- attempt-author account and application ID;
- study-team role;
- eResearch role;
- author appointments;
- named PI account and appointments;
- study creator ID.

These fields support authorized internal traceability. They are not included in
faculty-facing aggregate charts.

### Experience and activity context

- studies created before attempt start;
- total studies created at report-query time;
- other-study memberships;
- distinct login days;
- earliest and latest available login timestamps.

Attempt-start and query-time values have different analytical meanings and must
not be combined as though measured at the same time.

### Workflow timing

- time on the study-information page;
- total attempt duration;
- AI-generation latency.

Recorded durations can include pauses or work outside the application. They do
not directly measure cognitive effort or efficiency.

### AI source context

- input method or source type;
- source character count;
- user-reported content source;
- model-inferred content source;
- optional Other-category text.

### AI interaction

- suggestions offered;
- suggestions or lookup values selected;
- final saved submission;
- model metadata;
- optional user feedback.

The analysis distinguishes offer, selection, final retention, editing,
replacement, clearing, and unassisted final values.

## Normalized analytical layers

The audit-report program separates the source into four files.

| File | Grain | Purpose |
|---|---|---|
| `records.csv` | Attempt | Preserve canonical source rows |
| `ai_assistance_metrics.csv` | Completed AI attempt and field | Selection, outcome, lookup, compensation, and text metrics |
| `readability_metrics.csv` | Eligible nonblank text instance | Generic readability values without source text |
| `report_metadata.json` | Report run | Generation time and source-cutoff provenance |

Joins use the configured source record ID:

```text
records.ID
    = ai_assistance_metrics.record_id
    = readability_metrics.record_id
```

## Analysis eligibility

Study-field AI analysis requires:

```text
ATTEMPT_TYPE = AI
ATTEMPT_RESULT = COMPLETE
```

Eligible completed AI rows also require:

- completion time;
- suggestions payload;
- selections payload;
- final submission payload.

Manual and incomplete attempts remain in `records.csv` but do not produce
AI-assistance field rows.

Readability analysis includes:

- offered suggestions and final values from completed AI attempts;
- final values from completed manual attempts;
- nonblank text only.

## Relationships supported by the audit

The data can describe relationships such as:

- attempts within one study;
- the author sequence leading to completion;
- AI/manual mode sequences;
- suggestion offer, selection, and final outcome;
- text editing between selected and final values;
- lookup values offered, selected, retained, dropped, or added;
- compensation recommendation and final choice;
- source characteristics and latency;
- author experience and activity distributions;
- descriptive feedback presence and authorized feedback text.

## What the audit cannot establish

The audit does not by itself establish:

- why a user selected or ignored a suggestion;
- whether a suggestion was objectively good;
- whether AI caused completion, speed, or quality differences;
- actual keystrokes or cognitive effort;
- activity outside the application;
- whether no observed completion means abandonment;
- permanent author expertise, engagement, productivity, or tenure.

Use descriptive, non-causal language and state the analytical unit and
denominator for every result.

## Related documentation

- [Running the program](running.md)
- [Normalized report contract](normalized-report.md)
- [Exploration analytical rules](../../study-posting-audit-exploration/docs/analysis-rules.md)
- [Exploration output reference](../../study-posting-audit-exploration/docs/output-reference.md)
- [Source-to-report lineage](../../study-posting-audit-exploration/docs/data-lineage.md)
- [Study-field analysis policy](../../../packages/study-posting-ai-analysis/docs/analysis-specification.md)
- [Study-analysis control flow](../../../packages/study-posting-ai-analysis/docs/program-flow.md)
- [Generic post-edit methodology](../../../packages/text-post-edit-metrics/docs/methodology.md)
- [Generic readability metrics](../../../packages/text-readability-metrics/README.md)
