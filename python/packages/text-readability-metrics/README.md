# text-readability-metrics

Generic readability analysis for nonblank English text.

## Contract

Use the public API:

```python
from text_readability_metrics import analyze_readability

result = analyze_readability("Synthetic text used for readability analysis.")
```

`analyze_readability()` returns an immutable `ReadabilityResult`.

The package sets the `textstat` language profile to `en_US` before calculating
metrics.

## Result fields

| Field | Meaning | Unit |
|---|---|---|
| `flesch_kincaid_grade` | Flesch-Kincaid grade-level indicator | U.S. grade level |
| `automated_readability_index` | Automated Readability Index grade-level indicator | U.S. grade level |
| `coleman_liau_index` | Coleman-Liau grade-level indicator | U.S. grade level |
| `gunning_fog` | Gunning Fog grade-level indicator | Approximate education years |
| `dale_chall_readability_score` | Dale-Chall difficult-word indicator | Dale-Chall scale |
| `estimated_reading_time_seconds` | `textstat` reading-time estimate | Seconds |
| `sentence_count` | Estimated sentence count | Sentences |
| `word_count` | Estimated lexical word count | Words |
| `syllable_count` | Estimated syllable count | Syllables |
| `letter_count` | Estimated letter count | Letters |
| `polysyllable_count` | Estimated words with multiple syllables | Words |

Scores may legitimately be negative for short or unusual text.

Every score must be finite. Reading time must be finite and nonnegative. Counts
must be nonnegative integers.

## Formula families

The package delegates formulas and underlying text segmentation to `textstat`.
The standard formulas are summarized here for interpretation and independent
checking.

Implementation details can vary across libraries because sentence, word,
character, syllable, and difficult-word counting can vary.

### Flesch-Kincaid grade

Conventional form:

```text
FK grade =
    0.39 × (words / sentences)
    + 11.8 × (syllables / words)
    - 15.59
```

Example:

```text
words = 100
sentences = 5
syllables = 140

FK grade =
    0.39 × 20
    + 11.8 × 1.4
    - 15.59
  = 8.73
```

The package publishes the `textstat` result, not a separately reconstructed
value. Use the same locked `textstat` version when reproducing it.

### Automated Readability Index

Conventional form:

```text
ARI =
    4.71 × (characters / words)
    + 0.5 × (words / sentences)
    - 21.43
```

ARI uses character counts rather than syllables.

### Coleman-Liau Index

Conventional form:

```text
CLI = 0.0588 × L - 0.296 × S - 15.8
```

where:

```text
L = average letters per 100 words
S = average sentences per 100 words
```

### Gunning Fog

Conventional form:

```text
Fog =
    0.4 × (
        words / sentences
        + 100 × complex_words / words
    )
```

The exact treatment of complex or polysyllabic words depends on implementation
rules.

### Dale-Chall

Dale-Chall uses average sentence length and the percentage of words not found
on a familiar-word list.

Its scale is not interchangeable with the grade-level formulas above. The
exploration summarizes Dale-Chall separately when consensus direction is
calculated across grade-level formulas.

### Reading time and counts

`estimated_reading_time_seconds` and all counts are supplied by `textstat`.

Do not attempt to reproduce a score from a report value unless the exact
`textstat` version, language profile, and preprocessing behavior are also used.

## Implementation mapping

The adapter calls these `textstat` methods:

| Published field | Backend operation |
|---|---|
| `flesch_kincaid_grade` | `flesch_kincaid_grade` |
| `automated_readability_index` | `automated_readability_index` |
| `coleman_liau_index` | `coleman_liau_index` |
| `gunning_fog` | `gunning_fog` |
| `dale_chall_readability_score` | `dale_chall_readability_score` |
| `estimated_reading_time_seconds` | `reading_time` |
| `sentence_count` | `sentence_count` |
| `word_count` | `lexicon_count` |
| `syllable_count` | `syllable_count` |
| `letter_count` | `letter_count` |
| `polysyllable_count` | `polysyllabcount` |

The source implementation is under:

```text
python/packages/text-readability-metrics/src/text_readability_metrics/
```

Focused tests are under:

```text
python/packages/text-readability-metrics/tests/
```

## Input validation

Input must be a nonblank string.

Empty and whitespace-only strings raise `InvalidReadabilityTextError`.

Malformed, non-finite, negative-time, or invalid-count backend results raise
`InvalidReadabilityResultError`.

Both exceptions derive from `ReadabilityError`.

## Interpretation

Readability formulas estimate surface characteristics associated with sentence
length, word length, letters, syllables, and familiar-word lists.

They do not determine whether text is:

- correct;
- useful;
- inclusive;
- understandable to a particular audience;
- accessible;
- culturally appropriate;
- well organized;
- ethically adequate.

Short text, especially a title, has limited score reliability.

A lower grade-level indicator is not automatically better. A higher value is
not automatically worse.

Scores can vary across implementations and versions because tokenization,
sentence segmentation, syllable estimation, character rules, and word-list
behavior vary.

The package constrains `textstat` to a compatible version range. The root
`uv.lock` records the exact resolved version.

## Verification

Tests verify:

- the fixed `en_US` language profile;
- exact backend-method mapping;
- immutable result models;
- rejection of blank and non-string input;
- finite score requirements;
- nonnegative reading time;
- nonnegative integer counts;
- real-backend return types and finiteness.

Passing tests show that the adapter follows this contract. They do not
scientifically validate the formulas as measures of comprehension or
accessibility.

## References

- Kincaid, J. P., Fishburne, R. P., Rogers, R. L., and Chissom, B. S.
  *Derivation of New Readability Formulas for Navy Enlisted Personnel*.
- Senter, R. J., and Smith, E. A. *Automated Readability Index*.
- Coleman, M., and Liau, T. L. “A Computer Readability Formula Designed for
  Machine Scoring.”
- Gunning, R. *The Technique of Clear Writing*.
- Dale, E., and Chall, J. S. “A Formula for Predicting Readability.”
- [`textstat` documentation](https://github.com/textstat/textstat).

## Boundary

This package owns:

- generic readability calculation;
- the fixed English profile;
- immutable result modeling;
- input and result validation.

It performs no:

- study-specific field extraction;
- suggestion-selection matching;
- database access;
- CSV or filesystem output;
- report publication;
- command-line processing.

## Development

Run from the repository root:

```bash
make test PACKAGE=text-readability-metrics
make coverage PACKAGE=text-readability-metrics
make check
```

## License

MIT
