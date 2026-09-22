"""
SketricGen SDK Configuration

Handles configuration management for the SDK.
"""

import os
from dataclasses import dataclass
from typing import Optional

# Default API endpoints
DEFAULT_BASE_URL = "https://chat-v2.sketricgen.ai"
DEFAULT_WORKFLOW_ENDPOINT = "/api/v1/run-workflow"
DEFAULT_UPLOAD_INIT_ENDPOINT = (
    "https://v9xof9ohlg.execute-api.us-east-1.amazonaws.com/dev/publicAssetsUploadInit"
)
DEFAULT_UPLOAD_COMPLETE_ENDPOINT = "https://v9xof9ohlg.execute-api.us-east-1.amazonaws.com/dev/publicAssetsUploadComplete"

# Timeouts
DEFAULT_TIMEOUT = 300  # seconds
DEFAULT_UPLOAD_TIMEOUT = 300  # 5 minutes for large files

# Retry settings
DEFAULT_MAX_RETRIES = 3

# Upload limits
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB

# Allowed content types for upload
ALLOWED_CONTENT_TYPES = frozenset(
    {
        "image/jpeg",
        "image/webp",
        "image/png",
        "application/pdf",
        "image/gif",
        "text/csv",
        "application/csv",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/json",
        "text/html",
        "text/markdown",
        "text/plain",
        "text/xml",
        "application/xml",
        "text/yaml",
        "application/x-yaml",
        "application/yaml",
        "text/x-yaml",
        "text/javascript",
        "application/javascript",
        "application/typescript",
        "text/typescript",
        "text/css",
        "text/x-python",
        "text/x-script.python",
        "application/x-httpd-php",
        "text/x-java-source",
        "text/x-java",
        "text/x-c",
        "text/x-csrc",
        "text/x-c++",
        "text/x-c++src",
        "application/x-csh",
        "application/x-sh",
        "text/x-shellscript",
        "application/x-ruby",
        "text/x-ruby",
        "text/x-rust",
        "text/x-go",
        "text/x-scala",
        "text/x-swift",
        "text/x-csharp",
        "application/sql",
        "text/sql",
        "application/x-sql",
        "text/x-sql",
    }
)

EXTENSION_TO_CONTENT_TYPE = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".pdf": "application/pdf",
    ".csv": "text/csv",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".json": "application/json",
    ".html": "text/html",
    ".htm": "text/html",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".txt": "text/plain",
    ".yaml": "text/yaml",
    ".yml": "text/yaml",
    ".xml": "application/xml",
    ".ts": "application/typescript",
    ".tsx": "application/typescript",
    ".mts": "application/typescript",
    ".cts": "application/typescript",
    ".js": "text/javascript",
    ".jsx": "text/javascript",
    ".mjs": "text/javascript",
    ".cjs": "text/javascript",
    ".css": "text/css",
    ".scss": "text/css",
    ".sass": "text/css",
    ".less": "text/css",
    ".vue": "text/plain",
    ".svelte": "text/plain",
    ".py": "text/x-python",
    ".pyw": "text/x-python",
    ".pyi": "text/x-python",
    ".rb": "application/x-ruby",
    ".php": "application/x-httpd-php",
    ".java": "text/x-java-source",
    ".kt": "text/plain",
    ".kts": "text/plain",
    ".go": "text/x-go",
    ".rs": "text/x-rust",
    ".swift": "text/x-swift",
    ".scala": "text/x-scala",
    ".sc": "text/x-scala",
    ".c": "text/x-c",
    ".h": "text/x-c",
    ".cc": "text/x-c++",
    ".cpp": "text/x-c++",
    ".cxx": "text/x-c++",
    ".hpp": "text/x-c++",
    ".cs": "text/x-csharp",
    ".fs": "text/plain",
    ".fsx": "text/plain",
    ".sql": "application/sql",
    ".sh": "application/x-sh",
    ".bash": "application/x-sh",
    ".zsh": "application/x-sh",
    ".ps1": "text/plain",
    ".bat": "text/plain",
    ".cmd": "text/plain",
    ".r": "text/plain",
    ".dart": "text/plain",
    ".ex": "text/plain",
    ".exs": "text/plain",
    ".erl": "text/plain",
    ".hrl": "text/plain",
    ".clj": "text/plain",
    ".cljs": "text/plain",
    ".lua": "text/plain",
    ".pl": "text/plain",
    ".pm": "text/plain",
    ".rkt": "text/plain",
    ".zig": "text/plain",
    ".nim": "text/plain",
    ".odin": "text/plain",
    ".toml": "text/plain",
    ".ini": "text/plain",
    ".cfg": "text/plain",
    ".conf": "text/plain",
    ".properties": "text/plain",
    ".env": "text/plain",
    ".gitignore": "text/plain",
    ".dockerignore": "text/plain",
    ".gradle": "text/plain",
    ".cmake": "text/plain",
    ".mk": "text/plain",
    ".makefile": "text/plain",
    ".vim": "text/plain",
}


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
            SKETRICGEN_UPLOAD_TIMEOUT: Upload timeout in seconds (optional)
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
                "API key is required. Set SKETRICGEN_API_KEY environment "
                "variable or provide api_key parameter."
            )

        return cls(
            api_key=resolved_api_key,
            timeout=int(os.getenv("SKETRICGEN_TIMEOUT", str(DEFAULT_TIMEOUT))),
            upload_timeout=int(
                os.getenv("SKETRICGEN_UPLOAD_TIMEOUT", str(DEFAULT_UPLOAD_TIMEOUT))
            ),
            max_retries=int(
                os.getenv("SKETRICGEN_MAX_RETRIES", str(DEFAULT_MAX_RETRIES))
            ),
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
