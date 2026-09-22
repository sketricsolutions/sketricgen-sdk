"""
Basic usage examples for the SketricGen SDK.
"""

import asyncio
import json

from sketricgen import HitlDecision, HitlResume, SketricGenClient


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


async def hitl_example():
    """Example: Enable and resume human-in-the-loop execution."""
    client = SketricGenClient(api_key="sk_api_...")
    paused = await client.run_workflow(
        agent_id="agent-123",
        user_input="Schedule a recurring report",
        enable_hitl=True,
    )
    if paused.run_paused_hitl and paused.hitl_request:
        await client.run_workflow(
            agent_id="agent-123",
            conversation_id=paused.conversation_id,
            enable_hitl=True,
            hitl_resume=HitlResume(
                request_id=paused.hitl_request.request_id,
                decisions=[HitlDecision(type="approve")],
            ),
        )


async def admin_example():
    """Example: Use the same client for control-plane operations."""
    client = SketricGenClient(api_key="sk_api_...")
    me = await client.whoami()
    print(me.display_name)
    async for project in client.projects.list():
        print(project.display_name)


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
