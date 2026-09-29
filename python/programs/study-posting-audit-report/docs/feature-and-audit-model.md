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

Every valid Add Study workflow initializes one parent audit attempt before the
manual or AI-assisted path continues. A manual attempt has no linked generation
audit. An AI attempt has a linked generation audit, even when generation later
records an error.

### Manual authoring

1. The user begins a study-posting attempt.
2. The user enters or revises posting fields directly.
3. The attempt may be completed or may end without completion.
4. A completed attempt creates the posting and stores final values.

Manual attempts remain important context even though they do not have
AI-suggestion analysis.

### AI-assisted authoring

1. The user enables the optional AI path and supplies nonblank source text.
2. For an uploaded supported file, the browser extracts text before submission;
   the backend receives the extracted text, not the file. Direct entry sends
   the entered text through the same backend boundary.
3. Client validation prevents submission when source extraction or entry leaves
   the required text blank.
4. The application creates a linked generation audit and requests AI
   assistance.
5. A valid structured response may contain suggestions for some fields and
   empty arrays for others. Empty field suggestions are not a generation error.
6. A provider-call or calling-code exception is recorded as a linked AI error.
7. The user may select, ignore, edit, replace, or clear offered values.
8. The user may complete the posting or leave the attempt incomplete.
9. The final submission stores the values saved on completion.

AI assistance is available once within the posting-creation wizard. An AI
attempt remains an AI attempt whether suggestions were returned, selected,
edited, or retained.

The source audit keeps three concepts separate:

| Concept | Meaning |
|---|---|
| Source input method | Whether text was entered directly or extracted in the browser from a supported file type |
| User-reported content source | The user's controlled source category, with optional detail for Other |
| Model-inferred content source | The model's suggestion from the same allowed category vocabulary |

A provider response with no suggestion for a field is a returned result. It
must not be classified as an AI-generation failure.

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

- estimated time on the Study Information form during one attempt;
- total elapsed Add Study workflow time;
- AI-generation latency.

Study Information form time is measured from when the form appears until the
user continues to the next step. If the same attempt revisits and resubmits that
form, its submitted intervals are added within that attempt. The analysis does
not sum form time across separate attempts for a study.

Total workflow time runs from the start of the attempt through submission of
the Study Information and Inclusion/Exclusion Criteria steps and creation of
the posting. It is available only for completed attempts.

Both measures are elapsed time and may include pauses or time when the form was
open but the user was not actively working. They do not directly measure active
attention, cognitive effort, engagement quality, or efficiency.

### AI source context

- input method or source type;
- source character count;
- user-reported content source;
- model-inferred content source;
- optional Other-category text.

### AI interaction

- complete ordered suggestion text;
- latest suggestions or lookup values selected before submission;
- complete final saved submission;
- model metadata;
- optional user feedback.

For an ordinary text field, clicking another suggestion replaces the previously
recorded selection. The audit stores the latest selected suggestion, not a
history of every selection click. The selected text remains separate from the
editable final value, so selection does not imply unchanged retention.

Generated, selected, and final text are stored as complete strings. The
zero-based index of a selected text suggestion is derived by exact text matching
against the ordered generated list.

Show/hide suggestion controls and Read More/Read Less affect only the current
display. They are not persisted, do not change suggestion order or AI-exposure
classification, and cannot establish whether a suggestion was read.

Selection and optional feedback, final values, and Study Information form time
are saved through separate updates rather than one atomic capture. A failed
update can therefore leave one of these audit components unavailable even when
another was saved.

The analysis distinguishes offer, selection, final retention, editing,
replacement, clearing, and unassisted final values.

### Attempt classification

The sanitized source SQL derives the following values.

`ATTEMPT_TYPE` is `AI` when a linked generation audit has a source input method;
otherwise it is `MANUAL`. This identifies the authoring path, not generation
success or suggestion adoption.

`ATTEMPT_RESULT` uses this precedence:

1. a linked nonblank stack trace → `AI_ERROR`;
2. zero generation latency without a stack trace →
   `AI_ERROR_WITHOUT_STACK_TRACE`;
3. no completed workflow submission → `USER_DROPPED`;
4. otherwise → `COMPLETE`.

`AI_ERROR_WITHOUT_STACK_TRACE` is retained as a defensive anomaly category.
A valid response with empty field suggestions is not an error. Because error
evidence has precedence, use the exact result category together with completion
fields when answering whether a posting was created.

`USER_TYPE` is `EXISTED` when the attempt author matched an application
study-team relationship for that study and `NON_EXISTENT` otherwise. It is a
study-relative membership classification, not account existence, PI status, AI
use, or completion.

### Agreement reminder

The source-entry step includes a required client-side reminder linking to the
study-team agreement. Its per-attempt checkbox is not stored in this Study
Posting audit. First-login agreement capture is a separate access-control audit
outside this analytical dataset.

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
