"""Oracle connection adapter for the audit-report program.

The adapter uses python-oracledb thin mode by default. It does not initialize
the Oracle Client libraries or require thick mode.

DSN interpretation belongs to python-oracledb. Callers may provide an Easy
Connect string or a TNS alias resolvable by their local Oracle configuration.
"""

from collections.abc import Callable

import oracledb

from study_posting_audit_report.connections.protocols import ConnectFactory
from study_posting_audit_report.errors import AuditReportConfigurationError


def _require_nonblank_connection_value(
    value: object,
    *,
    field_name: str,
) -> str:
    """Return one nonblank Oracle connection value."""
    if not isinstance(value, str) or not value.strip():
        raise AuditReportConfigurationError(f"{field_name} must be a nonblank string")

    return value


class OracleDriver:
    """Create python-oracledb thin-mode connection factories."""

    __slots__ = ()

    @property
    def name(self) -> str:
        """Return the stable command-line driver name."""
        return "oracle"

    def create_connect(
        self,
        *,
        dsn: str,
        username: str,
        password: str,
    ) -> ConnectFactory:
        """Return a deferred Oracle connection factory.

        The connection is not opened until the returned callable is invoked.
        Connection ownership then belongs to the consuming row source.
        """
        validated_dsn = _require_nonblank_connection_value(
            dsn,
            field_name="Oracle DSN",
        )
        validated_username = _require_nonblank_connection_value(
            username,
            field_name="Oracle username",
        )
        validated_password = _require_nonblank_connection_value(
            password,
            field_name="Oracle password",
        )

        def connect() -> object:
            """Open one python-oracledb thin-mode connection."""
            connector: Callable[..., object] = oracledb.connect

            return connector(
                user=validated_username,
                password=validated_password,
                dsn=validated_dsn,
            )

        return connect
