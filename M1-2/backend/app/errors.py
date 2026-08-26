class DomainError(Exception):
    """Base exception for expected application errors."""


class ConfigurationError(DomainError):
    """Raised when application configuration is invalid."""
