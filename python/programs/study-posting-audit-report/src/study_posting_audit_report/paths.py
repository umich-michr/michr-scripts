"""Repository-operated default paths for the audit-report program.

The initial command-line client is designed to run from this repository's uv
workspace. Defaults are derived from the installed source module rather than
the process working directory.
"""

from pathlib import Path


def program_directory() -> Path:
    """Return the study-posting-audit-report workspace-member directory."""
    return Path(__file__).resolve().parents[2]


def workspace_root() -> Path:
    """Return the repository root containing the Python workspace."""
    return program_directory().parents[2]


def default_schema_path() -> Path:
    """Return the default audit-row schema path."""
    return program_directory() / "input" / "audit-schema.json"


def default_sql_path() -> Path:
    """Return the future database command's default operational SQL path."""
    return program_directory() / "input" / "audit-rows.sql"


def default_output_directory() -> Path:
    """Return the default normalized report output directory."""
    return workspace_root() / "output" / "study-posting-ai-audit-analysis" / "report"


def default_dotenv_path() -> Path:
    """Return the default program-local dotenv path."""
    return program_directory() / ".env"
