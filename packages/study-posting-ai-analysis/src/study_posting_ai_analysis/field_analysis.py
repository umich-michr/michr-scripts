"""Business rules for classifying and analyzing each form field.

Pure functions only: no database, filesystem, pandas, or logging
dependencies. Functions raise on invalid input rather than logging or returning
a sentinel.

Text evaluation order is blank, then exact, then cosmetic, then edited. Metrics
are calculated for all three nonblank outcomes, so an exact match records a
verified score rather than an assumed one.

Requiredness is enforced before any normalized metric is calculated, because a
blank required field is a validation error rather than a metric of zero.

See docs/analysis-specification.md sections 4, 5, 6, 10, and 11.
"""

from study_posting_ai_analysis.field_specs import (
    COMPENSATION_KINDS,
    CONTACT_FIELDS,
    CONTACT_PREFIX,
    FIELD_SPECS,
    REQUIRED_CONTACT_FIELDS,
)
from study_posting_ai_analysis.metrics import analyze_selected_suggestion
from study_posting_ai_analysis.models import (
    AnalysisResult,
    CompensationAnalysis,
    FieldKind,
    LookupValueAnalysis,
    MatchType,
    Pick,
    SuggestionEditingResult,
    TextFieldAnalysis,
)
from study_posting_ai_analysis.text_normalization import (
    is_blank_text,
    normalize_text_for_equivalence,
)
from study_posting_ai_analysis.validation import (
    require_integer_set,
    require_non_blank_string,
    require_object,
    require_optional_boolean,
    require_string,
    require_string_list,
)


def find_first_picked_suggestion(
    suggestions: list[str],
    selections: list[str],
) -> tuple[int, str] | None:
    """Locate the first selection that occurs among the offered suggestions.

    Parameters
    ----------
    suggestions
        Suggestions offered by the AI, in the order they were presented.
    selections
        Values the user selected.

    Returns
    -------
    tuple[int, str] | None
        The zero-based index within ``suggestions`` and the selected text, or
        ``None`` when no selection matches an offered suggestion.

    Notes
    -----
    The returned index refers to a position within ``suggestions``, not within
    ``selections``. When duplicate suggestions were offered, the first
    occurrence is reported.
    """
    suggestion_to_index: dict[str, int] = {}

    for index, suggestion in enumerate(suggestions):
        suggestion_to_index.setdefault(suggestion, index)

    for selection in selections:
        suggestion_index = suggestion_to_index.get(selection)

        if suggestion_index is not None:
            return suggestion_index, selection

    return None


def compare_selected_text(
    field: str,
    selected: str,
    final: str,
    *,
    allow_empty_final: bool,
) -> tuple[MatchType, SuggestionEditingResult | None]:
    """Compare a selected suggestion with the value ultimately saved.

    Evaluation order is blank, then exact, then cosmetic, then edited.

    Parameters
    ----------
    field
        Field name, used in exception messages and in the result.
    selected
        The suggestion the user applied.
    final
        The text the user saved.
    allow_empty_final
        Whether a blank final value is permitted for this field.

    Returns
    -------
    tuple[MatchType, SuggestionEditingResult | None]
        The outcome classification, and the editing metrics when the final text
        is nonblank. Metrics are ``None`` for a ``REMOVED`` outcome, because the
        normalized scores would require a zero denominator.

    Raises
    ------
    ValueError
        If ``field`` is blank, or the final text is blank for a required field.
    TypeError
        If ``selected`` or ``final`` is not a string.
    """
    field = require_non_blank_string(field, parameter_name="field")
    selected = require_string(selected, parameter_name="selected")
    final = require_string(final, parameter_name="final")

    if is_blank_text(final):
        if not allow_empty_final:
            raise ValueError(f"{field}: final saved text must not be blank")

        return MatchType.REMOVED, None

    if selected == final:
        match = MatchType.EXACT

    elif normalize_text_for_equivalence(selected) == (
        normalize_text_for_equivalence(final)
    ):
        # Differences confined to case, diacritics, punctuation, symbols, or
        # whitespace. The broad equivalence transformation is used only for this
        # classification and never as metric preprocessing.
        match = MatchType.COSMETIC_EQUIVALENT

    else:
        match = MatchType.EDITED

    editing_metrics = analyze_selected_suggestion(
        field_name=field,
        suggestion=selected,
        final=final,
    )

    return match, editing_metrics


