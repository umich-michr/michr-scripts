"""Technical post-editing metrics for AI-generated text.

Pure calculations only: no database, filesystem, pandas, logging, or
application-specific business rules.

The comparison is directional:

- ``suggestion`` is the generated or original text;
- ``final`` is the human-edited reference text;
- normalized scores use the final text length as their denominator.

The primary measure is TER-derived effort saved, ``1 - TER``. Character-level
Levenshtein and weighted soft-word scores are supporting robustness measures.

These values estimate technical textual post-editing. They do not measure
elapsed time, observed keystrokes, cognitive effort, or user satisfaction.
"""

from functools import lru_cache
import math

from rapidfuzz.distance import Levenshtein
from sacrebleu.metrics import TER

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

# Every argument is explicit for reproducibility. Changing this configuration
# changes reported results and requires a documented compatibility decision.
_TER = TER(
    normalized=False,
    no_punct=False,
    asian_support=False,
    case_sensitive=False,
)

_WORD_DISTANCE_CACHE_SIZE = 100_000


def _require_string(value: object, *, parameter_name: str) -> str:
    """Return a value when it is a string.

    The helper accepts ``object`` because values may originate from decoded
    JSON or another untyped boundary. This makes runtime narrowing genuine
    rather than statically redundant.

    Parameters
    ----------
    value
        Value to validate.
    parameter_name
        Name used in the exception message.

    Returns
    -------
    str
        The validated string.

    Raises
    ------
    TypeError
        If the value is not a string.
    """
    if not isinstance(value, str):
        raise TypeError(f"{parameter_name} must be a string")

    return value


@lru_cache(maxsize=_WORD_DISTANCE_CACHE_SIZE)
def normalized_word_distance(
    suggestion_word: str,
    final_word: str,
) -> float:
    """Return normalized character distance between two words.

    This value is used as the weighted soft-word substitution cost.

    Parameters
    ----------
    suggestion_word
        Word from the suggestion.
    final_word
        Word from the final text.

    Returns
    -------
    float
        A value from 0 through 1. Zero means identical; values closer to one
        indicate greater character dissimilarity.
    """
    return Levenshtein.normalized_distance(suggestion_word, final_word)


def calculate_ter_metrics(
    suggestion: str,
    final: str,
) -> TerResult:
    """Calculate TER and its effort-saved transformation.

    TER is case-insensitive under this package's fixed configuration.

    Parameters
    ----------
    suggestion
        Generated or original text.
    final
        Human-edited reference text.

    Returns
    -------
    TerResult
        TER rate plus raw and bounded effort-saved scores.

    Raises
    ------
    ValueError
        If the final text contains no words, because TER's denominator would
        be zero.
    """
    normalized_suggestion = normalize_metric_text(
        suggestion,
        case_sensitive=True,
    )
    normalized_final = normalize_metric_text(
        final,
        case_sensitive=True,
    )

    if count_whitespace_tokens(normalized_final) == 0:
        raise ValueError("TER is undefined when the final text contains no words")

    ter_percentage = _TER.sentence_score(
        normalized_suggestion,
        [normalized_final],
    ).score

    ter_rate = ter_percentage / 100.0
    effort_saved_raw = 1.0 - ter_rate

    return TerResult(
        ter_rate=ter_rate,
        effort_saved_raw=effort_saved_raw,
        effort_saved=clamp01(effort_saved_raw),
    )


