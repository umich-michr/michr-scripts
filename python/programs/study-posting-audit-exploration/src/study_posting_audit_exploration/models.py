"""Loaded-input, derived-data, and validation-result models."""

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True, slots=True)
class LoadedAuditReport:
    """Typed DataFrames loaded from one normalized report directory."""

    records: pd.DataFrame
    ai_assistance_metrics: pd.DataFrame
    readability_metrics: pd.DataFrame


@dataclass(frozen=True, slots=True)
class ValidationSummary:
    """Counts from a successfully validated normalized report."""

    record_attempt_count: int
    distinct_study_count: int
    completed_attempt_count: int
    incomplete_attempt_count: int
    ai_assistance_metric_row_count: int
    readability_metric_row_count: int


@dataclass(frozen=True, slots=True)
class DescriptiveStatistics:
    """One explicit descriptive summary for numeric observations."""

    nonmissing_count: int
    missing_count: int
    minimum: float | None
    percentile_25: float | None
    median: float | None
    average: float | None
    standard_deviation: float | None
    percentile_75: float | None
    percentile_90: float | None
    maximum: float | None


@dataclass(frozen=True, slots=True)
class AppointmentQualityFinding:
    """One malformed source appointment value."""

    audit_record_id: int
    appointment_source: str
    appointment_index: int
    issue_name: str


@dataclass(frozen=True, slots=True)
class AttemptHistoryTables:
    """Derived audit tables with explicit attempt, study, and author grains."""

    study_attempt_author_history: pd.DataFrame
    study_attempt_history: pd.DataFrame
    author_history: pd.DataFrame
