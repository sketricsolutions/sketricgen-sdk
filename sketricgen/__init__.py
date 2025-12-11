"""
SketricGen SDK

Python SDK for interacting with the SketricGen Chat Server API.

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
    SketricGenAPIError,
    SketricGenAuthenticationError,
    SketricGenContentTypeError,
    SketricGenError,
    SketricGenFileSizeError,
    SketricGenNetworkError,
    SketricGenTimeoutError,
    SketricGenUploadError,
    SketricGenValidationError,
)
from sketricgen.models.responses import (
    ChatResponse,
    StreamEvent,
)

__version__ = "0.1.0"

__all__ = [
    # Client
    "SketricGenClient",
    # Config
    "SketricGenConfig",
    # Exceptions
    "SketricGenError",
    "SketricGenAPIError",
    "SketricGenAuthenticationError",
    "SketricGenValidationError",
    "SketricGenNetworkError",
    "SketricGenTimeoutError",
    "SketricGenUploadError",
    "SketricGenFileSizeError",
    "SketricGenContentTypeError",
    # Response Models
    "ChatResponse",
    "StreamEvent",
]
