"""Technical post-editing metrics for applied LLM text suggestions.

Domain layer. Pure functions only: no database, filesystem, pandas, or logging
dependencies.

This module compares an LLM suggestion that was applied to an editable field
with the final text saved after any user editing.

Primary measure
    TER-derived effort saved, ``1 - TER``. When an LLM-generated suggestion was
    applied to an editable field, the final saved text is treated as its human
    post-edited version, so TER is used in an HTER-style analysis following
    Snover et al. (2006).

Supporting measures
    Character-level Levenshtein effort saved, and a custom weighted soft-word
    effort saved.

These measures quantify textual or technical post-editing. They do not measure
cognitive effort, elapsed time, observed keystrokes, or overall user utility.
See docs/analysis-specification.md sections 7 and 16.
"""

from functools import lru_cache
import math

from rapidfuzz.distance import Levenshtein
from sacrebleu.metrics import TER

from study_posting_ai_analysis.models import (
    CharacterResult,
    SoftWordResult,
    SuggestionEditingResult,
    TerResult,
)
from study_posting_ai_analysis.text_normalization import (
    clamp01,
    count_whitespace_tokens,
    unicode_nfc_normalize_text,
)
from study_posting_ai_analysis.validation import (
    require_non_blank_string,
    require_string,
)

# Every argument is stated explicitly for reproducibility. Changing any of
# these alters reported scores and requires a specification amendment; see
# docs/analysis-specification.md section 7.1.
_TER = TER(
    normalized=False,
    no_punct=False,
    asian_support=False,
    case_sensitive=False,
)

# Cache size chosen to cover repeated word pairs across a full batch. The
# function must stay a module-level function of two strings for caching to be
# effective.
_WORD_DISTANCE_CACHE_SIZE = 100_000


@lru_cache(maxsize=_WORD_DISTANCE_CACHE_SIZE)
def normalized_word_distance(
    suggestion_word: str,
    final_word: str,
) -> float:
    """Return the normalized character distance between two words.

    Used as the soft-word substitution cost, so that small within-word changes
    are charged a fraction of a full word substitution.

    Parameters
    ----------
    suggestion_word
        Word from the suggestion.
    final_word
        Word from the final saved text.

    Returns
    -------
    float
        A value from 0 through 1, where 0 means identical and values closer to
        1 indicate greater character dissimilarity.
    """
    return Levenshtein.normalized_distance(suggestion_word, final_word)


