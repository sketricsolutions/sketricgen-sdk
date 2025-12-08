"""
SketricGen SDK Upload Utilities

Handles file uploads to S3 using presigned POST URLs.
"""

import mimetypes
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Optional, Union

import httpx

from sketricgen.config import ALLOWED_CONTENT_TYPES, MAX_FILE_SIZE_BYTES
from sketricgen.exceptions import (
    SketricGenContentTypeError,
    SketricGenFileSizeError,
    SketricGenNetworkError,
    SketricGenUploadError,
    SketricGenValidationError,
)


def detect_content_type(file_name: str) -> Optional[str]:
    """
    Detect content type from file name.

    Args:
        file_name: Name of the file with extension

    Returns:
        MIME type string or None if undetectable
    """
    content_type, _ = mimetypes.guess_type(file_name)
    return content_type


def validate_content_type(content_type: Optional[str]) -> str:
    """
    Validate that content type is allowed.

    Args:
        content_type: MIME type to validate

    Returns:
        Validated content type

    Raises:
        SketricGenContentTypeError: If content type is not allowed
    """
    if not content_type:
        raise SketricGenValidationError("Unable to determine content type from file")

    if content_type not in ALLOWED_CONTENT_TYPES:
        raise SketricGenContentTypeError(
            f"Unsupported content type: {content_type}",
            content_type=content_type,
            allowed_types=list(ALLOWED_CONTENT_TYPES),
        )

    return content_type


def get_file_info(
    file_data: Union[str, bytes, BinaryIO],
    file_name: Optional[str] = None,
    content_type: Optional[str] = None,
) -> tuple[BinaryIO, int, str, str, bool]:
    """
    Extract file information from various input types.

    Args:
        file_data: File path, bytes, or file-like object
        file_name: Optional file name override
        content_type: Optional content type override

    Returns:
        Tuple of (file_object, file_size, content_type, file_name, should_close)

    Raises:
        FileNotFoundError: If file path doesn't exist
        SketricGenValidationError: If file name cannot be determined
        SketricGenFileSizeError: If file exceeds size limit
    """
    should_close = False

    if isinstance(file_data, str):
        # File path
        file_path = Path(file_data)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_data}")

        file_obj: BinaryIO = open(file_path, "rb")  # type: ignore
        file_size = file_path.stat().st_size
        resolved_file_name = file_name or file_path.name
        resolved_content_type = content_type or detect_content_type(resolved_file_name)
        should_close = True

    elif isinstance(file_data, bytes):
        # Bytes
        file_obj = BytesIO(file_data)  # type: ignore
        file_size = len(file_data)
        if not file_name:
            raise SketricGenValidationError(
                "file_name is required when uploading from bytes"
            )
        resolved_file_name = file_name
        resolved_content_type = content_type or detect_content_type(resolved_file_name)

    else:
        # File-like object
        file_obj = file_data
        # Try to get size
        current_pos = file_obj.tell()
        file_obj.seek(0, 2)  # Seek to end
        file_size = file_obj.tell()
        file_obj.seek(current_pos)  # Seek back

        if not file_name:
            # Try to get name from file object
            resolved_file_name = getattr(file_obj, "name", None)
            if not resolved_file_name:
                raise SketricGenValidationError(
                    "file_name is required when uploading from file-like object"
                )
            resolved_file_name = Path(resolved_file_name).name
        else:
            resolved_file_name = file_name

        resolved_content_type = content_type or detect_content_type(resolved_file_name)

    # Validate file size
    if file_size > MAX_FILE_SIZE_BYTES:
        if should_close:
            file_obj.close()
        raise SketricGenFileSizeError(
            f"File size ({file_size} bytes) exceeds maximum allowed size "
            f"({MAX_FILE_SIZE_BYTES} bytes / {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB)",
            file_size=file_size,
            max_size=MAX_FILE_SIZE_BYTES,
        )

    if file_size == 0:
        if should_close:
            file_obj.close()
        raise SketricGenValidationError("Cannot upload empty file")

    # Validate content type
    validated_content_type = validate_content_type(resolved_content_type)

    return file_obj, file_size, validated_content_type, resolved_file_name, should_close


