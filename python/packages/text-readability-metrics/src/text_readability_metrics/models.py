"""Immutable result models for text readability analysis."""

from dataclasses import dataclass
from math import isfinite

from text_readability_metrics.errors import InvalidReadabilityResultError

_FLOAT_FIELD_NAMES: tuple[str, ...] = (
    "flesch_kincaid_grade",
    "automated_readability_index",
    "coleman_liau_index",
    "gunning_fog",
    "dale_chall_readability_score",
    "estimated_reading_time_seconds",
)

_COUNT_FIELD_NAMES: tuple[str, ...] = (
    "sentence_count",
    "word_count",
    "syllable_count",
    "letter_count",
    "polysyllable_count",
)


@dataclass(frozen=True, slots=True)
class ReadabilityResult:
    """Semantic readability metrics and supporting counts."""

    flesch_kincaid_grade: float
    automated_readability_index: float
    coleman_liau_index: float
    gunning_fog: float
    dale_chall_readability_score: float
    estimated_reading_time_seconds: float
    sentence_count: int
    word_count: int
    syllable_count: int
    letter_count: int
    polysyllable_count: int

    def __post_init__(self) -> None:
        """Reject malformed, non-finite, and negative result values."""
        for field_name in _FLOAT_FIELD_NAMES:
            value = getattr(self, field_name)

            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise InvalidReadabilityResultError(
                    f"{field_name} must be a finite number"
                )

            canonical_value = float(value)

            if not isfinite(canonical_value):
                raise InvalidReadabilityResultError(
                    f"{field_name} must be a finite number"
                )

            if field_name == "estimated_reading_time_seconds" and canonical_value < 0:
                raise InvalidReadabilityResultError(
                    "estimated_reading_time_seconds must not be negative"
                )

            object.__setattr__(self, field_name, canonical_value)

        for field_name in _COUNT_FIELD_NAMES:
            value = getattr(self, field_name)

            if isinstance(value, bool) or not isinstance(value, int):
                raise InvalidReadabilityResultError(
                    f"{field_name} must be a nonnegative integer"
                )

            if value < 0:
                raise InvalidReadabilityResultError(
                    f"{field_name} must be a nonnegative integer"
                )
