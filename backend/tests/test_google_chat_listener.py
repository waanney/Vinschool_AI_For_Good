"""
Unit tests for the GoogleChatListener.

Tests cover:
- _parse_chat_event() — decoding Pub/Sub messages
- _process_event() — @mention routing through debouncer
- start()/stop() lifecycle
- Singleton get_google_chat_listener()

All tests mock external dependencies (Pub/Sub, Chat API, ChatService).
"""

import asyncio
import base64
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.chat.google_chat_listener import GoogleChatListener


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pubsub_message(text: str, user_name: str = "users/123",
                          display_name: str = "Parent A",
                          space: str = "spaces/abc",
                          thread: str = "spaces/abc/threads/t1") -> dict:
    """Build a fake Pub/Sub message wrapping a Google Chat MESSAGE event."""
    event = {
        "type": "MESSAGE",
        "message": {
            "text": text,
            "argumentText": text,
            "thread": {"name": thread},
        },
        "space": {"name": space},
        "user": {"name": user_name, "displayName": display_name},
    }
    encoded = base64.b64encode(json.dumps(event).encode()).decode()
    return {"message": {"data": encoded}, "ackId": "ack-123"}


def _make_listener() -> tuple[GoogleChatListener, AsyncMock, AsyncMock]:
    """
    Create a GoogleChatListener with mocked ChatService and reply method.
    """
    mock_chat = MagicMock()
    mock_chat.answer = AsyncMock(return_value="AI answer")
    mock_debouncer = MagicMock()
    mock_debouncer.add = AsyncMock()

    listener = GoogleChatListener(chat_service=mock_chat, debouncer=mock_debouncer)
    listener._reply_to_chat = AsyncMock()  # Mock the Chat API reply

    return listener, mock_chat, mock_debouncer


# ---------------------------------------------------------------------------
# _parse_chat_event
# ---------------------------------------------------------------------------


class TestParseChatEvent:
    """Tests for _parse_chat_event()."""

    def test_parses_valid_message(self):
        """Correctly parses a valid MESSAGE event."""
        listener, _, _ = _make_listener()
        msg = _make_pubsub_message("Bài tập Toán tuần này là gì?")
        event = listener._parse_chat_event(msg)

        assert event is not None
        assert event["type"] == "MESSAGE"
        assert event["text"] == "Bài tập Toán tuần này là gì?"
        assert event["user_id"] == "users/123"
        assert event["user_name"] == "Parent A"
        assert event["space_name"] == "spaces/abc"

    def test_ignores_non_message_events(self):
        """Non-MESSAGE events (ADDED_TO_SPACE, etc.) return None."""
        listener, _, _ = _make_listener()
        event_data = {
            "type": "ADDED_TO_SPACE",
            "space": {"name": "spaces/abc"},
            "user": {"name": "users/1"},
        }
        encoded = base64.b64encode(json.dumps(event_data).encode()).decode()
        msg = {"message": {"data": encoded}}
        result = listener._parse_chat_event(msg)
        assert result is None

    def test_handles_empty_data(self):
        """Empty data field returns None."""
        listener, _, _ = _make_listener()
        result = listener._parse_chat_event({"message": {"data": ""}})
        assert result is None

    def test_handles_invalid_json(self):
        """Invalid JSON data returns None (doesn't crash)."""
        listener, _, _ = _make_listener()
        encoded = base64.b64encode(b"not json").decode()
        result = listener._parse_chat_event({"message": {"data": encoded}})
        assert result is None


# ---------------------------------------------------------------------------
# _process_event
# ---------------------------------------------------------------------------


class TestProcessEvent:
    """Tests for _process_event()."""

    @pytest.mark.asyncio
    async def test_message_added_to_debouncer(self):
        """Any @mention message is added to the debouncer."""
        listener, _, mock_debouncer = _make_listener()

        event = {
            "text": "Bài tập Toán tuần này là gì?",
            "user_id": "users/123",
            "user_name": "Student A",
            "space_name": "spaces/abc",
            "thread_name": "threads/t1",
        }
        await listener._process_event(event)

        mock_debouncer.add.assert_called_once()
        call_kwargs = mock_debouncer.add.call_args
        assert call_kwargs[1]["user_id"] == "gchat-users/123"
        assert call_kwargs[1]["text"] == "Bài tập Toán tuần này là gì?"

    @pytest.mark.asyncio
    async def test_empty_message_sends_hint(self):
        """Empty text (just @mention, no question) sends a usage hint."""
        listener, _, _ = _make_listener()

        event = {
            "text": "",
            "user_id": "users/123",
            "user_name": "Student A",
            "space_name": "spaces/abc",
            "thread_name": "threads/t1",
        }
        await listener._process_event(event)

        listener._reply_to_chat.assert_called_once()
        reply_text = listener._reply_to_chat.call_args[0][1]
        assert "câu hỏi" in reply_text  # Hint message mentions "câu hỏi"


# ---------------------------------------------------------------------------
# _on_debounced callback
# ---------------------------------------------------------------------------


class TestOnDebounced:
    """Tests for the _on_debounced callback."""

    @pytest.mark.asyncio
    async def test_calls_chat_service_and_replies(self):
        """The debounced callback gets AI answer and replies."""
        listener, mock_chat, _ = _make_listener()

        await listener._on_debounced(
            "gchat-users/1", "combined question",
            space_name="spaces/abc",
            thread_name="threads/t1",
            user_name="Student A",
        )

        mock_chat.answer.assert_called_once_with(
            user_id="gchat-users/1",
            question="combined question",
            channel="gchat",
        )
        # Should have been called twice: typing indicator + answer
        assert listener._reply_to_chat.call_count == 2


# ---------------------------------------------------------------------------
# start / stop lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    """Tests for start/stop lifecycle."""

    def test_start_without_config_warns(self):
        """start() does nothing if project_id or subscription not set."""
        listener = GoogleChatListener.__new__(GoogleChatListener)
        listener._running = False
        listener._task = None
        listener._project_id = ""
        listener._subscription = ""

        listener.start()
        assert not listener._running

    def test_stop_sets_running_false(self):
        """stop() sets _running to False."""
        listener, _, _ = _make_listener()
        listener._running = True
        listener._task = MagicMock()
        listener._task.cancel = MagicMock()

        listener.stop()
        assert not listener._running


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


class TestGChatSingleton:
    """Tests for get_google_chat_listener singleton."""

    def test_returns_same_instance(self):
        """get_google_chat_listener() returns the same instance."""
        import services.chat.google_chat_listener as mod

        original = mod._listener
        try:
            mod._listener = None
            with patch.object(GoogleChatListener, "__init__", return_value=None):
                a = mod.get_google_chat_listener()
                b = mod.get_google_chat_listener()
                assert a is b
        finally:
            mod._listener = original
