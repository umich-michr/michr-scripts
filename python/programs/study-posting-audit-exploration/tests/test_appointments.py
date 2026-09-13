from pathlib import Path

import pandas as pd

from study_posting_audit_exploration import (
    ExplorationInputConfig,
    derive_appointments,
    load_audit_report,
)


def loaded_records(path: Path) -> pd.DataFrame:
    """Load a fresh synthetic records DataFrame."""
    return load_audit_report(
        ExplorationInputConfig(
            report_directory=path,
        )
    ).records


def test_derive_appointments_parses_author_and_pi_values(
    valid_report_directory: Path,
) -> None:
    records = loaded_records(valid_report_directory)
    records.loc[0, "AUTHOR_APPOINTMENTS"] = (
        "Professor:Synthetic Department:Synthetic School, "
        "Researcher:Another Department:Another School"
    )
    records.loc[0, "PI_APPOINTMENTS"] = "PI Professor:PI Department:PI School"

    appointments, findings = derive_appointments(records)

    assert findings == ()
    assert tuple(appointments.columns) == (
        "audit_record_id",
        "appointment_source",
        "appointment_index",
        "appointment_raw",
        "appointment_title",
        "appointment_department",
        "appointment_school",
    )

    first_author_rows = appointments.loc[
        appointments["audit_record_id"].eq(1001)
        & appointments["appointment_source"].eq("AUTHOR")
    ]

    assert first_author_rows[
        [
            "appointment_index",
            "appointment_title",
            "appointment_department",
            "appointment_school",
        ]
    ].to_dict(orient="records") == [
        {
            "appointment_index": 0,
            "appointment_title": "Professor",
            "appointment_department": "Synthetic Department",
            "appointment_school": "Synthetic School",
        },
        {
            "appointment_index": 1,
            "appointment_title": "Researcher",
            "appointment_department": "Another Department",
            "appointment_school": "Another School",
        },
    ]

    first_pi = appointments.loc[
        appointments["audit_record_id"].eq(1001)
        & appointments["appointment_source"].eq("PI")
    ].iloc[0]

    assert first_pi["appointment_title"] == "PI Professor"
    assert first_pi["appointment_department"] == "PI Department"
    assert first_pi["appointment_school"] == "PI School"


def test_appointment_parser_splits_from_right(
    valid_report_directory: Path,
) -> None:
    records = loaded_records(valid_report_directory)
    records.loc[0, "AUTHOR_APPOINTMENTS"] = (
        "Title:With:Colon:Department Name:School Name"
    )
    records.loc[0, "PI_APPOINTMENTS"] = pd.NA
    records.loc[1, "AUTHOR_APPOINTMENTS"] = pd.NA
    records.loc[1, "PI_APPOINTMENTS"] = pd.NA

    appointments, findings = derive_appointments(records)

    assert findings == ()
    assert len(appointments) == 1

    row = appointments.iloc[0]
    assert row["appointment_title"] == "Title:With:Colon"
    assert row["appointment_department"] == "Department Name"
    assert row["appointment_school"] == "School Name"


def test_blank_appointments_produce_empty_typed_output(
    valid_report_directory: Path,
) -> None:
    records = loaded_records(valid_report_directory)
    records["AUTHOR_APPOINTMENTS"] = pd.NA
    records["PI_APPOINTMENTS"] = pd.NA

    appointments, findings = derive_appointments(records)

    assert findings == ()
    assert appointments.empty
    assert str(appointments["audit_record_id"].dtype) == "Int64"
    assert str(appointments["appointment_source"].dtype) == "string"


def test_malformed_appointments_are_reported_without_raw_value(
    valid_report_directory: Path,
) -> None:
    records = loaded_records(valid_report_directory)
    sensitive_value = "SYNTHETIC-SENSITIVE-MALFORMED-APPOINTMENT"
    records.loc[0, "AUTHOR_APPOINTMENTS"] = sensitive_value
    records.loc[0, "PI_APPOINTMENTS"] = pd.NA
    records.loc[1, "AUTHOR_APPOINTMENTS"] = pd.NA
    records.loc[1, "PI_APPOINTMENTS"] = pd.NA

    appointments, findings = derive_appointments(records)

    assert appointments.empty
    assert len(findings) == 1

    finding = findings[0]
    assert finding.audit_record_id == 1001
    assert finding.appointment_source == "AUTHOR"
    assert finding.appointment_index == 0
    assert finding.issue_name == "MALFORMED_APPOINTMENT"
    assert sensitive_value not in repr(finding)
