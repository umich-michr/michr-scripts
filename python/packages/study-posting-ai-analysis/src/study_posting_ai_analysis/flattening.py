"""Conversion of nested analysis results into flat, tabular rows.

Pure functions: no pandas, database, filesystem, or logging dependencies.
Rows are plain dictionaries, so a consumer may build a DataFrame, write CSV,
serialize to JSON, or insert into a table as it prefers.

Every row has the same keys, in the order given by ``FLATTENED_COLUMNS``, so
that a consumer can write a header once and rely on it.

Free text is excluded unless requested, to reduce accidental disclosure of
potentially sensitive study content.

See docs/analysis-specification.md section 13.
"""

import json

from study_posting_ai_analysis.models import (
    AnalysisResult,
    CompensationAnalysis,
    LookupValueAnalysis,
)

#: Every column produced for every row, in order.
#:
#: A consumer may rely on this tuple for a CSV header or a table definition.
#: Adding a column here is a change to the published output and requires a
#: corresponding documentation update.
FLATTENED_COLUMNS: tuple[str, ...] = (
    # Identification
    "record_id",
    "field_name",
    "analysis_type",
    "match_type",
    # Suggestion offer and selection
    "suggestion_count_total",
    "suggestion_counts_json",
    "picked_kind",
    "picked_index",
    "selected_text",
    "final_text",
    # Primary TER-derived measure
    "ter_rate",
    "ter_effort_saved_raw",
    "ter_effort_saved",
    "policy_adjusted_effort_saved",
    # Character-level robustness measure
    "character_edit_distance",
    "character_effort_saved_raw",
    "character_effort_saved",
    # Soft-word robustness measure
    "soft_word_edit_distance",
    "soft_word_effort_saved_raw",
    "soft_word_effort_saved",
    # Absolute proxy and descriptive lengths
    "estimated_characters_saved",
    "suggestion_character_count",
    "final_character_count",
    "suggestion_word_count",
    "final_word_count",
    # Compensation Boolean
    "flag_suggested",
    "flag_saved",
    "flag_accepted",
    "flag_changed",
    "compensation_text_required",
    # Lookup identifiers
    "lookup_similarity",
    "offered_ids",
    "picked_ids",
    "saved_ids",
    "kept_ids",
    "dropped_ids",
    "added_ids",
    "saved_not_offered_ids",
)

#: Value of ``analysis_type`` for each result kind.
TEXT_ANALYSIS_TYPE = "TEXT"
COMPENSATION_ANALYSIS_TYPE = "COMPENSATION"
LOOKUP_ANALYSIS_TYPE = "LOOKUP"


def serialize_integer_set(values: frozenset[int]) -> str:
    """Render a set of identifiers as a sorted JSON array.

    Sorted so that the same set always produces the same text, which keeps
    exported rows stable across runs and comparable in a diff.

    Parameters
    ----------
    values
        Identifiers to render.

    Returns
    -------
    str
        A JSON array such as ``"[1, 2, 3]"``.
    """
    return json.dumps(sorted(values))


def _empty_row(
    *,
    record_id: str | int | None,
    field_name: str,
) -> dict[str, object]:
    """Return a row with every column present and unset.

    Building from a complete template guarantees that all rows share the same
    keys in the same order, whatever the result kind.
    """
    row: dict[str, object] = dict.fromkeys(FLATTENED_COLUMNS)

    row["record_id"] = record_id
    row["field_name"] = field_name

    return row


def _fill_lookup_row(
    row: dict[str, object],
    result: LookupValueAnalysis,
) -> None:
    """Populate lookup-specific columns.

    ``policy_adjusted_effort_saved`` and the TER columns are deliberately left
    unset. Lookup similarity measures a different construct and must never be
    averaged together with text effort-saved scores.
    """
    row["analysis_type"] = LOOKUP_ANALYSIS_TYPE
    row["lookup_similarity"] = result.similarity
    row["offered_ids"] = serialize_integer_set(result.offered)
    row["picked_ids"] = serialize_integer_set(result.picked)
    row["saved_ids"] = serialize_integer_set(result.saved)
    row["kept_ids"] = serialize_integer_set(result.kept)
    row["dropped_ids"] = serialize_integer_set(result.dropped)
    row["added_ids"] = serialize_integer_set(result.added)
    row["saved_not_offered_ids"] = serialize_integer_set(result.saved_not_offered)


