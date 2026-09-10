"""Structural contracts for report-program database drivers."""

from collections.abc import Callable
from typing import Protocol, runtime_checkable

#: Zero-argument factory returning a new DB-API-compatible connection.
type ConnectFactory = Callable[[], object]


@runtime_checkable
class DatabaseDriver(Protocol):
    """Adapter that creates a connection factory for one database driver."""

    @property
    def name(self) -> str:
        """Return the stable command-line driver name."""
        ...

    def create_connect(
        self,
        *,
        dsn: str,
        username: str,
        password: str,
    ) -> ConnectFactory:
        """Return a zero-argument connection factory."""
        ...
