"""Command-line interface for study-posting audit exploration."""

import argparse
from collections.abc import Sequence
import sys
from typing import TextIO

import pandas as pd

from study_posting_audit_exploration.aggregation import (
    build_attempt_analysis_tables,
    build_author_analysis_tables,
    build_field_analysis_tables,
    build_overview_tables,
    build_quality_analysis_tables,
    build_readability_analysis_tables,
    build_study_analysis_tables,
)
from study_posting_audit_exploration.config import (
    ExplorationInputConfig,
    ExplorationRunConfig,
)
from study_posting_audit_exploration.derivation import (
    derive_appointments,
    derive_attempt_histories,
    derive_completed_ai_field_analysis,
    derive_completed_ai_readability_pairs,
)
from study_posting_audit_exploration.errors import AuditExplorationError
from study_posting_audit_exploration.loading import load_audit_report
from study_posting_audit_exploration.models import (
    AppointmentQualityFinding,
    AttemptHistoryTables,
    ExplorationAnalysisTables,
    ExplorationPublication,
    LoadedAuditReport,
    ValidationSummary,
)
from study_posting_audit_exploration.publication import publish_exploration
from study_posting_audit_exploration.validation import validate_audit_report

_SOURCE_COLUMNS: tuple[str, ...] = (
    "ID",
    "SOURCE_TYPE",
    "STUDY_CONTENT_SOURCE",
    "LLM_INFERRED_STUDY_CONTENT_SOURCE",
    "STUDY_CONTENT_SOURCE_OTHER_VALUE",
    "LLM_INFERRED_STUDY_CONTENT_SOURCE_OTHER_VALUE",
)
_SOURCE_COLUMN_RENAMES: dict[str, str] = {
    "ID": "audit_record_id",
    "SOURCE_TYPE": "source_type",
    "STUDY_CONTENT_SOURCE": "study_content_source",
    "LLM_INFERRED_STUDY_CONTENT_SOURCE": "llm_inferred_study_content_source",
    "STUDY_CONTENT_SOURCE_OTHER_VALUE": "study_content_source_other_value",
    "LLM_INFERRED_STUDY_CONTENT_SOURCE_OTHER_VALUE": (
        "llm_inferred_study_content_source_other_value"
    ),
}
_STUDY_SNAPSHOT_COLUMNS: tuple[str, ...] = (
    "ID",
    "STUDY_NUM",
    "STUDY_PARTICIPANT_TYPE",
    "STUDY_DEPARTMENT",
    "SOURCE_TYPE",
    "STUDY_CONTENT_SOURCE",
)
_STUDY_SNAPSHOT_RENAMES: dict[str, str] = {
    "ID": "audit_record_id",
    "STUDY_NUM": "study_num",
    "STUDY_PARTICIPANT_TYPE": "study_participant_type",
    "STUDY_DEPARTMENT": "study_department",
    "SOURCE_TYPE": "source_type",
    "STUDY_CONTENT_SOURCE": "study_content_source",
}


