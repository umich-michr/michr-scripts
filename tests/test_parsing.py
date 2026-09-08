"""Tests for JSON input decoding."""

import pytest

from study_posting_ai_analysis.errors import InputParseError
from study_posting_ai_analysis.field_analysis import analyze_objects
from study_posting_ai_analysis.parsing import (
    parse_analysis_inputs,
    parse_json_object,
)

# ---------------------------------------------------------------------------
# Accepted forms
# ---------------------------------------------------------------------------


def test_decodes_a_json_string() -> None:
    assert parse_json_object('{"title": ["A"]}', name="input") == {"title": ["A"]}


def test_decodes_utf8_bytes() -> None:
    assert parse_json_object(b'{"title": "A"}', name="input") == {"title": "A"}


def test_passes_through_an_existing_mapping() -> None:
    """A caller holding dictionaries need not serialize them first."""
    payload = {"title": "A"}

    assert parse_json_object(payload, name="input") == payload


def test_accepts_an_empty_object() -> None:
    """An empty object is valid: nothing was suggested or selected."""
    assert parse_json_object("{}", name="input") == {}


def test_decodes_non_ascii_content() -> None:
    result = parse_json_object('{"title": "caf\\u00e9"}', name="input")

    assert result == {"title": "caf\u00e9"}


# ---------------------------------------------------------------------------
# Rejected forms
# ---------------------------------------------------------------------------


def test_absent_value_is_rejected() -> None:
    with pytest.raises(InputParseError, match="input is missing"):
        parse_json_object(None, name="input")


@pytest.mark.parametrize(
    "blank",
    ["", "   ", "\n\t"],
    ids=["empty", "spaces", "tabs-newlines"],
)
def test_blank_value_is_reported_as_blank_not_as_a_syntax_error(
    blank: str,
) -> None:
    """An empty column is a distinct condition, not a parse failure."""
    with pytest.raises(InputParseError, match="input is blank"):
        parse_json_object(blank, name="input")


def test_malformed_json_reports_its_position() -> None:
    with pytest.raises(InputParseError, match=r"invalid JSON at line 1, column 2"):
        parse_json_object("{", name="input")


def test_invalid_utf8_bytes_are_reported_as_an_encoding_problem() -> None:
    """UnicodeDecodeError falls outside JSONDecodeError, so it is caught here."""
    with pytest.raises(InputParseError, match="input is not valid UTF-8"):
        parse_json_object(b"\xff\xfe{}", name="input")


@pytest.mark.parametrize(
    ("payload", "type_name"),
    [
        ("[1, 2]", "list"),
        ("42", "int"),
        ('"text"', "str"),
        ("null", "NoneType"),
        ("true", "bool"),
    ],
    ids=["array", "integer", "string", "null", "boolean"],
)
def test_non_object_json_is_rejected(payload: str, type_name: str) -> None:
    with pytest.raises(
        InputParseError,
        match=rf"must contain a JSON object, received {type_name}",
    ):
        parse_json_object(payload, name="input")


def test_error_message_names_the_input() -> None:
    """The label lets a caller identify which column failed."""
    with pytest.raises(InputParseError, match="LLM_SUGGESTIONS is blank"):
        parse_json_object("", name="LLM_SUGGESTIONS")


def test_parse_error_is_a_value_error() -> None:
    """Callers using "except ValueError" continue to work."""
    with pytest.raises(ValueError, match="is missing"):
        parse_json_object(None, name="input")


# ---------------------------------------------------------------------------
# parse_analysis_inputs
# ---------------------------------------------------------------------------


def test_decodes_all_three_payloads_in_order() -> None:
    suggested, selected, final = parse_analysis_inputs(
        '{"title": ["Offered"]}',
        '{"title": ["Offered"]}',
        '{"title": "Offered"}',
    )

    assert suggested == {"title": ["Offered"]}
    assert selected == {"title": ["Offered"]}
    assert final == {"title": "Offered"}


@pytest.mark.parametrize(
    ("position", "expected_name"),
    [(0, "suggested"), (1, "selected"), (2, "final")],
    ids=["suggested", "selected", "final"],
)
def test_default_labels_identify_the_failing_payload(
    position: int,
    expected_name: str,
) -> None:
    arguments: list[object] = ['{"a": 1}', '{"a": 1}', '{"a": 1}']
    arguments[position] = None

    with pytest.raises(InputParseError, match=f"{expected_name} is missing"):
        parse_analysis_inputs(*arguments)


def test_labels_can_be_overridden_to_match_column_names() -> None:
    """A consumer reading a database reports the failing column by name."""
    with pytest.raises(InputParseError, match="FINAL_SUBMISSION is blank"):
        parse_analysis_inputs(
            '{"a": 1}',
            '{"a": 1}',
            "",
            suggested_name="LLM_SUGGESTIONS",
            selected_name="SELECTED_SUGGESTIONS",
            final_name="FINAL_SUBMISSION",
        )


def test_decoded_output_is_accepted_by_analyze_objects() -> None:
    """The parse and analyze steps compose without an intermediate conversion."""
    suggested, selected, final = parse_analysis_inputs(
        '{"title": ["Offered title"], "offersCompensation": false}',
        '{"title": ["Offered title"]}',
        (
            '{"title": "Offered title", "purpose": "P", "description": "D",'
            ' "contact": {"email": "a@example.edu", "name": "N"},'
            ' "offersCompensation": false}'
        ),
    )

    results = analyze_objects(suggested, selected, final)

    assert results["title"].match.value == "EXACT"
