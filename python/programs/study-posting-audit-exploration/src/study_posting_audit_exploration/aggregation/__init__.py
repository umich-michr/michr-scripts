"""Faculty-facing aggregate tables for audit exploration."""

import pandas as pd

from study_posting_audit_exploration.aggregation.attempt_histories import (
    build_author_handoff_summary,
    build_study_attempt_history_summary,
)
from study_posting_audit_exploration.aggregation.overview import (
    build_overview_summary,
)
from study_posting_audit_exploration.models import OverviewTables


def build_overview_tables(
    *,
    attempts: pd.DataFrame,
    studies: pd.DataFrame,
    authors: pd.DataFrame,
) -> OverviewTables:
    """Build all Batch 4A aggregate tables."""
    return OverviewTables(
        overview_summary=build_overview_summary(
            attempts=attempts,
            studies=studies,
            authors=authors,
        ),
        study_attempt_history_summary=build_study_attempt_history_summary(studies),
        author_handoff_summary=build_author_handoff_summary(
            attempts=attempts,
            studies=studies,
        ),
    )


__all__ = [
    "OverviewTables",
    "build_author_handoff_summary",
    "build_overview_summary",
    "build_overview_tables",
    "build_study_attempt_history_summary",
]
