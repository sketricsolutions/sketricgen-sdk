"""Foundation: construction, auth header, whoami, and error mapping."""

import httpx
import pytest
import respx

from sketricgen import (
    AdminClient,
    SketricGenAdminError,
    SketricGenAuthenticationError,
)
from sketricgen.admin.client import DEFAULT_ADMIN_BASE_URL

from .conftest import BASE_URL


def test_missing_key_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SKETRICGEN_ADMIN_API_KEY", raising=False)
    with pytest.raises(ValueError, match="SKETRICGEN_ADMIN_API_KEY"):
        AdminClient()


def test_key_read_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SKETRICGEN_ADMIN_API_KEY", "sk_admin_env")
    client = AdminClient()
    assert client._api_key == "sk_admin_env"


def test_default_base_url() -> None:
    client = AdminClient(api_key="sk_admin_x")
    assert client._base_url == DEFAULT_ADMIN_BASE_URL


def test_base_url_override_is_trimmed() -> None:
    client = AdminClient(api_key="sk_admin_x", base_url="https://sandbox.test/v1/")
    assert client._base_url == "https://sandbox.test/v1"


@respx.mock
async def test_whoami_request_and_response(admin: AdminClient) -> None:
    route = respx.get(f"{BASE_URL}/teamspaces").mock(
        return_value=httpx.Response(
            200,
            json={
                "teamspaces": [
                    {
                        "teamspace_id": "ts_1",
                        "slug": "acme",
                        "display_name": "Acme",
                        "subscription_plan": "builder",
                    }
                ]
            },
        )
    )

    me = await admin.whoami()

    assert route.called
    request = route.calls.last.request
    assert request.method == "GET"
    assert request.url.path == "/admin/v1/teamspaces"
    assert request.headers["Authorization"] == "Bearer sk_admin_test"
    assert me.teamspace_id == "ts_1"
    assert me.display_name == "Acme"


@respx.mock
def test_whoami_sync(admin: AdminClient) -> None:
    respx.get(f"{BASE_URL}/teamspaces").mock(
        return_value=httpx.Response(
            200, json={"teamspaces": [{"teamspace_id": "ts_9"}]}
        )
    )

    me = admin.whoami_sync()
    assert me.teamspace_id == "ts_9"


@respx.mock
async def test_admin_error_maps_status_and_code(admin: AdminClient) -> None:
    respx.get(f"{BASE_URL}/teamspaces").mock(
        return_value=httpx.Response(
            403, json={"error": "wrong project", "code": "project_scope_mismatch"}
        )
    )

    with pytest.raises(SketricGenAdminError) as excinfo:
        await admin.whoami()

    err = excinfo.value
    assert err.status_code == 403
    assert err.code == "project_scope_mismatch"
    assert "wrong project" in str(err)


@respx.mock
async def test_401_maps_to_authentication_error(admin: AdminClient) -> None:
    respx.get(f"{BASE_URL}/teamspaces").mock(
        return_value=httpx.Response(
            401, json={"error": "bad key", "code": "invalid_key"}
        )
    )

    with pytest.raises(SketricGenAuthenticationError) as excinfo:
        await admin.whoami()

    assert excinfo.value.status_code == 401


@respx.mock
def test_admin_error_sync_path(admin: AdminClient) -> None:
    respx.get(f"{BASE_URL}/teamspaces").mock(
        return_value=httpx.Response(
            404, json={"error": "nope", "code": "teamspace_not_found"}
        )
    )

    with pytest.raises(SketricGenAdminError) as excinfo:
        admin.whoami_sync()

    assert excinfo.value.code == "teamspace_not_found"
