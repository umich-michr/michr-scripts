# Program flow

Diagrams render in VS Code with **Markdown Preview Mermaid Support**
(`bierner.markdown-mermaid`), and natively on GitHub.

For metric definitions and business rules, see
[`analysis-specification.md`](analysis-specification.md).

---

## 1. Library boundary

This library performs no input or output. Three decoded objects in, one
structured result per field out. Everything outside the dashed boundary is the
responsibility of a consuming program.

```mermaid
flowchart LR
    subgraph Consumer["Consuming program"]
        SOURCE[("Data source<br/>database, CSV, HTTP")]
        LOOP["Row loop and<br/>error handling"]
        OUTPUT["Aggregation,<br/>CSV, reports"]
    end

    subgraph Library["study-posting-ai-analysis"]
        PARSE["parse_analysis_inputs()<br/>decode three JSON payloads"]
        ANALYZE["analyze_objects()<br/>validate and dispatch each field"]
        FLATTEN["flatten_analysis_results()<br/>one flat dict per field"]
    end

    SOURCE --> LOOP
    LOOP --> PARSE --> ANALYZE --> FLATTEN
    FLATTEN --> OUTPUT

    style Library stroke-dasharray: 5 5
```

The library raises on invalid input and never logs. A consumer decides whether a
failed record aborts the run or is recorded and skipped.

---

## 2. Input contract

```mermaid
flowchart TB
    RAW["JSON text, UTF-8 bytes,<br/>or an existing mapping"]
    PARSE["parse_json_object()"]

    RAW --> PARSE
    PARSE --> C1{"Absent?"}
    C1 -->|Yes| E1["InputParseError<br/>is missing"]
    C1 -->|No| C2{"Bytes?"}
    C2 -->|Yes| DECODE["Decode as UTF-8"]
    DECODE -->|Invalid| E2["InputParseError<br/>not valid UTF-8"]
    DECODE -->|Valid| C3
    C2 -->|No| C3{"String?"}
    C3 -->|Yes| C4{"Blank?"}
    C4 -->|Yes| E3["InputParseError<br/>is blank"]
    C4 -->|No| LOADS["json.loads()"]
    LOADS -->|Syntax error| E4["InputParseError<br/>invalid JSON at line, column"]
    LOADS -->|Parsed| C5
    C3 -->|No| C5{"Is an object?"}
    C5 -->|No| E5["InputParseError<br/>must contain a JSON object"]
    C5 -->|Yes| OK["dict[str, object]"]
```

Bytes are decoded explicitly rather than left to `json.loads`, which raises
`UnicodeDecodeError` outside the `JSONDecodeError` hierarchy and infers the
encoding from a byte-order mark. A blank value is reported before parsing,
because an empty column is an expected condition rather than a syntax error at
column 1.

JSON permits six value types; only an object is valid here. The other five are
rejected with the received type named.

---

## 3. Field dispatch

`analyze_objects()` rejects any field absent from `FIELD_SPECS`, then routes each
configured field by its `FieldKind`.

```mermaid
flowchart TB
    ORCH["analyze_objects(suggested, selected, final)"]
    CHECK{"All fields<br/>configured?"}

    ORCH --> CHECK
    CHECK -->|No| ERROR["ValueError<br/>add them to FIELD_SPECS"]
    CHECK -->|Yes| KIND{"FieldKind?"}

    KIND -->|TEXT| TEXT["analyze_text_field()<br/>title, purpose,<br/>description, about"]
    KIND -->|CONTACT| CONTACT["analyze_contact()<br/>email, name,<br/>phone, website"]
    KIND -->|COMPENSATION| COMP["analyze_compensation()<br/>text categories<br/>plus Boolean flag"]
    KIND -->|LOOKUP| LOOKUP["analyze_lookup_values()<br/>department, locations,<br/>topics"]
    KIND -->|MERGED| MERGED["offersCompensation<br/>skipped: reported inside<br/>the compensation result"]

    TEXT --> RESULTS["dict[str, AnalysisResult]"]
    CONTACT --> RESULTS
    COMP --> RESULTS
    LOOKUP --> RESULTS
```

Rejecting unconfigured fields is deliberate: a new form field must not be
silently ignored.

Contact expands into four separately reported subfields, so a record with all
ten configured fields produces twelve results — four contact entries, and none
for the merged `offersCompensation`.

---

## 4. Text field analysis

The shared path for ordinary text fields, contact subfields, and compensation
text.

