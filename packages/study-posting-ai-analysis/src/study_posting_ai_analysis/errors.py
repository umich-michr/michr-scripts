"""Exception types raised by this library.

The library raises only ``ValueError`` and ``TypeError`` for invalid input, so
callers need no special handling to use it idiomatically.

``InputParseError`` derives from ``ValueError`` so that ``except ValueError``
continues to work, while also being catchable specifically by a caller that
wants to distinguish a malformed JSON payload from a rule violation.

Repository, configuration, and record-level error types belong to the programs
that consume this library, not here.
"""


class InputParseError(ValueError):
    """A JSON input could not be decoded into an object."""
