# SketricGen SDK

Python SDK for the SketricGen Chat Server API.

## Installation

```bash
pip install sketricgen
```

Or install from source:

```bash
git clone https://github.com/sketricsolutions/sketricgen-sdk.git
cd sketricgen-sdk
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
- **Control Plane**: Manage projects, agents, knowledge bases, brand agents, and connectors via `AdminClient` (see [Control Plane — AdminClient](#control-plane--adminclient))
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
import json
from sketricgen import SketricGenClient

client = SketricGenClient(api_key="your-api-key")

# Async streaming
async for event in await client.run_workflow(
    agent_id="agent-123",
    user_input="Tell me a story",
    stream=True,
):
    data = json.loads(event.data)
    event_type = data["type"]
    
    if event_type == "TEXT_MESSAGE_CONTENT":
        # Print text chunks as they arrive
        print(data["delta"], end="", flush=True)
    elif event_type == "TOOL_CALL_START":
        print(f"\n[Calling tool: {data['tool_call_name']}]")
    elif event_type == "TOOL_CALL_END":
        print(f"[Tool completed]")
    elif event_type == "RUN_FINISHED":
        print()  # New line
    elif event_type == "RUN_ERROR":
        print(f"\nError: {data['message']}")

# Sync streaming
for event in client.run_workflow_sync(
    agent_id="agent-123",
    user_input="Tell me a story",
    stream=True,
):
    data = json.loads(event.data)
    if data["type"] == "TEXT_MESSAGE_CONTENT":
        print(data["delta"], end="", flush=True)
```

**Stream Event Types (AG-UI Protocol):**

