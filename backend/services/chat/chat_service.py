"""
Channel-aware chat orchestrator.

Receives debounced messages from any platform (Zalo clone, Google Chat),
calls the LLM for an answer, and returns the response.

Two channels are supported, each with its own persona and behaviour:

- **zalo** (default): AI ↔ parents.  Uses polite parent-facing Vietnamese
  (kính ngữ). When the LLM is not confident the answer simply apologises;
  no escalation email is sent.
- **gchat**: AI ↔ students.  Uses friendly student-facing Vietnamese.
  When the LLM is not confident an escalation email is sent to the
  homeroom teacher *and* the student is told the question was forwarded.

Architecture:
    Platform (Zalo / Google Chat)
        → Debouncer (3s quiet window)
        → ChatService.answer(channel=…)
        → LLM (provider from settings.default_provider)
        → Response routed back to platform

Lesson context is loaded from ``data/lesson.txt`` at startup.
The LLM provider (Gemini / OpenAI / Anthropic) is resolved from
``DEFAULT_PROVIDER`` and ``DEFAULT_LLM_MODEL`` in ``.env``.
"""

import asyncio
import pathlib
from typing import Optional

from pydantic_ai import Agent as PydanticAgent

from agents.base.agent import BaseAgent, AgentConfig
from config import settings
from utils.logger import logger

# Supported channel identifiers
CHANNEL_ZALO = "zalo"
CHANNEL_GCHAT = "gchat"


# ===== Lesson context — loaded from data/lesson.txt =====

_DATA_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "data"
_LESSON_FILE = _DATA_DIR / "lesson.txt"


def load_lesson_context() -> str:
    """
    Load lesson context from ``data/lesson.txt``.

    Returns the file contents, or an empty string if the file is missing.
    """
    try:
        text = _LESSON_FILE.read_text(encoding="utf-8").strip()
        if text:
            logger.info(f"[CHAT] Loaded lesson context from {_LESSON_FILE} ({len(text)} chars)")
        else:
            logger.warning(f"[CHAT] Lesson file is empty: {_LESSON_FILE}")
        return text
    except FileNotFoundError:
        logger.warning(f"[CHAT] Lesson file not found: {_LESSON_FILE}")
        return ""
    except Exception as e:
        logger.error(f"[CHAT] Error reading lesson file: {e}")
        return ""


def build_system_prompt(lesson_context: str, channel: str = CHANNEL_ZALO) -> str:
    """Build the system prompt for the given *channel*.

    Args:
        lesson_context: Lesson text to embed.
        channel: ``"zalo"`` (parent-facing) or ``"gchat"`` (student-facing).
    """
    if channel == CHANNEL_GCHAT:
        persona = (
            "Bạn là Cô Hana - trợ lý AI thông minh của Vinschool, "
            "hỗ trợ học sinh lớp 4B5.\n\n"
            "Nhiệm vụ:\n"
            "- Trả lời câu hỏi về bài học, bài tập, lịch học dựa trên tài liệu được cung cấp\n"
            "- Giải thích kiến thức phù hợp với học sinh lớp 4\n"
            "- Luôn thân thiện, dễ hiểu, dùng ngôn ngữ phù hợp với học sinh\n"
            "- Xưng \"cô\", gọi học sinh là \"con\" hoặc \"các con\"\n"
            "- Trả lời bằng tiếng Việt"
        )
    else:
        persona = (
            "Bạn là Cô Hana - trợ lý AI thông minh của Vinschool, "
            "hỗ trợ phụ huynh lớp 4B5.\n\n"
            "Nhiệm vụ:\n"
            "- Trả lời câu hỏi về bài học, bài tập, lịch học dựa trên tài liệu được cung cấp\n"
            "- Giải thích kiến thức phù hợp với học sinh lớp 4\n"
            "- Luôn thân thiện, lịch sự, dùng kính ngữ với phụ huynh\n"
            "- Xưng \"cô Hana\", gọi phụ huynh là \"Quý phụ huynh\" hoặc \"bố mẹ các con\"\n"
            "- Trả lời bằng tiếng Việt"
        )

    return f"""{persona}

Tài liệu học tập hiện tại:
{lesson_context}

Quy tắc:
1. CHỈ trả lời dựa trên tài liệu được cung cấp ở trên
2. Nếu câu hỏi KHÔNG liên quan đến nội dung học tập hoặc bạn KHÔNG TÌM THẤY \
thông tin trong tài liệu, hãy bắt đầu câu trả lời bằng: "[ESCALATE]"
3. Nếu bạn TÌM THẤY thông tin và TỰ TIN trả lời, hãy bắt đầu bằng: "[CONFIDENT]"
4. Sau tag [CONFIDENT] hoặc [ESCALATE], viết câu trả lời bình thường bằng tiếng Việt
5. Giữ câu trả lời ngắn gọn, dễ hiểu (dưới 300 từ)
"""


