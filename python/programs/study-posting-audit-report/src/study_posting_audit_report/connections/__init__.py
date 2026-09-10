"""Database connection adapters owned by the audit-report program."""

from study_posting_audit_report.connections.oracle import OracleDriver
from study_posting_audit_report.connections.protocols import (
    ConnectFactory,
    DatabaseDriver,
)
from study_posting_audit_report.connections.registry import (
    available_database_drivers,
    get_database_driver,
)

__all__ = [
    "ConnectFactory",
    "DatabaseDriver",
    "OracleDriver",
    "available_database_drivers",
    "get_database_driver",
]
