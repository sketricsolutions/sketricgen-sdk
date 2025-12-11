"""
Error handling examples for the SketricGen SDK.
"""

import asyncio
from sketricgen import (
    SketricGenClient,
    SketricGenAPIError,
    SketricGenAuthenticationError,
    SketricGenValidationError,
    SketricGenNetworkError,
    SketricGenTimeoutError,
    SketricGenFileSizeError,
    SketricGenContentTypeError,
    SketricGenUploadError,
)


async def workflow_error_handling():
    """Example: Handle errors when running workflows."""
    client = SketricGenClient(api_key="your-api-key")

    try:
        response = await client.run_workflow(
            agent_id="agent-123",
            user_input="Hello",
        )
        print(f"Response: {response.response}")

    except SketricGenAuthenticationError as e:
        # 401 - Invalid API key
        print(f"Authentication failed: {e}")
        print("Please check your API key.")

    except SketricGenValidationError as e:
        # Client-side validation failed
        print(f"Validation error: {e}")
        print("Please check your input parameters.")

    except SketricGenTimeoutError as e:
        # Request timed out
        print(f"Request timed out: {e}")
        print("Try again or increase timeout.")

    except SketricGenNetworkError as e:
        # Network/connection error
        print(f"Network error: {e}")
        print("Check your internet connection.")

    except SketricGenAPIError as e:
        # Other API errors (4xx, 5xx)
        print(f"API error ({e.status_code}): {e}")
        if e.response_body:
            print(f"Details: {e.response_body}")


async def file_upload_error_handling():
    """Example: Handle errors when running workflows with file attachments."""
    client = SketricGenClient(api_key="your-api-key")

    try:
        response = await client.run_workflow(
            agent_id="agent-123",
            user_input="Analyze this document",
            file_paths=["/path/to/file.pdf"],
        )
        print(f"Response: {response.response}")

    except SketricGenFileSizeError as e:
        # File exceeds 20 MB limit
        print(f"File too large: {e}")
        print(f"File size: {e.file_size} bytes")
        print(f"Max size: {e.max_size} bytes")

    except SketricGenContentTypeError as e:
        # Unsupported file type
        print(f"Unsupported file type: {e}")
        print(f"Your content type: {e.content_type}")
        print(f"Allowed types: {e.allowed_types}")

    except SketricGenUploadError as e:
        # S3 upload failed
        print(f"Upload failed: {e}")

    except SketricGenValidationError as e:
        # Empty file, etc.
        print(f"Validation error: {e}")

    except SketricGenAPIError as e:
        # API errors (agent not found, etc.)
        print(f"API error ({e.status_code}): {e}")

    except FileNotFoundError as e:
        # File doesn't exist
        print(f"File not found: {e}")


async def retry_on_error():
    """Example: Simple retry logic for transient errors."""
    client = SketricGenClient(api_key="your-api-key")

    max_retries = 3
    retry_delay = 1  # seconds

    for attempt in range(max_retries):
        try:
            response = await client.run_workflow(
                agent_id="agent-123",
                user_input="Hello",
            )
            print(f"Success: {response.response}")
            break

        except (SketricGenNetworkError, SketricGenTimeoutError) as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print("Max retries reached. Giving up.")
                raise

        except SketricGenAPIError as e:
            # Don't retry client errors (4xx)
            if 400 <= e.status_code < 500:
                print(f"Client error (no retry): {e}")
                raise
            # Retry server errors (5xx)
            print(f"Server error, attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
            else:
                raise


if __name__ == "__main__":
    asyncio.run(workflow_error_handling())