# ===== LLM model creation — delegates to BaseAgent =====

def _create_model():
    """
    Create PydanticAI model from settings.

    Delegates to ``BaseAgent._create_model()`` so provider logic
    is defined in exactly one place.
    """
    helper = BaseAgent.__new__(BaseAgent)
    helper.config = AgentConfig()
    return helper._create_model()


# ===== Per-user conversation history =====

_conversation_history: dict[str, list[dict[str, str]]] = {}
MAX_HISTORY = 10  # Keep last 10 messages per user


def _get_history(user_id: str) -> list[dict[str, str]]:
    """Get conversation history for a user."""
    return _conversation_history.get(user_id, [])


def _add_to_history(user_id: str, role: str, text: str) -> None:
    """Add a message to conversation history."""
    if user_id not in _conversation_history:
        _conversation_history[user_id] = []
    _conversation_history[user_id].append({"role": role, "text": text})
    # Trim to max history
    if len(_conversation_history[user_id]) > MAX_HISTORY:
        _conversation_history[user_id] = _conversation_history[user_id][-MAX_HISTORY:]


def clear_history(user_id: Optional[str] = None) -> None:
    """Clear conversation history (for a user or all users)."""
    global _conversation_history
    if user_id:
        _conversation_history.pop(user_id, None)
    else:
        _conversation_history.clear()


# ===== Escalation =====

ESCALATION_MESSAGE_ZALO = (
    "Xin lỗi, cô Hana hiện không có thông tin về vấn đề này ạ. "
    "Phụ huynh vui lòng liên hệ trực tiếp giáo viên chủ nhiệm "
    "để được hỗ trợ nhé ạ! 🙏"
)

ESCALATION_MESSAGE_GCHAT = (
    "Cô Hana chưa có thông tin về vấn đề này. "
    "Cô đã chuyển câu hỏi đến giáo viên chủ nhiệm, "
    "thầy/cô sẽ phản hồi sớm nhất nhé con! 📚"
)

# Backward-compat alias used in a few tests
ESCALATION_MESSAGE = ESCALATION_MESSAGE_ZALO


async def _send_escalation_email(user_id: str, question: str) -> None:
    """
    Send an escalation email to the teacher.

    Uses the existing EmailNotifier from the notification service.
    Falls back to logging if email is not configured.
    """
    try:
        from services.notification.models import (
            Notification,
            NotificationType,
            NotificationChannel,
            StudentInfo,
        )
        from services.notification import NotificationService

        service = NotificationService.for_escalation(
            teacher_email=settings.TEACHER_EMAIL,
            teacher_name="Giáo viên chủ nhiệm",
        )

        notification = Notification(
            notification_type=NotificationType.TEACHER_ESCALATION,
            channel=NotificationChannel.EMAIL,
            student=StudentInfo(
                student_id=user_id,
                name=user_id,
                grade="4",
                class_name="4B5",
            ),
            title=f"[Escalation] Câu hỏi từ phụ huynh: {question[:60]}",
            message=(
                f"Phụ huynh (ID: {user_id}) đã hỏi một câu ngoài phạm vi tài liệu:\n\n"
                f"Câu hỏi: {question}\n\n"
                f"Hệ thống AI không đủ tự tin để trả lời. "
                f"Vui lòng phản hồi trực tiếp trong nhóm chat."
            ),
        )

        results = await service.send(notification)
        for r in results:
            if r.success:
                logger.info(f"[ESCALATION] Email sent for user {user_id}")
            else:
                logger.warning(f"[ESCALATION] Email failed: {r.error_message}")

    except Exception as e:
        logger.warning(f"[ESCALATION] Could not send email (may not be configured): {e}")
        logger.info(
            f"[ESCALATION] Question from {user_id} needs teacher attention: {question}"
        )


# ===== ChatService =====

