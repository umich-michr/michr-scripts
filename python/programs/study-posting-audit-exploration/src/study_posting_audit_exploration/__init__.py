"""Exploratory analysis of normalized study-posting audit reports."""

from study_posting_audit_exploration.config import ExplorationInputConfig
from study_posting_audit_exploration.derivation import (
    AppointmentQualityFinding,
    author_changed,
    derive_appointments,
    derive_role_columns,
    effective_author_role,
    same_author_within_study,
)
from study_posting_audit_exploration.errors import (
    AuditExplorationError,
    ExplorationConfigurationError,
    ExplorationInputError,
    ExplorationValidationError,
)
from study_posting_audit_exploration.loading import load_audit_report
from study_posting_audit_exploration.models import (
    DescriptiveStatistics,
    LoadedAuditReport,
    ValidationSummary,
)
from study_posting_audit_exploration.statistics import describe_numeric
from study_posting_audit_exploration.validation import validate_audit_report

__version__ = "0.1.0"

__all__ = [
    "AppointmentQualityFinding",
    "AuditExplorationError",
    "DescriptiveStatistics",
    "ExplorationConfigurationError",
    "ExplorationInputConfig",
    "ExplorationInputError",
    "ExplorationValidationError",
    "LoadedAuditReport",
    "ValidationSummary",
    "__version__",
    "author_changed",
    "derive_appointments",
    "derive_role_columns",
    "describe_numeric",
    "effective_author_role",
    "load_audit_report",
    "same_author_within_study",
    "validate_audit_report",
]
