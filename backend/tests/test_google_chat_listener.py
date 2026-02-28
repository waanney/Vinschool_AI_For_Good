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


# ===== /grade command =====


class TestGradeCommand:
    """Tests for the /grade command."""

    def test_parse_chat_event_extracts_attachments(self):
        """_parse_chat_event() includes attachments from the message."""
        listener, _, _ = _make_listener()
        event_data = {
            "type": "MESSAGE",
            "message": {
                "text": "/grade",
                "argumentText": "/grade",
                "thread": {"name": "spaces/abc/threads/t1"},
                "attachment": [
                    {
                        "contentName": "math_hw.jpg",
                        "contentType": "image/jpeg",
                        "attachmentDataRef": {"resourceName": "media/123"},
                    }
                ],
            },
            "space": {"name": "spaces/abc"},
            "user": {"name": "users/123", "displayName": "Student A"},
        }
        encoded = base64.b64encode(json.dumps(event_data).encode()).decode()
        msg = {"message": {"data": encoded}, "ackId": "ack-grade"}

        event = listener._parse_chat_event(msg)

        assert event is not None
        assert len(event["attachments"]) == 1
        assert event["attachments"][0]["contentName"] == "math_hw.jpg"

    def test_parse_chat_event_empty_attachments(self):
        """_parse_chat_event() returns empty list when no attachments."""
        listener, _, _ = _make_listener()
        msg = _make_pubsub_message("/grade")
        event = listener._parse_chat_event(msg)

        assert event is not None
        assert event["attachments"] == []

    @pytest.mark.asyncio
    async def test_grade_routes_to_handle_grade(self):
        """/grade command routes to _handle_grade()."""
        listener, _, mock_debouncer = _make_listener()

        with patch(
            "services.chat.google_chat_listener.GoogleChatListener._handle_grade",
            new_callable=AsyncMock,
        ) as mock_handle:
            event = {
                "text": "/grade",
                "user_id": "users/123",
                "user_name": "Student A",
                "space_name": "spaces/abc",
                "thread_name": "threads/t1",
                "attachments": [],
            }
            await listener._process_event(event)

        mock_handle.assert_called_once_with(event)
        mock_debouncer.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_grade_no_attachments_sends_hint(self):
        """/grade without attachments sends a usage hint."""
        listener, _, _ = _make_listener()

        event = {
            "text": "/grade",
            "user_id": "users/123",
            "user_name": "Student A",
            "space_name": "spaces/abc",
            "thread_name": "threads/t1",
            "attachments": [],
        }
        await listener._handle_grade(event)

        listener._reply_to_chat.assert_called_once()
        reply_text = listener._reply_to_chat.call_args[0][1]
        assert "/grade" in reply_text

    @pytest.mark.asyncio
    async def test_grade_with_attachments_calls_workflow(self):
        """/grade with attachments downloads, grades, and stores submission."""
        import sys

        listener, _, _ = _make_listener()

        # Mock _download_attachment to return a fake path
        listener._download_attachment = AsyncMock(
            return_value="/tmp/test_hw.jpg"
        )

        # Mock the grading workflow
        mock_result = {
            "success": True,
            "score": 8.5,
            "feedback": "Tốt lắm!",
            "details": {
                "strengths": ["Nhanh"],
                "improvements": ["Cẩn thận hơn"],
                "criteria_scores": {},
            },
            "error": None,
        }

        # Mock assignment
        mock_assignment = MagicMock()
        mock_assignment.max_score = 10.0
        mock_assignment.subject = "Mathematics"
        mock_assignment.title = "Google Chat Submission"

        # Mock workflow
        mock_wf_instance = MagicMock()
        mock_wf_instance.grade_homework = AsyncMock(
            return_value=mock_result
        )
        mock_wf_instance.create_standard_rubric = MagicMock(
            return_value=[]
        )

        # Pre-seed sys.modules to avoid real imports that trigger Milvus
        mock_workflow_module = MagicMock()
        mock_workflow_module.HomeworkGradingWorkflow = MagicMock(
            return_value=mock_wf_instance
        )
        mock_assignment_module = MagicMock()
        mock_assignment_module.Assignment = MagicMock(
            return_value=mock_assignment
        )

        original_wf = sys.modules.get("workflow.homework_grading_workflow")
        original_assign = sys.modules.get("domain.models.assignment")
        try:
            sys.modules["workflow.homework_grading_workflow"] = mock_workflow_module
            sys.modules["domain.models.assignment"] = mock_assignment_module

            with patch(
                "services.chat.submission_store.add_submission",
                return_value={"id": "sub-1"},
            ) as mock_store:
                event = {
                    "text": "/grade",
                    "user_id": "users/123",
                    "user_name": "Student A",
                    "space_name": "spaces/abc",
                    "thread_name": "threads/t1",
                    "attachments": [
                        {
                            "contentName": "hw.jpg",
                            "contentType": "image/jpeg",
                        }
                    ],
                }
                await listener._handle_grade(event)

                # Should have downloaded the attachment
                listener._download_attachment.assert_called_once()

                # Should have called the grading workflow
                mock_wf_instance.grade_homework.assert_called_once()

                # Should have stored in submission store
                mock_store.assert_called_once()
                store_kwargs = mock_store.call_args[1]
                assert store_kwargs["student_name"] == "Student A"
                assert store_kwargs["score"] == 8.5

                # Should have replied (processing indicator + result)
                assert listener._reply_to_chat.call_count == 2
                final_reply = listener._reply_to_chat.call_args_list[1][0][1]
                assert "8.5" in final_reply
                assert "Tốt lắm!" in final_reply
        finally:
            # Restore original modules
            if original_wf is not None:
                sys.modules["workflow.homework_grading_workflow"] = original_wf
            else:
                sys.modules.pop("workflow.homework_grading_workflow", None)
            if original_assign is not None:
                sys.modules["domain.models.assignment"] = original_assign
            else:
                sys.modules.pop("domain.models.assignment", None)
