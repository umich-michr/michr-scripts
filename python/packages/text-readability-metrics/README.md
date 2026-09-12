# text-readability-metrics

Generic readability analysis for nonblank English text.

The package will expose:

```python
from text_readability_metrics import analyze_readability

result = analyze_readability("Synthetic text used for readability analysis.")
```

The result includes:

- Flesch–Kincaid Grade Level;
- Automated Readability Index;
- Coleman–Liau Index;
- Gunning Fog;
- Dale–Chall Readability Score;
- estimated reading time in seconds;
- sentence, word, syllable, letter, and polysyllable counts.

This package owns generic metric calculation and result validation. It performsno study-specific field extraction, database access, CSV output, reportpublication, or command-line processing.
