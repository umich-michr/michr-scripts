"""Reusable technical post-editing metrics.

This package compares an AI-generated suggestion with final human-edited text.
It performs pure calculations only: no database, filesystem, pandas, logging,
or application-specific business rules.

The metric API will be added incrementally while preserving the verified
behavior of ``study-posting-ai-analysis``.
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
