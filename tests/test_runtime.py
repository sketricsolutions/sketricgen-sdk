"""Unified runtime and HITL contract tests."""

import json

import httpx
import pytest
import respx
from pydantic import ValidationError

import sketricgen
from sketricgen import HitlDecision, HitlResume, SketricGenClient
from sketricgen.exceptions import SketricGenValidationError
from sketricgen.models.responses import ChatResponse, StreamEvent

BASE_URL = "https://runtime.test"
WORKFLOW_URL = f"{BASE_URL}/api/v1/run-workflow"


def _client() -> SketricGenClient:
    client = SketricGenClient(api_key="sk_api_test")
    client._config.base_url = BASE_URL
    return client


def _response(**overrides):
    body = {
        "agent_id": "agent-1",
        "user_id": "user-1",
        "conversation_id": "conversation-1",
        "response": "ok",
        "owner": "owner-1",
    }
    body.update(overrides)
    return body


def test_admin_client_is_not_public() -> None:
    assert not hasattr(sketricgen, "AdminClient")


@respx.mock
async def test_run_workflow_opts_into_hitl() -> None:
    route = respx.post(WORKFLOW_URL).mock(
        return_value=httpx.Response(201, json=_response())
    )

    response = await _client().run_workflow(
        agent_id="agent-1", user_input="hello", enable_hitl=True
    )

    assert isinstance(response, ChatResponse)
    assert route.calls.last.request.headers["API-KEY"] == "sk_api_test"
    assert json.loads(route.calls.last.request.content)["enable_hitl"] is True


@respx.mock
async def test_resume_hitl_and_parse_pause_response() -> None:
    route = respx.post(WORKFLOW_URL).mock(
        return_value=httpx.Response(
            201,
            json=_response(
                response="Paused for review",
                run_paused_hitl=True,
                hitl_request={
                    "request_id": "hitl-1",
                    "thread_id": "conversation-1",
                    "run_id": "run-1",
                    "interrupt_ids": ["interrupt-1"],
                    "action_requests": [
                        {"name": "request_human_input", "args": {"questions": []}}
                    ],
                    "review_configs": [{"allowed_decisions": ["respond"]}],
                    "status": "pending",
                },
            ),
        )
    )

    response = await _client().run_workflow(
        agent_id="agent-1",
        conversation_id="conversation-1",
        enable_hitl=True,
        hitl_resume=HitlResume(
            request_id="hitl-1",
            decisions=[HitlDecision(type="respond", message='{"answers":[]}')],
        ),
    )

    assert isinstance(response, ChatResponse)
    assert response.run_paused_hitl is True
    assert response.hitl_request is not None
    assert response.hitl_request.request_id == "hitl-1"
    request = json.loads(route.calls.last.request.content)
    assert request["hitl_resume"]["request_id"] == "hitl-1"
    assert request["user_input"] == ""


def test_resume_requires_conversation_id() -> None:
    with pytest.raises(SketricGenValidationError, match="conversation_id"):
        _client().run_workflow_sync(
            agent_id="agent-1",
            enable_hitl=True,
            hitl_resume=HitlResume(
                request_id="hitl-1",
                decisions=[HitlDecision(type="approve")],
            ),
        )


def test_resume_requires_hitl_opt_in() -> None:
    with pytest.raises(SketricGenValidationError, match="enable_hitl"):
        _client().run_workflow_sync(
            agent_id="agent-1",
            conversation_id="conversation-1",
            hitl_resume=HitlResume(
                request_id="hitl-1",
                decisions=[HitlDecision(type="approve")],
            ),
        )


def test_resume_rejects_unknown_decision_type() -> None:
    with pytest.raises(ValidationError):
        HitlDecision(type="edit")


@respx.mock
def test_sync_resume_uses_same_contract() -> None:
    route = respx.post(WORKFLOW_URL).mock(
        return_value=httpx.Response(201, json=_response())
    )

    response = _client().run_workflow_sync(
        agent_id="agent-1",
        conversation_id="conversation-1",
        enable_hitl=True,
        hitl_resume=HitlResume(
            request_id="hitl-1",
            decisions=[HitlDecision(type="reject")],
        ),
    )

    assert isinstance(response, ChatResponse)
    request = json.loads(route.calls.last.request.content)
    assert request["hitl_resume"]["decisions"] == [{"type": "reject"}]


@pytest.mark.parametrize(
    ("event_type", "terminal"),
    [
        ("TEXT_MESSAGE_CONTENT", False),
        ("RUN_FINISHED", True),
        ("RUN_ERROR", True),
        ("RUN_PAUSED_HITL", True),
    ],
)
def test_stream_terminal_events(event_type: str, terminal: bool) -> None:
    assert StreamEvent(event_type=event_type, data="{}").is_terminal is terminal


def test_data_only_sse_terminal_event() -> None:
    event = StreamEvent(event_type="message", data='{"type":"RUN_PAUSED_HITL"}')
    assert event.is_terminal is True
