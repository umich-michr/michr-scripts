"""Tests for contact subfield analysis."""

import pytest

from study_posting_ai_analysis.field_analysis import (
    analyze_contact,
    clean_contact,
)
from study_posting_ai_analysis.models import MatchType

ALL_CONTACT_RESULTS = frozenset(
    {
        "contact.email",
        "contact.name",
        "contact.phone",
        "contact.website",
    }
)

REQUIRED = frozenset({"email", "name"})


# ---------------------------------------------------------------------------
# clean_contact
# ---------------------------------------------------------------------------


def test_absent_subfields_become_empty_strings() -> None:
    assert clean_contact({"email": "a@example.edu"}) == {
        "email": "a@example.edu",
        "name": "",
        "phone": "",
        "website": "",
    }


def test_none_payload_yields_all_empty_strings() -> None:
    assert clean_contact(None) == {
        "email": "",
        "name": "",
        "phone": "",
        "website": "",
    }


def test_null_subfield_becomes_an_empty_string() -> None:
    assert clean_contact({"email": None})["email"] == ""


def test_unknown_subfield_is_rejected() -> None:
    """A new form field must not be silently ignored."""
    with pytest.raises(ValueError, match="Unknown contact fields"):
        clean_contact({"fax": "555-0100"})


def test_non_object_payload_is_rejected() -> None:
    with pytest.raises(TypeError, match="must be a dictionary"):
        clean_contact("a@example.edu")


def test_non_string_subfield_value_is_rejected() -> None:
    with pytest.raises(TypeError, match=r"contact\.phone must be a string"):
        clean_contact({"phone": 5550100})


# ---------------------------------------------------------------------------
# analyze_contact
# ---------------------------------------------------------------------------


def test_every_subfield_is_analyzed_separately() -> None:
    results = analyze_contact(
        suggested={
            "email": "test@example.edu",
            "name": "Test Person",
            "phone": "555-0100",
            "website": "https://example.edu",
        },
        selected={
            "email": "test@example.edu",
            "name": "Test Person",
            "phone": "",
            "website": "",
        },
        saved={
            "email": "test@example.edu",
            "name": "Test Person",
            "phone": "",
            "website": "",
        },
        required_fields=REQUIRED,
    )

    assert frozenset(results) == ALL_CONTACT_RESULTS
    assert results["contact.email"].match is MatchType.EXACT
    assert results["contact.name"].match is MatchType.EXACT
    assert results["contact.phone"].match is MatchType.UNASSISTED
    assert results["contact.website"].match is MatchType.UNASSISTED


def test_offered_but_unselected_subfield_counts_the_offer() -> None:
    """Offer coverage requires counting a suggestion that was not taken."""
    results = analyze_contact(
        suggested={"phone": "555-0100"},
        selected={},
        saved={"email": "a@example.edu", "name": "N", "phone": ""},
        required_fields=REQUIRED,
    )

    assert results["contact.phone"].suggestion_counts == {"contact.phone": 1}
    assert results["contact.phone"].match is MatchType.UNASSISTED


def test_pick_index_is_always_zero_for_contact() -> None:
    """A contact subfield offers at most one suggestion."""
    results = analyze_contact(
        suggested={"email": "a@example.edu"},
        selected={"email": "a@example.edu"},
        saved={"email": "a@example.edu", "name": "N"},
        required_fields=REQUIRED,
    )

    pick = results["contact.email"].pick

    assert pick is not None
    assert pick.kind == "contact.email"
    assert pick.index == 0


def test_edited_subfield_records_metrics() -> None:
    results = analyze_contact(
        suggested={"name": "Test Person"},
        selected={"name": "Test Person"},
        saved={"email": "a@example.edu", "name": "Testing Person"},
        required_fields=REQUIRED,
    )

    result = results["contact.name"]

    assert result.match is MatchType.EDITED
    assert result.editing_metrics is not None
    assert result.pick is not None
    assert result.pick.kind == "contact.name"


def test_optional_subfield_cleared_after_selection_is_removed() -> None:
    results = analyze_contact(
        suggested={"website": "https://example.edu"},
        selected={"website": "https://example.edu"},
        saved={"email": "a@example.edu", "name": "N", "website": ""},
        required_fields=REQUIRED,
    )

    result = results["contact.website"]

    assert result.match is MatchType.REMOVED
    assert result.editing_metrics is None


# ---------------------------------------------------------------------------
# Requiredness
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "required_field",
    ["email", "name"],
    ids=["email", "name"],
)
def test_required_subfield_rejects_blank_final(required_field: str) -> None:
    with pytest.raises(
        ValueError,
        match=rf"contact\.{required_field}: final saved text must not be blank",
    ):
        analyze_contact(
            suggested={},
            selected={},
            saved={},
            required_fields=frozenset({required_field}),
        )


def test_optional_subfields_permit_blank_finals() -> None:
    results = analyze_contact(
        suggested={},
        selected={},
        saved={},
        required_fields=frozenset(),
    )

    assert len(results) == 4

    for result in results.values():
        assert result.match is MatchType.UNASSISTED
        assert result.editing_metrics is None


def test_unknown_required_subfield_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown required contact fields"):
        analyze_contact(
            suggested={},
            selected={},
            saved={},
            required_fields=frozenset({"fax"}),
        )


# ---------------------------------------------------------------------------
# Selection consistency
# ---------------------------------------------------------------------------


def test_selection_without_an_offer_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="a contact suggestion was selected, but no suggestion was offered",
    ):
        analyze_contact(
            suggested={},
            selected={"email": "a@example.edu"},
            saved={"email": "a@example.edu", "name": "N"},
            required_fields=REQUIRED,
        )


def test_selection_differing_from_the_offer_is_rejected() -> None:
    """The selection must be the offered text, not a variant of it."""
    with pytest.raises(
        ValueError,
        match="selected text does not match the offered suggestion",
    ):
        analyze_contact(
            suggested={"email": "offered@example.edu"},
            selected={"email": "different@example.edu"},
            saved={"email": "different@example.edu", "name": "N"},
            required_fields=REQUIRED,
        )
