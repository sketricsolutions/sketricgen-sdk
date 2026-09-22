# Context — sketricgen SDK

Glossary for the `sketricgen` Python SDK. Terms only; no implementation details.

## Planes

- **Data plane** — the runtime surface that *runs* agents: the chat server's
  `run-workflow` and asset-upload endpoints. What today's `SketricGenClient`
  talks to.
- **Control plane** — the surface that *manages* resources (projects, agents,
  brand agents, knowledge bases, connectors, members, usage) via the Teamspace
  v2 Admin API at `/admin/v1/*`. A distinct API with its own host, auth scheme,
  and role model. The unified client routes management operations to this plane.

## Credentials

- **API key** — a `sk_api_…` credential with `runtime`, `admin`, or both access
  flags. Read by the SDK from `SKETRICGEN_API_KEY`. Runtime calls send it in the
  `API-KEY` header; control-plane calls send it as `Authorization: Bearer`. A
  call fails when the key lacks the access required by that plane.

## SDK clients

- **`SketricGenClient`** — the single public client. It runs workflows, uploads
  assets, and manages control-plane resources with one API key.

## Admin scope kinds

- **Project-scoped** — bound to one project; every operation targets it.
- **Teamspace-scoped** — spans all projects in the teamspace; unlocks project
  CRUD and member management; writes must name a `project_id`.
