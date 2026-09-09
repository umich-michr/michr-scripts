"""Immutable result models for technical post-editing metrics.

Pure data models only: no database, filesystem, pandas, logging, or
application-specific business rules.

The comparison is directional:

- ``suggestion`` is the generated or original text;
- ``final`` is the human-edited reference text;
- normalized effort-saved scores use the final text length as their
  denominator.

These results measure textual transformation. They do not measure elapsed time,
observed keystrokes, cognitive effort, or user satisfaction.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TerResult:
    """TER and its effort-saved transformation.

    Attributes
    ----------
    ter_rate
        Translation Edit Rate expressed as a proportion. It may exceed 1.
    effort_saved_raw
        ``1 - ter_rate``. It may be negative.
    effort_saved
        ``effort_saved_raw`` bounded to the interval ``[0, 1]``.
    """

    ter_rate: float
    effort_saved_raw: float
    effort_saved: float


@dataclass(frozen=True, slots=True)
class CharacterResult:
    """Character-level Levenshtein results.

    Attributes
    ----------
    distance
        Minimum number of character insertions, deletions, and substitutions
        required to transform the suggestion into the final text.
    effort_saved_raw
        ``1 - distance / final_character_count``. It may be negative.
    effort_saved
        ``effort_saved_raw`` bounded to the interval ``[0, 1]``.
    """

    distance: int
    effort_saved_raw: float
    effort_saved: float


@dataclass(frozen=True, slots=True)
class SoftWordResult:
    """Weighted word-level post-editing results.

    This is a supporting robustness measure rather than a standardized TER
    result.

    Attributes
    ----------
    distance
        Weighted word-level edit distance. Insertions and deletions cost 1 by
        default; substitutions cost the normalized character distance between
        the two words.
    effort_saved_raw
        ``1 - distance / final_word_count``. It may be negative.
    effort_saved
        ``effort_saved_raw`` bounded to the interval ``[0, 1]``.
    """

    distance: float
    effort_saved_raw: float
    effort_saved: float


@dataclass(frozen=True, slots=True)
class PostEditingResult:
    """Combined technical post-editing metrics for two texts.

    Produced by comparing an AI-generated suggestion with the final
    human-edited text.

    Attributes
    ----------
    ter_rate
        TER edit cost divided by final reference length.
    ter_effort_saved_raw
        ``1 - ter_rate``. It may be negative.
    ter_effort_saved
        Bounded TER-derived reporting score.
    character_edit_distance
        Character-level Levenshtein distance.
    character_effort_saved_raw
        Character score before bounding.
    character_effort_saved
        Bounded character-level score.
    soft_word_edit_distance
        Weighted word-level distance.
    soft_word_effort_saved_raw
        Soft-word score before bounding.
    soft_word_effort_saved
        Bounded soft-word score.
    estimated_characters_saved
        ``max(0, final_character_count - character_edit_distance)``.
        This is a technical proxy, not an observed keystroke count.
    suggestion_character_count
        Number of Python characters in the NFC-normalized suggestion.
    final_character_count
        Number of Python characters in the NFC-normalized final text.
    suggestion_word_count
        Number of whitespace-delimited suggestion tokens.
    final_word_count
        Number of whitespace-delimited final-text tokens.
    """

    ter_rate: float
    ter_effort_saved_raw: float
    ter_effort_saved: float

    character_edit_distance: int
    character_effort_saved_raw: float
    character_effort_saved: float

    soft_word_edit_distance: float
    soft_word_effort_saved_raw: float
    soft_word_effort_saved: float

    estimated_characters_saved: float

    suggestion_character_count: int
    final_character_count: int
    suggestion_word_count: int
    final_word_count: int
