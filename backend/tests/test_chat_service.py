"""
Unit tests for the Chat Service module.

Tests cover:
- load_lesson_context() — reads from data/lesson.txt
- build_system_prompt() — builds prompt with lesson context
- _create_model() — creates correct model for each provider
- ChatService.answer() — CONFIDENT / ESCALATE routing, history
- clear_history() / reset_chat_service() — cleanup utilities
- Per-user conversation history trimming

All tests mock the LLM to avoid API calls.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_LESSON = "Bài học phân số: 1/3 + 1/4 = 7/12"


class FakeRunResult:
    """Mimics pydantic_ai RunResult with .output attribute."""

    def __init__(self, text: str):
        self.output = text


def _make_chat_service(answer_text: str = "[CONFIDENT] OK"):
    """
    Create a ChatService with a mocked PydanticAI Agent.

    The agent.run() returns *answer_text* without calling any API.
    Both the zalo and gchat agents are patched to the same mock.
    """
    from services.chat.chat_service import ChatService, clear_history

    clear_history()  # Start with clean history

    mock_agent = MagicMock()
    mock_agent.run = AsyncMock(return_value=FakeRunResult(answer_text))

    svc = ChatService(lesson_context=SAMPLE_LESSON, model="test")
    # Patch both channel agents AFTER init
    svc._agent_zalo = mock_agent
    svc._agent_gchat = mock_agent
    return svc


# ---------------------------------------------------------------------------
# load_lesson_context
# ---------------------------------------------------------------------------


class TestLoadLessonContext:
    """Tests for load_lesson_context()."""

    def test_reads_from_file(self, tmp_path):
        """Returns file contents when the lesson file exists."""
        from services.chat import chat_service as mod

        lesson_file = tmp_path / "lesson.txt"
        lesson_file.write_text("Hello lesson", encoding="utf-8")

        original = mod._LESSON_FILE
        try:
            mod._LESSON_FILE = lesson_file
            result = mod.load_lesson_context()
            assert result == "Hello lesson"
        finally:
            mod._LESSON_FILE = original

    def test_returns_empty_when_missing(self, tmp_path):
        """Returns '' when the lesson file does not exist."""
        from services.chat import chat_service as mod

        original = mod._LESSON_FILE
        try:
            mod._LESSON_FILE = tmp_path / "nonexistent.txt"
            result = mod.load_lesson_context()
            assert result == ""
        finally:
            mod._LESSON_FILE = original

    def test_returns_empty_when_file_empty(self, tmp_path):
        """Returns '' when the lesson file is empty."""
        from services.chat import chat_service as mod

        lesson_file = tmp_path / "lesson.txt"
        lesson_file.write_text("", encoding="utf-8")

        original = mod._LESSON_FILE
        try:
            mod._LESSON_FILE = lesson_file
            result = mod.load_lesson_context()
            assert result == ""
        finally:
            mod._LESSON_FILE = original


# ---------------------------------------------------------------------------
# build_system_prompt
# ---------------------------------------------------------------------------


class TestBuildSystemPrompt:
    """Tests for build_system_prompt()."""

    def test_includes_lesson_context(self):
        """The system prompt must contain the lesson context verbatim."""
        from services.chat.chat_service import build_system_prompt

        prompt = build_system_prompt(SAMPLE_LESSON)
        assert SAMPLE_LESSON in prompt

    def test_includes_escalation_tag(self):
        """The prompt must mention [ESCALATE] so the LLM uses it."""
        from services.chat.chat_service import build_system_prompt

        prompt = build_system_prompt("any")
        assert "[ESCALATE]" in prompt

    def test_includes_confident_tag(self):
        """The prompt must mention [CONFIDENT]."""
        from services.chat.chat_service import build_system_prompt

        prompt = build_system_prompt("any")
        assert "[CONFIDENT]" in prompt

    def test_prompt_is_vietnamese(self):
        """The system prompt should be in Vietnamese."""
        from services.chat.chat_service import build_system_prompt

        prompt = build_system_prompt("any")
        assert "tiếng Việt" in prompt

    def test_zalo_prompt_mentions_parents(self):
        """Zalo prompt addresses parents (phụ huynh)."""
        from services.chat.chat_service import build_system_prompt

        prompt = build_system_prompt("any", channel="zalo")
        assert "phụ huynh" in prompt

    def test_gchat_prompt_mentions_students(self):
        """Google Chat prompt addresses students (học sinh)."""
        from services.chat.chat_service import build_system_prompt

        prompt = build_system_prompt("any", channel="gchat")
        assert "học sinh" in prompt
        assert "phụ huynh" not in prompt.split("Quy tắc")[0]  # persona section


# ---------------------------------------------------------------------------
# _create_model
# ---------------------------------------------------------------------------


class TestCreateModel:
    """Tests for _create_model() — verifies it delegates to BaseAgent."""

    def test_delegates_to_base_agent(self):
        """_create_model() should use BaseAgent._create_model() internally."""
        from unittest.mock import patch, MagicMock

        fake_model = MagicMock()
        with patch("agents.base.agent.BaseAgent._create_model", return_value=fake_model):
            from services.chat.chat_service import _create_model

            result = _create_model()
            assert result is fake_model

    def test_unsupported_provider_raises(self):
        """An unsupported provider raises ValueError (via BaseAgent)."""
        from agents.base.agent import AgentConfig

        with patch("services.chat.chat_service.AgentConfig") as MockConfig:
            MockConfig.return_value = AgentConfig(
                provider="cohere",
                model_name="cmd-r",
            )
            from services.chat.chat_service import _create_model

            with pytest.raises(ValueError):
                _create_model()


# ---------------------------------------------------------------------------
# ChatService.answer — CONFIDENT path
# ---------------------------------------------------------------------------


class TestChatServiceConfident:
    """Tests for ChatService.answer() when LLM returns [CONFIDENT]."""

    @pytest.mark.asyncio
    async def test_strips_confident_tag(self):
        """The [CONFIDENT] tag is stripped from the final answer."""
        svc = _make_chat_service("[CONFIDENT] Cộng phân số khác mẫu: quy đồng rồi cộng.")
        answer = await svc.answer("user-1", "Cộng phân số thế nào?")
        assert answer.startswith("Cộng phân số")
        assert "[CONFIDENT]" not in answer

    @pytest.mark.asyncio
    async def test_agent_called_with_question(self):
        """The underlying agent receives the user's question."""
        svc = _make_chat_service("[CONFIDENT] OK")
        await svc.answer("user-1", "Bài tập Toán là gì?")
        svc._agent_zalo.run.assert_called_once()
        prompt = svc._agent_zalo.run.call_args[0][0]
        assert "Bài tập Toán là gì?" in prompt


