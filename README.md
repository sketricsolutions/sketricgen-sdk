# SketricGen SDK

Python SDK for the SketricGen Chat Server API.

## Installation

```bash
pip install sketricgen
```

Or install from source:

```bash
cd sketric_sdk
pip install -e .
```

## Quick Start

```python
from sketricgen import SketricGenClient

# Initialize client
client = SketricGenClient(api_key="your-api-key")

# Run a workflow
response = await client.run_workflow(
    agent_id="agent-123",
    user_input="Hello, how are you?",
)
print(response.response)
```

## Features

- **Run Workflow**: Execute chat/workflow requests with agents
- **Streaming**: Real-time streaming responses using Server-Sent Events
- **Asset Upload**: Upload files (images, PDFs) to use in workflows
- **Async & Sync**: Both async and synchronous API support
- **Type Safety**: Full type hints for IDE support
- **Error Handling**: Comprehensive custom exception types

## Usage Examples

### Non-Streaming Workflow

```python
from sketricgen import SketricGenClient

client = SketricGenClient(api_key="your-api-key")

# Async
response = await client.run_workflow(
    agent_id="agent-123",
    user_input="What is the weather like today?",
    conversation_id="conv-456",  # Optional: resume conversation
)
print(f"Response: {response.response}")
print(f"Conversation ID: {response.conversation_id}")

# Sync
response = client.run_workflow_sync(
    agent_id="agent-123",
    user_input="Hello!",
)
```

### Streaming Workflow

```python
from sketricgen import SketricGenClient

client = SketricGenClient(api_key="your-api-key")

# Async streaming
async for event in await client.run_workflow(
    agent_id="agent-123",
    user_input="Tell me a story",
    stream=True,
):
    print(event.data, end="", flush=True)

# Sync streaming
for event in client.run_workflow_sync(
    agent_id="agent-123",
    user_input="Tell me a story",
    stream=True,
):
    print(event.data, end="", flush=True)
```

### Upload Asset

Upload files to use in your workflows. The SDK handles the entire upload process internally.

```python
from sketricgen import SketricGenClient

client = SketricGenClient(api_key="your-api-key")

# Upload from file path (async)
response = await client.upload_asset(
    agent_id="agent-123",
    file_path="/path/to/document.pdf",
)
print(f"File ID: {response.file_id}")
print(f"Access URL: {response.url}")

# Upload from file path (sync)
response = client.upload_asset_sync(
    agent_id="agent-123",
    file_path="/path/to/image.png",
)
```

### Upload from Bytes

```python
from sketricgen import SketricGenClient

client = SketricGenClient(api_key="your-api-key")

# Upload from bytes (file_name is required)
image_bytes = open("image.png", "rb").read()
response = await client.upload_asset(
    agent_id="agent-123",
    file_path=image_bytes,
    file_name="image.png",
)
print(f"Uploaded: {response.file_id}")
```

### Upload from File-like Object

```python
from sketricgen import SketricGenClient

client = SketricGenClient(api_key="your-api-key")

# Upload from file object
with open("document.pdf", "rb") as f:
    response = await client.upload_asset(
        agent_id="agent-123",
        file_path=f,
        file_name="document.pdf",
    )
```

### Using Uploaded Assets in Workflows

```python
from sketricgen import SketricGenClient

client = SketricGenClient(api_key="your-api-key")

# Upload an asset
upload = await client.upload_asset(
    agent_id="agent-123",
    file_path="/path/to/document.pdf",
)

# Use in workflow
response = await client.run_workflow(
    agent_id="agent-123",
    user_input="Please analyze this document",
    assets=[upload.file_id],  # Include the uploaded file
)
print(response.response)
```

### Error Handling

```python
from sketricgen import (
    SketricGenClient,
    SketricGenAPIError,
    SketricGenAuthenticationError,
    SketricGenValidationError,
    SketricGenNetworkError,
    SketricGenFileSizeError,
    SketricGenContentTypeError,
)

client = SketricGenClient(api_key="your-api-key")

try:
    response = await client.upload_asset(
        agent_id="agent-123",
        file_path="/path/to/file.pdf",
    )
except SketricGenAuthenticationError as e:
    print(f"Authentication failed: {e}")
except SketricGenFileSizeError as e:
    print(f"File too large: {e}")
    print(f"Max size: {e.max_size} bytes")
except SketricGenContentTypeError as e:
    print(f"Unsupported file type: {e}")
    print(f"Allowed types: {e.allowed_types}")
except SketricGenValidationError as e:
    print(f"Validation error: {e}")
except SketricGenAPIError as e:
    print(f"API error ({e.status_code}): {e}")
except SketricGenNetworkError as e:
    print(f"Network error: {e}")
```

### Configuration

```python
from sketricgen import SketricGenClient

# Direct configuration
client = SketricGenClient(
    api_key="your-api-key",
    base_url="https://api.sketricgen.com",
    timeout=30,
    upload_timeout=300,  # 5 minutes for large files
    max_retries=3,
)

# From environment variables
# Set SKETRICGEN_API_KEY, SKETRICGEN_BASE_URL (optional)
client = SketricGenClient.from_env()
```

## Supported File Types

For asset uploads, the following content types are supported:

- `image/jpeg`
- `image/png`
- `image/webp`
- `image/gif`
- `application/pdf`

Maximum file size: **20 MB**

## API Reference

### SketricGenClient

#### `run_workflow(agent_id, user_input, conversation_id?, contact_id?, assets?, stream?)`

Execute a workflow/chat request.

**Parameters:**
- `agent_id` (str): Agent ID to chat with
- `user_input` (str): User message (max 10000 characters)
- `conversation_id` (str, optional): Conversation ID for resuming
- `contact_id` (str, optional): External contact ID
- `assets` (list[str], optional): List of asset file IDs
- `stream` (bool, optional): Whether to stream the response

**Returns:** `ChatResponse` or `AsyncIterator[StreamEvent]` if streaming

#### `upload_asset(agent_id, file_path, file_name?, content_type?)`

Upload a file to use in workflows.

**Parameters:**
- `agent_id` (str): Agent ID associated with the upload
- `file_path` (str | bytes | BinaryIO): File path, bytes, or file-like object
- `file_name` (str, optional): File name (required for bytes/file-like objects)
- `content_type` (str, optional): MIME type override

**Returns:** `UploadResponse` with file details and access URL

### Response Models

#### `ChatResponse`
- `agent_id`: Workflow ID
- `user_id`: User identifier
- `conversation_id`: Conversation ID
- `response`: Assistant's response
- `owner`: Owner of the agent
- `error`: Error flag

#### `StreamEvent`
- `event_type`: Type of event
- `data`: Event content
- `id`: Optional event ID

#### `UploadResponse`
- `success`: Whether upload succeeded
- `file_id`: Unique file identifier
- `file_size_bytes`: Size of uploaded file
- `content_type`: MIME type
- `file_name`: File name
- `created_at`: Creation timestamp
- `url`: Presigned access URL (valid for 3 days)

### Sync Methods

All async methods have `_sync` variants:
- `run_workflow_sync()`
- `upload_asset_sync()`

## License

MIT License
