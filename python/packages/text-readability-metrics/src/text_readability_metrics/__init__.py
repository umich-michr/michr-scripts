"""Generic semantic readability metrics for English text."""

from text_readability_metrics.errors import (
    InvalidReadabilityResultError,
    InvalidReadabilityTextError,
    ReadabilityError,
)
from text_readability_metrics.metrics import analyze_readability
from text_readability_metrics.models import ReadabilityResult

__version__ = "0.1.0"

__all__ = [
    "InvalidReadabilityResultError",
    "InvalidReadabilityTextError",
    "ReadabilityError",
    "ReadabilityResult",
    "__version__",
    "analyze_readability",
]
