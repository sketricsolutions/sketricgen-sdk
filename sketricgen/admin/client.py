"""
SketricGen control-plane (Admin API) client.

``AdminClient`` wraps the curated automation surface of the Teamspace v2 Admin
API (`/admin/v1/*`) with typed, resource-grouped methods. It authenticates with
an admin key (`Authorization: Bearer sk_admin_…`) and is a distinct client from
the data-plane ``SketricGenClient`` — the two credentials are not
interchangeable.
"""

import asyncio
import os
import time
from collections.abc import AsyncIterator, Iterator
from typing import Any, Optional, TypeVar

import httpx

from sketricgen.admin.models import (
    AdminModel,
    Agent,
    BrandAgentDetail,
    BrandAgentJob,
    BrandAgentTemplate,
    BrandAgentUpdateResult,
    ConnectionStatus,
    ConnectLink,
    Connector,
    ConnectorAttachment,
    ConnectorDetachment,
    ConnectorTools,
    JobStatus,
    KnowledgeBase,
    Project,
    Teamspace,
    WidgetConfig,
    WidgetConfigUpdateResult,
)
from sketricgen.exceptions import (
    SketricGenAdminError,
    SketricGenAuthenticationError,
    SketricGenJobError,
    SketricGenNetworkError,
    SketricGenTimeoutError,
)

# The control-plane host is shipped with the SDK; the consumer supplies only a
# key. A per-deploy execute-api host — if production runs a different API id,
# only this constant changes. There is intentionally no env-var path for it.
# (The stage segment is named `dev` even in production, per the backend wiring.)
DEFAULT_ADMIN_BASE_URL = (
    "https://v9xof9ohlg.execute-api.us-east-1.amazonaws.com/dev/admin/v1"
)

DEFAULT_TIMEOUT = 30
DEFAULT_POLL_INTERVAL = 10.0
DEFAULT_WAIT_TIMEOUT = 600.0

_TERMINAL_JOB_STATES = frozenset({"succeeded", "failed"})

M = TypeVar("M", bound=AdminModel)

# Inside ConnectorsNamespace the public ``list`` method shadows the builtin, so
# ``list[...]`` annotations there are written through these module-level aliases.
ConnectorList = list[Connector]
AllowedToolNames = list[str]


def _clean_query(
    query: Optional[dict[str, Any]],
) -> dict[str, Any]:
    """Drop ``None`` and empty-string params, matching the API's URL builder."""
    if not query:
        return {}
    return {k: v for k, v in query.items() if v is not None and v != ""}


def _prune_none(body: dict[str, Any]) -> dict[str, Any]:
    """Keep only the fields the caller actually supplied."""
    return {k: v for k, v in body.items() if v is not None}


