"""Tests for pure audit-row selection and analysis processing."""

from collections.abc import Iterable, Iterator
from datetime import datetime
from typing import cast

import pytest

from study_posting_audit_report import (
    AuditColumnMapping,
    AuditReportConfig,
    AuditRowError,
    ProcessedAuditRow,
    analyze_audit_row,
    extract_record_id,
    process_audit_rows,
    validate_source_schema,
)
from tabular_row_sources import (
    ColumnSpec,
    ColumnType,
    Row,
    RowSchema,
)

type AuditObjects = tuple[
    dict[str, object],
    dict[str, object],
    dict[str, object],
]


def valid_analysis_objects() -> AuditObjects:
    """Return valid synthetic suggested, selected, and final objects."""
    suggested: dict[str, object] = {
        "about": ["About suggestion"],
        "compensation": {
            "genericCompensation": [],
            "specificCompensation": [],
        },
        "contact": {
            "email": "",
            "name": "",
            "phone": "",
            "website": "",
        },
        "department": [],
        "description": ["Description suggestion"],
        "locations": [],
        "offersCompensation": False,
        "purpose": ["Purpose suggestion"],
        "title": ["Title suggestion"],
        "topics": [],
    }

    selected: dict[str, object] = {
        "about": ["About suggestion"],
        "compensation": {
            "genericCompensation": [],
            "specificCompensation": [],
        },
        "contact": {
            "email": "",
            "name": "",
            "phone": "",
            "website": "",
        },
        "department": [],
        "description": ["Description suggestion"],
        "locations": [],
        "purpose": ["Purpose suggestion"],
        "title": ["Title suggestion"],
        "topics": [],
    }

    final: dict[str, object] = {
        "about": "About suggestion",
        "compensation": "",
        "contact": {
            "email": "person@example.edu",
            "name": "Test Person",
            "phone": "",
            "website": "",
        },
        "department": [],
        "description": "Description suggestion",
        "locations": [],
        "offersCompensation": False,
        "purpose": "Purpose suggestion",
        "title": "Title suggestion",
        "topics": [],
    }

    return suggested, selected, final


def source_schema(
    *,
    include_extra_column: bool = True,
) -> RowSchema:
    """Return a canonical source schema for audit processing."""
    columns: list[ColumnSpec] = [
        ColumnSpec(
            name="ID",
            data_type=ColumnType.INTEGER,
        ),
        ColumnSpec(
            name="END_TIME",
            data_type=ColumnType.DATETIME,
            nullable=True,
        ),
        ColumnSpec(
            name="ATTEMPT_TYPE",
            data_type=ColumnType.STRING,
        ),
        ColumnSpec(
            name="ATTEMPT_RESULT",
            data_type=ColumnType.STRING,
        ),
        ColumnSpec(
            name="LLM_SUGGESTIONS",
            data_type=ColumnType.JSON_OBJECT,
            nullable=True,
        ),
        ColumnSpec(
            name="SELECTED_SUGGESTIONS",
            data_type=ColumnType.JSON_OBJECT,
            nullable=True,
        ),
        ColumnSpec(
            name="FINAL_SUBMISSION",
            data_type=ColumnType.JSON_OBJECT,
            nullable=True,
        ),
    ]

    if include_extra_column:
        columns.append(
            ColumnSpec(
                name="STUDY_NUM",
                data_type=ColumnType.STRING,
                nullable=True,
            )
        )

    return RowSchema(columns=tuple(columns))


def completed_ai_source_row(
    *,
    record_id: object = 1001,
) -> Row:
    """Return one valid completed AI source row."""
    suggested, selected, final = valid_analysis_objects()

    return {
        "ID": record_id,
        "END_TIME": datetime.fromisoformat("2026-05-18T09:07:38"),
        "ATTEMPT_TYPE": "AI",
        "ATTEMPT_RESULT": "COMPLETE",
        "LLM_SUGGESTIONS": suggested,
        "SELECTED_SUGGESTIONS": selected,
        "FINAL_SUBMISSION": final,
        "STUDY_NUM": "SYNTHETIC-0001",
    }


