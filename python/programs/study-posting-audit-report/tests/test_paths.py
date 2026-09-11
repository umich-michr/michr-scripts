"""Tests for repository-operated audit-report default paths."""

from pathlib import Path

from study_posting_audit_report.paths import (
    default_dotenv_path,
    default_output_directory,
    default_schema_path,
    default_sql_path,
    program_directory,
    workspace_root,
)


def test_program_directory_contains_member_metadata() -> None:
    directory = program_directory()

    assert directory.name == "study-posting-audit-report"
    assert (directory / "pyproject.toml").is_file()
    assert (directory / "src" / "study_posting_audit_report").is_dir()


def test_workspace_root_contains_workspace_metadata() -> None:
    root = workspace_root()

    assert (root / "pyproject.toml").is_file()
    assert (root / "Makefile").is_file()
    assert root / "python" / "programs" == program_directory().parent


def test_default_schema_path_is_program_input_schema() -> None:
    path = default_schema_path()

    assert path == program_directory() / "input" / "audit-schema.json"
    assert path.is_file()


def test_default_sql_path_is_local_operational_query() -> None:
    path = default_sql_path()

    assert path == program_directory() / "input" / "audit-rows.sql"


def test_default_output_directory_is_under_workspace_output() -> None:
    assert default_output_directory() == (
        workspace_root() / "output" / "study-posting-ai-audit-analysis" / "report"
    )


def test_default_dotenv_path_is_program_dotenv() -> None:
    assert default_dotenv_path() == program_directory() / ".env"


def test_path_functions_return_absolute_paths() -> None:
    paths: tuple[Path, ...] = (
        program_directory(),
        workspace_root(),
        default_schema_path(),
        default_sql_path(),
        default_output_directory(),
        default_dotenv_path(),
    )

    assert all(path.is_absolute() for path in paths)
