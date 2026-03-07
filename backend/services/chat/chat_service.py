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
  When a student asks about their grades, Milvus is queried for recent
  grading results and the context is injected into the LLM prompt.

Architecture:
    Platform (Zalo / Google Chat)
        → Debouncer (3s quiet window)
        → ChatService.answer(channel=…)
        → LLM (provider from settings.default_provider)
        → Response routed back to platform

Lesson context is fetched from **Milvus** in production; falls back to
``data/lesson.txt`` for local development (see ``load_lesson_context()``).
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
    Load lesson context for the AI prompt.

    Strategy:
    1. **Production** — query Milvus vector DB for the latest lesson
       documents (requires ``MILVUS_HOST`` in ``.env``).
    2. **Demo / fallback** — read from ``data/lesson.txt``.

    Returns the combined context text, or an empty string if nothing
    is available.
    """
    # Try Milvus first (production)
    try:
        from config.settings import get_settings
        s = get_settings()
        if getattr(s, "MILVUS_HOST", None):
            from database.milvus_client import get_milvus_client
            client = get_milvus_client()
            if client and hasattr(client, "search"):
                logger.info("[CHAT] Attempting to load lesson context from Milvus")
                # In production, retrieve recent lesson documents
                # For now this is a hook — the actual query depends on
                # how documents are stored.  Falls through to file-based
                # if Milvus is not populated.
    except Exception as e:
        logger.debug(f"[CHAT] Milvus not available, falling back to file: {e}")

    # Fallback: read from data/lesson.txt
    return _load_lesson_from_file()


def _load_lesson_from_file() -> str:
    """Read lesson context from the local ``data/lesson.txt`` file."""
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
        persona = """
Bạn là Cô Hana - trợ lý AI thông minh của Vinschool, hỗ trợ học sinh lớp 4B5.

Nhiệm vụ:
- Trả lời câu hỏi về bài học, bài tập, lịch học dựa trên tài liệu được cung cấp
- Trả lời câu hỏi về điểm số, nhận xét, kết quả chấm bài nếu có kết quả chấm bài trong ngữ cảnh
- Giải thích kiến thức phù hợp với học sinh lớp 4
- Luôn thân thiện, dễ hiểu, dùng ngôn ngữ phù hợp với học sinh
- Xưng "cô", gọi học sinh là "con" hoặc "các con"
- Trả lời bằng tiếng Việt
"""
    else:
        persona = """
Bạn là Cô Hana - trợ lý AI thông minh của Vinschool, hỗ trợ phụ huynh lớp 4B5.

Nhiệm vụ:
- Trả lời câu hỏi về bài học, bài tập, lịch học dựa trên tài liệu được cung cấp
- Giải thích kiến thức phù hợp với học sinh lớp 4
- Luôn thân thiện, lịch sự, dùng kính ngữ với phụ huynh
- Xưng "cô Hana", gọi phụ huynh là "Quý phụ huynh" hoặc "bố mẹ các con"
- Trả lời bằng tiếng Việt
"""

    return f"""{persona}

Tài liệu học tập hiện tại:
{lesson_context}

Quy tắc:
1. CHỈ trả lời dựa trên: (a) tài liệu học tập ở trên, hoặc \
(b) phần "[Ngữ cảnh bổ sung]" trong tin nhắn của học sinh nếu có
2. Nếu học sinh/phụ huynh chào hỏi (ví dụ: "Xin chào", "Hello", "Chào cô", "Good morning", \
"Hi", "Cô ơi", "How are you?", hoặc bất kỳ lời chào/thăm hỏi nào), hãy đáp lại \
thân thiện bằng "[CONFIDENT]" kèm lời chào lại. KHÔNG escalate lời chào.
3. Nếu câu hỏi KHÔNG liên quan đến nội dung học tập VÀ KHÔNG phải lời chào/thăm hỏi, \
VÀ KHÔNG có thông tin liên quan trong "[Ngữ cảnh bổ sung]", \
hãy bắt đầu câu trả lời bằng: "[ESCALATE]"
4. Nếu bạn TÌM THẤY thông tin (trong tài liệu HOẶC trong "[Ngữ cảnh bổ sung]") \
và TỰ TIN trả lời, hãy bắt đầu bằng: "[CONFIDENT]"
5. Sau tag [CONFIDENT] hoặc [ESCALATE], viết câu trả lời bình thường bằng tiếng Việt
6. Giữ câu trả lời ngắn gọn, dễ hiểu (dưới 300 từ)
7. ĐỊNH DẠNG: Dùng dấu gạch ngang (-) cho danh sách, KHÔNG dùng dấu sao (*) để in đậm hoặc in nghiêng
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
    "để được hỗ trợ nhé ạ!"
)

