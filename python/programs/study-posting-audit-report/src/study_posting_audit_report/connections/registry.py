"""Database-driver registry for the audit-report program."""

from study_posting_audit_report.connections.oracle import OracleDriver
from study_posting_audit_report.connections.protocols import DatabaseDriver
from study_posting_audit_report.errors import AuditReportConfigurationError

_DRIVERS: dict[str, DatabaseDriver] = {
    "oracle": OracleDriver(),
}


def available_database_drivers() -> tuple[str, ...]:
    """Return registered driver names in stable order."""
    return tuple(_DRIVERS)


def get_database_driver(name: object) -> DatabaseDriver:
    """Return the selected database driver.

    Driver names are stripped and matched case-insensitively.
    """
    if not isinstance(name, str) or not name.strip():
        raise AuditReportConfigurationError("database driver must be a nonblank string")

    normalized = name.strip().casefold()

    try:
        return _DRIVERS[normalized]
    except KeyError as error:
        supported = ", ".join(available_database_drivers())

        raise AuditReportConfigurationError(
            f"unsupported database driver {name!r}; supported drivers: {supported}"
        ) from error
