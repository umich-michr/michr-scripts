from pathlib import Path

import pandas as pd
import pytest

from study_posting_audit_exploration import (
    ExplorationInputConfig,
    ExplorationValidationError,
    LoadedAuditReport,
    load_audit_report,
    validate_audit_report,
)


def load_valid(path: Path) -> LoadedAuditReport:
    return load_audit_report(
        ExplorationInputConfig(
            report_directory=path,
        )
    )


def report_with_ai_metrics(
    report: LoadedAuditReport,
    metrics: pd.DataFrame,
) -> LoadedAuditReport:
    """Return a report with replacement AI-assistance metrics."""
    return LoadedAuditReport(
        records=report.records,
        ai_assistance_metrics=metrics,
        readability_metrics=report.readability_metrics,
    )


def test_valid_report_returns_counts(
    valid_report_directory: Path,
) -> None:
    summary = validate_audit_report(load_valid(valid_report_directory))

    assert summary.record_attempt_count == 2
    assert summary.distinct_study_count == 1
    assert summary.completed_attempt_count == 1
    assert summary.incomplete_attempt_count == 1
    assert summary.ai_assistance_metric_row_count == 1
    assert summary.readability_metric_row_count == 2


def test_duplicate_audit_ids_are_rejected(
    valid_report_directory: Path,
) -> None:
    report = load_valid(valid_report_directory)
    report.records.loc[1, "ID"] = report.records.loc[0, "ID"]

    with pytest.raises(
        ExplorationValidationError,
        match="duplicate audit IDs",
    ):
        validate_audit_report(report)


@pytest.mark.parametrize(
    ("column_name", "message"),
    [
        ("STUDY_NUM", "missing study numbers"),
        ("AUTHOR_USER_NAME", "missing author usernames"),
    ],
)
def test_required_identity_is_rejected(
    valid_report_directory: Path,
    column_name: str,
    message: str,
) -> None:
    report = load_valid(valid_report_directory)
    report.records.loc[0, column_name] = pd.NA

    with pytest.raises(
        ExplorationValidationError,
        match=message,
    ):
        validate_audit_report(report)


def test_multiple_completed_attempts_for_study_are_rejected(
    valid_report_directory: Path,
) -> None:
    report = load_valid(valid_report_directory)
    report.records.loc[0, "ATTEMPT_RESULT"] = "COMPLETE"
    report.records.loc[0, "END_TIME"] = pd.Timestamp("2026-06-01T09:01:00")

    with pytest.raises(
        ExplorationValidationError,
        match="multiple completed attempts",
    ):
        validate_audit_report(report)


@pytest.mark.parametrize(
    ("column_name", "message"),
    [
        ("END_TIME", "missing completion time"),
        ("CREATED_BY_ID", "missing created-by ID"),
        ("CREATED_DATE", "missing created date"),
        ("STUDY_DEPARTMENT", "missing study department"),
    ],
)
def test_completed_attempt_requires_creation_values(
    valid_report_directory: Path,
    column_name: str,
    message: str,
) -> None:
    report = load_valid(valid_report_directory)
    complete_index = report.records["ATTEMPT_RESULT"].eq("COMPLETE")
    report.records.loc[complete_index, column_name] = pd.NA

    with pytest.raises(
        ExplorationValidationError,
        match=message,
    ):
        validate_audit_report(report)


def test_completed_attempt_user_must_match_creator(
    valid_report_directory: Path,
) -> None:
    report = load_valid(valid_report_directory)
    complete_index = report.records["ATTEMPT_RESULT"].eq("COMPLETE")
    report.records.loc[complete_index, "USER_ID"] = 999

    with pytest.raises(
        ExplorationValidationError,
        match="USER_ID and CREATED_BY_ID mismatches",
    ):
        validate_audit_report(report)


@pytest.mark.parametrize(
    "metric_name",
    [
        "ai_assistance_metrics",
        "readability_metrics",
    ],
)
def test_metric_audit_ids_must_join_to_records(
    valid_report_directory: Path,
    metric_name: str,
) -> None:
    report = load_valid(valid_report_directory)
    metrics = getattr(report, metric_name)
    metrics.loc[0, "record_id"] = 9999

    with pytest.raises(
        ExplorationValidationError,
        match=r"audit IDs absent from records\.csv",
    ):
        validate_audit_report(report)


