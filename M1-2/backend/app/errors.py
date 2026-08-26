class DomainError(Exception):
    """Base exception for expected application errors."""


class ConfigurationError(DomainError):
    """Raised when application configuration is invalid."""


class DuplicateDateError(DomainError):
    """Raised when a weight record already exists for a date."""


class InvalidPeriodError(DomainError):
    """Raised when a start date is after an end date."""


class RecordNotFoundError(DomainError):
    """Raised when a requested record does not exist."""
