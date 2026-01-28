"""Alert message formatter.

Formats notification messages with metadata and deep links.
"""

import logging
from datetime import timezone, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.state import StateManager

logger = logging.getLogger(__name__)


class AlertFormatter:
    """Formats alert messages for delivery."""

    # Emoji mapping for trigger types
    EMOJI = {
        "DM": "🔔",
        "Mention": "💬",
        "Reply": "💬"
    }

    def __init__(self, state: "StateManager"):
        """Initialize formatter.

        Args:
            state: State manager for accessing user timezone.
        """
        self.state = state

    async def format_alert(self, event, trigger_type: str) -> str:
        """Format an alert message.

        Args:
            event: Telethon NewMessage event
            trigger_type: Type of trigger ("DM", "Mention", or "Reply")

        Returns:
            Formatted alert message string
        """
        message = event.message

        # Get chat info - fetch if needed
        chat = await event.get_chat()
        chat_name = self._get_chat_name(chat)

        # Get sender info - fetch if needed
        sender = await event.get_sender()
        sender_name = self._get_sender_name(sender)

        # Get timestamp in user's timezone (HH:MM format)
        timestamp = self._format_timestamp(message.date)

        # Generate deep link
        deep_link = self._generate_deep_link(chat, message)

        # Get message preview
        preview = self._get_message_preview(message)

        # Check if message has media
        has_media = self.has_media(message)

        # Check if this is a DM (private chat) or group/channel
        is_dm = trigger_type == "DM"

        if is_dm:
            # DM Format:
            # 🔔 Sender Name
            #    message preview / [media]
            #
            #    HH:MM • View →
            alert = self._format_dm_alert(sender_name, preview, timestamp, deep_link, has_media)
        else:
            # Group Format:
            # 💬 Group Name
            # Sender Name: message preview / [media]
            #
            # HH:MM • View group →
            emoji = self.EMOJI.get(trigger_type, "💬")
            alert = self._format_group_alert(
                emoji, chat_name, sender_name, preview, timestamp, deep_link, has_media
            )

        return alert

    def _format_dm_alert(
        self, sender_name: str, preview: str, timestamp: str, deep_link: str, has_media: bool = False
    ) -> str:
        """Format a DM notification."""
        if has_media:
            # Media message - caption goes above media (Telegram shows: caption then media)
            # So we put sender name in caption, media will appear below it
            return f"""🔔 <b>{self._escape_html(sender_name)}</b>

{timestamp} • <a href="{deep_link}">View →</a>"""
        elif preview:
            return f"""🔔 <b>{self._escape_html(sender_name)}</b>
   {self._escape_html(preview)}

   {timestamp} • <a href="{deep_link}">View →</a>"""
        else:
            return f"""🔔 <b>{self._escape_html(sender_name)}</b>

   {timestamp} • <a href="{deep_link}">View →</a>"""

    def _format_group_alert(
        self,
        emoji: str,
        chat_name: str,
        sender_name: str,
        preview: str,
        timestamp: str,
        deep_link: str,
        has_media: bool = False,
    ) -> str:
        """Format a group/channel notification."""
        if has_media:
            # Media message - caption above media
            return f"""{emoji} <b>{self._escape_html(chat_name)}</b>
{self._escape_html(sender_name)}

{timestamp} • <a href="{deep_link}">View group →</a>"""
        elif preview:
            return f"""{emoji} <b>{self._escape_html(chat_name)}</b>
{self._escape_html(sender_name)}: {self._escape_html(preview)}

{timestamp} • <a href="{deep_link}">View group →</a>"""
        else:
            return f"""{emoji} <b>{self._escape_html(chat_name)}</b>
{self._escape_html(sender_name)}

{timestamp} • <a href="{deep_link}">View group →</a>"""

    def _format_timestamp(self, dt) -> str:
        """Format timestamp to HH:MM in user's timezone."""
        offset_hours = self.state.get_timezone_offset()
        user_tz = timezone(timedelta(hours=offset_hours))
        dt = dt.astimezone(user_tz)
        return dt.strftime("%H:%M")

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

        # For media messages, return empty string - media will be forwarded separately
        if message.media:
            return ""

        return "[No content]"

    def has_media(self, message) -> bool:
        """Check if message contains media that should be forwarded.

        Args:
            message: Message object

        Returns:
            True if message has forwardable media
        """
        if not message.media:
            return False

        from telethon.tl.types import (
            MessageMediaPhoto,
            MessageMediaDocument,
            MessageMediaWebPage,
        )

        # Forward photos, videos, documents, etc.
        # Skip web page previews (they're just link previews)
        if isinstance(message.media, MessageMediaWebPage):
            return False

        return isinstance(message.media, (MessageMediaPhoto, MessageMediaDocument))
