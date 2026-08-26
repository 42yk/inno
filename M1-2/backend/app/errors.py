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


class UnknownToolError(DomainError):
    """Raised when a model requests a tool outside the allow-list."""


class InvalidToolArgumentsError(DomainError):
    """Raised when model-provided tool arguments fail validation."""


class AIProviderError(DomainError):
    """Raised when an AI response cannot be generated safely."""


class ToolCallLimitError(DomainError):
    """Raised when a model requests too many tools for one chat turn."""


class DataStoreError(DomainError):
    """Raised when persisted application data cannot be processed."""
