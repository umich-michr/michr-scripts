# study-posting-ai-analysis

Pure library for comparing AI suggestions, user selections, and final saved
values for configured Study Posting fields.

```python
from study_posting_ai_analysis import analyze_objects

results = analyze_objects(
    suggested_object,
    selected_object,
    final_object,
)
```

## What it owns

- field configuration and requiredness;
- suggestion-selection validation;
- text outcome classification;
- cosmetic-equivalence policy;
- contact, compensation, and lookup analysis;
- JSON-object parsing;
- canonical flattened rows;
- study-specific policy scores.

It delegates generic text metrics to
[`text-post-edit-metrics`](../text-post-edit-metrics/).

It performs no database, CSV, filesystem, DataFrame, logging, CLI, aggregation,
or report-writing work.

## Main flow

```python
from study_posting_ai_analysis import (
    analyze_objects,
    flatten_analysis_results,
    parse_analysis_inputs,
)

suggested, selected, final = parse_analysis_inputs(
    suggested_payload,
    selected_payload,
    final_payload,
)

results = analyze_objects(suggested, selected, final)

rows = flatten_analysis_results(
    results,
    record_id="synthetic-record",
    include_text=False,
)
```

Call `analyze_objects()` directly when inputs are already dictionaries.

## Result families

| Family | Main behavior |
|---|---|
| Text | Exact, cosmetic-equivalent, edited, removed, or unassisted |
| Contact | Independent email, name, phone, and website analysis |
| Compensation | Text outcome plus suggested/final Boolean relationship |
| Lookup | Offered, picked, saved, kept, dropped, added, and Jaccard similarity |

Selected nonblank text receives a generic `PostEditingResult`. Removed and
unassisted text does not.

Lookup similarity remains separate from text effort-saved metrics.

## Parsing and flattening

`parse_json_object()` accepts JSON text, UTF-8 bytes, or a decoded dictionary.
It rejects missing, blank, malformed, non-UTF-8, and non-object values.

`flatten_analysis_results()` returns one canonical dictionary per field.

- Every row contains `FLATTENED_COLUMNS`.
- Values are scalar or `None`.
- Free text is excluded by default.
- Lookup sets are sorted JSON arrays.

`FLATTENED_COLUMNS` is a published contract.

## Public API

Important exports:

- `analyze_objects()`;
- specialized text, contact, compensation, and lookup analyzers;
- `parse_analysis_inputs()` and `parse_json_object()`;
- `flatten_analysis_results()`;
- `FLATTENED_COLUMNS`;
- field and compensation configuration constants.

## Documentation

| Document | Purpose |
|---|---|
| [`docs/analysis-specification.md`](docs/analysis-specification.md) | Authoritative field policy, outcomes, formulas, reporting vocabulary, and interpretation |
| [`docs/program-flow.md`](docs/program-flow.md) | Control flow and package boundaries |
| [`../text-post-edit-metrics/docs/methodology.md`](../text-post-edit-metrics/docs/methodology.md) | Generic text-metric formulas |
| [`../../programs/study-posting-audit-report/docs/feature-and-audit-model.md`](../../programs/study-posting-audit-report/docs/feature-and-audit-model.md) | Product flow and captured audit context |

If implementation and the analysis specification disagree, update or correct
them in the same change.

## Interpretation

Results describe suggestion use and textual transformation. They do not directly
measure time, cognition, observed keystrokes, semantic quality, satisfaction, or
overall usefulness.

## Development

```bash
make test PACKAGE=study-posting-ai-analysis
make coverage PACKAGE=study-posting-ai-analysis
make check
```

## License

MIT
