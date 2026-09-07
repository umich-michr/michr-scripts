"""Shared fixtures.

``valid_audit_objects`` returns a complete, valid baseline record. A test
modifies exactly one field to isolate the behavior under examination, which
mirrors the ``make_valid_objects`` helper from the original notebook suite.

All text is synthetic. Real study content must never appear in a fixture.
"""

import pytest


@pytest.fixture
def valid_audit_objects() -> tuple[
    dict[str, object],
    dict[str, object],
    dict[str, object],
]:
    """Return a valid suggested, selected, final triple.

    In the baseline, every text suggestion was offered, selected, and saved
    unchanged, so every text field is ``EXACT``. Contact values were written
    without assistance. Compensation is not offered.
    """
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
            # Required values written without AI assistance.
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
