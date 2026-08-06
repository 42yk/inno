"""애플리케이션 경계에서 공유하는 안전한 프로젝트 오류를 정의한다."""


class ProjectError(Exception):
    """An error with a stable, safe cause code for users and logs."""

    # 안전한 사용자 메시지와 안정적인 오류 코드를 보관한다.
    def __init__(self, message: str, code: str) -> None:
        self.message = message
        self.code = code
        super().__init__(f"{code}: {message}")


class ConfigurationError(ProjectError):
    """Raised when non-secret configuration cannot be safely loaded."""


class ValidationError(ProjectError):
    """Raised when a value violates a domain validation contract."""


class InputFileError(ProjectError):
    """Raised by file readers for an unusable input file."""


class PersistenceError(ProjectError):
    """Raised by repositories after a failed persistence operation."""


class AIServiceError(ProjectError):
    """Raised for a Gemini service failure that is safe to report."""


class AIResponseError(AIServiceError):
    """Raised when a Gemini response violates the expected schema."""


class OutputWriteError(ProjectError):
    """Raised when an output artifact cannot be written."""


class NotFoundError(ProjectError):
    """Raised when a requested persisted entity or scope does not exist."""


class StaleInsightError(ProjectError):
    """Raised when a dashboard scope has no current insight extraction."""
