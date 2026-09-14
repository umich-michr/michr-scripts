import pandas as pd
import pytest

from study_posting_audit_exploration import (
    ExplorationValidationError,
    build_suggestion_selection_summary,
)


def field_row(
    *,
    audit_record_id: int,
    field_name: str,
    counts: str,
    picked_kind: str | None,
    picked_index: int | None,
    analysis_type: str = "TEXT",
) -> dict[str, object]:
    """Return one synthetic completed-AI field row."""
    return {
        "audit_record_id": audit_record_id,
        "field_name": field_name,
        "analysis_type": analysis_type,
        "suggestion_counts_json": counts,
        "picked_kind": picked_kind,
        "picked_index": picked_index,
    }


def summary_row(
    summary: pd.DataFrame,
    *,
    field_name: str,
    suggestion_kind: str,
    suggestion_index: int,
) -> pd.Series:
    """Return one suggestion-position summary row."""
    return summary.loc[
        summary["field_name"].eq(field_name)
        & summary["suggestion_kind"].eq(suggestion_kind)
        & summary["suggestion_index"].eq(suggestion_index)
    ].iloc[0]


def test_suggestion_summary_counts_offers_and_selection_by_index() -> None:
    fields = pd.DataFrame.from_records(
        [
            field_row(
                audit_record_id=1,
                field_name="title",
                counts='{"title": 3}',
                picked_kind="title",
                picked_index=1,
            ),
            field_row(
                audit_record_id=2,
                field_name="title",
                counts='{"title": 2}',
                picked_kind="title",
                picked_index=0,
            ),
            field_row(
                audit_record_id=3,
                field_name="title",
                counts='{"title": 1}',
                picked_kind=None,
                picked_index=None,
            ),
        ]
    )

    summary = build_suggestion_selection_summary(fields)
    index_zero = summary_row(
        summary,
        field_name="title",
        suggestion_kind="title",
        suggestion_index=0,
    )
    index_one = summary_row(
        summary,
        field_name="title",
        suggestion_kind="title",
        suggestion_index=1,
    )
    index_two = summary_row(
        summary,
        field_name="title",
        suggestion_kind="title",
        suggestion_index=2,
    )

    assert index_zero["offered_suggestion_count"] == 6
    assert index_zero["selected_suggestion_count"] == 2
    assert index_zero["unselected_suggestion_count"] == 4
    assert index_zero["completed_ai_attempt_count_with_at_least_one_suggestion"] == 3
    assert index_zero["completed_ai_attempt_count_with_selected_suggestion"] == 2
    assert index_zero["suggestion_level_selection_percentage"] == pytest.approx(
        100.0 / 3.0
    )
    assert index_zero["attempt_level_selection_percentage"] == pytest.approx(
        200.0 / 3.0
    )
    assert index_zero["suggestion_count_at_index"] == 3
    assert index_zero["selected_suggestion_count_at_index"] == 1
    assert index_zero["selection_percentage_at_index"] == pytest.approx(100.0 / 3.0)

    assert index_one["suggestion_count_at_index"] == 2
    assert index_one["selected_suggestion_count_at_index"] == 1
    assert index_one["selection_percentage_at_index"] == pytest.approx(50.0)

    assert index_two["suggestion_count_at_index"] == 1
    assert index_two["selected_suggestion_count_at_index"] == 0
    assert index_two["selection_percentage_at_index"] == 0.0


def test_suggestion_summary_preserves_compensation_kinds() -> None:
    fields = pd.DataFrame.from_records(
        [
            field_row(
                audit_record_id=1,
                field_name="compensation",
                analysis_type="COMPENSATION",
                counts=('{"genericCompensation": 2, "specificCompensation": 1}'),
                picked_kind="specificCompensation",
                picked_index=0,
            )
        ]
    )

    summary = build_suggestion_selection_summary(fields)

    assert set(summary["suggestion_kind"]) == {
        "genericCompensation",
        "specificCompensation",
    }
    selected = summary_row(
        summary,
        field_name="compensation",
        suggestion_kind="specificCompensation",
        suggestion_index=0,
    )
    assert selected["selected_suggestion_count_at_index"] == 1


def test_suggestion_summary_ignores_lookup_rows() -> None:
    fields = pd.DataFrame.from_records(
        [
            field_row(
                audit_record_id=1,
                field_name="topics",
                analysis_type="LOOKUP",
                counts="{}",
                picked_kind=None,
                picked_index=None,
            )
        ]
    )

    summary = build_suggestion_selection_summary(fields)

    assert summary.empty
    assert "suggestion_kind" in summary.columns


@pytest.mark.parametrize(
    ("counts", "message"),
    [
        ("not-json", "contains invalid JSON"),
        ("[]", "must contain a JSON object"),
        ('{"": 1}', "invalid suggestion kind"),
        ('{"title": -1}', "invalid suggestion count"),
        ('{"title": true}', "invalid suggestion count"),
    ],
)
def test_suggestion_summary_rejects_invalid_counts(
    counts: str,
    message: str,
) -> None:
    fields = pd.DataFrame.from_records(
        [
            field_row(
                audit_record_id=1,
                field_name="title",
                counts=counts,
                picked_kind=None,
                picked_index=None,
            )
        ]
    )

    with pytest.raises(
        ExplorationValidationError,
        match=message,
    ):
        build_suggestion_selection_summary(fields)


def test_suggestion_summary_rejects_invalid_pick_index() -> None:
    fields = pd.DataFrame.from_records(
        [
            field_row(
                audit_record_id=1,
                field_name="title",
                counts='{"title": 1}',
                picked_kind="title",
                picked_index=-1,
            )
        ]
    )

    with pytest.raises(
        ExplorationValidationError,
        match="picked_index must contain a nonnegative integer or null",
    ):
        build_suggestion_selection_summary(fields)
