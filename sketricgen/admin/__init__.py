"""
Typed models for the SketricGen control-plane surface.
"""

from sketricgen.admin.client import (
    DEFAULT_ADMIN_BASE_URL,
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