def analyze_text_field(
    field: str,
    suggested: object,
    selected: object,
    final: object,
    *,
    allow_empty_final: bool,
) -> TextFieldAnalysis:
    """Analyze a text field offering zero or more suggested strings.

    Parameters
    ----------
    field
        Field name.
    suggested
        Suggestions offered by the AI. ``None`` is treated as none offered.
    selected
        Values the user selected. At most one is permitted.
    final
        The value the user saved. ``None`` is treated as blank.
    allow_empty_final
        Whether a blank final value is permitted for this field.

    Returns
    -------
    TextFieldAnalysis
        ``UNASSISTED`` when nothing was selected, otherwise the outcome of
        comparing the selection with the saved value.

    Raises
    ------
    ValueError
        If more than one suggestion was selected, if a selected value does not
        occur among the offered suggestions, or if a required final value is
        blank.
    TypeError
        If any container or the final value has the wrong type.
    """
    suggestions = require_string_list(
        suggested,
        parameter_name=f"{field}.suggested",
    )
    selections = require_string_list(
        selected,
        parameter_name=f"{field}.selected",
    )

    if len(selections) > 1:
        raise ValueError(f"{field}: at most one suggestion may be selected")

    if final is None:
        final_text = ""
    else:
        final_text = require_string(final, parameter_name=f"{field}.final")

    suggestion_counts = {field: len(suggestions)}

    if not selections:
        if is_blank_text(final_text) and not allow_empty_final:
            raise ValueError(f"{field}: final saved text must not be blank")

        return TextFieldAnalysis(
            suggestion_counts=suggestion_counts,
            pick=None,
            match=MatchType.UNASSISTED,
            editing_metrics=None,
            selected_text=None,
            final_text=final_text,
        )

    picked = find_first_picked_suggestion(suggestions, selections)

    if picked is None:
        raise ValueError(
            f"{field}: none of the selected text values occur in the suggestion list"
        )

    suggestion_index, selected_text = picked

    match, editing_metrics = compare_selected_text(
        field=field,
        selected=selected_text,
        final=final_text,
        allow_empty_final=allow_empty_final,
    )

    return TextFieldAnalysis(
        suggestion_counts=suggestion_counts,
        pick=Pick(kind=field, index=suggestion_index),
        match=match,
        editing_metrics=editing_metrics,
        selected_text=selected_text,
        final_text=final_text,
    )


def analyze_lookup_values(
    suggested: object,
    picked: object,
    saved: object,
) -> LookupValueAnalysis:
    """Analyze offered, picked, and saved lookup identifiers.

    Similarity is the Jaccard similarity between the picked and saved sets::

        size(picked & saved) / size(picked | saved)

    When no AI-offered value was picked, the outcome is ``UNASSISTED`` and
    similarity is assigned ``0.0`` as a realized-assistance policy value rather
    than calculated from an empty-set formula, which would be undefined.

    Parameters
    ----------
    suggested
        Identifiers offered by the AI.
    picked
        Identifiers the user selected. Each must have been offered.
    saved
        Identifiers the user ultimately saved.

    Returns
    -------
    LookupValueAnalysis

    Raises
    ------
    ValueError
        If a picked identifier was not among the offered identifiers.
    TypeError
        If any value is not a list of integers, or contains a Boolean.
    """
    offered_set = require_integer_set(suggested, field="suggested lookup values")
    picked_set = require_integer_set(picked, field="picked lookup values")
    saved_set = require_integer_set(saved, field="saved lookup values")

    invalid_picks = picked_set - offered_set

    if invalid_picks:
        raise ValueError(
            "Picked lookup values were not among the offered values: "
            f"{sorted(invalid_picks)}"
        )

    if not picked_set:
        return LookupValueAnalysis(
            offered=offered_set,
            picked=picked_set,
            saved=saved_set,
            match=MatchType.UNASSISTED,
            similarity=0.0,
        )

    if picked_set == saved_set:
        return LookupValueAnalysis(
            offered=offered_set,
            picked=picked_set,
            saved=saved_set,
            match=MatchType.EXACT,
            similarity=1.0,
        )

    union = picked_set | saved_set
    similarity = len(picked_set & saved_set) / len(union)

    return LookupValueAnalysis(
        offered=offered_set,
        picked=picked_set,
        saved=saved_set,
        match=MatchType.EDITED,
        similarity=similarity,
    )


