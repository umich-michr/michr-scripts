# Text Post-Edit Metrics: Methodology

**Status:** Canonical methodology for `text-post-edit-metrics`.

This document defines the package's comparison direction, preprocessing,
formulas, result fields, and interpretation limits.

For software-testing methodology, see
[`verification.md`](verification.md).

---

## 1. Purpose

`text-post-edit-metrics` compares an initial text with a value represented by the
caller as its edited or revised form.

```python
from text_post_edit_metrics import analyze_post_edit

result = analyze_post_edit(
    suggestion="Initial or generated text",
    final="Represented edited text",
)
```

The package calculates:

- Translation Edit Rate (TER);
- TER-derived raw and bounded effort-saved scores;
- character-level Levenshtein distance and scores;
- a custom weighted soft-word distance and scores;
- an estimated-characters-saved proxy;
- descriptive character and token counts.

These values quantify textual transformation under a post-editing
interpretation.

The package does not verify that:

- `final` was actually produced by editing `suggestion`;
- editing activity was observed;
- the texts are semantically equivalent;
- the comparison measures human effort, time, or satisfaction.

---

## 2. Comparison direction

The comparison is directional:

- `suggestion` is the initial, generated, or proposed text;
- `final` is the value represented as its edited or revised form;
- normalized denominators use the final text length.

Reversing the arguments can change the result because insertion and deletion are
directional and the denominator comes from `final`.

In the standard combined API:

```python
result = analyze_post_edit(
    suggestion=suggestion,
    final=final,
)
```

An empty suggestion is valid. It represents a comparison in which the entire
final text must be inserted.

The final text must:

- be a string;
- be nonempty;
- contain at least one whitespace-delimited token.

A zero-length final denominator is invalid.

---

## 3. Preprocessing

### 3.1 Unicode normalization

Metric inputs are normalized with Unicode Normalization Form C (`NFC`).

NFC makes canonically equivalent encodings compare consistently. For example, a
precomposed accented character and the equivalent base character followed by a
combining mark become the same normalized representation.

NFC does not intentionally remove:

- punctuation;
- symbols;
- diacritics;
- whitespace;
- capitalization.

These differences remain available to the metrics according to each metric's
configuration.

### 3.2 Case behavior

The standard combined analysis deliberately uses different case behavior across
metric families:

| Metric | Case behavior |
|---|---|
| TER | Case-insensitive |
| Character Levenshtein | Case-sensitive |
| Weighted soft-word | Case-sensitive |

A capitalization-only change may therefore produce:

- TER rate `0`;
- nonzero character distance;
- nonzero soft-word distance.

This is intentional. The supporting metrics preserve evidence of textual edits
that the configured TER calculation ignores.

### 3.3 Tokenization

The custom soft-word measure uses whitespace tokenization.

Consequences:

- punctuation remains attached to adjacent tokens;
- hyphenated forms remain one token;
- repeated whitespace does not alter token boundaries;
- no stemming is performed;
- no lemmatization is performed;
- no semantic model, embedding, thesaurus, or ontology is used.

Semantically related but orthographically different words may therefore receive
substantial substitution costs.

SacreBLEU TER applies its own processing. `final_word_count` must not be used to
reconstruct TER.

---

## 4. TER-derived effort saved

### 4.1 Translation Edit Rate

Translation Edit Rate evaluates the editing required to transform a system
output into a reference.

TER considers:

- word insertion;
- word deletion;
- word substitution;
- movement of a contiguous word sequence, called a shift.

The conventional rate is:

```text
TER = TER edit cost / final reference length
```

TER starts at `0` and may exceed `1`.

### 4.2 Package configuration

TER is calculated with SacreBLEU using:

```text
normalized     = False
no_punct       = False
asian_support  = False
case_sensitive = False
```

The configuration is explicit for reproducibility.

Changing any option can alter reported values and requires compatibility review,
updated documentation, and updated tests.

### 4.3 Effort-saved transformation

The raw directional transformation is:

```text
ter_effort_saved_raw = 1 - ter_rate
```

The bounded reporting score is:

```text
ter_effort_saved =
    min(1, max(0, ter_effort_saved_raw))
```

Interpretation:

| Value | Meaning |
|---|---|
| `ter_rate = 0` | No TER edits were required |
| `ter_rate = 0.25` | TER cost equaled one quarter of final reference length |
| `ter_rate = 1` | TER cost equaled final reference length |
| `ter_rate > 1` | TER cost exceeded final reference length |
| `ter_effort_saved = 1` | No TER edits were required |
| `ter_effort_saved = 0` | TER reached or exceeded the final-length baseline |
| `ter_effort_saved_raw < 0` | TER exceeded the final-length baseline |

