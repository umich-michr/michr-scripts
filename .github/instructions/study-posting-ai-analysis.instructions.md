---
applyTo: "python/packages/study-posting-ai-analysis/**"
---

# study-posting-ai-analysis instructions

## Package contract

This package analyzes three study-posting objects:

```python
results = analyze_objects(
    suggested_object,
    selected_object,
    final_object,
)
```

It interprets AI offers, user selections, and final saved values according to
study-posting form rules.

Technical text metrics are delegated to:

```python
from text_post_edit_metrics import analyze_post_edit
```

The returned `PostEditingResult` is stored in
`TextFieldAnalysis.editing_metrics`.

## Scope

This package owns:

- study-posting field definitions;
- text-suggestion selection validation;
- text outcome classification;
- cosmetic-equivalence policy;
- field requiredness;
- contact analysis;
- compensation text and Boolean analysis;
- lookup ID and Jaccard analysis;
- JSON decoding of the three input objects;
- flattening study results into tabular dictionaries.

It must not own:

- TER implementation;
- character-level Levenshtein implementation;
- weighted soft-word implementation;
- generic metric normalization;
- database or SQL access;
- CSV or filesystem access;
- pandas or DataFrames;
- logging;
- command-line behavior;
- audit-table eligibility or schema mapping.

Those responsibilities belong to other packages or programs.

## Dependency boundary

The dependency direction is:

```text
text-post-edit-metrics
          ↑
study-posting-ai-analysis
```

This package may import `text_post_edit_metrics`.

`text-post-edit-metrics` must never import this package.

Do not recreate metric wrappers or compatibility modules in this package.
There must be no study-package metric implementation or compatibility-wrapper
module. Import generic text metrics directly from `text_post_edit_metrics`.

Consumers that need generic text metrics import them directly:

```python
from text_post_edit_metrics import (
    PostEditingResult,
    analyze_post_edit,
)
```

## Field identity

`PostEditingResult` contains no field name.

Field identity is represented by:

- the key in `dict[str, AnalysisResult]`;
- `Pick.kind` when a suggestion was selected;
- `field_name` in flattened output.

Do not duplicate form-specific field identity inside the generic metric result.

## Outcome classification

### Text outcomes

| Outcome | Meaning |
|---|---|
| `EXACT` | Selected and final strings are exactly equal |
| `COSMETIC_EQUIVALENT` | Equal after the study cosmetic transformation |
| `EDITED` | Selected suggestion and nonblank final text differ substantively |
| `REMOVED` | Selected suggestion followed by an optional blank final value |
| `UNASSISTED` | No AI suggestion was selected |

Evaluation order is:

```text
blank → exact → cosmetic-equivalent → edited
```

Do not reorder these checks.

For `EXACT`, `COSMETIC_EQUIVALENT`, and `EDITED`, call:

```python
analyze_post_edit(
    suggestion=selected_text,
    final=final_text,
)
```

For `REMOVED` and `UNASSISTED`, `editing_metrics` is `None`.

## Cosmetic-equivalence policy

`normalize_text_for_equivalence()` performs:

1. Unicode NFKD decomposition;
2. Unicode-aware case folding;
3. combining-mark removal;
4. punctuation and symbol replacement with spaces;
5. whitespace collapsing and trimming.

It is used only for classification.

Never pass cosmetically normalized text into `analyze_post_edit()`. Metric inputs
must preserve actual punctuation, capitalization, diacritics, and whitespace
differences apart from the generic package's NFC normalization.

## Policy-adjusted score

| Outcome | Score |
|---|---:|
| `EXACT` | `1.0` |
| `COSMETIC_EQUIVALENT` | `1.0` |
| `EDITED` | bounded TER-derived score |
| `REMOVED` | `0.0` |
| `UNASSISTED` | `0.0` |

This is a product policy score, not a TER result.

## Requiredness

Required text fields:

- `title`
- `purpose`
- `description`
- `contact.email`
- `contact.name`

Optional text fields:

- `about`
- `contact.phone`
- `contact.website`

