"""Paginated list namespaces: projects, agents, knowledge_bases."""

import httpx
import respx

from sketricgen import AdminClient

from .conftest import BASE_URL


@respx.mock
async def test_projects_list_follows_cursor(admin: AdminClient) -> None:
    route = respx.get(f"{BASE_URL}/projects").mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "projects": [{"project_id": "p1"}, {"project_id": "p2"}],
                    "next_token": "tok1",
                },
            ),
            httpx.Response(
                200,
                json={"projects": [{"project_id": "p3"}], "next_token": None},
            ),
        ]
    )

    projects = [p async for p in admin.projects.list()]

    assert [p.project_id for p in projects] == ["p1", "p2", "p3"]
    assert route.call_count == 2
    # First page carries no cursor; second page threads next_token.
    assert "next_token" not in route.calls[0].request.url.params
    assert route.calls[1].request.url.params["next_token"] == "tok1"
    assert route.calls[0].request.headers["Authorization"] == "Bearer sk_admin_test"


@respx.mock
async def test_short_page_is_not_end_of_list(admin: AdminClient) -> None:
    # A page shorter than `limit` still has more when next_token is present.
    route = respx.get(f"{BASE_URL}/projects").mock(
        side_effect=[
            httpx.Response(
                200, json={"projects": [{"project_id": "p1"}], "next_token": "t"}
            ),
            httpx.Response(
                200, json={"projects": [{"project_id": "p2"}], "next_token": None}
            ),
        ]
    )

    projects = [p async for p in admin.projects.list()]
    assert [p.project_id for p in projects] == ["p1", "p2"]
    assert route.call_count == 2


@respx.mock
def test_projects_list_sync(admin: AdminClient) -> None:
    respx.get(f"{BASE_URL}/projects").mock(
        return_value=httpx.Response(
            200, json={"projects": [{"project_id": "p1"}], "next_token": None}
        )
    )

    projects = list(admin.projects.list_sync())
    assert [p.project_id for p in projects] == ["p1"]


@respx.mock
async def test_agents_list(admin: AdminClient) -> None:
    route = respx.get(f"{BASE_URL}/agents").mock(
        return_value=httpx.Response(
            200,
            json={
                "agents": [{"agent_id": "a1", "name": "One", "agent_type": "workflow"}],
                "next_token": None,
            },
        )
    )

    agents = [a async for a in admin.agents.list()]

    assert route.calls.last.request.url.path == "/admin/v1/agents"
    assert agents[0].agent_id == "a1"
    assert agents[0].agent_type == "workflow"


@respx.mock
def test_agents_list_sync(admin: AdminClient) -> None:
    respx.get(f"{BASE_URL}/agents").mock(
        return_value=httpx.Response(
            200, json={"agents": [{"agent_id": "a9"}], "next_token": None}
        )
    )
    agents = list(admin.agents.list_sync())
    assert agents[0].agent_id == "a9"


@respx.mock
async def test_knowledge_bases_list(admin: AdminClient) -> None:
    route = respx.get(f"{BASE_URL}/knowledge-bases").mock(
        return_value=httpx.Response(
            200,
            json={
                "knowledge_bases": [
                    {
                        "knowledge_base_id": "kb1",
                        "name": "Docs",
                        "agents_using_kb": ["a1"],
                    }
                ],
                "next_token": None,
            },
        )
    )

    kbs = [kb async for kb in admin.knowledge_bases.list()]

    assert route.calls.last.request.url.path == "/admin/v1/knowledge-bases"
    assert kbs[0].knowledge_base_id == "kb1"
    assert kbs[0].agents_using_kb == ["a1"]


@respx.mock
def test_knowledge_bases_list_sync(admin: AdminClient) -> None:
    respx.get(f"{BASE_URL}/knowledge-bases").mock(
        return_value=httpx.Response(
            200,
            json={
                "knowledge_bases": [{"knowledge_base_id": "kbx"}],
                "next_token": None,
            },
        )
    )
    kbs = list(admin.knowledge_bases.list_sync())
    assert kbs[0].knowledge_base_id == "kbx"