ESCALATION_MESSAGE_GCHAT = (
    "Cô Hana chưa có thông tin về vấn đề này. "
    "Cô đã chuyển câu hỏi đến giáo viên chủ nhiệm, "
    "thầy/cô sẽ phản hồi sớm nhất nhé con!"
)

# Backward-compat alias used in a few tests
ESCALATION_MESSAGE = ESCALATION_MESSAGE_ZALO


async def _send_escalation_email(
    user_id: str, user_name: str, question: str
) -> None:
    """
    Send an escalation email to the configured teacher(s).

    Uses the existing ``NotificationService.create_teacher_escalation()``
    factory method so we don't duplicate notification-building logic.
    ``TEACHER_EMAIL`` may contain multiple comma-separated addresses;
    the EmailNotifier delivers to all of them in a single transaction.
    Falls back to logging if email delivery fails.
    """
    try:
        from services.notification import NotificationService
        from services.notification.models import TeacherInfo, StudentInfo

        service = NotificationService()

        teacher = TeacherInfo(
            teacher_id="homeroom",
            name="Giáo viên chủ nhiệm",
            email=settings.TEACHER_EMAIL,
        )

        student = StudentInfo(
            student_id=user_id,
            name=user_name,
            grade="4",
            class_name="4B5",
        )

        notification = service.create_teacher_escalation(
            teacher=teacher,
            student=student,
            question=question,
            reason="Câu hỏi ngoài phạm vi tài liệu, AI không đủ tự tin trả lời",
        )

        results = await service.send(notification)
        for r in results:
            if r.success:
                logger.info(
                    f"[ESCALATION] Email sent to {len(settings.teacher_emails)} teacher(s) "
                    f"for {user_name} ({user_id})"
                )
            else:
                logger.warning(f"[ESCALATION] Email failed: {r.error_message}")

    except Exception as e:
        logger.warning(f"[ESCALATION] Could not send email: {e}")
        logger.info(
            f"[ESCALATION] Question from {user_name} needs teacher attention: {question}"
        )


# ===== Grading context retrieval (Milvus) =====

async def _fetch_grading_context(
    question: str, user_id: str, channel: str
) -> str:
    """
    Query Milvus for grading results relevant to the student's question.

    Only applies to ``gchat`` channel (students).  Returns a formatted
    context string that is prepended to the LLM prompt, or an empty
    string if Milvus is unavailable or no results match.
    """
    if channel != CHANNEL_GCHAT:
        return ""

    try:
        from database.repositories.grading_repository import (
            search_student_grades,
        )

        results = await search_student_grades(
            query=question,
            student_id=user_id,
            top_k=3,
        )

        if not results:
            return ""

        lines = [
            "[Ngữ cảnh bổ sung — kết quả chấm bài của học sinh này, dùng để trả lời câu hỏi về điểm số:]",
        ]
        for r in results:
            meta = r.get("metadata", {})
            lines.append(
                f"- Bài: {meta.get('assignment_title', '?')}, "
                f"Điểm: {r['score']}/{r['max_score']}, "
                f"Nhận xét ngắn: {meta.get('feedback', '')}"
            )
            if meta.get("detailed_feedback"):
                lines.append(f"  Nhận xét chi tiết: {meta['detailed_feedback']}")
            if meta.get("strengths"):
                lines.append(f"  Điểm mạnh: {', '.join(meta['strengths'])}")
            if meta.get("improvements"):
                lines.append(
                    f"  Cần cải thiện: {', '.join(meta['improvements'])}"
                )
        lines.append("[Hết ngữ cảnh bổ sung]")

        logger.info(
            f"[CHAT] Injected {len(results)} grading result(s) "
            f"into prompt for {user_id}"
        )
        return "\n".join(lines)

    except Exception as e:
        logger.debug(f"[CHAT] Grading context lookup skipped: {e}")
        return ""


