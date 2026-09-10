# Study-posting analysis flow

This document describes the control flow and package boundaries of
`study-posting-ai-analysis`.

For authoritative field policy, requiredness, formulas, outcome definitions,
reporting terminology, and interpretation, see
[`analysis-specification.md`](analysis-specification.md).

Generic text calculations are implemented by
[`text-post-edit-metrics`](../../text-post-edit-metrics/).

## 1. Package boundary

The package is a pure, one-record analysis library:

```text
suggested object
selected object
final object
        ↓
study-posting-ai-analysis
        ↓
structured field results
        ↓
optional flattened dictionaries
```

It performs no:

- database or SQL access;
- audit-row selection;
- CSV or filesystem I/O;
- batch iteration;
- aggregation;
- logging;
- command-line handling;
- report publication.

A consuming program owns those responsibilities.

```mermaid
flowchart LR
    subgraph Consumer["Consuming program"]
        SOURCE["CSV, database,<br/>or another source"]
        SELECT["Record selection and<br/>source-column mapping"]
        HANDLE["Batch policy,<br/>aggregation, output"]
    end

    subgraph Study["study-posting-ai-analysis"]
        PARSE["parse_analysis_inputs()<br/>optional JSON decoding"]
        ANALYZE["analyze_objects()<br/>validate and analyze"]
        FLATTEN["flatten_analysis_results()<br/>one row per field"]
    end

    SOURCE --> SELECT --> PARSE
    PARSE --> ANALYZE --> FLATTEN
    FLATTEN --> HANDLE
```

The library raises exceptions and never logs.

## 2. End-to-end analysis

The public composition path is:

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

rows = flatten_analysis_results(
    results,
    record_id="synthetic-record",
    include_text=False,
)
```

A caller that already has validated dictionaries may skip decoding and call
`analyze_objects()` directly.

```mermaid
flowchart TB
    PAYLOADS["Suggested, selected,<br/>and final payloads"]
    PARSE["Optional JSON-object decoding"]
    KEYS["Validate object types<br/>and configured fields"]
    DISPATCH["Dispatch by FieldKind"]
    SPECIALIZED["Text, contact, compensation,<br/>and lookup analyzers"]
    RESULTS["dict[str, AnalysisResult]"]
    FLATTEN["Optional flattening"]
    ROWS["list[dict[str, object]]"]

    PAYLOADS --> PARSE --> KEYS --> DISPATCH
    DISPATCH --> SPECIALIZED --> RESULTS
    RESULTS --> FLATTEN --> ROWS
```

## 3. Input decoding

`parse_json_object()` accepts:

- a JSON string;
- UTF-8 bytes;
- an already-decoded dictionary.

```mermaid
flowchart TB
    INPUT["Input value"]
    MISSING{"Missing?"}
    BYTES{"Bytes?"}
    DECODE["Decode UTF-8"]
    STRING{"String?"}
    BLANK{"Blank?"}
    JSON["json.loads()"]
    OBJECT{"Dictionary?"}
    RESULT["Fresh dict[str, object]"]

    INPUT --> MISSING
    MISSING -->|Yes| E_MISSING["InputParseError"]
    MISSING -->|No| BYTES

    BYTES -->|Yes| DECODE
    DECODE -->|Invalid| E_UTF8["InputParseError"]
    DECODE -->|Valid| STRING
    BYTES -->|No| STRING

    STRING -->|Yes| BLANK
    BLANK -->|Yes| E_BLANK["InputParseError"]
    BLANK -->|No| JSON
    JSON -->|Malformed| E_JSON["InputParseError"]
    JSON -->|Decoded| OBJECT

    STRING -->|No| OBJECT
    OBJECT -->|No| E_OBJECT["InputParseError"]
    OBJECT -->|Yes| RESULT
```

Valid JSON values that are not objects are rejected.

`parse_analysis_inputs()` applies this behavior independently to the suggested,
selected, and final payloads.

## 4. Top-level field dispatch

`analyze_objects()` validates top-level fields against `FIELD_SPECS`.

Unknown fields are rejected so a source or form change cannot be silently
ignored.

```mermaid
flowchart TB
    INPUTS["Suggested, selected,<br/>and final objects"]
    VALIDATE["Validate object types<br/>and configured keys"]
    UNKNOWN{"Unknown field?"}
    KIND{"FieldKind"}

    INPUTS --> VALIDATE --> UNKNOWN
    UNKNOWN -->|Yes| ERROR["ValueError"]
    UNKNOWN -->|No| KIND

    KIND -->|TEXT| TEXT["analyze_text_field()"]
    KIND -->|CONTACT| CONTACT["analyze_contact()"]
    KIND -->|COMPENSATION| COMP["analyze_compensation()"]
    KIND -->|LOOKUP| LOOKUP["analyze_lookup_values()"]
    KIND -->|MERGED| MERGED["Handled within another result"]

    TEXT --> RESULTS["dict[str, AnalysisResult]"]
    CONTACT --> RESULTS
    COMP --> RESULTS
    LOOKUP --> RESULTS