The raw score is retained because bounding every negative value to zero would
hide especially costly comparisons.

The score is a technical textual-transformation proxy. It must not be
interpreted as a literal percentage of time, thought, or keystrokes saved.

---

## 5. Character-level effort saved

Character-level Levenshtein distance calculates the minimum number of
single-character operations required to transform `suggestion` into `final`.

Permitted operations:

- insertion;
- deletion;
- substitution.

The raw score is:

```text
character_effort_saved_raw =
    1 - character_edit_distance / final_character_count
```

The bounded score is:

```text
character_effort_saved =
    min(1, max(0, character_effort_saved_raw))
```

The standard combined calculation:

- uses NFC-normalized strings;
- preserves capitalization;
- preserves punctuation;
- uses final character count as its denominator.

A character distance of `0` means the NFC-normalized strings are identical.

This measure is not an observed keystroke count. Actual editing may involve:

- block selection;
- copy and paste;
- cursor movement;
- deletion of selected spans;
- undo and redo operations;
- automated replacements.

---

## 6. Weighted soft-word effort saved

### 6.1 Operation costs

The package implements a custom weighted word-level edit distance.

At word level:

- insertion cost = `1`;
- deletion cost = `1`;
- substitution cost = normalized character-level Levenshtein distance between
  the two words.

Normalized character distance ranges from `0` through `1`:

- `0` means the words are identical;
- values closer to `1` indicate greater orthographic dissimilarity.

This gives partial credit to small within-word changes. For example, replacing
`analyze` with `analyzed` generally costs less than replacing `analyze` with an
orthographically unrelated word.

### 6.2 Dynamic-programming recurrence

The implementation calculates the minimum-cost sequence of insertions,
deletions, and substitutions using a weighted Wagner–Fischer recurrence.

For suggestion prefix position `i` and final prefix position `j`:

```text
distance[i, j] = min(
    distance[i, j - 1]     + insertion_cost,
    distance[i - 1, j]     + deletion_cost,
    distance[i - 1, j - 1] + substitution_cost,
)
```

The production implementation retains only two matrix rows to reduce memory
use.

Unlike TER, the custom soft-word measure does not include phrase-shift
operations.

### 6.3 Effort-saved transformation

The raw score is:

```text
soft_word_effort_saved_raw =
    1 - soft_word_edit_distance / final_word_count
```

The bounded score is:

```text
soft_word_effort_saved =
    min(1, max(0, soft_word_effort_saved_raw))
```

The soft-word result is a supporting robustness measure. It tests whether a
conclusion remains similar when small within-word changes receive fractional
rather than full substitution cost.

It is not standardized TER.

---

## 7. Estimated characters saved

The package calculates:

```text
estimated_characters_saved =
    max(0, final_character_count - character_edit_distance)
```

This is an absolute-scale technical-editing proxy.

It can help distinguish proportional and absolute retention. For example, a
long text may have a lower proportional score than a short text while retaining
more characters overall.

It is not:

- an observed count of characters avoided;
- an observed keystroke count;
- a direct measurement of time saved;
- a direct measurement of cognitive effort.

---

## 8. Raw and bounded scores

Each normalized metric retains:

1. a raw score, which may be negative;
2. a bounded score within `[0, 1]`.

Raw values preserve information about comparisons whose editing cost exceeds the
final-length baseline.

Bounded values are easier to summarize, but they collapse all negative raw
values to `0`.

Both should be retained when results may be used for research, diagnostics, or
quality review.

---

## 9. `PostEditingResult`

`analyze_post_edit()` returns an immutable `PostEditingResult`.

The result contains only generic metric values and descriptive text counts. It
does not contain:

- form-field identity;
- record identity;
- source information;
- selection state;
- product-policy classification.

Those values belong to consuming packages or programs.

### Field reference

