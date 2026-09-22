# Study Posting Audit inquiry guide

## Purpose

This guide helps faculty, analysts, developers, and language-model assistants
find authoritative answers about the Study Posting Audit analysis.

Use the repository documentation and source together. Do not infer a metric,
denominator, data source, or causal interpretation from a chart title alone.

## Where to start

| Question | Start here |
|---|---|
| What does the project do? | [Root README](../../../../README.md) |
| What files are produced? | [Exploration README](../README.md) |
| Where did a report value come from? | [Data lineage](data-lineage.md) |
| How are study fields classified? | [Study analysis specification](../../../packages/study-posting-ai-analysis/docs/analysis-specification.md) |
| How are edit metrics calculated? | [Post-edit methodology](../../../packages/text-post-edit-metrics/docs/methodology.md) |
| How are edit metrics tested? | [Post-edit verification](../../../packages/text-post-edit-metrics/docs/verification.md) |
| What does a readability metric mean? | [Readability package README](../../../packages/text-readability-metrics/README.md) |
| How are normalized source files produced? | [Audit-report README](../../study-posting-audit-report/README.md) |
| What does each aggregate column mean? | Generated `definitions/metric_definitions.csv` |
| Which research questions are currently supported? | Generated `research/candidate_research_questions.csv` |

## Answering a faculty question

A reliable answer should identify:

1. the analytical unit, such as attempt, study, author, field, suggestion, or
   readability pair;
2. the eligible population and denominator;
3. the source file and source column;
4. any derivation or filtering rule;
5. the aggregate output and report section;
6. missing-value treatment;
7. whether the result is descriptive or inferential;
8. the implementation and verification locations when calculation details are
   requested.

When possible, cite repository-relative paths and exact field names.

Do not claim that passing tests proves scientific validity. Tests establish
agreement with the documented software contract.

## Answer-quality checklist for an LLM

Before finalizing an answer, confirm:

- [ ] I cited the owning documentation or code.
- [ ] I stated the analytical unit.
- [ ] I stated the eligible population and denominator.
- [ ] I distinguished source values from derived values.
- [ ] I identified missing-value treatment.
- [ ] I distinguished current implementation from a proposed interpretation.
- [ ] I did not claim causality from descriptive output.
- [ ] I did not treat a software test as scientific validation.
- [ ] I used a synthetic example for calculations.
- [ ] I stated uncertainty where documentation is incomplete.

## Main analytical units

| Unit | Meaning |
|---|---|
| Attempt | One `records.csv` row, keyed by `ID` |
| Study | Attempts sharing `STUDY_NUM` |
| Attempt author | Exact `AUTHOR_USER_NAME` on an attempt |
| Completed study | A study's unique `COMPLETE` attempt |
| Field analysis | One completed AI attempt and analyzed field |
| Suggestion instance | One attempt, field, kind, and zero-based index |
| Readability pair | One selected suggestion and final value for the same attempt and field |

Do not combine counts across units without an explicit join and denominator.

## Suggestion index and intended model rank

The author-assistance prompt explicitly instructs the model to rank suggestions
from best to worst for:

- title;
- purpose;
- about.

For those fields, zero-based index 0 is the model's intended highest-ranked
suggestion, followed by later intended ranks.

This is prompt intent, not proof that the order is correct.

Selection by index can answer:

> Did authors select earlier prompt-ranked suggestions more often?

It cannot by itself answer:

> Did the model objectively rank suggestion quality correctly?

Important limitations:

- model rank is confounded with display position;
- later indices are not offered on every attempt;
- author selection measures preference or practical fit, not objective quality;
- selection does not show whether text was retained or heavily edited.

Use `selected at index / offered at index`, not raw selected counts.

For compensation, analyze suggestion kind and within-kind index separately.
The prompt places specific suggestions before generic suggestions, so the six
display positions are not one clean best-to-worst scale.

A stronger ranking evaluation would preserve hidden model rank while
randomizing display order and obtaining blinded rubric ratings.

## How to provide a calculation walkthrough

When asked to show a metric step by step:

1. use synthetic text, not operational study text;
2. state the direction: selected suggestion to final saved text;
3. show preprocessing, including Unicode NFC and case behavior;
4. enumerate the permitted edit operations;
5. calculate the raw distance or rate;
6. identify the final-text denominator;
7. calculate the raw effort-saved score;
8. apply the `[0, 1]` bound when the bounded field is requested;
9. state the result field name;
10. state what the value does not measure.

Example character calculation:

