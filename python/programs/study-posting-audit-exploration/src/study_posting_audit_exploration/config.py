"""Configuration for loading normalized audit-report outputs."""

from dataclasses import dataclass
from pathlib import Path

from study_posting_audit_exploration.errors import ExplorationConfigurationError


def _require_path(
    value: object,
    *,
    field_name: str,
) -> Path:
    """Return a nonblank filesystem path."""
    if isinstance(value, Path):
        return value

    if isinstance(value, str):
        if value.strip():
            return Path(value)

        raise ExplorationConfigurationError(f"{field_name} must not be blank")

    raise ExplorationConfigurationError(f"{field_name} must be a string or Path")


@dataclass(frozen=True, slots=True, init=False)
class ExplorationInputConfig:
    """Resolved paths for one normalized report input."""

    report_directory: Path

    def __init__(
        self,
        report_directory: str | Path,
    ) -> None:
        """Validate and store the report directory as a ``Path``."""
        object.__setattr__(
            self,
            "report_directory",
            _require_path(
                report_directory,
                field_name="report_directory",
            ),
        )
