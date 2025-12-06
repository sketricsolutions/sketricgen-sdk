"""
Basic usage examples for the SketricGen SDK.
"""

import asyncio
from sketricgen import SketricGenClient


async def run_workflow_example():
    """Example: Run a simple workflow."""
    client = SketricGenClient(api_key="your-api-key")

    response = await client.run_workflow(
        agent_id="agent-123",
        user_input="Hello, how are you?",
    )

    print(f"Agent ID: {response.agent_id}")
    print(f"Conversation ID: {response.conversation_id}")
    print(f"Response: {response.response}")


async def run_workflow_streaming_example():
    """Example: Run a workflow with streaming."""
    client = SketricGenClient(api_key="your-api-key")

    print("Streaming response:")
    async for event in await client.run_workflow(
        agent_id="agent-123",
        user_input="Tell me a short story",
        stream=True,
    ):
        print(event.data, end="", flush=True)
    print()  # New line at end


async def upload_asset_example():
    """Example: Upload an asset and use it in a workflow."""
    client = SketricGenClient(api_key="your-api-key")

    # Upload a file - SDK handles all steps internally
    upload_response = await client.upload_asset(
        agent_id="agent-123",
        file_path="/path/to/document.pdf",
    )

    print(f"Uploaded file ID: {upload_response.file_id}")
    print(f"File size: {upload_response.file_size_bytes} bytes")
    print(f"Access URL: {upload_response.url}")

    # Use the uploaded file in a workflow
    response = await client.run_workflow(
        agent_id="agent-123",
        user_input="Please analyze this document",
        assets=[upload_response.file_id],
    )

    print(f"Analysis: {response.response}")


async def upload_from_bytes_example():
    """Example: Upload from bytes."""
    client = SketricGenClient(api_key="your-api-key")

    # Read file as bytes
    with open("/path/to/image.png", "rb") as f:
        image_bytes = f.read()

    # Upload from bytes (file_name is required)
    response = await client.upload_asset(
        agent_id="agent-123",
        file_path=image_bytes,
        file_name="image.png",
    )

    print(f"Uploaded: {response.file_id}")


def sync_workflow_example():
    """Example: Run a workflow synchronously."""
    client = SketricGenClient(api_key="your-api-key")

    response = client.run_workflow_sync(
        agent_id="agent-123",
        user_input="Hello!",
    )

    print(f"Response: {response.response}")


def sync_upload_example():
    """Example: Upload an asset synchronously."""
    client = SketricGenClient(api_key="your-api-key")

    response = client.upload_asset_sync(
        agent_id="agent-123",
        file_path="/path/to/image.png",
    )

    print(f"Uploaded: {response.file_id}")


if __name__ == "__main__":
    # Run async examples
    asyncio.run(run_workflow_example())
