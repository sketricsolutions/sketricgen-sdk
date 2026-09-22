"""Shared fixtures for Admin API client tests."""

import json
from typing import Any

import httpx
import pytest

from sketricgen import SketricGenClient

BASE_URL = "https://admin.test/admin/v1"
API_KEY = "sk_api_test"


@pytest.fixture
def admin() -> SketricGenClient:
    """A unified client pointed at the mocked control-plane host."""
    client = SketricGenClient(api_key=API_KEY)
    client._admin._base_url = BASE_URL
    return client


def request_body(request: httpx.Request) -> dict[str, Any]:
    """Decode a captured request's JSON body."""
    return json.loads(request.content)
