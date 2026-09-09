# study-posting-ai-analysis

Analyzes AI suggestions, user selections, and final saved values for the
University of Michigan eResearch study-posting form.

Given three objects—suggested, selected, and final—the package returns one
structured analysis result per configured field.

It answers questions such as:

- Was a suggestion offered?
- Was an offered suggestion selected?
- Was selected text retained exactly, changed cosmetically, substantively
  edited, or removed?
- How much technical text post-editing was required?
- Were selected lookup IDs retained?
- Was the suggested compensation Boolean retained?

> These results describe technical textual post-editing and realized
> assistance. They do not directly measure elapsed time, cognitive effort,
> observed keystrokes, semantic equivalence, user satisfaction, or overall
> usefulness.

The
[analysis specification](docs/analysis-specification.md)
is the authoritative source for study policy and interpretation.

---

## Package contract

Three objects in:

```python
results = analyze_objects(
    suggested_object,
    selected_object,
    final_object,
)
```

One structured result per analyzed field out:

```python
title = results["title"]

print(title.match)
print(title.ter_effort_saved)
print(title.policy_adjusted_effort_saved)
```

The inputs represent:

| Input | Meaning |
|---|---|
| `suggested_object` | Text suggestions, lookup IDs, contact values, compensation suggestions, and the suggested compensation Boolean offered by the AI |
| `selected_object` | Suggestions and lookup IDs selected or applied by the user |
| `final_object` | Values ultimately saved in the study posting |

The package can optionally decode the three objects from JSON strings or UTF-8
bytes.

It performs no:

- database or SQL access;
- audit-record eligibility filtering;
- CSV or filesystem I/O;
- DataFrame construction;
- logging;
- command-line processing;
- batch iteration;
- report aggregation or publication.

Those responsibilities belong to consuming packages and programs.

---

## Dependency boundary

Technical text metrics are implemented by the sibling
[`text-post-edit-metrics`](../text-post-edit-metrics/) package.

```text
text-post-edit-metrics
          ↑
study-posting-ai-analysis
```

This package owns:

- study-posting field configuration;
- field requiredness;
- suggestion-selection validation;
- outcome classification;
- cosmetic-equivalence policy;
- contact and compensation behavior;
- lookup and Jaccard analysis;
- JSON-object parsing;
- flattened study-analysis rows.

It does not implement:

- TER;
- character-level Levenshtein distance;
- weighted soft-word distance;
- generic metric normalization.

Canonical generic metric documentation:

- [methodology](../text-post-edit-metrics/docs/methodology.md);
- [verification](../text-post-edit-metrics/docs/verification.md).

---

## Basic usage

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

results = analyze_objects(
    suggested,
    selected,
    final,
)

title = results["title"]

print("Match:", title.match)
print("TER-derived score:", title.ter_effort_saved)
print("Policy score:", title.policy_adjusted_effort_saved)

rows = flatten_analysis_results(
    results,
    record_id="audit-1234",
)
```

`parse_analysis_inputs()` accepts:

- JSON strings;
- UTF-8 bytes;
- already-decoded dictionaries.

A caller that already has dictionaries may call `analyze_objects()` directly.

---

## Text analysis

For selected, nonblank text, the package calls:

```python
from text_post_edit_metrics import analyze_post_edit
```

The returned `PostEditingResult` is stored in:

```python
text_result.editing_metrics
```

Field identity is not duplicated inside `PostEditingResult`. It remains in:

- the result-dictionary key;
- `Pick.kind` when a suggestion was selected;
- `field_name` in flattened output.

For example:

```python
title = results["title"]

title.match
title.pick
title.editing_metrics
title.ter_effort_saved
title.policy_adjusted_effort_saved
```

Callers comparing two texts independently should use the generic package
directly:

```python
from text_post_edit_metrics import analyze_post_edit