```text
suggestion = "cat"
final      = "cart"

minimum character edits = 1 insertion
final character count   = 4

character_effort_saved_raw = 1 - 1/4 = 0.75
character_effort_saved     = 0.75
estimated_characters_saved = max(0, 4 - 1) = 3
```

This does not mean exactly three keystrokes or 75% of time was saved.

For TER, use SacreBLEU with the documented fixed configuration. Do not manually
reconstruct TER from whitespace token counts because TER has its own processing
and phrase-shift behavior.

For weighted soft-word distance, show the Wagner-Fischer matrix or recurrence
only when requested. Substitution cost is RapidFuzz normalized character
distance between words.

## Post-edit metric interpretation

All text comparisons are directional:

```text
selected suggestion → final saved text
```

The generic methodology defines:

- Translation Edit Rate;
- bounded and raw TER-derived scores;
- character Levenshtein distance;
- character effort-saved scores;
- weighted soft-word distance;
- estimated characters saved.

These describe textual transformation. They do not directly measure time,
cognition, observed keystrokes, semantic quality, or usefulness.

For a mathematical walkthrough, use the worked examples and recurrences in the
[post-edit methodology](../../../packages/text-post-edit-metrics/docs/methodology.md).

## Readability interpretation

Readability formulas are descriptive indicators based on features such as
sentence length, word length, syllables, letters, and familiar-word lists.

They do not establish:

- comprehension;
- accuracy;
- accessibility;
- inclusiveness;
- usefulness;
- writing quality.

Short text, especially titles, has limited readability reliability.

## Source and output boundaries

The normalized report contains:

- `records.csv`;
- `ai_assistance_metrics.csv`;
- `readability_metrics.csv`.

The exploration validates those files and publishes 31 files, including:

- aggregate CSV files;
- restricted analysis-audit records;
- metric definitions;
- candidate research questions;
- a self-contained HTML report.

The HTML charts use aggregate tables. The final feedback table is the narrow
authorized exception and displays only audit record ID and
`USER_FEEDBACK_COMMENTS`.

## Descriptive versus inferential claims

The current exploration is descriptive.

It can describe:

- counts and percentages;
- distributions;
- selections and edits;
- observed associations;
- data-quality conditions.

It does not establish:

- causal effects of AI;
- improved writing or recruitment;
- individual performance;
- population-level generalizability;
- statistical significance unless a future analysis explicitly implements and
  documents it.

## Reproducibility checklist

For a reproducible answer, record:

- Git revision;
- analysis generation time;
- source report directory;
- source row counts;
- output row counts;
- metric dependency versions;
- exact numerator and denominator;
- missing-value treatment;
- any filters or grouping dimensions.

The generated manifest and metric definitions contain much of this information.

## Retry pathways and observed workflow patterns

Use these outputs together:

- `overview/study_retry_pathway_summary.csv` for the exhaustive,
  mutually exclusive one-row-per-pathway distribution;
- `overview/retry_characteristics_summary.csv` for completed-AI,
  completed-manual, and no-completion-observed characteristics;
- `overview/repeated_attempt_source_consistency_summary.csv` for detailed
  adjacent returned-result AI source comparisons.

Each study contributes to exactly one retry pathway. The pathway sequence uses
attempts through the unique completion attempt for completed studies and all
captured attempts otherwise. `USER_DROPPED` is an attempt result, not a study
outcome.

Interpret percentages with their paired denominators:

- pathway percentages: all studies with captured attempts;
- general characteristic percentages: studies in the outcome-group row;
- source-signature change: source-comparison-eligible studies;
- feedback recorded: AI-exposed studies.

Missing percentages indicate a zero denominator. Do not replace them with zero.

Completed timing is first attempt start to completed-attempt end. No-completion-observed timing
is first attempt to latest observed attempt. The latter does not measure
follow-up. Until a report-query timestamp and minimum follow-up threshold are
defined, do not compare no-completion-observed percentages as drop-off or final
outcomes.

Observed patterns can motivate qualitative follow-up. They do not establish why
authors changed modes, whether AI output was liked or rejected, whether source
changes were intentional experiments, why an author handoff occurred, or
whether a study was abandoned.

When `REPORT_RUN_CUTOFF` is available, distinguish observed activity span from follow-up after the latest attempt and from the total observation window. These durations remain descriptive. No study is follow-up eligible until a minimum threshold is explicitly selected.

In the retry summaries, use `study_count_with_report_run_cutoff` as the contributing count for cutoff medians. Do not compare those medians as threshold-qualified outcomes; no minimum follow-up threshold is defined.