def _add_input_argument(parser: argparse.ArgumentParser) -> None:
    """Add the shared normalized report input option."""
    parser.add_argument(
        "--input-report",
        required=True,
        metavar="PATH",
        help="Directory containing the three normalized report CSVs.",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the exploration command-line parser."""
    parser = argparse.ArgumentParser(
        prog="study-posting-audit-exploration",
        description="Validate and explore normalized study-posting audit reports.",
    )
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate one normalized report directory.",
    )
    _add_input_argument(validate_parser)

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Publish exploration outputs.",
    )
    _add_input_argument(analyze_parser)
    analyze_parser.add_argument(
        "--output",
        required=True,
        metavar="PATH",
        help="New exploration output directory.",
    )

    return parser


def _load_and_validate(
    input_report: str,
) -> tuple[LoadedAuditReport, ValidationSummary]:
    """Load and validate one report directory."""
    report = load_audit_report(
        ExplorationInputConfig(
            report_directory=input_report,
        )
    )
    summary = validate_audit_report(report)

    return report, summary


def _attempts_with_source_columns(
    report: LoadedAuditReport,
    histories: AttemptHistoryTables,
) -> pd.DataFrame:
    """Join attempt histories to source and inferred content columns."""
    source_columns = report.records.loc[
        :,
        list(_SOURCE_COLUMNS),
    ].rename(columns=_SOURCE_COLUMN_RENAMES)

    return histories.study_attempt_author_history.merge(
        source_columns,
        on="audit_record_id",
        how="left",
        validate="one_to_one",
    )


def _study_snapshot_records(
    report: LoadedAuditReport,
) -> pd.DataFrame:
    """Return one selected source-attempt snapshot per study."""
    ordered = report.records.sort_values(
        by=["STUDY_NUM", "START_TIME", "ID"],
        kind="stable",
        na_position="last",
    )
    completed = ordered.loc[ordered["ATTEMPT_RESULT"].eq("COMPLETE")]
    completed_studies = frozenset(str(value) for value in completed["STUDY_NUM"])
    not_completed = ordered.loc[~ordered["STUDY_NUM"].isin(completed_studies)]
    latest_not_completed = not_completed.drop_duplicates(
        subset=["STUDY_NUM"],
        keep="last",
    )

    return pd.concat(
        [
            completed,
            latest_not_completed,
        ],
        ignore_index=True,
    )


def _studies_with_grouping_columns(
    report: LoadedAuditReport,
    histories: AttemptHistoryTables,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    tuple[AppointmentQualityFinding, ...],
]:
    """Return enriched studies, study-keyed appointments, and findings."""
    snapshot_records = _study_snapshot_records(report)
    study_source = snapshot_records.loc[
        :,
        list(_STUDY_SNAPSHOT_COLUMNS),
    ].rename(columns=_STUDY_SNAPSHOT_RENAMES)
    studies = histories.study_attempt_history.merge(
        study_source.drop(columns=["audit_record_id"]),
        on="study_num",
        how="left",
        validate="one_to_one",
    )

    appointment_rows, findings = derive_appointments(snapshot_records)
    study_keys = study_source.loc[
        :,
        [
            "audit_record_id",
            "study_num",
        ],
    ]
    appointments = study_keys.merge(
        appointment_rows,
        on="audit_record_id",
        how="inner",
        validate="one_to_many",
    )

    return studies, appointments, findings


def _analysis_tables(
    report: LoadedAuditReport,
) -> ExplorationAnalysisTables:
    """Build all current exploration tables."""
    histories = derive_attempt_histories(report.records)
    attempts = _attempts_with_source_columns(
        report,
        histories,
    )
    studies, study_appointments, appointment_findings = _studies_with_grouping_columns(
        report,
        histories,
    )
    attempt_appointments, attempt_appointment_findings = derive_appointments(
        report.records
    )
    completed_ai_fields = derive_completed_ai_field_analysis(
        report.ai_assistance_metrics,
        report.records,
    )
    readability_pairs = derive_completed_ai_readability_pairs(
        report.readability_metrics,
        completed_ai_fields,
    )

    all_appointment_findings = (
        *appointment_findings,
        *attempt_appointment_findings,
    )

    return ExplorationAnalysisTables(
        histories=histories,
        quality=build_quality_analysis_tables(
            report=report,
            histories=histories,
            appointment_quality_findings=all_appointment_findings,
        ),
        overview=build_overview_tables(
            attempts=attempts,
            studies=histories.study_attempt_history,
            authors=histories.author_history,
        ),
        attempts=build_attempt_analysis_tables(attempts),
        studies=build_study_analysis_tables(
            studies,
            study_attempt_author_history=(histories.study_attempt_author_history),
            appointments=study_appointments,
            appointment_quality_findings=all_appointment_findings,
        ),
        authors=build_author_analysis_tables(
            attempts=attempts,
            authors=histories.author_history,
            appointments=attempt_appointments,
        ),
        fields=build_field_analysis_tables(
            completed_ai_fields,
            readability_pairs,
        ),
        readability=build_readability_analysis_tables(
            readability=report.readability_metrics,
            readability_pairs=readability_pairs,
            completed_ai_fields=completed_ai_fields,
        ),
    )


def _run_validate(
    namespace: argparse.Namespace,
    *,
    output: TextIO,
) -> None:
    """Load and validate one report directory."""
    _, summary = _load_and_validate(namespace.input_report)

    print("Audit report validation passed.", file=output)
    print(f"Attempts: {summary.record_attempt_count}", file=output)
    print(f"Distinct studies: {summary.distinct_study_count}", file=output)
    print(f"Completed attempts: {summary.completed_attempt_count}", file=output)
    print(f"Incomplete attempts: {summary.incomplete_attempt_count}", file=output)
    print(
        f"AI-assistance metric rows: {summary.ai_assistance_metric_row_count}",
        file=output,
    )
    print(
        f"Readability metric rows: {summary.readability_metric_row_count}",
        file=output,
    )


def _print_publication(
    publication: ExplorationPublication,
    *,
    output: TextIO,
) -> None:
    """Print the publication paths without source identifiers."""
    published = publication

    for label, value in (
        ("Exploration directory", published.output_directory),
        ("Manifest", published.manifest_path),
        ("HTML report", published.report_path),
        ("Metric definitions CSV", published.metric_definitions_path),
        ("Data quality summary CSV", published.data_quality_summary_path),
        (
            "Completed study author context summary CSV",
            published.completed_study_author_context_summary_path,
        ),
        (
            "Completed AI field analysis CSV",
            published.completed_ai_field_analysis_path,
        ),
        (
            "Completed AI readability pairs CSV",
            published.completed_ai_readability_pairs_path,
        ),
        (
            "Field adoption and editing summary CSV",
            published.field_adoption_editing_summary_path,
        ),
        (
            "Nontext field adoption summary CSV",
            published.nontext_field_adoption_summary_path,
        ),
        (
            "Suggestion selection summary CSV",
            published.suggestion_selection_summary_path,
        ),
        (
            "Compensation analysis summary CSV",
            published.compensation_analysis_summary_path,
        ),
        (
            "Selected versus unselected readability summary CSV",
            published.selected_vs_unselected_readability_summary_path,
        ),
        (
            "Field readability change summary CSV",
            published.field_readability_change_summary_path,
        ),
        (
            "Field readability target summary CSV",
            published.field_readability_target_summary_path,
        ),
        (
            "Field edit/readability cross summary CSV",
            published.field_edit_readability_cross_summary_path,
        ),
        (
            "Final text metric summary CSV",
            published.final_text_metric_summary_path,
        ),
        (
            "Candidate research questions CSV",
            published.candidate_research_questions_path,
        ),
    ):
        print(f"{label}: {value}", file=output)

    print(
        f"Published files: {published.output_file_count}",
        file=output,
    )


def _run_analyze(
    namespace: argparse.Namespace,
    *,
    output: TextIO,
) -> None:
    """Derive and publish current exploration output."""
    report, _ = _load_and_validate(namespace.input_report)
    publication = publish_exploration(
        config=ExplorationRunConfig(
            input_report_directory=namespace.input_report,
            output_directory=namespace.output,
        ),
        report=report,
        tables=_analysis_tables(report),
    )
    _print_publication(
        publication,
        output=output,
    )


def main(
    argv: Sequence[str] | None = None,
    *,
    output: TextIO | None = None,
    error_output: TextIO | None = None,
) -> int:
    """Run the exploration CLI and return a process exit status."""
    parser = build_parser()
    namespace = parser.parse_args(argv)
    resolved_output = sys.stdout if output is None else output
    resolved_error_output = sys.stderr if error_output is None else error_output

    try:
        if namespace.command == "validate":
            _run_validate(
                namespace,
                output=resolved_output,
            )
        elif namespace.command == "analyze":
            _run_analyze(
                namespace,
                output=resolved_output,
            )
        else:  # pragma: no cover - argparse restricts registered commands
            parser.error(f"unsupported command: {namespace.command}")
    except AuditExplorationError as error:
        print(f"error: {error}", file=resolved_error_output)

        return 2

    return 0