```mermaid
flowchart TB
    START["analyze_text_field()<br/>validate suggestion and<br/>selection lists"]
    MULTI{"More than one<br/>selection?"}

    START --> MULTI
    MULTI -->|Yes| E_MULTI["ValueError<br/>at most one may be selected"]
    MULTI -->|No| SELECTED{"Any<br/>selection?"}

    SELECTED -->|No| REQ{"Blank and<br/>required?"}
    REQ -->|Yes| E_BLANK["ValueError<br/>must not be blank"]
    REQ -->|No| UNASSISTED["match = UNASSISTED<br/>editing_metrics = None"]

    SELECTED -->|Yes| FIND["find_first_picked_suggestion()<br/>locate the selection and its<br/>index in the offer list"]
    FIND -->|Not found| E_OFFER["ValueError<br/>selection was never offered"]
    FIND -->|Found| COMPARE["compare_selected_text()"]

    COMPARE --> BLANK{"Final text<br/>blank?"}
    BLANK -->|"Yes, optional"| REMOVED["match = REMOVED<br/>editing_metrics = None"]
    BLANK -->|"Yes, required"| E_REQ["ValueError<br/>must not be blank"]
    BLANK -->|No| EXACT{"Strings<br/>equal?"}

    EXACT -->|Yes| M_EXACT["match = EXACT"]
    EXACT -->|No| COSMETIC["normalize_text_for_equivalence()<br/>NFKD, casefold, strip<br/>marks and punctuation"]

    COSMETIC -->|Equal| M_COSMETIC["match = COSMETIC_EQUIVALENT"]
    COSMETIC -->|Differ| M_EDITED["match = EDITED"]

    M_EXACT --> METRICS["analyze_selected_suggestion()"]
    M_COSMETIC --> METRICS
    M_EDITED --> METRICS

    METRICS --> RESULT["TextFieldAnalysis"]
    UNASSISTED --> RESULT
    REMOVED --> RESULT
```

Evaluation order is **blank, then exact, then cosmetic, then edited**.

Metrics are calculated for all three nonblank outcomes, not only `EDITED`, so an
exact match records a measured score of `1.0` rather than an assumed one.

`REMOVED` and `UNASSISTED` produce no editing metrics, because the normalized
scores would require a zero denominator. Their reported policy score is `0.0`,
which is a meaningful value rather than a missing one.

The cosmetic-equivalence transformation is used **only** for classification. It
never preprocesses a metric input; doing so would hide real edits. A
`COSMETIC_EQUIVALENT` result therefore carries a nonzero character edit distance
alongside its full policy credit.
---

## 5. Metric calculation

```mermaid
flowchart TB
    ENTRY["analyze_selected_suggestion()<br/>NFC-normalize both texts,<br/>reject an empty final value"]

    ENTRY --> TER["calculate_ter_metrics()<br/>SacreBLEU TER<br/>case-insensitive"]
    ENTRY --> CHAR["calculate_character_metrics()<br/>RapidFuzz Levenshtein<br/>case-sensitive"]
    ENTRY --> SOFT["calculate_soft_word_metrics()<br/>weighted word distance<br/>case-sensitive"]
    ENTRY --> LENGTHS["Character and<br/>whitespace-token counts"]

    SOFT --> DP["weighted_soft_word_distance()<br/>Wagner-Fischer recurrence,<br/>two rows retained"]
    DP --> WORD["normalized_word_distance()<br/>LRU-cached RapidFuzz<br/>normalized distance"]

    CHAR --> ABS["estimated_characters_saved<br/>max(0, final chars − distance)"]

    TER --> OUT
    CHAR --> OUT
    SOFT --> OUT
    LENGTHS --> OUT
    ABS --> OUT

    OUT["SuggestionEditingResult<br/>raw and bounded scores<br/>for every measure"]
```

| Measure | Formula | Role | Case |
|---|---|---|---|
| TER-derived | `1 − TER` | **Primary** | insensitive |
| Character | `1 − levenshtein / final_chars` | Secondary robustness | sensitive |
| Soft-word | `1 − weighted_distance / final_words` | Robustness | sensitive |
| Characters saved | `max(0, final_chars − distance)` | Absolute proxy | sensitive |

Every raw score may be negative and is retained. Bounded reporting scores are
`clamp01(raw)`. Both are stored, because clamping alone would hide suggestions
that cost more to fix than to rewrite.

The deliberate case asymmetry means a purely capitalization change yields TER
`0.0` while the character and soft-word measures report a nonzero distance —
which is the intended signal that something was edited even though TER regarded
the texts as equivalent.

The soft-word implementation retains only two dynamic-programming rows. A
full-matrix reference implementation in `tests/helpers/` verifies it across 1,500
seeded random cases to twelve decimal places. Unlike TER, it includes no
phrase-shift operation.

---

## 6. Compensation analysis

Two components: the AI-suggested Boolean, and an optional text suggestion. The
**saved** Boolean determines whether text is required.

```mermaid
flowchart TB
    START["analyze_compensation()"]
    START --> VALIDATE["require_optional_boolean()<br/>reject 1 and 0:<br/>bool subclasses int"]
    VALIDATE --> RULE{"Saved<br/>offersCompensation?"}

    RULE -->|None| FLAG_ERR["ValueError<br/>must be saved as True or False"]
    RULE -->|True| REQ["Text required"]
    RULE -->|False| OPT["Text optional"]

    REQ --> PICKED{"Text suggestion<br/>selected?"}
    OPT --> PICKED

    PICKED -->|Yes| SHARED["compare_selected_text()<br/>shared text path"]
    PICKED -->|"No, text present"| UNASSIST["match = UNASSISTED"]
    PICKED -->|"No, optional text blank"| UNASSIST
    PICKED -->|"No, required text blank"| TEXT_ERR["ValueError<br/>text required when<br/>offersCompensation is True"]

    SHARED --> OUT
    UNASSIST --> OUT

    OUT["CompensationAnalysis<br/>text outcome plus<br/>flag_suggested, flag_saved,<br/>flag_accepted, flag_changed,<br/>compensation_text_required"]
```

