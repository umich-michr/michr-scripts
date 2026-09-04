"""Domain vocabulary and result models.

Domain layer. Contains enumerations and frozen dataclasses only. This module
must not import a database driver, pandas, the filesystem, or logging.

Result objects are immutable and slotted. Values that can be derived from other
fields are exposed as properties rather than stored, so they cannot drift out of
agreement with the data they summarize.

See docs/analysis-specification.md sections 5 and 8 for the outcome vocabulary
and field definitions.
"""

from dataclasses import dataclass
from enum import StrEnum

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

#: Categorized text suggestions, as used by compensation analysis. Maps a
#: suggestion category name to the list of strings offered for it.
type Suggestions = dict[str, list[str]]


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class FieldKind(StrEnum):
    """How a configured form field is analyzed.

    Attributes
    ----------
    TEXT
        A list of suggested strings and one saved string.
    LOOKUP
        A list of integer identifiers.
    COMPENSATION
        Categorized text suggestions plus the ``offersCompensation`` Boolean.
    CONTACT
        A nested object holding at most one suggestion per subfield.
    MERGED
        A field reported as part of another field's analysis rather than
        separately. ``offersCompensation`` is merged into compensation.
    """

    TEXT = "TEXT"
    LOOKUP = "LOOKUP"
    COMPENSATION = "COMPENSATION"
    CONTACT = "CONTACT"
    MERGED = "MERGED"


class MatchType(StrEnum):
    """Classification of what became of an AI-provided value.

    Evaluation order for text fields is blank, then exact, then cosmetic,
    then edited. See docs/analysis-specification.md section 5.

    Attributes
    ----------
    EXACT
        The decoded Python strings are exactly equal, or the picked and saved
        lookup sets are identical.
    COSMETIC_EQUIVALENT
        Equal under the study's cosmetic-equivalence transformation:
        differences in case, diacritics, punctuation, symbols, and whitespace
        are ignored.
    EDITED
        A suggestion was applied and substantive differences remain in the
        nonblank final value.
    REMOVED
        A suggestion was selected, but the optional final value was left blank.
    UNASSISTED
        No AI-provided suggestion or lookup value was selected.
    """

    EXACT = "EXACT"
    COSMETIC_EQUIVALENT = "COSMETIC_EQUIVALENT"
    EDITED = "EDITED"
    REMOVED = "REMOVED"
    UNASSISTED = "UNASSISTED"


# ---------------------------------------------------------------------------
# Low-level metric results
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TerResult:
    """TER and its effort-saved transformation.

    Attributes
    ----------
    ter_rate
        TER expressed as a proportion. It can exceed 1.
    effort_saved_raw
        ``1 - ter_rate``. It can be negative.
    effort_saved
        ``effort_saved_raw`` bounded to ``[0, 1]`` for reporting.
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
        Minimum number of character insertions, deletions, and substitutions.
        Not an observed keystroke count.
    effort_saved_raw
        ``1 - distance / final_character_count``. It can be negative.
    effort_saved
        ``effort_saved_raw`` bounded to ``[0, 1]``.
    """

    distance: int
    effort_saved_raw: float
    effort_saved: float


@dataclass(frozen=True, slots=True)
class SoftWordResult:
    """Custom weighted word-level result.

    A supporting robustness measure, not the primary standardized metric.

    Attributes
    ----------
    distance
        Weighted word-level edit distance. Insertions and deletions cost 1;
        a substitution costs the normalized character distance between words.
    effort_saved_raw
        ``1 - distance / final_word_count``. It can be negative.
    effort_saved
        ``effort_saved_raw`` bounded to ``[0, 1]``.
    """

    distance: float
    effort_saved_raw: float
    effort_saved: float


