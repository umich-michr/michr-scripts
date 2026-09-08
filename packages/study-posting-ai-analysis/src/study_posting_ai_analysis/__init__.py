"""Metrics for AI-assisted study posting authoring.

Measures how much AI-generated text assistance survived into final
human-authored content in the eResearch study-posting form.

The contract is three inputs and one output: AI suggestions, user selections,
and final saved values in; per-field analysis results out. This library performs
no I/O and knows nothing about databases, files, or audit-table schemas.

These metrics quantify technical post-editing effort. They do not measure time
saved, keystrokes avoided, cognitive effort, or user satisfaction. See
docs/analysis-specification.md section 16.

Examples
--------
>>> from study_posting_ai_analysis import (
...     analyze_objects,
...     flatten_analysis_results,
...     parse_analysis_inputs,
... )
>>> suggested, selected, final = parse_analysis_inputs(
...     suggestions_json, selections_json, final_json
... )
>>> results = analyze_objects(suggested, selected, final)
>>> rows = flatten_analysis_results(results, record_id="audit-1234")
"""

from study_posting_ai_analysis.errors import InputParseError
from study_posting_ai_analysis.field_analysis import (
    analyze_compensation,
    analyze_contact,
    analyze_lookup_values,
    analyze_objects,
    analyze_text_field,
    compare_selected_text,
)
from study_posting_ai_analysis.field_specs import (
    COMPENSATION_KINDS,
    CONTACT_FIELDS,
    FIELD_SPECS,
    REQUIRED_CONTACT_FIELDS,
)
from study_posting_ai_analysis.flattening import (
    FLATTENED_COLUMNS,
    flatten_analysis_results,
)
from study_posting_ai_analysis.metrics import (
    analyze_selected_suggestion,
    calculate_character_metrics,
    calculate_soft_word_metrics,
    calculate_ter_metrics,
)
from study_posting_ai_analysis.models import (
    AnalysisResult,
    CharacterResult,
    CompensationAnalysis,
    FieldKind,
    FieldSpec,
    LookupValueAnalysis,
    MatchType,
    Pick,
    SoftWordResult,
    SuggestionEditingResult,
    Suggestions,
    TerResult,
    TextFieldAnalysis,
)
from study_posting_ai_analysis.parsing import (
    parse_analysis_inputs,
    parse_json_object,
)

__version__ = "0.1.0"

__all__ = [
    "COMPENSATION_KINDS",
    "CONTACT_FIELDS",
    "FIELD_SPECS",
    "FLATTENED_COLUMNS",
    "REQUIRED_CONTACT_FIELDS",
    "AnalysisResult",
    "CharacterResult",
    "CompensationAnalysis",
    "FieldKind",
    "FieldSpec",
    "InputParseError",
    "LookupValueAnalysis",
    "MatchType",
    "Pick",
    "SoftWordResult",
    "SuggestionEditingResult",
    "Suggestions",
    "TerResult",
    "TextFieldAnalysis",
    "__version__",
    "analyze_compensation",
    "analyze_contact",
    "analyze_lookup_values",
    "analyze_objects",
    "analyze_selected_suggestion",
    "analyze_text_field",
    "calculate_character_metrics",
    "calculate_soft_word_metrics",
    "calculate_ter_metrics",
    "compare_selected_text",
    "flatten_analysis_results",
    "parse_analysis_inputs",
    "parse_json_object",
]
