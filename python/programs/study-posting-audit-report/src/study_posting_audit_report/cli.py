"""Command-line interface for study-posting audit reports."""

import argparse
from collections.abc import Mapping, Sequence
import os
import sys
from typing import TextIO

from program_configuration import (
    ConfigurationError,
    PromptProvider,
    TerminalPromptProvider,
)
from study_posting_audit_report.cli_config import (
    CsvCommandArguments,
    CsvCommandConfig,
    load_command_dotenv,
    resolve_csv_command_config,
)
from study_posting_audit_report.config import AuditReportConfig
from study_posting_audit_report.connections import get_database_driver
from study_posting_audit_report.database_config import (
    DatabaseCommandArguments,
    DatabaseCommandConfig,
    resolve_database_command_config,
)
from study_posting_audit_report.errors import AuditReportError
from study_posting_audit_report.models import AuditCsvReport
from study_posting_audit_report.output import generate_csv_report
from tabular_row_sources import (
    CsvReadOptions,
    CsvRowSource,
    DbApiQuerySource,
    RowSourceError,
    load_schema_json,
    read_sql_file,
)


def _add_shared_report_arguments(
    parser: argparse.ArgumentParser,
) -> None:
    """Add options shared by CSV and database commands."""
    parser.add_argument(
        "--schema",
        dest="schema_path",
        metavar="PATH",
        help="Row-schema JSON path.",
    )
    parser.add_argument(
        "--output",
        dest="output_directory",
        metavar="PATH",
        help="New output directory.",
    )
    parser.add_argument(
        "--include-text",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Include selected and final text in field metrics.",
    )

    dotenv_group = parser.add_mutually_exclusive_group()
    dotenv_group.add_argument(
        "--env-file",
        metavar="PATH",
        help="Explicit dotenv file path.",
    )
    dotenv_group.add_argument(
        "--no-env-file",
        action="store_true",
        help="Do not read a dotenv file.",
    )

    parser.add_argument(
        "--prompt",
        dest="prompt_enabled",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Allow prompting for unresolved settings.",
    )


def _add_csv_arguments(
    parser: argparse.ArgumentParser,
) -> None:
    """Add CSV-source command-line options."""
    parser.add_argument(
        "--input",
        dest="input_path",
        metavar="PATH",
        help="Input CSV path.",
    )
    parser.add_argument(
        "--encoding",
        help="Input CSV encoding.",
    )
    parser.add_argument(
        "--delimiter",
        help="Input CSV delimiter character.",
    )
    parser.add_argument(
        "--quotechar",
        help="Input CSV quote character.",
    )
    parser.add_argument(
        "--escapechar",
        help="Optional input CSV escape character.",
    )
    parser.add_argument(
        "--null-value",
        dest="null_values",
        action="append",
        metavar="TEXT",
        help=(
            "CSV field text interpreted as null. Repeat to configure multiple "
            "markers. CLI markers replace configured defaults."
        ),
    )


