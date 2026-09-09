# Study-posting analysis flow

This document describes the control flow of `study-posting-ai-analysis`.

For authoritative business rules, formulas, interpretation, and reporting
terminology, see
[`analysis-specification.md`](analysis-specification.md).

Technical text calculations are implemented by the sibling
[`text-post-edit-metrics`](../../text-post-edit-metrics/) package.

Mermaid diagrams render natively on GitHub and in VS Code with Mermaid-enabled
Markdown preview.

---

## 1. Package boundary

`study-posting-ai-analysis` is a pure library. It receives three objects and
returns structured field results or flattened dictionaries.

```mermaid
flowchart LR
    subgraph Consumer["Consuming program"]
        SOURCE["Database, CSV, HTTP,<br/>or another source"]
        SELECT["Eligibility and<br/>source-column mapping"]
        HANDLE["Record loop,<br/>error handling,<br/>aggregation, output"]
    end

    subgraph Study["study-posting-ai-analysis"]
        PARSE["parse_analysis_inputs()<br/>optional JSON decoding"]
        ANALYZE["analyze_objects()<br/>validate and analyze fields"]
        FLATTEN["flatten_analysis_results()<br/>one dictionary per field"]
    end

    SOURCE --> SELECT --> PARSE
    PARSE --> ANALYZE --> FLATTEN
    FLATTEN --> HANDLE
```

The consuming program owns:

- database and file access;
- audit-row eligibility;
- source-column mapping;
- record identifiers;
- batch iteration;
- logging and failure policy;
- aggregation and report writing.

The library raises exceptions and never logs.

---

## 2. Input decoding

`parse_json_object()` accepts:

- a JSON string;
- UTF-8 bytes;
- an already-decoded dictionary.

```mermaid
flowchart TB
    INPUT["Input value"]
    MISSING{"Missing?"}
    BYTES{"Bytes?"}
    UTF8["Decode as UTF-8"]
    STRING{"String?"}
    BLANK{"Blank?"}
    JSON["json.loads()"]
    OBJECT{"Dictionary?"}
    RESULT["dict[str, object]"]

    INPUT --> MISSING
    MISSING -->|Yes| E_MISSING["InputParseError<br/>value is missing"]
    MISSING -->|No| BYTES

    BYTES -->|Yes| UTF8
    UTF8 -->|Invalid| E_UTF8["InputParseError<br/>invalid UTF-8"]
    UTF8 -->|Valid| STRING
    BYTES -->|No| STRING

    STRING -->|Yes| BLANK
    BLANK -->|Yes| E_BLANK["InputParseError<br/>value is blank"]
    BLANK -->|No| JSON
    JSON -->|Malformed| E_JSON["InputParseError<br/>line and column reported"]
    JSON -->|Decoded| OBJECT

    STRING -->|No| OBJECT
    OBJECT -->|No| E_OBJECT["InputParseError<br/>must contain an object"]
    OBJECT -->|Yes| RESULT
```

Valid JSON may decode to a list, number, string, Boolean, or null. Those values
are rejected because the analysis requires a JSON object.

`parse_analysis_inputs()` applies this behavior to the suggested, selected, and
final payloads.

---

## 3. Top-level field dispatch

`analyze_objects()` validates all top-level keys against `FIELD_SPECS`.

An unknown field is rejected so a form change cannot be silently ignored.

```mermaid
flowchart TB
    INPUTS["Suggested, selected,<br/>and final objects"]
    VALIDATE["Validate object types<br/>and configured keys"]
    UNKNOWN{"Unknown field?"}
    KIND{"FieldKind"}

    INPUTS --> VALIDATE --> UNKNOWN
    UNKNOWN -->|Yes| ERROR["ValueError<br/>add field to FIELD_SPECS"]
    UNKNOWN -->|No| KIND

    KIND -->|TEXT| TEXT["analyze_text_field()<br/>title, purpose,<br/>description, about"]
    KIND -->|CONTACT| CONTACT["analyze_contact()<br/>four subfields"]
    KIND -->|COMPENSATION| COMP["analyze_compensation()<br/>text plus Boolean"]
    KIND -->|LOOKUP| LOOKUP["analyze_lookup_values()<br/>integer ID sets"]
    KIND -->|MERGED| MERGED["No separate result<br/>handled by another field"]

    TEXT --> RESULTS["dict[str, AnalysisResult]"]
    CONTACT --> RESULTS
    COMP --> RESULTS
    LOOKUP --> RESULTS
```

`offersCompensation` is configured as `MERGED`. It is reported within the
compensation result rather than as an independent result.

The top-level `contact` object expands into:

- `contact.email`;
- `contact.name`;
- `contact.phone`;
- `contact.website`.

A complete valid input therefore produces twelve field results.

---

## 4. Text outcome classification

Ordinary text, contact text, and selected compensation text share the same final
comparison path.

