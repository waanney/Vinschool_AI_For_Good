"""
Google Chat Pub/Sub listener.

Subscribes to a Google Cloud Pub/Sub topic where Google Chat publishes
events when users @-mention the bot in a space.  The bot recognises
four slash commands embedded in the message text:

- ``/ask <question>`` — AI Q&A (student-facing persona, debounced)
- ``/grade``          — Grade submitted homework images via AI; results are
                        stored in Milvus so students can later ``/ask`` about
                        their scores
- ``/hw [môn]``       — Suggest supplementary homework based on the student's
                        Milvus profile and recent grades
- ``/dailysum``       — Hardcoded daily lesson summary

Certain demo phrases are recognised for hardcoded responses:
- ``/ask Cô ơi ngày mai có bài tập nào...`` → hardcoded
- ``/ask Cô ơi con chưa hiểu tại sao thả...`` → hardcoded
- ``/ask Cô ơi mai khai mạc Edurun...`` → hardcoded escalation + email
- ``/ask Cô ơi cho con bài tập để luyện...`` → hardcoded
- ``/grade Cô ơi chấm bài cộng trừ...`` → real grading flow with hardcoded result

Any other message is silently ignored so the bot does not respond to
every conversation in the shared space.

The bot responds as a **teacher to students** (student-facing persona),
and escalates unanswered questions to the homeroom teacher via email.

Setup required:
1. GCP project with Chat API + Pub/Sub API enabled
2. Pub/Sub topic (e.g. "chat-events") granted to chat-api-push@system.gserviceaccount.com
3. Pub/Sub subscription on that topic
4. Service account JSON key with roles: Pub/Sub Subscriber, Chat Bot
5. Chat App configured in GCP Console → Connection settings → Cloud Pub/Sub


See backend/README.md for detailed setup instructions.
"""

import asyncio
import json
import os
import shutil
import tempfile
from typing import Optional
from uuid import uuid4, UUID

import httpx

from config import settings
from utils.logger import logger


# ===== Demo / hardcoded response delay (seconds) =====
HARDCODED_RESPONSE_DELAY = settings.CHAT_DEBOUNCE_SECONDS

# ===== Demo phrase detection =====
# Prefixes used to match demo phrases (case-insensitive, stripped).
# Each entry: (prefix, response, escalate?)

DEMO_ASK_PHRASES = [
    {
        "prefix": "cô ơi ngày mai có bài tập nào",
        "response": """Chào con,
Ngày mai (Thứ 2) là hạn nộp bài tập ESL Unit 7, pages 84-89 trong sách Workbook con nhé.
Con nhớ hoàn thành và nộp bài đúng hạn nha!""",
        "escalate": False,
    },
    {
        "prefix": "cô ơi con chưa hiểu tại sao thả",
        "response": """Chào con, đây là một câu hỏi rất hay và thú vị đó!

Trong bài học con đã được học, khi dù rơi xuống, có hai lực chính tác dụng:
 - Trọng lực (gravity) kéo dù xuống.
 - Lực cản không khí (air resistance) đẩy lên trên.
 Dù lớn có diện tích bề mặt lớn hơn nên chặn nhiều không khí hơn khi rơi. Vì vậy lực cản không khí mạnh hơn.
Lực cản lớn hơn làm giảm tốc độ rơi. Không khí “đẩy ngược lại” mạnh hơn → dù rơi chậm hơn.
Như vậy, chiếc dù lớn rơi chậm hơn vì diện tích lớn tạo ra lực cản không khí (air resistance) tác dụng lên nó lớn hơn.

Nếu con còn gì không hiểu, con cứ hỏi cô nhé.""",
        "escalate": False,
    },
    {
        "prefix": "cô ơi mai khai mạc edurun",
        "response": """Cô Hana chưa có thông tin về vấn đề này. Cô đã chuyển câu hỏi đến giáo viên chủ nhiệm, thầy/cô sẽ phản hồi sớm nhất nhé con!""",
        "escalate": True,
    },
    {
        "prefix": "cô ơi cho con bài tập để luyện",
        "response": """Cô rất vui khi con muốn luyện tập thêm để nắm vững kiến thức này. Tinh thần học tập của con rất đáng khen!
Dưới đây là link bài tập thêm để con luyện tập nhé:

https://docs.google.com/document/d/1MI92CYi-ROlN50Qx1-xqLrkiWbpqtQ8e/edit

Con hãy nhớ lại bài học nhé, bước quan trọng nhất là phải **quy đồng mẫu số** trước khi cộng hoặc trừ.

Sau khi làm xong, nếu con muốn, con có thể gửi bài cho cô xem. Chúc con làm bài thật tốt nhé!""",
        "escalate": False,
    },
]

