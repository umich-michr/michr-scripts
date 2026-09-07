"""Tests for analyze_objects, the field dispatcher."""

import pytest

from study_posting_ai_analysis.field_analysis import analyze_objects
from study_posting_ai_analysis.field_specs import FIELD_SPECS
from study_posting_ai_analysis.models import (
    CompensationAnalysis,
    FieldKind,
    LookupValueAnalysis,
    MatchType,
    TextFieldAnalysis,
)

type AuditObjects = tuple[
    dict[str, object],
    dict[str, object],
    dict[str, object],
]

EXPECTED_RESULT_FIELDS = frozenset(
    {
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
)


# ---------------------------------------------------------------------------
# Dispatch coverage
# ---------------------------------------------------------------------------


def test_every_configured_non_merged_field_is_returned(
    valid_audit_objects: AuditObjects,
) -> None:
    suggested, selected, final = valid_audit_objects

    results = analyze_objects(suggested, selected, final)

    assert frozenset(results) == EXPECTED_RESULT_FIELDS


def test_merged_field_produces_no_separate_entry(
    valid_audit_objects: AuditObjects,
) -> None:
    """OffersCompensation is reported within the compensation result."""
    suggested, selected, final = valid_audit_objects

    results = analyze_objects(suggested, selected, final)

    assert "offersCompensation" not in results
    assert isinstance(results["compensation"], CompensationAnalysis)


def test_contact_expands_into_four_prefixed_entries(
    valid_audit_objects: AuditObjects,
) -> None:
    suggested, selected, final = valid_audit_objects

    results = analyze_objects(suggested, selected, final)

    contact_names = {name for name in results if name.startswith("contact.")}

    assert len(contact_names) == 4
    assert "contact" not in results


def test_each_field_receives_its_configured_result_type(
    valid_audit_objects: AuditObjects,
) -> None:
    """Guards against a lookup field being routed to the text analyzer."""
    suggested, selected, final = valid_audit_objects

    results = analyze_objects(suggested, selected, final)

    for field_name, field_spec in FIELD_SPECS.items():
        if field_spec.kind in {FieldKind.MERGED, FieldKind.CONTACT}:
            continue

        result = results[field_name]

        if field_spec.kind is FieldKind.LOOKUP:
            assert isinstance(result, LookupValueAnalysis), field_name
        else:
            assert isinstance(result, TextFieldAnalysis), field_name


# ---------------------------------------------------------------------------
# Baseline outcomes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field_name",
    ["about", "description", "purpose", "title"],
    ids=["about", "description", "purpose", "title"],
)
def test_baseline_text_fields_are_exact(
    valid_audit_objects: AuditObjects,
    field_name: str,
) -> None:
    suggested, selected, final = valid_audit_objects

    results = analyze_objects(suggested, selected, final)

    assert results[field_name].match is MatchType.EXACT


@pytest.mark.parametrize(
    "field_name",
    ["contact.email", "contact.name"],
    ids=["email", "name"],
)
def test_baseline_contact_values_are_unassisted(
    valid_audit_objects: AuditObjects,
    field_name: str,
) -> None:
    """Required values written without a suggestion are valid but unassisted."""
    suggested, selected, final = valid_audit_objects

    results = analyze_objects(suggested, selected, final)

    assert results[field_name].match is MatchType.UNASSISTED


def test_baseline_compensation_is_unassisted_and_not_required(
    valid_audit_objects: AuditObjects,
) -> None:
    suggested, selected, final = valid_audit_objects

    results = analyze_objects(suggested, selected, final)
    compensation = results["compensation"]

    assert isinstance(compensation, CompensationAnalysis)
    assert compensation.match is MatchType.UNASSISTED
    assert compensation.compensation_text_required is False


@pytest.mark.parametrize(
    "field_name",
    ["department", "locations", "topics"],
    ids=["department", "locations", "topics"],
)
def test_baseline_lookup_fields_are_unassisted(
    valid_audit_objects: AuditObjects,
    field_name: str,
) -> None:
    suggested, selected, final = valid_audit_objects

    results = analyze_objects(suggested, selected, final)
    result = results[field_name]

    assert result.match is MatchType.UNASSISTED
    assert isinstance(result, LookupValueAnalysis)
    assert result.similarity == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Requiredness enforced through the dispatcher
# ---------------------------------------------------------------------------


def test_selected_title_cannot_be_cleared(
    valid_audit_objects: AuditObjects,
) -> None:
    """A required field cannot be REMOVED; it is a validation error."""
    suggested, selected, final = valid_audit_objects

    final["title"] = ""

    with pytest.raises(
        ValueError,
        match="title: final saved text must not be blank",
    ):
        analyze_objects(suggested, selected, final)


def test_unassisted_title_cannot_be_blank(
    valid_audit_objects: AuditObjects,
) -> None:
    suggested, selected, final = valid_audit_objects

    selected["title"] = []
    final["title"] = ""

    with pytest.raises(
        ValueError,
        match="title: final saved text must not be blank",
    ):
        analyze_objects(suggested, selected, final)