class AdminClient:
    """
    Control-plane client for the SketricGen Admin API.

    Example:
        ```python
        from sketricgen import AdminClient

        admin = AdminClient()  # reads SKETRICGEN_ADMIN_API_KEY

        me = await admin.whoami()
        async for project in admin.projects.list():
            print(project.display_name)
        ```
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """
        Initialize the Admin client.

        Args:
            api_key: Admin API key. Falls back to ``SKETRICGEN_ADMIN_API_KEY``.
            base_url: Optional control-plane base URL override (for testing or
                self-hosting). Defaults to the SDK's baked-in host.
            timeout: Per-request timeout in seconds.

        Raises:
            ValueError: If no admin key is provided or found in the environment.
        """
        resolved_key = api_key or os.getenv("SKETRICGEN_ADMIN_API_KEY")
        if not resolved_key:
            raise ValueError(
                "Admin API key is required. Set the SKETRICGEN_ADMIN_API_KEY "
                "environment variable or pass api_key=... to AdminClient."
            )
        self._api_key = resolved_key
        self._base_url = (base_url or DEFAULT_ADMIN_BASE_URL).rstrip("/")
        self._timeout = timeout

        self.projects = ProjectsNamespace(self)
        self.agents = AgentsNamespace(self)
        self.knowledge_bases = KnowledgeBasesNamespace(self)
        self.brand_agents = BrandAgentsNamespace(self)
        self.connectors = ConnectorsNamespace(self)

    # ------------------------------------------------------------------
    # Request core
    # ------------------------------------------------------------------

    def _url(self, path: str) -> str:
        return f"{self._base_url}{path}"

    def _headers(self, has_body: bool) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
        }
        if has_body:
            headers["Content-Type"] = "application/json"
        return headers

    def _handle_error(self, response: httpx.Response) -> None:
        try:
            body = response.json()
        except Exception:
            body = None

        if isinstance(body, dict):
            code = body.get("code")
            message = body.get("error")
        else:
            code = None
            message = None
        message = message or response.text or f"HTTP {response.status_code}"

        if response.status_code == 401:
            raise SketricGenAuthenticationError(message)

        raise SketricGenAdminError(
            status_code=response.status_code,
            code=code or "admin_api_error",
            message=message,
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        query: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method,
                    self._url(path),
                    params=_clean_query(query),
                    json=json,
                    headers=self._headers(json is not None),
                    timeout=self._timeout,
                )
        except httpx.TimeoutException as e:
            raise SketricGenTimeoutError(f"Request timed out: {e}") from e
        except httpx.HTTPError as e:
            raise SketricGenNetworkError(f"Network error: {e}") from e

        if response.status_code >= 400:
            self._handle_error(response)
        return response.json() if response.content else {}

    def _request_sync(
        self,
        method: str,
        path: str,
        *,
        query: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        try:
            with httpx.Client() as client:
                response = client.request(
                    method,
                    self._url(path),
                    params=_clean_query(query),
                    json=json,
                    headers=self._headers(json is not None),
                    timeout=self._timeout,
                )
        except httpx.TimeoutException as e:
            raise SketricGenTimeoutError(f"Request timed out: {e}") from e
        except httpx.HTTPError as e:
            raise SketricGenNetworkError(f"Network error: {e}") from e

        if response.status_code >= 400:
            self._handle_error(response)
        return response.json() if response.content else {}

    # ------------------------------------------------------------------
    # Pagination
    # ------------------------------------------------------------------

    async def _paginate(
        self,
        path: str,
        items_key: str,
        model: type[M],
    ) -> AsyncIterator[M]:
        next_token: Optional[str] = None
        while True:
            query = {"next_token": next_token} if next_token else None
            data = await self._request("GET", path, query=query)
            for item in data.get(items_key) or []:
                yield model.model_validate(item)
            next_token = data.get("next_token")
            if next_token is None:
                break

    def _paginate_sync(
        self,
        path: str,
        items_key: str,
        model: type[M],
    ) -> Iterator[M]:
        next_token: Optional[str] = None
        while True:
            query = {"next_token": next_token} if next_token else None
            data = self._request_sync("GET", path, query=query)
            for item in data.get(items_key) or []:
                yield model.model_validate(item)
            next_token = data.get("next_token")
            if next_token is None:
                break

    # ------------------------------------------------------------------
    # whoami
    # ------------------------------------------------------------------

    async def whoami(self) -> Teamspace:
        """Return the caller's teamspace identity (``GET /teamspaces``)."""
        data = await self._request("GET", "/teamspaces")
        return self._teamspace_from(data)

    def whoami_sync(self) -> Teamspace:
        """Synchronous twin of :meth:`whoami`."""
        data = self._request_sync("GET", "/teamspaces")
        return self._teamspace_from(data)

    @staticmethod
    def _teamspace_from(data: dict[str, Any]) -> Teamspace:
        teamspaces = data.get("teamspaces") or []
        if not teamspaces:
            raise SketricGenAdminError(
                status_code=500,
                code="invalid_response",
                message="teamspaces response contained no teamspace",
            )
        return Teamspace.model_validate(teamspaces[0])


