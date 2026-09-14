"""Derivation of reusable analytical attributes from validated source rows."""

from study_posting_audit_exploration.derivation.appointments import (
    derive_appointments,
)
from study_posting_audit_exploration.derivation.attempt_history import (
    derive_attempt_histories,
)
from study_posting_audit_exploration.derivation.edit_intensity import (
    EDIT_INTENSITY_THRESHOLD_SCHEME,
    classify_edit_intensity,
    derive_completed_ai_field_analysis,
)
from study_posting_audit_exploration.derivation.identity import (
    author_changed,
    same_author_within_study,
)
from study_posting_audit_exploration.derivation.readability_pairs import (
    derive_completed_ai_readability_pairs,
)
from study_posting_audit_exploration.derivation.roles import (
    derive_role_columns,
    effective_author_role,
)
from study_posting_audit_exploration.models import AppointmentQualityFinding

__all__ = [
    "EDIT_INTENSITY_THRESHOLD_SCHEME",
    "AppointmentQualityFinding",
    "author_changed",
    "classify_edit_intensity",
    "derive_appointments",
    "derive_attempt_histories",
    "derive_completed_ai_field_analysis",
    "derive_completed_ai_readability_pairs",
    "derive_role_columns",
    "effective_author_role",
    "same_author_within_study",
]
