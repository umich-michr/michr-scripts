"""Tests for successful-generation source-context derivation."""

import pandas as pd

from study_posting_audit_exploration import derive_source_context_tables


def source_record(  # noqa: PLR0913
    *,
    audit_id: int,
    study_num: str,
    start_time: str,
    attempt_type: str = "AI",
    attempt_result: str = "USER_DROPPED",
    source_size: int | None = 100,
    latency: int | None = 500,
    source_type: str | None = "DOCX_FILE",
    reported_source: str | None = "Informed consent",
    inferred_source: str | None = "Informed consent",
) -> dict[str, object]:
    """Return one minimal validated-style source-context record."""
    return {
        "ID": audit_id,
        "STUDY_NUM": study_num,
        "START_TIME": pd.Timestamp(start_time),
        "ATTEMPT_TYPE": attempt_type,
        "ATTEMPT_RESULT": attempt_result,
        "SOURCE_SIZE_CHARS": source_size,
        "LATENCY_MS": latency,
        "SOURCE_TYPE": source_type,
        "STUDY_CONTENT_SOURCE": reported_source,
        "LLM_INFERRED_STUDY_CONTENT_SOURCE": inferred_source,
        "STUDY_CONTENT_SOURCE_OTHER_VALUE": None,
        "LLM_INFERRED_STUDY_CONTENT_SOURCE_OTHER_VALUE": None,
    }


def test_successful_generation_population_includes_dropped_and_complete() -> None:
    records = pd.DataFrame.from_records(
        [
            source_record(
                audit_id=1,
                study_num="STUDY-1",
                start_time="2026-01-01T09:00:00",
            ),
            source_record(
                audit_id=2,
                study_num="STUDY-1",
                start_time="2026-01-01T10:00:00",
                attempt_result="COMPLETE",
            ),
            source_record(
                audit_id=3,
                study_num="STUDY-2",
                start_time="2026-01-02T09:00:00",
                attempt_result="AI_ERROR",
            ),
            source_record(
                audit_id=4,
                study_num="STUDY-3",
                start_time="2026-01-03T09:00:00",
                attempt_type="MANUAL",
            ),
        ]
    )

    tables = derive_source_context_tables(records)
    attempts = tables.successful_ai_generations

    assert attempts["audit_record_id"].tolist() == [1, 2]
    assert attempts["attempt_completion_group"].tolist() == [
        "INCOMPLETE",
        "COMPLETE",
    ]


def test_transitions_classify_source_and_latency_changes() -> None:
    records = pd.DataFrame.from_records(
        [
            source_record(
                audit_id=1,
                study_num="STUDY-1",
                start_time="2026-01-01T09:00:00",
                source_size=100,
                latency=500,
            ),
            source_record(
                audit_id=2,
                study_num="STUDY-1",
                start_time="2026-01-01T10:00:00",
                source_size=100,
                latency=600,
            ),
            source_record(
                audit_id=3,
                study_num="STUDY-1",
                start_time="2026-01-01T11:00:00",
                source_size=150,
                latency=550,
            ),
            source_record(
                audit_id=4,
                study_num="STUDY-1",
                start_time="2026-01-01T12:00:00",
                attempt_result="COMPLETE",
                source_size=200,
                latency=800,
                source_type="PDF_FILE",
                reported_source="Study protocol",
                inferred_source="Study protocol",
            ),
        ]
    )

    transitions = derive_source_context_tables(records).successful_ai_transitions

    assert transitions["source_change_category"].tolist() == [
        "SAME_SOURCE_SIGNATURE",
        "SIZE_CHANGED_ONLY",
        "SIZE_AND_REPORTED_SOURCE_CHANGED",
    ]
    assert transitions["input_method_change_category"].tolist() == [
        "SAME",
        "SAME",
        "CHANGED",
    ]
    assert transitions["latency_change_ms"].tolist() == [
        100,
        -50,
        250,
    ]
    assert transitions["source_size_change_chars"].tolist() == [
        0,
        50,
        50,
    ]


def test_completed_pathway_reports_study_and_transition_counts() -> None:
    records = pd.DataFrame.from_records(
        [
            source_record(
                audit_id=1,
                study_num="STUDY-1",
                start_time="2026-01-01T09:00:00",
                source_size=100,
                latency=500,
            ),
            source_record(
                audit_id=2,
                study_num="STUDY-1",
                start_time="2026-01-01T10:00:00",
                source_size=150,
                latency=600,
            ),
            source_record(
                audit_id=3,
                study_num="STUDY-1",
                start_time="2026-01-01T11:00:00",
                attempt_result="COMPLETE",
                source_size=150,
                latency=700,
            ),
        ]
    )

    pathway = derive_source_context_tables(records).completed_ai_source_pathways.iloc[0]

    assert pathway["preceding_attempt_count"] == 2
    assert pathway["preceding_successful_ai_attempt_count"] == 2
    assert pathway["successful_ai_generation_attempt_count"] == 3
    assert pathway["comparable_successful_ai_transition_count"] == 2
    assert pathway["source_size_change_count"] == 1
    assert pathway["reported_source_change_count"] == 0
    assert pathway["source_signature_change_count"] == 1
    assert bool(pathway["any_source_signature_change"]) is True
    assert pathway["first_to_completion_source_size_comparison"] == "CHANGED"
    assert pathway["first_to_completion_latency_change_ms"] == 200
    assert pathway["preceding_to_completion_source_size_comparison"] == "SAME"
    assert pathway["preceding_to_completion_latency_change_ms"] == 100