def clean_contact(payload: object) -> dict[str, str]:
    """Validate a contact object, filling absent values with empty strings.

    Parameters
    ----------
    payload
        A contact JSON object, or ``None``.

    Returns
    -------
    dict[str, str]
        One entry per configured contact subfield.

    Raises
    ------
    ValueError
        If the object contains an unrecognized subfield, so that a new form
        field cannot be silently ignored.
    TypeError
        If the payload is not an object, or a subfield value is not a string.
    """
    if payload is None:
        payload = {}

    contact_object = require_object(payload, parameter_name="contact")

    unknown_fields = set(contact_object) - set(CONTACT_FIELDS)

    if unknown_fields:
        raise ValueError(f"Unknown contact fields: {sorted(unknown_fields)}")

    cleaned: dict[str, str] = {}

    for field in CONTACT_FIELDS:
        value = contact_object.get(field)

        if value is None:
            cleaned[field] = ""
        else:
            cleaned[field] = require_string(
                value,
                parameter_name=f"contact.{field}",
            )

    return cleaned


def analyze_contact(
    suggested: object,
    selected: object,
    saved: object,
    *,
    required_fields: frozenset[str],
) -> dict[str, TextFieldAnalysis]:
    """Analyze at most one suggestion per contact subfield.

    Each subfield is analyzed and reported separately, under a prefixed name
    such as ``"contact.email"``.

    Parameters
    ----------
    suggested
        Contact suggestions offered by the AI.
    selected
        Contact values the user selected.
    saved
        Contact values the user saved.
    required_fields
        Unprefixed subfield names whose final value must not be blank.

    Returns
    -------
    dict[str, TextFieldAnalysis]
        One result per configured contact subfield.

    Raises
    ------
    ValueError
        If ``required_fields`` names an unrecognized subfield, if a value was
        selected without a corresponding offer, if a selected value differs from
        the offered suggestion, or if a required final value is blank.
    """
    unknown_required_fields = set(required_fields) - set(CONTACT_FIELDS)

    if unknown_required_fields:
        raise ValueError(
            f"Unknown required contact fields: {sorted(unknown_required_fields)}"
        )

    suggestions = clean_contact(suggested)
    selections = clean_contact(selected)
    final_values = clean_contact(saved)

    results: dict[str, TextFieldAnalysis] = {}

    for contact_field in CONTACT_FIELDS:
        field_name = f"{CONTACT_PREFIX}.{contact_field}"
        allow_empty_final = contact_field not in required_fields

        suggestion_text = suggestions[contact_field]
        selected_text = selections[contact_field]
        final_text = final_values[contact_field]

        # A contact subfield offers at most one suggestion, so the count is
        # either zero or one.
        suggestion_counts = {field_name: int(bool(suggestion_text))}

        if not selected_text:
            if is_blank_text(final_text) and not allow_empty_final:
                raise ValueError(f"{field_name}: final saved text must not be blank")

            results[field_name] = TextFieldAnalysis(
                suggestion_counts=suggestion_counts,
                pick=None,
                match=MatchType.UNASSISTED,
                editing_metrics=None,
                selected_text=None,
                final_text=final_text,
            )
            continue

        if not suggestion_text:
            raise ValueError(
                f"{field_name}: a contact suggestion was selected, "
                "but no suggestion was offered"
            )

        if suggestion_text != selected_text:
            raise ValueError(
                f"{field_name}: selected text does not match the offered suggestion"
            )

        match, editing_metrics = compare_selected_text(
            field=field_name,
            selected=selected_text,
            final=final_text,
            allow_empty_final=allow_empty_final,
        )

        results[field_name] = TextFieldAnalysis(
            suggestion_counts=suggestion_counts,
            pick=Pick(kind=field_name, index=0),
            match=match,
            editing_metrics=editing_metrics,
            selected_text=selected_text,
            final_text=final_text,
        )

    return results


