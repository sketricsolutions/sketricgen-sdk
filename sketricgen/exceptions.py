"""
SketricGen SDK Exceptions

Custom exception types for handling various error scenarios.
"""

from typing import Any, Optional


class SketricGenError(Exception):
    """Base exception for all SketricGen SDK errors."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


class SketricGenAPIError(SketricGenError):
    """Raised when API returns an error response."""

    def __init__(
        self,
        message: str,
        status_code: int,
        response_body: Optional[dict[str, Any]] = None,
    ) -> None:
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message)

    def __str__(self) -> str:
        return f"[{self.status_code}] {self.message}"


class SketricGenValidationError(SketricGenError):
    """Raised when request validation fails."""

    pass


class SketricGenNetworkError(SketricGenError):
    """Raised when network request fails."""

    pass


class SketricGenTimeoutError(SketricGenError):
    """Raised when request times out."""

    pass


class SketricGenUploadError(SketricGenError):
    """Raised when file upload fails."""

    pass


class SketricGenFileSizeError(SketricGenError):
    """Raised when file exceeds size limit."""

    def __init__(self, message: str, file_size: int, max_size: int) -> None:
        self.file_size = file_size
        self.max_size = max_size
        super().__init__(message)


class SketricGenContentTypeError(SketricGenError):
    """Raised when content type is not allowed."""

    def __init__(
        self, message: str, content_type: str, allowed_types: list[str]
    ) -> None:
        self.content_type = content_type
        self.allowed_types = allowed_types
        super().__init__(message)


class SketricGenAuthenticationError(SketricGenAPIError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message=message, status_code=401)


class SketricGenAdminError(SketricGenError):
    """Raised when the control-plane Admin API returns an ``{error, code}`` body.

    Carries the HTTP ``status_code`` and the machine-readable ``code`` slug
    (e.g. ``project_scope_mismatch``, ``agent_limit_reached``) so callers can
    branch on the failure kind instead of parsing message strings.
    """

    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        super().__init__(message)

    def __str__(self) -> str:
        return f"[{self.status_code}] {self.code}: {self.message}"


class SketricGenJobError(SketricGenError):
    """Raised when a brand-agent provisioning job ends in a failed state."""

    def __init__(
        self,
        message: str,
        job_id: str,
        status: str,
        error_summary: Optional[str] = None,
    ) -> None:
        self.job_id = job_id
        self.status = status
        self.error_summary = error_summary
        super().__init__(message)
