"""Command-line interface for study-posting audit exploration."""

import argparse
from collections.abc import Sequence
import sys
from typing import TextIO

from study_posting_audit_exploration.aggregation import (
    build_attempt_analysis_tables,
    build_overview_tables,
)
from study_posting_audit_exploration.config import (
    ExplorationInputConfig,
    ExplorationRunConfig,
)
from study_posting_audit_exploration.derivation import derive_attempt_histories
from study_posting_audit_exploration.errors import AuditExplorationError
from study_posting_audit_exploration.loading import load_audit_report
from study_posting_audit_exploration.models import (
    LoadedAuditReport,
    ValidationSummary,
)
from study_posting_audit_exploration.publication import publish_exploration
from study_posting_audit_exploration.validation import validate_audit_report


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


def _run_analyze(
    namespace: argparse.Namespace,
    *,
    output: TextIO,
) -> None:
    """Derive and publish current exploration output."""
    report, _ = _load_and_validate(namespace.input_report)
    histories = derive_attempt_histories(report.records)
    attempts = histories.study_attempt_author_history.copy()

    source_columns = report.records.loc[
        :,
        [
            "ID",
            "SOURCE_TYPE",
            "STUDY_CONTENT_SOURCE",
            "LLM_INFERRED_STUDY_CONTENT_SOURCE",
            "STUDY_CONTENT_SOURCE_OTHER_VALUE",
            "LLM_INFERRED_STUDY_CONTENT_SOURCE_OTHER_VALUE",
        ],
    ].rename(
        columns={
            "ID": "audit_record_id",
            "SOURCE_TYPE": "source_type",
            "STUDY_CONTENT_SOURCE": "study_content_source",
            "LLM_INFERRED_STUDY_CONTENT_SOURCE": ("llm_inferred_study_content_source"),
            "STUDY_CONTENT_SOURCE_OTHER_VALUE": ("study_content_source_other_value"),
            "LLM_INFERRED_STUDY_CONTENT_SOURCE_OTHER_VALUE": (
                "llm_inferred_study_content_source_other_value"
            ),
        }
    )
    attempts = attempts.merge(
        source_columns,
        on="audit_record_id",
        how="left",
        validate="one_to_one",
    )

    overview_tables = build_overview_tables(
        attempts=attempts,
        studies=histories.study_attempt_history,
        authors=histories.author_history,
    )
    attempt_tables = build_attempt_analysis_tables(attempts)

    publication = publish_exploration(
        config=ExplorationRunConfig(
            input_report_directory=namespace.input_report,
            output_directory=namespace.output,
        ),
        report=report,
        histories=histories,
        overview_tables=overview_tables,
        attempt_tables=attempt_tables,
    )

    print(
        f"Exploration directory: {publication.output_directory}",
        file=output,
    )
    print(f"Manifest: {publication.manifest_path}", file=output)
    print(
        f"Attempt history CSV: {publication.study_attempt_author_history_path}",
        file=output,
    )
    print(
        f"Study history CSV: {publication.study_attempt_history_path}",
        file=output,
    )
    print(
        f"Author history CSV: {publication.author_history_path}",
        file=output,
    )
    print(
        f"Overview summary CSV: {publication.overview_summary_path}",
        file=output,
    )
    print(
        f"Study-attempt history summary CSV: "
        f"{publication.study_attempt_history_summary_path}",
        file=output,
    )
    print(
        f"Author handoff summary CSV: {publication.author_handoff_summary_path}",
        file=output,
    )
    print(
        f"Grouped attempt summary CSV: {publication.grouped_attempt_summary_path}",
        file=output,
    )
    print(
        f"Content-source concordance summary CSV: "
        f"{publication.content_source_concordance_summary_path}",
        file=output,
    )
    print(
        f"Content-source concordance matrix CSV: "
        f"{publication.content_source_concordance_matrix_path}",
        file=output,
    )
    print(
        f"Published files: {publication.output_file_count}",
        file=output,
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