# ---------------------------------------------------------------------------
# ChatService.answer — ESCALATE path
# ---------------------------------------------------------------------------


class TestChatServiceEscalate:
    """Tests for ChatService.answer() when LLM returns [ESCALATE]."""

    @pytest.mark.asyncio
    async def test_zalo_returns_parent_escalation_message(self):
        """Zalo escalation returns the parent-facing apology (no email)."""
        from services.chat.chat_service import ESCALATION_MESSAGE_ZALO

        svc = _make_chat_service("[ESCALATE] Tôi không biết.")
        answer = await svc.answer("user-1", "Lịch thi cuối kỳ?", channel="zalo")
        assert answer == ESCALATION_MESSAGE_ZALO

    @pytest.mark.asyncio
    async def test_zalo_escalation_does_not_trigger_email(self):
        """An escalation on Zalo just returns the message, no email task."""
        svc = _make_chat_service("[ESCALATE] Không tìm thấy.")

        with patch("asyncio.create_task") as mock_create_task:
            await svc.answer("user-2", "Khi nào thi?", channel="zalo")
            mock_create_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_gchat_returns_student_escalation_message(self):
        """Google Chat escalation returns the student-facing message."""
        from services.chat.chat_service import ESCALATION_MESSAGE_GCHAT

        svc = _make_chat_service("[ESCALATE] Tôi không biết.")
        answer = await svc.answer("user-1", "Lịch thi cuối kỳ?", channel="gchat")
        assert answer == ESCALATION_MESSAGE_GCHAT

    @pytest.mark.asyncio
    async def test_gchat_escalation_triggers_email(self):
        """Google Chat escalation fires an email task to the teacher."""
        svc = _make_chat_service("[ESCALATE] Không tìm thấy.")

        with patch("services.chat.chat_service.asyncio.create_task") as mock_create_task:
            await svc.answer("user-3", "Khi nào thi?", channel="gchat")
            mock_create_task.assert_called_once()


