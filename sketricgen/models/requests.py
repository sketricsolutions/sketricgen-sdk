"""
Sketric SDK Request Models

Pydantic models for API request validation.
"""

import os
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class HitlDecision(BaseModel):
    """A decision for one pending HITL action."""

    model_config = ConfigDict(extra="allow")

    type: Literal["respond", "approve", "reject"]
    message: Optional[str] = None


class HitlResume(BaseModel):
    """Resume a paused HITL request on the same conversation."""

    request_id: str = Field(..., min_length=1)
    decisions: list[HitlDecision] = Field(..., min_length=1)


class RunWorkflowRequest(BaseModel):
    """Request model for run-workflow endpoint."""

    agent_id: str = Field(..., description="Agent ID to chat with")
    user_input: str = Field("", max_length=10000, description="User message")
    assets: list[str] = Field(
        default_factory=list, description="List of asset file IDs"
    )
    conversation_id: Optional[str] = Field(
        None, description="Conversation ID for resuming"
    )
    contact_id: Optional[str] = Field(None, description="External contact ID")
    stream: bool = Field(False, description="Whether to stream the response")
    enable_hitl: bool = Field(False, description="Enable HITL for this run")
    hitl_resume: Optional[HitlResume] = Field(None, description="Pending HITL response")

    @field_validator("user_input")
    @classmethod
    def validate_user_input(cls, v: str) -> str:
        """Validate user input length."""
        if len(v) > 10000:
            raise ValueError("user_input cannot exceed 10000 characters")
        return v

    @model_validator(mode="after")
    def validate_run_input(self) -> "RunWorkflowRequest":
        if self.hitl_resume is not None:
            if not self.conversation_id:
                raise ValueError("conversation_id is required when hitl_resume is set")
            if not self.enable_hitl:
                raise ValueError("enable_hitl must be true when hitl_resume is set")
            return self
        if not self.user_input.strip() and not self.assets:
            raise ValueError(
                "user_input is required unless hitl_resume or assets is set"
            )
        return self

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id(cls, v: str) -> str:
        """Validate agent ID is not empty."""
        if not v.strip():
            raise ValueError("agent_id cannot be empty")
        return v.strip()


class InitiateUploadRequest(BaseModel):
    """Request model for initiate upload endpoint."""

    agent_id: str = Field(..., description="Agent ID associated with the upload")
    file_name: str = Field(..., description="File name with extension")

    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, v: str) -> str:
        """Validate file name has extension and sanitize path."""
        if not v or "." not in v:
            raise ValueError("file_name must include an extension (e.g. .png, .pdf)")
        # Sanitize path - only keep basename
        return os.path.basename(v)

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id(cls, v: str) -> str:
        """Validate agent ID is not empty."""
        if not v.strip():
            raise ValueError("agent_id cannot be empty")
        return v.strip()


class CompleteUploadRequest(BaseModel):
    """Request model for complete upload endpoint."""

    agent_id: str = Field(..., description="Agent ID (must match initiate_upload)")
    file_id: str = Field(..., description="File ID from initiate_upload")
    file_name: Optional[str] = Field(None, description="Optional file name override")

    @field_validator("agent_id", "file_id")
    @classmethod
    def validate_required_fields(cls, v: str) -> str:
        """Validate required fields are not empty."""
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()
