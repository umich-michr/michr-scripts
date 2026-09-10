"""Exceptions raised by the study-posting audit-report program."""

type RecordId = str | int


class AuditReportError(Exception):
    """Base class for expected report-program failures."""


class AuditReportConfigurationError(AuditReportError):
    """Program configuration is missing, invalid, or inconsistent."""


class AuditSourceError(AuditReportError):
    """A configured row source could not be opened, read, or converted."""


class AuditRowError(AuditReportError):
    """One source audit row cannot be identified, mapped, or analyzed.

    Attributes
    ----------
    row_number
        One-based source-row number, when known.
    record_id
        Canonical audit-record identifier, when successfully extracted.
    """

    def __init__(
        self,
        message: str,
        *,
        row_number: int | None = None,
        record_id: RecordId | None = None,
    ) -> None:
        self.row_number = row_number
        self.record_id = record_id

        context_parts: list[str] = []

        if row_number is not None:
            context_parts.append(f"source row {row_number}")

        if record_id is not None:
            context_parts.append(f"record {record_id!r}")

        if context_parts:
            context = ", ".join(context_parts)
            super().__init__(f"{context}: {message}")
        else:
            super().__init__(message)


class AuditOutputError(AuditReportError):
    """Report output cannot be validated, serialized, or written."""
