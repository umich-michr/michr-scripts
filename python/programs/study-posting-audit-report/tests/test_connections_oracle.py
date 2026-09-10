"""Tests for the Oracle report-program connection adapter."""

from collections.abc import Callable
from typing import cast

import pytest

from study_posting_audit_report.connections import (
    DatabaseDriver,
    OracleDriver,
)
from study_posting_audit_report.errors import AuditReportConfigurationError

_SYNTHETIC_SENSITIVE_VALUE = "synthetic-sensitive-value"


class RecordingConnector:
    """Record Oracle connection arguments and return a synthetic connection."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.connection = object()

    def __call__(
        self,
        **kwargs: object,
    ) -> object:
        """Record keyword arguments and return the configured connection."""
        self.calls.append(dict(kwargs))

        return self.connection


def replace_oracle_connector(
    monkeypatch: pytest.MonkeyPatch,
    connector: Callable[..., object],
) -> None:
    """Replace python-oracledb's connection function."""
    monkeypatch.setattr(
        "study_posting_audit_report.connections.oracle.oracledb.connect",
        connector,
    )


def test_oracle_driver_satisfies_database_driver_protocol() -> None:
    assert isinstance(OracleDriver(), DatabaseDriver)


def test_oracle_driver_name_is_stable() -> None:
    assert OracleDriver().name == "oracle"


def test_create_connect_is_deferred(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connector = RecordingConnector()
    replace_oracle_connector(
        monkeypatch,
        connector,
    )

    connect = OracleDriver().create_connect(
        dsn="database.example:1521/service",
        username="report_user",
        password=_SYNTHETIC_SENSITIVE_VALUE,
    )

    assert connector.calls == []

    connection = connect()

    assert connection is connector.connection
    assert connector.calls == [
        {
            "user": "report_user",
            "password": _SYNTHETIC_SENSITIVE_VALUE,
            "dsn": "database.example:1521/service",
        }
    ]


def test_oracle_driver_passes_tns_alias_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connector = RecordingConnector()
    replace_oracle_connector(
        monkeypatch,
        connector,
    )

    connect = OracleDriver().create_connect(
        dsn="REPORTING_DATABASE",
        username="report_user",
        password=_SYNTHETIC_SENSITIVE_VALUE,
    )

    connect()

    assert connector.calls[0]["dsn"] == "REPORTING_DATABASE"


def test_connection_factory_opens_a_new_connection_each_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connections = [object(), object()]
    calls: list[dict[str, object]] = []

    def connector(**kwargs: object) -> object:
        calls.append(dict(kwargs))

        return connections[len(calls) - 1]

    replace_oracle_connector(
        monkeypatch,
        connector,
    )
    connect = OracleDriver().create_connect(
        dsn="database.example:1521/service",
        username="report_user",
        password=_SYNTHETIC_SENSITIVE_VALUE,
    )

    first = connect()
    second = connect()

    assert first is connections[0]
    assert second is connections[1]
    assert len(calls) == 2


@pytest.mark.parametrize(
    ("field_name", "kwargs"),
    [
        (
            "Oracle DSN",
            {
                "dsn": "",
                "username": "report_user",
                "password": _SYNTHETIC_SENSITIVE_VALUE,
            },
        ),
        (
            "Oracle DSN",
            {
                "dsn": "   ",
                "username": "report_user",
                "password": _SYNTHETIC_SENSITIVE_VALUE,
            },
        ),
        (
            "Oracle username",
            {
                "dsn": "database.example:1521/service",
                "username": "",
                "password": _SYNTHETIC_SENSITIVE_VALUE,
            },
        ),
        (
            "Oracle password",
            {
                "dsn": "database.example:1521/service",
                "username": "report_user",
                "password": "",
            },
        ),
    ],
    ids=[
        "empty-dsn",
        "blank-dsn",
        "empty-username",
        "empty-password",
    ],
)
def test_oracle_connection_values_must_be_nonblank(
    field_name: str,
    kwargs: dict[str, object],
) -> None:
    with pytest.raises(
        AuditReportConfigurationError,
        match=rf"{field_name} must be a nonblank string",
    ):
        OracleDriver().create_connect(
            dsn=cast("str", kwargs["dsn"]),
            username=cast("str", kwargs["username"]),
            password=cast("str", kwargs["password"]),
        )


@pytest.mark.parametrize(
    ("field_name", "kwargs"),
    [
        (
            "Oracle DSN",
            {
                "dsn": None,
                "username": "report_user",
                "password": _SYNTHETIC_SENSITIVE_VALUE,
            },
        ),
        (
            "Oracle username",
            {
                "dsn": "database.example:1521/service",
                "username": 42,
                "password": _SYNTHETIC_SENSITIVE_VALUE,
            },
        ),
        (
            "Oracle password",
            {
                "dsn": "database.example:1521/service",
                "username": "report_user",
                "password": object(),
            },
        ),
    ],
    ids=[
        "dsn-none",
        "username-integer",
        "password-object",
    ],
)
def test_oracle_connection_values_must_be_strings(
    field_name: str,
    kwargs: dict[str, object],
) -> None:
    with pytest.raises(
        AuditReportConfigurationError,
        match=rf"{field_name} must be a nonblank string",
    ):
        OracleDriver().create_connect(
            dsn=cast("str", kwargs["dsn"]),
            username=cast("str", kwargs["username"]),
            password=cast("str", kwargs["password"]),
        )


def test_factory_representation_does_not_contain_password() -> None:
    connect = OracleDriver().create_connect(
        dsn="database.example:1521/service",
        username="report_user",
        password=_SYNTHETIC_SENSITIVE_VALUE,
    )

    assert _SYNTHETIC_SENSITIVE_VALUE not in repr(connect)
