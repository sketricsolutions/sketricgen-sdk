# sketricgen-sdk — Agent Instructions

This is the **public Python SDK** for SketricGen, published to **PyPI** as `sketricgen`. It wraps the SketricGen public REST API so developers can run workflows, upload files, and stream responses from Python applications.

---

## What this package does

- **Run workflows** — async and sync methods to send messages to agent workflows
- **Stream responses** — async/sync iterators yielding SSE events
- **Upload files** — 3-step S3 presigned upload (init -> upload to S3 -> complete)
- **Type safety** — full type hints, Pydantic models, `py.typed` marker

---

## Stack

- Python >= 3.9
- `httpx` for HTTP requests (async + sync)
- `pydantic` for request/response models
- Published to PyPI
- Package management: `uv` with `pyproject.toml` + `uv.lock`

---

## Directory structure

```
sketricgen/
├── __init__.py       # Public exports (SketricGenClient, Config, exceptions, response types)
├── client.py         # SketricGenClient class (run_workflow, run_workflow_sync, file upload)
├── config.py         # SketricGenConfig dataclass (URLs, timeouts, from_env())
├── exceptions.py     # Custom exceptions (SketricGenError, APIError, AuthError, ValidationError, etc.)
├── streaming.py      # SSE stream parsers (async + sync)
├── upload.py         # 3-step upload flow (detect content type, S3 presigned POST, complete)
├── models/
│   ├── __init__.py
│   ├── requests.py   # Request models (RunWorkflowRequest, InitiateUploadRequest, etc.)
│   └── responses.py  # Response models (ChatResponse, StreamEvent, UploadResponse, etc.)
└── py.typed          # PEP 561 type marker

tests/
├── __init__.py
└── fixtures/
    └── __init__.py

docs/examples/
├── basic_usage.py        # Quick-start examples (async, sync, streaming, files)
└── error_handling.py     # Error handling patterns and retry logic
```

---

## Public API surface

```python
from sketricgen import SketricGenClient

# Construct
client = SketricGenClient(api_key="your-key")
# Or from environment
config = SketricGenConfig.from_env()
client = SketricGenClient(api_key=config.api_key)

# Async non-streaming
response = await client.run_workflow(agent_id="agent-id", user_input="Hello")

# Sync non-streaming
response = client.run_workflow_sync(agent_id="agent-id", user_input="Hello")

# Async streaming
async for event in await client.run_workflow(agent_id="agent-id", user_input="Hello", stream=True):
    data = json.loads(event.data)
    if data["type"] == "TEXT_MESSAGE_CONTENT":
        print(data["delta"], end="")

# File upload
response = await client.run_workflow(
    agent_id="agent-id",
    user_input="Summarize this",
    file_paths=["/path/to/doc.pdf"]
)
```

### Key classes

| Class | Purpose |
|---|---|
| `SketricGenClient` | Main client (async + sync methods) |
| `SketricGenConfig` | Configuration (API key, URLs, timeouts, `from_env()`) |
| `ChatResponse` | Non-streaming response (`agent_id`, `conversation_id`, `response`) |
| `StreamEvent` | SSE event (`event_type`, `data`) |

### Exception hierarchy

All inherit from `SketricGenError`:
- `SketricGenAPIError` — HTTP error with status code
- `SketricGenAuthenticationError` — 401
- `SketricGenValidationError` — client-side validation
- `SketricGenNetworkError` — connection issues
- `SketricGenTimeoutError` — request timeout
- `SketricGenUploadError` — S3 upload failure
- `SketricGenFileSizeError` — file exceeds 20MB
- `SketricGenContentTypeError` — unsupported file type

### Allowed upload types

`image/jpeg`, `image/webp`, `image/png`, `application/pdf`, `image/gif` — max 20MB.

---

## Relationship to other services

- Calls `sketricgen-chatservers` at `/api/v1/run-workflow` (base URL: `https://chat-v2.sketricgen.ai`)
- Upload endpoints go to API Gateway Lambda (separate from chatservers)
- Must stay in sync with the Node.js SDK (`sketricgen-node-sdk`) — same API surface, same event types
- Changes to chatservers' public API require updates here

---

## Development

```bash
# Install dependencies
uv sync

# Install with dev deps
uv sync --extra dev

# Run tests
uv run pytest

# Type checking
uv run mypy sketricgen

# Lint + format
uv run ruff check .
uv run black .
```

---

## Files you must NEVER modify

- `uv.lock` — managed by uv. Only modify `pyproject.toml`.
- Do not change default API URLs without coordinating with chatservers and the Node.js SDK.

---

## Key docs to read

- `docs/examples/basic_usage.py` — quick-start patterns
- `docs/examples/error_handling.py` — error handling and retry patterns
- `README.md` — public-facing usage guide (this IS the user documentation)
