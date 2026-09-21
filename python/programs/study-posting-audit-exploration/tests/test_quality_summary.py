"""Tests for deterministic published-quality interpretation."""

import csv
import json
from pathlib import Path

import pytest

from study_posting_audit_exploration import (
    ExplorationInputError,
    ExplorationValidationError,
)
from study_posting_audit_exploration.quality import (
    DATA_QUALITY_CHECK_NAMES,
    DATA_QUALITY_CHECK_SEVERITIES,
    DATA_QUALITY_SUMMARY_COLUMNS,
)
from study_posting_audit_exploration.quality_summary import (
    load_published_quality_summary,
    render_quality_summary,
)


def _write_exploration(
    directory: Path,
    *,
    warning_counts: dict[str, int] | None = None,
) -> None:
    """Write one synthetic published quality contract."""
    warning_counts = {} if warning_counts is None else warning_counts
    quality_directory = directory / "quality"
    quality_directory.mkdir(parents=True)
    rows: list[dict[str, object]] = []

    for name in DATA_QUALITY_CHECK_NAMES:
        severity = DATA_QUALITY_CHECK_SEVERITIES[name]
        affected = warning_counts.get(name, 0)
        eligible = 20
        rows.append(
            {
                "data_quality_check_name": name,
                "severity_level": severity,
                "affected_attempt_count": affected,
                "affected_distinct_study_count": min(affected, 2),
                "affected_distinct_author_count": min(affected, 3),
                "eligible_attempt_count": eligible,
                "affected_attempt_percentage": 100.0 * affected / eligible,
                "check_definition": f"Synthetic definition for {name}.",
                "analysis_consequence": (
                    "Any detected case stops validation."
                    if severity == "FATAL"
                    else f"Synthetic consequence for {name}."
                ),
            }
        )

    with (quality_directory / "data_quality_summary.csv").open(
        mode="w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(DATA_QUALITY_SUMMARY_COLUMNS),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    warning_occurrences = sum(
        int(str(row["affected_attempt_count"]))
        for row in rows
        if row["severity_level"] == "WARNING"
    )
    manifest = {
        "source_report_directory": str(directory.parent / "report"),
        "output_file_count": 34,
        "quality_analysis_row_counts": {
            "data_quality_summary": len(rows),
        },
        "warning_count": warning_occurrences,
    }
    (directory / "analysis_manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )


def test_loads_and_renders_nonzero_warnings(tmp_path: Path) -> None:
    """Render stable counts and consequences without identifiers."""
    directory = tmp_path / "exploration"
    _write_exploration(
        directory,
        warning_counts={
            "MALFORMED_APPOINTMENT": 4,
        },
    )

    summary = load_published_quality_summary(directory)
    text = render_quality_summary(summary)

    assert summary.has_warnings
    assert summary.warning_occurrence_count == 4
    assert "Fatal validation checks passed: 13 of 13" in text
    assert "Warning categories detected: 1 of 3" in text
    assert "Warning occurrences: 4" in text
    assert "- MALFORMED_APPOINTMENT" in text
    assert "Affected attempts: 4 of 20 (20.0%)" in text
    assert "Affected studies: 2" in text
    assert "Affected authors: 3" in text
    assert "Synthetic consequence for MALFORMED_APPOINTMENT." in text
    assert "No attempts occurred after completion." in text
    assert "No studies had varying CREATED_BY_ID values." in text
    assert "Where to investigate:" in text
    assert "quality/data_quality_summary.csv" in text
    assert "analysis-audit-records/data_quality_findings.csv" in text
    assert "records.csv" in text


def test_renders_no_warning_result(tmp_path: Path) -> None:
    """Explain a valid run with no affected warning checks."""
    directory = tmp_path / "exploration"
    _write_exploration(directory)

    summary = load_published_quality_summary(directory)
    text = render_quality_summary(summary)

    assert not summary.has_warnings
    assert "Warning categories detected: 0 of 3" in text
    assert "Warning occurrences: 0" in text
    assert "No warning checks affected attempts." in text
    assert "No malformed appointment entries affected attempts." in text
    assert "No warning investigation is required for this run." in text


def test_rejects_missing_exploration_directory(tmp_path: Path) -> None:
    """Fail with a sanitized expected input error."""
    with pytest.raises(
        ExplorationInputError,
        match="Exploration directory does not exist",
    ):
        load_published_quality_summary(tmp_path / "missing")


def test_rejects_incorrect_quality_header(tmp_path: Path) -> None:
    """Require the exact quality CSV schema."""
    directory = tmp_path / "exploration"
    _write_exploration(directory)
    path = directory / "quality/data_quality_summary.csv"
    content = path.read_text(encoding="utf-8")
    path.write_text(
        content.replace("severity_level", "wrong_severity", 1),
        encoding="utf-8",
    )

    with pytest.raises(
        ExplorationValidationError,
        match="columns do not match",
    ):
        load_published_quality_summary(directory)


def test_rejects_missing_or_reordered_checks(tmp_path: Path) -> None:
    """Require one row per stable check in stable order."""
    directory = tmp_path / "exploration"
    _write_exploration(directory)
    path = directory / "quality/data_quality_summary.csv"

    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))

    rows[1], rows[2] = rows[2], rows[1]

    with path.open(mode="w", encoding="utf-8", newline="") as handle:
        csv.writer(handle, lineterminator="\n").writerows(rows)

    with pytest.raises(
        ExplorationValidationError,
        match="missing, duplicated, or out of order",
    ):
        load_published_quality_summary(directory)


@pytest.mark.parametrize(
    ("manifest_field", "value", "message"),
    [
        ("output_file_count", 33, "34-file contract"),
        ("warning_count", 99, "warning count does not match"),
    ],
)
def test_rejects_manifest_mismatch(
    tmp_path: Path,
    manifest_field: str,
    value: int,
    message: str,
) -> None:
    """Require manifest consistency with quality output."""
    directory = tmp_path / "exploration"
    _write_exploration(directory)
    path = directory / "analysis_manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest[manifest_field] = value
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(
        ExplorationValidationError,
        match=message,
    ):
        load_published_quality_summary(directory)


def test_rejects_nonzero_published_fatal_check(tmp_path: Path) -> None:
    """A published exploration cannot contain an affected fatal check."""
    directory = tmp_path / "exploration"
    _write_exploration(directory)
    path = directory / "quality/data_quality_summary.csv"

    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    rows[0]["affected_attempt_count"] = "1"
    rows[0]["affected_attempt_percentage"] = "5.0"

    with path.open(mode="w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(DATA_QUALITY_SUMMARY_COLUMNS),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(
        ExplorationValidationError,
        match="fatal quality check",
    ):
        load_published_quality_summary(directory)
