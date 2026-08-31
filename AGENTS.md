# sketricgen-sdk — Agent Instructions

This is the **public Python SDK** for SketricGen, published to **PyPI** as `sketricgen`. It ships two clients: `SketricGenClient` wraps the **data plane** (run workflows, upload files, stream responses), and `AdminClient` wraps the **control plane** (manage resources via the Teamspace v2 Admin API). See `CONTEXT.md` for the data-plane vs control-plane vocabulary.

---

## What this package does

**Data plane (`SketricGenClient`):**

- **Run workflows** — async and sync methods to send messages to agent workflows
- **Stream responses** — async/sync iterators yielding SSE events
- **Upload files** — 3-step S3 presigned upload (init -> upload to S3 -> complete)

**Control plane (`AdminClient`):**

- **Manage resources** — teamspace identity (`whoami`), projects, agents, knowledge bases, brand agents, and connectors over the curated 15-operation Admin API surface
- **Auto-paginating lists** — `projects.list()` / `agents.list()` / `knowledge_bases.list()` follow the cursor lazily
- **Async brand-agent provisioning** — `brand_agents.create_and_wait()` polls a job to completion; `create()` / `get_status()` expose the primitives

**Both:**

- **Async + sync** — every public method has a `_sync` twin
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
├── __init__.py       # Public exports (both clients, Config, exceptions, response types)
├── client.py         # SketricGenClient — data plane (run_workflow, run_workflow_sync, file upload)
├── config.py         # SketricGenConfig dataclass (URLs, timeouts, from_env())
├── exceptions.py     # Custom exceptions (SketricGenError base; APIError, AdminError, JobError, etc.)
├── streaming.py      # SSE stream parsers (async + sync)
├── upload.py         # 3-step upload flow (detect content type, S3 presigned POST, complete)
├── admin/            # Control plane — AdminClient
│   ├── __init__.py   # Exports AdminClient
│   ├── client.py     # AdminClient + resource namespaces; DEFAULT_ADMIN_BASE_URL; request core
│   └── models.py     # Admin API response models (extra="ignore")
├── models/
│   ├── __init__.py
│   ├── requests.py   # Request models (RunWorkflowRequest, InitiateUploadRequest, etc.)
│   └── responses.py  # Response models (ChatResponse, StreamEvent, UploadResponse, etc.)
└── py.typed          # PEP 561 type marker

tests/
├── __init__.py
├── admin/            # AdminClient tests, one module per namespace + foundation/lists
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

### Control-plane surface (`AdminClient`)

```python
from sketricgen import AdminClient

# Reads SKETRICGEN_ADMIN_API_KEY; base URL is baked in (optional base_url= override)
admin = AdminClient()

# whoami + auto-paginating lists (async; each has a _sync twin)
me = await admin.whoami()
async for project in admin.projects.list(): ...
async for agent in admin.agents.list(): ...
async for kb in admin.knowledge_bases.list(): ...

# brand agents
templates = await admin.brand_agents.list_templates()
job = await admin.brand_agents.create_and_wait(name="Acme", seed_url="https://acme.example.com")
job = await admin.brand_agents.create(name="Acme", seed_url="https://acme.example.com")
status = await admin.brand_agents.get_status(job.job_id)
detail = await admin.brand_agents.get(agent_id)
await admin.brand_agents.update(agent_id, display_name="Acme")
await admin.brand_agents.get_widget_config(agent_id)
await admin.brand_agents.update_widget_config(agent_id, primary_color="#0055FF")

# connectors (attach/detach are connector-centric; route lives under /agents)
await admin.connectors.list()
await admin.connectors.list_tools("gmail")
await admin.connectors.create_link("gmail", project_id="proj-123")
await admin.connectors.check_connection("gmail", project_id="proj-123")
await admin.connectors.attach(agent_id, "gmail", allowed_tools=["send_email"])
await admin.connectors.detach(agent_id, "gmail")
```

The 15-operation surface deliberately mirrors the in-repo MCP server, not the
full Admin API — the excluded endpoints (member/usage/conversation/CRUD) are
listed in `.scratch/control-plane-python-sdk/spec.md`. The base URL is a baked-in
`DEFAULT_ADMIN_BASE_URL` constant in `admin/client.py`; there is no env-var path
for it, so changing the control-plane host means editing that constant.

### Key classes

| Class | Purpose |
|---|---|
| `SketricGenClient` | Data-plane client — run workflows, upload files (async + sync) |
| `AdminClient` | Control-plane client — manage resources with an admin key (async + sync) |
| `SketricGenConfig` | Configuration (API key, URLs, timeouts, `from_env()`) |
| `ChatResponse` | Non-streaming response (`agent_id`, `conversation_id`, `response`) |
| `StreamEvent` | SSE event (`event_type`, `data`) |

### Exception hierarchy

All inherit from `SketricGenError`:
- `SketricGenAPIError` — HTTP error with status code
- `SketricGenAuthenticationError` — 401 (data plane and control plane)
- `SketricGenAdminError` — control-plane `{error, code}` body; carries `status_code` and machine-readable `code`
- `SketricGenJobError` — brand-agent provisioning job ended failed; carries `job_id`, `status`, `error_summary`
- `SketricGenValidationError` — client-side validation
- `SketricGenNetworkError` — connection issues
- `SketricGenTimeoutError` — request timeout (also raised by `create_and_wait` on wait timeout)
- `SketricGenUploadError` — S3 upload failure
- `SketricGenFileSizeError` — file exceeds 20MB
- `SketricGenContentTypeError` — unsupported file type

### Allowed upload types

`image/jpeg`, `image/webp`, `image/png`, `application/pdf`, `image/gif` — max 20MB.

---

## Relationship to other services

- Calls `sketricgen-chatservers` at `/api/v1/run-workflow` (base URL: `https://chat-v2.sketricgen.ai`)
- `AdminClient` calls the Teamspace v2 Admin API at `/admin/v1/*` (control plane) — a separate host baked into `DEFAULT_ADMIN_BASE_URL`, with `Authorization: Bearer` auth
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