def manual_source_row(
    *,
    record_id: object = 1002,
) -> Row:
    """Return one completed manual row with only a final payload."""
    _, _, final = valid_analysis_objects()

    return {
        "ID": record_id,
        "END_TIME": datetime.fromisoformat("2026-05-18T10:00:00"),
        "ATTEMPT_TYPE": "MANUAL",
        "ATTEMPT_RESULT": "COMPLETE",
        "LLM_SUGGESTIONS": None,
        "SELECTED_SUGGESTIONS": None,
        "FINAL_SUBMISSION": final,
        "STUDY_NUM": "SYNTHETIC-0002",
    }


def incomplete_ai_source_row(
    *,
    record_id: object = 1003,
    attempt_result: object = "USER_DROPPED",
) -> Row:
    """Return one incomplete AI row with absent analysis values."""
    return {
        "ID": record_id,
        "END_TIME": None,
        "ATTEMPT_TYPE": "AI",
        "ATTEMPT_RESULT": attempt_result,
        "LLM_SUGGESTIONS": None,
        "SELECTED_SUGGESTIONS": None,
        "FINAL_SUBMISSION": None,
        "STUDY_NUM": "SYNTHETIC-0003",
    }


def metric_row_for_field(
    outcome: ProcessedAuditRow,
    field_name: str,
) -> dict[str, object]:
    """Return one flattened metric row by field name."""
    matches = [row for row in outcome.metric_rows if row["field_name"] == field_name]

    assert len(matches) == 1

    return matches[0]


# ---------------------------------------------------------------------------
# Source-schema validation
# ---------------------------------------------------------------------------


def test_source_schema_accepts_required_and_extra_columns() -> None:
    validate_source_schema(
        source_schema(),
        config=AuditReportConfig(),
    )


def test_source_schema_accepts_required_columns_in_any_position() -> None:
    original = source_schema()
    reversed_schema = RowSchema(columns=tuple(reversed(original.columns)))

    validate_source_schema(
        reversed_schema,
        config=AuditReportConfig(),
    )


def test_source_schema_rejects_missing_required_columns() -> None:
    schema = RowSchema(
        columns=(
            ColumnSpec(
                name="ID",
                data_type=ColumnType.INTEGER,
            ),
        )
    )

    with pytest.raises(
        AuditRowError,
        match="source schema is missing required columns",
    ) as captured:
        validate_source_schema(
            schema,
            config=AuditReportConfig(),
        )

    message = str(captured.value)

    assert "END_TIME" in message
    assert "ATTEMPT_TYPE" in message
    assert "ATTEMPT_RESULT" in message
    assert "LLM_SUGGESTIONS" in message
    assert "SELECTED_SUGGESTIONS" in message
    assert "FINAL_SUBMISSION" in message


def test_source_schema_uses_custom_column_mapping() -> None:
    config = AuditReportConfig(
        columns=AuditColumnMapping(
            record_id="AUDIT_ID",
            end_time="FINISHED_AT",
            attempt_type="TYPE",
            attempt_result="RESULT",
            llm_suggestions="SUGGESTED",
            selected_suggestions="SELECTED",
            final_submission="FINAL",
        )
    )
    schema = RowSchema(
        columns=(
            ColumnSpec("AUDIT_ID", ColumnType.INTEGER),
            ColumnSpec(
                "FINISHED_AT",
                ColumnType.DATETIME,
                nullable=True,
            ),
            ColumnSpec("TYPE", ColumnType.STRING),
            ColumnSpec("RESULT", ColumnType.STRING),
            ColumnSpec(
                "SUGGESTED",
                ColumnType.JSON_OBJECT,
                nullable=True,
            ),
            ColumnSpec(
                "SELECTED",
                ColumnType.JSON_OBJECT,
                nullable=True,
            ),
            ColumnSpec(
                "FINAL",
                ColumnType.JSON_OBJECT,
                nullable=True,
            ),
        )
    )

    validate_source_schema(schema, config=config)


