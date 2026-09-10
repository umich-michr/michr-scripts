# study-posting-ai-analysis

Analyzes AI suggestions, user selections, and final saved values for the
University of Michigan eResearch study-posting form.

Given three objects—suggested, selected, and final—the package returns one
structured result per configured field.

```python
from study_posting_ai_analysis import analyze_objects

results = analyze_objects(
    suggested_object,
    selected_object,
    final_object,
)
```

The package answers questions such as:

- Was a suggestion offered and selected?
- Was selected text retained, cosmetically changed, substantively edited, or
  removed?
- How much technical text post-editing was required?
- Were selected lookup IDs retained?
- Was the suggested compensation Boolean retained?

These results describe realized assistance and textual transformation. They do
not directly measure time, cognition, observed keystrokes, semantic equivalence,
user satisfaction, or overall usefulness.

## Contract

Inputs represent:

| Input | Meaning |
|---|---|
| Suggested object | Suggestions and values offered by the AI |
| Selected object | Suggestions or lookup IDs selected by the user |
| Final object | Values ultimately saved in the study posting |

The primary API is:

```python
results = analyze_objects(
    suggested_object,
    selected_object,
    final_object,
)
```

The result dictionary contains one structured analysis result per configured
field.

The package can also:

- decode JSON strings or UTF-8 bytes into the three objects;
- flatten structured analysis results into canonical tabular dictionaries.

## Responsibilities

The package owns:

- study-posting field configuration;
- field requiredness;
- suggestion-selection validation;
- text outcome classification;
- cosmetic-equivalence policy;
- contact analysis;
- compensation text and Boolean analysis;
- lookup and Jaccard analysis;
- JSON-object parsing;
- canonical flattened rows;
- study-specific policy scores and result models.

It performs no:

- database or SQL access;
- audit-row selection;
- CSV or filesystem I/O;
- DataFrame construction;
- logging;
- command-line processing;
- batch iteration;
- aggregation or report publication.

Those responsibilities belong to consuming programs.

## Metric dependency

Generic technical text metrics belong to
[`text-post-edit-metrics`](../text-post-edit-metrics/):

```text
text-post-edit-metrics
          ↑
study-posting-ai-analysis
```

For selected, nonblank text, this package delegates to:

```python
from text_post_edit_metrics import analyze_post_edit

metrics = analyze_post_edit(
    suggestion=selected_text,
    final=final_text,
)
```

It does not reimplement:

- TER;
- character-level Levenshtein metrics;
- weighted soft-word metrics;
- generic metric normalization;
- `PostEditingResult`.

See the generic metric
[methodology](../text-post-edit-metrics/docs/methodology.md)
and
[verification documentation](../text-post-edit-metrics/docs/verification.md).

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

print("Outcome:", title.match)
print("TER-derived score:", title.ter_effort_saved)
print("Policy score:", title.policy_adjusted_effort_saved)

rows = flatten_analysis_results(
    results,
    record_id="synthetic-record",
)
```

A caller that already has dictionaries can call `analyze_objects()` directly.

## Parsing

Decode all three inputs:

```python
from study_posting_ai_analysis import parse_analysis_inputs

suggested, selected, final = parse_analysis_inputs(
    suggested_payload,
    selected_payload,
    final_payload,
)
```

`parse_analysis_inputs()` and `parse_json_object()` accept:

- JSON strings;
- UTF-8 bytes;
- already-decoded dictionaries.

They reject:

- missing values;
- blank strings;
- invalid UTF-8;
- malformed JSON;
- valid JSON values that are not objects.

Malformed input raises `InputParseError`, a `ValueError` subtype.

Source-column names, record identifiers, row selection, and source-schema
mapping belong to the consuming program.

## Analysis overview

The package analyzes four broad result families.

### Text fields

Text outcomes are:

| Outcome | Meaning |
|---|---|
| `EXACT` | Selected and final strings are exactly equal |
| `COSMETIC_EQUIVALENT` | They differ but are equal under study cosmetic policy |
| `EDITED` | Selected and nonblank final text differ substantively |
| `REMOVED` | A selected optional suggestion was cleared |
| `UNASSISTED` | No AI suggestion was selected |

For selected, nonblank outcomes, `editing_metrics` contains a generic
`PostEditingResult`.

For `REMOVED` and `UNASSISTED`, `editing_metrics` is `None`.

Field identity remains in:

- the result-dictionary key;
- `Pick.kind`;
- flattened `field_name`.

The detailed classification order, requiredness rules, cosmetic transformation,
and policy-adjusted scores are specified in
[`docs/analysis-specification.md`](docs/analysis-specification.md).

### Contact

The top-level contact object expands into:

- `contact.email`;
- `contact.name`;
- `contact.phone`;
- `contact.website`.

Each subfield is analyzed independently under its configured requiredness and
selection rules.

### Compensation

Compensation analysis reports text behavior separately from the suggested and
saved `offersCompensation` Boolean.

It preserves distinctions among:

- whether compensation was suggested;
- whether it was saved;
- whether the Boolean recommendation was accepted or changed;
- whether compensation text was required;
- how selected compensation text was edited.

### Lookup fields

Lookup fields are:

- `department`;
- `locations`;
- `topics`.

They use integer IDs and assisted Jaccard similarity. Lookup similarity is
reported separately from text effort-saved metrics.

Detailed contact, compensation, and lookup policy is authoritative in the
[analysis specification](docs/analysis-specification.md).

## Flattened output

Flatten structured results for tabular consumers:

```python
from study_posting_ai_analysis import flatten_analysis_results