metrics = analyze_post_edit(
    suggestion="Initial text",
    final="Represented edited text",
)
```

---

## Outcome classification

### Text outcomes

| Outcome | Meaning |
|---|---|
| `EXACT` | Selected and final strings are exactly equal |
| `COSMETIC_EQUIVALENT` | Strings differ but become equal under the study cosmetic transformation |
| `EDITED` | Selected and nonblank final text differ substantively |
| `REMOVED` | A suggestion was selected for an optional field, then the final value was cleared |
| `UNASSISTED` | No AI suggestion was selected |

Classification order is:

```text
blank → exact → cosmetic-equivalent → edited
```

For `EXACT`, `COSMETIC_EQUIVALENT`, and `EDITED`,
`editing_metrics` contains a `PostEditingResult`.

For `REMOVED` and `UNASSISTED`, `editing_metrics` is `None`.

### Policy-adjusted text score

| Outcome | Score |
|---|---:|
| `EXACT` | `1.0` |
| `COSMETIC_EQUIVALENT` | `1.0` |
| `EDITED` | Bounded TER-derived score |
| `REMOVED` | `0.0` |
| `UNASSISTED` | `0.0` |

This is a study-product policy score, not a standardized TER result.

---

## Cosmetic equivalence

The cosmetic-equivalence transformation applies:

1. Unicode NFKD decomposition;
2. Unicode-aware case folding;
3. combining-mark removal;
4. punctuation and symbol replacement with spaces;
5. whitespace collapsing and trimming.

It is used only for classification.

Cosmetically transformed text is never passed to the technical metrics because
doing so would hide actual edits. The original selected and final strings are
passed to `text_post_edit_metrics.analyze_post_edit()`.

---

## Required fields

| Field | Rule |
|---|---|
| `title` | Required |
| `purpose` | Required |
| `description` | Required |
| `about` | Optional |
| `contact.email` | Required |
| `contact.name` | Required |
| `contact.phone` | Optional |
| `contact.website` | Optional |
| Compensation text | Required when final `offersCompensation` is `True` |
| `offersCompensation` | Must be saved as `True` or `False` |

A blank required value raises `ValueError`. It is not represented as a score of
zero.

A selected suggestion cleared from an optional field is `REMOVED`.

An optional blank field with no selection is `UNASSISTED`.

---

## Contact analysis

The top-level `contact` object expands into four separately reported fields:

- `contact.email`;
- `contact.name`;
- `contact.phone`;
- `contact.website`.

Each contact subfield offers at most one suggestion.

A selected contact value must have been offered and must equal the offered value
before final editing.

Unknown contact fields are rejected.

---

## Compensation analysis

Compensation combines:

- categorized compensation-text suggestions;
- the suggested `offersCompensation` Boolean;
- the final saved Boolean;
- final compensation text.

Text categories:

- `genericCompensation`;
- `specificCompensation`.

At most one text suggestion may be selected across both categories.

The result reports:

| Field | Meaning |
|---|---|
| `flag_suggested` | AI-recommended Boolean, if available |
| `flag_saved` | Final saved Boolean |
| `flag_accepted` | Whether saved matched suggested |
| `flag_changed` | Whether saved differed from suggested |
| `compensation_text_required` | Whether final saved Boolean requires text |

Boolean acceptance and text post-editing are separate outcomes.

Examples:

| Scenario | Text outcome |
|---|---|
| AI suggested `False`; user saved `True` and wrote text independently | `UNASSISTED` |
| User selected text, saved `False`, and cleared text | `REMOVED` |

---

## Lookup analysis

Lookup fields are:

- `department`;
- `locations`;
- `topics`.

Values are integer IDs. Booleans are rejected because `bool` is a subclass of
`int`.

Every picked ID must have been offered.

For assisted outcomes:

```text
lookup_similarity =
    |picked ∩ saved| / |picked ∪ saved|
```

The result also reports:

- `offered`;
- `picked`;
- `saved`;
- `kept`;
- `dropped`;
- `added`;
- `saved_not_offered`.

When nothing was picked:

- outcome = `UNASSISTED`;
- similarity = study-policy value `0.0`;
- no empty-set Jaccard calculation is performed.

Lookup similarity must not be averaged with text effort-saved scores.

---

## Parsing

### `parse_json_object()`

Accepts:

- JSON strings;
- UTF-8 bytes;
- already-decoded dictionaries.

Rejects:

- missing values;
- blank strings;
- invalid UTF-8;
- malformed JSON;
- valid JSON values that are not objects.

Malformed input raises `InputParseError`, which subclasses `ValueError`.

### `parse_analysis_inputs()`

Applies the same behavior to all three analysis inputs:

```python
suggested, selected, final = parse_analysis_inputs(
    suggested_payload,
    selected_payload,
    final_payload,
)
```

Database column names, row identifiers, eligibility rules, and source-schema
mapping belong to the consuming program.

---

## Flattened output

`flatten_analysis_results()` returns:

```python
list[dict[str, object]]
```

It produces one row per analyzed field:

```python
rows = flatten_analysis_results(
    results,
    record_id="audit-1234",
    include_text=False,
)
```

Every row:

- contains every name in `FLATTENED_COLUMNS`;
- preserves canonical column order;
- contains only `None`, `bool`, `int`, `float`, or `str`;
- excludes selected and final free text by default.

Lookup ID sets are serialized as sorted JSON arrays.

Lookup rows leave text-metric and policy-adjusted text columns as `None`.

`FLATTENED_COLUMNS` is a published contract. Adding, removing, or renaming a
column requires documentation and compatibility review.

### Writing CSV is a consumer responsibility

```python
import csv

from study_posting_ai_analysis import FLATTENED_COLUMNS

with open("analysis.csv", "w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=FLATTENED_COLUMNS,
    )
    writer.writeheader()
    writer.writerows(rows)
