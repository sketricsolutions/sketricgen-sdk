"""Live probe against the dev environment.

Read-mostly. Control-plane reads are cross-checked against dev DynamoDB; the
data-plane read/run confirms the renamed runtime-key path end-to-end; mutating
probes are opt-in (``SKETRICGEN_LIVE_WRITE``) and clean up after themselves.

Run with real keys and a configured AWS CLI:

    export SKETRICGEN_API_KEY=sk_api_...
    pytest -m live tests/live -s          # -s shows the SDK-vs-DynamoDB report
"""

import json
import os
import struct
import zlib

import pytest

from sketricgen import (
    ChatResponse,
    HitlDecision,
    HitlResume,
    SketricGenAdminError,
    SketricGenAuthenticationError,
    SketricGenClient,
)

from .dynamo import DynamoProbe
from .fixtures import TEAMSPACE_ID, TEST_AGENT_ID, TEST_BRAND_AGENT_ID
from .reporter import ProbeReporter

pytestmark = pytest.mark.live


def _minimal_png() -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    width = height = 16
    rows = b"".join(b"\x00" + b"\xff\xff\xff" * width for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


def _minimal_pdf() -> bytes:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] "
            b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
        ),
        b"<< /Length 42 >>\nstream\nBT /F1 12 Tf 20 100 Td (SDK probe) Tj ET\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    content = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(objects, 1):
        offsets.append(len(content))
        content.extend(f"{index} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = len(content)
    content.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    content.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        content.extend(f"{offset:010d} 00000 n \n".encode())
    content.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(content)


# ---------------------------------------------------------------------------
# Control-plane reads — verified against DynamoDB
# ---------------------------------------------------------------------------


async def test_whoami_matches_dynamo(
    admin: SketricGenClient, dynamo: DynamoProbe, reporter: ProbeReporter
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
    admin: SketricGenClient, dynamo: DynamoProbe, reporter: ProbeReporter
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
    admin: SketricGenClient, dynamo: DynamoProbe, reporter: ProbeReporter
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
    admin: SketricGenClient, dynamo: DynamoProbe, reporter: ProbeReporter
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
    admin: SketricGenClient, reporter: ProbeReporter
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
    admin: SketricGenClient, reporter: ProbeReporter
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
    api_key: str, admin: SketricGenClient, reporter: ProbeReporter
) -> None:
    # Gated on a configured run so a keyless `pytest -m live` skips uniformly.
    bad = SketricGenClient(api_key="sk_api_invalid_probe_key")
    bad._admin._base_url = admin._admin._base_url
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


async def test_multiple_file_types_against_dev(
    runtime_client,
    tmp_path,
    reporter: ProbeReporter,
) -> None:
    files = {
        "pixel.png": _minimal_png(),
        "sample.pdf": _minimal_pdf(),
        "notes.txt": b"SketricGen SDK live upload probe.\n",
        "payload.json": b'{"probe": "sketricgen-sdk", "ok": true}\n',
        "sheet.csv": b"name,value\nprobe,1\n",
    }
    paths = []
    for name, contents in files.items():
        path = tmp_path / name
        path.write_bytes(contents)
        paths.append(str(path))

    response = await runtime_client.run_workflow(
        agent_id=TEST_AGENT_ID,
        user_input="Confirm that you received the attached test files.",
        file_paths=paths,
    )
    assert isinstance(response, ChatResponse)
    assert not response.error, f"attachment run returned an error: {response.error}"
    assert response.response
    reporter.record(
        "run_workflow (5 attachment types)",
        sdk="png,pdf,txt,json,csv",
        observed=f"conv={response.conversation_id}",
        match=True,
    )


async def test_hitl_pause_and_resume_against_dev(
    runtime_client,
    reporter: ProbeReporter,
) -> None:
    paused = await runtime_client.run_workflow(
        agent_id=TEST_BRAND_AGENT_ID,
        user_input=(
            "Call the lead_capture_form tool now so I can enter my details. "
            "Do not answer with plain text instead."
        ),
        enable_hitl=True,
    )
    assert isinstance(paused, ChatResponse)
    assert paused.run_paused_hitl
    assert paused.hitl_request is not None

    skip = json.dumps(
        {
            "skipped": True,
            "full_name": None,
            "email": None,
            "form_payload": {},
            "consent_given": False,
            "metadata": {"skip_reason": "sdk_live_probe"},
        }
    )
    decisions = [
        HitlDecision(
            type="respond",
            message=skip if action.name == "lead_capture_form" else "",
        )
        for action in paused.hitl_request.action_requests
    ]
    resumed = await runtime_client.run_workflow(
        agent_id=TEST_BRAND_AGENT_ID,
        user_input="Skip the form.",
        conversation_id=paused.conversation_id,
        enable_hitl=True,
        hitl_resume=HitlResume(
            request_id=paused.hitl_request.request_id,
            decisions=decisions,
        ),
    )
    assert isinstance(resumed, ChatResponse)
    assert not resumed.error, f"HITL resume returned an error: {resumed.error}"
    assert not resumed.run_paused_hitl
    reporter.record(
        "run_workflow (HITL pause/resume)",
        sdk=f"request={paused.hitl_request.request_id}",
        observed=f"conv={paused.conversation_id}",
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
    admin: SketricGenClient,
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