def calculate_character_metrics(
    suggestion: str,
    final: str,
    *,
    case_sensitive: bool = True,
) -> CharacterResult:
    """Calculate directional character-level post-editing metrics.

    Parameters
    ----------
    suggestion
        Generated or original text.
    final
        Human-edited reference text.
    case_sensitive
        Whether capitalization differences contribute to the distance.

    Returns
    -------
    CharacterResult
        Character distance plus raw and bounded effort-saved scores.

    Raises
    ------
    ValueError
        If the final text is empty, because the denominator would be zero.
    """
    normalized_suggestion = normalize_metric_text(
        suggestion,
        case_sensitive=case_sensitive,
    )
    normalized_final = normalize_metric_text(
        final,
        case_sensitive=case_sensitive,
    )

    number_of_final_characters = len(normalized_final)

    if number_of_final_characters == 0:
        raise ValueError("Character effort saved is undefined when final text is empty")

    character_distance = Levenshtein.distance(
        normalized_suggestion,
        normalized_final,
    )

    effort_saved_raw = 1.0 - (character_distance / number_of_final_characters)

    return CharacterResult(
        distance=character_distance,
        effort_saved_raw=effort_saved_raw,
        effort_saved=clamp01(effort_saved_raw),
    )


def weighted_soft_word_distance(
    suggestion: str,
    final: str,
    *,
    insertion_cost: float = 1.0,
    deletion_cost: float = 1.0,
    case_sensitive: bool = True,
) -> float:
    """Calculate weighted word-level edit distance.

    Operations:

    - insert one final-text word: ``insertion_cost``;
    - delete one suggestion word: ``deletion_cost``;
    - substitute one word: normalized character-level Levenshtein distance
      between the suggestion and final words.

    The implementation uses a weighted Wagner-Fischer recurrence and retains
    only two matrix rows to reduce memory use. Unlike TER, it does not include
    phrase-shift operations.

    Parameters
    ----------
    suggestion
        Generated or original text.
    final
        Human-edited reference text.
    insertion_cost
        Cost of inserting one final-text word.
    deletion_cost
        Cost of deleting one suggestion word.
    case_sensitive
        Whether capitalization differences contribute to substitution cost.

    Returns
    -------
    float
        Minimum weighted edit cost.

    Raises
    ------
    ValueError
        If either insertion or deletion cost is negative or non-finite.
    """
    for cost_name, cost_value in (
        ("insertion_cost", insertion_cost),
        ("deletion_cost", deletion_cost),
    ):
        if not math.isfinite(cost_value):
            raise ValueError(f"{cost_name} must be finite")

        if cost_value < 0:
            raise ValueError(f"{cost_name} must be non-negative")

    normalized_suggestion = normalize_metric_text(
        suggestion,
        case_sensitive=case_sensitive,
    )
    normalized_final = normalize_metric_text(
        final,
        case_sensitive=case_sensitive,
    )

    suggestion_words = normalized_suggestion.split()
    final_words = normalized_final.split()

    number_of_suggestion_words = len(suggestion_words)
    number_of_final_words = len(final_words)

    if number_of_suggestion_words == 0:
        return number_of_final_words * insertion_cost

    if number_of_final_words == 0:
        return number_of_suggestion_words * deletion_cost

    # Transform an empty suggestion prefix into each final prefix.
    previous_row = [
        final_prefix_length * insertion_cost
        for final_prefix_length in range(number_of_final_words + 1)
    ]

    for suggestion_position in range(1, number_of_suggestion_words + 1):
        suggestion_word = suggestion_words[suggestion_position - 1]

        # Transform the current suggestion prefix into an empty final prefix.
        current_row = [suggestion_position * deletion_cost]

        for final_position in range(1, number_of_final_words + 1):
            final_word = final_words[final_position - 1]

            substitution_cost = normalized_word_distance(
                suggestion_word,
                final_word,
            )

            cost_after_insertion = current_row[final_position - 1] + insertion_cost
            cost_after_deletion = previous_row[final_position] + deletion_cost
            cost_after_substitution = (
                previous_row[final_position - 1] + substitution_cost
            )

            current_row.append(
                min(
                    cost_after_insertion,
                    cost_after_deletion,
                    cost_after_substitution,
                )
            )

        previous_row = current_row

    return previous_row[number_of_final_words]


