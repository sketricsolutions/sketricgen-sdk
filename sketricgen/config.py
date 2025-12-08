"""
SketricGen SDK Configuration

Handles configuration management for the SDK.
"""

import os
from dataclasses import dataclass
from typing import Optional


# Default API endpoints
DEFAULT_BASE_URL = "https://dev-chat.sketricgen.ai"
DEFAULT_WORKFLOW_ENDPOINT = "/api/v1/run-workflow"
DEFAULT_UPLOAD_INIT_ENDPOINT = "https://0uwfaq2dke.execute-api.us-east-1.amazonaws.com/dev/publicAssetsUploadInit"
DEFAULT_UPLOAD_COMPLETE_ENDPOINT = "https://0uwfaq2dke.execute-api.us-east-1.amazonaws.com/dev/publicAssetsUploadComplete"

# Timeouts
DEFAULT_TIMEOUT = 30  # seconds
DEFAULT_UPLOAD_TIMEOUT = 300  # 5 minutes for large files

# Retry settings
DEFAULT_MAX_RETRIES = 3

# Upload limits
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB

# Allowed content types for upload
ALLOWED_CONTENT_TYPES = frozenset({
    "image/jpeg",
    "image/webp",
    "image/png",
    "application/pdf",
    "image/gif",
})


@dataclass
class SketricGenConfig:
    """Configuration for SketricGen SDK."""

    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout: int = DEFAULT_TIMEOUT
    upload_timeout: int = DEFAULT_UPLOAD_TIMEOUT
    max_retries: int = DEFAULT_MAX_RETRIES
    workflow_endpoint: str = DEFAULT_WORKFLOW_ENDPOINT
    upload_init_endpoint: str = DEFAULT_UPLOAD_INIT_ENDPOINT
    upload_complete_endpoint: str = DEFAULT_UPLOAD_COMPLETE_ENDPOINT

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if not self.api_key:
            raise ValueError("API key is required")
        # Normalize base URL
        self.base_url = self.base_url.rstrip("/")

    @classmethod
    def from_env(
        cls,
        api_key: Optional[str] = None,
    ) -> "SketricGenConfig":
        """
        Load configuration from environment variables.

        Environment Variables:
            SKETRICGEN_API_KEY: API key (required if not provided)
            SKETRICGEN_TIMEOUT: Request timeout in seconds (optional)
            SKETRICGEN_MAX_RETRIES: Maximum retry attempts (optional)

        Args:
            api_key: Override API key from environment

        Returns:
            SketricGenConfig instance

        Raises:
            ValueError: If API key is not provided or found in environment
        """
        resolved_api_key = api_key or os.getenv("SKETRICGEN_API_KEY")
        if not resolved_api_key:
            raise ValueError(
                "API key is required. Set SKETRICGEN_API_KEY environment variable "
                "or provide api_key parameter."
            )

        return cls(
            api_key=resolved_api_key,
            timeout=int(os.getenv("SKETRICGEN_TIMEOUT", str(DEFAULT_TIMEOUT))),
            max_retries=int(os.getenv("SKETRICGEN_MAX_RETRIES", str(DEFAULT_MAX_RETRIES))),
        )

    def get_workflow_url(self) -> str:
        """Get full URL for workflow endpoint."""
        return f"{self.base_url}{self.workflow_endpoint}"

    def get_upload_init_url(self) -> str:
        """Get full URL for upload init endpoint."""
        return self.upload_init_endpoint

    def get_upload_complete_url(self) -> str:
        """Get full URL for upload complete endpoint."""
        return self.upload_complete_endpoint