# ===== ChatService =====

class ChatService:
    """
    Main chat orchestrator.

    Handles AI Q&A and daily summaries for two channels:

    * **zalo** — parent-facing (``/ask``, ``/dailysum``, ``/demosum`` commands in Zalo clone UI)
    * **gchat** — student-facing (``@BotName /ask``, ``/dailysum``, ``/demosum`` in Google Chat)

    Each channel gets its own PydanticAI agent with a tailored system
    prompt and escalation behaviour.  Every command returns a single
    reply — no intermediate typing indicator messages.
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

    async def answer(
        self,
        user_id: str,
        question: str,
        channel: str = CHANNEL_ZALO,
        user_name: Optional[str] = None,
    ) -> str:
        """
        Answer a question from a user.

        Args:
            user_id: Unique user identifier (e.g., "zalo-parent-123")
            question: The question text (already stripped of command prefix)
            channel: ``"zalo"`` (parent) or ``"gchat"`` (student)
            user_name: Display name of the user (for escalation emails).
                       Falls back to *user_id* if not provided.

        Returns:
            AI response text (plain Vietnamese)
        """
        display_name = user_name or user_id
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

            # Attempt to enrich prompt with grading results from Milvus.
            # If the student asks about their score / feedback, Milvus
            # returns relevant grading records so Cô Hana can answer.
            grading_context = await _fetch_grading_context(
                question, user_id, channel
            )
            if grading_context:
                prompt = f"{grading_context}\n\n{prompt}"

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
                        _send_escalation_email(user_id, display_name, question)
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

    async def summarize_daily(self, channel: str = CHANNEL_ZALO) -> str:
        """
        Generate a daily lesson summary using the AI agent.

        Reads from the same lesson context that powers /ask, then asks
        the LLM to produce a friendly plain-text summary suitable for
        the given channel (parent-facing for Zalo, student-facing for
        Google Chat).

        Args:
            channel: ``"zalo"`` (parent) or ``"gchat"`` (student).

        Returns:
            AI-generated plain-text summary.
        """
        if not self._lesson_context:
            return (
                "Xin lỗi, hiện chưa có dữ liệu bài học hôm nay. "
                "Vui lòng thử lại sau ạ."
            )

        if channel == CHANNEL_GCHAT:
            agent = self._agent_gchat
            instruction = """
Tóm tắt toàn bộ bài học hôm nay thành 1 tin nhắn duy nhất gửi cho học sinh.

YÊU CẦU NỘI DUNG:
(1) Mỗi môn: nêu chủ đề + kiến thức chính + bài tập + hạn nộp/lưu ý (nếu có).
(2) Nếu thiếu thông tin phần nào, ghi đúng: "Không có".