# ---------------------------------------------------------------------------
# Record-ID extraction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1, 1),
        (0, 0),
        (-1, -1),
        ("audit-1", "audit-1"),
        ("  audit-1  ", "  audit-1  "),
    ],
    ids=[
        "positive-integer",
        "zero",
        "negative-integer",
        "string",
        "padded-string",
    ],
)
def test_extract_record_id_accepts_supported_values(
    value: object,
    expected: str | int,
) -> None:
    row: Row = {"ID": value}

    assert (
        extract_record_id(
            row,
            config=AuditReportConfig(),
            row_number=7,
        )
        == expected
    )


def test_extract_record_id_rejects_missing_column() -> None:
    with pytest.raises(
        AuditRowError,
        match="source row is missing required column 'ID'",
    ) as captured:
        extract_record_id(
            {},
            config=AuditReportConfig(),
            row_number=4,
        )

    assert captured.value.row_number == 4
    assert captured.value.record_id is None


def test_extract_record_id_rejects_null() -> None:
    with pytest.raises(
        AuditRowError,
        match="must not be null",
    ):
        extract_record_id(
            {"ID": None},
            config=AuditReportConfig(),
            row_number=1,
        )


@pytest.mark.parametrize(
    "value",
    ["", "   ", "\n\t"],
    ids=["empty", "spaces", "tabs-newlines"],
)
def test_extract_record_id_rejects_blank_string(value: str) -> None:
    with pytest.raises(
        AuditRowError,
        match="must not be blank",
    ):
        extract_record_id(
            {"ID": value},
            config=AuditReportConfig(),
            row_number=1,
        )


@pytest.mark.parametrize(
    "value",
    [True, False],
    ids=["true", "false"],
)
def test_extract_record_id_rejects_boolean(value: bool) -> None:
    with pytest.raises(
        AuditRowError,
        match="must not contain a Boolean",
    ):
        extract_record_id(
            {"ID": value},
            config=AuditReportConfig(),
            row_number=1,
        )


@pytest.mark.parametrize(
    "value",
    [1.5, object(), [], {}],
    ids=["float", "object", "list", "dictionary"],
)
def test_extract_record_id_rejects_unsupported_type(
    value: object,
) -> None:
    with pytest.raises(
        AuditRowError,
        match="must contain a string or integer",
    ):
        extract_record_id(
            {"ID": value},
            config=AuditReportConfig(),
            row_number=1,
        )


# ---------------------------------------------------------------------------
# Completed AI-row analysis
# ---------------------------------------------------------------------------


def test_analyze_audit_row_produces_one_metric_row_per_field() -> None:
    metric_rows = analyze_audit_row(
        completed_ai_source_row(),
        config=AuditReportConfig(),
        row_number=1,
        record_id=1001,
    )

    assert len(metric_rows) == 12
    assert {row["field_name"] for row in metric_rows} == {
        "about",
        "compensation",
        "contact.email",
        "contact.name",
        "contact.phone",
        "contact.website",
        "department",
        "description",
        "locations",
        "purpose",
        "title",
        "topics",
    }


def test_analyze_audit_row_carries_record_id_to_every_metric() -> None:
    metric_rows = analyze_audit_row(
        completed_ai_source_row(),
        config=AuditReportConfig(),
        row_number=1,
        record_id="audit-1001",
    )

    assert all(row["record_id"] == "audit-1001" for row in metric_rows)


def test_analyze_audit_row_excludes_text_by_default() -> None:
    metric_rows = analyze_audit_row(
        completed_ai_source_row(),
        config=AuditReportConfig(),
        row_number=1,
        record_id=1001,
    )

    for row in metric_rows:
        assert row["selected_text"] is None
        assert row["final_text"] is None


