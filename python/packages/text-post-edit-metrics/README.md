# text-post-edit-metrics

Directional technical post-editing metrics for comparing an initial text with a
value represented by the caller as its edited form.

```python
from text_post_edit_metrics import analyze_post_edit

result = analyze_post_edit(
    suggestion="Support analysis of research data.",
    final="Support analysis of clinical research data.",
)

print(result.ter_effort_saved)
print(result.character_edit_distance)
print(result.soft_word_edit_distance)
```

The comparison direction matters:

- `suggestion` is the initial, generated, or proposed text;
- `final` is the value represented as its edited or revised form;
- normalized scores use final-text length as their denominator.

The package does not verify that `final` was actually produced by editing
`suggestion`. It measures the pair under a post-editing interpretation.

> These metrics estimate **technical textual post-editing**. They do not
> directly measure elapsed time, cognitive effort, observed keystrokes, semantic
> equivalence, user satisfaction, or overall usefulness.

---

## Scope

This package owns:

- Unicode NFC normalization for metric inputs;
- Translation Edit Rate (TER);
- TER-derived raw and bounded scores;
- character-level Levenshtein distance and scores;
- weighted soft-word distance and scores;
- an estimated-characters-saved proxy;
- descriptive character and token counts;
- immutable result models.

It does not own:

- form fields or requiredness;
- suggestion-selection or acceptance policy;
- product-specific classifications;
- contact, compensation, or lookup analysis;
- record identifiers;
- database, CSV, or filesystem access;
- DataFrames;
- logging;
- command-line applications.

Those responsibilities belong to consuming packages and programs.

---

## Documentation

| Document | Purpose |
|---|---|
| [`docs/methodology.md`](docs/methodology.md) | Canonical comparison direction, preprocessing, formulas, result fields, and interpretation limits |
| [`docs/verification.md`](docs/verification.md) | Canonical software-verification strategy, boundary tests, differential testing, coverage, and change requirements |

This README provides the package overview and public API. The methodology and
verification documents are authoritative for their respective subjects.

---

## Primary API

### `analyze_post_edit()`

```python
from text_post_edit_metrics import analyze_post_edit

result = analyze_post_edit(
    suggestion="We analyze research data.",
    final="We analyze clinical research data.",
)
```

The function returns an immutable `PostEditingResult`.

An empty suggestion is valid:

```python
result = analyze_post_edit(
    suggestion="",
    final="A final response",
)
```

This represents a comparison where the complete final text must be inserted.

The final value must:

- be a string;
- be nonempty;
- contain at least one whitespace-delimited token.

Invalid types raise `TypeError`. An invalid final denominator raises
`ValueError`.

---

## Result fields

