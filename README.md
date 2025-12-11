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
- **File Attachments**: Attach files (images, PDFs) to workflows seamlessly
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

### Workflow with File Attachments

Attach files to your workflows. The SDK handles file uploads automatically in the background.

```python
from sketricgen import SketricGenClient

client = SketricGenClient(api_key="your-api-key")

# Async with file attachment
response = await client.run_workflow(
    agent_id="agent-123",
    user_input="Please analyze this document",
    file_paths=["/path/to/document.pdf"],
)
print(response.response)

# Sync with file attachment
response = client.run_workflow_sync(
    agent_id="agent-123",
    user_input="Summarize this document",
    file_paths=["/path/to/document.pdf"],
)
```

### Multiple File Attachments

```python
from sketricgen import SketricGenClient

client = SketricGenClient(api_key="your-api-key")

# Attach multiple files at once
response = await client.run_workflow(
    agent_id="agent-123",
    user_input="Compare these two documents",
    file_paths=[
        "/path/to/document1.pdf",
        "/path/to/document2.pdf",
    ],
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
    response = await client.run_workflow(
        agent_id="agent-123",
        user_input="Analyze this document",
        file_paths=["/path/to/file.pdf"],
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
except FileNotFoundError as e:
    print(f"File not found: {e}")
```

### Configuration

```python
from sketricgen import SketricGenClient

# Direct configuration
client = SketricGenClient(
    api_key="your-api-key",
    timeout=30,
    upload_timeout=300,  # 5 minutes for large files
    max_retries=3,
)

# From environment variables
# Set SKETRICGEN_API_KEY
client = SketricGenClient.from_env()
```

## Supported File Types

For file attachments, the following content types are supported:

- `image/jpeg`
- `image/png`
- `image/webp`
- `image/gif`
- `application/pdf`

Maximum file size: **20 MB**

## API Reference

### SketricGenClient

#### `run_workflow(agent_id, user_input, conversation_id?, contact_id?, file_paths?, stream?)`

Execute a workflow/chat request.

**Parameters:**
- `agent_id` (str): Agent ID to chat with
- `user_input` (str): User message (max 10000 characters)
- `conversation_id` (str, optional): Conversation ID for resuming
- `contact_id` (str, optional): External contact ID
- `file_paths` (list[str], optional): List of file paths to upload and attach
- `stream` (bool, optional): Whether to stream the response

**Returns:** `ChatResponse` or `AsyncIterator[StreamEvent]` if streaming

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

### Sync Methods

The async `run_workflow()` method has a synchronous variant:
- `run_workflow_sync()`

## License

MIT License