class ProjectsNamespace:
    def __init__(self, client: AdminClient) -> None:
        self._client = client

    def list(self) -> AsyncIterator[Project]:
        """Lazily page through every project (``GET /projects``)."""
        return self._client._paginate("/projects", "projects", Project)

    def list_sync(self) -> Iterator[Project]:
        """Synchronous twin of :meth:`list`."""
        return self._client._paginate_sync("/projects", "projects", Project)


class AgentsNamespace:
    def __init__(self, client: AdminClient) -> None:
        self._client = client

    def list(self) -> AsyncIterator[Agent]:
        """Lazily page through every agent (``GET /agents``)."""
        return self._client._paginate("/agents", "agents", Agent)

    def list_sync(self) -> Iterator[Agent]:
        """Synchronous twin of :meth:`list`."""
        return self._client._paginate_sync("/agents", "agents", Agent)


class KnowledgeBasesNamespace:
    def __init__(self, client: AdminClient) -> None:
        self._client = client

    def list(self) -> AsyncIterator[KnowledgeBase]:
        """Lazily page through every knowledge base (``GET /knowledge-bases``)."""
        return self._client._paginate(
            "/knowledge-bases", "knowledge_bases", KnowledgeBase
        )

    def list_sync(self) -> Iterator[KnowledgeBase]:
        """Synchronous twin of :meth:`list`."""
        return self._client._paginate_sync(
            "/knowledge-bases", "knowledge_bases", KnowledgeBase
        )


