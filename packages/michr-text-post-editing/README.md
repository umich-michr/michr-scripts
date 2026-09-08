# michr-text-post-editing

Reusable technical post-editing metrics for comparing an AI-generated
suggestion with the final human-edited text.

## Planned API

```python
from michr_text_post_editing import analyze_post_edit

result = analyze_post_edit(
    suggestion="Support analysis of research data.",
    final="Support analysis of clinical research data.",
)
```

The comparison is directional:

- `suggestion` is the original generated text;
- `final` is the revised human-saved text;
- normalized scores use the final text length as their denominator.

The package will provide:

- TER and TER-derived effort-saved scores;
- character-level Levenshtein metrics;
- weighted soft-word metrics;
- an estimated-characters-saved proxy;
- descriptive character and word counts.

These are proxies for **technical textual post-editing effort**. They do not
measure time saved, cognitive effort, observed keystrokes, or user satisfaction.

The implementation is being extracted from
`study-posting-ai-analysis`. Until that extraction is complete, the public
surface contains only package metadata.
