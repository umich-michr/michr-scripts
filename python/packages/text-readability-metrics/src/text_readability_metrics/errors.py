"""Exceptions raised by text readability analysis."""


class ReadabilityError(ValueError):
    """Base exception for readability input and result failures."""


class InvalidReadabilityTextError(ReadabilityError):
    """Raised when readability input is not nonblank text."""


class InvalidReadabilityResultError(ReadabilityError):
    """Raised when a readability backend returns an invalid result."""