DEMO_GRADE_PREFIX = "cô ơi chấm bài cộng trừ"
DEMO_GRADE_SCORE = 8.5
DEMO_GRADE_FEEDBACK = "Nhìn chung con đã làm khá tốt bài tập này. Con hiểu được hầu hết các dạng bài và làm đúng nhiều câu. Tuy nhiên, vẫn còn một vài lỗi nhỏ liên quan đến cộng trừ phân số có mẫu số khác nhau và quy đồng mẫu số."
DEMO_GRADE_DETAILED = """Kết quả chấm bài:
1. Fraction Calculations
c) 2/8 + 1/4 = 3/8 ❌
1/4 = 2/8
2/8 + 2/8 = 4/8 = 1/2

d) 3/4 - 1/4 = 1/3 ❌
Đúng phải là: 2/4 = 1/2

2. Pizza Word Problems
D: 1/2 pizza =
8 x 1/2 = 4 slices
Con ghi 3 slices ❌

Ngoài những lỗi nhỏ trên, các phần còn lại con làm rất tốt, đặc biệt là các bài toán tình huống và ước lượng phân số.

Cô mong con sẽ luyện thêm các bài cộng trừ phân số khác mẫu số để tránh nhầm lẫn khi quy đồng.

Con có muốn làm thêm một vài bài tập luyện tập về cộng trừ phân số với mẫu số khác nhau không?"""


def _match_demo_ask(question: str) -> Optional[dict]:
    """Return the matching demo phrase dict, or None."""
    q = question.lower().strip()
    for phrase in DEMO_ASK_PHRASES:
        if q.startswith(phrase["prefix"]):
            return phrase
    return None


def _is_demo_grade(text_after_grade: str) -> bool:
    """Check if the /grade command text matches the demo grade phrase."""
    return text_after_grade.lower().strip().startswith(DEMO_GRADE_PREFIX)


