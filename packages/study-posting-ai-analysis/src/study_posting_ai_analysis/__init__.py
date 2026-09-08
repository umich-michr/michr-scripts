"""Analysis of AI-assisted study-posting form values.

Given the suggestions an AI offered, the values a user selected, and the final
values saved, this package applies study-posting business rules and returns one
structured analysis result per field.

Technical text post-editing calculations are provided by the separate
``michr-text-post-editing`` package.

This package performs no database, filesystem, reporting, or logging I/O.
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
from study_posting_ai_analysis.models import (
    AnalysisResult,
    CompensationAnalysis,
    FieldKind,
    FieldSpec,
    LookupValueAnalysis,
    MatchType,
    Pick,
    Suggestions,
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
    "CompensationAnalysis",
    "FieldKind",
    "FieldSpec",
    "InputParseError",
    "LookupValueAnalysis",
    "MatchType",
    "Pick",
    "Suggestions",
    "TextFieldAnalysis",
    "__version__",
    "analyze_compensation",
    "analyze_contact",
    "analyze_lookup_values",
    "analyze_objects",
    "analyze_text_field",
    "compare_selected_text",
    "flatten_analysis_results",
    "parse_analysis_inputs",
    "parse_json_object",
]
