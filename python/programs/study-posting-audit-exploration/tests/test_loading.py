import csv
from pathlib import Path

import pandas as pd
import pytest

from study_posting_audit_exploration import (
    ExplorationInputConfig,
    ExplorationInputError,
    load_audit_report,
)
from study_posting_audit_exploration.input_contracts import (
    AI_ASSISTANCE_METRICS_FILENAME,
    READABILITY_METRICS_FILENAME,
    RECORDS_FILENAME,
)


def test_loads_all_three_files_with_typed_columns(
    valid_report_directory: Path,
) -> None:
    report = load_audit_report(
        ExplorationInputConfig(
            report_directory=valid_report_directory,
        )
    )

    assert len(report.records) == 2
    assert len(report.ai_assistance_metrics) == 1
    assert len(report.readability_metrics) == 2

    assert str(report.records["ID"].dtype) == "Int64"
    assert pd.api.types.is_datetime64_any_dtype(report.records["START_TIME"])
    assert str(report.ai_assistance_metrics["ter_rate"].dtype) == "Float64"
    assert str(report.readability_metrics["word_count"].dtype) == "Int64"


def test_missing_report_directory_is_rejected(tmp_path: Path) -> None:
    missing = tmp_path / "missing"

    with pytest.raises(
        ExplorationInputError,
        match="Input report directory does not exist",
    ):
        load_audit_report(
            ExplorationInputConfig(
                report_directory=missing,
            )
        )


def test_report_path_must_be_directory(tmp_path: Path) -> None:
    path = tmp_path / "report"
    path.write_text("not a directory", encoding="utf-8")

    with pytest.raises(
        ExplorationInputError,
        match="Input report path is not a directory",
    ):
        load_audit_report(
            ExplorationInputConfig(
                report_directory=path,
            )
        )


@pytest.mark.parametrize(
    "file_name",
    [
        RECORDS_FILENAME,
        AI_ASSISTANCE_METRICS_FILENAME,
        READABILITY_METRICS_FILENAME,
    ],
)
def test_required_input_file_must_exist(
    valid_report_directory: Path,
    file_name: str,
) -> None:
    (valid_report_directory / file_name).unlink()

    with pytest.raises(
        ExplorationInputError,
        match="Required input file does not exist",
    ):
        load_audit_report(
            ExplorationInputConfig(
                report_directory=valid_report_directory,
            )
        )


def test_input_header_must_match_exactly(
    valid_report_directory: Path,
) -> None:
    path = valid_report_directory / RECORDS_FILENAME

    with path.open(
        mode="r",
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(csv.reader(handle))

    rows[0][0] = "WRONG_ID"

    with path.open(
        mode="w",
        encoding="utf-8",
        newline="",
    ) as handle:
        csv.writer(handle).writerows(rows)

    with pytest.raises(
        ExplorationInputError,
        match=r"Input columns do not match records\.csv",
    ):
        load_audit_report(
            ExplorationInputConfig(
                report_directory=valid_report_directory,
            )
        )


@pytest.mark.parametrize(
    ("file_name", "column_name"),
    [
        (RECORDS_FILENAME, "ID"),
        (AI_ASSISTANCE_METRICS_FILENAME, "ter_rate"),
        (READABILITY_METRICS_FILENAME, "word_count"),
    ],
)
def test_invalid_typed_value_is_rejected_without_exposing_value(
    valid_report_directory: Path,
    file_name: str,
    column_name: str,
) -> None:
    path = valid_report_directory / file_name
    sensitive_value = "SYNTHETIC-SENSITIVE-INVALID-VALUE"

    frame = pd.read_csv(
        path,
        dtype="string",
        keep_default_na=False,
    )
    frame.loc[0, column_name] = sensitive_value
    frame.to_csv(
        path,
        index=False,
        lineterminator="\n",
    )

    with pytest.raises(
        ExplorationInputError,
        match=f"column {column_name!r} contains an invalid",
    ) as captured:
        load_audit_report(
            ExplorationInputConfig(
                report_directory=valid_report_directory,
            )
        )

    assert sensitive_value not in str(captured.value)


def test_input_file_path_must_not_be_directory(
    valid_report_directory: Path,
) -> None:
    records_path = valid_report_directory / RECORDS_FILENAME
    records_path.unlink()
    records_path.mkdir()

    with pytest.raises(
        ExplorationInputError,
        match="Input file path is a directory",
    ):
        load_audit_report(
            ExplorationInputConfig(
                report_directory=valid_report_directory,
            )
        )


def test_invalid_datetime_is_rejected_without_exposing_value(
    valid_report_directory: Path,
) -> None:
    path = valid_report_directory / RECORDS_FILENAME
    sensitive_value = "SYNTHETIC-SENSITIVE-INVALID-DATETIME"

    frame = pd.read_csv(
        path,
        dtype="string",
        keep_default_na=False,
    )
    frame.loc[0, "START_TIME"] = sensitive_value
    frame.to_csv(
        path,
        index=False,
        lineterminator="\n",
    )

    with pytest.raises(
        ExplorationInputError,
        match=r"records\.csv column 'START_TIME' contains an invalid datetime",
    ) as captured:
        load_audit_report(
            ExplorationInputConfig(
                report_directory=valid_report_directory,
            )
        )

    assert sensitive_value not in str(captured.value)


def test_empty_input_file_is_rejected(
    valid_report_directory: Path,
) -> None:
    path = valid_report_directory / READABILITY_METRICS_FILENAME
    path.write_text("", encoding="utf-8")

    with pytest.raises(
        ExplorationInputError,
        match="Could not read input file",
    ):
        load_audit_report(
            ExplorationInputConfig(
                report_directory=valid_report_directory,
            )
        )
