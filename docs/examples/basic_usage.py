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
    import json
    
    client = SketricGenClient(api_key="your-api-key")

    print("Streaming response:")
    async for event in await client.run_workflow(
        agent_id="agent-123",
        user_input="Tell me a short story",
        stream=True,
    ):
        data = json.loads(event.data)
        
        if data["type"] == "TEXT_MESSAGE_CONTENT":
            # Print text chunks as they arrive
            print(data["delta"], end="", flush=True)
        elif data["type"] == "RUN_FINISHED":
            print()  # New line at end


async def run_workflow_with_files_example():
    """Example: Run a workflow with file attachments."""
    client = SketricGenClient(api_key="your-api-key")

    # Run workflow with file attachments
    # Files are automatically uploaded in the background
    response = await client.run_workflow(
        agent_id="agent-123",
        user_input="Please analyze this document",
        file_paths=["/path/to/document.pdf"],
    )

    print(f"Analysis: {response.response}")


async def run_workflow_with_multiple_files_example():
    """Example: Run a workflow with multiple file attachments."""
    client = SketricGenClient(api_key="your-api-key")

    # Multiple files can be attached at once
    response = await client.run_workflow(
        agent_id="agent-123",
        user_input="Compare these two documents",
        file_paths=[
            "/path/to/document1.pdf",
            "/path/to/document2.pdf",
        ],
    )

    print(f"Comparison: {response.response}")


def sync_workflow_example():
    """Example: Run a workflow synchronously."""
    client = SketricGenClient(api_key="your-api-key")

    response = client.run_workflow_sync(
        agent_id="agent-123",
        user_input="Hello!",
    )

    print(f"Response: {response.response}")


def sync_workflow_with_files_example():
    """Example: Run a synchronous workflow with file attachments."""
    client = SketricGenClient(api_key="your-api-key")

    response = client.run_workflow_sync(
        agent_id="agent-123",
        user_input="Summarize this document",
        file_paths=["/path/to/document.pdf"],
    )

    print(f"Summary: {response.response}")


if __name__ == "__main__":
    # Run async examples
    asyncio.run(run_workflow_example())
