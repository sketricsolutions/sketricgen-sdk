"""
Sketric SDK Request Models

Pydantic models for API request validation.
"""

import os
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class RunWorkflowRequest(BaseModel):
    """Request model for run-workflow endpoint."""

    agent_id: str = Field(..., description="Agent ID to chat with")
    user_input: str = Field(..., max_length=10000, description="User message")
    assets: list[str] = Field(
        default_factory=list, description="List of asset file IDs"
    )
    conversation_id: Optional[str] = Field(
        None, description="Conversation ID for resuming"
    )
    contact_id: Optional[str] = Field(None, description="External contact ID")
    stream: bool = Field(False, description="Whether to stream the response")

    @field_validator("user_input")
    @classmethod
    def validate_user_input(cls, v: str) -> str:
        """Validate user input length."""
        if len(v) > 10000:
            raise ValueError("user_input cannot exceed 10000 characters")
        if not v.strip():
            raise ValueError("user_input cannot be empty")
        return v

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