class ChatService:
    """
    Main chat orchestrator.

    Handles AI Q&A for two channels:

    * **zalo** — parent-facing (``/ask`` command in Zalo clone UI)
    * **gchat** — student-facing (``@BotName`` mention in Google Chat)

    Each channel gets its own PydanticAI agent with a tailored system
    prompt and escalation behaviour.
    """

    def __init__(self, lesson_context: Optional[str] = None, model=None):
        """
        Args:
            lesson_context: Lesson text to embed in the system prompt.
                            If None, loads from ``data/lesson.txt``.
            model: PydanticAI model to use. If None, created from settings.
        """
        # Load lesson context
        if lesson_context is None:
            lesson_context = load_lesson_context()
        self._lesson_context = lesson_context

        # Create model
        if model is None:
            model = _create_model()

        # Channel-specific agents (share the same model, different prompts)
        self._agent_zalo = PydanticAgent(
            model=model,
            system_prompt=build_system_prompt(lesson_context, channel=CHANNEL_ZALO),
        )
        self._agent_gchat = PydanticAgent(
            model=model,
            system_prompt=build_system_prompt(lesson_context, channel=CHANNEL_GCHAT),
        )

        logger.info(
            f"[CHAT] ChatService initialized with provider={settings.default_provider}, "
            f"model={settings.default_llm_model} "
            f"(lesson: {len(lesson_context)} chars)"
        )

    async def answer(self, user_id: str, question: str, channel: str = CHANNEL_ZALO) -> str:
        """
        Answer a question from a user.

        Args:
            user_id: Unique user identifier (e.g., "zalo-parent-123")
            question: The question text (already stripped of command prefix)
            channel: ``"zalo"`` (parent) or ``"gchat"`` (student)

        Returns:
            AI response text (plain Vietnamese)
        """
        try:
            # Select channel-specific agent & labels
            if channel == CHANNEL_GCHAT:
                agent = self._agent_gchat
                user_label = "Học sinh"
                prompt_prefix = "Câu hỏi mới từ học sinh"
            else:
                agent = self._agent_zalo
                user_label = "Phụ huynh"
                prompt_prefix = "Câu hỏi mới từ phụ huynh"

            # Build prompt with conversation history
            history = _get_history(user_id)
            history_str = ""
            if history:
                history_lines = []
                for msg in history[-6:]:  # Last 6 messages for context
                    role_label = user_label if msg["role"] == "user" else "Cô Hana"
                    history_lines.append(f"{role_label}: {msg['text']}")
                history_str = (
                    "\nLịch sử cuộc trò chuyện gần đây:\n"
                    + "\n".join(history_lines)
                    + "\n\n"
                )

            prompt = f"{history_str}{prompt_prefix}: {question}"

            # Call LLM
            result = await agent.run(prompt)
            raw_answer = str(result.output).strip()

            # Parse confidence tag
            escalate = False
            answer_text = raw_answer

            if raw_answer.startswith("[ESCALATE]"):
                escalate = True
                if channel == CHANNEL_GCHAT:
                    answer_text = ESCALATION_MESSAGE_GCHAT
                    # Fire-and-forget escalation email to teacher
                    asyncio.create_task(
                        _send_escalation_email(user_id, question)
                    )
                else:
                    answer_text = ESCALATION_MESSAGE_ZALO

            elif raw_answer.startswith("[CONFIDENT]"):
                answer_text = raw_answer.replace("[CONFIDENT]", "").strip()

            # Update history
            _add_to_history(user_id, "user", question)
            _add_to_history(user_id, "assistant", answer_text)

            logger.info(
                f"[CHAT] Answered for {user_id} ({channel}): "
                f"{'ESCALATED' if escalate else 'CONFIDENT'} "
                f"({len(answer_text)} chars)"
            )

            return answer_text

        except Exception as e:
            logger.error(f"[CHAT] Error answering question: {e}")
            return (
                "Xin lỗi, hệ thống AI đang gặp sự cố. "
                "Vui lòng thử lại sau hoặc liên hệ giáo viên trực tiếp ạ."
            )


# ===== Singleton =====

_chat_service: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    """Get or create the global ChatService instance."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service


def reset_chat_service() -> None:
    """Reset the singleton (useful for tests or hot-reloading lesson data)."""
    global _chat_service
    _chat_service = None
    clear_history()