Compensation text is required exactly when the final saved
`offersCompensation` value is `True`.

The saved compensation Boolean must be `True` or `False`.

A blank required value raises `ValueError`. It is not assigned a score of zero.

## Contact rules

Contact subfields are analyzed separately:

- `contact.email`
- `contact.name`
- `contact.phone`
- `contact.website`

Each subfield offers at most one suggestion.

A selected contact value must:

- have a corresponding offered value;
- equal the offered value before final editing.

Contact analysis expands one top-level `contact` object into four result entries.

## Compensation rules

Compensation combines:

- an optional categorized text suggestion;
- the suggested `offersCompensation` Boolean;
- the final saved Boolean.

Suggestion categories:

- `genericCompensation`
- `specificCompensation`

At most one compensation text suggestion may be selected across both categories.

Boolean acceptance and text post-editing are separate outcomes.

Examples:

| Scenario | Text outcome |
|---|---|
| AI suggested `False`; user saved `True` and wrote text independently | `UNASSISTED` |
| User selected text, changed the Boolean to `False`, and cleared text | `REMOVED` |

## Lookup rules

Lookup fields:

- `department`
- `locations`
- `topics`

Values are integer identifiers.

Reject Booleans explicitly because `bool` subclasses `int`.

Every picked ID must have been offered.

For assisted outcomes:

```text
lookup_similarity = |picked ∩ saved| / |picked ∪ saved|
```

When nothing was picked:

- outcome is `UNASSISTED`;
- similarity is the policy value `0.0`;
- do not attempt an empty-set Jaccard calculation.

Never combine lookup similarity with text effort-saved scores.

## Parsing

`parse_json_object()` accepts:

- JSON strings;
- UTF-8 bytes;
- already-decoded dictionaries.

It rejects:

- missing values;
- blank strings;
- malformed JSON;
- invalid UTF-8;
- valid JSON values that are not objects.

`parse_analysis_inputs()` applies this behavior consistently to all three study
objects.

Database column names and audit-record identifiers belong to consuming programs,
not this package.

## Flattening

`flatten_analysis_results()` returns:

```python
list[dict[str, object]]
```

Every row:

- contains all names in `FLATTENED_COLUMNS`;
- preserves the same column order;
- contains only `None`, `bool`, `int`, `float`, or `str`;
- excludes selected and final text by default.

Lookup identifier sets are serialized as sorted JSON arrays.

Lookup rows leave text metric and policy columns as `None`.

`FLATTENED_COLUMNS` is a published contract. Adding, removing, or renaming a
column requires README and specification updates.

## Errors

Use:

- `InputParseError` for malformed JSON input;
- `TypeError` for wrong runtime types;
- `ValueError` for form-policy violations.

Functions raise and never log.

Messages should identify the field or subfield that failed.

Record-level identifiers and error-capture policy belong to consuming programs.

## Tests

Use the shared `valid_audit_objects` fixture and modify only the field relevant
to the behavior under test.

Tests should cover:

- every `MatchType`;
- required and optional behavior;
- selected-but-unoffered rejection;
- contact expansion and requiredness;
- compensation Boolean and text combinations;
- lookup set partitions and Jaccard similarity;
- JSON parsing;
- flattened row shape and text exclusion;
- integration with `PostEditingResult`.

Do not duplicate low-level TER, character, soft-word, or differential tests.
Those belong to `text-post-edit-metrics`.

Run:

```bash
make test PACKAGE=study-posting-ai-analysis
make coverage PACKAGE=study-posting-ai-analysis
make check
```

## Documentation

The specification of record is:

```text
python/packages/study-posting-ai-analysis/docs/analysis-specification.md
```

Update it alongside changes to:

- requiredness;
- field configuration;
- outcome classification;
- cosmetic equivalence;
- compensation policy;
- lookup policy;
- policy-adjusted scoring;
- flattened output.

The technical metric implementation is documented primarily by
`python/packages/text-post-edit-metrics/README.md`, while the study specification
retains the formulas needed to interpret study reports.
