"""Live probe against the dev environment.

Read-mostly. Control-plane reads are cross-checked against dev DynamoDB; the
data-plane read/run confirms the renamed runtime-key path end-to-end; mutating
probes are opt-in (``SKETRICGEN_LIVE_WRITE``) and clean up after themselves.

Run with real keys and a configured AWS CLI:

    export SKETRICGEN_ADMIN_API_KEY=sk_admin_...
    export SKETRICGEN_RUNTIME_API_KEY=sk_runtime_...
    pytest -m live tests/live -s          # -s shows the SDK-vs-DynamoDB report
"""

import os

import pytest

from sketricgen import (
    AdminClient,
    ChatResponse,
    SketricGenAdminError,
    SketricGenAuthenticationError,
)

from .dynamo import DynamoProbe
from .fixtures import TEAMSPACE_ID, TEST_AGENT_ID
from .reporter import ProbeReporter

pytestmark = pytest.mark.live


# ---------------------------------------------------------------------------
# Control-plane reads — verified against DynamoDB
# ---------------------------------------------------------------------------


async def test_whoami_matches_dynamo(
    admin: AdminClient, dynamo: DynamoProbe, reporter: ProbeReporter
) -> None:
    me = await admin.whoami()
    row = dynamo.teamspace()
    assert row is not None, "fixture teamspace row missing from DynamoDB"

    assert me.teamspace_id == TEAMSPACE_ID
    assert me.teamspace_id == row["teamspace_id"]
    assert me.display_name == row.get("display_name")
    assert me.slug == row.get("slug")
    assert me.subscription_plan == row.get("subscription_plan")

    reporter.record(
        "whoami",
        sdk=f"{me.teamspace_id} ({me.subscription_plan})",
        observed=f"{row['teamspace_id']} ({row.get('subscription_plan')})",
        match=True,
    )


async def test_projects_match_dynamo(
    admin: AdminClient, dynamo: DynamoProbe, reporter: ProbeReporter
) -> None:
    sdk_ids = {p.project_id async for p in admin.projects.list()}
    ddb_ids = set(dynamo.project_ids())

    match = sdk_ids == ddb_ids
    reporter.record(
        "projects.list",
        sdk=f"{len(sdk_ids)} ids",
        observed=f"{len(ddb_ids)} rows",
        match=match,
    )
    assert match, f"SDK-only={sdk_ids - ddb_ids}, DDB-only={ddb_ids - sdk_ids}"


async def test_agents_include_test_agent_and_fields_match(
    admin: AdminClient, dynamo: DynamoProbe, reporter: ProbeReporter
) -> None:
    sdk_agents = {a.agent_id: a async for a in admin.agents.list()}
    assert TEST_AGENT_ID in sdk_agents, "test agent absent from admin.agents.list()"

    # Every listed agent must exist as a real row (the API returns a curated
    # subset of the teamspace's rows, so this is a subset check, not equality).
    ddb_agent_ids = dynamo.agent_ids()
    orphans = set(sdk_agents) - ddb_agent_ids
    assert not orphans, f"agents returned by SDK with no DynamoDB row: {orphans}"

    # Field-level match for the test agent, resolved via the by-id GSI.
    sdk_agent = sdk_agents[TEST_AGENT_ID]
    row = dynamo.agent_by_id(TEST_AGENT_ID)
    assert row is not None, "test agent row missing from DynamoDB"
    assert sdk_agent.name == row.get("name")
    assert sdk_agent.agent_type == row.get("agent_type")
    assert sdk_agent.agent_status == row.get("agent_status")
    assert sdk_agent.project_id == row.get("project_id")
    assert sdk_agent.teamspace_id == row.get("teamspace_id") == TEAMSPACE_ID

    reporter.record(
        "agents.list",
        sdk=f"{len(sdk_agents)} agents, test={sdk_agent.name}",
        observed=f"row {row['agent_id']} ({row.get('agent_status')})",
        match=True,
    )


async def test_knowledge_bases_match_dynamo(
    admin: AdminClient, dynamo: DynamoProbe, reporter: ProbeReporter
) -> None:
    sdk_ids = {kb.knowledge_base_id async for kb in admin.knowledge_bases.list()}
    ddb_ids = set(dynamo.knowledge_base_ids())

    match = sdk_ids == ddb_ids
    reporter.record(
        "knowledge_bases.list",
        sdk=f"{len(sdk_ids)} ids",
        observed=f"{len(ddb_ids)} rows",
        match=match,
    )
    assert match, f"SDK-only={sdk_ids - ddb_ids}, DDB-only={ddb_ids - sdk_ids}"


async def test_catalogs_return_without_error(
    admin: AdminClient, reporter: ProbeReporter
) -> None:
    # Catalogs are server-curated, not teamspace rows — no DynamoDB cross-check.
    templates = await admin.brand_agents.list_templates()
    connectors = await admin.connectors.list()
    assert templates, "brand-agent template catalog was empty"
    assert connectors, "connector catalog was empty"

    reporter.record(
        "brand_agents.list_templates",
        sdk=f"{len(templates)} templates",
        observed="catalog (no DDB check)",
        match=True,
    )
    reporter.record(
        "connectors.list",
        sdk=f"{len(connectors)} connectors",
        observed="catalog (no DDB check)",
        match=True,
    )


