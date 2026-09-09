"""Reusable technical post-editing metrics.

This package compares an AI-generated suggestion with final human-edited text.
It performs pure calculations only: no database, filesystem, pandas, logging,
or application-specific business rules.

The comparison is directional. Normalized scores use the final text length as
their denominator.
"""

from text_post_edit_metrics.metrics import (
    analyze_post_edit,
    calculate_character_metrics,
    calculate_soft_word_metrics,
    calculate_ter_metrics,
    normalized_word_distance,
    weighted_soft_word_distance,
)
from text_post_edit_metrics.models import (
    CharacterResult,
    PostEditingResult,
    SoftWordResult,
    TerResult,
)
from text_post_edit_metrics.normalization import (
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
    "analyze_post_edit",
    "calculate_character_metrics",
    "calculate_soft_word_metrics",
    "calculate_ter_metrics",
    "clamp01",
    "count_whitespace_tokens",
    "normalize_metric_text",
    "normalized_word_distance",
    "weighted_soft_word_distance",
]