class GoogleChatListener:
    """
    Listens for Google Chat messages via Pub/Sub and replies via Chat REST API.

    This is a pull-based subscriber: it periodically pulls messages from
    a Pub/Sub subscription, processes slash commands (/ask, /grade,
    /hw, /dailysum), and replies inline.  All other messages are
    silently ignored.

    Messages sent via /ask are debounced per-user (default 3s) so rapid
    follow-up messages are concatenated into a single AI request.
    """

    def __init__(self, chat_service=None, debouncer=None):
        """
        Args:
            chat_service: ChatService instance for handling questions.
                          If None, imports get_chat_service() lazily.
            debouncer: MessageDebouncer for batching rapid messages.
                       If None, one is created with settings.CHAT_DEBOUNCE_SECONDS.
        """
        self._chat_service = chat_service
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._credentials = None
        self._project_id = settings.GOOGLE_CLOUD_PROJECT_ID
        self._subscription = settings.GOOGLE_CHAT_PUBSUB_SUBSCRIPTION

        # Debouncer — batches rapid messages from the same user
        from services.chat.debouncer import MessageDebouncer

        quiet = getattr(settings, "CHAT_DEBOUNCE_SECONDS", 3.0) or 3.0
        self._debouncer = debouncer or MessageDebouncer(
            quiet_period=float(quiet),
            on_fire=self._on_debounced,
        )

    @property
    def chat_service(self):
        if self._chat_service is None:
            from services.chat.chat_service import get_chat_service
            self._chat_service = get_chat_service()
        return self._chat_service

    def _load_credentials(self):
        """Load Google service account credentials from GOOGLE_CREDENTIALS_JSON."""
        try:
            from google.oauth2 import service_account

            json_content = settings.GOOGLE_CREDENTIALS_JSON
            scopes = [
                "https://www.googleapis.com/auth/chat.bot",
                "https://www.googleapis.com/auth/pubsub",
            ]

            if not json_content:
                logger.warning("[GCHAT] GOOGLE_CREDENTIALS_JSON not configured")
                return None

            try:
                info = json.loads(json_content)
                self._credentials = service_account.Credentials.from_service_account_info(
                    info, scopes=scopes
                )
                logger.info("[GCHAT] Credentials loaded from GOOGLE_CREDENTIALS_JSON")
                return self._credentials
            except Exception as e:
                logger.error(f"[GCHAT] Failed to load credentials from JSON string: {e}")
                return None

        except ImportError:
            logger.error("[GCHAT] google-auth not installed")
            return None
        except Exception as e:
            logger.error(f"[GCHAT] Unexpected error loading credentials: {e}")
            return None

    def _get_access_token(self) -> Optional[str]:
        """Get a valid access token, refreshing if needed."""
        if not self._credentials:
            if not self._load_credentials():
                return None

        from google.auth.transport.requests import Request

        if self._credentials.expired or not self._credentials.token:
            self._credentials.refresh(Request())

        return self._credentials.token

    async def _pull_messages(self) -> list[dict]:
        """
        Pull messages from Pub/Sub subscription.

        Returns list of received Pub/Sub messages.
        """
        token = self._get_access_token()
        if not token:
            return []

        url = (
            f"https://pubsub.googleapis.com/v1/"
            f"{self._subscription}:pull"
        )

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                    json={"maxMessages": 10},
                    timeout=30,
                )
                if resp.status_code != 200:
                    if resp.status_code != 404:  # 404 = no messages
                        logger.warning(
                            f"[GCHAT] Pub/Sub pull failed: {resp.status_code} {resp.text[:200]}"
                        )
                    return []

                data = resp.json()
                return data.get("receivedMessages", [])

            except httpx.TimeoutException:
                return []  # Normal — no messages available
            except Exception as e:
                logger.error(f"[GCHAT] Pub/Sub pull error: {e}")
                return []

    async def _ack_messages(self, ack_ids: list[str]) -> None:
        """Acknowledge processed messages so they aren't re-delivered."""
        if not ack_ids:
            return

        token = self._get_access_token()
        if not token:
            return

        url = (
            f"https://pubsub.googleapis.com/v1/"
            f"{self._subscription}:acknowledge"
        )

        async with httpx.AsyncClient() as client:
            try:
                await client.post(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                    json={"ackIds": ack_ids},
                    timeout=10,
                )
            except Exception as e:
                logger.warning(f"[GCHAT] Failed to ack messages: {e}")

    async def _reply_to_chat(
        self,
        space_name: str,
        text: str,
        thread_name: Optional[str] = None,
    ) -> Optional[str]:
        """
        Send a reply message via Google Chat REST API.

        Args:
            space_name: e.g. "spaces/AAAAxxxxxx"
            text: Reply text
            thread_name: Optional thread to reply in

        Returns:
            The message resource name (e.g. "spaces/xxx/messages/yyy"),
            or None on failure.
        """
        token = self._get_access_token()
        if not token:
            logger.error("[GCHAT] Cannot reply: no access token")
            return None

        url = f"https://chat.googleapis.com/v1/{space_name}/messages"

        body: dict = {"text": text}
        if thread_name:
            body["thread"] = {"name": thread_name}

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                    json=body,
                    timeout=15,
                )
                if resp.status_code in (200, 201):
                    msg_name = resp.json().get("name")
                    logger.info(f"[GCHAT] Reply sent to {space_name} ({msg_name})")
                    return msg_name
                else:
                    logger.warning(
                        f"[GCHAT] Reply failed: {resp.status_code} {resp.text[:200]}"
                    )
            except Exception as e:
                logger.error(f"[GCHAT] Reply error: {e}")
        return None

    async def _delete_message(self, message_name: str) -> None:
        """
        Delete a Google Chat message by its resource name.

        Retained for future use (e.g. removing outdated bot messages);
        not called in the normal single-message command flow.

        Args:
            message_name: Resource name returned by _reply_to_chat,
                          e.g. "spaces/xxx/messages/yyy"
        """
        token = self._get_access_token()
        if not token:
            return

        url = f"https://chat.googleapis.com/v1/{message_name}"
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.delete(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10,
                )
                if resp.status_code in (200, 204):
                    logger.debug(f"[GCHAT] Message deleted: {message_name}")
                else:
                    logger.warning(
                        f"[GCHAT] Delete failed: {resp.status_code} {resp.text[:100]}"
                    )
            except Exception as e:
                logger.warning(f"[GCHAT] Delete error: {e}")

    def _parse_chat_event(self, pubsub_message: dict) -> Optional[dict]:
        """
        Parse a Pub/Sub message into a Google Chat event.

        Returns dict with keys: type, text, user_id, user_name, space_name, thread_name
        or None if not a processable message.
        """
        try:
            import base64

            raw_data = pubsub_message.get("message", {}).get("data", "")
            if not raw_data:
                return None

            decoded = base64.b64decode(raw_data).decode("utf-8")
            event = json.loads(decoded)

            event_type = event.get("type", "")
            if event_type != "MESSAGE":
                logger.debug(f"[GCHAT] Ignoring event type: {event_type}")
                return None

            message = event.get("message", {})
            text = message.get("argumentText") or message.get("text", "")
            space = event.get("space", {})
            user = event.get("user", {})
            thread = message.get("thread", {})

            return {
                "type": event_type,
                "text": text.strip(),
                "user_id": user.get("name", "unknown"),
                "user_name": user.get("displayName", "Unknown User"),
                "space_name": space.get("name", ""),
                "thread_name": thread.get("name"),
                "attachments": message.get("attachment", []),
            }

        except Exception as e:
            logger.warning(f"[GCHAT] Failed to parse event: {e}")
            return None

    async def _handle_dailysum(self, event: dict) -> None:
        """
        Handle the /dailysum command: post the hardcoded daily
        lesson summary to the current Google Chat space.
        """
        from services.scheduler import DEMO_LESSON_CONTENT_STUDENTS

        space_name = event["space_name"]
        thread_name = event["thread_name"]

        await asyncio.sleep(HARDCODED_RESPONSE_DELAY)
        await self._reply_to_chat(space_name, DEMO_LESSON_CONTENT_STUDENTS, thread_name)

    async def _process_event(self, event: dict) -> None:
        """
        Process a parsed Google Chat event.

        Responds to four commands:
        - /ask <question>  — AI Q&A (debounced, student persona);
                             certain demo phrases return hardcoded responses
        - /grade           — Grade submitted homework images;
                             demo phrase "Cô ơi chấm bài cộng trừ..." uses
                             real grading flow with hardcoded result
        - /hw [môn]        — Suggest supplementary homework
        - /dailysum        — Hardcoded daily lesson summary

        All other messages are silently ignored so the bot doesn't respond
        to every conversation in the shared space.
        """
        text = event["text"].strip()
        user_id = event["user_id"]
        space_name = event["space_name"]
        thread_name = event["thread_name"]

        if not text:
            return

        # /help — show available commands
        if text.lower().startswith("/help"):
            help_text = (
                "📋 Danh sách lệnh Google Chat:\n\n"
                "/ask <câu hỏi> — Hỏi đáp AI (Cô Hana sẽ trả lời)\n"
                "/grade — Chấm bài tập (đính kèm ảnh bài làm)\n"
                "/hw [môn] — Gợi ý bài tập bổ sung (dựa trên hồ sơ học sinh)\n"
                "/dailysum — Tóm tắt bài học hôm nay\n"
                "/help — Hiển thị danh sách lệnh này"
            )
            await self._reply_to_chat(space_name, help_text, thread_name)
            return

        # /dailysum — hardcoded daily summary
        if text.lower().startswith("/dailysum"):
            logger.info(f"[GCHAT] /dailysum from {event['user_name']}")
            await self._handle_dailysum(event)
            return

        # /grade — grade submitted homework images
        if text.lower().startswith("/grade"):
            logger.info(f"[GCHAT] /grade from {event['user_name']}")
            await self._handle_grade(event)
            return

        # /hw [subject] — supplementary homework suggestions
        if text.lower().startswith("/hw"):
            logger.info(f"[GCHAT] /hw from {event['user_name']}")
            await self._handle_hw(event)
            return

        # /ask <question> — AI Q&A
        if text.lower().startswith("/ask"):
            question = text[4:].strip()
            if not question:
                await self._reply_to_chat(
                    space_name,
                    "Vui lòng nhập câu hỏi sau /ask ạ.\n"
                    "Ví dụ: @Vinschool Bot /ask Bài tập Toán tuần này là gì?",
                    thread_name,
                )
                return

            logger.info(f"[GCHAT] /ask from {event['user_name']}: {question[:80]}")

            # Check for demo phrases first
            demo = _match_demo_ask(question)
            if demo:
                logger.info(f"[GCHAT] Demo phrase matched: {demo['prefix']}")
                await asyncio.sleep(HARDCODED_RESPONSE_DELAY)
                await self._reply_to_chat(space_name, demo["response"], thread_name)
                if demo["escalate"]:
                    from services.chat.chat_service import _send_escalation_email
                    asyncio.create_task(
                        _send_escalation_email(
                            f"gchat-{user_id}",
                            event["user_name"],
                            question,
                        )
                    )
                return

            # Add to debouncer — fires after quiet period
            await self._debouncer.add(
                user_id=f"gchat-{user_id}",
                text=question,
                space_name=space_name,
                thread_name=thread_name,
                user_name=event["user_name"],
            )
            return

        # Any other message — silently ignore (bot shares space with everyone)
        logger.debug(f"[GCHAT] Ignoring non-command message from {event['user_name']}: {text[:40]}")

    async def _handle_grade(self, event: dict) -> None:
        """
        Handle the /grade command: grade student-submitted images.

        Flow:
        1. Parse text after ``/grade`` — detect demo phrase
        2. Validate attachments are present
        3. Download attachment images to temp files
        4. Grade using HomeworkGradingWorkflow (or hardcoded for demo)
        5. Store submission in submission_store
        6. Reply with feedback in Google Chat
        7. Send notification to teacher (low-grade alert if applicable)
        """
        space_name = event["space_name"]
        thread_name = event["thread_name"]
        user_id = event["user_id"]
        user_name = event["user_name"]
        attachments = event.get("attachments", [])
        text = event["text"].strip()

        # Detect demo grade phrase
        text_after_grade = text[6:].strip()  # strip "/grade"
        is_demo = _is_demo_grade(text_after_grade)

        # Validate attachments — both demo and real require images
        if not attachments:
            await self._reply_to_chat(
                space_name,
                "Vui lòng đính kèm hình ảnh bài tập ạ.",
                thread_name,
            )
            return

        # Send processing indicator
        await self._reply_to_chat(
            space_name,
            f"Cô Hana đang chấm bài của {user_name}... "
            f"({len(attachments)} ảnh)",
            thread_name,
        )

        # Download attachments to temp directory
        downloaded_paths = []
        temp_dir = tempfile.mkdtemp(prefix="vinschool_grade_")

        try:
            for i, attachment in enumerate(attachments):
                path = await self._download_attachment(
                    attachment, temp_dir, index=i
                )
                if path:
                    downloaded_paths.append(path)

            if not downloaded_paths:
                await self._reply_to_chat(
                    space_name,
                    "Xin lỗi, cô không tải được ảnh bài tập. "
                    "Vui lòng thử lại ạ.",
                    thread_name,
                )
                return

            # Create assignment entity for grading
            from domain.models.assignment import Assignment

            assignment = Assignment(
                title="Google Chat Submission",
                teacher_id=UUID("00000000-0000-4000-8000-000000000001"),
                student_id=UUID("00000000-0000-4000-8000-000000000002"),
                class_name="4B5",
                subject="Mathematics",
                max_score=10.0,
            )
            assignment.submit(
                file_path=downloaded_paths[0],
            )

            if is_demo:
                # Demo grade: skip AI, use hardcoded score/feedback
                await asyncio.sleep(HARDCODED_RESPONSE_DELAY)
                score = DEMO_GRADE_SCORE
                feedback = DEMO_GRADE_FEEDBACK
                detailed_feedback = DEMO_GRADE_DETAILED
                details = {}
            else:
                # Real grade: call AI via workflow
                from workflow.homework_grading_workflow import (
                    HomeworkGradingWorkflow,
                )

                workflow = HomeworkGradingWorkflow()
                rubric = workflow.create_standard_rubric(
                    "Mathematics", "homework"
                )

                grading_result = await workflow.grade_homework(
                    assignment=assignment,
                    rubric=rubric,
                    submission_file_path=downloaded_paths[0],
                    notify_teacher=True,
                    teacher_email=settings.TEACHER_EMAIL,
                    student_name=user_name,
                )

                score = grading_result.get("score", 0.0)
                feedback = grading_result.get("feedback", "")
                detailed_feedback = grading_result.get("detailed_feedback", "")
                details = grading_result.get("details", {})
                grading_error = grading_result.get("error", None)

                # Sanitize feedback — if it contains raw error text
                # (e.g. tesseract not found), replace with a clean message
                has_error = (
                    grading_error
                    or "error" in feedback.lower()
                    or "tesseract" in feedback.lower()
                    or "not installed" in feedback.lower()
                )
                if has_error and score == 0.0:
                    feedback = (
                        "Cô Hana chưa thể đọc rõ bài tập trong ảnh.\n"
                        "Vui lòng chụp lại rõ hơn và gửi lại ạ."
                    )
                    detailed_feedback = ""
                    details = {}  # Clear error details

            # Store in submission store for LMS dashboard
            from services.chat.submission_store import add_submission

            submission = add_submission(
                student_id=user_id,
                student_name=user_name,
                score=score,
                max_score=assignment.max_score,
                feedback=feedback,
                detailed_feedback=detailed_feedback,
                attachment_paths=self._persist_images(
                    downloaded_paths
                ),
                subject=assignment.subject,
                assignment_title=assignment.title,
                details=details,
            )

            # Store grading result in Milvus so /ask can retrieve it
            try:
                from database.repositories.grading_repository import (
                    store_grading_result,
                )
                await store_grading_result(
                    student_id=f"gchat-{user_id}",
                    student_name=user_name,
                    subject=assignment.subject,
                    assignment_title=assignment.title,
                    score=score,
                    max_score=assignment.max_score,
                    feedback=feedback,
                    detailed_feedback=detailed_feedback,
                    graded_at=submission["graded_at"],
                )
            except Exception as milvus_err:
                logger.warning(
                    f"[GCHAT] Non-critical: failed to store grading "
                    f"in Milvus: {milvus_err}"
                )

            # Build reply message
            reply_parts = [
                f"Kết quả chấm bài của {user_name}:",
                f"Điểm: {score:.1f}/{assignment.max_score:.1f}",
            ]
            if feedback:
                reply_parts.append(f"\nNhận xét:\n{feedback}")
            if detailed_feedback:
                reply_parts.append(f"\nChi tiết:\n{detailed_feedback}")

            reply_text = "\n".join(reply_parts)
            # Strip any markdown formatting characters
            reply_text = reply_text.replace("*", "").replace("#", "")
            await self._reply_to_chat(
                space_name, reply_text, thread_name
            )

            logger.info(
                f"[GCHAT] Graded submission for {user_name}: "
                f"{score}/{assignment.max_score}"
            )

        except Exception as e:
            logger.error(f"[GCHAT] Error grading submission: {e}")
            await self._reply_to_chat(
                space_name,
                "Xin lỗi, có lỗi xảy ra khi chấm bài.\n"
                "Vui lòng thử lại sau ạ.",
                thread_name,
            )

    async def _handle_hw(self, event: dict) -> None:
        """
        Handle the ``/hw`` command: suggest supplementary homework.

        Flow:
        1. Parse optional subject from ``/hw [môn]``
        2. Look up student profile from Milvus
        3. Look up recent grading results from Milvus
        4. Build context and call LLM for personalised suggestions
        5. Reply in Google Chat
        """
        space_name = event["space_name"]
        thread_name = event["thread_name"]
        user_id = event["user_id"]
        user_name = event["user_name"]

        # Parse optional subject: "/hw Toán" → subject "Toán"
        text = event["text"].strip()
        subject_hint = text[3:].strip() if len(text) > 3 else ""

        # Send processing indicator
        await self._reply_to_chat(
            space_name,
            f"Cô Hana đang chuẩn bị bài tập bổ sung cho {user_name}... ✏️",
            thread_name,
        )

        try:
            from services.chat.chat_service import (
                ChatService,
                CHANNEL_GCHAT,
            )

            service = ChatService()
            suggestions = await service.suggest_homework(
                user_id=f"gchat-{user_id}",
                user_name=user_name,
                subject_hint=subject_hint,
            )

            await self._reply_to_chat(space_name, suggestions, thread_name)
            logger.info(
                f"[GCHAT] /hw reply sent to {user_name} "
                f"({len(suggestions)} chars)"
            )

        except Exception as e:
            logger.error(f"[GCHAT] Error generating homework suggestions: {e}")
            await self._reply_to_chat(
                space_name,
                "Xin lỗi, cô Hana chưa thể tạo bài tập bổ sung lúc này.\n"
                "Vui lòng thử lại sau ạ.",
                thread_name,
            )

    @staticmethod
    def _persist_images(temp_paths: list[str]) -> list[str]:
        """Copy downloaded temp images to a persistent uploads directory.

        Returns a list of web-accessible relative paths like
        ``submissions/<uuid>_<filename>`` that can be served by the
        ``/uploads`` static-files mount.
        """
        from api.main import UPLOADS_DIR

        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        persisted: list[str] = []
        for src in temp_paths:
            filename = f"{uuid4().hex[:8]}_{os.path.basename(src)}"
            dest = UPLOADS_DIR / filename
            shutil.copy2(src, dest)
            # Relative to the /uploads mount root (uploads/)
            persisted.append(f"submissions/{filename}")
            logger.info(f"[GCHAT] Persisted image: {dest}")
        return persisted

    async def _download_attachment(
        self,
        attachment: dict,
        temp_dir: str,
        index: int = 0,
    ) -> Optional[str]:
        """
        Download a Google Chat attachment to a temporary file.

        Args:
            attachment: Attachment metadata from the Chat event.
            temp_dir: Directory to save the downloaded file.
            index: Attachment index (for naming).

        Returns:
            Path to the downloaded file, or None on failure.
        """
        try:
            # Google Chat attachments have:
            # - attachmentDataRef.resourceName for Chat API download
            # - downloadUri for direct download (if available)
            # - contentName for the filename
            # - contentType for MIME type
            content_name = attachment.get(
                "contentName", f"attachment_{index}.jpg"
            )
            download_uri = attachment.get("downloadUri")
            resource_name = (
                attachment.get("attachmentDataRef", {})
                .get("resourceName")
            )

            file_path = os.path.join(temp_dir, content_name)

            # Try direct download URI first
            if download_uri:
                token = self._get_access_token()
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        download_uri,
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=30,
                        follow_redirects=True,
                    )
                    if resp.status_code == 200:
                        with open(file_path, "wb") as f:
                            f.write(resp.content)
                        logger.info(
                            f"[GCHAT] Downloaded attachment: "
                            f"{content_name}"
                        )
                        return file_path

            # Try Chat API media download
            if resource_name:
                token = self._get_access_token()
                url = (
                    f"https://chat.googleapis.com/v1/media/"
                    f"{resource_name}?alt=media"
                )
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        url,
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=30,
                        follow_redirects=True,
                    )
                    if resp.status_code == 200:
                        with open(file_path, "wb") as f:
                            f.write(resp.content)
                        logger.info(
                            f"[GCHAT] Downloaded attachment via API: "
                            f"{content_name}"
                        )
                        return file_path

            logger.warning(
                f"[GCHAT] Could not download attachment: "
                f"{content_name}"
            )
            return None

        except Exception as e:
            logger.error(
                f"[GCHAT] Error downloading attachment: {e}"
            )
            return None

    async def _on_debounced(
        self, user_id: str, combined_text: str, **metadata
    ) -> None:
        """
        Callback fired by the debouncer after the quiet window.

        Gets the AI answer and posts it — single message, no typing indicator.
        """
        space_name = metadata.get("space_name", "")
        thread_name = metadata.get("thread_name")
        user_name = metadata.get("user_name", user_id)

        logger.info(
            f"[GCHAT] Debouncer fired for {user_name}: {combined_text[:80]}"
        )

        # Get AI answer (student-facing channel)
        answer = await self.chat_service.answer(
            user_id=user_id,
            question=combined_text,
            channel="gchat",
            user_name=user_name,
        )

        # Send the answer
        await self._reply_to_chat(space_name, answer, thread_name)

    async def _poll_loop(self) -> None:
        """Main polling loop — runs as a background task.

        Messages are acknowledged immediately after retrieval to prevent
        Pub/Sub redelivery during slow AI calls (e.g. /dailysum).
        """
        logger.info(
            f"[GCHAT] Pub/Sub listener started. "
            f"Subscription: {self._subscription}"
        )

        while self._running:
            try:
                messages = await self._pull_messages()
                ack_ids = []
                events = []

                for msg in messages:
                    ack_id = msg.get("ackId")
                    if ack_id:
                        ack_ids.append(ack_id)

                    event = self._parse_chat_event(msg)
                    if event:
                        events.append(event)

                # Acknowledge immediately so Pub/Sub won't redeliver while
                # we await potentially slow AI calls (e.g. /dailysum).
                await self._ack_messages(ack_ids)

                for event in events:
                    await self._process_event(event)

                # Small delay between polls to avoid burning CPU
                await asyncio.sleep(1)

            except asyncio.CancelledError:
                logger.info("[GCHAT] Pub/Sub listener cancelled")
                break
            except Exception as e:
                logger.error(f"[GCHAT] Poll loop error: {e}")
                await asyncio.sleep(5)  # Back off on error

        logger.info("[GCHAT] Pub/Sub listener stopped")

    def start(self) -> None:
        """Start the Pub/Sub listener as a background asyncio task."""
        if self._running:
            logger.warning("[GCHAT] Listener already running")
            return

        if not self._project_id or not self._subscription:
            logger.warning(
                "[GCHAT] Pub/Sub listener not started: "
                "GOOGLE_CLOUD_PROJECT_ID or GOOGLE_CHAT_PUBSUB_SUBSCRIPTION not configured"
            )
            return

        self._running = True
        self._task = asyncio.create_task(self._poll_loop())

    def stop(self) -> None:
        """Stop the Pub/Sub listener."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("[GCHAT] Listener stopped")


# ===== Singleton =====

_listener: Optional[GoogleChatListener] = None


def get_google_chat_listener() -> GoogleChatListener:
    """Get or create the global GoogleChatListener instance."""
    global _listener
    if _listener is None:
        _listener = GoogleChatListener()
    return _listener
