# Program flow and architecture

Diagrams render in VS Code with the **Markdown Preview Mermaid Support**
extension (`bierner.markdown-mermaid`), and natively on GitHub.

For metric definitions and business rules, see
[`analysis-specification.md`](analysis-specification.md).

---

## 1. Layers

Dependencies point inward only. The domain layer does not know that Oracle,
SQLite, pandas, or a notebook exists.

```mermaid
flowchart TB
    A["Presentation<br/>cli.py, reporting.py<br/>CSV, summaries, terminal output"]
    B["Application<br/>pipeline.py<br/>orchestration, per-record error capture"]
    C["Domain<br/>models, text_normalization, metrics,<br/>field_specs, field_analysis"]
    D["Adapter<br/>adapters/sqlite, adapters/oracle<br/>database access"]

    D --> B
    B --> C
    C --> B
    B --> A
```

| Layer | Contains | May import |
|---|---|---|
| Presentation | Argument parsing, flattening, DataFrame construction, export | anything |
| Application | Record iteration, error capture, use-case coordination | domain, repository Protocol |
| Domain | Field rules, match classification, metric calculations, result models | stdlib, sacrebleu, rapidfuzz |
| Adapter | Eligibility queries, row mapping, JSON decoding | domain, database drivers |

This separation is what allows the same domain analysis to run from a notebook,
a command-line program, a scheduled job, a web service, or a test suite.

---

## 2. End-to-end pipeline

```mermaid
flowchart TB
    subgraph Sources["Input adapters"]
        CSV["SQL-export CSV"]
        SQLITE[("SQLite<br/>local development")]
        ORACLE[("Oracle<br/>production")]
    end

    subgraph Repo["Repository"]
        ELIGIBLE["iter_eligible_records()<br/>ATTEMPT_TYPE = 'AI'<br/>ATTEMPT_RESULT = 'COMPLETE'"]
        DECODE["decode_json_object_column()<br/>validate and decode<br/>three JSON columns"]
        RECORD["AuditRecord"]
    end

    subgraph App["Application"]
        PIPE["analyze_audit_records()"]
        ERRORS["Per-record error capture<br/>one failure does not stop the run"]
    end

    subgraph Domain["Domain"]
        MAIN["analyze_objects()"]
        RESULTS["Structured result dataclasses"]
    end

    subgraph Report["Reporting"]
        FLAT["flatten_analysis_results()<br/>one flat row per field"]
        FRAME["pandas DataFrame"]
        SUMMARY["Aggregate summaries"]
        EXPORT["suggestion_analysis.csv"]
    end

    CSV --> SQLITE
    SQLITE --> ELIGIBLE
    ORACLE --> ELIGIBLE
    ELIGIBLE --> DECODE --> RECORD --> PIPE
    PIPE --> MAIN --> RESULTS --> FLAT
    PIPE --> ERRORS
    FLAT --> FRAME --> SUMMARY
    FRAME --> EXPORT
```

This mirrors the real-world process: an audit event is stored, eligible events
are selected, JSON payloads are decoded, each field is interpreted according to
its type and business rules, metrics are calculated, and results are transformed
for analysis.

---

## 3. Field dispatch

`analyze_objects()` validates that every top-level key is configured, then routes
each field by its `FieldKind`.

```mermaid
flowchart TB
    ORCH["analyze_objects(suggested, selected, final)"]
    KIND{"FieldKind?"}

    ORCH --> KIND

    KIND -->|TEXT| TEXT["analyze_text_field()<br/>title, purpose,<br/>description, about"]
    KIND -->|CONTACT| CONTACT["analyze_contact()<br/>email, name,<br/>phone, website"]
    KIND -->|COMPENSATION| COMP["analyze_compensation()<br/>text categories<br/>+ Boolean flag"]
    KIND -->|LOOKUP| LOOKUP["analyze_lookup_values()<br/>department, locations,<br/>topics"]
    KIND -->|MERGED| MERGED["offersCompensation<br/>skipped: handled inside<br/>compensation analysis"]

    TEXT --> RESULTS["Result dictionary<br/>one entry per analyzed field"]
    CONTACT --> RESULTS
    COMP --> RESULTS
    LOOKUP --> RESULTS
```

