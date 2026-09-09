# text-post-edit-metrics

Reusable technical post-editing metrics for comparing an AI-generated
suggestion with final human-edited text.

The package provides a small, directional API:

```python
from text_post_edit_metrics import analyze_post_edit

result = analyze_post_edit(
    suggestion="Support analysis of research data.",
    final="Support analysis of clinical research data.",
)

result.ter_rate
result.ter_effort_saved
result.character_edit_distance
result.soft_word_edit_distance
result.estimated_characters_saved
```

The comparison direction matters:

- `suggestion` is the generated or original text;
- `final` is the human-edited reference text;
- normalized scores use the final text length as their denominator.

> These metrics estimate **technical textual post-editing**. They do not measure
> elapsed time, cognitive effort, observed keystrokes, user satisfaction, or
> semantic equivalence.

---

## Scope

This package owns:

- Unicode NFC preprocessing for metric inputs;
- Translation Edit Rate (TER);
- TER-derived raw and bounded effort-saved scores;
- character-level Levenshtein distance and scores;
- weighted soft-word distance and scores;
- an estimated-characters-saved proxy;
- descriptive character and word counts;
- immutable result models.

It does not own:

- form fields or field requiredness;
- suggestion-selection policy;
- contact, compensation, or lookup behavior;
- database or CSV access;
- filesystem access;
- DataFrames;
- logging;
- command-line programs.

Those concerns belong to consuming packages and programs.

---

## Primary API

### `analyze_post_edit`

```python
from text_post_edit_metrics import analyze_post_edit

result = analyze_post_edit(
    suggestion="We analyze research data.",
    final="We analyze clinical research data.",
)
```

Returns an immutable `PostEditingResult`.

An empty suggestion is permitted:

```python
result = analyze_post_edit(
    suggestion="",
    final="A final response",
)
```

This represents a baseline where the complete final text had to be inserted.

The final text must:

- be a string;
- be nonempty;
- contain at least one whitespace-delimited token.

Invalid input raises `TypeError` or `ValueError`.

---

## Result fields

| Field | Definition |
|---|---|
| `ter_rate` | TER edit cost divided by final reference length; may exceed `1` |
| `ter_effort_saved_raw` | `1 - ter_rate`; may be negative |
| `ter_effort_saved` | Raw TER-derived score bounded to `[0, 1]` |
| `character_edit_distance` | Character-level Levenshtein distance |
| `character_effort_saved_raw` | `1 - distance / final_character_count`; may be negative |
| `character_effort_saved` | Raw character score bounded to `[0, 1]` |
| `soft_word_edit_distance` | Weighted word-level edit distance |
| `soft_word_effort_saved_raw` | `1 - distance / final_word_count`; may be negative |
| `soft_word_effort_saved` | Raw soft-word score bounded to `[0, 1]` |
| `estimated_characters_saved` | `max(0, final_character_count - character_edit_distance)` |
| `suggestion_character_count` | Characters in the NFC-normalized suggestion |
| `final_character_count` | Characters in the NFC-normalized final text |
| `suggestion_word_count` | Whitespace-delimited suggestion tokens |
| `final_word_count` | Whitespace-delimited final tokens |

Raw values are retained deliberately. Reporting only bounded scores would hide
cases where editing cost exceeded the final-length baseline.

`estimated_characters_saved` is an absolute technical-editing proxy. It is not a
measurement of literal avoided typing or observed keystrokes.

---

## Metrics

### TER-derived effort saved

The primary measure is:

```text
ter_effort_saved_raw = 1 - TER
ter_effort_saved = min(1, max(0, ter_effort_saved_raw))
```

TER is calculated with SacreBLEU using:

```text
normalized     = False
no_punct       = False
asian_support  = False
case_sensitive = False
```

TER includes insertions, deletions, substitutions, and phrase shifts. It is
normalized by final reference length.

### Character-level effort saved

```text
character_effort_saved_raw =
    1 - character_edit_distance / final_character_count
```

Character distance uses RapidFuzz Levenshtein distance and is case-sensitive by
default.

It is a textual editing proxy, not a keystroke count.

### Weighted soft-word effort saved

```text
soft_word_effort_saved_raw =
    1 - soft_word_edit_distance / final_word_count
```

At word level:

- insertion cost is `1`;
- deletion cost is `1`;
- substitution cost is normalized character-level Levenshtein distance between
  the two words.

This gives partial credit to small within-word changes such as `analyze` to
`analyzed`.

The implementation uses a weighted Wagner–Fischer dynamic-programming recurrence
and retains two matrix rows. Unlike TER, it has no phrase-shift operation.

This is a custom robustness measure, not standardized TER.

---

## Preprocessing

Metric text is normalized with Unicode NFC.

Under the default public API:

- TER is case-insensitive;
- character distance is case-sensitive;
- soft-word distance is case-sensitive;
- whitespace tokenization is used;
- punctuation remains attached to words;
- hyphenated forms remain one token;
- repeated whitespace does not affect tokenization;
- no stemming or lemmatization is performed;
- no semantic model, embedding, thesaurus, or ontology is used.

Semantically similar but orthographically different words may therefore receive
substantial substitution costs.

---

## Lower-level API

The package also exports:

```python
from text_post_edit_metrics import (
    CharacterResult,
    PostEditingResult,
    SoftWordResult,
    TerResult,
    calculate_character_metrics,
    calculate_soft_word_metrics,
    calculate_ter_metrics,
    clamp01,
    count_whitespace_tokens,
    normalize_metric_text,
    normalized_word_distance,
    weighted_soft_word_distance,
)
```

Use `analyze_post_edit()` for the complete standard calculation. The lower-level
functions are useful for focused analysis, testing, and research.

Custom insertion and deletion costs are supported by the soft-word functions:

```python
distance = weighted_soft_word_distance(
    suggestion="one two",
    final="one",
    insertion_cost=2.0,
    deletion_cost=3.0,
)
```

---

## Verification

The automated suite covers:

- identity and boundary conditions;
- raw and bounded score formulas;
- Unicode normalization;
- case behavior;
- empty suggestion behavior;
- invalid final denominators;
- unequal insertion and deletion costs;
- unequal-length word alignments;
- fractional word substitutions;
- result immutability;
- public API exports.

The optimized two-row soft-word implementation is compared with an independent
full-matrix implementation across:

- 1,000 seeded random pairs with standard costs;
- 500 seeded random pairs with unequal costs;
- explicit empty, repeated-word, and unequal-length cases.

The implementations agree to an absolute tolerance of `1e-12`.

This verifies implementation consistency. It does not establish that the metric
measures human cognitive effort or time.

---

## Development

From the workspace root:

```bash
make setup
make test PACKAGE=text-post-edit-metrics
make coverage PACKAGE=text-post-edit-metrics
make check
```

Run only the randomized differential tests:

```bash
make test-slow PACKAGE=text-post-edit-metrics
```

Skip them:

```bash
make test-fast PACKAGE=text-post-edit-metrics
```

Runtime dependencies:

| Dependency | Purpose |
|---|---|
| SacreBLEU 2.6.x | TER |
| RapidFuzz 3.14.x | character-level Levenshtein |

Exact versions are recorded in the workspace `uv.lock`.

---

## References

Snover, M., Dorr, B., Schwartz, R., Micciulla, L., & Makhoul, J. (2006).
*A Study of Translation Edit Rate with Targeted Human Annotation*.

Levenshtein, V. I. (1966). Binary codes capable of correcting deletions,
insertions, and reversals.

Wagner, R. A., & Fischer, M. J. (1974). The string-to-string correction
problem.