# ---------------------------------------------------------------------------
# Combined editing result
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SuggestionEditingResult:
    """Technical post-editing measures for one applied suggestion.

    Produced only when a suggestion was selected or applied and the final saved
    text is nonblank. Not produced for ``UNASSISTED`` or ``REMOVED`` outcomes,
    because the normalized scores would require a zero denominator.

    These values measure textual transformation. They are proxies for technical
    post-editing effort and do not measure elapsed time, keystrokes, or
    cognitive effort. See docs/analysis-specification.md sections 8 and 16.
    """

    field_name: str

    # Primary TER-derived measure.
    ter_rate: float
    ter_effort_saved_raw: float
    ter_effort_saved: float

    # Character-level robustness measure.
    character_edit_distance: int
    character_effort_saved_raw: float
    character_effort_saved: float

    # Custom soft-word robustness measure.
    soft_word_edit_distance: float
    soft_word_effort_saved_raw: float
    soft_word_effort_saved: float

    # Absolute technical-editing proxy.
    estimated_characters_saved: float

    # Descriptive length values, measured after NFC normalization.
    suggestion_character_count: int
    final_character_count: int
    suggestion_word_count: int
    final_word_count: int


# ---------------------------------------------------------------------------
# Selection identification
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Pick:
    """Identifies the suggestion the user selected.

    Attributes
    ----------
    kind
        Suggestion category or field name.
    index
        Zero-based position of the selected value within the offered list for
        ``kind``. When duplicate suggestions were offered, the first occurrence
        is reported.
    """

    kind: str
    index: int


# ---------------------------------------------------------------------------
# Field analysis results
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TextFieldAnalysis:
    """Analysis of one text field.

    Attributes
    ----------
    suggestion_counts
        Number of suggestions offered, keyed by suggestion category.
    pick
        The selected suggestion, or ``None`` when nothing was selected.
    match
        Outcome classification.
    editing_metrics
        Present when a suggestion was selected and the final text was nonblank.
        ``None`` for ``UNASSISTED`` and ``REMOVED`` outcomes.
    selected_text
        The exact suggestion text selected, or ``None``.
    final_text
        The exact text saved by the user. May be blank for optional fields.
    """

    suggestion_counts: dict[str, int]
    pick: Pick | None
    match: MatchType
    editing_metrics: SuggestionEditingResult | None
    selected_text: str | None
    final_text: str

    @property
    def ter_effort_saved(self) -> float | None:
        """Bounded TER-derived score, or ``None`` when undefined.

        ``None`` indicates that no normalized post-editing score was
        calculated, which occurs for ``UNASSISTED`` and ``REMOVED`` outcomes.
        """
        if self.editing_metrics is None:
            return None

        return self.editing_metrics.ter_effort_saved

    @property
    def policy_adjusted_effort_saved(self) -> float:
        """Product-level reporting score.

        ``EXACT`` and ``COSMETIC_EQUIVALENT`` receive full credit. ``EDITED``
        receives the bounded TER-derived score. ``REMOVED`` and ``UNASSISTED``
        receive zero.

        This is a policy score, not a TER result. See
        docs/analysis-specification.md section 6.
        """
        if self.match in {MatchType.EXACT, MatchType.COSMETIC_EQUIVALENT}:
            return 1.0

        if self.match is MatchType.EDITED and self.editing_metrics is not None:
            return self.editing_metrics.ter_effort_saved

        return 0.0


@dataclass(frozen=True, slots=True)
class CompensationAnalysis(TextFieldAnalysis):
    """Compensation text analysis together with the ``offersCompensation`` flag.

    Boolean acceptance is reported separately from text post-editing scores,
    because the two measure different things. See
    docs/analysis-specification.md section 10.

    Attributes
    ----------
    flag_suggested
        AI-recommended value, or ``None`` when no recommendation was available.
    flag_saved
        Final Boolean saved by the user.
    """

    flag_suggested: bool | None
    flag_saved: bool | None

    @property
    def flag_accepted(self) -> bool | None:
        """Whether the saved value matched the AI recommendation.

        ``None`` means the AI made no recommendation, or no final value was
        available, so no comparison was possible.
        """
        if self.flag_suggested is None:
            return None

        if self.flag_saved is None:
            return None

        return self.flag_suggested == self.flag_saved

    @property
    def flag_changed(self) -> bool | None:
        """Whether the user changed the AI-recommended value.

        ``None`` means no comparison was possible.
        """
        if self.flag_suggested is None:
            return None

        if self.flag_saved is None:
            return None

        return self.flag_suggested != self.flag_saved

    @property
    def compensation_text_required(self) -> bool:
        """Whether compensation text was required.

        Text is required exactly when the saved ``offersCompensation`` value is
        ``True``.
        """
        return self.flag_saved is True