```

The library itself does not open or write files.

---

## Public API

| Name | Purpose |
|---|---|
| `analyze_objects()` | Analyze all configured fields |
| `analyze_text_field()` | Analyze one ordinary text field |
| `analyze_contact()` | Analyze contact subfields |
| `analyze_compensation()` | Analyze compensation text and Boolean policy |
| `analyze_lookup_values()` | Analyze offered, picked, and saved lookup IDs |
| `compare_selected_text()` | Classify selected text against its final value |
| `parse_analysis_inputs()` | Decode the three JSON inputs |
| `parse_json_object()` | Decode one JSON object |
| `flatten_analysis_results()` | Convert structured results to flat rows |
| `FLATTENED_COLUMNS` | Canonical flattened output columns |
| `FIELD_SPECS` | Configured study-posting fields |
| `CONTACT_FIELDS` | Configured contact subfields |
| `REQUIRED_CONTACT_FIELDS` | Required contact subfields |
| `COMPENSATION_KINDS` | Compensation suggestion categories |

Technical text metrics and `PostEditingResult` are imported from
`text_post_edit_metrics`, not re-exported by this package.

---

## Reporting guidance

Report statistics separately because they answer different questions and use
different denominators.

| Statistic | Denominator | Recommended label |
|---|---|---|
| Fields with an offer | All analyzed text fields | Suggestion offer coverage |
| Fields with a selection | Text fields with an offer | Suggestion selection rate |
| Mean policy score among offered fields | Offered text fields | Realized suggestion utility |
| Mean policy score among selected fields | Selected text fields | Selected-suggestion utility |
| Mean bounded TER-derived score | Selected suggestions with nonblank final values | TER-derived post-editing score |

Always report the denominator or sample count with a mean.

Do not:

- describe an all-text-fields average simply as “effort saved”;
- combine lookup similarity with text effort-saved scores;
- combine compensation-Boolean acceptance with compensation-text metrics.

---

## Architecture

```text
src/study_posting_ai_analysis/
├── __init__.py
├── errors.py             InputParseError
├── field_analysis.py     Field classification and analyzers
├── field_specs.py        Field configuration and requiredness
├── flattening.py         Structured results to tabular rows
├── models.py             Study-specific result models
├── parsing.py            JSON-object decoding
├── text_normalization.py Cosmetic equivalence and blank-text policy
├── validation.py         Runtime checks at trust boundaries
└── py.typed              PEP 561 typing marker
```

Text metrics are delegated:

```text
study-posting-ai-analysis
          │
          └── text-post-edit-metrics
                ├── TER
                ├── character Levenshtein metrics
                ├── weighted soft-word metrics
                ├── metric normalization
                └── PostEditingResult
```

---

## Development

Run commands from the repository root.

```bash
make test PACKAGE=study-posting-ai-analysis
make coverage PACKAGE=study-posting-ai-analysis
```

Run a focused subset:

```bash
make test \
  PACKAGE=study-posting-ai-analysis \
  PYTEST_ARGS="-k compensation -vv"
```

Run the complete workspace gate:

```bash
make check
```

Shared setup, contribution, CI, and workspace guidance are documented in the
[root README](../../../README.md).

---

## Documentation

| Document | Purpose |
|---|---|
| [`docs/analysis-specification.md`](docs/analysis-specification.md) | Specification of record for study methodology and field policy |
| [`docs/program-flow.md`](docs/program-flow.md) | Study-analysis control-flow diagrams |
| [`../text-post-edit-metrics/README.md`](../text-post-edit-metrics/README.md) | Generic metric API overview |
| [`../text-post-edit-metrics/docs/methodology.md`](../text-post-edit-metrics/docs/methodology.md) | Canonical generic metric methodology |
| [`../text-post-edit-metrics/docs/verification.md`](../text-post-edit-metrics/docs/verification.md) | Canonical generic metric verification |
| [`../../../README.md`](../../../README.md) | Repository organization and workflow |

If implementation and the study specification disagree, either implementation
is wrong or the specification must be amended in the same change.

---

## Data handling

- Free text is excluded from flattened rows unless `include_text=True`.
- The library never logs.
- Tests and examples use synthetic content.
- Real study content, production identifiers, credentials, and database exports
  must not appear in tests or documentation.
- Consumers are responsible for appropriate handling of source and output data.

---

## Reproducibility

| Component | Version |
|---|---|
| Python | 3.14 |
| `study-posting-ai-analysis` | 0.1.x |
| `text-post-edit-metrics` | 0.1.x |
| SacreBLEU | 2.6.x, owned by `text-post-edit-metrics` |
| RapidFuzz | 3.14.x, owned by `text-post-edit-metrics` |

Exact resolved versions are recorded in the repository root `uv.lock`.

For published or archived analysis, record:

- Python and package versions;
- analysis date;
- Git revision;
- record and field-instance counts;
- inclusion and exclusion rules;
- every aggregate denominator.

---

## License

MIT