def test_optional_about_field_may_be_cleared(
    valid_audit_objects: AuditObjects,
) -> None:
    suggested, selected, final = valid_audit_objects

    final["about"] = ""

    results = analyze_objects(suggested, selected, final)
    about = results["about"]

    assert isinstance(about, TextFieldAnalysis)
    assert about.match is MatchType.REMOVED
    assert about.editing_metrics is None


def test_required_contact_email_cannot_be_blank(
    valid_audit_objects: AuditObjects,
) -> None:
    suggested, selected, final = valid_audit_objects

    contact = final["contact"]
    assert isinstance(contact, dict)
    contact["email"] = ""

    with pytest.raises(
        ValueError,
        match=r"contact\.email: final saved text must not be blank",
    ):
        analyze_objects(suggested, selected, final)


def test_compensation_text_is_required_when_saved_flag_is_true(
    valid_audit_objects: AuditObjects,
) -> None:
    suggested, selected, final = valid_audit_objects

    final["offersCompensation"] = True
    final["compensation"] = ""

    with pytest.raises(ValueError, match="final text is required"):
        analyze_objects(suggested, selected, final)


def test_missing_saved_compensation_flag_is_rejected(
    valid_audit_objects: AuditObjects,
) -> None:
    suggested, selected, final = valid_audit_objects

    del final["offersCompensation"]

    with pytest.raises(ValueError, match="must be saved as True or False"):
        analyze_objects(suggested, selected, final)


# ---------------------------------------------------------------------------
# Unknown field rejection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "object_name",
    ["suggested", "selected", "final"],
    ids=["suggested", "selected", "final"],
)
def test_unknown_field_is_rejected_in_any_object(
    valid_audit_objects: AuditObjects,
    object_name: str,
) -> None:
    """A new form field must not be silently ignored."""
    objects = dict(
        zip(
            ("suggested", "selected", "final"),
            valid_audit_objects,
            strict=True,
        )
    )

    objects[object_name]["unexpectedField"] = "value"

    with pytest.raises(ValueError, match="add them to FIELD_SPECS"):
        analyze_objects(
            objects["suggested"],
            objects["selected"],
            objects["final"],
        )


@pytest.mark.parametrize(
    "position",
    [0, 1, 2],
    ids=["suggested", "selected", "final"],
)
def test_non_object_input_is_rejected(
    valid_audit_objects: AuditObjects,
    position: int,
) -> None:
    arguments: list[object] = list(valid_audit_objects)
    arguments[position] = "not an object"

    with pytest.raises(TypeError, match="must be a dictionary"):
        analyze_objects(*arguments)


# ---------------------------------------------------------------------------
# Assisted end-to-end case
# ---------------------------------------------------------------------------


def test_edited_and_assisted_record_reports_expected_outcomes(
    valid_audit_objects: AuditObjects,
) -> None:
    """One record exercising several outcomes together."""
    suggested, selected, final = valid_audit_objects

    # Title edited after selection.
    final["title"] = "Revised Title suggestion"

    # Description differs only cosmetically.
    final["description"] = "description suggestion"

    # Topics offered, partially accepted, then altered.
    suggested["topics"] = [10, 20, 30]
    selected["topics"] = [10, 20]
    final["topics"] = [20, 30]

    # Compensation offered, selected, and saved unchanged.
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

    results = analyze_objects(suggested, selected, final)

    assert results["title"].match is MatchType.EDITED
    assert results["description"].match is MatchType.COSMETIC_EQUIVALENT
    assert results["purpose"].match is MatchType.EXACT

    topics = results["topics"]
    assert isinstance(topics, LookupValueAnalysis)
    assert topics.match is MatchType.EDITED
    assert topics.similarity == pytest.approx(1.0 / 3.0)
    assert topics.kept == frozenset({20})
    assert topics.dropped == frozenset({10})
    assert topics.added == frozenset({30})

    compensation = results["compensation"]
    assert isinstance(compensation, CompensationAnalysis)
    assert compensation.match is MatchType.EXACT
    assert compensation.flag_accepted is True
    assert compensation.compensation_text_required is True


def test_cosmetic_equivalence_receives_full_policy_credit(
    valid_audit_objects: AuditObjects,
) -> None:
    """Policy score is 1.0 for cosmetic differences, per specification §6."""
    suggested, selected, final = valid_audit_objects

    final["title"] = "title suggestion"

    results = analyze_objects(suggested, selected, final)
    title = results["title"]

    assert isinstance(title, TextFieldAnalysis)
    assert title.match is MatchType.COSMETIC_EQUIVALENT
    assert title.policy_adjusted_effort_saved == pytest.approx(1.0)
    assert title.editing_metrics is not None
    assert title.editing_metrics.character_edit_distance > 0
