"""Cross-file validation required for readability pairing."""

import pandas as pd

from study_posting_audit_exploration.errors import ExplorationValidationError

_COMPLETE = "COMPLETE"
_AI = "AI"
_SELECTED_TRUE = "true"


def _selected_suggestions(readability: pd.DataFrame) -> pd.DataFrame:
    """Return readability suggestion rows marked selected."""
    selected = readability["selected"].astype("string").str.lower()

    return readability.loc[
        readability["text_role"].eq("SUGGESTED") & selected.eq(_SELECTED_TRUE)
    ]


def _require_completed_ownership(
    records: pd.DataFrame,
    readability: pd.DataFrame,
) -> None:
    """Require readability rows to belong to matching completed attempts."""
    context = records.loc[
        :,
        [
            "ID",
            "ATTEMPT_TYPE",
            "ATTEMPT_RESULT",
        ],
    ].rename(
        columns={
            "ID": "record_id",
            "ATTEMPT_TYPE": "record_attempt_type",
        }
    )
    joined = readability.merge(
        context,
        on="record_id",
        how="left",
        validate="many_to_one",
    )
    incomplete_count = int((~joined["ATTEMPT_RESULT"].eq(_COMPLETE)).sum())

    if incomplete_count:
        raise ExplorationValidationError(
            "readability_metrics.csv rows must belong to completed attempts: "
            f"{incomplete_count} affected rows"
        )

    mismatched_type_count = int(
        joined["attempt_type"].ne(joined["record_attempt_type"]).sum()
    )

    if mismatched_type_count:
        raise ExplorationValidationError(
            "readability_metrics.csv attempt_type values do not match records.csv: "
            f"{mismatched_type_count} affected rows"
        )


def _require_unique_pair_components(
    readability: pd.DataFrame,
) -> None:
    """Require at most one final and selected row per attempt and field."""
    final = readability.loc[readability["text_role"].eq("FINAL")]
    duplicate_final_count = int(
        final.duplicated(
            subset=[
                "record_id",
                "field_name",
            ],
            keep=False,
        ).sum()
    )

    if duplicate_final_count:
        raise ExplorationValidationError(
            "readability_metrics.csv contains multiple final rows per audit field: "
            f"{duplicate_final_count} affected rows"
        )

    selected = _selected_suggestions(readability)
    duplicate_selected_count = int(
        selected.duplicated(
            subset=[
                "record_id",
                "field_name",
            ],
            keep=False,
        ).sum()
    )

    if duplicate_selected_count:
        raise ExplorationValidationError(
            "readability_metrics.csv contains multiple selected suggestions "
            f"per audit field: {duplicate_selected_count} affected rows"
        )


def _require_selected_suggestion_matches_pick(
    records: pd.DataFrame,
    ai_assistance: pd.DataFrame,
    readability: pd.DataFrame,
) -> None:
    """Require existing selected readability rows to match AI field picks."""
    selected = _selected_suggestions(readability)
    ai_context = ai_assistance.loc[
        :,
        [
            "record_id",
            "field_name",
            "picked_kind",
            "picked_index",
        ],
    ]
    joined = selected.merge(
        ai_context,
        on=[
            "record_id",
            "field_name",
        ],
        how="left",
        validate="one_to_one",
    )
    mismatch_count = int(
        (
            joined["picked_kind"].isna()
            | joined["picked_index"].isna()
            | joined["suggestion_kind"].ne(joined["picked_kind"])
            | joined["suggestion_index"].ne(joined["picked_index"])
        ).sum()
    )

    if mismatch_count:
        raise ExplorationValidationError(
            "selected readability suggestions do not match AI-assistance picks: "
            f"{mismatch_count} affected rows"
        )

    attempt_context = records.loc[
        :,
        [
            "ID",
            "ATTEMPT_TYPE",
            "ATTEMPT_RESULT",
        ],
    ].rename(columns={"ID": "record_id"})
    selected_attempts = selected.merge(
        attempt_context,
        on="record_id",
        how="left",
        validate="many_to_one",
    )
    invalid_owner_count = int(
        (
            ~selected_attempts["ATTEMPT_TYPE"].eq(_AI)
            | ~selected_attempts["ATTEMPT_RESULT"].eq(_COMPLETE)
        ).sum()
    )

    if invalid_owner_count:
        raise ExplorationValidationError(
            "selected readability suggestions must belong to completed AI attempts: "
            f"{invalid_owner_count} affected rows"
        )


def validate_readability_pairing_contract(
    records: pd.DataFrame,
    ai_assistance: pd.DataFrame,
    readability: pd.DataFrame,
) -> None:
    """Validate existing rows used for optional readability pairing.

    The normalized report emits readability rows only for nonblank text.
    Therefore, an assisted AI field is not required to have selected and final
    readability rows. Pair derivation uses only fields where both components
    exist.
    """
    _require_completed_ownership(
        records,
        readability,
    )
    _require_unique_pair_components(readability)
    _require_selected_suggestion_matches_pick(
        records,
        ai_assistance,
        readability,
    )
