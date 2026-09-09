---
applyTo: "python/packages/study-posting-ai-analysis/**"
---

# study-posting-ai-analysis instructions

## Contract and scope

This pure library analyzes three objects:

```python
results = analyze_objects(suggested, selected, final)
```

It owns study-posting policy:

- configured fields and requiredness;
- suggestion-selection validation;
- match classification;
- cosmetic-equivalence classification;
- contact and compensation behavior;
- lookup/Jaccard analysis;
- JSON-object parsing;
- flattening to tabular dictionaries.

It performs no database, CSV, filesystem, DataFrame, logging, CLI, audit-table
filtering, or report-writing work.

Technical text metrics belong to `text-post-edit-metrics`:

```python
from text_post_edit_metrics import PostEditingResult, analyze_post_edit
```

Do not recreate metric algorithms or a study-package metric-wrapper module.

## Field identity and text metrics

`PostEditingResult` contains no study field name. Field identity belongs in:

- the key of `dict[str, AnalysisResult]`;
- `Pick.kind` for a selected suggestion;
- `field_name` in flattened output.

For selected, nonblank text, call:

```python
analyze_post_edit(
    suggestion=selected_text,
    final=final_text,
)
```

Store the result in `TextFieldAnalysis.editing_metrics`.

For `REMOVED` and `UNASSISTED`, `editing_metrics` is `None`.

## Text outcomes

Evaluate in this order:

```text
blank → exact → cosmetic-equivalent → edited
```

| Outcome | Meaning |
|---|---|
| `EXACT` | Selected and final strings are equal |
| `COSMETIC_EQUIVALENT` | Equal after the study cosmetic transformation |
| `EDITED` | Selected and nonblank final text differ substantively |
| `REMOVED` | Selected suggestion followed by an optional blank final |
| `UNASSISTED` | No AI suggestion was selected |

Policy-adjusted scores:

| Outcome | Score |
|---|---:|
| `EXACT` | `1.0` |
| `COSMETIC_EQUIVALENT` | `1.0` |
| `EDITED` | bounded TER-derived score |
| `REMOVED` | `0.0` |
| `UNASSISTED` | `0.0` |

## Cosmetic equivalence

`normalize_text_for_equivalence()` applies:

1. NFKD decomposition;
2. case folding;
3. combining-mark removal;
4. punctuation and symbol replacement with spaces;
5. whitespace collapsing.

Use it only for classification. Never pass its output to
`analyze_post_edit()`, because that would hide actual textual edits.

## Requiredness

Required:

- `title`
- `purpose`
- `description`
- `contact.email`
- `contact.name`

Optional:

- `about`
- `contact.phone`
- `contact.website`

Compensation text is required exactly when the final saved
`offersCompensation` value is `True`. The saved Boolean must be `True` or
`False`.

A blank required value raises `ValueError`; it is not assigned a score.

## Contact and compensation

Contact expands into four results:

- `contact.email`
- `contact.name`
- `contact.phone`
- `contact.website`

A selected contact value must have been offered and must equal the offered value
before final editing.

Compensation combines categorized text and the `offersCompensation` Boolean.
Categories are:

- `genericCompensation`
- `specificCompensation`

At most one compensation text suggestion may be selected across both categories.
Boolean acceptance and text post-editing are separate outcomes.

## Lookup fields

Lookup fields are `department`, `locations`, and `topics`.

- IDs must be integers; explicitly reject Booleans.
- Every picked ID must have been offered.
- Assisted similarity is Jaccard: `|picked ∩ saved| / |picked ∪ saved|`.
- If nothing was picked, classify as `UNASSISTED` and assign policy similarity
  `0.0`.
- Never combine lookup similarity with text effort-saved scores.

## Parsing and flattening

`parse_json_object()` accepts JSON text, UTF-8 bytes, or a decoded dictionary.
It rejects missing, blank, malformed, non-UTF-8, and non-object values.

`flatten_analysis_results()` returns one `dict[str, object]` per field.

- Every row contains all `FLATTENED_COLUMNS` in canonical order.
- Values are only `None`, `bool`, `int`, `float`, or `str`.
- Free text is excluded by default.
- Lookup sets are sorted JSON arrays.
- Lookup rows leave text metric and policy columns as `None`.

`FLATTENED_COLUMNS` is a published contract.

## Tests and documentation

Test study-specific behavior here. Do not duplicate low-level metric tests owned
by `text-post-edit-metrics`.

Use the shared `valid_audit_objects` fixture and modify only fields relevant to
the test.

The specification of record is:

```text
python/packages/study-posting-ai-analysis/docs/analysis-specification.md
```

Update it with changes to field configuration, requiredness, classification,
cosmetic equivalence, compensation, lookup policy, policy scoring, or flattened
output.

Run:

```bash
make test PACKAGE=study-posting-ai-analysis
make coverage PACKAGE=study-posting-ai-analysis
make check
```
