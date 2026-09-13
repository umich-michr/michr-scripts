"""Loaded-input and validation-result models."""

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
