# Study-posting analysis flow

`study-posting-ai-analysis` is a pure, one-record analysis library.

For authoritative field policy and interpretation, see
[`analysis-specification.md`](analysis-specification.md). Generic text metrics
belong to [`text-post-edit-metrics`](../../text-post-edit-metrics/).

## Boundary

```text
suggested object
selected object
final object
        ↓
optional JSON decoding
        ↓
study-posting-ai-analysis
        ↓
structured field results
        ↓
optional flattened dictionaries
```

The consuming program owns source access, row selection, identifiers, batch
policy, aggregation, logging, and publication.

## Public composition

```python
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

A caller with dictionaries can skip decoding.

## Dispatch

`analyze_objects()` rejects unknown top-level fields and dispatches configured
fields by kind:

```text
ordinary text  → analyze_text_field()
contact        → analyze_contact()
compensation   → analyze_compensation()
lookup         → analyze_lookup_values()
```

Contact expands to email, name, phone, and website. `offersCompensation` is
reported within the compensation result.

## Shared text path

```text
validate offer, selection, final requiredness
        ↓
no selected suggestion → UNASSISTED
selected + blank optional final → REMOVED
selected + exact final → EXACT
selected + cosmetic equivalent → COSMETIC_EQUIVALENT
selected + other nonblank final → EDITED
        ↓
selected and nonblank
        ↓
text_post_edit_metrics.analyze_post_edit()
```

Study cosmetic normalization is classification-only. Original selected and final
strings are passed to generic metrics.

## Specialized paths

### Contact

Validates recognized contact subfields and applies the shared text path to each.

### Compensation

Validates categorized suggestions and the suggested/final compensation Boolean.
Boolean acceptance and text editing remain separate.

### Lookup

Validates integer IDs, rejects Booleans, confirms picks were offered, derives
kept/dropped/added sets, classifies outcome, and calculates assisted Jaccard
similarity.

## Flattening

`flatten_analysis_results()` creates one row per field:

- all `FLATTENED_COLUMNS` are present in canonical order;
- text is omitted unless `include_text=True`;
- lookup sets are sorted JSON arrays;
- text-only columns remain missing on lookup rows.

The consuming program owns file output and data controls.

## Errors

The library raises and never logs.

| Condition | Error |
|---|---|
| Missing, blank, malformed, or non-object JSON | `InputParseError` |
| Wrong runtime type | `TypeError` |
| Requiredness or policy violation | `ValueError` |
| Unknown field or unoffered selection | `ValueError` |
