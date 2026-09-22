"""
Sketric SDK Response Models

Pydantic models for API response parsing.
"""

import json
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class Asset(BaseModel):
    """Generated asset returned by a workflow."""

    file_id: str
    url: Optional[str] = None
    content_type: Optional[str] = None


class HitlActionRequest(BaseModel):
    """Tool action awaiting a human decision."""

    model_config = ConfigDict(extra="allow")

    name: str
    args: dict[str, Any] = Field(default_factory=dict)


class HitlReviewConfig(BaseModel):
    """Allowed decisions for one HITL action."""

    model_config = ConfigDict(extra="allow")

    allowed_decisions: list[Literal["respond", "approve", "reject"]]


class HitlRequest(BaseModel):
    """Durable metadata for a paused HITL run."""

    model_config = ConfigDict(extra="allow")

    schema_version: int = 1
    request_id: str
    thread_id: str
    run_id: str
    interrupt_ids: list[str] = Field(default_factory=list)
    original_run_id: Optional[str] = None
    action_requests: list[HitlActionRequest]
    review_configs: list[HitlReviewConfig]
    paused_at: Optional[str] = None
    status: Literal["pending", "resuming", "resolved", "superseded"] = "pending"


class ChatResponse(BaseModel):
    """Response model for chat/workflow session."""

    agent_id: str = Field(..., description="Workflow ID")
    user_id: str = Field(..., description="User identifier")
    conversation_id: str = Field(..., description="Conversation ID")
    response: str = Field(..., description="Assistant's response")
    owner: str = Field(..., description="Owner of the agent")
    error: bool = Field(default=False, description="Error flag")
    assets: list[Asset] = Field(default_factory=list)
    run_paused_hitl: bool = False
    hitl_interrupts: Optional[list[dict[str, Any]]] = None
    hitl_request: Optional[HitlRequest] = None
    run_halted_out_of_credits: bool = False
    web_search_citations: Optional[list[dict[str, str]]] = None


class StreamEvent(BaseModel):
    """Model for streaming events."""

    event_type: str = Field(..., description="Type of the event")
    data: str = Field(..., description="Event data/content")
    id: Optional[str] = Field(None, description="Event ID")

    @property
    def is_terminal(self) -> bool:
        """Whether this event ends the current workflow stream."""
        terminal_types = {"RUN_FINISHED", "RUN_ERROR", "RUN_PAUSED_HITL"}
        if self.event_type in terminal_types:
            return True
        try:
            return json.loads(self.data).get("type") in terminal_types
        except (json.JSONDecodeError, AttributeError):
            return False


class PresignedUpload(BaseModel):
    """Presigned upload information from S3."""

    url: str = Field(..., description="S3 presigned POST URL")
    fields: dict[str, str] = Field(..., description="Form fields for S3 upload")
    expires_at: str = Field(..., description="ISO timestamp when URL expires")
    max_file_bytes: int = Field(..., description="Maximum file size in bytes")


class InitiateUploadResponse(BaseModel):
    """Response model for initiate upload endpoint."""

    success: bool = Field(..., description="Whether the request succeeded")
    file_id: str = Field(..., description="Unique file identifier")
    content_type: str = Field(..., description="Detected MIME type")
    upload: PresignedUpload = Field(..., description="Presigned upload details")


class CompleteUploadResponse(BaseModel):
    """Response model for complete upload endpoint."""

    success: bool = Field(..., description="Whether the upload completed")
    file_id: str = Field(..., description="File identifier")
    file_size_bytes: int = Field(..., description="Size of uploaded file")
    content_type: str = Field(..., description="MIME type of the file")
    file_name: str = Field(..., description="Final file name")
    created_at: str = Field(..., description="ISO timestamp of creation")
    url: str = Field(..., description="Presigned GET URL (valid for 3 days)")


class APIErrorResponse(BaseModel):
    """Model for API error responses."""

    success: bool = Field(False, description="Always false for errors")
    message: str = Field(..., description="Error message")
    allowed_types: Optional[list[str]] = Field(
        None, description="Allowed content types (if applicable)"
    )
