"""Tests for conversion of analysis results into flat rows."""

import json
from pathlib import Path

import pytest

from study_posting_ai_analysis.field_analysis import (
    analyze_lookup_values,
    analyze_objects,
)
from study_posting_ai_analysis.flattening import (
    FLATTENED_COLUMNS,
    flatten_analysis_results,
    serialize_integer_set,
)
from study_posting_ai_analysis.metrics import analyze_selected_suggestion
from study_posting_ai_analysis.models import (
    AnalysisResult,
    CompensationAnalysis,
    MatchType,
    Pick,
    TextFieldAnalysis,
)

type AuditObjects = tuple[
    dict[str, object],
    dict[str, object],
    dict[str, object],
]


def make_text_result(
    *,
    match: MatchType,
    selected: str | None,
    final: str,
) -> TextFieldAnalysis:
    """Return a text result, with metrics only when a selection was made."""
    metrics = (
        analyze_selected_suggestion(
            field_name="title",
            suggestion=selected,
            final=final,
        )
        if selected is not None and final.strip()
        else None
    )

    return TextFieldAnalysis(
        suggestion_counts={"title": 1},
        pick=Pick(kind="title", index=0) if selected is not None else None,
        match=match,
        editing_metrics=metrics,
        selected_text=selected,
        final_text=final,
    )


# ---------------------------------------------------------------------------
# serialize_integer_set
# ---------------------------------------------------------------------------


def test_identifiers_are_rendered_sorted() -> None:
    """Sorted output keeps exported rows stable across runs."""
    assert serialize_integer_set(frozenset({3, 1, 2})) == "[1, 2, 3]"


def test_empty_set_renders_as_an_empty_array() -> None:
    assert serialize_integer_set(frozenset()) == "[]"


def test_rendered_identifiers_round_trip_through_json() -> None:
    """A consumer must be able to recover the set from the exported text."""
    values = frozenset({10, 20, 30})

    assert set(json.loads(serialize_integer_set(values))) == values


# ---------------------------------------------------------------------------
# Row shape
# ---------------------------------------------------------------------------


def test_every_row_has_every_column_in_order(
    valid_audit_objects: AuditObjects,
) -> None:
    """A consumer writes one header and relies on it for all rows."""
    rows = flatten_analysis_results(analyze_objects(*valid_audit_objects))

    assert rows

    for row in rows:
        assert tuple(row) == FLATTENED_COLUMNS


def test_one_row_is_produced_per_analyzed_field(
    valid_audit_objects: AuditObjects,
) -> None:
    results = analyze_objects(*valid_audit_objects)
    rows = flatten_analysis_results(results)

    assert len(rows) == len(results)
    assert {row["field_name"] for row in rows} == set(results)


def test_column_names_are_unique() -> None:
    assert len(FLATTENED_COLUMNS) == len(set(FLATTENED_COLUMNS))


@pytest.mark.parametrize(
    "record_id",
    [1234, "audit-1234", None],
    ids=["integer", "string", "absent"],
)
def test_record_id_is_carried_onto_every_row(
    valid_audit_objects: AuditObjects,
    record_id: str | int | None,
) -> None:
    rows = flatten_analysis_results(
        analyze_objects(*valid_audit_objects),
        record_id=record_id,
    )

    assert all(row["record_id"] == record_id for row in rows)


def test_analysis_type_distinguishes_the_three_result_kinds(
    valid_audit_objects: AuditObjects,
) -> None:
    rows = flatten_analysis_results(analyze_objects(*valid_audit_objects))

    assert {row["analysis_type"] for row in rows} == {
        "TEXT",
        "COMPENSATION",
        "LOOKUP",
    }


# ---------------------------------------------------------------------------
# Text rows
# ---------------------------------------------------------------------------


def test_exact_text_row_reports_full_scores() -> None:
    text = "Research Assistant"
    result = make_text_result(
        match=MatchType.EXACT,
        selected=text,
        final=text,
    )

    row = flatten_analysis_results({"title": result})[0]

    assert row["analysis_type"] == "TEXT"
    assert row["match_type"] == "EXACT"
    assert row["ter_effort_saved"] == pytest.approx(1.0)
    assert row["policy_adjusted_effort_saved"] == pytest.approx(1.0)
    assert row["character_edit_distance"] == 0
    assert row["suggestion_count_total"] == 1
    assert row["picked_kind"] == "title"
    assert row["picked_index"] == 0


def test_unassisted_row_has_no_metrics_but_a_policy_score() -> None:
    """Zero is a meaningful policy value; the TER score is undefined."""
    result = make_text_result(
        match=MatchType.UNASSISTED,
        selected=None,
        final="Written independently",
    )

    row = flatten_analysis_results({"title": result})[0]

    assert row["match_type"] == "UNASSISTED"
    assert row["ter_effort_saved"] is None
    assert row["ter_rate"] is None
    assert row["character_edit_distance"] is None
    assert row["policy_adjusted_effort_saved"] == pytest.approx(0.0)
    assert row["picked_kind"] is None
    assert row["picked_index"] is None