Contact expands into four separately reported subfields
(`contact.email`, `contact.name`, `contact.phone`, `contact.website`).

---

## 4. Text field analysis

The shared path for ordinary text fields, contact subfields, and compensation
text.

```mermaid
flowchart TB
    START["analyze_text_field()<br/>validate suggestion and<br/>selection lists"]
    SELECTED{"Suggestion<br/>selected?"}

    START --> SELECTED

    SELECTED -->|No| UNASSISTED["match = UNASSISTED<br/>editing_metrics = None"]
    SELECTED -->|Yes| FIND["find_first_picked_suggestion()<br/>locate selected text and<br/>its index in the offer list"]

    FIND --> COMPARE["compare_selected_text()"]
    COMPARE --> BLANK{"Final text<br/>blank?"}

    BLANK -->|"Yes, field optional"| REMOVED["match = REMOVED<br/>editing_metrics = None"]
    BLANK -->|"Yes, field required"| ERROR["ValueError<br/>required text must not be blank"]
    BLANK -->|No| EXACT{"Strings<br/>equal?"}

    EXACT -->|Yes| M_EXACT["match = EXACT"]
    EXACT -->|No| COSMETIC["normalize_text_for_equivalence()<br/>NFKD, casefold,<br/>strip marks and punctuation"]

    COSMETIC -->|Equivalent| M_COSMETIC["match = COSMETIC_EQUIVALENT"]
    COSMETIC -->|Not equivalent| M_EDITED["match = EDITED"]

    M_EXACT --> METRICS
    M_COSMETIC --> METRICS
    M_EDITED --> METRICS

    METRICS["analyze_selected_suggestion()"]
    METRICS --> RESULT["TextFieldAnalysis<br/>match, Pick, texts,<br/>SuggestionEditingResult"]
    UNASSISTED --> RESULT
    REMOVED --> RESULT
```

Evaluation order is **blank → exact → cosmetic → edited**. Metrics are
calculated for all three nonblank outcomes, not only `EDITED`, so an exact match
records a verifiable score of `1.0` rather than an assumed one.

`REMOVED` and `UNASSISTED` produce no editing metrics, because the
normalized score's final-length denominator would be zero.

---

## 5. Metric calculation

```mermaid
flowchart TB
    ENTRY["analyze_selected_suggestion()<br/>NFC-normalize both texts,<br/>reject empty final text"]

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

| Measure | Formula | Role |
|---|---|---|
| TER-derived | `1 − TER` | **Primary** |
| Character | `1 − levenshtein / final_chars` | Secondary robustness |
| Soft-word | `1 − weighted_distance / final_words` | Robustness |
| Characters saved | `max(0, final_chars − distance)` | Absolute proxy |

Every raw score may be negative and is retained. Bounded reporting scores are
`clamp01(raw)`. Both are stored; the raw value is never discarded, because
clamping would otherwise hide suggestions that cost more to fix than to rewrite.

---

## 6. Compensation analysis

Two components: the AI-suggested Boolean, and an optional text suggestion. The
**saved** Boolean determines whether text is required.

```mermaid
flowchart TB
    START["analyze_compensation()"]
    START --> VALIDATE["validate_optional_boolean()<br/>suggested and saved flags"]
    VALIDATE --> RULE{"Saved<br/>offersCompensation?"}

    RULE -->|True| REQ["Compensation text required"]
    RULE -->|False| OPT["Compensation text optional"]
    RULE -->|None| FLAG_ERR["ValueError<br/>must be saved as True or False"]

    REQ --> PICKED{"Text suggestion<br/>selected?"}
    OPT --> PICKED

    PICKED -->|Yes| SHARED["compare_selected_text()<br/>shared text path"]
    PICKED -->|"No, final text present"| UNASSIST["match = UNASSISTED"]
    PICKED -->|"No, optional text blank"| UNASSIST
    PICKED -->|"No, required text blank"| TEXT_ERR["ValueError<br/>text required when<br/>offersCompensation is True"]

    SHARED --> OUT
    UNASSIST --> OUT

    OUT["CompensationAnalysis<br/>text outcome plus<br/>flag_suggested, flag_saved,<br/>flag_accepted, flag_changed,<br/>compensation_text_required"]