| Field | Definition | Recommended use |
|---|---|---|
| `ter_rate` | TER cost divided by final reference length; may exceed `1` | Conventional edit rate |
| `ter_effort_saved_raw` | `1 - ter_rate`; may be negative | Unbounded TER-derived diagnostic |
| `ter_effort_saved` | Raw TER-derived score bounded to `[0, 1]` | Primary bounded reporting score |
| `character_edit_distance` | Character-level Levenshtein distance | Supporting technical edit distance |
| `character_effort_saved_raw` | `1 - distance / final_character_count`; may be negative | Unbounded character diagnostic |
| `character_effort_saved` | Raw character score bounded to `[0, 1]` | Supporting bounded score |
| `soft_word_edit_distance` | Weighted word-level edit distance | Supporting robustness distance |
| `soft_word_effort_saved_raw` | `1 - distance / final_word_count`; may be negative | Unbounded soft-word diagnostic |
| `soft_word_effort_saved` | Raw soft-word score bounded to `[0, 1]` | Supporting bounded score |
| `estimated_characters_saved` | Final character count minus character distance, bounded below at zero | Absolute technical-editing proxy |
| `suggestion_character_count` | Characters in NFC-normalized suggestion | Descriptive length |
| `final_character_count` | Characters in NFC-normalized final | Character denominator and descriptive length |
| `suggestion_word_count` | Whitespace-delimited suggestion tokens | Descriptive length |
| `final_word_count` | Whitespace-delimited final tokens | Soft-word denominator and descriptive length |

---

## 10. Which value answers which question?

| Question | Value |
|---|---|
| What is the conventional TER edit rate? | `ter_rate` |
| What is the primary bounded post-editing score? | `ter_effort_saved` |
| Did TER exceed final reference length? | `ter_effort_saved_raw` |
| What is the exact character edit distance? | `character_edit_distance` |
| Do conclusions hold under character-level scoring? | `character_effort_saved` |
| Do conclusions hold when small within-word changes receive partial credit? | `soft_word_effort_saved` |
| What is the absolute retained-character proxy? | `estimated_characters_saved` |
| Could text length help explain score differences? | Character and word count fields |

---

## 11. Example interpretation

Given:

```text
ter_rate = 0.20
ter_effort_saved = 0.80
character_effort_saved = 0.90
soft_word_effort_saved = 0.86
estimated_characters_saved = 180
```

A careful interpretation is:

> TER cost equaled 20% of final reference length, yielding a bounded
> TER-derived post-editing score of 0.80. Supporting character and soft-word
> scores were also high. The character calculation yielded an absolute
> technical-editing proxy of 180 characters.

It would not be appropriate to conclude:

> The user saved exactly 80% of their time or avoided exactly 180 keystrokes.

---

## 12. Interpretation limits

The package quantifies textual transformation.

It does not directly measure:

- cognitive effort;
- reading or deliberation time;
- elapsed task time;
- observed keystrokes;
- cursor movement;
- block selection;
- copy, paste, or undo operations;
- whether one text was actually produced by editing the other;
- whether the initial text changed the editor's ideas;
- semantic equivalence;
- user satisfaction;
- perceived helpfulness.

A small textual change can follow substantial deliberation. Conversely, a large
textual replacement can be easy in a graphical editor.

Claims about time, cognition, or user benefit require external validation, such
as:

- task-completion time;
- editing-event logs;
- observed keystrokes;
- user ratings;
- qualitative feedback;
- a no-suggestion comparison condition.

---

## 13. Reproducibility

For published or archived results, record:

- Python version;
- `text-post-edit-metrics` version;
- SacreBLEU version;
- RapidFuzz version;
- metric configuration;
- analysis date;
- Git revision;
- input counts;
- any nondefault lower-level options.

Exact workspace dependency versions are recorded in the repository root
`uv.lock`.

Major dependency versions are bounded because upgrades could alter reported
values.

---

## 14. Implementation and checking

Production implementation:

```text
python/packages/text-post-edit-metrics/src/text_post_edit_metrics/
├── metrics.py
├── models.py
└── normalization.py
```

Key mappings:

| Calculation | Implementation |
|---|---|
| TER and TER-derived scores | `calculate_ter_metrics()` |
| Character Levenshtein scores | `calculate_character_metrics()` |
| Weighted soft-word recurrence | `weighted_soft_word_distance()` |
| Weighted soft-word normalized score | `calculate_soft_word_metrics()` |
| Combined result | `analyze_post_edit()` |
| Unicode normalization and token counts | `normalization.py` |

Verification is documented in
[`verification.md`](verification.md)
and implemented under:

```text
python/packages/text-post-edit-metrics/tests/
```

Use the locked dependencies when reproducing report values.

## 15. References

### Translation Edit Rate

Snover, M., Dorr, B., Schwartz, R., Micciulla, L., & Makhoul, J. (2006).
*A Study of Translation Edit Rate with Targeted Human Annotation*.

### Character edit distance

Levenshtein, V. I. (1966). Binary codes capable of correcting deletions,
insertions, and reversals.

### Dynamic-programming edit distance

Wagner, R. A., & Fischer, M. J. (1974). The string-to-string correction
problem.