def analyze_compensation(
    suggested: object,
    selected: object,
    final_text: object,
    flag_suggested: object,
    flag_saved: object,
    *,
    radio_required: bool = True,
) -> CompensationAnalysis:
    """Analyze compensation text together with the ``offersCompensation`` flag.

    The saved Boolean determines whether text is required: text is required when
    the saved value is ``True`` and may be blank when it is ``False``.

    Two cases worth noting. If a selected suggestion is later cleared while the
    saved flag is ``False``, the text outcome is ``REMOVED`` and normalized
    metrics are left undefined. If no suggestion was selected but the user set
    the flag to ``True`` and supplied text, the outcome is ``UNASSISTED``.

    Parameters
    ----------
    suggested
        Categorized compensation text suggestions.
    selected
        Categorized compensation text selections. At most one across all
        categories.
    final_text
        The compensation text the user saved.
    flag_suggested
        The AI-recommended ``offersCompensation`` value.
    flag_saved
        The ``offersCompensation`` value the user saved.
    radio_required
        Whether a saved Boolean is mandatory.

    Returns
    -------
    CompensationAnalysis

    Raises
    ------
    ValueError
        If more than one suggestion was selected, if a required saved Boolean is
        absent, if a selected value does not occur among the offered
        suggestions, or if text is required but blank.
    TypeError
        If any container or flag has the wrong type.
    """
    suggested_object = (
        {}
        if suggested is None
        else require_object(suggested, parameter_name="suggested compensation")
    )
    selected_object = (
        {}
        if selected is None
        else require_object(selected, parameter_name="selected compensation")
    )

    if final_text is None:
        saved_text = ""
    else:
        saved_text = require_string(
            final_text,
            parameter_name="final compensation text",
        )

    suggested_flag = require_optional_boolean(
        flag_suggested,
        parameter_name="flag_suggested",
    )
    saved_flag = require_optional_boolean(
        flag_saved,
        parameter_name="flag_saved",
    )

    if radio_required and saved_flag is None:
        raise ValueError("offersCompensation must be saved as True or False")

    compensation_text_required = saved_flag is True
    allow_empty_final = not compensation_text_required

    suggestions_by_kind = {
        kind: require_string_list(
            suggested_object.get(kind),
            parameter_name=f"suggested[{kind!r}]",
        )
        for kind in COMPENSATION_KINDS
    }

    selections_by_kind = {
        kind: require_string_list(
            selected_object.get(kind),
            parameter_name=f"selected[{kind!r}]",
        )
        for kind in COMPENSATION_KINDS
    }

    selected_entry_count = sum(
        len(selections) for selections in selections_by_kind.values()
    )

    if selected_entry_count > 1:
        raise ValueError("At most one compensation text suggestion may be selected")

    suggestion_counts = {
        kind: len(values) for kind, values in suggestions_by_kind.items()
    }

    for kind in COMPENSATION_KINDS:
        suggestions_for_kind = suggestions_by_kind[kind]
        selections_for_kind = selections_by_kind[kind]

        if not selections_for_kind:
            continue

        picked = find_first_picked_suggestion(
            suggestions_for_kind,
            selections_for_kind,
        )

        if picked is None:
            raise ValueError(
                f"{kind}: none of the selected text values occur in the suggestion list"
            )

        suggestion_index, selected_text = picked

        match, editing_metrics = compare_selected_text(
            field=kind,
            selected=selected_text,
            final=saved_text,
            allow_empty_final=allow_empty_final,
        )

        return CompensationAnalysis(
            suggestion_counts=suggestion_counts,
            pick=Pick(kind=kind, index=suggestion_index),
            match=match,
            editing_metrics=editing_metrics,
            selected_text=selected_text,
            final_text=saved_text,
            flag_suggested=suggested_flag,
            flag_saved=saved_flag,
        )

    # No text suggestion was selected. When the saved flag is True the user must
    # nevertheless have supplied compensation text.
    if compensation_text_required and is_blank_text(saved_text):
        raise ValueError(
            "compensation: final text is required when offersCompensation is True"
        )

    # A nonblank final value with no selection is valid but unassisted. This
    # covers an AI recommendation of False followed by the user setting True and
    # writing text independently.
    return CompensationAnalysis(
        suggestion_counts=suggestion_counts,
        pick=None,
        match=MatchType.UNASSISTED,
        editing_metrics=None,
        selected_text=None,
        final_text=saved_text,
        flag_suggested=suggested_flag,
        flag_saved=saved_flag,
    )


