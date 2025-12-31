"""Bot command handlers for priority contacts and snooze.

Handles user commands sent to the notification bot.
"""

import logging
import time
from typing import Optional, Tuple

from telethon import TelegramClient

from src.state import StateManager
from src.notifier import NotificationSink

logger = logging.getLogger(__name__)


class CommandHandler:
    """Handles bot commands for priority contacts and snooze."""

    def __init__(
        self,
        state: StateManager,
        notifier: NotificationSink,
        client: TelegramClient,
        owner_id: int,
    ):
        """Initialize command handler.

        Args:
            state: State manager instance
            notifier: Notification sink for sending responses
            client: Telethon client for resolving usernames
            owner_id: ID of the bot owner (only they can use commands)
        """
        self.state = state
        self.notifier = notifier
        self.client = client
        self.owner_id = owner_id

    async def handle_command(self, text: str, sender_id: int) -> Optional[str]:
        """Handle a command message.

        Args:
            text: Message text
            sender_id: ID of the message sender

        Returns:
            Response message, or None if not a command
        """
        if sender_id != self.owner_id:
            return None

        text = text.strip()
        if not text.startswith('/'):
            return None

        parts = text.split(maxsplit=2)
        command = parts[0].lower().split('@')[0]  # Handle /command@botname
        args = parts[1:] if len(parts) > 1 else []

        try:
            if command == '/start':
                return self._handle_start()
            elif command == '/help':
                return self._handle_help()
            elif command == '/priority':
                return await self._handle_priority(args)
            elif command == '/mute':
                return await self._handle_mute(args)
            elif command == '/unmute':
                return await self._handle_unmute(args)
            elif command == '/listmuted':
                return self._handle_listmuted()
            elif command == '/snooze':
                return self._handle_snooze(args)
            elif command == '/unsnooze':
                return await self._handle_unsnooze()
            elif command == '/status':
                return self._handle_status()
        except Exception as e:
            logger.error(f"Error handling command {command}: {e}", exc_info=True)
            return f"🤖 ❌ Error: {str(e)}"

        return None

    def _handle_start(self) -> str:
        """Handle /start command."""
        return """🤖 <b>Priority Notifier Bot</b>

Welcome! This bot monitors your Telegram for important messages and sends you alerts for:
• Direct messages (DMs)
• Mentions (@username)
• Replies to your messages

Use /help to see all available commands."""

    def _handle_help(self) -> str:
        """Handle /help command."""
        return """🤖 <b>Available Commands</b>

<b>Status</b>
/status - Show current notifier status

<b>Snooze</b>
/snooze &lt;duration&gt; - Snooze alerts (e.g., 30m, 2h, 1d)
/snooze --queue &lt;duration&gt; - Snooze with queueing
/snooze status - Check snooze status
/unsnooze - End snooze and deliver queued alerts

<b>Priority Contacts</b>
/priority mode &lt;whitelist|blacklist|off&gt; - Set filter mode
/priority add @user - Add to priority list
/priority remove @user - Remove from priority list
/priority list - Show priority list

<b>Mute List</b>
/mute @chat - Mute a chat/user
/unmute @chat - Unmute a chat/user
/listmuted - Show muted list"""

    async def _handle_priority(self, args: list) -> str:
        """Handle /priority command.

        Subcommands:
            mode <whitelist|blacklist|off>
            add @user
            remove @user
            list
        """
        if not args:
            return self._priority_help()

        subcommand = args[0].lower()

        if subcommand == 'mode':
            if len(args) < 2:
                return f"Current mode: {self.state.priority_mode}\n\nUsage: /priority mode <whitelist|blacklist|off>"

            mode = args[1].lower()
            if mode == 'off':
                mode = 'disabled'

            if mode not in ('disabled', 'whitelist', 'blacklist'):
                return "🤖 Invalid mode. Use: whitelist, blacklist, or off"

            warning = self.state.set_priority_mode(mode)
            response = f"🤖 Priority mode set to: <b>{mode}</b>"
            if mode == 'whitelist':
                response += "\n\nOnly contacts in the priority list will trigger alerts."
            elif mode == 'blacklist':
                response += "\n\nAll contacts except muted ones will trigger alerts."
            else:
                response += "\n\nAll qualifying messages will trigger alerts."
            if warning:
                response += f"\n\n⚠️ {warning}"
            return response

        elif subcommand == 'add':
            if len(args) < 2:
                return "🤖 Usage: /priority add @username"

            identifier = args[1]
            entity_id, display_name = await self._resolve_entity(identifier)
            if entity_id is None:
                return f"🤖 Could not resolve: {identifier}"

            if self.state.add_priority_contact(entity_id, display_name):
                return f"🤖 Added <b>{display_name}</b> to priority list"
            else:
                return f"🤖 {display_name} is already in the priority list"

        elif subcommand == 'remove':
            if len(args) < 2:
                return "🤖 Usage: /priority remove @username"

            identifier = args[1]
            entity_id, display_name = await self._resolve_entity(identifier)
            if entity_id is None:
                return f"🤖 Could not resolve: {identifier}"

            if self.state.remove_priority_contact(entity_id):
                return f"🤖 Removed <b>{display_name}</b> from priority list"
            else:
                return f"🤖 {display_name} was not in the priority list"

        elif subcommand == 'list':
            return self._format_priority_list()

        else:
            return self._priority_help()

    def _priority_help(self) -> str:
        """Return priority command help."""
        return """🤖 <b>Priority Commands</b>

/priority mode &lt;whitelist|blacklist|off&gt;
/priority add @user - Add to priority list
/priority remove @user - Remove from priority list
/priority list - Show priority list

Current mode: """ + self.state.priority_mode

    def _format_priority_list(self) -> str:
        """Format the priority list for display."""
        mode = self.state.priority_mode
        response = f"🤖 <b>Priority List</b>\n\nMode: {mode}\n\n"

        if self.state.priority_whitelist:
            response += "Contacts:\n"
            for cid, name in self.state.priority_whitelist.items():
                response += f"  • {name}\n"
        else:
            response += "List is empty.\n"

        if mode == 'whitelist':
            response += "\nOnly these contacts will trigger alerts."
        elif mode == 'disabled':
            response += "\nFiltering is disabled. All qualifying messages trigger alerts."

        return response

    async def _handle_mute(self, args: list) -> str:
        """Handle /mute @chat command."""
        if not args:
            return "🤖 Usage: /mute @username or @groupname"

        identifier = args[0]
        entity_id, display_name = await self._resolve_entity(identifier)
        if entity_id is None:
            return f"🤖 Could not resolve: {identifier}"

        if self.state.add_muted_contact(entity_id, display_name):
            response = f"🤖 Muted <b>{display_name}</b>"
            if self.state.priority_mode != 'blacklist':
                response += "\n\n⚠️ Note: Mute list only applies when mode is 'blacklist'. Current mode: " + self.state.priority_mode
            return response
        else:
            return f"🤖 {display_name} is already muted"

    async def _handle_unmute(self, args: list) -> str:
        """Handle /unmute @chat command."""
        if not args:
            return "🤖 Usage: /unmute @username or @groupname"

        identifier = args[0]
        entity_id, display_name = await self._resolve_entity(identifier)
        if entity_id is None:
            return f"🤖 Could not resolve: {identifier}"

        if self.state.remove_muted_contact(entity_id):
            return f"🤖 Unmuted <b>{display_name}</b>"
        else:
            return f"🤖 {display_name} was not muted"

    def _handle_listmuted(self) -> str:
        """Handle /listmuted command."""
        mode = self.state.priority_mode
        response = f"🤖 <b>Muted List</b>\n\nMode: {mode}\n\n"

        if self.state.priority_blacklist:
            response += "Muted:\n"
            for cid, name in self.state.priority_blacklist.items():
                response += f"  • {name}\n"
        else:
            response += "List is empty.\n"

        if mode == 'blacklist':
            response += "\nThese contacts will NOT trigger alerts."
        elif mode == 'disabled':
            response += "\nFiltering is disabled. Mute list is inactive."
        else:
            response += f"\nMute list is inactive in {mode} mode."

        return response

    def _handle_snooze(self, args: list) -> str:
        """Handle /snooze command."""
        if not args:
            return self._snooze_help()

        arg = args[0].lower()

        # /snooze status
        if arg == 'status':
            return self._snooze_status()

        # Check for --queue flag
        queue_mode = False
        duration_arg = arg

        if arg == '--queue':
            queue_mode = True
            if len(args) < 2:
                return "Usage: /snooze --queue <duration>\nExample: /snooze --queue 2h"
            duration_arg = args[1]

        # Parse duration
        seconds = self.state.parse_duration(duration_arg)
        if seconds is None:
            return f"Invalid duration format: {duration_arg}\n\nValid formats: 30m, 2h, 1d"

        self.state.activate_snooze(seconds, queue_mode=queue_mode)

        # Format end time
        end_time = time.time() + seconds
        end_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))

        response = f"🤖 <b>Snooze Activated</b>\n\nUntil: {end_str}"
        if queue_mode:
            response += "\n\nAlerts will be queued and delivered when you unsnooze."
        else:
            response += "\n\nAlerts will be silently dropped."

        return response

    def _snooze_help(self) -> str:
        """Return snooze command help."""
        return """🤖 <b>Snooze Commands</b>

/snooze &lt;duration&gt; - Snooze alerts (e.g., 30m, 2h, 1d)
/snooze --queue &lt;duration&gt; - Snooze with queueing
/snooze status - Check snooze status
/unsnooze - End snooze and deliver queued alerts

""" + self._snooze_status()

    def _snooze_status(self) -> str:
        """Return snooze status."""
        if not self.state.snooze_active:
            return "🤖 Snooze: <b>Inactive</b>"

        remaining = self.state.snooze_remaining_seconds()
        if remaining is None or remaining <= 0:
            return "🤖 Snooze: <b>Expired</b>"

        # Format remaining time
        if remaining >= 3600:
            remaining_str = f"{remaining/3600:.1f}h"
        elif remaining >= 60:
            remaining_str = f"{remaining/60:.0f}m"
        else:
            remaining_str = f"{remaining:.0f}s"

        response = f"🤖 Snooze: <b>Active</b> ({remaining_str} remaining)"
        response += f"\nBehavior: {self.state.snooze_behavior}"

        if self.state.snooze_behavior == 'queue':
            response += f"\nQueued alerts: {self.state.get_queue_size()}/{self.state.queue_limit}"

        return response

    async def _handle_unsnooze(self) -> str:
        """Handle /unsnooze command."""
        if not self.state.snooze_active:
            return "🤖 Snooze is not active."

        queued_alerts = self.state.deactivate_snooze()

        if not queued_alerts:
            return "🤖 <b>Snooze Deactivated</b>\n\nNo queued alerts."

        # Deliver queued alerts
        delivered = 0
        for alert in queued_alerts:
            try:
                message = alert.get('message', '')
                if message:
                    await self.notifier.send_alert(message)
                    delivered += 1
            except Exception as e:
                logger.error(f"Failed to deliver queued alert: {e}")

        return f"🤖 <b>Snooze Deactivated</b>\n\nDelivered {delivered}/{len(queued_alerts)} queued alerts."

    def _handle_status(self) -> str:
        """Handle /status command - show overall status."""
        lines = ["🤖 <b>Notifier Status</b>"]

        # Priority status
        lines.append(f"\n<b>Priority Mode:</b> {self.state.priority_mode}")
        if self.state.priority_mode == 'whitelist':
            lines.append(f"  Priority contacts: {len(self.state.priority_whitelist)}")
        elif self.state.priority_mode == 'blacklist':
            lines.append(f"  Muted contacts: {len(self.state.priority_blacklist)}")

        # Snooze status (without duplicate 🤖 prefix)
        snooze = self._snooze_status().replace("🤖 ", "")
        lines.append(f"\n{snooze}")

        return "\n".join(lines)

    async def _resolve_entity(self, identifier: str) -> Tuple[Optional[int], str]:
        """Resolve a username or ID to an entity.

        Args:
            identifier: Username (@user) or numeric ID

        Returns:
            Tuple of (entity_id, display_name), or (None, '') if not found
        """
        try:
            # Remove @ prefix if present
            if identifier.startswith('@'):
                identifier = identifier[1:]

            # Try to get entity
            entity = await self.client.get_entity(identifier)

            # Get display name
            if hasattr(entity, 'title'):
                display_name = entity.title  # Groups/channels
            elif hasattr(entity, 'first_name'):
                display_name = entity.first_name
                if hasattr(entity, 'last_name') and entity.last_name:
                    display_name += f" {entity.last_name}"
            else:
                display_name = identifier

            # Add username if available
            if hasattr(entity, 'username') and entity.username:
                display_name += f" (@{entity.username})"

            return entity.id, display_name

        except Exception as e:
            logger.warning(f"Failed to resolve entity {identifier}: {e}")
            return None, ""
