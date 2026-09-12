"""Generic semantic readability metric calculation."""

from typing import Protocol

import textstat

from text_readability_metrics.errors import InvalidReadabilityTextError
from text_readability_metrics.models import ReadabilityResult

_LANGUAGE = "en_US"


class _TextstatBackend(Protocol):
    """Subset of textstat used by this package."""

    def set_lang(self, lang: str) -> None: ...

    def flesch_kincaid_grade(self, text: str) -> float: ...

    def automated_readability_index(self, text: str) -> float: ...

    def coleman_liau_index(self, text: str) -> float: ...

    def gunning_fog(self, text: str) -> float: ...

    def dale_chall_readability_score(self, text: str) -> float: ...

    def reading_time(self, text: str) -> float: ...

    def sentence_count(self, text: str) -> int: ...

    def lexicon_count(self, text: str) -> int: ...

    def syllable_count(self, text: str) -> int: ...

    def letter_count(self, text: str) -> int: ...

    def polysyllabcount(self, text: str) -> int: ...


def _require_text(value: object) -> str:
    """Return nonblank readability input text."""
    if not isinstance(value, str):
        raise InvalidReadabilityTextError("text must be a string")

    if not value.strip():
        raise InvalidReadabilityTextError("text must not be blank")

    return value


def _analyze_with_backend(
    text: str,
    *,
    backend: _TextstatBackend,
) -> ReadabilityResult:
    """Calculate one immutable result with an injected backend."""
    backend.set_lang(_LANGUAGE)

    return ReadabilityResult(
        flesch_kincaid_grade=backend.flesch_kincaid_grade(text),
        automated_readability_index=backend.automated_readability_index(text),
        coleman_liau_index=backend.coleman_liau_index(text),
        gunning_fog=backend.gunning_fog(text),
        dale_chall_readability_score=backend.dale_chall_readability_score(text),
        estimated_reading_time_seconds=backend.reading_time(text),
        sentence_count=backend.sentence_count(text),
        word_count=backend.lexicon_count(text),
        syllable_count=backend.syllable_count(text),
        letter_count=backend.letter_count(text),
        polysyllable_count=backend.polysyllabcount(text),
    )


def analyze_readability(text: str) -> ReadabilityResult:
    """Analyze one nonblank English text value."""
    canonical_text = _require_text(text)
    backend = textstat

    return _analyze_with_backend(
        canonical_text,
        backend=backend,
    )
