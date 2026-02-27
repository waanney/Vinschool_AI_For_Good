"""
Unit tests for the GoogleChatListener.

Tests cover:
- _parse_chat_event() — decoding Pub/Sub messages
- _process_event() — slash command routing (/ask, /dailysum, /demosum)
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


# ===== Helpers =====


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
    Create a GoogleChatListener with mocked ChatService and reply/delete methods.
    """
    mock_chat = MagicMock()
    mock_chat.answer = AsyncMock(return_value="AI answer")
    mock_debouncer = MagicMock()
    mock_debouncer.add = AsyncMock()

    listener = GoogleChatListener(chat_service=mock_chat, debouncer=mock_debouncer)
    listener._reply_to_chat = AsyncMock(return_value="spaces/abc/messages/msg-123")
    listener._delete_message = AsyncMock()

    return listener, mock_chat, mock_debouncer


# ===== _parse_chat_event =====


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


# ===== _process_event =====


class TestProcessEvent:
    """Tests for _process_event()."""

    @pytest.mark.asyncio
    async def test_ask_message_added_to_debouncer(self):
        """"/ask <question> is stripped and forwarded to the debouncer."""
        listener, _, mock_debouncer = _make_listener()

        event = {
            "text": "/ask Bài tập Toán tuần này là gì?",
            "user_id": "users/123",
            "user_name": "Student A",
            "space_name": "spaces/abc",
            "thread_name": "threads/t1",
        }
        await listener._process_event(event)

        mock_debouncer.add.assert_called_once()
        call_kwargs = mock_debouncer.add.call_args
        assert call_kwargs[1]["user_id"] == "gchat-users/123"
        # /ask prefix is stripped before passing to debouncer
        assert call_kwargs[1]["text"] == "Bài tập Toán tuần này là gì?"

    @pytest.mark.asyncio
    async def test_non_command_message_ignored(self):
        """Messages without /ask or /dailysum prefix are silently ignored."""
        listener, _, mock_debouncer = _make_listener()

        event = {
            "text": "Chào cô!",  # No command prefix
            "user_id": "users/123",
            "user_name": "Student A",
            "space_name": "spaces/abc",
            "thread_name": "threads/t1",
        }
        await listener._process_event(event)

        # Debouncer not touched, no reply sent
        mock_debouncer.add.assert_not_called()
        listener._reply_to_chat.assert_not_called()

    @pytest.mark.asyncio
    async def test_ask_with_no_question_sends_hint(self):
        """/ask with no question text sends a usage hint."""
        listener, _, _ = _make_listener()

        event = {
            "text": "/ask",
            "user_id": "users/123",
            "user_name": "Student A",
            "space_name": "spaces/abc",
            "thread_name": "threads/t1",
        }
        await listener._process_event(event)

        listener._reply_to_chat.assert_called_once()
        reply_text = listener._reply_to_chat.call_args[0][1]
        assert "/ask" in reply_text  # Hint message refers to /ask

    @pytest.mark.asyncio
    async def test_empty_message_ignored(self):
        """Completely empty text is silently ignored."""
        listener, _, mock_debouncer = _make_listener()

        event = {
            "text": "",
            "user_id": "users/123",
            "user_name": "Student A",
            "space_name": "spaces/abc",
            "thread_name": "threads/t1",
        }
        await listener._process_event(event)

        mock_debouncer.add.assert_not_called()
        listener._reply_to_chat.assert_not_called()

    @pytest.mark.asyncio
    async def test_dailysum_command_handled(self):
        """/dailysum triggers _handle_dailysum (typing + summary + delete)."""
        listener, _, mock_debouncer = _make_listener()

        with patch(
            "services.chat.google_chat_listener.GoogleChatListener._handle_dailysum",
            new_callable=AsyncMock,
        ) as mock_handle:
            event = {
                "text": "/dailysum",
                "user_id": "users/123",
                "user_name": "Student A",
                "space_name": "spaces/abc",
                "thread_name": "threads/t1",
            }
            await listener._process_event(event)

        mock_handle.assert_called_once_with(event)
        mock_debouncer.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_demosum_command_handled(self):
        """/demosum triggers _handle_demosum (hardcoded summary)."""
        listener, _, mock_debouncer = _make_listener()

        with patch(
            "services.chat.google_chat_listener.GoogleChatListener._handle_demosum",
            new_callable=AsyncMock,
        ) as mock_handle:
            event = {
                "text": "/demosum",
                "user_id": "users/123",
                "user_name": "Student A",
                "space_name": "spaces/abc",
                "thread_name": "threads/t1",
            }
            await listener._process_event(event)

        mock_handle.assert_called_once_with(event)
        mock_debouncer.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_demosum_posts_hardcoded_content(self):
        """_handle_demosum sends the hardcoded DEMO_LESSON_CONTENT_STUDENTS."""
        listener, _, _ = _make_listener()

        event = {
            "text": "/demosum",
            "user_id": "users/123",
            "user_name": "Student A",
            "space_name": "spaces/abc",
            "thread_name": "threads/t1",
        }
        await listener._handle_demosum(event)

        # Should have a single reply call (no typing indicator)
        listener._reply_to_chat.assert_called_once()
        listener._delete_message.assert_not_called()
        reply_text = listener._reply_to_chat.call_args[0][1]
        assert "Toán" in reply_text  # Contains lesson content

    @pytest.mark.asyncio
    async def test_handle_dailysum_calls_ai(self):
        """_handle_dailysum calls chat_service.summarize_daily and posts the result."""
        listener, mock_chat, _ = _make_listener()
        mock_chat.summarize_daily = AsyncMock(return_value="AI generated summary")

        event = {
            "text": "/dailysum",
            "user_id": "users/123",
            "user_name": "Student A",
            "space_name": "spaces/abc",
            "thread_name": "threads/t1",
        }
        await listener._handle_dailysum(event)

        mock_chat.summarize_daily.assert_called_once_with(channel="gchat")
        listener._reply_to_chat.assert_called_once()
        listener._delete_message.assert_not_called()
        reply_text = listener._reply_to_chat.call_args[0][1]
        assert reply_text == "AI generated summary"


class TestOnDebounced:
    """Tests for the _on_debounced callback."""

    @pytest.mark.asyncio
    async def test_calls_chat_service_and_replies(self):
        """The debounced callback gets AI answer and sends a single reply (no typing indicator)."""
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
            user_name="Student A",
        )
        # Single reply — no typing indicator
        assert listener._reply_to_chat.call_count == 1
        # No delete call — no typing indicator to remove
        listener._delete_message.assert_not_called()


# ===== start / stop lifecycle =====


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


# ===== Singleton =====


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
