"""Shared fixtures for Admin API client tests."""

import json
from typing import Any

import httpx
import pytest

from sketricgen import AdminClient

BASE_URL = "https://admin.test/admin/v1"
API_KEY = "sk_admin_test"


@pytest.fixture
def admin() -> AdminClient:
    """An AdminClient pointed at the mocked control-plane host."""
    return AdminClient(api_key=API_KEY, base_url=BASE_URL)


def request_body(request: httpx.Request) -> dict[str, Any]:
    """Decode a captured request's JSON body."""
    return json.loads(request.content)
