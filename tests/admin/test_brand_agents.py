"""Brand-agent namespace: templates, provisioning, edits, widget config."""

import httpx
import pytest
import respx

from sketricgen import AdminClient, SketricGenJobError, SketricGenTimeoutError

from .conftest import BASE_URL, request_body


@respx.mock
async def test_list_templates(admin: AdminClient) -> None:
    route = respx.get(f"{BASE_URL}/brand-agent-templates").mock(
        return_value=httpx.Response(
            200,
            json={
                "brand_agent_templates": [
                    {"slug": "support", "name": "Support", "min_plan": "builder"},
                    {"slug": "sales", "name": "Sales"},
                ],
                "total": 2,
                "has_more": False,
                "truncated": False,
            },
        )
    )

    templates = await admin.brand_agents.list_templates(limit=5)

    assert route.calls.last.request.url.path == "/admin/v1/brand-agent-templates"
    assert route.calls.last.request.url.params["limit"] == "5"
    assert [t.slug for t in templates] == ["support", "sales"]


@respx.mock
def test_list_templates_sync(admin: AdminClient) -> None:
    respx.get(f"{BASE_URL}/brand-agent-templates").mock(
        return_value=httpx.Response(
            200, json={"brand_agent_templates": [{"slug": "faq"}]}
        )
    )
    templates = admin.brand_agents.list_templates_sync()
    assert templates[0].slug == "faq"


@respx.mock
async def test_create_returns_job_handle(admin: AdminClient) -> None:
    route = respx.post(f"{BASE_URL}/brand-agents").mock(
        return_value=httpx.Response(
            202,
            json={
                "agent_id": "skbrand_1",
                "job_id": "job_1",
                "status": "queued",
                "poll_url": "/admin/v1/jobs/job_1",
                "publish_widget": True,
            },
        )
    )

    job = await admin.brand_agents.create(
        name="Acme Bot",
        seed_url="https://acme.example",
        description="helpful",
        publish_widget=False,
    )

    body = request_body(route.calls.last.request)
    assert body == {
        "name": "Acme Bot",
        "seed_url": "https://acme.example",
        "description": "helpful",
        "publish_widget": False,
    }
    assert job.agent_id == "skbrand_1"
    assert job.job_id == "job_1"


@respx.mock
def test_create_sync(admin: AdminClient) -> None:
    respx.post(f"{BASE_URL}/brand-agents").mock(
        return_value=httpx.Response(
            202, json={"agent_id": "skbrand_2", "job_id": "job_2"}
        )
    )
    job = admin.brand_agents.create_sync(name="B", seed_url="https://b.example")
    assert job.job_id == "job_2"


@respx.mock
async def test_get_status(admin: AdminClient) -> None:
    route = respx.get(f"{BASE_URL}/jobs/job_1").mock(
        return_value=httpx.Response(
            200, json={"job_id": "job_1", "status": "crawling", "phase": "crawl"}
        )
    )

    status = await admin.brand_agents.get_status("job_1")

    assert route.calls.last.request.url.path == "/admin/v1/jobs/job_1"
    assert status.status == "crawling"


@respx.mock
async def test_create_and_wait_success(admin: AdminClient) -> None:
    respx.post(f"{BASE_URL}/brand-agents").mock(
        return_value=httpx.Response(
            202, json={"agent_id": "skbrand_3", "job_id": "job_3"}
        )
    )
    respx.get(f"{BASE_URL}/jobs/job_3").mock(
        side_effect=[
            httpx.Response(200, json={"job_id": "job_3", "status": "queued"}),
            httpx.Response(200, json={"job_id": "job_3", "status": "crawling"}),
            httpx.Response(
                200,
                json={
                    "job_id": "job_3",
                    "status": "succeeded",
                    "embed": {
                        "widget_url": "https://w.example",
                        "snippet": "<script></script>",
                        "is_public": True,
                    },
                },
            ),
        ]
    )

    result = await admin.brand_agents.create_and_wait(
        name="C",
        seed_url="https://c.example",
        poll_interval=0.01,
        timeout=5,
    )

    assert result.status == "succeeded"
    assert result.embed is not None
    assert result.embed.snippet == "<script></script>"


@respx.mock
async def test_create_and_wait_raises_on_failure(admin: AdminClient) -> None:
    respx.post(f"{BASE_URL}/brand-agents").mock(
        return_value=httpx.Response(202, json={"agent_id": "s4", "job_id": "job_4"})
    )
    respx.get(f"{BASE_URL}/jobs/job_4").mock(
        side_effect=[
            httpx.Response(200, json={"job_id": "job_4", "status": "crawling"}),
            httpx.Response(
                200,
                json={
                    "job_id": "job_4",
                    "status": "failed",
                    "error_summary": "no pages extracted",
                },
            ),
        ]
    )

    with pytest.raises(SketricGenJobError) as excinfo:
        await admin.brand_agents.create_and_wait(
            name="D", seed_url="https://d.example", poll_interval=0.01, timeout=5
        )

    assert excinfo.value.job_id == "job_4"
    assert excinfo.value.status == "failed"
    assert "no pages extracted" in str(excinfo.value)