def test_nonfinite_metric_is_rejected(
    valid_report_directory: Path,
) -> None:
    report = load_valid(valid_report_directory)
    report.readability_metrics.loc[0, "flesch_kincaid_grade"] = float("inf")

    with pytest.raises(
        ExplorationValidationError,
        match="contains non-finite values",
    ):
        validate_audit_report(report)


def test_ai_assistance_field_name_is_required(
    valid_report_directory: Path,
) -> None:
    report = load_valid(valid_report_directory)
    report.ai_assistance_metrics.loc[0, "field_name"] = pd.NA

    with pytest.raises(
        ExplorationValidationError,
        match="missing field names",
    ):
        validate_audit_report(report)


def test_duplicate_ai_assistance_identity_is_rejected(
    valid_report_directory: Path,
) -> None:
    report = load_valid(valid_report_directory)
    duplicate = report.ai_assistance_metrics.iloc[[0]].copy()
    metrics = pd.concat(
        [
            report.ai_assistance_metrics,
            duplicate,
        ],
        ignore_index=True,
    )

    with pytest.raises(
        ExplorationValidationError,
        match="duplicate audit-field identities",
    ):
        validate_audit_report(report_with_ai_metrics(report, metrics))


@pytest.mark.parametrize(
    ("column_name", "value"),
    [
        ("analysis_type", "SYNTHETIC_UNKNOWN"),
        ("match_type", "SYNTHETIC_UNKNOWN"),
    ],
)
def test_ai_assistance_vocabularies_are_validated(
    valid_report_directory: Path,
    column_name: str,
    value: str,
) -> None:
    report = load_valid(valid_report_directory)
    report.ai_assistance_metrics.loc[0, column_name] = value

    with pytest.raises(
        ExplorationValidationError,
        match=rf"unsupported {column_name} values",
    ):
        validate_audit_report(report)


@pytest.mark.parametrize(
    "column_name",
    [
        "flag_suggested",
        "flag_saved",
        "flag_accepted",
        "flag_changed",
        "compensation_text_required",
    ],
)
def test_ai_assistance_boolean_text_is_validated(
    valid_report_directory: Path,
    column_name: str,
) -> None:
    report = load_valid(valid_report_directory)
    report.ai_assistance_metrics.loc[0, column_name] = "SYNTHETIC_UNKNOWN"

    with pytest.raises(
        ExplorationValidationError,
        match=rf"{column_name!r} must contain true, false, or null",
    ):
        validate_audit_report(report)


@pytest.mark.parametrize(
    "column_name",
    [
        "picked_kind",
        "picked_index",
    ],
)
def test_assisted_text_requires_pick_identity(
    valid_report_directory: Path,
    column_name: str,
) -> None:
    report = load_valid(valid_report_directory)
    report.ai_assistance_metrics.loc[0, column_name] = pd.NA

    with pytest.raises(
        ExplorationValidationError,
        match="assisted text AI metrics require picked_kind and picked_index",
    ):
        validate_audit_report(report)


def test_unassisted_text_must_not_contain_pick(
    valid_report_directory: Path,
) -> None:
    report = load_valid(valid_report_directory)
    report.ai_assistance_metrics.loc[0, "match_type"] = "UNASSISTED"

    with pytest.raises(
        ExplorationValidationError,
        match="unassisted text AI metrics must not contain a picked suggestion",
    ):
        validate_audit_report(report)


def test_negative_picked_index_is_rejected(
    valid_report_directory: Path,
) -> None:
    report = load_valid(valid_report_directory)
    report.ai_assistance_metrics.loc[0, "picked_index"] = -1

    with pytest.raises(
        ExplorationValidationError,
        match="negative picked indices",
    ):
        validate_audit_report(report)


def test_lookup_row_must_not_contain_text_pick(
    valid_report_directory: Path,
) -> None:
    report = load_valid(valid_report_directory)
    report.ai_assistance_metrics.loc[0, "analysis_type"] = "LOOKUP"

    with pytest.raises(
        ExplorationValidationError,
        match="lookup AI metrics must not contain text suggestion picks",
    ):
        validate_audit_report(report)


