from pathlib import Path
from typing import cast

import pytest

from study_posting_audit_exploration import (
    ExplorationConfigurationError,
    ExplorationInputConfig,
    ExplorationRunConfig,
)


@pytest.mark.parametrize("value", ["", " ", "\n\t"])
def test_report_directory_must_not_be_blank(value: str) -> None:
    with pytest.raises(
        ExplorationConfigurationError,
        match="report_directory must not be blank",
    ):
        ExplorationInputConfig(report_directory=value)


def test_report_directory_must_be_string_or_path() -> None:
    value = cast("str | Path", 17)

    with pytest.raises(
        ExplorationConfigurationError,
        match="report_directory must be a string or Path",
    ):
        ExplorationInputConfig(report_directory=value)


def test_report_directory_string_is_converted_to_path() -> None:
    config = ExplorationInputConfig(report_directory="synthetic-report")

    assert config.report_directory == Path("synthetic-report")


def test_run_config_uses_documented_defaults() -> None:
    config = ExplorationRunConfig(
        input_report_directory="synthetic-report",
        output_directory="synthetic-output",
    )

    assert config.input_report_directory == Path("synthetic-report")
    assert config.output_directory == Path("synthetic-output")
    assert config.edit_intensity_threshold_scheme == "EXPLORATORY_CHARACTER_RATIO_10_30"
    assert config.readability_unchanged_tolerance == pytest.approx(0.1)


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("input_report_directory", "", "input_report_directory must not be blank"),
        ("output_directory", " ", "output_directory must not be blank"),
        (
            "edit_intensity_threshold_scheme",
            "",
            "edit_intensity_threshold_scheme must be nonblank",
        ),
        (
            "readability_unchanged_tolerance",
            -0.1,
            "readability_unchanged_tolerance must be a nonnegative finite number",
        ),
        (
            "readability_unchanged_tolerance",
            float("inf"),
            "readability_unchanged_tolerance must be a nonnegative finite number",
        ),
    ],
)
def test_run_config_rejects_invalid_values(
    field_name: str,
    value: object,
    message: str,
) -> None:
    arguments: dict[str, object] = {
        "input_report_directory": "synthetic-report",
        "output_directory": "synthetic-output",
        "edit_intensity_threshold_scheme": ("EXPLORATORY_CHARACTER_RATIO_10_30"),
        "readability_unchanged_tolerance": 0.1,
    }
    arguments[field_name] = value

    with pytest.raises(
        ExplorationConfigurationError,
        match=message,
    ):
        ExplorationRunConfig(**arguments)  # type: ignore[arg-type]
