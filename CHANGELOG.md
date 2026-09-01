# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/) (pre-1.0: breaking changes
may ride minor bumps).

## [0.2.0] — 2026-09-01

Adds control-plane support: a new `AdminClient` for the Teamspace v2 Admin API,
alongside the existing data-plane `SketricGenClient`.

### Added

- **`AdminClient`** — a typed, resource-grouped client for the control plane
  (`/admin/v1/*`), authenticated with an admin key
  (`Authorization: Bearer sk_admin_…`). Curated 15-operation surface:
  - top-level `whoami()`
  - `projects.list()`, `agents.list()`, `knowledge_bases.list()` — auto-paginating
  - `brand_agents` — `list_templates()`, `create()`, `get_status()`,
    `create_and_wait()`, `get()`, `update()`, `get_widget_config()`,
    `update_widget_config()`
  - `connectors` — `list()`, `list_tools()`, `create_link()`,
    `check_connection()`, `attach()`, `detach()`
- Async methods with synchronous `_sync` twins throughout.
- Typed Pydantic response models that ignore unknown fields, so a server-side
  field addition doesn't break a pinned SDK.
- `SketricGenAdminError` (carries the machine-readable server `code`) and
  `SketricGenJobError`; a 401 raises `SketricGenAuthenticationError`. All inherit
  `SketricGenError`.
- Admin key resolves from `SKETRICGEN_ADMIN_API_KEY` or a constructor arg; base
  URL is baked in with an optional `base_url=` override for testing.
- A gated live probe (`tests/live/`) that validates the SDK against the dev
  control plane, data plane, and DynamoDB. Deselected by default; never runs in
  CI.

### Changed

- **BREAKING:** the data-plane key environment variable is now
  **`SKETRICGEN_RUNTIME_API_KEY`** (was `SKETRICGEN_API_KEY`), with no
  back-compat alias. The `API-KEY` request header the chat server expects is
  unchanged — only the env-var name changed.

### Notes

- The shipped `DEFAULT_ADMIN_BASE_URL` targets the production control plane,
  matching the already-production data-plane and upload defaults.

[0.2.0]: https://github.com/sketricsolutions/sketricgen-sdk/releases/tag/v0.2.0
