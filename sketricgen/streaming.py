"""
SketricGen SDK Streaming Utilities

Handles Server-Sent Events (SSE) parsing for streaming responses.
"""

from typing import AsyncIterator, Iterator, Optional

import httpx

from sketricgen.models.responses import StreamEvent


async def parse_sse_stream(response: httpx.Response) -> AsyncIterator[StreamEvent]:
    """
    Parse Server-Sent Events stream from an async response.

    Yields StreamEvent objects as they arrive from the server.

    Args:
        response: httpx async response object

    Yields:
        StreamEvent objects containing event type and data
    """
    event_type: Optional[str] = None
    data_lines: list[str] = []
    event_id: Optional[str] = None

    async for line in response.aiter_lines():
        line = line.strip()

        # Empty line signals end of event
        if not line:
            if event_type or data_lines:
                yield StreamEvent(
                    event_type=event_type or "message",
                    data="\n".join(data_lines),
                    id=event_id,
                )
                event_type = None
                data_lines = []
                event_id = None
            continue

        # Parse SSE fields
        if line.startswith("event:"):
            event_type = line[6:].strip()
        elif line.startswith("data:"):
            data_lines.append(line[5:].strip())
        elif line.startswith("id:"):
            event_id = line[3:].strip()
        elif line.startswith(":"):
            # Comment line, ignore (often used for heartbeat)
            pass

    # Handle any remaining data
    if event_type or data_lines:
        yield StreamEvent(
            event_type=event_type or "message",
            data="\n".join(data_lines),
            id=event_id,
        )


def parse_sse_stream_sync(response: httpx.Response) -> Iterator[StreamEvent]:
    """
    Parse Server-Sent Events stream from a sync response.

    Yields StreamEvent objects as they arrive from the server.

    Args:
        response: httpx sync response object

    Yields:
        StreamEvent objects containing event type and data
    """
    event_type: Optional[str] = None
    data_lines: list[str] = []
    event_id: Optional[str] = None

    for line in response.iter_lines():
        line = line.strip()

        # Empty line signals end of event
        if not line:
            if event_type or data_lines:
                yield StreamEvent(
                    event_type=event_type or "message",
                    data="\n".join(data_lines),
                    id=event_id,
                )
                event_type = None
                data_lines = []
                event_id = None
            continue

        # Parse SSE fields
        if line.startswith("event:"):
            event_type = line[6:].strip()
        elif line.startswith("data:"):
            data_lines.append(line[5:].strip())
        elif line.startswith("id:"):
            event_id = line[3:].strip()
        elif line.startswith(":"):
            # Comment line, ignore (often used for heartbeat)
            pass

    # Handle any remaining data
    if event_type or data_lines:
        yield StreamEvent(
            event_type=event_type or "message",
            data="\n".join(data_lines),
            id=event_id,
        )
