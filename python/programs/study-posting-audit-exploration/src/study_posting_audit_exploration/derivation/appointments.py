"""Parsing of author and PI appointment strings."""

import re

import pandas as pd

from study_posting_audit_exploration.models import AppointmentQualityFinding

_APPOINTMENT_SEPARATOR = re.compile(r",\s+")
_APPOINTMENT_PART_COUNT = 3

_APPOINTMENT_OUTPUT_COLUMNS: tuple[str, ...] = (
    "audit_record_id",
    "appointment_source",
    "appointment_index",
    "appointment_raw",
    "appointment_title",
    "appointment_department",
    "appointment_school",
)
_APPOINTMENT_SOURCES: tuple[tuple[str, str], ...] = (
    ("AUTHOR_APPOINTMENTS", "AUTHOR"),
    ("PI_APPOINTMENTS", "PI"),
)


def _split_appointments(value: object) -> tuple[str, ...]:
    """Return raw nonblank appointment values."""
    if not isinstance(value, str) or not value.strip():
        return ()

    return tuple(_APPOINTMENT_SEPARATOR.split(value))


def _parse_appointment(
    value: str,
) -> tuple[str, str, str] | None:
    """Parse one Title:Department:School value from the right."""
    parts = tuple(part.strip() for part in value.rsplit(":", 2))

    if len(parts) != _APPOINTMENT_PART_COUNT or any(not part for part in parts):
        return None

    return parts[0], parts[1], parts[2]


def _appointment_rows(
    records: pd.DataFrame,
    *,
    column_name: str,
    appointment_source: str,
) -> tuple[list[dict[str, object]], list[AppointmentQualityFinding]]:
    """Return parsed rows and quality findings for one source column."""
    rows: list[dict[str, object]] = []
    findings: list[AppointmentQualityFinding] = []

    for audit_id, source_value in zip(
        records["ID"],
        records[column_name],
        strict=True,
    ):
        for appointment_index, raw_value in enumerate(
            _split_appointments(source_value)
        ):
            parsed = _parse_appointment(raw_value)

            if parsed is None:
                findings.append(
                    AppointmentQualityFinding(
                        audit_record_id=int(audit_id),
                        appointment_source=appointment_source,
                        appointment_index=appointment_index,
                        issue_name="MALFORMED_APPOINTMENT",
                    )
                )
                continue

            title, department, school = parsed
            rows.append(
                {
                    "audit_record_id": int(audit_id),
                    "appointment_source": appointment_source,
                    "appointment_index": appointment_index,
                    "appointment_raw": raw_value,
                    "appointment_title": title,
                    "appointment_department": department,
                    "appointment_school": school,
                }
            )

    return rows, findings


def _empty_appointment_frame() -> pd.DataFrame:
    """Return an empty appointment DataFrame with stable columns."""
    return pd.DataFrame(columns=list(_APPOINTMENT_OUTPUT_COLUMNS)).astype(
        {
            "audit_record_id": "Int64",
            "appointment_source": "string",
            "appointment_index": "Int64",
            "appointment_raw": "string",
            "appointment_title": "string",
            "appointment_department": "string",
            "appointment_school": "string",
        }
    )


def derive_appointments(
    records: pd.DataFrame,
) -> tuple[pd.DataFrame, tuple[AppointmentQualityFinding, ...]]:
    """Parse author and PI appointments into one long-format DataFrame."""
    all_rows: list[dict[str, object]] = []
    all_findings: list[AppointmentQualityFinding] = []

    for column_name, appointment_source in _APPOINTMENT_SOURCES:
        rows, findings = _appointment_rows(
            records,
            column_name=column_name,
            appointment_source=appointment_source,
        )
        all_rows.extend(rows)
        all_findings.extend(findings)

    if not all_rows:
        return _empty_appointment_frame(), tuple(all_findings)

    output = pd.DataFrame.from_records(
        all_rows,
        columns=list(_APPOINTMENT_OUTPUT_COLUMNS),
    )
    output = output.astype(
        {
            "audit_record_id": "Int64",
            "appointment_source": "string",
            "appointment_index": "Int64",
            "appointment_raw": "string",
            "appointment_title": "string",
            "appointment_department": "string",
            "appointment_school": "string",
        }
    )

    return output, tuple(all_findings)