def analyze_objects(
    suggested_object: object,
    selected_object: object,
    final_object: object,
) -> dict[str, AnalysisResult]:
    """Analyze every configured field in one audit record.

    Requiredness is sourced from three places: ``FIELD_SPECS`` for ordinary text
    fields, ``REQUIRED_CONTACT_FIELDS`` for contact subfields, and the saved
    ``offersCompensation`` value for compensation text.

    Parameters
    ----------
    suggested_object
        Decoded ``LLM_SUGGESTIONS`` object.
    selected_object
        Decoded ``SELECTED_SUGGESTIONS`` object.
    final_object
        Decoded ``FINAL_SUBMISSION`` object.

    Returns
    -------
    dict[str, AnalysisResult]
        One result per analyzed field. Contact expands into four prefixed
        entries. ``offersCompensation`` produces no entry of its own, because it
        is reported within the compensation result.

    Raises
    ------
    ValueError
        If any object contains a field absent from ``FIELD_SPECS``, so that a new
        form field cannot be silently ignored, or if any field-level rule is
        violated.
    TypeError
        If any of the three inputs is not a JSON object.
    """
    suggested = require_object(
        suggested_object,
        parameter_name="suggested_object",
    )
    selected = require_object(
        selected_object,
        parameter_name="selected_object",
    )
    final = require_object(final_object, parameter_name="final_object")

    configured_fields = set(FIELD_SPECS)

    for parameter_name, value in (
        ("suggested_object", suggested),
        ("selected_object", selected),
        ("final_object", final),
    ):
        unknown_fields = set(value) - configured_fields

        if unknown_fields:
            raise ValueError(
                f"Unknown fields in {parameter_name}; "
                f"add them to FIELD_SPECS: {sorted(unknown_fields)}"
            )

    results: dict[str, AnalysisResult] = {}

    for field_name, field_spec in FIELD_SPECS.items():
        field_kind = field_spec.kind

        # MERGED fields are reported inside another field's result rather than
        # separately. offersCompensation is reported within compensation.
        if field_kind is FieldKind.MERGED:
            continue

        suggested_value = suggested.get(field_name)
        selected_value = selected.get(field_name)
        final_value = final.get(field_name)

        match field_kind:
            case FieldKind.TEXT:
                if field_spec.text_required is None:
                    raise ValueError(
                        f"{field_name}: TEXT fields must declare text_required"
                    )

                results[field_name] = analyze_text_field(
                    field=field_name,
                    suggested=suggested_value,
                    selected=selected_value,
                    final=final_value,
                    allow_empty_final=not field_spec.text_required,
                )

            case FieldKind.LOOKUP:
                results[field_name] = analyze_lookup_values(
                    suggested=suggested_value,
                    picked=selected_value,
                    saved=final_value,
                )

            case FieldKind.CONTACT:
                results.update(
                    analyze_contact(
                        suggested=suggested_value,
                        selected=selected_value,
                        saved=final_value,
                        required_fields=REQUIRED_CONTACT_FIELDS,
                    )
                )

            case FieldKind.COMPENSATION:
                results[field_name] = analyze_compensation(
                    suggested=suggested_value,
                    selected=selected_value,
                    final_text=final_value,
                    flag_suggested=suggested.get("offersCompensation"),
                    flag_saved=final.get("offersCompensation"),
                    radio_required=True,
                )

            case _:
                raise AssertionError(f"Unhandled field kind: {field_kind}")

    return results
