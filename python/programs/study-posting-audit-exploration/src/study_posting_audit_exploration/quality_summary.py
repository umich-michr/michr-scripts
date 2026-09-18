"""Read and explain one published identifier-free data-quality summary."""

from collections.abc import Mapping
import csv
from dataclasses import dataclass
import json
import math
from pathlib import Path

from study_posting_audit_exploration.errors import (
    ExplorationInputError,
    ExplorationValidationError,
)
from study_posting_audit_exploration.quality import (
    DATA_QUALITY_CHECK_NAMES,
    DATA_QUALITY_CHECK_SEVERITIES,
    DATA_QUALITY_SUMMARY_COLUMNS,
)

_MANIFEST_FILENAME = "analysis_manifest.json"
_QUALITY_RELATIVE_PATH = Path("quality/data_quality_summary.csv")
_EXPECTED_OUTPUT_FILE_COUNT = 31
_NULL_VALUE = "\\N"
_FATAL = "FATAL"
_WARNING = "WARNING"

_ZERO_WARNING_MESSAGES: Mapping[str, str] = {
    "ATTEMPT_AFTER_COMPLETION": "No attempts occurred after completion.",
    "CREATED_BY_ID_VARIES_WITHIN_STUDY": (
        "No studies had varying CREATED_BY_ID values."
    ),
    "MALFORMED_APPOINTMENT": "No malformed appointment entries affected attempts.",
}


@dataclass(frozen=True, slots=True)
class PublishedQualityCheck:
    """One validated row from a published quality summary."""

    name: str
    severity: str
    affected_attempt_count: int
    affected_distinct_study_count: int
    affected_distinct_author_count: int
    eligible_attempt_count: int
    affected_attempt_percentage: float | None
    definition: str
    consequence: str


@dataclass(frozen=True, slots=True)
class PublishedQualitySummary:
    """Validated quality rows and investigation context."""

    checks: tuple[PublishedQualityCheck, ...]
    warning_occurrence_count: int
    exploration_directory: Path
    source_report_directory: Path

    @property
    def fatal_checks(self) -> tuple[PublishedQualityCheck, ...]:
        """Return fatal checks in stable published order."""
        return tuple(check for check in self.checks if check.severity == _FATAL)

    @property
    def warning_checks(self) -> tuple[PublishedQualityCheck, ...]:
        """Return warning checks in stable published order."""
        return tuple(check for check in self.checks if check.severity == _WARNING)

    @property
    def affected_warning_checks(self) -> tuple[PublishedQualityCheck, ...]:
        """Return warning checks with at least one affected attempt."""
        return tuple(
            check for check in self.warning_checks if check.affected_attempt_count > 0
        )

    @property
    def has_warnings(self) -> bool:
        """Return whether any warning check has affected attempts."""
        return bool(self.affected_warning_checks)


def _require_directory(path: Path) -> None:
    """Require one existing exploration directory."""
    if not path.exists():
        raise ExplorationInputError(f"Exploration directory does not exist: {path}")

    if not path.is_dir():
        raise ExplorationInputError(f"Exploration path is not a directory: {path}")


def _read_manifest(path: Path) -> dict[str, object]:
    """Read one JSON manifest object."""
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ExplorationInputError(
            f"Required exploration file does not exist: {path}"
        ) from error
    except PermissionError as error:
        raise ExplorationInputError(
            f"Exploration file cannot be read: {path}"
        ) from error
    except (UnicodeError, OSError, json.JSONDecodeError) as error:
        raise ExplorationInputError(
            f"Could not read exploration manifest: {path}"
        ) from error

    if not isinstance(content, dict):
        raise ExplorationValidationError(
            "Exploration manifest must contain a JSON object"
        )

    return content


def _read_quality_rows(path: Path) -> list[dict[str, str]]:
    """Read the quality CSV with its exact public schema."""
    try:
        with path.open(
            mode="r",
            encoding="utf-8",
            newline="",
        ) as handle:
            reader = csv.DictReader(handle)
            fieldnames = tuple(reader.fieldnames or ())

            if fieldnames != DATA_QUALITY_SUMMARY_COLUMNS:
                raise ExplorationValidationError(
                    "Data-quality summary columns do not match the published schema"
                )

            return [dict(row) for row in reader]
    except FileNotFoundError as error:
        raise ExplorationInputError(
            f"Required exploration file does not exist: {path}"
        ) from error
    except PermissionError as error:
        raise ExplorationInputError(
            f"Exploration file cannot be read: {path}"
        ) from error
    except (UnicodeError, OSError, csv.Error) as error:
        raise ExplorationInputError(
            f"Could not read data-quality summary: {path}"
        ) from error


