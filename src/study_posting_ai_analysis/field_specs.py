"""Form field configuration and requiredness rules.

Contains configuration data only; no calculations and no I/O.

Requiredness is enforced before any normalized post-editing metric is
calculated, because a blank required field is a validation error rather than a
metric of zero. See docs/analysis-specification.md section 4.
"""

from study_posting_ai_analysis.models import FieldKind, FieldSpec

# ---------------------------------------------------------------------------
# Compensation
# ---------------------------------------------------------------------------

#: Compensation text suggestion categories, in the order they are searched for
#: a selection. At most one suggestion may be selected across both.
COMPENSATION_KINDS: tuple[str, ...] = (
    "genericCompensation",
    "specificCompensation",
)

# ---------------------------------------------------------------------------
# Contact
# ---------------------------------------------------------------------------

#: Contact subfields, each analyzed and reported separately.
CONTACT_FIELDS: tuple[str, ...] = ("email", "name", "phone", "website")

#: Prefix applied to contact subfield names in reported results, producing
#: names such as "contact.email".
CONTACT_PREFIX = "contact"

#: Contact subfields whose final saved value must not be blank.
REQUIRED_CONTACT_FIELDS: frozenset[str] = frozenset({"email", "name"})

# ---------------------------------------------------------------------------
# Top-level fields
# ---------------------------------------------------------------------------

#: How each configured top-level field is analyzed.
#:
#: A field absent from this mapping is rejected during analysis, so a new form
#: field cannot be silently ignored.
#:
#: ``text_required`` applies only to ordinary TEXT fields. Compensation
#: requiredness is determined dynamically from the saved ``offersCompensation``
#: value, and contact requiredness is determined per subfield by
#: ``REQUIRED_CONTACT_FIELDS``.
FIELD_SPECS: dict[str, FieldSpec] = {
    "about": FieldSpec(
        kind=FieldKind.TEXT,
        text_required=False,
    ),
    "compensation": FieldSpec(
        kind=FieldKind.COMPENSATION,
        text_required=None,
    ),
    "contact": FieldSpec(
        kind=FieldKind.CONTACT,
        text_required=None,
    ),
    "department": FieldSpec(
        kind=FieldKind.LOOKUP,
    ),
    "description": FieldSpec(
        kind=FieldKind.TEXT,
        text_required=True,
    ),
    "locations": FieldSpec(
        kind=FieldKind.LOOKUP,
    ),
    "offersCompensation": FieldSpec(
        kind=FieldKind.MERGED,
    ),
    "purpose": FieldSpec(
        kind=FieldKind.TEXT,
        text_required=True,
    ),
    "title": FieldSpec(
        kind=FieldKind.TEXT,
        text_required=True,
    ),
    "topics": FieldSpec(
        kind=FieldKind.LOOKUP,
    ),
}
