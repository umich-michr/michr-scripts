"""Configuration for normalized audit exploration."""

from dataclasses import dataclass
from pathlib import Path

from study_posting_audit_exploration.errors import ExplorationConfigurationError

_DEFAULT_EDIT_THRESHOLD_SCHEME = "EXPLORATORY_CHARACTER_RATIO_10_30"
_DEFAULT_READABILITY_TOLERANCE = 0.1


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


def _require_nonblank_string(
    value: object,
    *,
    field_name: str,
) -> str:
    """Return a nonblank string."""
    if not isinstance(value, str) or not value.strip():
        raise ExplorationConfigurationError(f"{field_name} must be nonblank")

    return value


def _require_nonnegative_float(
    value: object,
    *,
    field_name: str,
) -> float:
    """Return a finite nonnegative float."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ExplorationConfigurationError(
            f"{field_name} must be a nonnegative finite number"
        )

    converted = float(value)

    if converted < 0 or not converted < float("inf"):
        raise ExplorationConfigurationError(
            f"{field_name} must be a nonnegative finite number"
        )

    return converted


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


@dataclass(frozen=True, slots=True, init=False)
class ExplorationRunConfig:
    """Resolved configuration for one exploration publication run."""

    input_report_directory: Path
    output_directory: Path
    edit_intensity_threshold_scheme: str
    readability_unchanged_tolerance: float

    def __init__(
        self,
        *,
        input_report_directory: str | Path,
        output_directory: str | Path,
        edit_intensity_threshold_scheme: str = _DEFAULT_EDIT_THRESHOLD_SCHEME,
        readability_unchanged_tolerance: float = _DEFAULT_READABILITY_TOLERANCE,
    ) -> None:
        """Validate and store one run configuration."""
        object.__setattr__(
            self,
            "input_report_directory",
            _require_path(
                input_report_directory,
                field_name="input_report_directory",
            ),
        )
        object.__setattr__(
            self,
            "output_directory",
            _require_path(
                output_directory,
                field_name="output_directory",
            ),
        )
        object.__setattr__(
            self,
            "edit_intensity_threshold_scheme",
            _require_nonblank_string(
                edit_intensity_threshold_scheme,
                field_name="edit_intensity_threshold_scheme",
            ),
        )
        object.__setattr__(
            self,
            "readability_unchanged_tolerance",
            _require_nonnegative_float(
                readability_unchanged_tolerance,
                field_name="readability_unchanged_tolerance",
            ),
        )
