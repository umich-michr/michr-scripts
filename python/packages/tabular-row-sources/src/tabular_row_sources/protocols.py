"""Structural interface for schema-aware lazy row sources.

A source owns its resources and exposes rows through a context manager. This
allows files, cursors, and database connections to close deterministically
after normal completion, early termination, or an exception.
"""

from collections.abc import Iterator
from contextlib import AbstractContextManager
from typing import Protocol, runtime_checkable

from tabular_row_sources.models import Row, RowSchema


@runtime_checkable
class RowSource(Protocol):
    """A schema-aware source that lazily yields canonical rows.

    Implementations may read CSV files, execute DB-API queries, or obtain rows
    from another tabular source.

    A new context manager must be returned by each ``open_rows()`` call.
    """

    @property
    def schema(self) -> RowSchema:
        """Return the canonical schema produced by this source."""
        ...

    def open_rows(
        self,
    ) -> AbstractContextManager[Iterator[Row]]:
        """Open the source and lazily yield canonical rows.

        Returns
        -------
        AbstractContextManager[Iterator[Row]]
            Context manager yielding an iterator of fresh row dictionaries.

        Raises
        ------
        RowSourceError
            If the source cannot be configured, opened, interpreted, converted,
            queried, fetched, or read.
        """
        ...
