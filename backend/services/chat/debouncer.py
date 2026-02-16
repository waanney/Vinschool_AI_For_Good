"""
Per-user message debouncer.

Batches rapid consecutive messages from the same user into a single
AI request. When a user sends multiple messages within a quiet window
(default 3 seconds), they are concatenated and processed as one.

Example:
    T+0s: "xin chào"         → buffer = ["xin chào"], timer starts
    T+1s: "cho con hỏi"      → buffer = ["xin chào", "cho con hỏi"], timer resets
    T+2s: "bài phân số"      → buffer = [..., "bài phân số"], timer resets
    T+5s: timer fires        → AI receives: "xin chào\ncho con hỏi\nbài phân số"
                               = single API call, single response
"""

import asyncio
from typing import Callable, Awaitable
from utils.logger import logger


class MessageDebouncer:
    """
    Debounces messages per user.

    Usage:
        debouncer = MessageDebouncer(quiet_period=3.0, on_fire=my_callback)
        await debouncer.add("user-123", "xin chào")
        await debouncer.add("user-123", "cho con hỏi")  # resets timer
        # 3 seconds of silence → on_fire("user-123", "xin chào\\ncho con hỏi")
    """

    def __init__(
        self,
        quiet_period: float = 3.0,
        on_fire: Callable[[str, str], Awaitable[None]] | None = None,
    ):
        """
        Args:
            quiet_period: Seconds of silence before firing (default 3s)
            on_fire: Async callback(user_id, combined_text) called when timer fires
        """
        self.quiet_period = quiet_period
        self.on_fire = on_fire

        # Per-user state
        self._buffers: dict[str, list[str]] = {}
        self._timers: dict[str, asyncio.Task] = {}
        self._metadata: dict[str, dict] = {}  # Extra data passed through

    async def add(self, user_id: str, text: str, **metadata) -> None:
        """
        Add a message to the user's buffer and (re)start the quiet timer.

        Args:
            user_id: Unique identifier for the user
            text: Message text to buffer
            **metadata: Extra data (platform, space_id, etc.) passed to callback
        """
        # Append to buffer
        if user_id not in self._buffers:
            self._buffers[user_id] = []
        self._buffers[user_id].append(text)

        # Store latest metadata (overwrite with newest)
        self._metadata[user_id] = metadata

        # Cancel existing timer
        if user_id in self._timers:
            self._timers[user_id].cancel()

        # Start new timer
        self._timers[user_id] = asyncio.create_task(
            self._wait_and_fire(user_id)
        )

        buffer_size = len(self._buffers[user_id])
        logger.debug(
            f"[DEBOUNCE] {user_id}: buffered message #{buffer_size}, "
            f"timer reset to {self.quiet_period}s"
        )

    async def _wait_and_fire(self, user_id: str) -> None:
        """Wait for quiet period then fire the combined message."""
        try:
            await asyncio.sleep(self.quiet_period)

            # Collect buffered messages
            messages = self._buffers.pop(user_id, [])
            metadata = self._metadata.pop(user_id, {})
            self._timers.pop(user_id, None)

            if not messages:
                return

            combined = "\n".join(messages)
            logger.info(
                f"[DEBOUNCE] {user_id}: firing {len(messages)} message(s) "
                f"({len(combined)} chars)"
            )

            if self.on_fire:
                await self.on_fire(user_id, combined, **metadata)

        except asyncio.CancelledError:
            # Timer was reset by a new message — expected behavior
            pass
        except Exception as e:
            logger.error(f"[DEBOUNCE] Error in fire callback for {user_id}: {e}")

    async def flush(self, user_id: str) -> None:
        """Force-fire a user's buffer immediately (useful for testing)."""
        if user_id in self._timers:
            self._timers[user_id].cancel()
        messages = self._buffers.pop(user_id, [])
        metadata = self._metadata.pop(user_id, {})
        self._timers.pop(user_id, None)

        if messages and self.on_fire:
            combined = "\n".join(messages)
            await self.on_fire(user_id, combined, **metadata)

    def pending_count(self) -> int:
        """Number of users with buffered messages."""
        return len(self._buffers)
