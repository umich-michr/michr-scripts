"""Tests for source-context aggregate summaries."""

import pandas as pd
import pytest

from study_posting_audit_exploration import (
    ExplorationValidationError,
    derive_source_context_tables,
)
from study_posting_audit_exploration.aggregation import (
    REPEATED_ATTEMPT_SOURCE_CONSISTENCY_COLUMNS,
    SOURCE_CONTEXT_DISTRIBUTION_COLUMNS,
    SOURCE_SIZE_LATENCY_COLUMNS,
    build_repeated_attempt_source_consistency_summary,
    build_source_context_distribution_summary,
    build_source_size_latency_summary,
)


def attempt_rows() -> pd.DataFrame:
    """Return synthetic successful-generation attempts."""
    rows: list[dict[str, object]] = [
        {
            "study_num": "S-1",
            "audit_record_id": 1,
            "attempt_start_timestamp": pd.Timestamp("2026-01-01T09:00:00"),
            "attempt_result": "USER_DROPPED",
            "attempt_completion_group": "INCOMPLETE",
            "is_completed_ai_attempt": False,
            "source_size_chars": 100,
            "latency_ms": 1_000,
            "source_type": "DOCX_FILE",
            "study_content_source": "Informed consent",
            "llm_inferred_study_content_source": " informed CONSENT ",
            "study_content_source_other_value": None,
            "llm_inferred_study_content_source_other_value": None,
        },
        {
            "study_num": "S-1",
            "audit_record_id": 2,
            "attempt_start_timestamp": pd.Timestamp("2026-01-01T10:00:00"),
            "attempt_result": "COMPLETE",
            "attempt_completion_group": "COMPLETE",
            "is_completed_ai_attempt": True,
            "source_size_chars": 200,
            "latency_ms": 2_000,
            "source_type": "DOCX_FILE",
            "study_content_source": "Other",
            "llm_inferred_study_content_source": "Other",
            "study_content_source_other_value": "Registry export",
            "llm_inferred_study_content_source_other_value": "registry EXPORT",
        },
        {
            "study_num": "S-2",
            "audit_record_id": 3,
            "attempt_start_timestamp": pd.Timestamp("2026-01-02T09:00:00"),
            "attempt_result": "COMPLETE",
            "attempt_completion_group": "COMPLETE",
            "is_completed_ai_attempt": True,
            "source_size_chars": 300,
            "latency_ms": 3_000,
            "source_type": "PDF_FILE",
            "study_content_source": "Study protocol",
            "llm_inferred_study_content_source": "Informed consent",
            "study_content_source_other_value": None,
            "llm_inferred_study_content_source_other_value": None,
        },
        {
            "study_num": "S-3",
            "audit_record_id": 4,
            "attempt_start_timestamp": pd.Timestamp("2026-01-03T09:00:00"),
            "attempt_result": "USER_DROPPED",
            "attempt_completion_group": "INCOMPLETE",
            "is_completed_ai_attempt": False,
            "source_size_chars": 400,
            "latency_ms": None,
            "source_type": None,
            "study_content_source": None,
            "llm_inferred_study_content_source": None,
            "study_content_source_other_value": None,
            "llm_inferred_study_content_source_other_value": None,
        },
    ]

    return pd.DataFrame.from_records(rows)


def record(
    *,
    audit_id: int,
    start: str,
    result: str,
    size: int | None,
    latency: int | None,
    source: str | None = "Informed consent",
    source_type: str | None = "DOCX_FILE",
) -> dict[str, object]:
    """Return one synthetic validated-style source record."""
    return {
        "ID": audit_id,
        "STUDY_NUM": "S-1",
        "START_TIME": pd.Timestamp(start),
        "ATTEMPT_TYPE": "AI",
        "ATTEMPT_RESULT": result,
        "SOURCE_SIZE_CHARS": size,
        "LATENCY_MS": latency,
        "SOURCE_TYPE": source_type,
        "STUDY_CONTENT_SOURCE": source,
        "LLM_INFERRED_STUDY_CONTENT_SOURCE": source,
        "STUDY_CONTENT_SOURCE_OTHER_VALUE": None,
        "LLM_INFERRED_STUDY_CONTENT_SOURCE_OTHER_VALUE": None,
    }


