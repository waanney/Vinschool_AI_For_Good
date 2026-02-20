"""
Google Chat Pub/Sub listener.

Subscribes to a Google Cloud Pub/Sub topic where Google Chat publishes
events when users send messages.  Users interact with the bot by
@-mentioning it in a Google Chat space — no slash command is needed.

The bot responds as a **teacher to students** (student-facing persona),
and escalates unanswered questions to the homeroom teacher via email.

Setup required:
1. GCP project with Chat API + Pub/Sub API enabled
2. Pub/Sub topic (e.g. "chat-events") granted to chat-api-push@system.gserviceaccount.com
3. Pub/Sub subscription on that topic
4. Service account JSON key with roles: Pub/Sub Subscriber, Chat Bot
5. Chat App configured in GCP Console → Connection settings → Cloud Pub/Sub

Note: Because Google Chat uses @mention to trigger the bot, the
``argumentText`` field already contains just the user’s question
(the @mention is stripped automatically by the Chat API).

See backend/README.md for detailed setup instructions.
"""

import asyncio
import json
from typing import Optional

import httpx

from config import settings
from utils.logger import logger


class GoogleChatListener:
    """
    Listens for Google Chat messages via Pub/Sub and replies via Chat REST API.

    This is a pull-based subscriber: it periodically pulls messages from
    a Pub/Sub subscription, processes @mention messages, and replies inline.

    Messages are debounced per-user (default 3s) so rapid follow-up
    messages are concatenated into a single AI request.
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
        """Load Google service account credentials."""
        try:
            from google.oauth2 import service_account

            creds_path = settings.GOOGLE_APPLICATION_CREDENTIALS
            if not creds_path:
                logger.error("[GCHAT] GOOGLE_APPLICATION_CREDENTIALS not set")
                return None

            scopes = [
                "https://www.googleapis.com/auth/chat.bot",
                "https://www.googleapis.com/auth/pubsub",
            ]
            self._credentials = service_account.Credentials.from_service_account_file(
                creds_path, scopes=scopes
            )
            logger.info("[GCHAT] Service account credentials loaded")
            return self._credentials

        except ImportError:
            logger.error(
                "[GCHAT] google-auth not installed. "
                "Run: pip install google-auth"
            )
            return None
        except Exception as e:
            logger.error(f"[GCHAT] Failed to load credentials: {e}")
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

    async def _reply_to_chat(self, space_name: str, text: str, thread_name: Optional[str] = None) -> None:
        """
        Send a reply message via Google Chat REST API.

        Args:
            space_name: e.g. "spaces/AAAAxxxxxx"
            text: Reply text
            thread_name: Optional thread to reply in
        """
        token = self._get_access_token()
        if not token:
            logger.error("[GCHAT] Cannot reply: no access token")
            return

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
                    logger.info(f"[GCHAT] Reply sent to {space_name}")
                else:
                    logger.warning(
                        f"[GCHAT] Reply failed: {resp.status_code} {resp.text[:200]}"
                    )
            except Exception as e:
                logger.error(f"[GCHAT] Reply error: {e}")

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
            }

        except Exception as e:
            logger.warning(f"[GCHAT] Failed to parse event: {e}")
            return None

    async def _process_event(self, event: dict) -> None:
        """
        Process a parsed Google Chat event.

        Every @mention message is treated as a question for the AI.
        Messages are debounced per-user (rapid follow-ups are batched).
        """
        text = event["text"]
        user_id = event["user_id"]
        space_name = event["space_name"]
        thread_name = event["thread_name"]

        question = text.strip()
        if not question:
            await self._reply_to_chat(
                space_name,
                "Vui lòng nhập câu hỏi sau khi tag cô ạ.\n"
                "Ví dụ: @Vinschool Bot Bài tập Toán tuần này là gì?",
                thread_name,
            )
            return

        logger.info(f"[GCHAT] Question from {event['user_name']}: {question[:80]}")

        # Add to debouncer — fires after quiet period
        await self._debouncer.add(
            user_id=f"gchat-{user_id}",
            text=question,
            space_name=space_name,
            thread_name=thread_name,
            user_name=event["user_name"],
        )

    async def _on_debounced(
        self, user_id: str, combined_text: str, **metadata
    ) -> None:
        """
        Callback fired by the debouncer after the quiet window.

        Gets the AI answer and replies in Google Chat.
        """
        space_name = metadata.get("space_name", "")
        thread_name = metadata.get("thread_name")
        user_name = metadata.get("user_name", user_id)

        logger.info(
            f"[GCHAT] Debouncer fired for {user_name}: {combined_text[:80]}"
        )

        # Send typing indicator
        await self._reply_to_chat(
            space_name,
            "Cô Hana đang tra cứu thông tin...",
            thread_name,
        )

        # Get AI answer (student-facing channel)
        answer = await self.chat_service.answer(
            user_id=user_id,
            question=combined_text,
            channel="gchat",
            user_name=user_name,
        )

        # Send answer
        await self._reply_to_chat(space_name, answer, thread_name)

    async def _poll_loop(self) -> None:
        """Main polling loop — runs as a background task."""
        logger.info(
            f"[GCHAT] Pub/Sub listener started. "
            f"Subscription: {self._subscription}"
        )

        while self._running:
            try:
                messages = await self._pull_messages()
                ack_ids = []

                for msg in messages:
                    ack_id = msg.get("ackId")
                    if ack_id:
                        ack_ids.append(ack_id)

                    event = self._parse_chat_event(msg)
                    if event:
                        await self._process_event(event)

                # Acknowledge all processed messages
                await self._ack_messages(ack_ids)

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