@dataclass(frozen=True, slots=True)
class LookupValueAnalysis:
    """Analysis of offered, picked, and saved lookup identifiers.

    For assisted outcomes, ``similarity`` is the Jaccard similarity between the
    picked and saved sets. When no AI-offered value was picked, the outcome is
    ``UNASSISTED`` and similarity is assigned ``0.0`` as a realized-assistance
    policy value rather than calculated from an empty-set Jaccard formula, which
    would be undefined.

    Lookup similarity must never be averaged together with text effort-saved
    scores; they measure different constructs. See
    docs/analysis-specification.md section 11.

    Attributes
    ----------
    offered
        All identifiers offered by the AI.
    picked
        AI-offered identifiers selected by the user.
    saved
        Final identifiers saved by the user.
    match
        Outcome classification.
    similarity
        Jaccard similarity, or the policy value ``0.0`` when nothing was picked.
    """

    offered: frozenset[int]
    picked: frozenset[int]
    saved: frozenset[int]
    match: MatchType
    similarity: float

    @property
    def kept(self) -> frozenset[int]:
        """Picked values retained in the final saved set."""
        return self.picked & self.saved

    @property
    def dropped(self) -> frozenset[int]:
        """Picked values removed before saving."""
        return self.picked - self.saved

    @property
    def added(self) -> frozenset[int]:
        """Saved values that were not among the picked values."""
        return self.saved - self.picked

    @property
    def saved_not_offered(self) -> frozenset[int]:
        """Saved values that were not present in any AI offer."""
        return self.saved - self.offered


# ---------------------------------------------------------------------------
# Field configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """How one configured form field is analyzed.

    Attributes
    ----------
    kind
        Determines which analyzer handles the field.
    text_required
        Relevant only to ordinary ``TEXT`` fields. Compensation requiredness is
        determined dynamically from the saved ``offersCompensation`` value, and
        contact requiredness is determined per subfield, so both leave this
        ``None``.
    """

    kind: FieldKind
    text_required: bool | None = None


# ---------------------------------------------------------------------------
# Audit record
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AuditRecord:
    """One eligible audit record with its JSON columns decoded.

    An eligible record has ``ATTEMPT_TYPE = 'AI'`` and
    ``ATTEMPT_RESULT = 'COMPLETE'``. The three JSON columns are required to
    decode into JSON objects.

    Attributes
    ----------
    audit_id
        Primary key of the audit row.
    study_num
        Study number, when present.
    start_time
        Attempt start timestamp as stored, or ``None``.
    end_time
        Attempt end timestamp as stored, or ``None``.
    suggested
        Decoded ``LLM_SUGGESTIONS`` object.
    selected
        Decoded ``SELECTED_SUGGESTIONS`` object.
    final
        Decoded ``FINAL_SUBMISSION`` object.
    """

    audit_id: int
    study_num: str | None
    start_time: str | None
    end_time: str | None
    suggested: dict[str, object]
    selected: dict[str, object]
    final: dict[str, object]


# # ---------------------------------------------------------------------------
# # Result union
# # ---------------------------------------------------------------------------

# #: Any result produced for a single analyzed field.
type AnalysisResult = TextFieldAnalysis | CompensationAnalysis | LookupValueAnalysis
