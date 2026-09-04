"""Metrics for AI-assisted study posting authoring audit records.

Measures how much AI-generated text assistance survived into final
human-authored content in the eResearch study-posting form.

These metrics quantify technical post-editing effort. They do not measure time
saved, keystrokes avoided, cognitive effort, or user satisfaction. See
docs/analysis-specification.md section 16.

The public surface is re-exported here so callers need not know the internal
module layout::

    from study_posting_ai_analysis import MatchType, analyze_objects
"""

from study_posting_ai_analysis.models import (
    AnalysisResult,
    AuditRecord,
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

__version__ = "0.1.0"

__all__ = [
    "AnalysisResult",
    "AuditRecord",
    "CharacterResult",
    "CompensationAnalysis",
    "FieldKind",
    "FieldSpec",
    "LookupValueAnalysis",
    "MatchType",
    "Pick",
    "SoftWordResult",
    "SuggestionEditingResult",
    "Suggestions",
    "TerResult",
    "TextFieldAnalysis",
    "__version__",
]