def test_distribution_summary_uses_explicit_populations_and_denominators() -> None:
    summary = build_source_context_distribution_summary(attempt_rows())

    assert tuple(summary.columns) == SOURCE_CONTEXT_DISTRIBUTION_COLUMNS
    all_row = summary.loc[
        summary["population_name"].eq("ALL_SUCCESSFUL_AI_GENERATIONS")
        & summary["summary_dimension_name"].eq("ALL")
    ].iloc[0]
    completed = summary.loc[
        summary["population_name"].eq("COMPLETED_AI_ATTEMPTS")
        & summary["summary_dimension_name"].eq("ALL")
    ].iloc[0]

    assert all_row["population_attempt_count"] == 4
    assert all_row["attempt_count_with_source_size"] == 4
    assert all_row["attempt_count_with_latency"] == 3
    assert all_row["attempt_count_missing_latency"] == 1
    assert all_row["median_source_size_chars"] == 250.0
    assert all_row["median_latency_ms"] == 2_000.0
    assert completed["population_attempt_count"] == 2
    assert completed["median_source_size_chars"] == 250.0


def test_distribution_summary_reports_categories_concordance_and_other_detail() -> None:
    summary = build_source_context_distribution_summary(attempt_rows())
    all_rows = summary.loc[
        summary["population_name"].eq("ALL_SUCCESSFUL_AI_GENERATIONS")
    ]
    docx = all_rows.loc[
        all_rows["summary_dimension_name"].eq("INPUT_METHOD")
        & all_rows["summary_dimension_value"].eq("docx_file")
    ].iloc[0]
    overall = all_rows.loc[all_rows["summary_dimension_name"].eq("ALL")].iloc[0]

    assert docx["eligible_attempt_count"] == 3
    assert docx["category_attempt_count"] == 2
    assert docx["category_attempt_percentage"] == pytest.approx(200 / 3)
    assert pd.isna(docx["comparable_content_source_attempt_count"])
    assert pd.isna(docx["other_category_attempt_count"])
    assert overall["comparable_content_source_attempt_count"] == 3
    assert overall["matching_content_source_attempt_count"] == 2
    assert overall["content_source_match_percentage"] == pytest.approx(200 / 3)
    assert overall["other_category_attempt_count"] == 1
    assert overall["other_category_attempt_count_with_nonblank_detail"] == 1
    assert overall["other_detail_completeness_percentage"] == 100.0
    assert overall["both_other_detail_attempt_count"] == 1
    assert overall["matching_other_detail_attempt_count"] == 1


def test_source_size_latency_uses_shared_quartile_edges() -> None:
    summary = build_source_size_latency_summary(attempt_rows())

    assert tuple(summary.columns) == SOURCE_SIZE_LATENCY_COLUMNS
    all_overall = summary.loc[
        summary["population_name"].eq("ALL_SUCCESSFUL_AI_GENERATIONS")
        & summary["reported_source_group"].eq("ALL")
    ]
    completed = summary.loc[summary["population_name"].eq("COMPLETED_AI_ATTEMPTS")]

    assert all_overall["source_size_band_name"].tolist() == [
        "Q1_OF_4",
        "Q2_OF_4",
        "Q3_OF_4",
        "Q4_OF_4",
    ]
    assert all_overall["source_size_band_q25_edge_chars"].unique().tolist() == [175.0]
    assert all_overall["source_size_band_q50_edge_chars"].unique().tolist() == [250.0]
    assert all_overall["source_size_band_q75_edge_chars"].unique().tolist() == [325.0]
    assert set(completed["source_size_band_q25_edge_chars"]) == {175.0}
    assert all_overall["band_attempt_count"].sum() == 4


def test_source_size_latency_collapses_duplicate_edges() -> None:
    attempts = attempt_rows()
    attempts["source_size_chars"] = 100

    summary = build_source_size_latency_summary(attempts)
    all_overall = summary.loc[
        summary["population_name"].eq("ALL_SUCCESSFUL_AI_GENERATIONS")
        & summary["reported_source_group"].eq("ALL")
    ]

    assert all_overall["source_size_band_name"].tolist() == ["Q1_OF_2"]
    assert all_overall["band_attempt_count"].tolist() == [4]


