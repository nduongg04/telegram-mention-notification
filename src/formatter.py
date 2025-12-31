"""Alert message formatter.

Formats notification messages with metadata and deep links.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AlertFormatter:
    """Formats alert messages for delivery."""

    # Emoji mapping for trigger types
    EMOJI = {
        "DM": "🔔",
        "Mention": "📢",
        "Reply": "💬"
    }

    async def format_alert(self, event, trigger_type: str) -> str:
        """Format an alert message.

        Args:
            event: Telethon NewMessage event
            trigger_type: Type of trigger ("DM", "Mention", or "Reply")

        Returns:
            Formatted alert message string
        """
        message = event.message

        # Get emoji for trigger type
        emoji = self.EMOJI.get(trigger_type, "🔔")

        # Get chat info - fetch if needed
        chat = await event.get_chat()
        chat_name = self._get_chat_name(chat)

        # Get sender info - fetch if needed
        sender = await event.get_sender()
        sender_name = self._get_sender_name(sender)
        sender_username = self._get_sender_username(sender)

        # Get timestamp
        timestamp = message.date.strftime("%Y-%m-%d %H:%M:%S")

        # Generate deep link
        deep_link = self._generate_deep_link(chat, message)

        # Get message preview
        preview = self._get_message_preview(message)

        # Build alert message (using HTML for bot API)
        alert = f"""{emoji} <b>[{trigger_type}]</b>
<b>Chat:</b> {self._escape_html(chat_name)}
<b>From:</b> {self._escape_html(sender_name)}{sender_username}
<b>Time:</b> {timestamp}
<b>Link:</b> {deep_link}

<b>Preview:</b>
{self._escape_html(preview)}"""

        return alert

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _get_chat_name(self, chat) -> str:
        """Get chat display name."""
        if not chat:
            return "Unknown Chat"

        if hasattr(chat, 'title') and chat.title:
            return chat.title
        elif hasattr(chat, 'first_name') and chat.first_name:
            name = chat.first_name
            if hasattr(chat, 'last_name') and chat.last_name:
                name += f" {chat.last_name}"
            return name
        elif hasattr(chat, 'username') and chat.username:
            return f"@{chat.username}"

        return "Unknown Chat"

    def _get_sender_name(self, sender) -> str:
        """Get sender display name."""
        if not sender:
            return "Unknown"

        if hasattr(sender, 'first_name') and sender.first_name:
            name = sender.first_name
            if hasattr(sender, 'last_name') and sender.last_name:
                name += f" {sender.last_name}"
            return name.strip()

        if hasattr(sender, 'title') and sender.title:
            return sender.title

        return "Unknown"

    def _get_sender_username(self, sender) -> str:
        """Get sender username if available."""
        if sender and hasattr(sender, 'username') and sender.username:
            return f" (@{sender.username})"
        return ""

    def _generate_deep_link(self, chat, message) -> str:
        """Generate deep link to message.

        Args:
            chat: Chat object
            message: Message object

        Returns:
            Deep link URL
        """
        try:
            if not chat:
                return "tg://resolve?domain=telegram"

            # Private chat with user - use username if available
            if hasattr(chat, 'username') and chat.username:
                return f"https://t.me/{chat.username}"

            # Check if it's a private chat (User type)
            from telethon.tl.types import User, Channel, Chat

            if isinstance(chat, User):
                # For private chats, link to user profile
                return f"tg://user?id={chat.id}"

            # Channel or supergroup with username
            if isinstance(chat, Channel):
                if chat.username:
                    return f"https://t.me/{chat.username}/{message.id}"
                else:
                    # Private channel/supergroup - use c/ link format
                    # Channel IDs are stored with -100 prefix internally
                    channel_id = chat.id
                    return f"https://t.me/c/{channel_id}/{message.id}"

            # Regular group (Chat type)
            if isinstance(chat, Chat):
                return f"tg://openmessage?chat_id={chat.id}&message_id={message.id}"

            return "tg://resolve?domain=telegram"

        except Exception as e:
            logger.warning(f"Failed to generate deep link: {e}")
            return "tg://resolve?domain=telegram"

    def _get_message_preview(self, message) -> str:
        """Get message preview text (truncated to 200 characters).

        Args:
            message: Message object

        Returns:
            Preview text
        """
        if message.text:
            text = message.text
            if len(text) > 200:
                return text[:200] + "..."
            return text

        # Media-only message
        if message.media:
            return "[Media]"

        return "[No content]"