# ---------------------------------------------------------------------------
# ChatService.answer — error handling
# ---------------------------------------------------------------------------


class TestChatServiceError:
    """Tests for ChatService.answer() error handling."""

    @pytest.mark.asyncio
    async def test_returns_error_message_on_exception(self):
        """On LLM exception, returns a user-friendly error string."""
        from services.chat.chat_service import ChatService, clear_history

        clear_history()
        svc = ChatService(lesson_context=SAMPLE_LESSON, model="test")
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(side_effect=RuntimeError("API down"))
        svc._agent_zalo = mock_agent
        svc._agent_gchat = mock_agent

        answer = await svc.answer("user-err", "Hello?")
        assert "sự cố" in answer  # "hệ thống AI đang gặp sự cố"


# ---------------------------------------------------------------------------
# Conversation history
# ---------------------------------------------------------------------------


class TestConversationHistory:
    """Tests for per-user conversation history."""

    @pytest.mark.asyncio
    async def test_history_stored(self):
        """After answer(), both user and assistant messages are stored."""
        from services.chat.chat_service import _get_history, clear_history

        clear_history()
        svc = _make_chat_service("[CONFIDENT] Fine")
        await svc.answer("user-h1", "Xin chào")

        hist = _get_history("user-h1")
        assert len(hist) == 2
        assert hist[0]["role"] == "user"
        assert hist[1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_history_included_in_prompt(self):
        """Follow-up questions include previous conversation history."""
        from services.chat.chat_service import clear_history

        clear_history()
        svc = _make_chat_service("[CONFIDENT] Answer 1")
        await svc.answer("user-h2", "First question")

        svc._agent_zalo.run.reset_mock()
        svc._agent_zalo.run = AsyncMock(return_value=FakeRunResult("[CONFIDENT] Answer 2"))
        await svc.answer("user-h2", "Second question")

        prompt = svc._agent_zalo.run.call_args[0][0]
        assert "First question" in prompt
        assert "Second question" in prompt

    @pytest.mark.asyncio
    async def test_history_trimmed(self):
        """History is trimmed to MAX_HISTORY entries."""
        from services.chat.chat_service import (
            _get_history,
            _add_to_history,
            clear_history,
            MAX_HISTORY,
        )

        clear_history()
        for i in range(MAX_HISTORY + 5):
            _add_to_history("user-trim", "user", f"msg-{i}")

        hist = _get_history("user-trim")
        assert len(hist) == MAX_HISTORY

    def test_clear_history_single_user(self):
        """clear_history(user_id) clears only that user."""
        from services.chat.chat_service import (
            _add_to_history,
            _get_history,
            clear_history,
        )

        clear_history()
        _add_to_history("A", "user", "hello")
        _add_to_history("B", "user", "world")

        clear_history("A")
        assert _get_history("A") == []
        assert len(_get_history("B")) == 1

    def test_clear_history_all(self):
        """clear_history() without args clears all users."""
        from services.chat.chat_service import (
            _add_to_history,
            _get_history,
            clear_history,
        )

        clear_history()
        _add_to_history("A", "user", "hello")
        _add_to_history("B", "user", "world")

        clear_history()
        assert _get_history("A") == []
        assert _get_history("B") == []


# ---------------------------------------------------------------------------
# Singleton helpers
# ---------------------------------------------------------------------------


class TestSingleton:
    """Tests for get_chat_service / reset_chat_service."""

    def test_reset_clears_singleton(self):
        """reset_chat_service() forces a fresh instance next time."""
        from services.chat.chat_service import (
            reset_chat_service,
            _chat_service,
        )
        import services.chat.chat_service as mod

        # Set a dummy singleton
        mod._chat_service = "dummy"
        reset_chat_service()
        assert mod._chat_service is None
