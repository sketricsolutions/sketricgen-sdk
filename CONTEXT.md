# Context — sketricgen SDK

Glossary for the `sketricgen` Python SDK. Terms only; no implementation details.

## Planes

- **Data plane** — the runtime surface that *runs* agents: the chat server's
  `run-workflow` and asset-upload endpoints. What today's `SketricGenClient`
  talks to.
- **Control plane** — the surface that *manages* resources (projects, agents,
  brand agents, knowledge bases, connectors, members, usage) via the Teamspace
  v2 Admin API at `/admin/v1/*`. A distinct API with its own host, auth scheme,
  and role model. The new admin client talks to this.

## Credentials

- **Runtime key** — a data-plane API key (prefix `sk_runtime_…`) that authorizes
  running workflows. Carries no role. Read by the SDK from
  `SKETRICGEN_RUNTIME_API_KEY`. Sent to the chat server as an `API-KEY` header.
- **Admin key** — a control-plane API key (prefix `sk_admin_…`) that authorizes
  managing resources. Carries a **role** (`viewer` / `editor` / `admin`) and a
  **scope** (a single project, or the whole teamspace). Read by the SDK from
  `SKETRICGEN_ADMIN_API_KEY`. Sent to the control plane as an
  `Authorization: Bearer` header. An admin key **cannot** run workflows and a
  runtime key **cannot** reach the control plane — they are not
  interchangeable.

## SDK clients

- **`SketricGenClient`** — the data-plane client. Runs workflows and uploads
  assets with a runtime key.
- **`AdminClient`** — the control-plane client. Manages resources with an admin
  key. Its base URL is a value the SDK ships, not something the SDK's user
  configures; the user supplies only their admin key.

## Scope kinds (admin key)

- **Project-scoped** — bound to one project; every operation targets it.
- **Teamspace-scoped** — spans all projects in the teamspace; unlocks project
  CRUD and member management; writes must name a `project_id`.