def calculate_soft_word_metrics(
    suggestion: str,
    final: str,
    *,
    insertion_cost: float = 1.0,
    deletion_cost: float = 1.0,
    case_sensitive: bool = True,
) -> SoftWordResult:
    """Calculate weighted soft-word post-editing metrics.

    Parameters
    ----------
    suggestion
        Generated or original text.
    final
        Human-edited reference text.
    insertion_cost
        Cost of inserting one final-text word.
    deletion_cost
        Cost of deleting one suggestion word.
    case_sensitive
        Whether capitalization differences contribute to substitution cost.

    Returns
    -------
    SoftWordResult
        Weighted distance plus raw and bounded effort-saved scores.

    Raises
    ------
    ValueError
        If the final text contains no words, because the denominator would be
        zero.
    """
    normalized_final = normalize_metric_text(
        final,
        case_sensitive=case_sensitive,
    )

    number_of_final_words = count_whitespace_tokens(normalized_final)

    if number_of_final_words == 0:
        raise ValueError(
            "Soft-word effort saved is undefined when final text contains no words"
        )

    distance = weighted_soft_word_distance(
        suggestion,
        final,
        insertion_cost=insertion_cost,
        deletion_cost=deletion_cost,
        case_sensitive=case_sensitive,
    )

    effort_saved_raw = 1.0 - distance / number_of_final_words

    return SoftWordResult(
        distance=distance,
        effort_saved_raw=effort_saved_raw,
        effort_saved=clamp01(effort_saved_raw),
    )


def analyze_post_edit(
    suggestion: str,
    final: str,
) -> PostEditingResult:
    """Analyze technical post-editing between suggestion and final text.

    This is the package's primary entry point.

    An empty suggestion is valid: it represents a baseline where the entire
    final text had to be inserted. The final text must be nonempty and contain
    at least one whitespace-delimited token.

    Parameters
    ----------
    suggestion
        Generated or original text.
    final
        Human-edited reference text.

    Returns
    -------
    PostEditingResult
        TER, character, soft-word, absolute-proxy, and length measures.

    Raises
    ------
    TypeError
        If either argument is not a string.
    ValueError
        If the final text is empty or contains no words.
    """
    suggestion = _require_string(
        suggestion,
        parameter_name="suggestion",
    )
    final = _require_string(
        final,
        parameter_name="final",
    )

    normalized_suggestion = normalize_metric_text(
        suggestion,
        case_sensitive=True,
    )
    normalized_final = normalize_metric_text(
        final,
        case_sensitive=True,
    )

    final_character_count = len(normalized_final)
    final_word_count = count_whitespace_tokens(normalized_final)

    if final_character_count == 0:
        raise ValueError("The final text must not be empty")

    if final_word_count == 0:
        raise ValueError("The final text must contain at least one word")

    ter_result = calculate_ter_metrics(
        normalized_suggestion,
        normalized_final,
    )
    character_result = calculate_character_metrics(
        normalized_suggestion,
        normalized_final,
        case_sensitive=True,
    )
    soft_word_result = calculate_soft_word_metrics(
        normalized_suggestion,
        normalized_final,
        case_sensitive=True,
    )

    suggestion_character_count = len(normalized_suggestion)
    suggestion_word_count = count_whitespace_tokens(normalized_suggestion)

    estimated_characters_saved = max(
        0.0,
        float(final_character_count - character_result.distance),
    )

    return PostEditingResult(
        ter_rate=ter_result.ter_rate,
        ter_effort_saved_raw=ter_result.effort_saved_raw,
        ter_effort_saved=ter_result.effort_saved,
        character_edit_distance=character_result.distance,
        character_effort_saved_raw=character_result.effort_saved_raw,
        character_effort_saved=character_result.effort_saved,
        soft_word_edit_distance=soft_word_result.distance,
        soft_word_effort_saved_raw=soft_word_result.effort_saved_raw,
        soft_word_effort_saved=soft_word_result.effort_saved,
        estimated_characters_saved=estimated_characters_saved,
        suggestion_character_count=suggestion_character_count,
        final_character_count=final_character_count,
        suggestion_word_count=suggestion_word_count,
        final_word_count=final_word_count,
    )
