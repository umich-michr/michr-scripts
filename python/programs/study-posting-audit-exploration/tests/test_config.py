from pathlib import Path
from typing import cast

import pytest

from study_posting_audit_exploration import (
    ExplorationConfigurationError,
    ExplorationInputConfig,
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
