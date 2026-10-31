"""A rerun in the middle of an agent run must not leave the chat locked."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from streamlit.runtime.scriptrunner_utils.exceptions import RerunException

from browser_use_demo import streamlit as app
from browser_use_demo.streamlit import resumable_messages

TOOL_USE = {"type": "tool_use", "id": "t1", "name": "browser", "input": {}}


def test_resumable_messages_drops_unanswered_tool_call():
    messages = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": [{"type": "text", "text": "ok"}, TOOL_USE]},
    ]
    assert resumable_messages(messages) == messages[:1]


def test_resumable_messages_keeps_complete_history():
    messages = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": [TOOL_USE]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": []}]},
        {"role": "assistant", "content": [{"type": "text", "text": "done"}]},
    ]
    assert resumable_messages(messages) == messages


@pytest.mark.asyncio
async def test_rerun_mid_run_unlocks_chat_and_keeps_progress():
    state = SimpleNamespace(
        messages=[], chat_disabled=True, active_response_container=MagicMock(),
        active_messages=[], tools={}, model="m", provider="anthropic",
        system_prompt="", api_key="k", max_tokens=1024, browser_tool=None,
    )

    async def interrupted_loop(*, messages, **kwargs):
        # One full tool round, then a widget click reruns the script mid-call
        messages.append({"role": "assistant", "content": [TOOL_USE]})
        messages.append(
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": []}]}
        )
        messages.append({"role": "assistant", "content": [dict(TOOL_USE, id="t2")]})
        raise RerunException(None)

    with patch.object(app, "st", MagicMock(session_state=state)), patch.object(
        app, "sampling_loop", interrupted_loop
    ), patch.object(app, "MessageRenderer"):
        with pytest.raises(RerunException):
            await app.run_agent("export timesheets")

    assert state.chat_disabled is False
    # User turn and the finished tool round survive; the unanswered call is dropped
    assert [m["role"] for m in state.messages] == ["user", "assistant", "user"]