def test_negative_source_size_or_latency_is_rejected() -> None:
    attempts = attempt_rows()
    attempts.loc[0, "source_size_chars"] = -1

    with pytest.raises(
        ExplorationValidationError,
        match="negative values",
    ):
        build_source_context_distribution_summary(attempts)


def test_empty_source_size_population_has_stable_columns() -> None:
    attempts = attempt_rows()
    attempts["source_size_chars"] = None

    summary = build_source_size_latency_summary(attempts)

    assert summary.empty
    assert tuple(summary.columns) == SOURCE_SIZE_LATENCY_COLUMNS


def test_repeated_summary_keeps_study_and_transition_grains_separate() -> None:
    records = pd.DataFrame.from_records(
        [
            record(
                audit_id=1,
                start="2026-01-01T09:00:00",
                result="USER_DROPPED",
                size=100,
                latency=1_000,
            ),
            record(
                audit_id=2,
                start="2026-01-01T10:00:00",
                result="USER_DROPPED",
                size=150,
                latency=900,
            ),
            record(
                audit_id=3,
                start="2026-01-01T11:00:00",
                result="COMPLETE",
                size=150,
                latency=1_100,
            ),
        ]
    )
    source_context = derive_source_context_tables(records)
    summary = build_repeated_attempt_source_consistency_summary(source_context)

    assert tuple(summary.columns) == (REPEATED_ATTEMPT_SOURCE_CONSISTENCY_COLUMNS)
    study_size_changed = summary.loc[
        summary["summary_grain"].eq("COMPLETED_AI_STUDY")
        & summary["comparison_dimension_name"].eq("SOURCE_SIZE")
        & summary["comparison_category"].eq("CHANGED")
    ].iloc[0]
    transition_size_changed = summary.loc[
        summary["summary_grain"].eq("ALL_CONSECUTIVE_SUCCESSFUL_AI_TRANSITION")
        & summary["comparison_dimension_name"].eq("SOURCE_SIZE")
        & summary["comparison_category"].eq("CHANGED")
    ].iloc[0]
    transition_size_same = summary.loc[
        summary["summary_grain"].eq("ALL_CONSECUTIVE_SUCCESSFUL_AI_TRANSITION")
        & summary["comparison_dimension_name"].eq("SOURCE_SIZE")
        & summary["comparison_category"].eq("SAME")
    ].iloc[0]

    assert study_size_changed["eligible_unit_count"] == 1
    assert study_size_changed["category_unit_count"] == 1
    assert transition_size_changed["eligible_unit_count"] == 2
    assert transition_size_changed["category_unit_count"] == 1
    assert transition_size_same["category_unit_count"] == 1
    assert transition_size_changed["median_latency_change_ms"] == -100.0
    assert transition_size_same["median_latency_change_ms"] == 200.0


def test_repeated_summary_first_and_preceding_comparisons_differ() -> None:
    records = pd.DataFrame.from_records(
        [
            record(
                audit_id=1,
                start="2026-01-01T09:00:00",
                result="USER_DROPPED",
                size=100,
                latency=1_000,
            ),
            record(
                audit_id=2,
                start="2026-01-01T10:00:00",
                result="USER_DROPPED",
                size=200,
                latency=1_500,
            ),
            record(
                audit_id=3,
                start="2026-01-01T11:00:00",
                result="COMPLETE",
                size=200,
                latency=1_500,
            ),
        ]
    )
    summary = build_repeated_attempt_source_consistency_summary(
        derive_source_context_tables(records)
    )

    first_changed = summary.loc[
        summary["summary_grain"].eq("FIRST_SUCCESSFUL_AI_TO_COMPLETION")
        & summary["comparison_dimension_name"].eq("SOURCE_SIZE")
        & summary["comparison_category"].eq("CHANGED")
    ].iloc[0]
    preceding_same = summary.loc[
        summary["summary_grain"].eq("PRECEDING_SUCCESSFUL_AI_TO_COMPLETION")
        & summary["comparison_dimension_name"].eq("SOURCE_SIZE")
        & summary["comparison_category"].eq("SAME")
    ].iloc[0]

    assert first_changed["category_unit_count"] == 1
    assert first_changed["median_latency_change_ms"] == 500.0
    assert preceding_same["category_unit_count"] == 1
    assert preceding_same["median_latency_change_ms"] == 0.0


