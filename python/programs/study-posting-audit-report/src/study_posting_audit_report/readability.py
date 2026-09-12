"""Study-specific extraction and analysis of readable text instances."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, cast

from study_posting_audit_report.config import AuditReportConfig
from study_posting_audit_report.errors import AuditRowError, RecordId
from tabular_row_sources import Row

READABILITY_COLUMNS: tuple[str, ...] = (
    "record_id",
    "attempt_type",
    "field_name",
    "text_role",
    "suggestion_kind",
    "suggestion_index",
    "selected",
    "flesch_kincaid_grade",
    "automated_readability_index",
    "coleman_liau_index",
    "gunning_fog",
    "dale_chall_readability_score",
    "estimated_reading_time_seconds",
    "sentence_count",
    "word_count",
    "syllable_count",
    "letter_count",
    "polysyllable_count",
)

_READABILITY_FIELDS: tuple[str, ...] = (
    "title",
    "about",
    "purpose",
    "description",
)
_COMPENSATION_KINDS: tuple[str, ...] = (
    "genericCompensation",
    "specificCompensation",
)
_COMPLETED_ATTEMPT_RESULT = "COMPLETE"
_AI_ATTEMPT_TYPE = "AI"

type ReadabilityRow = dict[str, object]


class ReadabilityResultLike(Protocol):
    """Read-only result required from a readability analyzer."""

    @property
    def flesch_kincaid_grade(self) -> float:
        """Return Flesch-Kincaid Grade Level."""
        ...

    @property
    def automated_readability_index(self) -> float:
        """Return Automated Readability Index."""
        ...

    @property
    def coleman_liau_index(self) -> float:
        """Return Coleman-Liau Index."""
        ...

    @property
    def gunning_fog(self) -> float:
        """Return Gunning Fog score."""
        ...

    @property
    def dale_chall_readability_score(self) -> float:
        """Return Dale-Chall Readability Score."""
        ...

    @property
    def estimated_reading_time_seconds(self) -> float:
        """Return estimated reading time in seconds."""
        ...

    @property
    def sentence_count(self) -> int:
        """Return sentence count."""
        ...

    @property
    def word_count(self) -> int:
        """Return word count."""
        ...

    @property
    def syllable_count(self) -> int:
        """Return syllable count."""
        ...

    @property
    def letter_count(self) -> int:
        """Return letter count."""
        ...

    @property
    def polysyllable_count(self) -> int:
        """Return polysyllable count."""
        ...


type ReadabilityAnalyzer = Callable[[str], ReadabilityResultLike]


@dataclass(frozen=True, slots=True)
class _ReadabilityContext:
    """Shared context for building readability rows."""

    analyzer: ReadabilityAnalyzer
    record_id: RecordId
    attempt_type: str
    row_number: int


def _require_object(
    value: object,
    *,
    object_name: str,
    row_number: int,
    record_id: RecordId,
) -> Mapping[str, object]:
    """Return a string-keyed decoded object."""
    if not isinstance(value, Mapping):
        raise AuditRowError(
            f"readability {object_name} must be an object",
            row_number=row_number,
            record_id=record_id,
        )

    mapping = cast("Mapping[object, object]", value)
    result: dict[str, object] = {}

    for key, item in mapping.items():
        if not isinstance(key, str):
            raise AuditRowError(
                f"readability {object_name} field names must be strings",
                row_number=row_number,
                record_id=record_id,
            )

        result[key] = item

    return result


def _optional_text(
    value: object,
    *,
    field_name: str,
    row_number: int,
    record_id: RecordId,
) -> str | None:
    """Return nonblank text or ``None``."""
    if value is None:
        return None

    if not isinstance(value, str):
        raise AuditRowError(
            f"readability field {field_name!r} must contain text or null",
            row_number=row_number,
            record_id=record_id,
        )

    if not value.strip():
        return None

    return value


def _text_sequence(
    value: object,
    *,
    field_name: str,
    row_number: int,
    record_id: RecordId,
) -> tuple[str, ...]:
    """Return a sequence containing only text values."""
    if value is None:
        return ()

    if not isinstance(value, Sequence) or isinstance(
        value,
        (str, bytes, bytearray),
    ):
        raise AuditRowError(
            f"readability suggestions for {field_name!r} must be a sequence",
            row_number=row_number,
            record_id=record_id,
        )

    values = cast("Sequence[object]", value)
    result: list[str] = []

    for item in values:
        if not isinstance(item, str):
            raise AuditRowError(
                f"readability suggestions for {field_name!r} must contain text",
                row_number=row_number,
                record_id=record_id,
            )

        result.append(item)

    return tuple(result)


def _selected_index(
    suggestions: tuple[str, ...],
    selections: tuple[str, ...],
) -> int | None:
    """Return the first offered index matching the selected value."""
    if not selections:
        return None

    selected_text = selections[0]

    try:
        return suggestions.index(selected_text)
    except ValueError:
        return None


def _try_analyze_text(
    analyzer: ReadabilityAnalyzer,
    text: str,
) -> ReadabilityResultLike | None:
    """Return a readability result or discard a third-party failure."""
    try:
        return analyzer(text)
    except Exception:
        # Analyzer errors may contain source text. Do not log, chain, or expose
        # the original exception.
        return None


def _analyze_text(
    analyzer: ReadabilityAnalyzer,
    text: str,
    *,
    row_number: int,
    record_id: RecordId,
    field_name: str,
    text_role: str,
) -> ReadabilityResultLike:
    """Analyze text while preventing source text from entering errors."""
    result = _try_analyze_text(
        analyzer,
        text,
    )

    if result is None:
        raise AuditRowError(
            f"readability analysis failed for field {field_name!r}, role {text_role!r}",
            row_number=row_number,
            record_id=record_id,
        )

    return result


def _build_row(
    *,
    context: _ReadabilityContext,
    text: str,
    field_name: str,
    text_role: str,
    suggestion_kind: str | None,
    suggestion_index: int | None,
    selected: bool | None,
) -> ReadabilityRow:
    """Return one canonical readability row."""
    result = _analyze_text(
        context.analyzer,
        text,
        row_number=context.row_number,
        record_id=context.record_id,
        field_name=field_name,
        text_role=text_role,
    )

    return {
        "record_id": context.record_id,
        "attempt_type": context.attempt_type,
        "field_name": field_name,
        "text_role": text_role,
        "suggestion_kind": suggestion_kind,
        "suggestion_index": suggestion_index,
        "selected": selected,
        "flesch_kincaid_grade": result.flesch_kincaid_grade,
        "automated_readability_index": result.automated_readability_index,
        "coleman_liau_index": result.coleman_liau_index,
        "gunning_fog": result.gunning_fog,
        "dale_chall_readability_score": (result.dale_chall_readability_score),
        "estimated_reading_time_seconds": (result.estimated_reading_time_seconds),
        "sentence_count": result.sentence_count,
        "word_count": result.word_count,
        "syllable_count": result.syllable_count,
        "letter_count": result.letter_count,
        "polysyllable_count": result.polysyllable_count,
    }


def _ordinary_suggestion_rows(
    *,
    analyzer: ReadabilityAnalyzer,
    suggested: Mapping[str, object],
    selected: Mapping[str, object],
    record_id: RecordId,
    attempt_type: str,
    row_number: int,
    field_names: tuple[str, ...] = _READABILITY_FIELDS,
) -> list[ReadabilityRow]:
    """Return readability rows for ordinary offered suggestions."""
    rows: list[ReadabilityRow] = []
    context = _ReadabilityContext(
        analyzer=analyzer,
        record_id=record_id,
        attempt_type=attempt_type,
        row_number=row_number,
    )

    for field_name in field_names:
        suggestions = _text_sequence(
            suggested.get(field_name),
            field_name=field_name,
            row_number=row_number,
            record_id=record_id,
        )
        selections = _text_sequence(
            selected.get(field_name),
            field_name=field_name,
            row_number=row_number,
            record_id=record_id,
        )
        selected_index = _selected_index(
            suggestions,
            selections,
        )

        for suggestion_index, text_value in enumerate(suggestions):
            text = _optional_text(
                text_value,
                field_name=field_name,
                row_number=row_number,
                record_id=record_id,
            )

            if text is None:
                continue

            rows.append(
                _build_row(
                    context=context,
                    text=text,
                    field_name=field_name,
                    text_role="SUGGESTED",
                    suggestion_kind=field_name,
                    suggestion_index=suggestion_index,
                    selected=suggestion_index == selected_index,
                )
            )

    return rows


def _compensation_suggestion_rows(
    *,
    analyzer: ReadabilityAnalyzer,
    suggested: Mapping[str, object],
    selected: Mapping[str, object],
    record_id: RecordId,
    attempt_type: str,
    row_number: int,
) -> list[ReadabilityRow]:
    """Return readability rows for categorized compensation suggestions."""
    suggested_compensation = _require_object(
        suggested.get("compensation"),
        object_name="suggested compensation",
        row_number=row_number,
        record_id=record_id,
    )
    selected_compensation = _require_object(
        selected.get("compensation"),
        object_name="selected compensation",
        row_number=row_number,
        record_id=record_id,
    )
    rows: list[ReadabilityRow] = []
    context = _ReadabilityContext(
        analyzer=analyzer,
        record_id=record_id,
        attempt_type=attempt_type,
        row_number=row_number,
    )

    for kind in _COMPENSATION_KINDS:
        suggestions = _text_sequence(
            suggested_compensation.get(kind),
            field_name=kind,
            row_number=row_number,
            record_id=record_id,
        )
        selections = _text_sequence(
            selected_compensation.get(kind),
            field_name=kind,
            row_number=row_number,
            record_id=record_id,
        )
        selected_index = _selected_index(
            suggestions,
            selections,
        )

        for suggestion_index, text_value in enumerate(suggestions):
            text = _optional_text(
                text_value,
                field_name="compensation",
                row_number=row_number,
                record_id=record_id,
            )

            if text is None:
                continue

            rows.append(
                _build_row(
                    context=context,
                    text=text,
                    field_name="compensation",
                    text_role="SUGGESTED",
                    suggestion_kind=kind,
                    suggestion_index=suggestion_index,
                    selected=suggestion_index == selected_index,
                )
            )

    return rows


def _final_rows(
    *,
    analyzer: ReadabilityAnalyzer,
    final: Mapping[str, object],
    record_id: RecordId,
    attempt_type: str,
    row_number: int,
    field_names: tuple[str, ...] = (*_READABILITY_FIELDS, "compensation"),
) -> list[ReadabilityRow]:
    """Return readability rows for final saved text fields."""
    rows: list[ReadabilityRow] = []
    context = _ReadabilityContext(
        analyzer=analyzer,
        record_id=record_id,
        attempt_type=attempt_type,
        row_number=row_number,
    )

    for field_name in field_names:
        text = _optional_text(
            final.get(field_name),
            field_name=field_name,
            row_number=row_number,
            record_id=record_id,
        )

        if text is None:
            continue

        rows.append(
            _build_row(
                context=context,
                text=text,
                field_name=field_name,
                text_role="FINAL",
                suggestion_kind=None,
                suggestion_index=None,
                selected=None,
            )
        )

    return rows


def analyze_readability_for_row(
    row: Row,
    *,
    config: AuditReportConfig,
    row_number: int,
    record_id: RecordId,
    analyzer: ReadabilityAnalyzer,
) -> tuple[ReadabilityRow, ...]:
    """Return readability rows for one completed audit request."""
    attempt_result = row[config.columns.attempt_result]

    if attempt_result != _COMPLETED_ATTEMPT_RESULT:
        return ()

    attempt_type_value = row[config.columns.attempt_type]

    if not isinstance(attempt_type_value, str):
        raise AuditRowError(
            "readability attempt type must be a string",
            row_number=row_number,
            record_id=record_id,
        )

    final = _require_object(
        row[config.columns.final_submission],
        object_name="final submission",
        row_number=row_number,
        record_id=record_id,
    )
    rows: list[ReadabilityRow] = []

    if attempt_type_value == _AI_ATTEMPT_TYPE:
        suggested = _require_object(
            row[config.columns.llm_suggestions],
            object_name="suggestions",
            row_number=row_number,
            record_id=record_id,
        )
        selected = _require_object(
            row[config.columns.selected_suggestions],
            object_name="selections",
            row_number=row_number,
            record_id=record_id,
        )

        for field_name in _READABILITY_FIELDS:
            rows.extend(
                _ordinary_suggestion_rows(
                    analyzer=analyzer,
                    suggested=suggested,
                    selected=selected,
                    record_id=record_id,
                    attempt_type=attempt_type_value,
                    row_number=row_number,
                    field_names=(field_name,),
                )
            )
            rows.extend(
                _final_rows(
                    analyzer=analyzer,
                    final=final,
                    record_id=record_id,
                    attempt_type=attempt_type_value,
                    row_number=row_number,
                    field_names=(field_name,),
                )
            )

        rows.extend(
            _compensation_suggestion_rows(
                analyzer=analyzer,
                suggested=suggested,
                selected=selected,
                record_id=record_id,
                attempt_type=attempt_type_value,
                row_number=row_number,
            )
        )
        rows.extend(
            _final_rows(
                analyzer=analyzer,
                final=final,
                record_id=record_id,
                attempt_type=attempt_type_value,
                row_number=row_number,
                field_names=("compensation",),
            )
        )
    else:
        rows.extend(
            _final_rows(
                analyzer=analyzer,
                final=final,
                record_id=record_id,
                attempt_type=attempt_type_value,
                row_number=row_number,
            )
        )

    return tuple(rows)