The streaming API uses [AG-UI](https://docs.ag-ui.com) events from `ag_ui.core`:

| Event Type | Description | Key Fields |
|------------|-------------|------------|
| `RUN_STARTED` | Workflow execution started | `thread_id`, `run_id` |
| `TEXT_MESSAGE_START` | Assistant message started | `message_id`, `role` |
| `TEXT_MESSAGE_CONTENT` | Text chunk | `message_id`, `delta` |
| `TEXT_MESSAGE_END` | Assistant message completed | `message_id` |
| `TOOL_CALL_START` | Tool/function call started | `tool_call_id`, `tool_call_name` |
| `TOOL_CALL_END` | Tool/function call completed | `tool_call_id` |
| `RUN_FINISHED` | Workflow completed | `thread_id`, `run_id`, `result` |
| `RUN_ERROR` | Workflow error occurred | `message` |
| `CUSTOM` | Custom event | varies |

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
# Set SKETRICGEN_RUNTIME_API_KEY
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
- `type`: Type of event
- `data`: Event content
- `id`: Optional event ID

### Sync Methods

The async `run_workflow()` method has a synchronous variant:
- `run_workflow_sync()`

## Control Plane — AdminClient

`SketricGenClient` talks to the **data plane** (running workflows). To *manage*
resources — teamspace identity, projects, agents, knowledge bases, brand agents,
and connectors — use `AdminClient`, which talks to the **control plane** (the
Teamspace v2 Admin API).

The two clients use different credentials and are **not interchangeable**:

| | `SketricGenClient` (data plane) | `AdminClient` (control plane) |
|---|---|---|
| Purpose | Run workflows, upload files | Manage resources |
| Credential | Runtime key (`sk_runtime_…`) | Admin key (`sk_admin_…`) |
| Env var | `SKETRICGEN_RUNTIME_API_KEY` | `SKETRICGEN_ADMIN_API_KEY` |
| Auth header | `API-KEY` | `Authorization: Bearer` |
| Base URL | Configurable | Shipped with the SDK |

### Construction

```python
from sketricgen import AdminClient

# Reads the admin key from SKETRICGEN_ADMIN_API_KEY
admin = AdminClient()

# Or pass the key explicitly
admin = AdminClient(api_key="sk_admin_...")
```

The control-plane base URL is **built into the SDK** — you supply only your admin
key, never a hostname. A `base_url=` argument is available for testing or
self-hosting, but there is intentionally no environment-variable path for it:

```python
admin = AdminClient(base_url="https://sandbox.example.com/admin/v1")
```

A missing admin key fails closed immediately:

```python
AdminClient(api_key=None)  # raises ValueError if SKETRICGEN_ADMIN_API_KEY is unset
```

Every method is **async-first with a synchronous `_sync` twin**, matching
`SketricGenClient`.

### whoami

```python
# Async
me = await admin.whoami()
print(me.teamspace_id, me.display_name)

# Sync
me = admin.whoami_sync()
```

### Listing resources

`projects.list()`, `agents.list()`, and `knowledge_bases.list()` **transparently
page through every result** — you never manage a `next_token` cursor. They return
a lazy iterator, so only the pages you consume are fetched:

```python
# Async — lazy async iterator
async for project in admin.projects.list():
    print(project.project_id, project.display_name)

async for agent in admin.agents.list():
    print(agent.agent_id, agent.name)

async for kb in admin.knowledge_bases.list():
    print(kb.knowledge_base_id, kb.name)

# Sync — lazy iterator
for project in admin.projects.list_sync():
    print(project.project_id)
for agent in admin.agents.list_sync():
    print(agent.agent_id)
for kb in admin.knowledge_bases.list_sync():
    print(kb.knowledge_base_id)
```

### Brand agents

Brand-agent provisioning is asynchronous on the server. Use `create_and_wait()`
for the one-call path, or drive the `create()` / `get_status()` primitives
yourself.

```python
# One call: create and poll to completion
job = await admin.brand_agents.create_and_wait(
    name="Acme Support",
    seed_url="https://acme.example.com",
    poll_interval=10.0,   # seconds between polls
    timeout=600.0,        # give up after this many seconds
)
print(job.status)              # "succeeded"
print(job.embed.snippet)       # embed code for the finished agent

# Or drive the async flow yourself
job = await admin.brand_agents.create(
    name="Acme Support",
    seed_url="https://acme.example.com",
)
status = await admin.brand_agents.get_status(job.job_id)
print(status.status, status.phase)

# Browse the template catalog
templates = await admin.brand_agents.list_templates()

# Inspect and edit an existing brand agent
detail = await admin.brand_agents.get(agent_id)
result = await admin.brand_agents.update(
    agent_id,
    display_name="Acme Assistant",
    instructions="Be concise.",
    model="gpt-4o",
    knowledge_base_ids=["kb-123"],
)

# Widget configuration
config = await admin.brand_agents.get_widget_config(agent_id)
await admin.brand_agents.update_widget_config(agent_id, primary_color="#0055FF")

# Sync
job = admin.brand_agents.create_and_wait_sync(
    name="Acme Support", seed_url="https://acme.example.com",
)
templates = admin.brand_agents.list_templates_sync()
```

`create_and_wait()` raises `SketricGenJobError` if the job fails and
`SketricGenTimeoutError` if it does not reach a terminal state within `timeout` —
a failed provision is never silently treated as success. Sync twins:
`create_and_wait_sync()`, `create_sync()`, `get_status_sync()`, `get_sync()`,
`update_sync()`, `list_templates_sync()`, `get_widget_config_sync()`,
`update_widget_config_sync()`.

### Connectors

```python
# Curated brand-connector catalog
connectors = await admin.connectors.list()

# Grantable tool names for one connector
tools = await admin.connectors.list_tools("gmail")

# Mint a hosted consent URL, then poll until a human finishes connecting
link = await admin.connectors.create_link("gmail", project_id="proj-123")
print(link.connect_url)
status = await admin.connectors.check_connection("gmail", project_id="proj-123")
print(status.connected)

# Attach a connector's tools to an agent, or detach it
await admin.connectors.attach(agent_id, "gmail", allowed_tools=["send_email"])
await admin.connectors.detach(agent_id, "gmail")

# Sync
connectors = admin.connectors.list_sync()
admin.connectors.attach_sync(agent_id, "gmail", allowed_tools=["send_email"])
```

Attach/detach are grouped under `connectors` (connector-centric) even though the
underlying route lives under `/agents`. Sync twins: `list_sync()`,
`list_tools_sync()`, `create_link_sync()`, `check_connection_sync()`,
`attach_sync()`, `detach_sync()`.

### Error handling

Control-plane errors carry a machine-readable `code`, so you can branch on the
failure kind instead of parsing message strings:

```python
from sketricgen import (
    AdminClient,
    SketricGenAdminError,
    SketricGenAuthenticationError,
    SketricGenJobError,
    SketricGenError,
)

admin = AdminClient()

try:
    job = await admin.brand_agents.create_and_wait(
        name="Acme", seed_url="https://acme.example.com",
    )
except SketricGenAuthenticationError:
    print("Admin key rejected (401)")
except SketricGenJobError as e:
    print(f"Provisioning failed for job {e.job_id}: {e.error_summary}")
except SketricGenAdminError as e:
    if e.code == "agent_limit_reached":
        print("Out of agent quota")
    else:
        print(f"Admin API error [{e.status_code}] {e.code}: {e}")
except SketricGenError as e:
    # Base class — catches anything the SDK raises, data plane or control plane
    print(f"SDK error: {e}")
```

Response models tolerate unknown fields, so a server-side field addition never
breaks a pinned SDK version.

## License

MIT License