rows = flatten_analysis_results(
    results,
    record_id="synthetic-record",
    include_text=False,
)
```

The function returns:

```python
list[dict[str, object]]
```

Every row:

- contains every name in `FLATTENED_COLUMNS`;
- preserves canonical column order;
- contains only `None`, `bool`, `int`, `float`, or `str`;
- excludes selected and final free text by default.

Lookup ID sets are serialized as sorted JSON arrays. Lookup rows leave
text-specific metrics and policy columns as `None`.

`FLATTENED_COLUMNS` is a published contract. Adding, removing, or renaming a
column requires compatibility review and documentation updates.

The package does not write CSV files. File and report output belongs to the
consumer.

## Public API

| Name | Purpose |
|---|---|
| `analyze_objects()` | Analyze all configured study-posting fields |
| `analyze_text_field()` | Analyze one ordinary text field |
| `analyze_contact()` | Analyze contact subfields |
| `analyze_compensation()` | Analyze compensation text and Boolean policy |
| `analyze_lookup_values()` | Analyze offered, picked, and saved lookup IDs |
| `compare_selected_text()` | Classify selected text against the final value |
| `parse_analysis_inputs()` | Decode the three analysis inputs |
| `parse_json_object()` | Decode one JSON object |
| `flatten_analysis_results()` | Produce canonical flat rows |
| `FLATTENED_COLUMNS` | Canonical flattened column names |
| `FIELD_SPECS` | Configured study-posting fields |
| `CONTACT_FIELDS` | Configured contact subfields |
| `REQUIRED_CONTACT_FIELDS` | Required contact subfields |
| `COMPENSATION_KINDS` | Compensation suggestion categories |

Technical metric functions and `PostEditingResult` remain owned by
`text-post-edit-metrics` and are not re-exported here.

## Reporting guidance

Different result families answer different questions and must not be combined
indiscriminately.

In particular:

- report every mean with its denominator or sample count;
- distinguish offered fields from selected fields;
- distinguish study policy scores from technical metric scores;
- keep lookup similarity separate from text effort-saved scores;
- keep compensation-Boolean acceptance separate from compensation-text
  metrics.

The authoritative reporting vocabulary and interpretation limits are in
[`docs/analysis-specification.md`](docs/analysis-specification.md).

## Documentation

| Document | Ownership |
|---|---|
| [`docs/analysis-specification.md`](docs/analysis-specification.md) | Study methodology, fields, policy, scores, reporting vocabulary, and interpretation |
| [`docs/program-flow.md`](docs/program-flow.md) | Analysis control flow and module boundaries |
| [`../text-post-edit-metrics/README.md`](../text-post-edit-metrics/README.md) | Generic metric API |
| [`../text-post-edit-metrics/docs/methodology.md`](../text-post-edit-metrics/docs/methodology.md) | Generic metric methodology |
| [`../text-post-edit-metrics/docs/verification.md`](../text-post-edit-metrics/docs/verification.md) | Generic metric verification |

If implementation and the study specification disagree, either implementation
is incorrect or the specification must be amended in the same change.

## Data handling

- Free text is excluded from flattened rows unless `include_text=True`.
- The library performs no logging.
- Tests and examples use synthetic content.
- Do not commit real study content, production identifiers, credentials, or
  database exports.
- Consumers are responsible for appropriate source and output controls.

## Reproducibility

Exact dependency versions are recorded in the repository root `uv.lock`.

For archived analysis, record:

- Python and package versions;
- analysis date;
- Git revision;
- record and field-instance counts;
- inclusion and exclusion rules;
- every aggregate denominator.

## Development

Run from the repository root:

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

See the [root README](../../../README.md) for workspace-wide guidance.

## License

MIT
