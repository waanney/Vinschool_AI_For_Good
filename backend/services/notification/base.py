"""
Base notifier interface.

This module defines the abstract base class for all notification channels.
Each channel (email, Google Chat, etc.) must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Optional

from .models import Notification, NotificationResult


class BaseNotifier(ABC):
    """
    Abstract base class for notification channels.

    All notification channel implementations must inherit from this class
    and implement the send() method.
    """

    def __init__(self, enabled: bool = True):
        """
        Initialize the notifier.

        Args:
            enabled: Whether this notification channel is enabled.
        """
        self._enabled = enabled

    @property
    def enabled(self) -> bool:
        """Check if this notifier is enabled."""
        return self._enabled

    @property
    @abstractmethod
    def channel_name(self) -> str:
        """Return the name of this notification channel."""
        pass

    @abstractmethod
    async def send(self, notification: Notification) -> NotificationResult:
        """
        Send a notification through this channel.

        Args:
            notification: The notification to send.

        Returns:
            NotificationResult with success status and any error details.
        """
        pass

    @abstractmethod
    async def validate_config(self) -> tuple[bool, Optional[str]]:
        """
        Validate that the notifier is properly configured.

        Returns:
            Tuple of (is_valid, error_message). If valid, error_message is None.
        """
        pass

    def format_message(self, notification: Notification) -> str:
        """
        Format the notification message for this channel.

        Override in subclasses for channel-specific formatting.

        Args:
            notification: The notification to format.

        Returns:
            Formatted message string.
        """
        return notification.message

    async def send_if_enabled(self, notification: Notification) -> Optional[NotificationResult]:
        """
        Send notification only if this channel is enabled.

        Args:
            notification: The notification to send.

        Returns:
            NotificationResult if sent, None if channel is disabled.
        """
        if not self.enabled:
            return None
        return await self.send(notification)