# ---------------------------------------------------------------------------
# Control-plane error contract
# ---------------------------------------------------------------------------


async def test_bad_id_raises_admin_error_with_code(
    admin: AdminClient, reporter: ProbeReporter
) -> None:
    unknown = "skflow_00000000-0000-0000-0000-000000000000"
    with pytest.raises(SketricGenAdminError) as excinfo:
        await admin.brand_agents.get(unknown)

    err = excinfo.value
    assert err.status_code >= 400
    assert (
        err.code and err.code != "admin_api_error"
    ), "expected a machine-readable server code on the error"
    reporter.record(
        "brand_agents.get(unknown)",
        sdk=f"raise AdminError[{err.code}]",
        observed=f"HTTP {err.status_code}",
        match=True,
    )


async def test_bad_key_raises_authentication_error(
    admin_key: str, reporter: ProbeReporter
) -> None:
    # Gated on a configured run (admin_key) so a keyless `pytest -m live` skips
    # uniformly; the probe itself uses a deliberately invalid key, not admin_key.
    bad = AdminClient(api_key="sk_admin_invalid_probe_key")
    with pytest.raises(SketricGenAuthenticationError) as excinfo:
        await bad.whoami()

    assert excinfo.value.status_code == 401
    reporter.record(
        "whoami(bad key)",
        sdk="raise AuthenticationError",
        observed="HTTP 401",
        match=True,
    )


# ---------------------------------------------------------------------------
# Data-plane read/run — confirms the renamed runtime-key path against dev-chat
# ---------------------------------------------------------------------------


async def test_run_workflow_against_dev(
    runtime_client, dynamo: DynamoProbe, reporter: ProbeReporter
) -> None:
    response = await runtime_client.run_workflow(
        agent_id=TEST_AGENT_ID,
        user_input="Reply with the single word: pong.",
    )
    assert isinstance(response, ChatResponse)
    assert response.agent_id == TEST_AGENT_ID
    assert not response.error, f"run_workflow returned an error: {response.error}"
    assert response.response, "run_workflow returned an empty response"

    # The agent we ran is the same DynamoDB row the control-plane probe matched.
    row = dynamo.agent_by_id(TEST_AGENT_ID)
    assert row is not None

    reporter.record(
        "run_workflow (dev-chat)",
        sdk=f"conv={response.conversation_id}",
        observed=f"agent row {row['agent_id']}",
        match=True,
    )


# ---------------------------------------------------------------------------
# Write probe — opt-in only, with cleanup and DynamoDB verification
# ---------------------------------------------------------------------------
#
# This probe MUST target a disposable brand agent, not the shared test agent:
# it renames the agent and restores it. Point it at a throwaway brand agent with
#   export SKETRICGEN_LIVE_WRITE_AGENT=skflow_...   # a brand-agent you can mutate
# It is skipped unless BOTH SKETRICGEN_LIVE_WRITE and that id are set.
#
# `brand_agents.update(display_name=...)` writes the value to the SkGenAgent
# row's `name` attribute, so the effect is directly observable in DynamoDB and
# is cleanly reversible by writing the original value back.


async def test_brand_agent_display_name_roundtrip(
    write_enabled: None,
    admin: AdminClient,
    dynamo: DynamoProbe,
    reporter: ProbeReporter,
) -> None:
    agent_id = os.getenv("SKETRICGEN_LIVE_WRITE_AGENT")
    if not agent_id:
        pytest.skip(
            "SKETRICGEN_LIVE_WRITE_AGENT not set; the mutating probe needs a "
            "disposable brand-agent id (never the shared test agent)"
        )

    before = dynamo.agent_by_id(agent_id)
    assert before is not None, "target write agent has no DynamoDB row"
    original_name = before.get("name")
    probe_name = "SDK live-probe (temporary)"
    assert original_name != probe_name, "unexpected pre-existing probe name"

    restored = False
    try:
        await admin.brand_agents.update(agent_id, display_name=probe_name)

        # Effect must be observable in DynamoDB: row.name is now the probe value.
        after = dynamo.agent_by_id(agent_id)
        assert after is not None
        observed = after.get("name")
        match = observed == probe_name
        reporter.record(
            "brand_agents.update(display_name)",
            sdk=f"display_name={probe_name!r}",
            observed=f"row.name={observed!r}",
            match=match,
        )
        assert match, "update did not reach the agent's DynamoDB row"
    finally:
        # Restore the original display name no matter what happened above.
        if original_name:
            await admin.brand_agents.update(agent_id, display_name=original_name)
            final = dynamo.agent_by_id(agent_id)
            restored = bool(final and final.get("name") == original_name)
        reporter.record(
            "brand_agents.update (restore)",
            sdk=f"display_name={original_name!r}",
            observed="restored" if restored else "RESTORE FAILED",
            match=restored,
        )
