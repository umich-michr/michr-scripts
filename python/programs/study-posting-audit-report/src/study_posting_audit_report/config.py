"""Configuration models for audit-row mapping and report behavior.

The report program owns knowledge of source-column names. Analysis libraries
remain independent of database schemas and source mappings.

A row is analyzed when all three configured analysis payloads are present. A row
is skipped when all three payloads are null. Partial payload presence is treated
as an inconsistent source row and raises ``AuditRowError``.
"""

from dataclasses import dataclass

from study_posting_audit_report.errors import (
    AuditReportConfigurationError,
)


def _require_nonblank_name(
    value: object,
    *,
    field_name: str,
) -> str:
    """Return a nonblank source-column name."""
    if not isinstance(value, str) or not value.strip():
        raise AuditReportConfigurationError(f"{field_name} must be a nonblank string")

    return value


@dataclass(frozen=True, slots=True)
class AuditColumnMapping:
    """Map source columns to record identity and analysis inputs.

    Attributes
    ----------
    record_id
        Source column containing the unique audit-record identifier.
    llm_suggestions
        Source column containing the suggestions object.
    selected_suggestions
        Source column containing the selections object.
    final_submission
        Source column containing the final saved object.
    """

    record_id: str = "ID"
    llm_suggestions: str = "LLM_SUGGESTIONS"
    selected_suggestions: str = "SELECTED_SUGGESTIONS"
    final_submission: str = "FINAL_SUBMISSION"

    def __post_init__(self) -> None:
        """Validate names and reject ambiguous mappings."""
        names = (
            _require_nonblank_name(
                self.record_id,
                field_name="record_id",
            ),
            _require_nonblank_name(
                self.llm_suggestions,
                field_name="llm_suggestions",
            ),
            _require_nonblank_name(
                self.selected_suggestions,
                field_name="selected_suggestions",
            ),
            _require_nonblank_name(
                self.final_submission,
                field_name="final_submission",
            ),
        )

        if len(names) != len(set(names)):
            raise AuditReportConfigurationError(
                "Audit column mappings must use unique source-column names"
            )

    @property
    def required_columns(self) -> tuple[str, ...]:
        """Return columns required to identify and analyze source rows."""
        return (
            self.record_id,
            self.llm_suggestions,
            self.selected_suggestions,
            self.final_submission,
        )

    @property
    def payload_columns(self) -> tuple[str, str, str]:
        """Return the three analysis-payload columns in canonical order."""
        return (
            self.llm_suggestions,
            self.selected_suggestions,
            self.final_submission,
        )


@dataclass(frozen=True, slots=True)
class AuditReportConfig:
    """Core behavior configuration for one report run.

    Attributes
    ----------
    columns
        Source-column mapping.
    include_text
        Whether flattened field metrics include selected and final free text.
        Defaults to ``False``.
    """

    columns: AuditColumnMapping = AuditColumnMapping()
    include_text: bool = False

    def __post_init__(self) -> None:
        """Validate nested configuration and privacy-sensitive flags."""
        if not isinstance(self.columns, AuditColumnMapping):
            raise AuditReportConfigurationError("columns must be an AuditColumnMapping")

        if type(self.include_text) is not bool:
            raise AuditReportConfigurationError("include_text must be a Boolean")
