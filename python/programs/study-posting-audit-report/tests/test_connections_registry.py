"""Tests for report-program database-driver selection."""

from typing import cast

import pytest

from study_posting_audit_report.connections import (
    DatabaseDriver,
    OracleDriver,
    available_database_drivers,
    get_database_driver,
)
from study_posting_audit_report.errors import AuditReportConfigurationError


def test_available_database_drivers_are_stable() -> None:
    assert available_database_drivers() == ("oracle",)


@pytest.mark.parametrize(
    "name",
    [
        "oracle",
        "ORACLE",
        " Oracle ",
    ],
    ids=["lowercase", "uppercase", "padded"],
)
def test_get_database_driver_returns_oracle(name: str) -> None:
    driver = get_database_driver(name)

    assert isinstance(driver, DatabaseDriver)
    assert isinstance(driver, OracleDriver)
    assert driver.name == "oracle"


@pytest.mark.parametrize(
    "name",
    ["", "   ", "\n\t"],
    ids=["empty", "spaces", "control-whitespace"],
)
def test_database_driver_name_must_be_nonblank(name: str) -> None:
    with pytest.raises(
        AuditReportConfigurationError,
        match="database driver must be a nonblank string",
    ):
        get_database_driver(name)


def test_database_driver_name_must_be_string() -> None:
    with pytest.raises(
        AuditReportConfigurationError,
        match="database driver must be a nonblank string",
    ):
        get_database_driver(cast("str", 42))


def test_unknown_database_driver_is_rejected() -> None:
    with pytest.raises(
        AuditReportConfigurationError,
        match="unsupported database driver 'postgresql'; supported drivers: oracle",
    ):
        get_database_driver("postgresql")
