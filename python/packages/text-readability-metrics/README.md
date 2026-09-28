# text-readability-metrics

Generic readability analysis for nonblank English text.

```python
from text_readability_metrics import analyze_readability

result = analyze_readability("Synthetic text used for readability analysis.")
```

`analyze_readability()` returns an immutable `ReadabilityResult` and sets the
`textstat` language profile to `en_US`.

## Result fields

| Field | Meaning |
|---|---|
| `flesch_kincaid_grade` | Flesch-Kincaid grade indicator |
| `automated_readability_index` | Automated Readability Index |
| `coleman_liau_index` | Coleman-Liau Index |
| `gunning_fog` | Gunning Fog indicator |
| `dale_chall_readability_score` | Dale-Chall difficult-word indicator |
| `estimated_reading_time_seconds` | `textstat` reading-time estimate |
| Counts | Sentences, words, syllables, letters, and polysyllables |

Scores may legitimately be negative for short or unusual text. Every score must
be finite. Reading time and counts must be nonnegative.

The package publishes `textstat` results rather than independently reconstructed
formula values. Exact reproduction requires the locked `textstat` version and
language profile.

## Validation

Input must be a nonblank string.

- Invalid text raises `InvalidReadabilityTextError`.
- Malformed, non-finite, negative-time, or invalid-count backend output raises
  `InvalidReadabilityResultError`.

Both derive from `ReadabilityError`.

## Interpretation

Readability formulas describe surface features such as sentence length, word
length, letters, syllables, and familiar-word lists.

They do not establish:

- comprehension;
- accuracy;
- accessibility;
- inclusiveness;
- usefulness;
- cultural appropriateness;
- writing quality.

Short text, especially titles, has limited reliability. Lower is not
automatically better, and higher is not automatically worse.

## Boundary

The package owns generic readability calculation, the fixed English profile,
immutable results, and validation.

It performs no study-field extraction, suggestion matching, database access,
CSV output, reporting, or CLI processing.

## Verification and reproducibility

Tests verify backend-method mapping, the fixed language profile, result
validation, immutability, and real-backend return types.

Exact dependency versions are in the root `uv.lock`. Record the Git revision,
Python/package versions, language profile, and analysis date when archiving
results.

## Development

```bash
make test PACKAGE=text-readability-metrics
make coverage PACKAGE=text-readability-metrics
make check
```

## License

MIT