def test_analyze_audit_row_includes_text_when_enabled() -> None:
    metric_rows = analyze_audit_row(
        completed_ai_source_row(),
        config=AuditReportConfig(include_text=True),
        row_number=1,
        record_id=1001,
    )
    title = next(row for row in metric_rows if row["field_name"] == "title")

    assert title["selected_text"] == "Title suggestion"
    assert title["final_text"] == "Title suggestion"


@pytest.mark.parametrize(
    "missing_column",
    [
        "LLM_SUGGESTIONS",
        "SELECTED_SUGGESTIONS",
        "FINAL_SUBMISSION",
    ],
)
def test_analyze_audit_row_rejects_missing_payload_column(
    missing_column: str,
) -> None:
    row = completed_ai_source_row()
    del row[missing_column]

    with pytest.raises(
        AuditRowError,
        match=f"source row is missing required column '{missing_column}'",
    ):
        analyze_audit_row(
            row,
            config=AuditReportConfig(),
            row_number=3,
            record_id=1001,
        )


@pytest.mark.parametrize(
    ("column_name", "invalid_value"),
    [
        ("LLM_SUGGESTIONS", None),
        ("SELECTED_SUGGESTIONS", None),
        ("FINAL_SUBMISSION", None),
        ("LLM_SUGGESTIONS", "not-json"),
        ("SELECTED_SUGGESTIONS", []),
        ("FINAL_SUBMISSION", 42),
    ],
    ids=[
        "null-suggested",
        "null-selected",
        "null-final",
        "bad-json-suggested",
        "list-selected",
        "integer-final",
    ],
)
def test_analyze_audit_row_wraps_payload_errors(
    column_name: str,
    invalid_value: object,
) -> None:
    row = completed_ai_source_row()
    row[column_name] = invalid_value

    with pytest.raises(
        AuditRowError,
        match="analysis failed",
    ) as captured:
        analyze_audit_row(
            row,
            config=AuditReportConfig(),
            row_number=9,
            record_id=1001,
        )

    assert captured.value.row_number == 9
    assert captured.value.record_id == 1001
    assert captured.value.__cause__ is not None


def test_analyze_audit_row_wraps_study_policy_error() -> None:
    row = completed_ai_source_row()
    final = row["FINAL_SUBMISSION"]

    assert isinstance(final, dict)

    final["title"] = ""

    with pytest.raises(
        AuditRowError,
        match="analysis failed",
    ) as captured:
        analyze_audit_row(
            row,
            config=AuditReportConfig(),
            row_number=6,
            record_id=1001,
        )

    assert "title: final saved text must not be blank" in str(captured.value)


# ---------------------------------------------------------------------------
# Analysis selection and stream processing
# ---------------------------------------------------------------------------


def test_completed_ai_row_is_analyzed() -> None:
    outcome = next(
        process_audit_rows(
            [completed_ai_source_row()],
            config=AuditReportConfig(),
        )
    )

    assert outcome.analyzed is True
    assert len(outcome.metric_rows) == 12


def test_completed_manual_row_is_preserved_without_analysis() -> None:
    row = manual_source_row()

    outcome = next(
        process_audit_rows(
            [row],
            config=AuditReportConfig(),
        )
    )

    assert outcome.record == row
    assert outcome.record is not row
    assert outcome.analyzed is False
    assert outcome.metric_rows == ()


@pytest.mark.parametrize(
    "attempt_result",
    [
        "USER_DROPPED",
        "AI_ERROR",
        "AI_ERROR_WITHOUT_STACK_TRACE",
        "FAILED",
        None,
    ],
    ids=[
        "user-dropped",
        "ai-error",
        "error-without-stack",
        "failed",
        "null-result",
    ],
)
def test_incomplete_ai_row_is_preserved_without_analysis(
    attempt_result: object,
) -> None:
    row = incomplete_ai_source_row(
        attempt_result=attempt_result,
    )
    row["LLM_SUGGESTIONS"] = "malformed-but-not-inspected"

    outcome = next(
        process_audit_rows(
            [row],
            config=AuditReportConfig(),
        )
    )

    assert outcome.record == row
    assert outcome.analyzed is False
    assert outcome.metric_rows == ()


