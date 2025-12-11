"""
SketricGen SDK Client

Main client class for interacting with the SketricGen Chat Server API.
"""

import asyncio
from typing import AsyncIterator, BinaryIO, Iterator, Optional, Union

import httpx

from sketricgen.config import SketricGenConfig
from sketricgen.exceptions import (
    SketricGenAPIError,
    SketricGenAuthenticationError,
    SketricGenNetworkError,
    SketricGenTimeoutError,
    SketricGenValidationError,
)
from sketricgen.models.requests import (
    CompleteUploadRequest,
    InitiateUploadRequest,
    RunWorkflowRequest,
)
from sketricgen.models.responses import (
    ChatResponse,
    CompleteUploadResponse,
    InitiateUploadResponse,
    StreamEvent,
)
from sketricgen.streaming import parse_sse_stream, parse_sse_stream_sync
from sketricgen.upload import (
    detect_content_type,
    get_file_info,
    upload_file_to_s3,
    upload_file_to_s3_sync,
)


class SketricGenClient:
    """
    Main client for interacting with SketricGen Chat Server API.

    Example:
        ```python
        client = SketricGenClient(api_key="your-api-key")

        # Run workflow
        response = await client.run_workflow(
            agent_id="agent-123",
            user_input="Hello, how are you?",
            conversation_id="conv-456"
        )

        # Run workflow with file attachments
        response = await client.run_workflow(
            agent_id="agent-123",
            user_input="Analyze this document",
            file_paths=["/path/to/document.pdf"]
        )
        ```
    """

    def __init__(
        self,
        api_key: str,
        timeout: int = 30,
        upload_timeout: int = 300,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize the SketricGen client.

        Args:
            api_key: Your SketricGen API key
            timeout: Request timeout in seconds
            upload_timeout: Upload timeout in seconds (for large files)
            max_retries: Maximum number of retry attempts
        """
        self._config = SketricGenConfig(
            api_key=api_key,
            timeout=timeout,
            upload_timeout=upload_timeout,
            max_retries=max_retries,
        )

    @classmethod
    def from_env(cls, **kwargs) -> "SketricGenClient":
        """
        Create a client from environment variables.

        Environment Variables:
            SKETRICGEN_API_KEY: API key (required)
            SKETRICGEN_TIMEOUT: Request timeout (optional)
            SKETRICGEN_MAX_RETRIES: Max retries (optional)

        Args:
            **kwargs: Override any config values

        Returns:
            SketricGenClient instance
        """
        config = SketricGenConfig.from_env()
        return cls(
            api_key=config.api_key,
            timeout=kwargs.get("timeout", config.timeout),
            max_retries=kwargs.get("max_retries", config.max_retries),
        )

    def _get_headers(self) -> dict[str, str]:
        """Get default request headers."""
        return {
            "API-KEY": self._config.api_key,
            "Content-Type": "application/json",
        }

    def _get_upload_headers(self) -> dict[str, str]:
        """Get headers for upload endpoints (uses X-API-KEY)."""
        return {
            "X-API-KEY": self._config.api_key,
            "Content-Type": "application/json",
        }

    def _handle_error_response(self, response: httpx.Response) -> None:
        """
        Handle error responses from the API.

        Args:
            response: httpx response object

        Raises:
            SketricGenAuthenticationError: For 401 errors
            SketricGenAPIError: For other error responses
        """
        try:
            body = response.json()
            message = body.get("message", body.get("detail", "Unknown error"))
        except Exception:
            body = None
            message = response.text or "Unknown error"

        if response.status_code == 401:
            raise SketricGenAuthenticationError(message)

        raise SketricGenAPIError(
            message=message,
            status_code=response.status_code,
            response_body=body,
        )

    # =========================================================================
    # Run Workflow Methods
    # =========================================================================

    async def run_workflow(
        self,
        agent_id: str,
        user_input: str,
        conversation_id: Optional[str] = None,
        contact_id: Optional[str] = None,
        file_paths: Optional[list[str]] = None,
        stream: bool = False,
    ) -> Union[ChatResponse, AsyncIterator[StreamEvent]]:
        """
        Execute a workflow/chat request.

        Args:
            agent_id: Agent ID to chat with
            user_input: User message (max 10000 characters)
            conversation_id: Optional conversation ID for resuming
            contact_id: Optional external contact ID
            file_paths: Optional list of file paths to upload and attach
            stream: Whether to stream the response

        Returns:
            ChatResponse if stream=False, AsyncIterator[StreamEvent] if stream=True

        Raises:
            SketricGenAPIError: For API errors
            SketricGenValidationError: For validation errors
            SketricGenNetworkError: For network errors
            SketricGenFileSizeError: If a file exceeds size limit
            SketricGenContentTypeError: If a file type is not supported

        Example:
            ```python
            # Non-streaming
            response = await client.run_workflow(
                agent_id="agent-123",
                user_input="Hello!"
            )
            print(response.response)

            # With file attachments
            response = await client.run_workflow(
                agent_id="agent-123",
                user_input="Analyze this document",
                file_paths=["/path/to/document.pdf"]
            )

            # Streaming
            async for event in await client.run_workflow(
                agent_id="agent-123",
                user_input="Tell me a story",
                stream=True
            ):
                print(event.data, end="", flush=True)
            ```
        """
        # Upload files if provided
        asset_ids: list[str] = []
        if file_paths:
            for file_path in file_paths:
                upload_response = await self._upload_asset(
                    agent_id=agent_id,
                    file_path=file_path,
                )
                asset_ids.append(upload_response.file_id)

        try:
            request = RunWorkflowRequest(
                agent_id=agent_id,
                user_input=user_input,
                conversation_id=conversation_id,
                contact_id=contact_id,
                assets=asset_ids,
                stream=stream,
            )
        except ValueError as e:
            raise SketricGenValidationError(str(e)) from e

        if stream:
            return self._run_workflow_stream(request)
        else:
            return await self._run_workflow_non_stream(request)

    async def _run_workflow_non_stream(
        self, request: RunWorkflowRequest
    ) -> ChatResponse:
        """Execute non-streaming workflow request."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._config.get_workflow_url(),
                    json=request.model_dump(exclude_none=True),
                    headers=self._get_headers(),
                    timeout=self._config.timeout,
                )

                if response.status_code >= 400:
                    self._handle_error_response(response)

                return ChatResponse.model_validate(response.json())

        except httpx.TimeoutException as e:
            raise SketricGenTimeoutError(f"Request timed out: {e}") from e
        except httpx.HTTPError as e:
            raise SketricGenNetworkError(f"Network error: {e}") from e

    async def _run_workflow_stream(
        self, request: RunWorkflowRequest
    ) -> AsyncIterator[StreamEvent]:
        """Execute streaming workflow request."""
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    self._config.get_workflow_url(),
                    json=request.model_dump(exclude_none=True),
                    headers=self._get_headers(),
                    timeout=None,  # No timeout for streaming
                ) as response:
                    if response.status_code >= 400:
                        await response.aread()
                        self._handle_error_response(response)

                    async for event in parse_sse_stream(response):
                        yield event

        except httpx.TimeoutException as e:
            raise SketricGenTimeoutError(f"Request timed out: {e}") from e
        except httpx.HTTPError as e:
            raise SketricGenNetworkError(f"Network error: {e}") from e

    def run_workflow_sync(
        self,
        agent_id: str,
        user_input: str,
        conversation_id: Optional[str] = None,
        contact_id: Optional[str] = None,
        file_paths: Optional[list[str]] = None,
        stream: bool = False,
    ) -> Union[ChatResponse, Iterator[StreamEvent]]:
        """
        Synchronous version of run_workflow.

        Args:
            agent_id: Agent ID to chat with
            user_input: User message (max 10000 characters)
            conversation_id: Optional conversation ID for resuming
            contact_id: Optional external contact ID
            file_paths: Optional list of file paths to upload and attach
            stream: Whether to stream the response

        Returns:
            ChatResponse if stream=False, Iterator[StreamEvent] if stream=True

        Raises:
            SketricGenAPIError: For API errors
            SketricGenValidationError: For validation errors
            SketricGenNetworkError: For network errors
            SketricGenFileSizeError: If a file exceeds size limit
            SketricGenContentTypeError: If a file type is not supported
        """
        # Upload files if provided
        asset_ids: list[str] = []
        if file_paths:
            for file_path in file_paths:
                upload_response = self._upload_asset_sync(
                    agent_id=agent_id,
                    file_path=file_path,
                )
                asset_ids.append(upload_response.file_id)

        try:
            request = RunWorkflowRequest(
                agent_id=agent_id,
                user_input=user_input,
                conversation_id=conversation_id,
                contact_id=contact_id,
                assets=asset_ids,
                stream=stream,
            )
        except ValueError as e:
            raise SketricGenValidationError(str(e)) from e

        if stream:
            return self._run_workflow_stream_sync(request)
        else:
            return self._run_workflow_non_stream_sync(request)

    def _run_workflow_non_stream_sync(self, request: RunWorkflowRequest) -> ChatResponse:
        """Execute non-streaming workflow request synchronously."""
        try:
            with httpx.Client() as client:
                response = client.post(
                    self._config.get_workflow_url(),
                    json=request.model_dump(exclude_none=True),
                    headers=self._get_headers(),
                    timeout=self._config.timeout,
                )

                if response.status_code >= 400:
                    self._handle_error_response(response)

                return ChatResponse.model_validate(response.json())

        except httpx.TimeoutException as e:
            raise SketricGenTimeoutError(f"Request timed out: {e}") from e
        except httpx.HTTPError as e:
            raise SketricGenNetworkError(f"Network error: {e}") from e

    def _run_workflow_stream_sync(
        self, request: RunWorkflowRequest
    ) -> Iterator[StreamEvent]:
        """Execute streaming workflow request synchronously."""
        try:
            with httpx.Client() as client:
                with client.stream(
                    "POST",
                    self._config.get_workflow_url(),
                    json=request.model_dump(exclude_none=True),
                    headers=self._get_headers(),
                    timeout=None,
                ) as response:
                    if response.status_code >= 400:
                        response.read()
                        self._handle_error_response(response)

                    yield from parse_sse_stream_sync(response)

        except httpx.TimeoutException as e:
            raise SketricGenTimeoutError(f"Request timed out: {e}") from e
        except httpx.HTTPError as e:
            raise SketricGenNetworkError(f"Network error: {e}") from e

    # =========================================================================
    # Asset Upload Methods
    # =========================================================================

    async def _initiate_upload(
        self,
        agent_id: str,
        file_name: str,
    ) -> InitiateUploadResponse:
        """
        Internal Step 1: Initialize an asset upload session.

        Args:
            agent_id: Agent ID associated with the upload
            file_name: File name with extension (e.g., "document.pdf")

        Returns:
            InitiateUploadResponse with file_id and presigned POST URL
        """
        try:
            request = InitiateUploadRequest(
                agent_id=agent_id,
                file_name=file_name,
            )
        except ValueError as e:
            raise SketricGenValidationError(str(e)) from e

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._config.get_upload_init_url(),
                    json=request.model_dump(exclude_none=True),
                    headers=self._get_upload_headers(),
                    timeout=self._config.timeout,
                )

                if response.status_code >= 400:
                    self._handle_error_response(response)

                return InitiateUploadResponse.model_validate(response.json())

        except httpx.TimeoutException as e:
            raise SketricGenTimeoutError(f"Request timed out: {e}") from e
        except httpx.HTTPError as e:
            raise SketricGenNetworkError(f"Network error: {e}") from e

    async def _upload_to_s3(
        self,
        upload_url: str,
        upload_fields: dict[str, str],
        file_path: Union[str, bytes, BinaryIO],
        content_type: Optional[str] = None,
    ) -> None:
        """
        Internal Step 2: Upload file to S3 using presigned POST URL.

        Args:
            upload_url: S3 presigned POST URL from initiate_upload
            upload_fields: Form fields from initiate_upload response
            file_path: Path to file, bytes, or file-like object
            content_type: Optional content type override
        """
        await upload_file_to_s3(
            upload_url=upload_url,
            upload_fields=upload_fields,
            file_data=file_path,
            content_type=content_type,
            timeout=float(self._config.upload_timeout),
        )

    async def _complete_upload(
        self,
        agent_id: str,
        file_id: str,
        file_name: Optional[str] = None,
    ) -> CompleteUploadResponse:
        """
        Internal Step 3: Complete the upload process and register the file.

        Args:
            agent_id: Agent ID (must match initiate_upload)
            file_id: File ID from initiate_upload response
            file_name: Optional file name override

        Returns:
            CompleteUploadResponse with file details and access URL
        """
        try:
            request = CompleteUploadRequest(
                agent_id=agent_id,
                file_id=file_id,
                file_name=file_name,
            )
        except ValueError as e:
            raise SketricGenValidationError(str(e)) from e

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._config.get_upload_complete_url(),
                    json=request.model_dump(exclude_none=True),
                    headers=self._get_upload_headers(),
                    timeout=self._config.timeout,
                )

                if response.status_code >= 400:
                    self._handle_error_response(response)

                return CompleteUploadResponse.model_validate(response.json())

        except httpx.TimeoutException as e:
            raise SketricGenTimeoutError(f"Request timed out: {e}") from e
        except httpx.HTTPError as e:
            raise SketricGenNetworkError(f"Network error: {e}") from e

    async def _upload_asset(
        self,
        agent_id: str,
        file_path: Union[str, bytes, BinaryIO],
        file_name: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> CompleteUploadResponse:
        """
        Internal: Upload an asset file to use in workflows.

        This method handles the complete upload process internally.
        Users should use file_paths parameter in run_workflow instead.

        Args:
            agent_id: Agent ID associated with the upload
            file_path: Path to file, bytes, or file-like object
            file_name: Optional file name (auto-detected from path if not provided)
            content_type: Optional content type (auto-detected if not provided)

        Returns:
            CompleteUploadResponse with file details and access URL

        Raises:
            SketricGenAPIError: For API errors
            SketricGenValidationError: For validation errors
            SketricGenNetworkError: For network/upload errors
        """
        # Determine file name if not provided
        if isinstance(file_path, str):
            from pathlib import Path
            resolved_file_name = file_name or Path(file_path).name
        elif file_name:
            resolved_file_name = file_name
        else:
            raise SketricGenValidationError(
                "file_name is required when uploading from bytes or file-like object"
            )

        # Step 1: Initiate upload
        init_response = await self._initiate_upload(
            agent_id=agent_id,
            file_name=resolved_file_name,
        )

        # Step 2: Upload to S3
        await self._upload_to_s3(
            upload_url=init_response.upload.url,
            upload_fields=init_response.upload.fields,
            file_path=file_path,
            content_type=content_type or init_response.content_type,
        )

        # Step 3: Complete upload
        return await self._complete_upload(
            agent_id=agent_id,
            file_id=init_response.file_id,
            file_name=resolved_file_name,
        )

    # =========================================================================
    # Synchronous Upload Methods (Internal)
    # =========================================================================

    def _initiate_upload_sync(
        self,
        agent_id: str,
        file_name: str,
    ) -> InitiateUploadResponse:
        """Internal synchronous version of initiate_upload."""
        try:
            request = InitiateUploadRequest(
                agent_id=agent_id,
                file_name=file_name,
            )
        except ValueError as e:
            raise SketricGenValidationError(str(e)) from e

        try:
            with httpx.Client() as client:
                response = client.post(
                    self._config.get_upload_init_url(),
                    json=request.model_dump(exclude_none=True),
                    headers=self._get_upload_headers(),
                    timeout=self._config.timeout,
                )

                if response.status_code >= 400:
                    self._handle_error_response(response)

                return InitiateUploadResponse.model_validate(response.json())

        except httpx.TimeoutException as e:
            raise SketricGenTimeoutError(f"Request timed out: {e}") from e
        except httpx.HTTPError as e:
            raise SketricGenNetworkError(f"Network error: {e}") from e

    def _upload_to_s3_sync(
        self,
        upload_url: str,
        upload_fields: dict[str, str],
        file_path: Union[str, bytes, BinaryIO],
        content_type: Optional[str] = None,
    ) -> None:
        """Internal synchronous version of upload_to_s3."""
        upload_file_to_s3_sync(
            upload_url=upload_url,
            upload_fields=upload_fields,
            file_data=file_path,
            content_type=content_type,
            timeout=float(self._config.upload_timeout),
        )

    def _complete_upload_sync(
        self,
        agent_id: str,
        file_id: str,
        file_name: Optional[str] = None,
    ) -> CompleteUploadResponse:
        """Internal synchronous version of complete_upload."""
        try:
            request = CompleteUploadRequest(
                agent_id=agent_id,
                file_id=file_id,
                file_name=file_name,
            )
        except ValueError as e:
            raise SketricGenValidationError(str(e)) from e

        try:
            with httpx.Client() as client:
                response = client.post(
                    self._config.get_upload_complete_url(),
                    json=request.model_dump(exclude_none=True),
                    headers=self._get_upload_headers(),
                    timeout=self._config.timeout,
                )

                if response.status_code >= 400:
                    self._handle_error_response(response)

                return CompleteUploadResponse.model_validate(response.json())

        except httpx.TimeoutException as e:
            raise SketricGenTimeoutError(f"Request timed out: {e}") from e
        except httpx.HTTPError as e:
            raise SketricGenNetworkError(f"Network error: {e}") from e

    def _upload_asset_sync(
        self,
        agent_id: str,
        file_path: Union[str, bytes, BinaryIO],
        file_name: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> CompleteUploadResponse:
        """Internal synchronous version of upload_asset."""
        # Determine file name if not provided
        if isinstance(file_path, str):
            from pathlib import Path
            resolved_file_name = file_name or Path(file_path).name
        elif file_name:
            resolved_file_name = file_name
        else:
            raise SketricGenValidationError(
                "file_name is required when uploading from bytes or file-like object"
            )

        # Step 1: Initiate upload
        init_response = self._initiate_upload_sync(
            agent_id=agent_id,
            file_name=resolved_file_name,
        )

        # Step 2: Upload to S3
        self._upload_to_s3_sync(
            upload_url=init_response.upload.url,
            upload_fields=init_response.upload.fields,
            file_path=file_path,
            content_type=content_type or init_response.content_type,
        )

        # Step 3: Complete upload
        return self._complete_upload_sync(
            agent_id=agent_id,
            file_id=init_response.file_id,
            file_name=resolved_file_name,
        )
