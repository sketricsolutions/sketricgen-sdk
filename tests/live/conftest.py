"""Gating and fixtures for the live probe.

The probe is opt-in on two levels:

1. The ``live`` marker is deselected by default (see ``pyproject.toml``), so a
   plain ``pytest`` run never collects these tests. Run them with
   ``pytest -m live``.
2. Even under ``-m live``, each test skips unless the credential / AWS it needs
   is actually present, so a keyless ``pytest -m live`` skips cleanly instead of
   erroring.

Keys come only from the environment and are never written to any file, fixture,
log, or assertion message.
"""

import os
from typing import Optional

import pytest

from sketricgen import AdminClient, SketricGenClient

from .dynamo import DynamoProbe, DynamoUnavailable
from .fixtures import (
    DEV_ADMIN_BASE_URL,
    DEV_CHAT_BASE_URL,
    DEV_UPLOAD_COMPLETE_URL,
    DEV_UPLOAD_INIT_URL,
)
from .reporter import ProbeReporter

_REPORTER_KEY = pytest.StashKey[ProbeReporter]()


def _env(name: str) -> Optional[str]:
    value = os.getenv(name)
    return value if value else None


@pytest.fixture(scope="session")
def admin_key() -> str:
    key = _env("SKETRICGEN_ADMIN_API_KEY")
    if not key:
        pytest.skip("SKETRICGEN_ADMIN_API_KEY not set; skipping control-plane probe")
    return key


@pytest.fixture(scope="session")
def runtime_key() -> str:
    key = _env("SKETRICGEN_RUNTIME_API_KEY")
    if not key:
        pytest.skip("SKETRICGEN_RUNTIME_API_KEY not set; skipping data-plane probe")
    return key


@pytest.fixture(scope="session")
def admin(admin_key: str) -> AdminClient:
    """Admin client pinned at the dev control plane.

    The shipped ``DEFAULT_ADMIN_BASE_URL`` targets prod, so the probe overrides
    it to dev explicitly rather than relying on the default.
    """
    return AdminClient(api_key=admin_key, base_url=DEV_ADMIN_BASE_URL)


@pytest.fixture(scope="session")
def runtime_client(runtime_key: str) -> SketricGenClient:
    """Data-plane client pointed at dev-chat with dev upload endpoints.

    ``SketricGenClient`` has no public ``base_url`` override, so this test-only
    fixture retargets the private config at the dev host. Shipped defaults are
    untouched.
    """
    client = SketricGenClient(api_key=runtime_key, timeout=120)
    client._config.base_url = DEV_CHAT_BASE_URL
    client._config.upload_init_endpoint = DEV_UPLOAD_INIT_URL
    client._config.upload_complete_endpoint = DEV_UPLOAD_COMPLETE_URL
    return client


@pytest.fixture(scope="session")
def dynamo() -> DynamoProbe:
    """Read-only DynamoDB accessor; skips the probe if AWS is unreachable."""
    probe = DynamoProbe()
    try:
        probe.preflight()
    except DynamoUnavailable as e:
        pytest.skip(f"dev DynamoDB not reachable: {e}")
    return probe


@pytest.fixture(scope="session")
def reporter(request: pytest.FixtureRequest) -> ProbeReporter:
    """One reporter for the session, surfaced in the terminal summary."""
    existing = request.config.stash.get(_REPORTER_KEY, None)
    if existing is None:
        existing = ProbeReporter()
        request.config.stash[_REPORTER_KEY] = existing
    return existing


@pytest.fixture
def write_enabled() -> None:
    """Gate mutating probes behind an explicit opt-in flag."""
    if not _env("SKETRICGEN_LIVE_WRITE"):
        pytest.skip(
            "SKETRICGEN_LIVE_WRITE not set; skipping mutating probe (has real "
            "side effects and cost)"
        )


def pytest_terminal_summary(terminalreporter, exitstatus, config) -> None:
    reporter = config.stash.get(_REPORTER_KEY, None)
    if reporter is None or not reporter.rows:
        return
    terminalreporter.write_sep("=", "live probe report")
    terminalreporter.write_line(reporter.render())
    terminalreporter.write_sep("-", "reminder")
    terminalreporter.write_line(
        "Revoke/rotate the temporary SKETRICGEN_ADMIN_API_KEY and "
        "SKETRICGEN_RUNTIME_API_KEY now that the probe has run."
    )