```mermaid
flowchart TB
    START["Validate offered and<br/>selected text"]
    MULTIPLE{"More than one<br/>selection?"}
    SELECTED{"Suggestion<br/>selected?"}
    REQUIRED{"Final blank<br/>and required?"}
    FIND["Find selection in<br/>offered suggestions"]
    OFFERED{"Selection<br/>was offered?"}
    COMPARE["compare_selected_text()"]
    BLANK{"Final blank?"}
    EXACT{"Selected equals final?"}
    COSMETIC{"Equal under cosmetic<br/>transformation?"}

    START --> MULTIPLE
    MULTIPLE -->|Yes| E_MULTIPLE["ValueError"]
    MULTIPLE -->|No| SELECTED

    SELECTED -->|No| REQUIRED
    REQUIRED -->|Yes| E_REQUIRED["ValueError"]
    REQUIRED -->|No| UNASSISTED["UNASSISTED<br/>editing_metrics = None"]

    SELECTED -->|Yes| FIND --> OFFERED
    OFFERED -->|No| E_OFFER["ValueError"]
    OFFERED -->|Yes| COMPARE

    COMPARE --> BLANK
    BLANK -->|"Yes, optional"| REMOVED["REMOVED<br/>editing_metrics = None"]
    BLANK -->|"Yes, required"| E_REQUIRED
    BLANK -->|No| EXACT

    EXACT -->|Yes| M_EXACT["EXACT"]
    EXACT -->|No| COSMETIC
    COSMETIC -->|Yes| M_COSMETIC["COSMETIC_EQUIVALENT"]
    COSMETIC -->|No| M_EDITED["EDITED"]

    M_EXACT --> METRICS
    M_COSMETIC --> METRICS
    M_EDITED --> METRICS

    METRICS["text_post_edit_metrics.analyze_post_edit()"]
    METRICS --> RESULT["PostEditingResult attached to<br/>TextFieldAnalysis.editing_metrics"]
```

Classification order is:

```text
blank → exact → cosmetic-equivalent → edited
```

Metrics are calculated for all selected, nonblank outcomes—including `EXACT`
and `COSMETIC_EQUIVALENT`.

`REMOVED` and `UNASSISTED` have no `PostEditingResult`.

---

## 5. Generic text-metric delegation

The study package determines whether comparison is appropriate. The generic
package performs the calculation.

```mermaid
flowchart LR
    subgraph Study["study-posting-ai-analysis"]
        CLASSIFY["Classify selected<br/>study field"]
        ATTACH["Attach metrics to<br/>field result"]
    end

    subgraph Metrics["text-post-edit-metrics"]
        ANALYZE["analyze_post_edit()<br/>suggestion → final"]
        TER["TER-derived metrics"]
        CHAR["Character metrics"]
        SOFT["Weighted soft-word metrics"]
        COUNTS["Character and word counts"]
        RESULT["PostEditingResult"]
    end

    CLASSIFY -->|"Selected and nonblank"| ANALYZE
    ANALYZE --> TER
    ANALYZE --> CHAR
    ANALYZE --> SOFT
    ANALYZE --> COUNTS

    TER --> RESULT
    CHAR --> RESULT
    SOFT --> RESULT
    COUNTS --> RESULT

    RESULT --> ATTACH
```

The study package contains no TER, Levenshtein, or weighted soft-word
implementation.

`PostEditingResult` contains no form-field identity. Field identity remains in:

- the result-dictionary key;
- `Pick.kind`;
- flattened `field_name`.

The metric package’s argument direction is significant:

```text
suggestion = selected or applied AI text
final      = final saved text
```

Normalized denominators use final-text length.

---

## 6. Cosmetic-equivalence policy

Cosmetic equivalence is a study-specific classification rule, not metric
preprocessing.

```mermaid
flowchart LR
    INPUT["Selected and final text"]
    NFKD["NFKD decomposition"]
    CASE["Unicode case folding"]
    MARKS["Remove combining marks"]
    PUNCT["Replace punctuation<br/>and symbols with spaces"]
    SPACE["Collapse whitespace"]
    EQUAL{"Results equal?"}

    INPUT --> NFKD --> CASE --> MARKS --> PUNCT --> SPACE --> EQUAL
    EQUAL -->|Yes| COSMETIC["COSMETIC_EQUIVALENT"]
    EQUAL -->|No| EDITED["EDITED"]
```

The original selected and final strings—not cosmetically transformed strings—are
passed to `text_post_edit_metrics.analyze_post_edit()`.

This preserves capitalization, punctuation, diacritic, and whitespace edits in
the underlying metrics.

---

## 7. Contact analysis

Each contact subfield offers at most one suggestion.

```mermaid
flowchart TB
    CONTACT["Suggested, selected,<br/>and final contact objects"]
    CLEAN["clean_contact()<br/>validate fields and values"]
    FIELD["For each contact subfield"]
    SELECTED{"Suggestion selected?"}
    OFFERED{"Suggestion offered<br/>and selection equal?"}
    REQUIRED{"Final blank<br/>and required?"}

    CONTACT --> CLEAN --> FIELD --> SELECTED

    SELECTED -->|No| REQUIRED
    REQUIRED -->|Yes| ERROR_REQUIRED["ValueError"]
    REQUIRED -->|No| UNASSISTED["UNASSISTED"]

    SELECTED -->|Yes| OFFERED
    OFFERED -->|No| ERROR_OFFER["ValueError"]
    OFFERED -->|Yes| TEXT["Shared text<br/>comparison path"]

    TEXT --> RESULT["TextFieldAnalysis"]
    UNASSISTED --> RESULT
```