The canonical field reference is maintained in
[`docs/methodology.md`](docs/methodology.md#9-posteditingresult).

| Field | Definition |
|---|---|
| `ter_rate` | TER edit cost divided by final reference length; may exceed `1` |
| `ter_effort_saved_raw` | `1 - ter_rate`; may be negative |
| `ter_effort_saved` | Raw TER-derived score bounded to `[0, 1]` |
| `character_edit_distance` | Character-level Levenshtein distance |
| `character_effort_saved_raw` | `1 - character_edit_distance / final_character_count`; may be negative |
| `character_effort_saved` | Raw character score bounded to `[0, 1]` |
| `soft_word_edit_distance` | Weighted word-level edit distance |
| `soft_word_effort_saved_raw` | `1 - soft_word_edit_distance / final_word_count`; may be negative |
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

The definitions below summarize the standard public configuration. See the
canonical [methodology documentation](docs/methodology.md) for complete
direction, preprocessing, formulas, field definitions, and interpretation
limits.

### TER-derived effort saved

The primary measure is:

```text
TER = TER edit cost / final reference length

ter_effort_saved_raw = 1 - TER

ter_effort_saved =
    min(1, max(0, ter_effort_saved_raw))
```

TER is calculated with SacreBLEU using:

```text
normalized     = False
no_punct       = False
asian_support  = False
case_sensitive = False
```

TER includes insertions, deletions, substitutions, and phrase shifts. It is
normalized by final reference length and is case-insensitive under this
configuration.

TER may exceed `1`, making the raw effort-saved score negative.

### Character-level effort saved

```text
character_effort_saved_raw =
    1 - character_edit_distance / final_character_count

character_effort_saved =
    min(1, max(0, character_effort_saved_raw))
```

Character distance uses RapidFuzz Levenshtein distance.

The standard combined API:

- uses Unicode NFC-normalized strings;
- preserves case;
- preserves punctuation;
- uses final character count as the denominator.

It is a technical textual-editing proxy, not a keystroke count.

### Weighted soft-word effort saved

```text
soft_word_effort_saved_raw =
    1 - soft_word_edit_distance / final_word_count

soft_word_effort_saved =
    min(1, max(0, soft_word_effort_saved_raw))
```

At word level:

- insertion cost is `1`;
- deletion cost is `1`;
- substitution cost is normalized character-level Levenshtein distance between
  the two words.

This gives partial credit to small within-word changes, such as replacing
`analyze` with `analyzed`.

The implementation uses a weighted Wagner–Fischer recurrence and retains two
matrix rows. Unlike TER, it has no phrase-shift operation.

This is a custom robustness measure, not standardized TER.

### Estimated characters saved

```text
estimated_characters_saved =
    max(0, final_character_count - character_edit_distance)
```

This helps compare the absolute magnitude of retained text across inputs of
different lengths.

It is not an observed count of avoided characters, typing, or keystrokes.

---

## Preprocessing

Metric inputs are normalized with Unicode NFC.

Under `analyze_post_edit()`:

- TER is case-insensitive;
- character distance is case-sensitive;
- soft-word distance is case-sensitive;
- soft-word tokenization uses whitespace;
- punctuation remains attached to adjacent tokens;
- hyphenated forms remain one token;
- repeated whitespace does not affect tokenization;
- no stemming or lemmatization is performed;
- no embedding, semantic model, thesaurus, or ontology is used.

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

Use `analyze_post_edit()` for the complete standard calculation.

Lower-level functions support focused analysis and research. For example,
soft-word insertion and deletion costs may be configured independently:

```python
distance = weighted_soft_word_distance(
    suggestion="one two",
    final="one",
    insertion_cost=2.0,
    deletion_cost=3.0,
)
```

Changing low-level options produces results outside the standard combined
configuration and should be documented by the caller.

---

## Verification

The package test suite covers:

- metric formulas and denominator direction;
- raw and bounded scores;
- Unicode NFC normalization;
- case behavior;
- empty and invalid inputs;
- configurable soft-word operation costs;
- result immutability;
- public API exports;
- combined-result wiring.

The optimized two-row soft-word implementation is compared with a full-matrix
reference implementation across:

- 1,000 seeded random pairs using standard costs;
- 500 seeded random pairs using unequal insertion and deletion costs;
- explicit empty, repeated-token, and unequal-length cases.

The implementations agree within absolute tolerance `1e-12`.

This establishes implementation consistency for the tested behavior. It does not
establish that the metrics measure human time, cognition, observed keystrokes, or
usefulness.

See the canonical
[verification documentation](docs/verification.md)
for test ownership, boundary cases, seeds, differential-testing procedure,
coverage, and change requirements.

---

## Development

Run commands from the repository root.

Package tests:

```bash
make test PACKAGE=text-post-edit-metrics
```

Package coverage:

```bash
make coverage PACKAGE=text-post-edit-metrics
```

Run only the randomized differential tests:

```bash
make test-slow PACKAGE=text-post-edit-metrics
```

Skip them:

```bash
make test-fast PACKAGE=text-post-edit-metrics
```

Run the complete workspace gate:

```bash
make check
```

Shared setup and contribution guidance are documented in the
[root README](../../../README.md).

---

## Dependencies and reproducibility

| Dependency | Purpose |
|---|---|
| Python 3.14 | Runtime |
| SacreBLEU 2.6.x | TER |
| RapidFuzz 3.14.x | Character-level Levenshtein calculations |

Major versions are bounded because dependency changes could alter reported
values.

Exact resolved versions are recorded in the repository root `uv.lock`.

For published or archived results, record:

- Python and package versions;
- Git revision;
- metric configuration;
- analysis date;
- input counts;
- any nondefault lower-level options.

---

## References

Snover, M., Dorr, B., Schwartz, R., Micciulla, L., & Makhoul, J. (2006).
*A Study of Translation Edit Rate with Targeted Human Annotation*.

Levenshtein, V. I. (1966). Binary codes capable of correcting deletions,
insertions, and reversals.

Wagner, R. A., & Fischer, M. J. (1974). The string-to-string correction
problem.

---

## License

MIT