@pytest.mark.parametrize(
    ("record_index", "attempt_type", "attempt_result"),
    [
        (0, "AI", "USER_DROPPED"),
        (1, "MANUAL", "COMPLETE"),
    ],
)
def test_ai_assistance_rows_require_completed_ai_attempts(
    valid_report_directory: Path,
    record_index: int,
    attempt_type: str,
    attempt_result: str,
) -> None:
    report = load_valid(valid_report_directory)
    audit_id = report.records["ID"].astype("int64").iloc[record_index]
    report.ai_assistance_metrics.loc[0, "record_id"] = audit_id
    report.records.loc[record_index, "ATTEMPT_TYPE"] = attempt_type
    report.records.loc[record_index, "ATTEMPT_RESULT"] = attempt_result

    with pytest.raises(
        ExplorationValidationError,
        match="must belong to completed AI attempts",
    ):
        validate_audit_report(report)


def test_readability_suggestion_requires_selected_marker(
    valid_report_directory: Path,
) -> None:
    report = load_valid(valid_report_directory)
    suggested = report.readability_metrics["text_role"].eq("SUGGESTED")
    report.readability_metrics.loc[suggested, "selected"] = pd.NA

    with pytest.raises(
        ExplorationValidationError,
        match="suggestion rows require selected markers",
    ):
        validate_audit_report(report)


def test_readability_final_must_not_have_selected_marker(
    valid_report_directory: Path,
) -> None:
    report = load_valid(valid_report_directory)
    final = report.readability_metrics["text_role"].eq("FINAL")
    report.readability_metrics.loc[final, "selected"] = "false"

    with pytest.raises(
        ExplorationValidationError,
        match="final rows must not contain selected markers",
    ):
        validate_audit_report(report)


def test_null_audit_id_is_rejected(
    valid_report_directory: Path,
) -> None:
    report = load_valid(valid_report_directory)
    report.records.loc[0, "ID"] = pd.NA

    with pytest.raises(
        ExplorationValidationError,
        match="null audit ID",
    ):
        validate_audit_report(report)


def test_unsupported_attempt_type_is_rejected(
    valid_report_directory: Path,
) -> None:
    report = load_valid(valid_report_directory)
    report.records.loc[0, "ATTEMPT_TYPE"] = "SYNTHETIC_UNKNOWN"

    with pytest.raises(
        ExplorationValidationError,
        match="unsupported attempt types",
    ):
        validate_audit_report(report)


def test_missing_attempt_result_is_rejected(
    valid_report_directory: Path,
) -> None:
    report = load_valid(valid_report_directory)
    report.records.loc[0, "ATTEMPT_RESULT"] = pd.NA

    with pytest.raises(
        ExplorationValidationError,
        match="missing attempt results",
    ):
        validate_audit_report(report)


@pytest.mark.parametrize(
    "metric_name",
    [
        "ai_assistance_metrics",
        "readability_metrics",
    ],
)
def test_metric_audit_id_must_not_be_null(
    valid_report_directory: Path,
    metric_name: str,
) -> None:
    report = load_valid(valid_report_directory)
    metrics = getattr(report, metric_name)
    metrics.loc[0, "record_id"] = pd.NA

    with pytest.raises(
        ExplorationValidationError,
        match="contains a null audit record ID",
    ):
        validate_audit_report(report)


def test_readability_text_role_is_validated(
    valid_report_directory: Path,
) -> None:
    report = load_valid(valid_report_directory)
    report.readability_metrics.loc[0, "text_role"] = "SYNTHETIC_UNKNOWN"

    with pytest.raises(
        ExplorationValidationError,
        match="unsupported text roles",
    ):
        validate_audit_report(report)


def test_readability_selected_value_is_validated(
    valid_report_directory: Path,
) -> None:
    report = load_valid(valid_report_directory)
    suggested = report.readability_metrics["text_role"].eq("SUGGESTED")
    report.readability_metrics.loc[suggested, "selected"] = "SYNTHETIC_UNKNOWN"

    with pytest.raises(
        ExplorationValidationError,
        match="selected values must be true, false, or null",
    ):
        validate_audit_report(report)


def test_duplicate_readability_identity_is_rejected(
    valid_report_directory: Path,
) -> None:
    report = load_valid(valid_report_directory)
    duplicate = report.readability_metrics.iloc[[0]].copy()
    duplicated_readability = pd.concat(
        [
            report.readability_metrics,
            duplicate,
        ],
        ignore_index=True,
    )
    invalid_report = LoadedAuditReport(
        records=report.records,
        ai_assistance_metrics=report.ai_assistance_metrics,
        readability_metrics=duplicated_readability,
    )

    with pytest.raises(
        ExplorationValidationError,
        match="duplicate text-instance identities",
    ):
        validate_audit_report(invalid_report)
