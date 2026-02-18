"""
Unit tests for the MessageDebouncer.

Tests cover:
- Single message fires after quiet period
- Multiple rapid messages are concatenated
- flush() fires immediately
- Metadata is passed through to callback
- pending_count() tracking
- Timer cancellation on new message
"""

import asyncio
import pytest
from unittest.mock import AsyncMock

from services.chat.debouncer import MessageDebouncer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_debouncer(
    quiet_period: float = 0.1,
    on_fire: AsyncMock | None = None,
) -> tuple[MessageDebouncer, AsyncMock]:
    """Create a debouncer with a short quiet period for fast tests."""
    callback = on_fire or AsyncMock()
    db = MessageDebouncer(quiet_period=quiet_period, on_fire=callback)
    return db, callback


# ---------------------------------------------------------------------------
# Basic fire behavior
# ---------------------------------------------------------------------------


class TestDebouncerFire:
    """Tests for the debouncer fire behavior."""

    @pytest.mark.asyncio
    async def test_single_message_fires(self):
        """A single message fires after the quiet period."""
        db, cb = _make_debouncer(quiet_period=0.05)
        await db.add("user-1", "hello")
        await asyncio.sleep(0.15)  # Wait for fire

        cb.assert_called_once()
        args = cb.call_args
        assert args[0][0] == "user-1"
        assert args[0][1] == "hello"

    @pytest.mark.asyncio
    async def test_multiple_messages_concatenated(self):
        """Rapid messages from the same user are concatenated."""
        db, cb = _make_debouncer(quiet_period=0.1)
        await db.add("user-1", "xin chào")
        await db.add("user-1", "cho con hỏi")
        await db.add("user-1", "bài phân số")
        await asyncio.sleep(0.25)

        cb.assert_called_once()
        combined = cb.call_args[0][1]
        assert "xin chào" in combined
        assert "cho con hỏi" in combined
        assert "bài phân số" in combined
        assert combined == "xin chào\ncho con hỏi\nbài phân số"

    @pytest.mark.asyncio
    async def test_different_users_separate(self):
        """Messages from different users fire independently."""
        db, cb = _make_debouncer(quiet_period=0.05)
        await db.add("user-A", "hello A")
        await db.add("user-B", "hello B")
        await asyncio.sleep(0.15)

        assert cb.call_count == 2
        user_ids = {call.args[0] for call in cb.call_args_list}
        assert user_ids == {"user-A", "user-B"}


# ---------------------------------------------------------------------------
# flush
# ---------------------------------------------------------------------------


class TestDebouncerFlush:
    """Tests for debouncer.flush()."""

    @pytest.mark.asyncio
    async def test_flush_fires_immediately(self):
        """flush() fires buffered messages without waiting."""
        db, cb = _make_debouncer(quiet_period=10)  # Long quiet period
        await db.add("user-1", "urgent question")
        await db.flush("user-1")

        cb.assert_called_once()
        assert cb.call_args[0][1] == "urgent question"

    @pytest.mark.asyncio
    async def test_flush_empty_user_no_fire(self):
        """flush() on a user with no buffered messages doesn't fire."""
        db, cb = _make_debouncer()
        await db.flush("nonexistent")
        cb.assert_not_called()

    @pytest.mark.asyncio
    async def test_flush_clears_buffer(self):
        """After flush(), the user's buffer is empty."""
        db, cb = _make_debouncer(quiet_period=10)
        await db.add("user-1", "msg")
        await db.flush("user-1")

        assert db.pending_count() == 0


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TestDebouncerMetadata:
    """Tests for metadata pass-through."""

    @pytest.mark.asyncio
    async def test_metadata_passed_to_callback(self):
        """Extra kwargs are passed through to the on_fire callback."""
        db, cb = _make_debouncer(quiet_period=0.05)
        await db.add("user-1", "hello", space_name="spaces/abc", thread_name="threads/1")
        await asyncio.sleep(0.15)

        cb.assert_called_once()
        kwargs = cb.call_args[1]
        assert kwargs["space_name"] == "spaces/abc"
        assert kwargs["thread_name"] == "threads/1"


# ---------------------------------------------------------------------------
# pending_count
# ---------------------------------------------------------------------------


class TestDebouncerPendingCount:
    """Tests for pending_count()."""

    @pytest.mark.asyncio
    async def test_pending_count_increases(self):
        """pending_count reflects the number of users with buffered messages."""
        db, _ = _make_debouncer(quiet_period=10)
        assert db.pending_count() == 0

        await db.add("user-1", "a")
        assert db.pending_count() == 1

        await db.add("user-2", "b")
        assert db.pending_count() == 2

    @pytest.mark.asyncio
    async def test_pending_count_decreases_after_fire(self):
        """pending_count decreases after messages fire."""
        db, _ = _make_debouncer(quiet_period=0.05)
        await db.add("user-1", "a")
        assert db.pending_count() == 1

        await asyncio.sleep(0.15)
        assert db.pending_count() == 0
