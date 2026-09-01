# Live probe (dev)

A gated, **manually-run** integration probe that exercises the real SDK against
the **dev** control plane, data plane, and DynamoDB. It is **not** part of CI:
the `live` marker is deselected by default (see `pyproject.toml`), so a plain
`pytest` never runs it.

## What it checks

- **Control plane (read)** — `whoami`, `projects.list`, `agents.list`,
  `knowledge_bases.list`, `brand_agents.list_templates`, `connectors.list`, each
  cross-checked against the dev DynamoDB rows. Plus the error contract: a bad id
  → `SketricGenAdminError` (with server `code`), a bad key → `401`.
- **Data plane (read/run)** — `run_workflow` against `dev-chat` with the renamed
  `SKETRICGEN_RUNTIME_API_KEY`.
- **Write (opt-in)** — a `brand_agents.update` display-name round-trip that
  verifies the effect in DynamoDB and restores the original value.

Every operation is reported SDK-returned vs DynamoDB-observed in the pytest
terminal summary, followed by a reminder to revoke the temporary keys.

## Running it

Keys are supplied at run time and **never committed**. Rotate/delete them after.

```bash
export SKETRICGEN_ADMIN_API_KEY=sk_admin_...
export SKETRICGEN_RUNTIME_API_KEY=sk_runtime_...
# AWS CLI must already be configured for the dev DynamoDB tables (us-east-1).

pytest -m live tests/live -s        # -s shows the SDK-vs-DynamoDB report
```

Each test skips (rather than errors) if the credential or AWS access it needs is
absent, so a keyless `pytest -m live` skips the whole probe.

## Environment

| Variable | Purpose |
|---|---|
| `SKETRICGEN_ADMIN_API_KEY` | Control-plane admin key (required for control-plane probes). |
| `SKETRICGEN_RUNTIME_API_KEY` | Data-plane runtime key (required for the `run_workflow` probe). |
| `SKETRICGEN_DDB_TABLE_SUFFIX` | Optional. The Amplify `SkGen<Model>-<suffix>-NONE` suffix. Auto-resolved by locating the fixture teamspace if unset. |
| `SKETRICGEN_DDB_REGION` | Optional. DynamoDB region (default `us-east-1`). |
| `SKETRICGEN_LIVE_WRITE` | Opt-in flag for the mutating probe. Unset ⇒ skipped. |
| `SKETRICGEN_LIVE_WRITE_AGENT` | A **disposable brand-agent** id for the write probe to rename and restore. **Never the shared test agent.** Unset ⇒ the write probe skips. |

The endpoint overrides are baked into the fixtures: control plane uses the SDK's
shipped dev default; the data-plane client is retargeted at `dev-chat`; uploads
point at the dev API base.