async def upload_file_to_s3(
    upload_url: str,
    upload_fields: dict[str, str],
    file_data: Union[str, bytes, BinaryIO],
    content_type: Optional[str] = None,
    timeout: float = 300.0,
) -> None:
    """
    Upload file to S3 using presigned POST URL.

    Args:
        upload_url: S3 presigned POST URL
        upload_fields: Form fields from presigned POST
        file_data: File path, bytes, or file-like object
        content_type: Optional content type override
        timeout: Upload timeout in seconds

    Raises:
        SketricGenNetworkError: For network errors
        SketricGenUploadError: For upload failures
        SketricGenFileSizeError: For file size errors
    """
    # Determine file name from fields
    key = upload_fields.get("key", "")
    file_name = key.split("/")[-1] if key else None

    file_obj, file_size, resolved_content_type, resolved_file_name, should_close = (
        get_file_info(file_data, file_name, content_type)
    )

    try:
        # Get content type from presigned fields (must match S3 policy exactly)
        policy_content_type = upload_fields.get("Content-Type", resolved_content_type)

        # Build multipart form data manually to ensure correct field order
        # S3 requires: all policy fields first, then file last
        form_files = {}
        
        # Add all presigned fields first (in order)
        for key, value in upload_fields.items():
            form_files[key] = (None, value)
        
        # Add file last (required by S3)
        form_files["file"] = (resolved_file_name, file_obj, policy_content_type)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                upload_url,
                files=form_files,
                timeout=timeout,
            )

            if response.status_code >= 400:
                raise SketricGenUploadError(
                    f"S3 upload failed with status {response.status_code}: {response.text}"
                )

    except httpx.TimeoutException as e:
        raise SketricGenNetworkError(f"Upload timed out: {e}") from e
    except httpx.HTTPError as e:
        raise SketricGenNetworkError(f"Failed to upload file to S3: {e}") from e
    finally:
        if should_close:
            file_obj.close()


def upload_file_to_s3_sync(
    upload_url: str,
    upload_fields: dict[str, str],
    file_data: Union[str, bytes, BinaryIO],
    content_type: Optional[str] = None,
    timeout: float = 300.0,
) -> None:
    """
    Synchronous version of upload_file_to_s3.

    Args:
        upload_url: S3 presigned POST URL
        upload_fields: Form fields from presigned POST
        file_data: File path, bytes, or file-like object
        content_type: Optional content type override
        timeout: Upload timeout in seconds

    Raises:
        SketricGenNetworkError: For network errors
        SketricGenUploadError: For upload failures
    """
    # Determine file name from fields
    key = upload_fields.get("key", "")
    file_name = key.split("/")[-1] if key else None

    file_obj, file_size, resolved_content_type, resolved_file_name, should_close = (
        get_file_info(file_data, file_name, content_type)
    )

    try:
        # Get content type from presigned fields (must match S3 policy exactly)
        policy_content_type = upload_fields.get("Content-Type", resolved_content_type)

        # Build multipart form data manually to ensure correct field order
        # S3 requires: all policy fields first, then file last
        form_files = {}
        
        # Add all presigned fields first (in order)
        for key, value in upload_fields.items():
            form_files[key] = (None, value)
        
        # Add file last (required by S3)
        form_files["file"] = (resolved_file_name, file_obj, policy_content_type)

        with httpx.Client() as client:
            response = client.post(
                upload_url,
                files=form_files,
                timeout=timeout,
            )

            if response.status_code >= 400:
                raise SketricGenUploadError(
                    f"S3 upload failed with status {response.status_code}: {response.text}"
                )

    except httpx.TimeoutException as e:
        raise SketricGenNetworkError(f"Upload timed out: {e}") from e
    except httpx.HTTPError as e:
        raise SketricGenNetworkError(f"Failed to upload file to S3: {e}") from e
    finally:
        if should_close:
            file_obj.close()