def test_completed_pathway_counts_manual_and_failed_preceding_attempts() -> None:
    records = pd.DataFrame.from_records(
        [
            source_record(
                audit_id=1,
                study_num="STUDY-1",
                start_time="2026-01-01T09:00:00",
                attempt_type="MANUAL",
            ),
            source_record(
                audit_id=2,
                study_num="STUDY-1",
                start_time="2026-01-01T10:00:00",
                attempt_result="AI_ERROR",
            ),
            source_record(
                audit_id=3,
                study_num="STUDY-1",
                start_time="2026-01-01T11:00:00",
                attempt_result="COMPLETE",
            ),
        ]
    )

    pathway = derive_source_context_tables(records).completed_ai_source_pathways.iloc[0]

    assert pathway["preceding_attempt_count"] == 2
    assert pathway["preceding_successful_ai_attempt_count"] == 0
    assert pathway["comparable_successful_ai_transition_count"] == 0
    assert pathway["first_to_completion_source_signature_comparison"] == ("MISSING")
    assert pathway["preceding_to_completion_source_signature_comparison"] == ("MISSING")


def test_ordering_uses_audit_id_as_tie_breaker() -> None:
    records = pd.DataFrame.from_records(
        [
            source_record(
                audit_id=2,
                study_num="STUDY-1",
                start_time="2026-01-01T09:00:00",
                attempt_result="COMPLETE",
                source_size=200,
            ),
            source_record(
                audit_id=1,
                study_num="STUDY-1",
                start_time="2026-01-01T09:00:00",
                source_size=100,
            ),
        ]
    )

    tables = derive_source_context_tables(records)

    assert tables.successful_ai_generations["audit_record_id"].tolist() == [
        1,
        2,
    ]
    assert tables.successful_ai_transitions["previous_audit_record_id"].tolist() == [1]
    assert tables.successful_ai_transitions["current_audit_record_id"].tolist() == [2]


def test_relative_size_change_missing_for_zero_previous_size() -> None:
    records = pd.DataFrame.from_records(
        [
            source_record(
                audit_id=1,
                study_num="STUDY-1",
                start_time="2026-01-01T09:00:00",
                source_size=0,
            ),
            source_record(
                audit_id=2,
                study_num="STUDY-1",
                start_time="2026-01-01T10:00:00",
                attempt_result="COMPLETE",
                source_size=10,
            ),
        ]
    )

    transition = derive_source_context_tables(records).successful_ai_transitions.iloc[0]

    assert transition["source_size_change_chars"] == 10
    assert pd.isna(transition["relative_source_size_change"])


def test_empty_successful_population_has_stable_columns() -> None:
    records = pd.DataFrame.from_records(
        [
            source_record(
                audit_id=1,
                study_num="STUDY-1",
                start_time="2026-01-01T09:00:00",
                attempt_type="MANUAL",
            ),
            source_record(
                audit_id=2,
                study_num="STUDY-2",
                start_time="2026-01-02T09:00:00",
                attempt_result="AI_ERROR",
            ),
        ]
    )

    tables = derive_source_context_tables(records)

    assert tables.successful_ai_generations.empty
    assert tables.successful_ai_transitions.empty
    assert tables.completed_ai_source_pathways.empty


def test_completed_pathway_stops_at_completion() -> None:
    records = pd.DataFrame.from_records(
        [
            source_record(
                audit_id=1,
                study_num="STUDY-1",
                start_time="2026-01-01T09:00:00",
                source_size=100,
            ),
            source_record(
                audit_id=2,
                study_num="STUDY-1",
                start_time="2026-01-01T10:00:00",
                attempt_result="COMPLETE",
                source_size=200,
            ),
            source_record(
                audit_id=3,
                study_num="STUDY-1",
                start_time="2026-01-01T11:00:00",
                source_size=300,
            ),
        ]
    )

    pathway = derive_source_context_tables(records).completed_ai_source_pathways.iloc[0]

    assert pathway["successful_ai_generation_attempt_count"] == 2
    assert pathway["comparable_successful_ai_transition_count"] == 1
    assert pathway["completed_source_size_chars"] == 200