def test_non_ai_row_does_not_inspect_result_or_payloads() -> None:
    row = manual_source_row()
    row["ATTEMPT_RESULT"] = object()
    row["LLM_SUGGESTIONS"] = object()
    row["SELECTED_SUGGESTIONS"] = object()
    row["FINAL_SUBMISSION"] = object()

    outcome = next(
        process_audit_rows(
            [row],
            config=AuditReportConfig(),
        )
    )

    assert outcome.analyzed is False
    assert outcome.metric_rows == ()


def test_completed_ai_row_requires_end_time() -> None:
    row = completed_ai_source_row()
    row["END_TIME"] = None

    with pytest.raises(
        AuditRowError,
        match="completed AI row requires non-null column 'END_TIME'",
    ) as captured:
        next(
            process_audit_rows(
                [row],
                config=AuditReportConfig(),
            )
        )

    assert captured.value.row_number == 1
    assert captured.value.record_id == 1001


@pytest.mark.parametrize(
    "null_columns",
    [
        {"LLM_SUGGESTIONS"},
        {"SELECTED_SUGGESTIONS"},
        {"FINAL_SUBMISSION"},
        {
            "LLM_SUGGESTIONS",
            "SELECTED_SUGGESTIONS",
            "FINAL_SUBMISSION",
        },
    ],
    ids=[
        "suggested",
        "selected",
        "final",
        "all",
    ],
)
def test_completed_ai_row_requires_every_payload(
    null_columns: set[str],
) -> None:
    row = completed_ai_source_row()

    for column_name in null_columns:
        row[column_name] = None

    with pytest.raises(
        AuditRowError,
        match="completed AI row requires all analysis payloads",
    ) as captured:
        next(
            process_audit_rows(
                [row],
                config=AuditReportConfig(),
            )
        )

    message = str(captured.value)

    assert captured.value.row_number == 1
    assert captured.value.record_id == 1001

    for column_name in null_columns:
        assert column_name in message


def test_completed_ai_payload_error_does_not_include_payload_values() -> None:
    confidential_value = "CONFIDENTIAL-PAYLOAD-CONTENT"
    row = completed_ai_source_row()
    row["LLM_SUGGESTIONS"] = confidential_value
    row["SELECTED_SUGGESTIONS"] = None

    with pytest.raises(AuditRowError) as captured:
        next(
            process_audit_rows(
                [row],
                config=AuditReportConfig(),
            )
        )

    assert "SELECTED_SUGGESTIONS" in str(captured.value)
    assert confidential_value not in str(captured.value)


@pytest.mark.parametrize(
    "missing_column",
    [
        "END_TIME",
        "ATTEMPT_TYPE",
        "ATTEMPT_RESULT",
        "LLM_SUGGESTIONS",
        "SELECTED_SUGGESTIONS",
        "FINAL_SUBMISSION",
    ],
)
def test_completed_ai_row_rejects_missing_processing_column(
    missing_column: str,
) -> None:
    row = completed_ai_source_row()
    del row[missing_column]

    with pytest.raises(
        AuditRowError,
        match=f"source row is missing required column '{missing_column}'",
    ):
        next(
            process_audit_rows(
                [row],
                config=AuditReportConfig(),
            )
        )


def test_process_audit_rows_preserves_every_selected_and_skipped_record() -> None:
    rows = [
        manual_source_row(record_id=1),
        incomplete_ai_source_row(record_id=2),
        completed_ai_source_row(record_id=3),
    ]

    outcomes = list(
        process_audit_rows(
            rows,
            config=AuditReportConfig(),
        )
    )

    assert [outcome.record_id for outcome in outcomes] == [1, 2, 3]
    assert [outcome.analyzed for outcome in outcomes] == [
        False,
        False,
        True,
    ]
    assert outcomes[0].metric_rows == ()
    assert outcomes[1].metric_rows == ()
    assert len(outcomes[2].metric_rows) == 12