def _nonnegative_integer(value: str, *, field_name: str) -> int:
    """Return one nonnegative integer from published CSV text."""
    try:
        converted = int(value)
    except ValueError as error:
        raise ExplorationValidationError(
            f"Data-quality field {field_name!r} must be an integer"
        ) from error

    if converted < 0:
        raise ExplorationValidationError(
            f"Data-quality field {field_name!r} must be nonnegative"
        )

    return converted


def _optional_percentage(value: str) -> float | None:
    """Return one finite nonnegative percentage or None."""
    if value == _NULL_VALUE:
        return None

    try:
        converted = float(value)
    except ValueError as error:
        raise ExplorationValidationError(
            "Data-quality affected percentage must be numeric or missing"
        ) from error

    if not math.isfinite(converted) or converted < 0:
        raise ExplorationValidationError(
            "Data-quality affected percentage must be finite and nonnegative"
        )

    return converted


def _nonblank(value: str, *, field_name: str) -> str:
    """Return nonblank published text."""
    if not value.strip():
        raise ExplorationValidationError(
            f"Data-quality field {field_name!r} must be nonblank"
        )

    return value


def _quality_check(row: dict[str, str]) -> PublishedQualityCheck:
    """Convert and validate one quality CSV row."""
    name = _nonblank(
        row["data_quality_check_name"],
        field_name="data_quality_check_name",
    )
    expected_severity = DATA_QUALITY_CHECK_SEVERITIES.get(name)

    if expected_severity is None:
        raise ExplorationValidationError(
            f"Data-quality summary contains unsupported check: {name}"
        )

    severity = row["severity_level"]

    if severity != expected_severity:
        raise ExplorationValidationError(
            f"Data-quality check {name!r} has an inconsistent severity"
        )

    attempt_count = _nonnegative_integer(
        row["affected_attempt_count"],
        field_name="affected_attempt_count",
    )
    eligible_count = _nonnegative_integer(
        row["eligible_attempt_count"],
        field_name="eligible_attempt_count",
    )
    percentage = _optional_percentage(row["affected_attempt_percentage"])

    if eligible_count == 0 and percentage is not None:
        raise ExplorationValidationError(
            f"Data-quality check {name!r} must have a missing percentage "
            "when its eligible denominator is zero"
        )

    if eligible_count > 0:
        expected_percentage = 100.0 * attempt_count / eligible_count

        if percentage is None or not math.isclose(
            percentage,
            expected_percentage,
            rel_tol=1e-9,
            abs_tol=1e-9,
        ):
            raise ExplorationValidationError(
                f"Data-quality check {name!r} has an inconsistent percentage"
            )

    if severity == _FATAL and attempt_count != 0:
        raise ExplorationValidationError(
            f"Published fatal quality check {name!r} must have zero affected attempts"
        )

    return PublishedQualityCheck(
        name=name,
        severity=severity,
        affected_attempt_count=attempt_count,
        affected_distinct_study_count=_nonnegative_integer(
            row["affected_distinct_study_count"],
            field_name="affected_distinct_study_count",
        ),
        affected_distinct_author_count=_nonnegative_integer(
            row["affected_distinct_author_count"],
            field_name="affected_distinct_author_count",
        ),
        eligible_attempt_count=eligible_count,
        affected_attempt_percentage=percentage,
        definition=_nonblank(
            row["check_definition"],
            field_name="check_definition",
        ),
        consequence=_nonblank(
            row["analysis_consequence"],
            field_name="analysis_consequence",
        ),
    )