```

Boolean acceptance is reported **separately** from text post-editing scores; they
measure different things.

Two cases worth understanding:

| Scenario | Text outcome |
|---|---|
| AI suggested `False`, user changed to `True` and wrote text unaided | `UNASSISTED` |
| Suggestion selected, then Boolean changed to `False` and text cleared | `REMOVED` |

At most one compensation text suggestion may be selected across both categories
(`genericCompensation`, `specificCompensation`).

---

## 7. Lookup field analysis

```mermaid
flowchart TB
    START["analyze_lookup_values()"]
    START --> COERCE["coerce_integer_set()<br/>reject bool: it subclasses int"]
    COERCE --> VALID{"All picked IDs<br/>were offered?"}

    VALID -->|No| ERR["ValueError<br/>picked values not among<br/>offered values"]
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

Lookup similarity is **never** averaged together with text effort-saved scores.
The two measure different constructs and are summarized separately by field.

When nothing was picked, `0.0` is assigned as a realized-assistance policy value
rather than calculated — an empty-set Jaccard formula is undefined.

---

## 8. Reporting

```mermaid
flowchart TB
    RESULTS["analyze_objects() result<br/>one structured result per field"]
    RESULTS --> FLAT["flatten_analysis_results()<br/>one flat row per field;<br/>free text excluded by default"]
    FLAT --> FRAME["pandas DataFrame"]

    FRAME --> TEXT_R["Text reporting<br/>offer coverage, selection rate,<br/>realized utility,<br/>selected-suggestion utility,<br/>TER-derived post-editing score"]
    FRAME --> LOOKUP_R["Lookup reporting<br/>Jaccard similarity<br/>summarized per field"]
    FRAME --> COMP_R["Compensation reporting<br/>Boolean acceptance and text<br/>post-editing, reported separately"]
    FRAME --> CSV["suggestion_analysis.csv"]
```

Each statistic has a different denominator and answers a different question:

| Statistic | Denominator | Label |
|---|---|---|
| Fields with an offer ÷ analyzed text fields | all text fields | Suggestion offer coverage |
| Fields with a selection ÷ fields with an offer | offered fields | Suggestion selection rate |
| Mean policy score among offered fields | offered fields | Realized suggestion utility |
| Mean policy score among selected suggestions | selected fields | Selected-suggestion utility |
| Mean `ter_effort_saved` among nonblank post-edits | measurable post-edits | TER-derived post-editing score |

Every reported mean must be accompanied by its denominator or sample count.
Never report an all-text-fields average simply as "effort saved" without stating
its denominator.

---

## 9. Error handling

```mermaid
flowchart TB
    LOOP["For each eligible record"]
    LOOP --> TRY["analyze_objects()"]

    TRY -->|Success| OK["RecordAnalysisOutcome<br/>results populated"]
    TRY -->|AnalysisError| CAPTURE["RecordAnalysisOutcome<br/>error recorded,<br/>audit ID retained"]

    OK --> NEXT["Continue to next record"]
    CAPTURE --> LOG["Log at WARNING<br/>field text never logged"]
    LOG --> NEXT

    NEXT --> DONE["Run summary<br/>records analyzed,<br/>records failed"]
```

A single malformed record does not abort a batch. Failures are recorded with the
audit record ID and reported in the run summary, so a partial run is
distinguishable from a complete one.

Validation errors are deliberate and informative — a blank required field is an
error, not a metric of zero.
