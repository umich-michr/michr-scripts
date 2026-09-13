"""Exceptions raised by study-posting audit exploration."""


class AuditExplorationError(Exception):
    """Base class for expected exploration-program failures."""


class ExplorationConfigurationError(AuditExplorationError):
    """Exploration configuration is invalid or inconsistent."""


class ExplorationInputError(AuditExplorationError):
    """An input file cannot be opened, parsed, or converted."""


class ExplorationValidationError(AuditExplorationError):
    """Loaded report inputs violate the exploration contract."""
