"""Trigger detection engine for message filtering.

Determines if a message should generate an alert based on trigger conditions.
"""

import logging
from typing import Tuple, Optional
from telethon.tl.types import User

logger = logging.getLogger(__name__)


class TriggerEngine:
    """Evaluates messages against trigger conditions."""

    def __init__(self, user_id: int, username: Optional[str] = None, bot_chat_id: Optional[int] = None):
        """Initialize trigger engine.

        Args:
            user_id: The authenticated user's ID
            username: The authenticated user's username (if any)
            bot_chat_id: The bot's chat ID to exclude from alerts
        """
        self.user_id = user_id
        self.username = username
        self.bot_chat_id = bot_chat_id

    async def should_alert(self, event) -> Tuple[bool, Optional[str]]:
        """Determine if a message should trigger an alert.

        Args:
            event: Telethon NewMessage event

        Returns:
            Tuple of (should_alert: bool, trigger_type: str or None)
            trigger_type can be "DM", "Mention", or "Reply"
        """
        message = event.message

        # Exclusion: service messages (e.g., user joined, chat created, etc.)
        if getattr(message, 'action', None) is not None:
            return False, None

        # Exclusion: messages from self
        if message.sender_id == self.user_id:
            return False, None

        # Exclusion: messages from bots (prevent infinite loop with notification bot)
        sender = await event.get_sender()
        if sender and getattr(sender, 'bot', False):
            return False, None

        # Get chat to check type
        chat = await event.get_chat()

        # Trigger A: Direct Message (only true 1-on-1 chats with a User)
        if isinstance(chat, User):
            return True, "DM"

        # Trigger B: Mention
        if self._is_mentioned(message):
            return True, "Mention"

        # Trigger C: Reply to user's message
        if await self._is_reply_to_user(event):
            return True, "Reply"

        return False, None

    def _is_mentioned(self, message) -> bool:
        """Check if the user is mentioned in the message.

        Args:
            message: Telethon Message object

        Returns:
            True if user is mentioned
        """
        # Check for text mention (@username)
        if message.text and self.username:
            if f"@{self.username}" in message.text:
                return True

        # Check for mention entities
        if message.entities:
            for entity in message.entities:
                # MessageEntityMention or MessageEntityMentionName
                if hasattr(entity, 'user_id') and entity.user_id == self.user_id:
                    return True

        return False

    async def _is_reply_to_user(self, event) -> bool:
        """Check if the message is a reply to the user's message.

        Args:
            event: Telethon NewMessage event

        Returns:
            True if message is a reply to user's own message
        """
        message = event.message

        if not message.is_reply:
            return False

        try:
            # Get the replied-to message
            replied_msg = await message.get_reply_message()
            if replied_msg and replied_msg.sender_id == self.user_id:
                return True
        except Exception as e:
            logger.warning(f"Failed to fetch replied message: {e}")

        return False
