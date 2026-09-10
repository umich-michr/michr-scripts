"""Tests for pure audit-row payload classification and analysis processing."""

from collections.abc import Iterable, Iterator
from typing import cast

import pytest

from study_posting_audit_report import (
    AuditColumnMapping,
    AuditReportConfig,
    AuditRowError,
    PayloadState,
    ProcessedAuditRow,
    analyze_audit_row,
    classify_payload_state,
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


def analyzable_source_row(
    *,
    record_id: object = 1001,
) -> Row:
    """Return one valid source row with all analysis payloads present."""
    suggested, selected, final = valid_analysis_objects()

    return {
        "ID": record_id,
        "LLM_SUGGESTIONS": suggested,
        "SELECTED_SUGGESTIONS": selected,
        "FINAL_SUBMISSION": final,
        "STUDY_NUM": "HUM00000001",
    }


def skipped_source_row(
    *,
    record_id: object = 1002,
) -> Row:
    """Return one source row with all analysis payloads null."""
    return {
        "ID": record_id,
        "LLM_SUGGESTIONS": None,
        "SELECTED_SUGGESTIONS": None,
        "FINAL_SUBMISSION": None,
        "STUDY_NUM": "HUM00000002",
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


def test_source_schema_does_not_require_attempt_columns() -> None:
    schema = source_schema()

    assert "ATTEMPT_TYPE" not in schema.column_names
    assert "ATTEMPT_RESULT" not in schema.column_names

    validate_source_schema(
        schema,
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

    assert "LLM_SUGGESTIONS" in message
    assert "SELECTED_SUGGESTIONS" in message
    assert "FINAL_SUBMISSION" in message


def test_source_schema_uses_custom_column_mapping() -> None:
    config = AuditReportConfig(
        columns=AuditColumnMapping(
            record_id="AUDIT_ID",
            llm_suggestions="SUGGESTED",
            selected_suggestions="SELECTED",
            final_submission="FINAL",
        )
    )
    schema = RowSchema(
        columns=(
            ColumnSpec("AUDIT_ID", ColumnType.INTEGER),
            ColumnSpec("SUGGESTED", ColumnType.JSON_OBJECT),
            ColumnSpec("SELECTED", ColumnType.JSON_OBJECT),
            ColumnSpec("FINAL", ColumnType.JSON_OBJECT),
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
# Payload-state classification
# ---------------------------------------------------------------------------


def test_three_present_payloads_are_analyzable() -> None:
    state = classify_payload_state(
        analyzable_source_row(),
        config=AuditReportConfig(),
        row_number=1,
        record_id=1001,
    )

    assert state is PayloadState.ANALYZABLE


def test_three_null_payloads_are_skipped() -> None:
    state = classify_payload_state(
        skipped_source_row(),
        config=AuditReportConfig(),
        row_number=1,
        record_id=1002,
    )

    assert state is PayloadState.SKIPPED


@pytest.mark.parametrize(
    "present_columns",
    [
        {"LLM_SUGGESTIONS"},
        {"SELECTED_SUGGESTIONS"},
        {"FINAL_SUBMISSION"},
        {"LLM_SUGGESTIONS", "SELECTED_SUGGESTIONS"},
        {"LLM_SUGGESTIONS", "FINAL_SUBMISSION"},
        {"SELECTED_SUGGESTIONS", "FINAL_SUBMISSION"},
    ],
    ids=[
        "suggested-only",
        "selected-only",
        "final-only",
        "suggested-and-selected",
        "suggested-and-final",
        "selected-and-final",
    ],
)
def test_partial_payload_presence_is_rejected(
    present_columns: set[str],
) -> None:
    suggested, selected, final = valid_analysis_objects()
    values: dict[str, object] = {
        "LLM_SUGGESTIONS": suggested,
        "SELECTED_SUGGESTIONS": selected,
        "FINAL_SUBMISSION": final,
    }
    row: Row = {
        "ID": 1001,
        **{
            column: value if column in present_columns else None
            for column, value in values.items()
        },
    }

    with pytest.raises(
        AuditRowError,
        match="analysis payloads must be either all null or all present",
    ) as captured:
        classify_payload_state(
            row,
            config=AuditReportConfig(),
            row_number=4,
            record_id=1001,
        )

    assert captured.value.row_number == 4
    assert captured.value.record_id == 1001


def test_partial_payload_error_identifies_presence_without_payload_values() -> None:
    confidential_value = "CONFIDENTIAL-PAYLOAD-CONTENT"
    row: Row = {
        "ID": 1001,
        "LLM_SUGGESTIONS": confidential_value,
        "SELECTED_SUGGESTIONS": None,
        "FINAL_SUBMISSION": None,
    }

    with pytest.raises(AuditRowError) as captured:
        classify_payload_state(
            row,
            config=AuditReportConfig(),
            row_number=8,
            record_id=1001,
        )

    message = str(captured.value)

    assert "LLM_SUGGESTIONS" in message
    assert "SELECTED_SUGGESTIONS" in message
    assert "FINAL_SUBMISSION" in message
    assert confidential_value not in message


@pytest.mark.parametrize(
    "missing_column",
    [
        "LLM_SUGGESTIONS",
        "SELECTED_SUGGESTIONS",
        "FINAL_SUBMISSION",
    ],
)
def test_payload_classification_rejects_missing_column(
    missing_column: str,
) -> None:
    row = analyzable_source_row()
    del row[missing_column]

    with pytest.raises(
        AuditRowError,
        match=f"source row is missing required column '{missing_column}'",
    ) as captured:
        classify_payload_state(
            row,
            config=AuditReportConfig(),
            row_number=5,
            record_id=1001,
        )

    assert captured.value.row_number == 5
    assert captured.value.record_id == 1001


def test_attempt_values_do_not_influence_analyzable_state() -> None:
    row = analyzable_source_row()
    row["ATTEMPT_TYPE"] = "MANUAL"
    row["ATTEMPT_RESULT"] = "FAILED"

    state = classify_payload_state(
        row,
        config=AuditReportConfig(),
        row_number=1,
        record_id=1001,
    )

    assert state is PayloadState.ANALYZABLE


def test_attempt_values_do_not_influence_skipped_state() -> None:
    row = skipped_source_row()
    row["ATTEMPT_TYPE"] = "AI"
    row["ATTEMPT_RESULT"] = "COMPLETE"

    state = classify_payload_state(
        row,
        config=AuditReportConfig(),
        row_number=1,
        record_id=1002,
    )

    assert state is PayloadState.SKIPPED


# ---------------------------------------------------------------------------
# Audit-row analysis
# ---------------------------------------------------------------------------


def test_analyze_audit_row_produces_one_metric_row_per_field() -> None:
    metric_rows = analyze_audit_row(
        analyzable_source_row(),
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
        analyzable_source_row(),
        config=AuditReportConfig(),
        row_number=1,
        record_id="audit-1001",
    )

    assert all(row["record_id"] == "audit-1001" for row in metric_rows)


def test_analyze_audit_row_excludes_text_by_default() -> None:
    metric_rows = analyze_audit_row(
        analyzable_source_row(),
        config=AuditReportConfig(),
        row_number=1,
        record_id=1001,
    )

    for row in metric_rows:
        assert row["selected_text"] is None
        assert row["final_text"] is None


def test_analyze_audit_row_includes_text_when_enabled() -> None:
    metric_rows = analyze_audit_row(
        analyzable_source_row(),
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
    row = analyzable_source_row()
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
    row = analyzable_source_row()
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
    row = analyzable_source_row()
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
# Stream processing
# ---------------------------------------------------------------------------


def test_process_audit_rows_preserves_every_source_record() -> None:
    rows = [
        skipped_source_row(record_id=1),
        analyzable_source_row(record_id=2),
    ]

    outcomes = list(
        process_audit_rows(
            rows,
            config=AuditReportConfig(),
        )
    )

    assert len(outcomes) == 2

    assert outcomes[0].record_id == 1
    assert outcomes[0].analyzed is False
    assert outcomes[0].metric_rows == ()

    assert outcomes[1].record_id == 2
    assert outcomes[1].analyzed is True
    assert len(outcomes[1].metric_rows) == 12


def test_process_audit_rows_assigns_one_based_source_numbers() -> None:
    outcomes = list(
        process_audit_rows(
            [
                skipped_source_row(record_id=1),
                analyzable_source_row(record_id=2),
            ],
            config=AuditReportConfig(),
        )
    )

    assert outcomes[0].source_row_number == 1
    assert outcomes[1].source_row_number == 2


def test_processed_record_is_a_fresh_dictionary() -> None:
    original = skipped_source_row()

    outcome = next(
        process_audit_rows(
            [original],
            config=AuditReportConfig(),
        )
    )

    assert outcome.record == original
    assert outcome.record is not original


def test_processing_rejects_partial_payload_presence() -> None:
    row = skipped_source_row()
    row["LLM_SUGGESTIONS"] = "not-json"

    with pytest.raises(
        AuditRowError,
        match="analysis payloads must be either all null or all present",
    ) as captured:
        next(
            process_audit_rows(
                [row],
                config=AuditReportConfig(),
            )
        )

    assert captured.value.row_number == 1
    assert captured.value.record_id == 1002


def test_processing_analyzes_three_present_payloads_regardless_of_shape() -> None:
    row = analyzable_source_row()
    row["LLM_SUGGESTIONS"] = "not-json"
    row["SELECTED_SUGGESTIONS"] = object()
    row["FINAL_SUBMISSION"] = 42

    with pytest.raises(
        AuditRowError,
        match="analysis failed",
    ) as captured:
        next(
            process_audit_rows(
                [row],
                config=AuditReportConfig(),
            )
        )

    assert captured.value.row_number == 1
    assert captured.value.record_id == 1001
    assert captured.value.__cause__ is not None


def test_processing_ignores_attempt_values_for_present_payloads() -> None:
    row = analyzable_source_row()
    row["ATTEMPT_TYPE"] = "MANUAL"
    row["ATTEMPT_RESULT"] = "FAILED"

    outcome = next(
        process_audit_rows(
            [row],
            config=AuditReportConfig(),
        )
    )

    assert outcome.analyzed is True
    assert len(outcome.metric_rows) == 12


def test_processing_ignores_attempt_values_for_null_payloads() -> None:
    row = skipped_source_row()
    row["ATTEMPT_TYPE"] = "AI"
    row["ATTEMPT_RESULT"] = "COMPLETE"

    outcome = next(
        process_audit_rows(
            [row],
            config=AuditReportConfig(),
        )
    )

    assert outcome.analyzed is False
    assert outcome.metric_rows == ()


def test_processing_rejects_duplicate_integer_ids() -> None:
    rows = [
        skipped_source_row(record_id=7),
        analyzable_source_row(record_id=7),
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
        skipped_source_row(record_id="audit-7"),
        analyzable_source_row(record_id="audit-7"),
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
                skipped_source_row(record_id=7),
                skipped_source_row(record_id="7"),
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
        yield skipped_source_row(record_id=1)
        events.append("second")
        yield analyzable_source_row(record_id=2)

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
            [analyzable_source_row()],
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
