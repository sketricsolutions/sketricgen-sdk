"""
Control-plane (Admin API) response models.

Pydantic models mirroring the `/admin/v1/*` response shapes. Every model
ignores unknown fields (`extra="ignore"`) so a server-side field addition does
not break a pinned SDK version.
"""

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class AdminModel(BaseModel):
    """Base for all Admin API response models. Tolerates unknown fields."""

    model_config = ConfigDict(extra="ignore")


# ---------------------------------------------------------------------------
# Teamspace / projects / agents / knowledge bases
# ---------------------------------------------------------------------------


class Teamspace(AdminModel):
    teamspace_id: str
    slug: Optional[str] = None
    display_name: Optional[str] = None
    subscription_plan: Optional[str] = None


class Project(AdminModel):
    project_id: str
    teamspace_id: Optional[str] = None
    slug: Optional[str] = None
    display_name: Optional[str] = None
    is_default: Optional[bool] = None


class Agent(AdminModel):
    agent_id: str
    name: Optional[str] = None
    agent_type: Optional[str] = None
    agent_status: Optional[str] = None
    teamspace_id: Optional[str] = None
    project_id: Optional[str] = None
    created_at: Optional[str] = None
    last_updated: Optional[str] = None
    is_draft: Optional[bool] = None
    last_published_at: Optional[str] = None


class KnowledgeBase(AdminModel):
    knowledge_base_id: str
    name: Optional[str] = None
    kb_status: Optional[str] = None
    vector_store_id: Optional[str] = None
    agents_using_kb: list[str] = Field(default_factory=list)
    teamspace_id: Optional[str] = None
    project_id: Optional[str] = None
    created_at: Optional[str] = None
    last_updated: Optional[str] = None


# ---------------------------------------------------------------------------
# Brand agents
# ---------------------------------------------------------------------------


class RequiredConnector(AdminModel):
    app_slug: str
    name: Optional[str] = None
    provider: Optional[str] = None
    requires_auth: Optional[bool] = None
    allowed_tools: Optional[list[str]] = None


class BrandAgentTemplate(AdminModel):
    slug: str
    name: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    difficulty_level: Optional[str] = None
    industries: Optional[list[str]] = None
    min_plan: Optional[str] = None
    has_skills: Optional[bool] = None
    has_artifacts: Optional[bool] = None
    required_connectors: Optional[list[RequiredConnector]] = None


class BrandAgentJob(AdminModel):
    """The 202 handle returned by ``brand_agents.create``."""

    agent_id: str
    job_id: str
    status: Optional[str] = None
    poll_url: Optional[str] = None
    publish_widget: Optional[bool] = None
    template_slug: Optional[str] = None
    knowledge_base_id: Optional[str] = None
    note: Optional[str] = None


class JobEmbed(AdminModel):
    widget_url: Optional[str] = None
    snippet: Optional[str] = None
    is_public: Optional[bool] = None


class JobStatus(AdminModel):
    """Progress of a brand-agent provisioning job (``GET /jobs/{job_id}``)."""

    job_id: str
    status: str
    crawl_status: Optional[str] = None
    phase: Optional[str] = None
    agent_id: Optional[str] = None
    base_url: Optional[str] = None
    progress: Optional[dict[str, Any]] = None
    connectors: Optional[list[RequiredConnector]] = None
    error_summary: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    embed: Optional[JobEmbed] = None


class BrandAgentDetail(AdminModel):
    """Settings + structure for an existing brand agent."""

    agent: Optional[dict[str, Any]] = None
    settings: Optional[dict[str, Any]] = None
    used_knowledge_bases: Optional[list[str]] = None
    structure: Optional[dict[str, int]] = None
    subscription_plan: Optional[str] = None
    available_models: Optional[list[dict[str, Any]]] = None


class BrandAgentUpdateResult(AdminModel):
    """Result of ``brand_agents.update`` — the GET shape plus patch metadata."""

    agent: Optional[dict[str, Any]] = None
    settings: Optional[dict[str, Any]] = None
    used_knowledge_bases: Optional[list[str]] = None
    structure: Optional[dict[str, int]] = None
    subscription_plan: Optional[str] = None
    available_models: Optional[list[dict[str, Any]]] = None
    updated: list[str] = Field(default_factory=list)
    file_search_node_added: Optional[bool] = None
    republished: Optional[bool] = None


class WidgetConfig(AdminModel):
    agent_id: str
    exists: Optional[bool] = None
    widget_config: dict[str, Any] = Field(default_factory=dict)
    branding_removal_entitled: Optional[bool] = None


class WidgetConfigUpdateResult(AdminModel):
    agent_id: str
    updated: list[str] = Field(default_factory=list)
    widget_config: dict[str, Any] = Field(default_factory=dict)
    branding_removal_entitled: Optional[bool] = None


# ---------------------------------------------------------------------------
# Connectors
# ---------------------------------------------------------------------------


class ConnectorTool(AdminModel):
    tool_name: str
    tool_display_name: Optional[str] = None
    tool_description: Optional[str] = None


class Connector(AdminModel):
    app_slug: str
    name: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    category: Optional[str] = None
    provider: Optional[str] = None
    auth_strategy: Optional[str] = None
    requires_auth: Optional[bool] = None
    supports_connect_link: Optional[bool] = None
    tools: list[ConnectorTool] = Field(default_factory=list)


class ConnectorTools(AdminModel):
    """Grantable tool names for one connector (``connectors.list_tools``)."""

    app_slug: str
    provider: Optional[str] = None
    restriction: Optional[str] = None
    tools: list[ConnectorTool] = Field(default_factory=list)
    total: Optional[int] = None
    limit: Optional[int] = None
    offset: Optional[int] = None
    has_more: Optional[bool] = None
    note: Optional[str] = None


class ConnectLink(AdminModel):
    app_slug: str
    provider: Optional[str] = None
    already_connected: Optional[bool] = None
    connect_url: Optional[str] = None
    expires_at: Optional[str] = None
    note: Optional[str] = None


class ConnectionStatus(AdminModel):
    app_slug: str
    provider: Optional[str] = None
    connected: bool


class ConnectorAttachment(AdminModel):
    agent_id: str
    app_slug: str
    provider: Optional[str] = None
    allowed_tools: Optional[list[str]] = None
    unrestricted: Optional[bool] = None
    note: Optional[str] = None
    attached: Optional[bool] = None
    changed: Optional[bool] = None


class ConnectorDetachment(AdminModel):
    agent_id: str
    app_slug: str
    attached: Optional[bool] = None
