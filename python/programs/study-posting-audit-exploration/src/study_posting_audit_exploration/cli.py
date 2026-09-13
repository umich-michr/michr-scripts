"""Command-line interface for study-posting audit exploration."""

import argparse
from collections.abc import Sequence
import sys
from typing import TextIO

from study_posting_audit_exploration.config import ExplorationInputConfig
from study_posting_audit_exploration.errors import AuditExplorationError
from study_posting_audit_exploration.loading import load_audit_report
from study_posting_audit_exploration.validation import validate_audit_report


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
    validate_parser.add_argument(
        "--input-report",
        required=True,
        metavar="PATH",
        help="Directory containing the three normalized report CSVs.",
    )

    return parser


def _run_validate(
    namespace: argparse.Namespace,
    *,
    output: TextIO,
) -> None:
    """Load and validate one report directory."""
    config = ExplorationInputConfig(
        report_directory=namespace.input_report,
    )
    report = load_audit_report(config)
    summary = validate_audit_report(report)

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
        else:  # pragma: no cover - argparse restricts this to registered commands
            parser.error(f"unsupported command: {namespace.command}")
    except AuditExplorationError as error:
        print(f"error: {error}", file=resolved_error_output)

        return 2

    return 0
