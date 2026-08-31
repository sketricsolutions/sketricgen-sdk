"""
SketricGen control-plane (Admin API) surface.

Exposes the ``AdminClient`` and the typed response models for the curated
15-operation Admin API surface.
"""

from sketricgen.admin.client import (
    DEFAULT_ADMIN_BASE_URL,
    AdminClient,
)
from sketricgen.admin.models import (
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
    ConnectorTool,
    ConnectorTools,
    JobEmbed,
    JobStatus,
    KnowledgeBase,
    Project,
    RequiredConnector,
    Teamspace,
    WidgetConfig,
    WidgetConfigUpdateResult,
)

__all__ = [
    "AdminClient",
    "DEFAULT_ADMIN_BASE_URL",
    "Agent",
    "BrandAgentDetail",
    "BrandAgentJob",
    "BrandAgentTemplate",
    "BrandAgentUpdateResult",
    "ConnectLink",
    "Connector",
    "ConnectionStatus",
    "ConnectorAttachment",
    "ConnectorDetachment",
    "ConnectorTool",
    "ConnectorTools",
    "JobEmbed",
    "JobStatus",
    "KnowledgeBase",
    "Project",
    "RequiredConnector",
    "Teamspace",
    "WidgetConfig",
    "WidgetConfigUpdateResult",
]