def test_process_audit_rows_assigns_one_based_source_numbers() -> None:
    outcomes = list(
        process_audit_rows(
            [
                manual_source_row(record_id=1),
                completed_ai_source_row(record_id=2),
            ],
            config=AuditReportConfig(),
        )
    )

    assert outcomes[0].source_row_number == 1
    assert outcomes[1].source_row_number == 2


def test_processing_rejects_duplicate_integer_ids() -> None:
    rows = [
        manual_source_row(record_id=7),
        completed_ai_source_row(record_id=7),
    ]

    with pytest.raises(
        AuditRowError,
        match="duplicate record ID",
    ) as captured:
        list(
            process_audit_rows(
                rows,
                config=AuditReportConfig(),
            )
        )

    assert captured.value.row_number == 2
    assert captured.value.record_id == 7


def test_processing_rejects_duplicate_string_ids() -> None:
    rows = [
        manual_source_row(record_id="audit-7"),
        completed_ai_source_row(record_id="audit-7"),
    ]

    with pytest.raises(
        AuditRowError,
        match="duplicate record ID",
    ):
        list(
            process_audit_rows(
                rows,
                config=AuditReportConfig(),
            )
        )


def test_integer_and_string_ids_are_distinct() -> None:
    outcomes = list(
        process_audit_rows(
            [
                manual_source_row(record_id=7),
                manual_source_row(record_id="7"),
            ],
            config=AuditReportConfig(),
        )
    )

    assert [outcome.record_id for outcome in outcomes] == [
        7,
        "7",
    ]


def test_process_audit_rows_rejects_non_mapping_source_value() -> None:
    invalid_rows = cast(
        "Iterable[Row]",
        [42],
    )

    with pytest.raises(
        AuditRowError,
        match="source value must be a row mapping",
    ):
        list(
            process_audit_rows(
                invalid_rows,
                config=AuditReportConfig(),
            )
        )


def test_process_audit_rows_rejects_non_string_key() -> None:
    invalid_row = cast(
        "Row",
        {1: "value"},
    )

    with pytest.raises(
        AuditRowError,
        match="source row column names must be strings",
    ):
        list(
            process_audit_rows(
                [invalid_row],
                config=AuditReportConfig(),
            )
        )


def test_processing_is_lazy() -> None:
    events: list[str] = []

    def rows() -> Iterator[Row]:
        events.append("first")
        yield manual_source_row(record_id=1)
        events.append("second")
        yield completed_ai_source_row(record_id=2)

    outcomes = process_audit_rows(
        rows(),
        config=AuditReportConfig(),
    )

    assert events == []

    first = next(outcomes)

    assert first.record_id == 1
    assert events == ["first"]

    second = next(outcomes)

    assert second.record_id == 2
    assert events == ["first", "second"]


def test_metric_rows_are_fresh_dictionaries() -> None:
    outcome = next(
        process_audit_rows(
            [completed_ai_source_row()],
            config=AuditReportConfig(),
        )
    )
    title = metric_row_for_field(outcome, "title")
    purpose = metric_row_for_field(outcome, "purpose")

    assert title is not purpose


# ---------------------------------------------------------------------------
# Error-model context
# ---------------------------------------------------------------------------


def test_audit_row_error_without_context_uses_plain_message() -> None:
    error = AuditRowError("failed")

    assert str(error) == "failed"
    assert error.row_number is None
    assert error.record_id is None


def test_audit_row_error_with_row_context() -> None:
    error = AuditRowError(
        "failed",
        row_number=3,
    )

    assert str(error) == "source row 3: failed"


def test_audit_row_error_with_record_context() -> None:
    error = AuditRowError(
        "failed",
        record_id="audit-3",
    )

    assert str(error) == "record 'audit-3': failed"


def test_audit_row_error_with_full_context() -> None:
    error = AuditRowError(
        "failed",
        row_number=3,
        record_id=1001,
    )

    assert str(error) == "source row 3, record 1001: failed"