```

`offersCompensation` is a merged field represented within the compensation
result rather than as an independent result.

The contact object expands into four separately reported results:

```text
contact.email
contact.name
contact.phone
contact.website
```

A complete valid analysis produces twelve field results.

Field definitions and requiredness are authoritative in the
[analysis specification](analysis-specification.md).

## 5. Shared text-analysis path

Ordinary text, contact text, and selected compensation text use the same
comparison path.

```mermaid
flowchart TB
    START["Validate offered, selected,<br/>and final values"]
    SELECTED{"Suggestion selected?"}
    VALID_SELECTION["Confirm selected value<br/>was offered"]
    FINAL["Validate final requiredness"]
    COMPARE["compare_selected_text()"]
    OUTCOME{"Text outcome"}

    START --> SELECTED

    SELECTED -->|No| FINAL
    FINAL -->|Invalid| E_REQUIRED["ValueError"]
    FINAL -->|Valid| UNASSISTED["UNASSISTED<br/>no editing metrics"]

    SELECTED -->|Yes| VALID_SELECTION
    VALID_SELECTION -->|Invalid| E_SELECTION["ValueError"]
    VALID_SELECTION -->|Valid| COMPARE

    COMPARE --> OUTCOME
    OUTCOME -->|Blank optional final| REMOVED["REMOVED<br/>no editing metrics"]
    OUTCOME -->|Exact| EXACT["EXACT"]
    OUTCOME -->|Cosmetic equivalent| COSMETIC["COSMETIC_EQUIVALENT"]
    OUTCOME -->|Otherwise| EDITED["EDITED"]

    EXACT --> METRICS["analyze_post_edit()"]
    COSMETIC --> METRICS
    EDITED --> METRICS
    METRICS --> RESULT["PostEditingResult attached<br/>to field result"]
```

The classification order and outcome meanings are defined in the
[analysis specification](analysis-specification.md#5-outcome-vocabulary).

Selected, nonblank outcomes receive generic editing metrics. `REMOVED` and
`UNASSISTED` do not.

## 6. Generic metric delegation

The study package decides whether a generic text comparison is appropriate.
`text-post-edit-metrics` performs the calculation.

```mermaid
flowchart LR
    subgraph Study["study-posting-ai-analysis"]
        CLASSIFY["Validate and classify<br/>selected study text"]
        ATTACH["Attach PostEditingResult<br/>to field result"]
    end

    subgraph Metrics["text-post-edit-metrics"]
        ANALYZE["analyze_post_edit()<br/>suggestion → final"]
        RESULT["TER, character,<br/>soft-word, counts"]
    end

    CLASSIFY -->|"Selected and nonblank"| ANALYZE
    ANALYZE --> RESULT --> ATTACH
```

The argument direction is:

```text
suggestion = selected or applied AI text
final      = final saved text
```

The study package contains no TER, character-distance, or weighted soft-word
implementation.

`PostEditingResult` contains no study field name. Field identity remains in:

- the result-dictionary key;
- `Pick.kind`;
- flattened `field_name`.

Study cosmetic normalization is used only for outcome classification. The
original selected and final strings are passed to `analyze_post_edit()`.

## 7. Specialized analyzers

### Contact

`analyze_contact()`:

1. validates the suggested, selected, and final contact objects;
2. rejects unknown subfields;
3. validates each selected contact value against the offered value;
4. applies the shared text-analysis path independently to each contact
   subfield;
5. returns four `TextFieldAnalysis` results.

### Compensation

`analyze_compensation()`:

1. validates categorized text suggestions;
2. validates the suggested and saved compensation Booleans;
3. enforces compensation-text requiredness from the saved Boolean;
4. applies the shared text-analysis path when text was selected;
5. returns one `CompensationAnalysis`.

Boolean acceptance and text editing remain separate result dimensions.

### Lookup fields

`analyze_lookup_values()`:

1. validates offered, picked, and saved integer IDs;
2. rejects Boolean values;
3. confirms every picked ID was offered;
4. derives retained, dropped, added, and saved-not-offered sets;
5. classifies the outcome;
6. calculates assisted Jaccard similarity when applicable;
7. returns `LookupValueAnalysis`.

Lookup similarity remains separate from text effort-saved metrics.

Detailed specialized policy is authoritative in the
[analysis specification](analysis-specification.md).

## 8. Flattening

`flatten_analysis_results()` converts structured field results into canonical
tabular dictionaries.

```mermaid
flowchart TB
    RESULTS["dict[str, AnalysisResult]"]
    EACH["For each field result"]
    TEMPLATE["Initialize every<br/>FLATTENED_COLUMNS entry"]
    TYPE{"Result type"}

    RESULTS --> EACH --> TEMPLATE --> TYPE

    TYPE -->|Text| TEXT["Populate text outcome,<br/>policy, and metrics"]
    TYPE -->|Compensation| COMP["Populate text plus<br/>Boolean fields"]
    TYPE -->|Lookup| LOOKUP["Populate similarity and<br/>serialized ID sets"]

    TEXT --> PRIVACY{"include_text?"}
    COMP --> PRIVACY
    PRIVACY -->|Yes| INCLUDE["Include selected<br/>and final text"]
    PRIVACY -->|No| OMIT["Leave text columns None"]

    INCLUDE --> ROW["Canonical flat row"]
    OMIT --> ROW
    LOOKUP --> ROW
```

Every flattened row:

- contains every name in `FLATTENED_COLUMNS`;
- preserves canonical column order;
- contains only `None`, `bool`, `int`, `float`, or `str`;
- excludes selected and final text unless `include_text=True`.

Lookup sets are serialized as sorted JSON arrays. Lookup rows leave
text-specific metric and policy columns as `None`.

The consuming program owns file output and data-handling controls.

## 9. Errors

The library raises and never logs.

| Condition | Exception |
|---|---|
| Missing, blank, malformed, or non-object JSON | `InputParseError` |
| Wrong runtime type | `TypeError` |
| Requiredness or study-policy violation | `ValueError` |
| Unknown field | `ValueError` |
| Selected value that was not offered | `ValueError` |

A consuming program decides whether an invalid record:

- aborts processing;
- is recorded and skipped;
- is sent for review.

Record IDs, logging, batch policy, and report publication remain outside this
package.
