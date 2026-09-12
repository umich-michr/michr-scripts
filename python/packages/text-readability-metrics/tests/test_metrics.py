"""Tests for generic readability metric calculation."""

from math import isfinite

import pytest

from text_readability_metrics import (
    InvalidReadabilityTextError,
    ReadabilityResult,
    analyze_readability,
    metrics,
)


class FakeTextstat:
    """Record backend calls and return deterministic metric values."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.language: str | None = None

    def set_lang(self, lang: str) -> None:
        self.language = lang

    def _record(self, name: str, text: str, value: float | int) -> float | int:
        self.calls.append((name, text))
        return value

    def flesch_kincaid_grade(self, text: str) -> float:
        return float(self._record("flesch_kincaid_grade", text, 1.1))

    def automated_readability_index(self, text: str) -> float:
        return float(self._record("automated_readability_index", text, 2.2))

    def coleman_liau_index(self, text: str) -> float:
        return float(self._record("coleman_liau_index", text, 3.3))

    def gunning_fog(self, text: str) -> float:
        return float(self._record("gunning_fog", text, 4.4))

    def dale_chall_readability_score(self, text: str) -> float:
        return float(self._record("dale_chall_readability_score", text, 5.5))

    def reading_time(self, text: str) -> float:
        return float(self._record("reading_time", text, 6.6))

    def sentence_count(self, text: str) -> int:
        return int(self._record("sentence_count", text, 7))

    def lexicon_count(self, text: str) -> int:
        return int(self._record("lexicon_count", text, 8))

    def syllable_count(self, text: str) -> int:
        return int(self._record("syllable_count", text, 9))

    def letter_count(self, text: str) -> int:
        return int(self._record("letter_count", text, 10))

    def polysyllabcount(self, text: str) -> int:
        return int(self._record("polysyllabcount", text, 11))


@pytest.mark.parametrize("value", [None, 17, True, b"text"])
def test_analyze_readability_requires_string(value: object) -> None:
    with pytest.raises(
        InvalidReadabilityTextError,
        match="text must be a string",
    ):
        analyze_readability(value)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", ["", " ", "\t\r\n"])
def test_analyze_readability_rejects_blank_text(value: str) -> None:
    with pytest.raises(
        InvalidReadabilityTextError,
        match="text must not be blank",
    ):
        analyze_readability(value)


def test_analyze_readability_maps_every_backend_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = FakeTextstat()
    text = "Synthetic readability text."

    monkeypatch.setattr(metrics, "textstat", backend)

    result = analyze_readability(text)

    assert result == ReadabilityResult(
        flesch_kincaid_grade=1.1,
        automated_readability_index=2.2,
        coleman_liau_index=3.3,
        gunning_fog=4.4,
        dale_chall_readability_score=5.5,
        estimated_reading_time_seconds=6.6,
        sentence_count=7,
        word_count=8,
        syllable_count=9,
        letter_count=10,
        polysyllable_count=11,
    )
    assert backend.language == "en_US"
    assert backend.calls == [
        ("flesch_kincaid_grade", text),
        ("automated_readability_index", text),
        ("coleman_liau_index", text),
        ("gunning_fog", text),
        ("dale_chall_readability_score", text),
        ("reading_time", text),
        ("sentence_count", text),
        ("lexicon_count", text),
        ("syllable_count", text),
        ("letter_count", text),
        ("polysyllabcount", text),
    ]


def test_real_backend_returns_finite_typed_result() -> None:
    result = analyze_readability(
        "A synthetic sentence contains several carefully selected words."
    )

    for value in (
        result.flesch_kincaid_grade,
        result.automated_readability_index,
        result.coleman_liau_index,
        result.gunning_fog,
        result.dale_chall_readability_score,
        result.estimated_reading_time_seconds,
    ):
        assert isinstance(value, float)
        assert isfinite(value)

    for value in (
        result.sentence_count,
        result.word_count,
        result.syllable_count,
        result.letter_count,
        result.polysyllable_count,
    ):
        assert isinstance(value, int)
        assert value >= 0