Required contact fields:

- `email`;
- `name`.

Optional contact fields:

- `phone`;
- `website`.

Unknown contact subfields are rejected.

---

## 8. Compensation analysis

Compensation combines categorized text suggestions with the
`offersCompensation` Boolean.

```mermaid
flowchart TB
    START["analyze_compensation()"]
    FLAGS["Validate suggested<br/>and saved Booleans"]
    SAVED{"Saved Boolean"}
    SELECTED{"Text suggestion<br/>selected?"}
    REQUIRED{"Required text<br/>present?"}

    START --> FLAGS --> SAVED

    SAVED -->|Missing| E_FLAG["ValueError"]
    SAVED -->|True| TEXT_REQUIRED["Text required"]
    SAVED -->|False| TEXT_OPTIONAL["Text optional"]

    TEXT_REQUIRED --> SELECTED
    TEXT_OPTIONAL --> SELECTED

    SELECTED -->|Yes| TEXT["Shared text<br/>comparison path"]
    SELECTED -->|No| REQUIRED

    REQUIRED -->|"Required and blank"| E_TEXT["ValueError"]
    REQUIRED -->|"Present or optional"| UNASSISTED["UNASSISTED"]

    TEXT --> RESULT["CompensationAnalysis"]
    UNASSISTED --> RESULT
```

Compensation-text categories:

- `genericCompensation`;
- `specificCompensation`.

At most one text suggestion may be selected across both categories.

The result reports Boolean acceptance separately from text outcome:

- `flag_suggested`;
- `flag_saved`;
- `flag_accepted`;
- `flag_changed`;
- `compensation_text_required`.

---

## 9. Lookup analysis

Lookup values are sets of integer IDs.

```mermaid
flowchart TB
    START["Validate offered,<br/>picked, and saved IDs"]
    VALID{"Every picked ID<br/>was offered?"}
    ANY{"Any ID picked?"}
    EQUAL{"Picked equals saved?"}
    JACCARD["Jaccard similarity<br/>intersection ÷ union"]

    START --> VALID
    VALID -->|No| ERROR["ValueError"]
    VALID -->|Yes| ANY

    ANY -->|No| UNASSISTED["UNASSISTED<br/>similarity = 0.0 policy value"]
    ANY -->|Yes| EQUAL

    EQUAL -->|Yes| EXACT["EXACT<br/>similarity = 1.0"]
    EQUAL -->|No| JACCARD --> EDITED["EDITED"]

    UNASSISTED --> RESULT["LookupValueAnalysis"]
    EXACT --> RESULT
    EDITED --> RESULT
```

Booleans are rejected because `bool` is a subclass of `int`.

Derived sets are:

- `kept = picked ∩ saved`;
- `dropped = picked − saved`;
- `added = saved − picked`;
- `saved_not_offered = saved − offered`.

Lookup similarity must not be combined with text effort-saved scores.

---

## 10. Flattening

`flatten_analysis_results()` converts structured field results into plain
tabular dictionaries.

```mermaid
flowchart TB
    RESULTS["dict[str, AnalysisResult]"]
    EACH["For each field"]
    TEMPLATE["Create row from<br/>FLATTENED_COLUMNS"]
    KIND{"Result type"}

    RESULTS --> EACH --> TEMPLATE --> KIND

    KIND -->|Text| TEXT["Populate offer, pick,<br/>policy, and metric fields"]
    KIND -->|Compensation| COMP["Populate text fields<br/>plus Boolean fields"]
    KIND -->|Lookup| LOOKUP["Populate similarity<br/>and serialized ID sets"]

    TEXT --> PRIVACY{"include_text?"}
    COMP --> PRIVACY
    PRIVACY -->|Yes| INCLUDE["Include selected<br/>and final text"]
    PRIVACY -->|No| OMIT["Leave text columns None"]

    INCLUDE --> ROW["Flat dictionary"]
    OMIT --> ROW
    LOOKUP --> ROW

    ROW --> OUTPUT["list[dict[str, object]]"]
```

Every row:

- contains every name in `FLATTENED_COLUMNS`;
- preserves canonical column order;
- contains only `None`, `bool`, `int`, `float`, or `str`;
- excludes free text unless explicitly requested.

Lookup rows leave text metric and policy fields as `None`.

Identifier sets are serialized as sorted JSON arrays.

---

## 11. Error boundary

The library raises and never logs.

| Condition | Exception |
|---|---|
| Missing, blank, malformed, or non-object JSON | `InputParseError` |
| Wrong runtime type | `TypeError` |
| Requiredness or form-policy violation | `ValueError` |
| Unknown field | `ValueError` |
| Selected value that was not offered | `ValueError` |

A consuming program determines whether an invalid record:

- aborts processing;
- is recorded and skipped;
- is sent to a review queue.

Record identifiers, logging, and batch-failure policy remain outside the
library.