class BrandAgentsNamespace:
    def __init__(self, client: AdminClient) -> None:
        self._client = client

    # -- templates -----------------------------------------------------

    async def list_templates(
        self, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> list[BrandAgentTemplate]:
        """Return the brand-agent template catalog."""
        data = await self._client._request(
            "GET",
            "/brand-agent-templates",
            query={"limit": limit, "offset": offset},
        )
        return self._templates_from(data)

    def list_templates_sync(
        self, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> list[BrandAgentTemplate]:
        """Synchronous twin of :meth:`list_templates`."""
        data = self._client._request_sync(
            "GET",
            "/brand-agent-templates",
            query={"limit": limit, "offset": offset},
        )
        return self._templates_from(data)

    @staticmethod
    def _templates_from(data: dict[str, Any]) -> list[BrandAgentTemplate]:
        return [
            BrandAgentTemplate.model_validate(t)
            for t in data.get("brand_agent_templates") or []
        ]

    # -- create / status ----------------------------------------------

    def _create_body(
        self,
        name: str,
        seed_url: str,
        description: Optional[str],
        project_id: Optional[str],
        publish_widget: Optional[bool],
        template_slug: Optional[str],
        knowledge_base_id: Optional[str],
    ) -> dict[str, Any]:
        return _prune_none(
            {
                "name": name,
                "seed_url": seed_url,
                "description": description,
                "project_id": project_id,
                "publish_widget": publish_widget,
                "template_slug": template_slug,
                "knowledge_base_id": knowledge_base_id,
            }
        )

    async def create(
        self,
        name: str,
        seed_url: str,
        description: Optional[str] = None,
        project_id: Optional[str] = None,
        publish_widget: Optional[bool] = None,
        template_slug: Optional[str] = None,
        knowledge_base_id: Optional[str] = None,
    ) -> BrandAgentJob:
        """Start brand-agent provisioning and return the job handle (202)."""
        body = self._create_body(
            name,
            seed_url,
            description,
            project_id,
            publish_widget,
            template_slug,
            knowledge_base_id,
        )
        data = await self._client._request("POST", "/brand-agents", json=body)
        return BrandAgentJob.model_validate(data)

    def create_sync(
        self,
        name: str,
        seed_url: str,
        description: Optional[str] = None,
        project_id: Optional[str] = None,
        publish_widget: Optional[bool] = None,
        template_slug: Optional[str] = None,
        knowledge_base_id: Optional[str] = None,
    ) -> BrandAgentJob:
        """Synchronous twin of :meth:`create`."""
        body = self._create_body(
            name,
            seed_url,
            description,
            project_id,
            publish_widget,
            template_slug,
            knowledge_base_id,
        )
        data = self._client._request_sync("POST", "/brand-agents", json=body)
        return BrandAgentJob.model_validate(data)

    async def get_status(self, job_id: str) -> JobStatus:
        """Report provisioning progress (``GET /jobs/{job_id}``)."""
        data = await self._client._request("GET", f"/jobs/{job_id}")
        return JobStatus.model_validate(data)

    def get_status_sync(self, job_id: str) -> JobStatus:
        """Synchronous twin of :meth:`get_status`."""
        data = self._client._request_sync("GET", f"/jobs/{job_id}")
        return JobStatus.model_validate(data)

    async def create_and_wait(
        self,
        name: str,
        seed_url: str,
        description: Optional[str] = None,
        project_id: Optional[str] = None,
        publish_widget: Optional[bool] = None,
        template_slug: Optional[str] = None,
        knowledge_base_id: Optional[str] = None,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        timeout: float = DEFAULT_WAIT_TIMEOUT,
    ) -> JobStatus:
        """Create a brand agent and poll to a terminal state.

        Returns the finished :class:`JobStatus` (carrying the ``embed`` snippet)
        on success. Raises :class:`SketricGenJobError` if the job fails and
        :class:`SketricGenTimeoutError` if it does not finish within ``timeout``.
        """
        job = await self.create(
            name,
            seed_url,
            description,
            project_id,
            publish_widget,
            template_slug,
            knowledge_base_id,
        )
        deadline = time.monotonic() + timeout
        while True:
            status = await self.get_status(job.job_id)
            terminal = self._check_terminal(status)
            if terminal is not None:
                return terminal
            if time.monotonic() >= deadline:
                raise SketricGenTimeoutError(
                    f"Brand agent job {job.job_id} did not finish within "
                    f"{timeout}s (last status: {status.status})"
                )
            await asyncio.sleep(poll_interval)

    def create_and_wait_sync(
        self,
        name: str,
        seed_url: str,
        description: Optional[str] = None,
        project_id: Optional[str] = None,
        publish_widget: Optional[bool] = None,
        template_slug: Optional[str] = None,
        knowledge_base_id: Optional[str] = None,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        timeout: float = DEFAULT_WAIT_TIMEOUT,
    ) -> JobStatus:
        """Synchronous twin of :meth:`create_and_wait`."""
        job = self.create_sync(
            name,
            seed_url,
            description,
            project_id,
            publish_widget,
            template_slug,
            knowledge_base_id,
        )
        deadline = time.monotonic() + timeout
        while True:
            status = self.get_status_sync(job.job_id)
            terminal = self._check_terminal(status)
            if terminal is not None:
                return terminal
            if time.monotonic() >= deadline:
                raise SketricGenTimeoutError(
                    f"Brand agent job {job.job_id} did not finish within "
                    f"{timeout}s (last status: {status.status})"
                )
            time.sleep(poll_interval)

    @staticmethod
    def _check_terminal(status: JobStatus) -> Optional[JobStatus]:
        if status.status not in _TERMINAL_JOB_STATES:
            return None
        if status.status == "failed":
            raise SketricGenJobError(
                message=(
                    f"Brand agent job {status.job_id} failed: "
                    f"{status.error_summary or 'no error summary provided'}"
                ),
                job_id=status.job_id,
                status=status.status,
                error_summary=status.error_summary,
            )
        return status

    # -- get / update --------------------------------------------------

    async def get(self, agent_id: str) -> BrandAgentDetail:
        """Return a brand agent's settings and structure."""
        data = await self._client._request("GET", f"/brand-agents/{agent_id}")
        return BrandAgentDetail.model_validate(data)

    def get_sync(self, agent_id: str) -> BrandAgentDetail:
        """Synchronous twin of :meth:`get`."""
        data = self._client._request_sync("GET", f"/brand-agents/{agent_id}")
        return BrandAgentDetail.model_validate(data)

    def _update_body(
        self,
        display_name: Optional[str],
        agent_name: Optional[str],
        instructions: Optional[str],
        model: Optional[str],
        knowledge_base_ids: Optional[list[str]],
    ) -> dict[str, Any]:
        return _prune_none(
            {
                "display_name": display_name,
                "agent_name": agent_name,
                "instructions": instructions,
                "model": model,
                "knowledge_base_ids": knowledge_base_ids,
            }
        )

    async def update(
        self,
        agent_id: str,
        display_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        instructions: Optional[str] = None,
        model: Optional[str] = None,
        knowledge_base_ids: Optional[list[str]] = None,
    ) -> BrandAgentUpdateResult:
        """Patch the exposed brand-agent fields (``PATCH /brand-agents/{id}``)."""
        body = self._update_body(
            display_name, agent_name, instructions, model, knowledge_base_ids
        )
        data = await self._client._request(
            "PATCH", f"/brand-agents/{agent_id}", json=body
        )
        return BrandAgentUpdateResult.model_validate(data)

    def update_sync(
        self,
        agent_id: str,
        display_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        instructions: Optional[str] = None,
        model: Optional[str] = None,
        knowledge_base_ids: Optional[list[str]] = None,
    ) -> BrandAgentUpdateResult:
        """Synchronous twin of :meth:`update`."""
        body = self._update_body(
            display_name, agent_name, instructions, model, knowledge_base_ids
        )
        data = self._client._request_sync(
            "PATCH", f"/brand-agents/{agent_id}", json=body
        )
        return BrandAgentUpdateResult.model_validate(data)

    # -- widget config -------------------------------------------------

    async def get_widget_config(self, agent_id: str) -> WidgetConfig:
        """Read the published widget configuration."""
        data = await self._client._request(
            "GET", f"/brand-agents/{agent_id}/widget-config"
        )
        return WidgetConfig.model_validate(data)

    def get_widget_config_sync(self, agent_id: str) -> WidgetConfig:
        """Synchronous twin of :meth:`get_widget_config`."""
        data = self._client._request_sync(
            "GET", f"/brand-agents/{agent_id}/widget-config"
        )
        return WidgetConfig.model_validate(data)

    async def update_widget_config(
        self, agent_id: str, **fields: Any
    ) -> WidgetConfigUpdateResult:
        """Patch the widget configuration with the supplied fields."""
        data = await self._client._request(
            "PATCH",
            f"/brand-agents/{agent_id}/widget-config",
            json=_prune_none(fields),
        )
        return WidgetConfigUpdateResult.model_validate(data)

    def update_widget_config_sync(
        self, agent_id: str, **fields: Any
    ) -> WidgetConfigUpdateResult:
        """Synchronous twin of :meth:`update_widget_config`."""
        data = self._client._request_sync(
            "PATCH",
            f"/brand-agents/{agent_id}/widget-config",
            json=_prune_none(fields),
        )
        return WidgetConfigUpdateResult.model_validate(data)


class ConnectorsNamespace:
    def __init__(self, client: AdminClient) -> None:
        self._client = client

    async def list(self) -> ConnectorList:
        """Return the curated brand-connector catalog (``GET /connectors``)."""
        data = await self._client._request("GET", "/connectors")
        return self._connectors_from(data)

    def list_sync(self) -> ConnectorList:
        """Synchronous twin of :meth:`list`."""
        data = self._client._request_sync("GET", "/connectors")
        return self._connectors_from(data)

    @staticmethod
    def _connectors_from(data: dict[str, Any]) -> ConnectorList:
        return [Connector.model_validate(c) for c in data.get("connectors") or []]

    async def list_tools(
        self, app_slug: str, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> ConnectorTools:
        """Return the grantable tool names for one connector."""
        data = await self._client._request(
            "GET",
            f"/connectors/{app_slug}/tools",
            query={"limit": limit, "offset": offset},
        )
        return ConnectorTools.model_validate(data)

    def list_tools_sync(
        self, app_slug: str, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> ConnectorTools:
        """Synchronous twin of :meth:`list_tools`."""
        data = self._client._request_sync(
            "GET",
            f"/connectors/{app_slug}/tools",
            query={"limit": limit, "offset": offset},
        )
        return ConnectorTools.model_validate(data)

    async def create_link(
        self,
        app_slug: str,
        project_id: Optional[str] = None,
        agent_type: Optional[str] = None,
    ) -> ConnectLink:
        """Mint a hosted consent URL for a connector."""
        body = _prune_none({"project_id": project_id, "agent_type": agent_type})
        data = await self._client._request(
            "POST", f"/connectors/{app_slug}/connect-link", json=body
        )
        return ConnectLink.model_validate(data)

    def create_link_sync(
        self,
        app_slug: str,
        project_id: Optional[str] = None,
        agent_type: Optional[str] = None,
    ) -> ConnectLink:
        """Synchronous twin of :meth:`create_link`."""
        body = _prune_none({"project_id": project_id, "agent_type": agent_type})
        data = self._client._request_sync(
            "POST", f"/connectors/{app_slug}/connect-link", json=body
        )
        return ConnectLink.model_validate(data)

    async def check_connection(
        self,
        app_slug: str,
        agent_type: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> ConnectionStatus:
        """Report whether a connected account exists for a connector."""
        data = await self._client._request(
            "GET",
            f"/connectors/{app_slug}/connection",
            query={"agent_type": agent_type, "project_id": project_id},
        )
        return ConnectionStatus.model_validate(data)

    def check_connection_sync(
        self,
        app_slug: str,
        agent_type: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> ConnectionStatus:
        """Synchronous twin of :meth:`check_connection`."""
        data = self._client._request_sync(
            "GET",
            f"/connectors/{app_slug}/connection",
            query={"agent_type": agent_type, "project_id": project_id},
        )
        return ConnectionStatus.model_validate(data)

    async def attach(
        self,
        agent_id: str,
        app_slug: str,
        allowed_tools: Optional[AllowedToolNames] = None,
    ) -> ConnectorAttachment:
        """Attach a connector's tools to an agent."""
        body = _prune_none({"app_slug": app_slug, "allowed_tools": allowed_tools})
        data = await self._client._request(
            "POST", f"/agents/{agent_id}/connectors", json=body
        )
        return ConnectorAttachment.model_validate(data)

    def attach_sync(
        self,
        agent_id: str,
        app_slug: str,
        allowed_tools: Optional[AllowedToolNames] = None,
    ) -> ConnectorAttachment:
        """Synchronous twin of :meth:`attach`."""
        body = _prune_none({"app_slug": app_slug, "allowed_tools": allowed_tools})
        data = self._client._request_sync(
            "POST", f"/agents/{agent_id}/connectors", json=body
        )
        return ConnectorAttachment.model_validate(data)

    async def detach(self, agent_id: str, app_slug: str) -> ConnectorDetachment:
        """Remove a connector from an agent."""
        data = await self._client._request(
            "DELETE", f"/agents/{agent_id}/connectors/{app_slug}"
        )
        return ConnectorDetachment.model_validate(data)

    def detach_sync(self, agent_id: str, app_slug: str) -> ConnectorDetachment:
        """Synchronous twin of :meth:`detach`."""
        data = self._client._request_sync(
            "DELETE", f"/agents/{agent_id}/connectors/{app_slug}"
        )
        return ConnectorDetachment.model_validate(data)
