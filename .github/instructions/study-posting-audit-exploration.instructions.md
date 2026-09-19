---
applyTo: "python/programs/study-posting-audit-exploration/**"
---

# study-posting-audit-exploration instructions

## Contract

This program validates normalized audit-report output and publishes a
self-contained descriptive exploration.

It owns:

- normalized-input validation;
- attempt, study, author, field, and readability derivation;
- aggregate CSV contracts;
- metric definitions;
- candidate research questions;
- data-quality summaries and restricted findings;
- faculty-facing HTML;
- manifest and atomic publication.

It must not reimplement:

- source extraction;
- generic row conversion;
- study field analysis;
- generic post-edit metrics;
- generic readability formulas;
- Oracle connectivity.

## Input and publication contracts

Required normalized inputs:

- `records.csv`;
- `ai_assistance_metrics.csv`;
- `readability_metrics.csv`.

A successful run publishes exactly 31 files.

Publication uses staging followed by atomic rename. Do not change the inventory,
manifest, schemas, or paths without updating exact-inventory tests and
documentation.

## Analytical units

Keep these distinct:

- attempt;
- study;
- exact attempt author;
- completed study;
- attempt-field;
- suggestion instance;
- readability pair.

Every percentage requires an explicit denominator.

## Faculty and LLM answers

When answering questions about the exploration:

1. identify the analytical unit;
2. name the eligible population;
3. identify numerator and denominator;
4. cite normalized inputs;
5. cite derived and aggregate outputs;
6. cite implementation and tests when formulas are questioned;
7. distinguish descriptive results from inferential or causal claims.

Use:

- `docs/inquiry-guide.md`;
- `docs/data-lineage.md`;
- generated `definitions/metric_definitions.csv`;
- generated `analysis_manifest.json`;
- owning package methodology.

Do not infer undocumented semantics from column names alone.

## Suggestion index

For title, purpose, and about, zero-based suggestion index represents the
model's prompt-assigned intended rank. Index 0 is intended to be highest.

Selection-by-index is descriptive and does not prove objective ranking quality.

Use offered-at-index denominators. Treat compensation separately by suggestion
kind because specific suggestions precede generic suggestions.

## HTML boundaries

Charts consume aggregate tables only.

The user-feedback table is the narrow authorized exception and may render only:

- `records.ID`;
- `records.USER_FEEDBACK_COMMENTS`.

Do not pass source records or restricted findings to chart APIs.

Preserve:

- semantic navigation;
- faculty summary;
- native details/summary progressive disclosure;
- print expansion of collapsed content;
- accessible feedback table;
- aggregate cautions;
- feedback as the final report section.

## Restricted outputs

`analysis-audit-records/` contains identifier-bearing internal traceability
data. Do not pass it to faculty-facing charts or HTML.

`data_quality_findings.csv` may be used locally for targeted investigation.

## Interpretation

The program is descriptive.

Do not claim:

- causal AI effects;
- improved writing or recruitment;
- objective suggestion quality from selection alone;
- author productivity;
- scientific validity from passing tests.

Tests establish software agreement with documented contracts.

## Development

Use synthetic data only.

Run focused checks:

```bash
make format
make lint
make typecheck
make test PACKAGE=study-posting-audit-exploration
make coverage PACKAGE=study-posting-audit-exploration
git diff --check
```

Run full gates before commit:

```bash
make docs-check
make check
make hooks-run
```