def test_completion_pathway_excludes_successful_attempts_after_completion() -> None:
    records = pd.DataFrame.from_records(
        [
            record(
                audit_id=1,
                start="2026-01-01T09:00:00",
                result="USER_DROPPED",
                size=100,
                latency=1_000,
            ),
            record(
                audit_id=2,
                start="2026-01-01T10:00:00",
                result="COMPLETE",
                size=200,
                latency=2_000,
            ),
            record(
                audit_id=3,
                start="2026-01-01T11:00:00",
                result="USER_DROPPED",
                size=300,
                latency=3_000,
            ),
        ]
    )

    pathway = derive_source_context_tables(records).completed_ai_source_pathways.iloc[0]

    assert pathway["successful_ai_generation_attempt_count"] == 2
    assert pathway["preceding_successful_ai_attempt_count"] == 1
    assert pathway["comparable_successful_ai_transition_count"] == 1
    assert pathway["source_size_change_count"] == 1


def test_repeated_summary_separates_all_and_completed_path_transitions() -> None:
    records = pd.DataFrame.from_records(
        [
            record(
                audit_id=1,
                start="2026-01-01T09:00:00",
                result="USER_DROPPED",
                size=100,
                latency=1_000,
            ),
            record(
                audit_id=2,
                start="2026-01-01T10:00:00",
                result="COMPLETE",
                size=200,
                latency=2_000,
            ),
            record(
                audit_id=3,
                start="2026-01-01T11:00:00",
                result="USER_DROPPED",
                size=300,
                latency=3_000,
            ),
        ]
    )
    source_context = derive_source_context_tables(records)
    pathway = source_context.completed_ai_source_pathways.iloc[0]

    assert pathway["successful_ai_generation_attempt_count"] == 2
    assert pathway["comparable_successful_ai_transition_count"] == 1

    summary = build_repeated_attempt_source_consistency_summary(source_context)
    all_changed = summary.loc[
        summary["summary_grain"].eq("ALL_CONSECUTIVE_SUCCESSFUL_AI_TRANSITION")
        & summary["comparison_dimension_name"].eq("SOURCE_SIZE")
        & summary["comparison_category"].eq("CHANGED")
    ].iloc[0]
    completed_changed = summary.loc[
        summary["summary_grain"].eq(
            "COMPLETED_AI_PATH_CONSECUTIVE_SUCCESSFUL_AI_TRANSITION"
        )
        & summary["comparison_dimension_name"].eq("SOURCE_SIZE")
        & summary["comparison_category"].eq("CHANGED")
    ].iloc[0]

    assert all_changed["eligible_unit_count"] == 2
    assert all_changed["category_unit_count"] == 2
    assert completed_changed["eligible_unit_count"] == 1
    assert completed_changed["category_unit_count"] == 1


def test_missing_comparisons_use_missing_units_as_denominator() -> None:
    records = pd.DataFrame.from_records(
        [
            record(
                audit_id=1,
                start="2026-01-01T09:00:00",
                result="USER_DROPPED",
                size=None,
                latency=1_000,
            ),
            record(
                audit_id=2,
                start="2026-01-01T10:00:00",
                result="COMPLETE",
                size=200,
                latency=2_000,
            ),
        ]
    )
    summary = build_repeated_attempt_source_consistency_summary(
        derive_source_context_tables(records)
    )
    missing = summary.loc[
        summary["summary_grain"].eq("ALL_CONSECUTIVE_SUCCESSFUL_AI_TRANSITION")
        & summary["comparison_dimension_name"].eq("SOURCE_SIZE")
        & summary["comparison_category"].eq("MISSING")
    ].iloc[0]

    assert missing["population_unit_count"] == 1
    assert missing["eligible_unit_count"] == 1
    assert missing["category_unit_count"] == 1
    assert missing["category_unit_percentage"] == 100.0