@respx.mock
async def test_create_and_wait_times_out(admin: AdminClient) -> None:
    respx.post(f"{BASE_URL}/brand-agents").mock(
        return_value=httpx.Response(202, json={"agent_id": "s5", "job_id": "job_5"})
    )
    respx.get(f"{BASE_URL}/jobs/job_5").mock(
        return_value=httpx.Response(200, json={"job_id": "job_5", "status": "queued"})
    )

    with pytest.raises(SketricGenTimeoutError):
        await admin.brand_agents.create_and_wait(
            name="E", seed_url="https://e.example", poll_interval=0.01, timeout=0
        )


@respx.mock
def test_create_and_wait_sync_success(admin: AdminClient) -> None:
    respx.post(f"{BASE_URL}/brand-agents").mock(
        return_value=httpx.Response(202, json={"agent_id": "s6", "job_id": "job_6"})
    )
    respx.get(f"{BASE_URL}/jobs/job_6").mock(
        side_effect=[
            httpx.Response(200, json={"job_id": "job_6", "status": "queued"}),
            httpx.Response(200, json={"job_id": "job_6", "status": "succeeded"}),
        ]
    )

    result = admin.brand_agents.create_and_wait_sync(
        name="F", seed_url="https://f.example", poll_interval=0.01, timeout=5
    )
    assert result.status == "succeeded"


@respx.mock
async def test_get_brand_agent(admin: AdminClient) -> None:
    route = respx.get(f"{BASE_URL}/brand-agents/skbrand_1").mock(
        return_value=httpx.Response(
            200,
            json={
                "agent": {"agent_id": "skbrand_1"},
                "settings": {"agent_name": "Bot", "model": "gpt-4o"},
                "structure": {"agent": 1, "file_search": 1},
            },
        )
    )

    detail = await admin.brand_agents.get("skbrand_1")

    assert route.calls.last.request.url.path == "/admin/v1/brand-agents/skbrand_1"
    assert detail.settings is not None
    assert detail.settings["model"] == "gpt-4o"
    assert detail.structure == {"agent": 1, "file_search": 1}


@respx.mock
async def test_update_sends_only_supplied_fields(admin: AdminClient) -> None:
    route = respx.patch(f"{BASE_URL}/brand-agents/skbrand_1").mock(
        return_value=httpx.Response(
            200,
            json={
                "updated": ["instructions", "knowledge_base_ids"],
                "file_search_node_added": True,
                "republished": True,
            },
        )
    )

    result = await admin.brand_agents.update(
        "skbrand_1",
        instructions="Be concise",
        knowledge_base_ids=["kb1", "kb2"],
    )

    request = route.calls.last.request
    assert request.method == "PATCH"
    assert request_body(request) == {
        "instructions": "Be concise",
        "knowledge_base_ids": ["kb1", "kb2"],
    }
    assert result.updated == ["instructions", "knowledge_base_ids"]
    assert result.file_search_node_added is True


@respx.mock
def test_update_sync(admin: AdminClient) -> None:
    respx.patch(f"{BASE_URL}/brand-agents/skbrand_2").mock(
        return_value=httpx.Response(200, json={"updated": ["model"]})
    )
    result = admin.brand_agents.update_sync("skbrand_2", model="gpt-4o")
    assert result.updated == ["model"]


@respx.mock
async def test_get_widget_config(admin: AdminClient) -> None:
    route = respx.get(f"{BASE_URL}/brand-agents/skbrand_1/widget-config").mock(
        return_value=httpx.Response(
            200,
            json={
                "agent_id": "skbrand_1",
                "exists": True,
                "widget_config": {"theme": "dark", "primaryColor": "#112233"},
                "branding_removal_entitled": False,
            },
        )
    )

    config = await admin.brand_agents.get_widget_config("skbrand_1")

    assert (
        route.calls.last.request.url.path
        == "/admin/v1/brand-agents/skbrand_1/widget-config"
    )
    assert config.widget_config["theme"] == "dark"
    assert config.exists is True


@respx.mock
async def test_update_widget_config(admin: AdminClient) -> None:
    route = respx.patch(f"{BASE_URL}/brand-agents/skbrand_1/widget-config").mock(
        return_value=httpx.Response(
            200,
            json={
                "agent_id": "skbrand_1",
                "updated": ["theme"],
                "widget_config": {"theme": "light"},
            },
        )
    )

    result = await admin.brand_agents.update_widget_config("skbrand_1", theme="light")

    assert request_body(route.calls.last.request) == {"theme": "light"}
    assert result.updated == ["theme"]


@respx.mock
def test_update_widget_config_sync(admin: AdminClient) -> None:
    respx.patch(f"{BASE_URL}/brand-agents/s2/widget-config").mock(
        return_value=httpx.Response(
            200, json={"agent_id": "s2", "updated": ["isPublic"], "widget_config": {}}
        )
    )
    result = admin.brand_agents.update_widget_config_sync("s2", isPublic=True)
    assert result.updated == ["isPublic"]
