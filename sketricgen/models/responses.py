"""
Sketric SDK Response Models

Pydantic models for API response parsing.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class ChatResponse(BaseModel):
    """Response model for chat/workflow session."""

    agent_id: str = Field(..., description="Workflow ID")
    user_id: str = Field(..., description="User identifier")
    conversation_id: str = Field(..., description="Conversation ID")
    response: str = Field(..., description="Assistant's response")
    owner: str = Field(..., description="Owner of the agent")
    error: bool = Field(default=False, description="Error flag")


class StreamEvent(BaseModel):
    """Model for streaming events."""

    event_type: str = Field(..., description="Type of the event")
    data: str = Field(..., description="Event data/content")
    id: Optional[str] = Field(None, description="Event ID")


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
