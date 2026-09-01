"""Connectors namespace: catalog, tools, links, connection, attach/detach."""

import httpx
import respx

from sketricgen import AdminClient

from .conftest import BASE_URL, request_body


@respx.mock
async def test_list_connectors(admin: AdminClient) -> None:
    route = respx.get(f"{BASE_URL}/connectors").mock(
        return_value=httpx.Response(
            200,
            json={
                "connectors": [
                    {
                        "app_slug": "gmail",
                        "name": "Gmail",
                        "provider": "pipedream",
                        "supports_connect_link": True,
                        "tools": [{"tool_name": "send_email"}],
                    }
                ]
            },
        )
    )

    connectors = await admin.connectors.list()

    assert route.calls.last.request.url.path == "/admin/v1/connectors"
    assert connectors[0].app_slug == "gmail"
    assert connectors[0].tools[0].tool_name == "send_email"


@respx.mock
def test_list_connectors_sync(admin: AdminClient) -> None:
    respx.get(f"{BASE_URL}/connectors").mock(
        return_value=httpx.Response(200, json={"connectors": [{"app_slug": "slack"}]})
    )
    connectors = admin.connectors.list_sync()
    assert connectors[0].app_slug == "slack"


@respx.mock
async def test_list_tools(admin: AdminClient) -> None:
    route = respx.get(f"{BASE_URL}/connectors/gmail/tools").mock(
        return_value=httpx.Response(
            200,
            json={
                "app_slug": "gmail",
                "provider": "pipedream",
                "restriction": "unrestricted",
                "tools": [{"tool_name": "send_email"}, {"tool_name": "list_labels"}],
                "total": 2,
                "has_more": False,
            },
        )
    )

    tools = await admin.connectors.list_tools("gmail", limit=50, offset=0)

    request = route.calls.last.request
    assert request.url.path == "/admin/v1/connectors/gmail/tools"
    assert request.url.params["limit"] == "50"
    assert request.url.params["offset"] == "0"
    assert tools.restriction == "unrestricted"
    assert [t.tool_name for t in tools.tools] == ["send_email", "list_labels"]


@respx.mock
def test_list_tools_sync(admin: AdminClient) -> None:
    respx.get(f"{BASE_URL}/connectors/discord/tools").mock(
        return_value=httpx.Response(
            200, json={"app_slug": "discord", "tools": [], "restriction": "curated"}
        )
    )
    tools = admin.connectors.list_tools_sync("discord")
    assert tools.restriction == "curated"


@respx.mock
async def test_create_link(admin: AdminClient) -> None:
    route = respx.post(f"{BASE_URL}/connectors/gmail/connect-link").mock(
        return_value=httpx.Response(
            200,
            json={
                "app_slug": "gmail",
                "provider": "pipedream",
                "already_connected": False,
                "connect_url": "https://connect.example/abc",
                "expires_at": "2026-01-01T00:00:00Z",
            },
        )
    )

    link = await admin.connectors.create_link("gmail", agent_type="brand-agent")

    request = route.calls.last.request
    assert request.url.path == "/admin/v1/connectors/gmail/connect-link"
    assert request_body(request) == {"agent_type": "brand-agent"}
    assert link.connect_url == "https://connect.example/abc"


@respx.mock
def test_create_link_sync(admin: AdminClient) -> None:
    respx.post(f"{BASE_URL}/connectors/gmail/connect-link").mock(
        return_value=httpx.Response(
            200,
            json={"app_slug": "gmail", "already_connected": True, "connect_url": None},
        )
    )
    link = admin.connectors.create_link_sync("gmail")
    assert link.already_connected is True


@respx.mock
async def test_check_connection(admin: AdminClient) -> None:
    route = respx.get(f"{BASE_URL}/connectors/gmail/connection").mock(
        return_value=httpx.Response(
            200, json={"app_slug": "gmail", "provider": "pipedream", "connected": True}
        )
    )

    status = await admin.connectors.check_connection(
        "gmail", agent_type="brand-agent", project_id="p1"
    )

    request = route.calls.last.request
    assert request.url.path == "/admin/v1/connectors/gmail/connection"
    assert request.url.params["agent_type"] == "brand-agent"
    assert request.url.params["project_id"] == "p1"
    assert status.connected is True


@respx.mock
async def test_attach(admin: AdminClient) -> None:
    route = respx.post(f"{BASE_URL}/agents/skbrand_1/connectors").mock(
        return_value=httpx.Response(
            200,
            json={
                "agent_id": "skbrand_1",
                "app_slug": "gmail",
                "provider": "pipedream",
                "allowed_tools": ["send_email"],
                "unrestricted": False,
                "attached": True,
                "changed": True,
            },
        )
    )

    result = await admin.connectors.attach(
        "skbrand_1", "gmail", allowed_tools=["send_email"]
    )

    request = route.calls.last.request
    assert request.url.path == "/admin/v1/agents/skbrand_1/connectors"
    assert request_body(request) == {
        "app_slug": "gmail",
        "allowed_tools": ["send_email"],
    }
    assert result.attached is True
    assert result.allowed_tools == ["send_email"]


@respx.mock
def test_attach_sync_omits_allowed_tools(admin: AdminClient) -> None:
    route = respx.post(f"{BASE_URL}/agents/a1/connectors").mock(
        return_value=httpx.Response(
            200, json={"agent_id": "a1", "app_slug": "web_search", "attached": True}
        )
    )
    result = admin.connectors.attach_sync("a1", "web_search")
    assert request_body(route.calls.last.request) == {"app_slug": "web_search"}
    assert result.attached is True


@respx.mock
async def test_detach(admin: AdminClient) -> None:
    route = respx.delete(f"{BASE_URL}/agents/skbrand_1/connectors/gmail").mock(
        return_value=httpx.Response(
            200, json={"agent_id": "skbrand_1", "app_slug": "gmail", "attached": False}
        )
    )

    result = await admin.connectors.detach("skbrand_1", "gmail")

    request = route.calls.last.request
    assert request.method == "DELETE"
    assert request.url.path == "/admin/v1/agents/skbrand_1/connectors/gmail"
    assert result.attached is False


@respx.mock
def test_detach_sync(admin: AdminClient) -> None:
    respx.delete(f"{BASE_URL}/agents/a1/connectors/slack").mock(
        return_value=httpx.Response(
            200, json={"agent_id": "a1", "app_slug": "slack", "attached": False}
        )
    )
    result = admin.connectors.detach_sync("a1", "slack")
    assert result.attached is False