def test_removed_row_has_no_metrics_but_a_policy_score() -> None:
    result = make_text_result(
        match=MatchType.REMOVED,
        selected="https://example.edu",
        final="",
    )

    row = flatten_analysis_results({"contact.website": result})[0]

    assert row["match_type"] == "REMOVED"
    assert row["ter_effort_saved"] is None
    assert row["policy_adjusted_effort_saved"] == pytest.approx(0.0)
    assert row["picked_index"] == 0


def test_cosmetic_row_records_full_policy_credit_with_real_distance() -> None:
    """Policy credit is full, but the underlying metrics show the change."""
    result = make_text_result(
        match=MatchType.COSMETIC_EQUIVALENT,
        selected="Research Assistant",
        final="research assistant",
    )

    row = flatten_analysis_results({"title": result})[0]

    assert row["policy_adjusted_effort_saved"] == pytest.approx(1.0)

    character_distance = row["character_edit_distance"]
    assert isinstance(character_distance, int)
    assert character_distance > 0


def test_suggestion_counts_are_serialized_deterministically() -> None:
    result = CompensationAnalysis(
        suggestion_counts={
            "specificCompensation": 2,
            "genericCompensation": 1,
        },
        pick=None,
        match=MatchType.UNASSISTED,
        editing_metrics=None,
        selected_text=None,
        final_text="",
        flag_suggested=False,
        flag_saved=False,
    )

    row = flatten_analysis_results({"compensation": result})[0]

    assert row["suggestion_counts_json"] == (
        '{"genericCompensation": 1, "specificCompensation": 2}'
    )
    assert row["suggestion_count_total"] == 3


# ---------------------------------------------------------------------------
# Free text handling
# ---------------------------------------------------------------------------


def test_text_is_excluded_by_default() -> None:
    """Reduces accidental disclosure of potentially sensitive content."""
    result = make_text_result(
        match=MatchType.EXACT,
        selected="Sensitive study text",
        final="Sensitive study text",
    )

    row = flatten_analysis_results({"title": result})[0]

    assert row["selected_text"] is None
    assert row["final_text"] is None


def test_text_is_included_only_when_requested() -> None:
    result = make_text_result(
        match=MatchType.EXACT,
        selected="Offered title",
        final="Offered title",
    )

    row = flatten_analysis_results(
        {"title": result},
        include_text=True,
    )[0]

    assert row["selected_text"] == "Offered title"
    assert row["final_text"] == "Offered title"


def test_no_text_appears_anywhere_in_a_row_by_default(
    valid_audit_objects: AuditObjects,
) -> None:
    """Guards against text leaking through a column other than the two."""
    suggested, selected, final = valid_audit_objects

    marker = "UNIQUEMARKERTEXT"
    final["title"] = marker
    suggested["title"] = [marker]
    selected["title"] = [marker]

    rows = flatten_analysis_results(analyze_objects(suggested, selected, final))

    for row in rows:
        for value in row.values():
            assert marker not in str(value)


# ---------------------------------------------------------------------------
# Compensation rows
# ---------------------------------------------------------------------------


def test_compensation_row_reports_both_flag_and_text_outcomes(
    valid_audit_objects: AuditObjects,
) -> None:
    suggested, selected, final = valid_audit_objects

    offer = "Participants receive a $50 gift card."
    suggested["compensation"] = {
        "genericCompensation": [],
        "specificCompensation": [offer],
    }
    selected["compensation"] = {
        "genericCompensation": [],
        "specificCompensation": [offer],
    }
    suggested["offersCompensation"] = True
    final["offersCompensation"] = True
    final["compensation"] = offer

    rows = flatten_analysis_results(analyze_objects(suggested, selected, final))
    row = next(row for row in rows if row["field_name"] == "compensation")

    assert row["analysis_type"] == "COMPENSATION"
    assert row["match_type"] == "EXACT"
    assert row["flag_suggested"] is True
    assert row["flag_saved"] is True
    assert row["flag_accepted"] is True
    assert row["flag_changed"] is False
    assert row["compensation_text_required"] is True
    assert row["picked_kind"] == "specificCompensation"