Boolean acceptance is reported **separately** from text post-editing scores; they
measure different things. When either Boolean is absent, `flag_accepted` and
`flag_changed` are `None` rather than `False`, so records without a recommendation
can be excluded from an acceptance rate.

Two cases worth understanding:

| Scenario | Text outcome |
|---|---|
| AI suggested `False`; user set `True` and wrote text unaided | `UNASSISTED` |
| Suggestion selected, then Boolean set `False` and text cleared | `REMOVED` |

At most one text suggestion may be selected across both categories
(`genericCompensation`, `specificCompensation`).

---

## 7. Lookup field analysis

```mermaid
flowchart TB
    START["analyze_lookup_values()"]
    START --> COERCE["require_integer_set()<br/>reject bool: True would<br/>otherwise become 1"]
    COERCE --> VALID{"All picked IDs<br/>were offered?"}

    VALID -->|No| ERR["ValueError<br/>not among the offered values"]
    VALID -->|Yes| ANY{"Any ID<br/>picked?"}

    ANY -->|No| UNASSIST["match = UNASSISTED<br/>similarity = 0.0<br/>policy value, not calculated"]
    ANY -->|"Yes, picked = saved"| EXACT["match = EXACT<br/>similarity = 1.0"]
    ANY -->|"Yes, sets differ"| JACCARD["Jaccard similarity<br/>intersection ÷ union"]

    JACCARD --> EDITED["match = EDITED"]

    UNASSIST --> OUT
    EXACT --> OUT
    EDITED --> OUT

    OUT["LookupValueAnalysis<br/>offered, picked, saved,<br/>kept, dropped, added,<br/>saved_not_offered"]
```

When nothing was picked, `0.0` is assigned as a realized-assistance policy value
rather than calculated — an empty-set Jaccard formula is undefined.

Lookup similarity measures a different construct from text effort saved and must
never be averaged together with it. The `kept`, `dropped`, `added`, and
`saved_not_offered` sets are derived properties, so they cannot drift out of
agreement with the three stored sets.

---

## 8. Flattening

```mermaid
flowchart TB
    RESULTS["dict[str, AnalysisResult]"]
    RESULTS --> LOOP["For each field"]
    LOOP --> TEMPLATE["Build a row from<br/>FLATTENED_COLUMNS<br/>every column present, unset"]

    TEMPLATE --> KIND{"Result kind?"}

    KIND -->|LOOKUP| FILL_L["Populate similarity and<br/>the seven identifier sets;<br/>leave TER and policy unset"]
    KIND -->|"TEXT or COMPENSATION"| FILL_T["Populate counts, pick,<br/>policy score, and metrics<br/>when present"]

    FILL_T --> COMP{"Compensation?"}
    COMP -->|Yes| FLAGS["Populate the four<br/>flag columns"]
    COMP -->|No| ROW
    FLAGS --> ROW
    FILL_L --> ROW

    ROW["dict[str, object]<br/>38 columns, identical<br/>keys in identical order"]
    ROW --> ROWS["list[dict[str, object]]"]
```

Every row is built from one template, so all rows share the same keys in the same
order whatever the result kind. A consumer writes a header once and relies on it.

Values are only `None`, `bool`, `int`, `float`, or `str`. Identifier sets are
rendered as sorted JSON arrays, which keeps exported rows stable across runs and
comparable in a diff.

Lookup rows leave `policy_adjusted_effort_saved` and every TER column as `None`.
This is deliberate: `None` means "not applicable," so a mean over text rows
cannot be contaminated by a similarity value.

Free text is excluded unless `include_text=True` is passed, reducing accidental
disclosure of potentially sensitive study content.

---

## 9. Error behavior

The library raises and never logs. A consumer decides what a failure means.

| Condition | Exception |
|---|---|
| Malformed or absent JSON input | `InputParseError`, a `ValueError` |
| Wrong container or value type | `TypeError` |
| Rule violation, such as a blank required field | `ValueError` |
| Unconfigured field present in an input object | `ValueError` |
| Selection that was never offered | `ValueError` |

A blank required field is an error, not a metric of zero. That distinction
matters: a score of zero would silently enter an average, whereas an exception
forces the consumer to decide whether the record is usable.

Every message names the field, and for compensation and contact the prefixed
subfield, so a batch consumer can report precisely which field of which record
failed.

A typical consumer records the failure with its own record identifier and
continues:

```python
for row in rows:
    try:
        results = analyze_objects(*parse_analysis_inputs(*row.payloads))
    except (ValueError, TypeError) as error:
        logger.warning("Record %s failed: %s", row.identifier, error)
        continue

    output.extend(flatten_analysis_results(results, record_id=row.identifier))
```