def _manifest_integer(
    value: object,
    *,
    field_name: str,
) -> int:
    """Return one nonnegative manifest integer."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ExplorationValidationError(
            f"Exploration manifest field {field_name!r} must be a nonnegative integer"
        )

    return value


def _validate_manifest(
    manifest: dict[str, object],
    *,
    quality_row_count: int,
    warning_occurrence_count: int,
) -> None:
    """Require manifest consistency with the quality CSV."""
    output_file_count = _manifest_integer(
        manifest.get("output_file_count"),
        field_name="output_file_count",
    )

    if output_file_count != _EXPECTED_OUTPUT_FILE_COUNT:
        raise ExplorationValidationError(
            "Exploration manifest output-file count does not match the "
            "current 31-file contract"
        )

    quality_counts = manifest.get("quality_analysis_row_counts")

    if not isinstance(quality_counts, dict):
        raise ExplorationValidationError(
            "Exploration manifest lacks quality-analysis row counts"
        )

    published_row_count = _manifest_integer(
        quality_counts.get("data_quality_summary"),
        field_name="quality_analysis_row_counts.data_quality_summary",
    )

    if published_row_count != quality_row_count:
        raise ExplorationValidationError(
            "Exploration manifest quality row count does not match "
            "data_quality_summary.csv"
        )

    manifest_warning_count = _manifest_integer(
        manifest.get("warning_count"),
        field_name="warning_count",
    )

    if manifest_warning_count != warning_occurrence_count:
        raise ExplorationValidationError(
            "Exploration manifest warning count does not match the quality summary"
        )


def load_published_quality_summary(
    exploration_directory: str | Path,
) -> PublishedQualitySummary:
    """Load and validate quality output from one published exploration."""
    directory = Path(exploration_directory)
    _require_directory(directory)
    rows = _read_quality_rows(directory / _QUALITY_RELATIVE_PATH)
    checks = tuple(_quality_check(row) for row in rows)
    names = tuple(check.name for check in checks)

    if names != DATA_QUALITY_CHECK_NAMES:
        raise ExplorationValidationError(
            "Data-quality checks are missing, duplicated, or out of order"
        )

    warning_occurrence_count = sum(
        check.affected_attempt_count for check in checks if check.severity == _WARNING
    )
    manifest = _read_manifest(directory / _MANIFEST_FILENAME)
    _validate_manifest(
        manifest,
        quality_row_count=len(checks),
        warning_occurrence_count=warning_occurrence_count,
    )
    source_report_directory = manifest.get("source_report_directory")

    if (
        not isinstance(source_report_directory, str)
        or not source_report_directory.strip()
    ):
        raise ExplorationValidationError(
            "Exploration manifest lacks a source report directory"
        )

    return PublishedQualitySummary(
        checks=checks,
        warning_occurrence_count=warning_occurrence_count,
        exploration_directory=directory.resolve(),
        source_report_directory=Path(source_report_directory),
    )


def render_quality_summary(summary: PublishedQualitySummary) -> str:
    """Return a deterministic plain-text explanation of quality results."""
    fatal_checks = summary.fatal_checks
    warning_checks = summary.warning_checks
    affected_warnings = summary.affected_warning_checks
    lines = [
        "Data-quality summary",
        "",
        (f"Fatal validation checks passed: {len(fatal_checks)} of {len(fatal_checks)}"),
        (
            "Warning categories detected: "
            f"{len(affected_warnings)} of {len(warning_checks)}"
        ),
        f"Warning occurrences: {summary.warning_occurrence_count}",
        "",
    ]

    if affected_warnings:
        lines.append("Warnings:")

        for check in affected_warnings:
            percentage = check.affected_attempt_percentage
            percentage_text = "missing" if percentage is None else f"{percentage:.1f}%"
            lines.extend(
                [
                    f"- {check.name}",
                    (
                        "  Affected attempts: "
                        f"{check.affected_attempt_count} of "
                        f"{check.eligible_attempt_count} "
                        f"({percentage_text})"
                    ),
                    (f"  Affected studies: {check.affected_distinct_study_count}"),
                    (f"  Affected authors: {check.affected_distinct_author_count}"),
                    f"  Consequence: {check.consequence}",
                ]
            )

        lines.append("")
    else:
        lines.extend(
            [
                "Warnings:",
                "- No warning checks affected attempts.",
                "",
            ]
        )

    lines.append("Zero-result warning checks:")

    lines.extend(
        f"- {_ZERO_WARNING_MESSAGES.get(check.name, f'{check.name}: none.')}"
        for check in warning_checks
        if check.affected_attempt_count == 0
    )

    if summary.has_warnings:
        quality_path = (
            summary.exploration_directory / "quality/data_quality_summary.csv"
        )
        findings_path = (
            summary.exploration_directory
            / "analysis-audit-records/data_quality_findings.csv"
        )
        records_path = summary.source_report_directory / "records.csv"
        lines.extend(
            [
                "",
                "Where to investigate:",
                (f"- Warning definitions and aggregate counts: {quality_path}"),
                (f"- Restricted audit IDs and finding positions: {findings_path}"),
                (f"- Matching normalized source attempts: {records_path}"),
                (
                    "Use audit_record_id from data_quality_findings.csv to "
                    "locate the corresponding records.csv row."
                ),
            ]
        )
    else:
        lines.extend(
            [
                "",
                "No warning investigation is required for this run.",
            ]
        )

    return "\n".join(lines) + "\n"
