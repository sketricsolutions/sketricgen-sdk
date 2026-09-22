"""
SketricGen SDK

Python SDK for interacting with the SketricGen runtime and Admin APIs.

Example:
    ```python
    from sketricgen import SketricGenClient

    # Initialize client
    client = SketricGenClient(api_key="your-api-key")

    # Run workflow
    response = await client.run_workflow(
        agent_id="agent-123",
        user_input="Hello, how are you?"
    )
    print(response.response)

    # Run workflow with file attachments
    response = await client.run_workflow(
        agent_id="agent-123",
        user_input="Analyze this document",
        file_paths=["/path/to/document.pdf"]
    )
    print(response.response)
    ```
"""

from sketricgen.client import SketricGenClient
from sketricgen.config import SketricGenConfig
from sketricgen.exceptions import (
    SketricGenAdminError,
    SketricGenAPIError,
    SketricGenAuthenticationError,
    SketricGenContentTypeError,
    SketricGenError,
    SketricGenFileSizeError,
    SketricGenJobError,
    SketricGenNetworkError,
    SketricGenTimeoutError,
    SketricGenUploadError,
    SketricGenValidationError,
)
from sketricgen.models.requests import HitlDecision, HitlResume
from sketricgen.models.responses import (
    ChatResponse,
    HitlActionRequest,
    HitlRequest,
    HitlReviewConfig,
    StreamEvent,
)

__version__ = "0.3.0"

__all__ = [
    # Clients
    "SketricGenClient",
    # Config
    "SketricGenConfig",
    # Exceptions
    "SketricGenError",
    "SketricGenAPIError",
    "SketricGenAuthenticationError",
    "SketricGenAdminError",
    "SketricGenJobError",
    "SketricGenValidationError",
    "SketricGenNetworkError",
    "SketricGenTimeoutError",
    "SketricGenUploadError",
    "SketricGenFileSizeError",
    "SketricGenContentTypeError",
    # Response Models
    "ChatResponse",
    "HitlDecision",
    "HitlResume",
    "HitlActionRequest",
    "HitlRequest",
    "HitlReviewConfig",
    "StreamEvent",
]
