"""Reusable technical post-editing metrics.

This package compares an AI-generated suggestion with final human-edited text.
It performs pure calculations only: no database, filesystem, pandas, logging,
or application-specific business rules.

The comparison is directional. Normalized scores use the final text length as
their denominator.
"""

from michr_text_post_editing.models import (
    CharacterResult,
    PostEditingResult,
    SoftWordResult,
    TerResult,
)
from michr_text_post_editing.normalization import (
    clamp01,
    count_whitespace_tokens,
    normalize_metric_text,
)

__version__ = "0.1.0"

__all__ = [
    "CharacterResult",
    "PostEditingResult",
    "SoftWordResult",
    "TerResult",
    "__version__",
    "clamp01",
    "count_whitespace_tokens",
    "normalize_metric_text",
]