YÊU CẦU ĐỊNH DẠNG (BẮT BUỘC):
(1) Xuất PLAIN TEXT, KHÔNG Markdown.
(2) CẤM dùng các ký tự: *, **, _, `, #, >.
(3) Danh sách môn học chỉ dùng số thứ tự: 1., 2., 3., ...
(4) Dưới mỗi môn, chỉ dùng gạch ngang (-) cho đúng 3 dòng con theo thứ tự:
    - Kiến thức:
    - Bài tập về nhà:
    - Hạn nộp/Lưu ý:
(5) KHÔNG thêm mục/đoạn nào khác ngoài mẫu.

TRẢ VỀ ĐÚNG THEO MẪU NÀY (GIỮ NGUYÊN XUỐNG DÒNG):
Các con thân mến,
Cô Hana gửi lại nội dung buổi học ngày hôm nay của các con:

1. <Môn> - <Chủ đề>
- Kiến thức: <...>
- Bài tập về nhà: <...>
- Hạn nộp/Lưu ý: <...>

2. <Môn> - <Chủ đề>
- Kiến thức: <...>
- Bài tập về nhà: <...>
- Hạn nộp/Lưu ý: <...>

Các con nhớ hoàn thành bài tập đầy đủ nhé!
Trân trọng,
Cô Hana

TỰ KIỂM TRA: Nếu còn xuất hiện bất kỳ ký tự bị cấm (*, _, `, #, >) hoặc có định dạng khác mẫu,
hãy tự viết lại cho đúng rồi mới gửi."""
        else:
            agent = self._agent_zalo
            instruction = """
Tóm tắt toàn bộ bài học hôm nay thành 1 tin nhắn duy nhất gửi cho phụ huynh.

YÊU CẦU NỘI DUNG:
(1) Mỗi môn: nêu chủ đề + kiến thức chính + bài tập + hạn nộp/lưu ý (nếu có).
(2) Nếu thiếu thông tin phần nào, ghi đúng: "Không có".
(3) Nếu có link tài liệu thì ghi vào phần "Hạn nộp/Lưu ý". Nếu không có, ghi: "Không có".

YÊU CẦU ĐỊNH DẠNG (BẮT BUỘC):
(1) Xuất PLAIN TEXT, KHÔNG Markdown.
(2) CẤM dùng các ký tự: *, **, _, `, #, >.
(3) Danh sách môn học chỉ dùng số thứ tự: 1., 2., 3., ...
(4) Dưới mỗi môn, chỉ dùng gạch ngang (-) cho đúng 3 dòng con theo thứ tự:
    - Kiến thức:
    - Bài tập về nhà:
    - Hạn nộp/Lưu ý:
(5) KHÔNG thêm mục/đoạn nào khác ngoài mẫu.

TRẢ VỀ ĐÚNG THEO MẪU NÀY (GIỮ NGUYÊN XUỐNG DÒNG):
Bố mẹ các con thân mến,
Cô Hana xin gửi lại nội dung buổi học ngày hôm nay của các con ạ:

1. <Môn> - <Chủ đề>
- Kiến thức: <...>
- Bài tập về nhà: <...>
- Hạn nộp/Lưu ý: <...>

2. <Môn> - <Chủ đề>
- Kiến thức: <...>
- Bài tập về nhà: <...>
- Hạn nộp/Lưu ý: <...>

Kính mong bố mẹ hỗ trợ nhắc nhở các con hoàn thành bài tập đầy đủ giúp cô ạ.
Cảm ơn bố mẹ các con đã đọc tin ạ!
Trân trọng,
Cô Hana

TỰ KIỂM TRA: Nếu còn xuất hiện bất kỳ ký tự bị cấm (*, _, `, #, >) hoặc có định dạng khác mẫu,
hãy tự viết lại cho đúng rồi mới gửi."""

        prompt = f"[SUMMARIZE]\n{instruction}"

        try:
            result = await agent.run(prompt)
            raw = str(result.output).strip()

            # Strip confidence tags if present
            for tag in ("[CONFIDENT]", "[ESCALATE]"):
                if raw.startswith(tag):
                    raw = raw[len(tag):].strip()

            logger.info(
                f"[CHAT] Daily summary generated ({channel}): {len(raw)} chars"
            )
            return raw

        except Exception as e:
            logger.error(f"[CHAT] Error generating daily summary: {e}")
            return (
                "Xin lỗi, hệ thống AI đang gặp sự cố khi tạo tóm tắt. "
                "Vui lòng thử lại sau ạ."
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
