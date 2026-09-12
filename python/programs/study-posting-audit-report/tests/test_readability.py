"""Focused tests for report-level readability extraction and validation."""

from dataclasses import dataclass

import pytest

from study_posting_audit_report import (
    AuditReportConfig,
    AuditRowError,
    analyze_readability_for_row,
)
from tabular_row_sources import Row


@dataclass(frozen=True, slots=True)
class FakeReadabilityResult:
    """Deterministic readability result used at the report boundary."""

    flesch_kincaid_grade: float = 1.0
    automated_readability_index: float = 2.0
    coleman_liau_index: float = 3.0
    gunning_fog: float = 4.0
    dale_chall_readability_score: float = 5.0
    estimated_reading_time_seconds: float = 6.0
    sentence_count: int = 7
    word_count: int = 8
    syllable_count: int = 9
    letter_count: int = 10
    polysyllable_count: int = 11


class RecordingReadabilityAnalyzer:
    """Record each analyzed text and return a deterministic result."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, text: str) -> FakeReadabilityResult:
        self.calls.append(text)
        return FakeReadabilityResult()


def completed_ai_row(
    *,
    suggestions: object | None = None,
    selections: object | None = None,
    final: object | None = None,
    attempt_type: object = "AI",
) -> Row:
    """Return a minimal completed AI row for readability extraction."""
    return {
        "ID": 2001,
        "ATTEMPT_TYPE": attempt_type,
        "ATTEMPT_RESULT": "COMPLETE",
        "LLM_SUGGESTIONS": (
            {
                "title": [],
                "about": [],
                "purpose": [],
                "description": [],
                "compensation": {
                    "genericCompensation": [],
                    "specificCompensation": [],
                },
            }
            if suggestions is None
            else suggestions
        ),
        "SELECTED_SUGGESTIONS": (
            {
                "title": [],
                "about": [],
                "purpose": [],
                "description": [],
                "compensation": {
                    "genericCompensation": [],
                    "specificCompensation": [],
                },
            }
            if selections is None
            else selections
        ),
        "FINAL_SUBMISSION": (
            {
                "title": "",
                "about": "",
                "purpose": "",
                "description": "",
                "compensation": "",
            }
            if final is None
            else final
        ),
    }


def analyze(row: Row) -> tuple[dict[str, object], ...]:
    """Analyze one synthetic row with a deterministic analyzer."""
    return analyze_readability_for_row(
        row,
        config=AuditReportConfig(),
        row_number=3,
        record_id=2001,
        analyzer=RecordingReadabilityAnalyzer(),
    )


@pytest.mark.parametrize(
    ("column_name", "object_name"),
    [
        ("FINAL_SUBMISSION", "final submission"),
        ("LLM_SUGGESTIONS", "suggestions"),
        ("SELECTED_SUGGESTIONS", "selections"),
    ],
)
def test_completed_ai_requires_readability_objects(
    column_name: str,
    object_name: str,
) -> None:
    row = completed_ai_row()
    row[column_name] = []

    with pytest.raises(
        AuditRowError,
        match=rf"readability {object_name} must be an object",
    ) as captured:
        analyze(row)

    assert captured.value.row_number == 3
    assert captured.value.record_id == 2001


@pytest.mark.parametrize(
    "column_name",
    [
        "FINAL_SUBMISSION",
        "LLM_SUGGESTIONS",
        "SELECTED_SUGGESTIONS",
    ],
)
def test_readability_objects_require_string_field_names(
    column_name: str,
) -> None:
    row = completed_ai_row()
    row[column_name] = {1: "synthetic value"}

    with pytest.raises(
        AuditRowError,
        match="field names must be strings",
    ):
        analyze(row)


@pytest.mark.parametrize(
    "value",
    [
        17,
        {"nested": "value"},
    ],
)
def test_final_readability_field_must_be_text_or_null(
    value: object,
) -> None:
    row = completed_ai_row(
        final={
            "title": value,
            "about": "",
            "purpose": "",
            "description": "",
            "compensation": "",
        }
    )

    with pytest.raises(
        AuditRowError,
        match=r"readability field 'title' must contain text or null",
    ):
        analyze(row)


def test_null_final_text_is_skipped() -> None:
    analyzer = RecordingReadabilityAnalyzer()
    row = completed_ai_row(
        final={
            "title": None,
            "about": "",
            "purpose": "",
            "description": "",
            "compensation": "",
        }
    )

    rows = analyze_readability_for_row(
        row,
        config=AuditReportConfig(),
        row_number=3,
        record_id=2001,
        analyzer=analyzer,
    )

    assert rows == ()
    assert analyzer.calls == []


@pytest.mark.parametrize(
    "value",
    [
        "not a sequence",
        b"bytes are not a suggestion sequence",
        bytearray(b"nor is a bytearray"),
        {"not": "a sequence"},
    ],
)
def test_suggestions_must_be_non_string_sequences(
    value: object,
) -> None:
    row = completed_ai_row()
    suggestions = row["LLM_SUGGESTIONS"]
    assert isinstance(suggestions, dict)
    suggestions["title"] = value

    with pytest.raises(
        AuditRowError,
        match=r"readability suggestions for 'title' must be a sequence",
    ):
        analyze(row)


def test_null_suggestion_and_selection_sequences_are_empty() -> None:
    analyzer = RecordingReadabilityAnalyzer()
    row = completed_ai_row()
    suggestions = row["LLM_SUGGESTIONS"]
    selections = row["SELECTED_SUGGESTIONS"]
    assert isinstance(suggestions, dict)
    assert isinstance(selections, dict)
    suggestions["title"] = None
    selections["title"] = None

    rows = analyze_readability_for_row(
        row,
        config=AuditReportConfig(),
        row_number=3,
        record_id=2001,
        analyzer=analyzer,
    )

    assert rows == ()
    assert analyzer.calls == []


@pytest.mark.parametrize(
    "column_name",
    [
        "LLM_SUGGESTIONS",
        "SELECTED_SUGGESTIONS",
    ],
)
def test_suggestion_sequences_require_text_items(
    column_name: str,
) -> None:
    row = completed_ai_row()
    value = row[column_name]
    assert isinstance(value, dict)
    value["title"] = ["valid synthetic text", 17]

    with pytest.raises(
        AuditRowError,
        match=r"readability suggestions for 'title' must contain text",
    ):
        analyze(row)


def test_selection_not_present_in_suggestions_marks_every_offer_unselected() -> None:
    analyzer = RecordingReadabilityAnalyzer()
    row = completed_ai_row()
    suggestions = row["LLM_SUGGESTIONS"]
    selections = row["SELECTED_SUGGESTIONS"]
    assert isinstance(suggestions, dict)
    assert isinstance(selections, dict)
    suggestions["title"] = ["First synthetic title", "Second synthetic title"]
    selections["title"] = ["Different synthetic title"]

    rows = analyze_readability_for_row(
        row,
        config=AuditReportConfig(),
        row_number=3,
        record_id=2001,
        analyzer=analyzer,
    )

    assert [item["selected"] for item in rows] == [False, False]
    assert analyzer.calls == [
        "First synthetic title",
        "Second synthetic title",
    ]


def test_blank_ordinary_and_compensation_suggestions_are_skipped() -> None:
    analyzer = RecordingReadabilityAnalyzer()
    row = completed_ai_row()
    suggestions = row["LLM_SUGGESTIONS"]
    assert isinstance(suggestions, dict)
    suggestions["title"] = ["", "   "]
    suggestions["compensation"] = {
        "genericCompensation": ["\t"],
        "specificCompensation": ["Synthetic compensation"],
    }

    rows = analyze_readability_for_row(
        row,
        config=AuditReportConfig(),
        row_number=3,
        record_id=2001,
        analyzer=analyzer,
    )

    assert len(rows) == 1
    assert rows[0]["field_name"] == "compensation"
    assert rows[0]["suggestion_kind"] == "specificCompensation"
    assert rows[0]["suggestion_index"] == 0
    assert analyzer.calls == ["Synthetic compensation"]


@pytest.mark.parametrize(
    "attempt_type",
    [
        None,
        17,
        True,
    ],
)
def test_completed_row_requires_string_attempt_type(
    attempt_type: object,
) -> None:
    row = completed_ai_row(attempt_type=attempt_type)

    with pytest.raises(
        AuditRowError,
        match="readability attempt type must be a string",
    ) as captured:
        analyze(row)

    assert captured.value.row_number == 3
    assert captured.value.record_id == 2001