def test_undefined_flag_acceptance_is_none_not_false() -> None:
    """A missing recommendation must be excludable from an acceptance rate."""
    result = CompensationAnalysis(
        suggestion_counts={
            "genericCompensation": 0,
            "specificCompensation": 0,
        },
        pick=None,
        match=MatchType.UNASSISTED,
        editing_metrics=None,
        selected_text=None,
        final_text="",
        flag_suggested=None,
        flag_saved=False,
    )

    row = flatten_analysis_results({"compensation": result})[0]

    assert row["flag_suggested"] is None
    assert row["flag_accepted"] is None
    assert row["flag_changed"] is None


def test_text_columns_are_unset_on_a_compensation_row_without_metrics() -> None:
    result = CompensationAnalysis(
        suggestion_counts={
            "genericCompensation": 1,
            "specificCompensation": 0,
        },
        pick=None,
        match=MatchType.UNASSISTED,
        editing_metrics=None,
        selected_text=None,
        final_text="",
        flag_suggested=True,
        flag_saved=False,
    )

    row = flatten_analysis_results({"compensation": result})[0]

    assert row["ter_rate"] is None
    assert row["character_edit_distance"] is None
    assert row["soft_word_edit_distance"] is None
    assert row["estimated_characters_saved"] is None


# ---------------------------------------------------------------------------
# Lookup rows
# ---------------------------------------------------------------------------


def test_lookup_row_reports_similarity_and_every_identifier_set() -> None:
    result = analyze_lookup_values(
        suggested=[1, 2, 3],
        picked=[1, 2],
        saved=[2, 3, 9],
    )

    row = flatten_analysis_results({"topics": result}, record_id="record-1")[0]

    assert row["analysis_type"] == "LOOKUP"
    assert row["match_type"] == "EDITED"
    assert row["lookup_similarity"] == pytest.approx(1.0 / 4.0)
    assert row["offered_ids"] == "[1, 2, 3]"
    assert row["picked_ids"] == "[1, 2]"
    assert row["saved_ids"] == "[2, 3, 9]"
    assert row["kept_ids"] == "[2]"
    assert row["dropped_ids"] == "[1]"
    assert row["added_ids"] == "[3, 9]"
    assert row["saved_not_offered_ids"] == "[9]"


def test_lookup_similarity_is_not_written_into_a_text_column() -> None:
    """Similarity and text effort saved measure different constructs.

    A lookup row must leave the TER and policy columns unset, so that a mean
    over text rows cannot be contaminated by a lookup value. See specification
    section 11.
    """
    result = analyze_lookup_values(
        suggested=[1, 2, 3],
        picked=[1, 2],
        saved=[2, 3],
    )

    row = flatten_analysis_results({"topics": result})[0]

    assert row["ter_rate"] is None
    assert row["ter_effort_saved"] is None
    assert row["ter_effort_saved_raw"] is None
    assert row["policy_adjusted_effort_saved"] is None
    assert row["character_effort_saved"] is None
    assert row["soft_word_effort_saved"] is None
    assert row["lookup_similarity"] == pytest.approx(1.0 / 3.0)


def test_unassisted_lookup_row_reports_the_policy_similarity() -> None:
    result = analyze_lookup_values(suggested=[1, 2], picked=[], saved=[5])

    row = flatten_analysis_results({"topics": result})[0]

    assert row["match_type"] == "UNASSISTED"
    assert row["lookup_similarity"] == pytest.approx(0.0)
    assert row["picked_ids"] == "[]"
    assert row["saved_not_offered_ids"] == "[5]"


def test_lookup_row_leaves_suggestion_count_columns_unset() -> None:
    """Suggestion counts describe text offers, not identifier sets."""
    result = analyze_lookup_values(suggested=[1], picked=[1], saved=[1])

    row = flatten_analysis_results({"topics": result})[0]

    assert row["suggestion_count_total"] is None
    assert row["suggestion_counts_json"] is None
    assert row["picked_kind"] is None
    assert row["picked_index"] is None


# ---------------------------------------------------------------------------
# Consumer usability
# ---------------------------------------------------------------------------


def test_rows_contain_only_types_a_csv_writer_can_handle(
    valid_audit_objects: AuditObjects,
) -> None:
    """No nested structures: a consumer writes rows without conversion."""
    rows = flatten_analysis_results(
        analyze_objects(*valid_audit_objects),
        include_text=True,
    )

    permitted = (type(None), bool, int, float, str)

    for row in rows:
        for column, value in row.items():
            assert isinstance(value, permitted), f"{column}: {type(value)}"


def test_empty_results_produce_no_rows() -> None:
    empty: dict[str, AnalysisResult] = {}

    assert flatten_analysis_results(empty) == []


# ---------------------------------------------------------------------------
# Documentation alignment
# ---------------------------------------------------------------------------


def test_specification_documents_the_flattening_step() -> None:
    """Section 13 describes the conversion to one row per field."""
    specification = Path("docs/analysis-specification.md").read_text(encoding="utf-8")

    assert "flatten_analysis_results" in specification