def calculate_ter_metrics(suggestion: str, final: str) -> TerResult:
    """Calculate TER and its effort-saved transformation.

    The suggestion had been applied to the editable field before the final text
    was produced, so the comparison is interpreted as an HTER-style technical
    post-editing setup.

    TER is case-insensitive under the configuration declared in this module.

    Parameters
    ----------
    suggestion
        The applied LLM suggestion.
    final
        The final text saved by the user.

    Returns
    -------
    TerResult
        The TER rate together with raw and bounded effort-saved scores.

    Raises
    ------
    ValueError
        If the final text contains no words, because TER's reference-length
        denominator would be zero.
    """
    normalized_suggestion = unicode_nfc_normalize_text(
        suggestion,
        case_sensitive=True,
    )
    normalized_final = unicode_nfc_normalize_text(final, case_sensitive=True)

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

    The distance is the minimum number of single-character insertions,
    deletions, and substitutions required to transform the suggestion into the
    final text. It is a technical-editing proxy, not an observed keystroke
    count.

    Parameters
    ----------
    suggestion
        The applied LLM suggestion.
    final
        The final text saved by the user.
    case_sensitive
        When ``False``, case differences are ignored. The study-level
        configuration preserves case.

    Returns
    -------
    CharacterResult
        The distance together with raw and bounded effort-saved scores.

    Raises
    ------
    ValueError
        If the final text is empty, because the denominator would be zero.
    """
    normalized_suggestion = unicode_nfc_normalize_text(
        suggestion,
        case_sensitive=case_sensitive,
    )
    normalized_final = unicode_nfc_normalize_text(
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

    effort_saved_raw = 1.0 - character_distance / number_of_final_characters

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
    """Calculate the weighted word-level edit distance from suggestion to final.

    Operations and their costs:

    - insert one final-text word: ``insertion_cost``;
    - delete one suggestion word: ``deletion_cost``;
    - substitute one word for another: the normalized character-level
      Levenshtein distance between them.

    The implementation uses a weighted Wagner-Fischer dynamic-programming
    recurrence and retains only two matrix rows to reduce memory use. A
    full-matrix reference implementation in ``tests/helpers`` verifies this
    optimization.

    Unlike TER, this measure does not include phrase-shift operations.

    Parameters
    ----------
    suggestion
        The applied LLM suggestion.
    final
        The final text saved by the user.
    insertion_cost
        Cost of inserting one word. Must be finite and non-negative.
    deletion_cost
        Cost of deleting one word. Must be finite and non-negative.
    case_sensitive
        When ``False``, case differences are ignored.

    Returns
    -------
    float
        The minimum total weighted cost.

    Raises
    ------
    ValueError
        If either operation cost is not finite or is negative.
    """
    for cost_name, cost_value in (
        ("insertion_cost", insertion_cost),
        ("deletion_cost", deletion_cost),
    ):
        if not math.isfinite(cost_value):
            raise ValueError(f"{cost_name} must be finite")

        if cost_value < 0:
            raise ValueError(f"{cost_name} must be non-negative")

    normalized_suggestion = unicode_nfc_normalize_text(
        suggestion,
        case_sensitive=case_sensitive,
    )
    normalized_final = unicode_nfc_normalize_text(
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

    # Row zero: transform an empty suggestion prefix into each final prefix by
    # inserting every final word.
    previous_row = [
        final_prefix_length * insertion_cost
        for final_prefix_length in range(number_of_final_words + 1)
    ]

    for suggestion_position in range(1, number_of_suggestion_words + 1):
        suggestion_word = suggestion_words[suggestion_position - 1]

        # Column zero: transform the current suggestion prefix into an empty
        # final prefix by deleting every processed suggestion word.
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
    """Calculate the custom weighted soft-word post-editing score.

    This is a supporting robustness measure. It tests whether conclusions remain
    similar when small within-word changes receive partial credit rather than
    being charged as complete word substitutions. It must not replace the
    primary TER-derived result unless separately validated.

    Parameters
    ----------
    suggestion
        The applied LLM suggestion.
    final
        The final text saved by the user.
    insertion_cost
        Cost of inserting one word.
    deletion_cost
        Cost of deleting one word.
    case_sensitive
        When ``False``, case differences are ignored. The study-level
        configuration preserves case.

    Returns
    -------
    SoftWordResult
        The distance together with raw and bounded effort-saved scores.

    Raises
    ------
    ValueError
        If the final text contains no words, because the denominator would be
        zero.
    """
    normalized_final = unicode_nfc_normalize_text(
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


def analyze_selected_suggestion(
    field_name: str,
    suggestion: str,
    final: str,
) -> SuggestionEditingResult:
    """Analyze a text suggestion that was applied to a field and then saved.

    Call this only when all three conditions hold:

    1. an LLM suggestion was shown;
    2. the user selected or inserted that suggestion; and
    3. a nonblank final field value was saved.

    Suggestions that were shown but not selected belong to suggestion
    acceptance-rate reporting and are analyzed separately.

    Parameters
    ----------
    field_name
        Name of the form field, such as ``"title"`` or ``"description"``.
    suggestion
        The exact LLM suggestion the user applied.
    final
        The exact field text the user ultimately saved.

    Returns
    -------
    SuggestionEditingResult
        Primary and supporting technical post-editing measures, together with
        descriptive length counts.

    Raises
    ------
    ValueError
        If ``field_name`` is blank, or if the final text is empty or contains no
        words.
    TypeError
        If ``suggestion`` or ``final`` is not a string.
    """
    # Values reach this function from decoded JSON, so their types are checked
    # at runtime even though the signature documents them as strings.
    field_name = require_non_blank_string(
        field_name,
        parameter_name="field_name",
    )
    suggestion = require_string(suggestion, parameter_name="suggestion")
    final = require_string(final, parameter_name="final")

    normalized_suggestion = unicode_nfc_normalize_text(
        suggestion,
        case_sensitive=True,
    )
    normalized_final = unicode_nfc_normalize_text(final, case_sensitive=True)

    final_character_count = len(normalized_final)
    final_word_count = count_whitespace_tokens(normalized_final)

    if final_character_count == 0:
        raise ValueError("The final saved text must not be empty")

    if final_word_count == 0:
        raise ValueError("The final saved text must contain at least one word")

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

    # An absolute technical-editing proxy: the final character count less the
    # character edit distance. Bounded below at zero, because a suggestion
    # requiring more edits than the length of the final text should not report
    # negative characters saved. This is not a count of avoided keystrokes.
    estimated_characters_saved = max(
        0.0,
        float(final_character_count - character_result.distance),
    )

    return SuggestionEditingResult(
        field_name=field_name,
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