def _add_database_arguments(
    parser: argparse.ArgumentParser,
) -> None:
    """Add database-source command-line options."""
    parser.add_argument(
        "--driver",
        help="Database driver name. Defaults to oracle.",
    )
    parser.add_argument(
        "--dsn",
        help="Database DSN, Easy Connect string, or resolvable TNS alias.",
    )
    parser.add_argument(
        "--username",
        help="Database username.",
    )
    parser.add_argument(
        "--sql-file",
        dest="sql_path",
        metavar="PATH",
        help="SQL query file path.",
    )
    parser.add_argument(
        "--fetch-size",
        help="Positive number of rows requested per database fetch.",
    )
    parser.add_argument(
        "--sql-params-json",
        dest="sql_parameters_json",
        metavar="JSON",
        help="JSON object containing SQL bind parameters.",
    )
    parser.add_argument(
        "--sql-param",
        dest="sql_parameter_overrides",
        action="append",
        metavar="NAME=VALUE",
        help=(
            "String SQL bind parameter override. Repeat for multiple values. "
            "Overrides values from --sql-params-json, environment, or dotenv."
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the program command-line parser."""
    parser = argparse.ArgumentParser(
        prog="study-posting-audit-report",
        description=(
            "Generate normalized study-posting audit records and field metrics."
        ),
    )
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    csv_parser = subparsers.add_parser(
        "csv",
        help="Read audit rows from a CSV file.",
    )
    _add_shared_report_arguments(csv_parser)
    _add_csv_arguments(csv_parser)

    database_parser = subparsers.add_parser(
        "database",
        help="Read audit rows from a database query.",
    )
    _add_shared_report_arguments(database_parser)
    _add_database_arguments(database_parser)

    return parser


def _csv_arguments(namespace: argparse.Namespace) -> CsvCommandArguments:
    """Convert an argparse namespace into unresolved CSV arguments."""
    return CsvCommandArguments(
        input_path=namespace.input_path,
        schema_path=namespace.schema_path,
        output_directory=namespace.output_directory,
        include_text=namespace.include_text,
        encoding=namespace.encoding,
        delimiter=namespace.delimiter,
        quotechar=namespace.quotechar,
        escapechar=namespace.escapechar,
        null_values=namespace.null_values,
        env_file=namespace.env_file,
        no_env_file=namespace.no_env_file,
        prompt_enabled=namespace.prompt_enabled,
    )


def _database_arguments(
    namespace: argparse.Namespace,
) -> DatabaseCommandArguments:
    """Convert an argparse namespace into unresolved database arguments."""
    return DatabaseCommandArguments(
        driver=namespace.driver,
        dsn=namespace.dsn,
        username=namespace.username,
        sql_path=namespace.sql_path,
        schema_path=namespace.schema_path,
        output_directory=namespace.output_directory,
        fetch_size=namespace.fetch_size,
        sql_parameters_json=namespace.sql_parameters_json,
        sql_parameter_overrides=namespace.sql_parameter_overrides,
        include_text=namespace.include_text,
        env_file=namespace.env_file,
        no_env_file=namespace.no_env_file,
        prompt_enabled=namespace.prompt_enabled,
    )


def run_csv_command(config: CsvCommandConfig) -> AuditCsvReport:
    """Generate a report from resolved CSV command configuration."""
    schema = load_schema_json(config.schema_path)
    source = CsvRowSource(
        path=config.input_path,
        schema=schema,
        encoding=config.encoding,
        null_values=config.null_values,
        options=CsvReadOptions(
            delimiter=config.delimiter,
            quotechar=config.quotechar,
            escapechar=config.escapechar,
        ),
    )

    return generate_csv_report(
        source,
        output_directory=config.output_directory,
        config=AuditReportConfig(
            include_text=config.include_text,
        ),
    )


def run_database_command(
    config: DatabaseCommandConfig,
) -> AuditCsvReport:
    """Generate a report from resolved database command configuration."""
    driver = get_database_driver(config.driver)
    connect = driver.create_connect(
        dsn=config.dsn,
        username=config.username,
        password=config.password,
    )
    schema = load_schema_json(config.schema_path)
    sql = read_sql_file(config.sql_path)
    source = DbApiQuerySource(
        connect=connect,
        sql=sql,
        schema=schema,
        parameters=config.sql_parameters or None,
        fetch_size=config.fetch_size,
    )

    return generate_csv_report(
        source,
        output_directory=config.output_directory,
        config=AuditReportConfig(
            include_text=config.include_text,
        ),
    )


def _print_report(
    report: AuditCsvReport,
    *,
    output: TextIO,
) -> None:
    """Print a concise successful-run summary."""
    summary = report.summary

    print(f"Report directory: {report.output_directory}", file=output)
    print(f"Records CSV: {report.records_path}", file=output)
    print(
        f"AI assistance metrics CSV: {report.ai_assistance_metrics_path}", file=output
    )
    print(f"Source rows: {summary.source_rows}", file=output)
    print(f"Analyzed rows: {summary.analyzed_rows}", file=output)
    print(f"Skipped rows: {summary.skipped_rows}", file=output)
    print(f"AI assistance rows: {summary.ai_assistance_rows}", file=output)


def _run_csv_from_namespace(
    namespace: argparse.Namespace,
    *,
    environment: Mapping[str, object],
    prompt_provider: PromptProvider | None,
    output: TextIO,
) -> None:
    """Resolve one CSV invocation and generate its report."""
    arguments = _csv_arguments(namespace)
    dotenv = load_command_dotenv(
        arguments,
        environment=environment,
    )
    config = resolve_csv_command_config(
        arguments,
        environment=environment,
        dotenv=dotenv,
        prompt_provider=prompt_provider,
    )
    report = run_csv_command(config)

    _print_report(
        report,
        output=output,
    )


def _run_database_from_namespace(
    namespace: argparse.Namespace,
    *,
    environment: Mapping[str, object],
    prompt_provider: PromptProvider | None,
    output: TextIO,
) -> None:
    """Resolve one database invocation and generate its report."""
    arguments = _database_arguments(namespace)
    dotenv = load_command_dotenv(
        arguments,
        environment=environment,
    )
    config = resolve_database_command_config(
        arguments,
        environment=environment,
        dotenv=dotenv,
        prompt_provider=prompt_provider,
    )
    report = run_database_command(config)

    _print_report(
        report,
        output=output,
    )


def main(
    argv: Sequence[str] | None = None,
    *,
    environment: Mapping[str, object] | None = None,
    prompt_provider: PromptProvider | None = None,
    output: TextIO | None = None,
    error_output: TextIO | None = None,
) -> int:
    """Run the command-line program and return a process exit status."""
    parser = build_parser()
    namespace = parser.parse_args(argv)
    resolved_environment: Mapping[str, object] = (
        os.environ if environment is None else environment
    )
    resolved_prompt_provider = (
        TerminalPromptProvider() if prompt_provider is None else prompt_provider
    )
    resolved_output = sys.stdout if output is None else output
    resolved_error_output = sys.stderr if error_output is None else error_output

    try:
        if namespace.command == "csv":
            _run_csv_from_namespace(
                namespace,
                environment=resolved_environment,
                prompt_provider=resolved_prompt_provider,
                output=resolved_output,
            )
        elif namespace.command == "database":
            _run_database_from_namespace(
                namespace,
                environment=resolved_environment,
                prompt_provider=resolved_prompt_provider,
                output=resolved_output,
            )
        else:
            parser.error(f"unsupported command: {namespace.command}")
    except (
        AuditReportError,
        ConfigurationError,
        RowSourceError,
    ) as error:
        print(f"error: {error}", file=resolved_error_output)

        return 2

    return 0
