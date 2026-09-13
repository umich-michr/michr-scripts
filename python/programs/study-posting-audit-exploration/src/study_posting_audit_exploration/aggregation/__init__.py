"""Faculty-facing aggregate tables for audit exploration."""

import pandas as pd

from study_posting_audit_exploration.aggregation.attempt_histories import (
    build_author_handoff_summary,
    build_study_attempt_history_summary,
)
from study_posting_audit_exploration.aggregation.attempts import (
    build_grouped_attempt_summary,
)
from study_posting_audit_exploration.aggregation.content_sources import (
    build_content_source_concordance_matrix,
    build_content_source_concordance_summary,
)
from study_posting_audit_exploration.aggregation.overview import (
    build_overview_summary,
)
from study_posting_audit_exploration.aggregation.studies import (
    build_grouped_study_summary,
)
from study_posting_audit_exploration.models import (
    AttemptAnalysisTables,
    OverviewTables,
    StudyAnalysisTables,
)


def build_overview_tables(
    *,
    attempts: pd.DataFrame,
    studies: pd.DataFrame,
    authors: pd.DataFrame,
) -> OverviewTables:
    """Build all overview aggregate tables."""
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


def build_attempt_analysis_tables(
    attempts: pd.DataFrame,
) -> AttemptAnalysisTables:
    """Build grouped attempt and content-source aggregate tables."""
    return AttemptAnalysisTables(
        grouped_attempt_summary=build_grouped_attempt_summary(attempts),
        content_source_concordance_summary=(
            build_content_source_concordance_summary(attempts)
        ),
        content_source_concordance_matrix=(
            build_content_source_concordance_matrix(attempts)
        ),
    )


def build_study_analysis_tables(
    studies: pd.DataFrame,
) -> StudyAnalysisTables:
    """Build grouped study aggregate tables."""
    return StudyAnalysisTables(
        grouped_study_summary=build_grouped_study_summary(studies),
    )


__all__ = [
    "AttemptAnalysisTables",
    "OverviewTables",
    "StudyAnalysisTables",
    "build_attempt_analysis_tables",
    "build_author_handoff_summary",
    "build_content_source_concordance_matrix",
    "build_content_source_concordance_summary",
    "build_grouped_attempt_summary",
    "build_grouped_study_summary",
    "build_overview_summary",
    "build_overview_tables",
    "build_study_analysis_tables",
    "build_study_attempt_history_summary",
]