def _fill_text_row(
    row: dict[str, object],
    result: AnalysisResult,
    *,
    include_text: bool,
) -> None:
    """Populate columns common to text and compensation results."""
    if isinstance(result, LookupValueAnalysis):
        raise TypeError("Lookup results are populated by _fill_lookup_row")

    row["analysis_type"] = (
        COMPENSATION_ANALYSIS_TYPE
        if isinstance(result, CompensationAnalysis)
        else TEXT_ANALYSIS_TYPE
    )

    row["suggestion_count_total"] = sum(result.suggestion_counts.values())
    row["suggestion_counts_json"] = json.dumps(
        result.suggestion_counts,
        sort_keys=True,
    )

    if result.pick is not None:
        row["picked_kind"] = result.pick.kind
        row["picked_index"] = result.pick.index

    if include_text:
        row["selected_text"] = result.selected_text
        row["final_text"] = result.final_text

    # Present for every text outcome, including UNASSISTED and REMOVED, because
    # a zero there is a meaningful policy value rather than a missing one.
    row["policy_adjusted_effort_saved"] = result.policy_adjusted_effort_saved

    metrics = result.editing_metrics

    if metrics is not None:
        row["ter_rate"] = metrics.ter_rate
        row["ter_effort_saved_raw"] = metrics.ter_effort_saved_raw
        row["ter_effort_saved"] = metrics.ter_effort_saved

        row["character_edit_distance"] = metrics.character_edit_distance
        row["character_effort_saved_raw"] = metrics.character_effort_saved_raw
        row["character_effort_saved"] = metrics.character_effort_saved

        row["soft_word_edit_distance"] = metrics.soft_word_edit_distance
        row["soft_word_effort_saved_raw"] = metrics.soft_word_effort_saved_raw
        row["soft_word_effort_saved"] = metrics.soft_word_effort_saved

        row["estimated_characters_saved"] = metrics.estimated_characters_saved
        row["suggestion_character_count"] = metrics.suggestion_character_count
        row["final_character_count"] = metrics.final_character_count
        row["suggestion_word_count"] = metrics.suggestion_word_count
        row["final_word_count"] = metrics.final_word_count

    if isinstance(result, CompensationAnalysis):
        row["flag_suggested"] = result.flag_suggested
        row["flag_saved"] = result.flag_saved
        row["flag_accepted"] = result.flag_accepted
        row["flag_changed"] = result.flag_changed
        row["compensation_text_required"] = result.compensation_text_required


def flatten_analysis_results(
    results: dict[str, AnalysisResult],
    *,
    record_id: str | int | None = None,
    include_text: bool = False,
) -> list[dict[str, object]]:
    """Convert nested analysis results into one flat row per field.

    Parameters
    ----------
    results
        Output of ``analyze_objects``.
    record_id
        Identifier carried onto every row for provenance. Any value the caller
        finds useful, such as an audit record identifier.
    include_text
        Whether to include the selected and final field text. Defaults to
        ``False`` to reduce accidental disclosure of potentially sensitive
        study content.

    Returns
    -------
    list[dict[str, object]]
        One row per analyzed field. Every row has the same keys, in the order
        given by ``FLATTENED_COLUMNS``. Fields not applicable to a row's result
        kind are ``None``.

    Notes
    -----
    Lookup rows leave the TER and policy columns unset. Lookup similarity and
    text effort-saved scores measure different constructs and must be summarized
    separately, never combined into one average.

    Examples
    --------
    >>> rows = flatten_analysis_results(results, record_id=1234)
    >>> sorted({row["analysis_type"] for row in rows})
    ['COMPENSATION', 'LOOKUP', 'TEXT']
    """
    rows: list[dict[str, object]] = []

    for field_name, result in results.items():
        row = _empty_row(record_id=record_id, field_name=field_name)
        row["match_type"] = result.match.value

        if isinstance(result, LookupValueAnalysis):
            _fill_lookup_row(row, result)
        else:
            _fill_text_row(row, result, include_text=include_text)

        rows.append(row)

    return rows
