"""State management for deduplication, priority contacts, and snooze.

Maintains persistent state to track processed messages, priority contacts,
and snooze configuration.
"""

import json
import logging
import os
import re
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Default queue size limit for snooze queue mode
DEFAULT_QUEUE_LIMIT = 100


class StateManager:
    """Manages deduplication state with JSON persistence."""

    def __init__(self, state_file: str):
        """Initialize state manager.

        Args:
            state_file: Path to state file
        """
        self.state_file = state_file
        self.processed_messages: Dict[str, Dict] = {}
        self.last_cleanup: float = time.time()

        # Priority contacts state
        self.priority_mode: str = "disabled"  # disabled, whitelist, blacklist
        self.priority_whitelist: Dict[int, str] = {}  # id -> display_name
        self.priority_blacklist: Dict[int, str] = {}  # id -> display_name

        # Snooze state
        self.snooze_active: bool = False
        self.snooze_until: Optional[float] = None
        self.snooze_behavior: str = "drop"  # drop or queue
        self.snooze_queue: List[Dict[str, Any]] = []
        self.queue_limit: int = DEFAULT_QUEUE_LIMIT

        # User timezone (UTC offset in hours)
        self.timezone_offset: float = 0.0

        self.load()

    def is_processed(self, chat_id: int, message_id: int) -> bool:
        """Check if a message has already been processed.

        Args:
            chat_id: Chat ID
            message_id: Message ID

        Returns:
            True if message was already processed
        """
        key = self._make_key(chat_id, message_id)
        return key in self.processed_messages

    def mark_processed(self, chat_id: int, message_id: int, trigger_type: str):
        """Mark a message as processed.

        Args:
            chat_id: Chat ID
            message_id: Message ID
            trigger_type: Type of trigger that caused the alert
        """
        key = self._make_key(chat_id, message_id)
        self.processed_messages[key] = {
            'timestamp': time.time(),
            'trigger_type': trigger_type
        }
        self.save()

    def _make_key(self, chat_id: int, message_id: int) -> str:
        """Generate composite key for message identification.

        Args:
            chat_id: Chat ID
            message_id: Message ID

        Returns:
            Composite key string
        """
        return f"{chat_id}:{message_id}"

    def load(self):
        """Load state from file."""
        if not os.path.exists(self.state_file):
            logger.info(f"State file {self.state_file} does not exist, starting with empty state")
            return

        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
                self.processed_messages = data.get('processed_messages', {})
                self.last_cleanup = data.get('last_cleanup', time.time())

                # Load priority contacts state (migration: add defaults if missing)
                priority_data = data.get('priority_contacts', {})
                self.priority_mode = priority_data.get('mode', 'disabled')
                # Convert keys back to int (JSON stores as string)
                whitelist = priority_data.get('whitelist', {})
                self.priority_whitelist = {int(k): v for k, v in whitelist.items()}
                blacklist = priority_data.get('blacklist', {})
                self.priority_blacklist = {int(k): v for k, v in blacklist.items()}

                # Load snooze state (migration: add defaults if missing)
                snooze_data = data.get('snooze', {})
                self.snooze_active = snooze_data.get('active', False)
                self.snooze_until = snooze_data.get('until', None)
                self.snooze_behavior = snooze_data.get('behavior', 'drop')
                self.snooze_queue = snooze_data.get('queue', [])

                # Load timezone (migration: default to 0 if missing)
                self.timezone_offset = data.get('timezone_offset', 0.0)

                # Check if snooze expired during downtime
                if self.snooze_active and self.snooze_until:
                    if time.time() > self.snooze_until:
                        logger.info("Snooze expired during downtime, deactivating")
                        self.snooze_active = False
                        # Queue will be delivered on first run if any

            logger.info(f"Loaded state with {len(self.processed_messages)} processed messages")
            if self.priority_mode != 'disabled':
                logger.info(f"Priority mode: {self.priority_mode}")
            if self.snooze_active:
                remaining = self.snooze_until - time.time()
                logger.info(f"Snooze active for {remaining/60:.1f} more minutes")

        except json.JSONDecodeError as e:
            logger.error(f"State file is corrupted: {e}")
            # Backup corrupted file
            backup_file = f"{self.state_file}.backup.{int(time.time())}"
            try:
                os.rename(self.state_file, backup_file)
                logger.info(f"Backed up corrupted state to {backup_file}")
            except Exception as backup_error:
                logger.warning(f"Failed to backup corrupted state: {backup_error}")

            # Start with empty state
            self._reset_state()

        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            self._reset_state()

    def _reset_state(self):
        """Reset all state to defaults."""
        self.processed_messages = {}
        self.last_cleanup = time.time()
        self.priority_mode = "disabled"
        self.priority_whitelist = {}
        self.priority_blacklist = {}
        self.snooze_active = False
        self.snooze_until = None
        self.snooze_behavior = "drop"
        self.snooze_queue = []
        self.timezone_offset = 0.0

    def save(self):
        """Save state to file atomically."""
        try:
            # Write to temporary file
            temp_file = f"{self.state_file}.tmp"
            data = {
                'processed_messages': self.processed_messages,
                'last_cleanup': self.last_cleanup,
                'priority_contacts': {
                    'mode': self.priority_mode,
                    'whitelist': {str(k): v for k, v in self.priority_whitelist.items()},
                    'blacklist': {str(k): v for k, v in self.priority_blacklist.items()},
                },
                'snooze': {
                    'active': self.snooze_active,
                    'until': self.snooze_until,
                    'behavior': self.snooze_behavior,
                    'queue': self.snooze_queue,
                },
                'timezone_offset': self.timezone_offset,
            }

            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)

            # Atomic rename
            os.rename(temp_file, self.state_file)
            logger.debug(f"Saved state with {len(self.processed_messages)} entries")

        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def cleanup_old_entries(self, days: int = 30):
        """Remove entries older than specified days.

        Args:
            days: Number of days to retain entries (default: 30)
        """
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        initial_count = len(self.processed_messages)

        # Filter out old entries
        self.processed_messages = {
            k: v for k, v in self.processed_messages.items()
            if v.get('timestamp', 0) > cutoff_time
        }

        removed_count = initial_count - len(self.processed_messages)
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old entries from state")
            self.last_cleanup = time.time()
            self.save()

    def should_cleanup(self) -> bool:
        """Check if cleanup should run (every 24 hours).

        Returns:
            True if cleanup is due
        """
        return (time.time() - self.last_cleanup) > (24 * 60 * 60)

    # -------------------------------------------------------------------------
    # Priority Contacts Methods
    # -------------------------------------------------------------------------

    def set_priority_mode(self, mode: str) -> str:
        """Set the priority filtering mode.

        Args:
            mode: One of 'disabled', 'whitelist', or 'blacklist'

        Returns:
            Warning message if switching between whitelist/blacklist, else empty
        """
        old_mode = self.priority_mode
        warning = ""

        if mode not in ('disabled', 'whitelist', 'blacklist'):
            raise ValueError(f"Invalid mode: {mode}")

        # Warn when switching between whitelist and blacklist
        if old_mode in ('whitelist', 'blacklist') and mode in ('whitelist', 'blacklist') and old_mode != mode:
            warning = f"Switched from {old_mode} to {mode} mode. The other list is preserved but inactive."

        self.priority_mode = mode
        self.save()
        return warning

    def add_priority_contact(self, contact_id: int, display_name: str) -> bool:
        """Add a contact to the priority whitelist.

        Args:
            contact_id: Telegram user/chat ID
            display_name: Display name for the contact

        Returns:
            True if added, False if already exists
        """
        if contact_id in self.priority_whitelist:
            return False
        self.priority_whitelist[contact_id] = display_name
        self.save()
        return True

    def remove_priority_contact(self, contact_id: int) -> bool:
        """Remove a contact from the priority whitelist.

        Args:
            contact_id: Telegram user/chat ID

        Returns:
            True if removed, False if not found
        """
        if contact_id not in self.priority_whitelist:
            return False
        del self.priority_whitelist[contact_id]
        self.save()
        return True

    def add_muted_contact(self, contact_id: int, display_name: str) -> bool:
        """Add a contact to the mute blacklist.

        Args:
            contact_id: Telegram user/chat ID
            display_name: Display name for the contact

        Returns:
            True if added, False if already exists
        """
        if contact_id in self.priority_blacklist:
            return False
        self.priority_blacklist[contact_id] = display_name
        self.save()
        return True

    def remove_muted_contact(self, contact_id: int) -> bool:
        """Remove a contact from the mute blacklist.

        Args:
            contact_id: Telegram user/chat ID

        Returns:
            True if removed, False if not found
        """
        if contact_id not in self.priority_blacklist:
            return False
        del self.priority_blacklist[contact_id]
        self.save()
        return True

    def should_process_message(self, sender_id: int, chat_id: int) -> bool:
        """Check if a message should be processed based on priority filter.

        Args:
            sender_id: ID of the message sender
            chat_id: ID of the chat

        Returns:
            True if message should be processed, False if filtered out
        """
        if self.priority_mode == "disabled":
            return True

        if self.priority_mode == "whitelist":
            # Only process if sender or chat is in whitelist
            return sender_id in self.priority_whitelist or chat_id in self.priority_whitelist

        if self.priority_mode == "blacklist":
            # Block if sender or chat is in blacklist
            return sender_id not in self.priority_blacklist and chat_id not in self.priority_blacklist

        return True

    # -------------------------------------------------------------------------
    # Snooze Methods
    # -------------------------------------------------------------------------

    @staticmethod
    def parse_duration(duration_str: str) -> Optional[int]:
        """Parse duration string to seconds.

        Args:
            duration_str: Duration like '30m', '2h', '1d'

        Returns:
            Duration in seconds, or None if invalid format
        """
        match = re.match(r'^(\d+)([mhd])$', duration_str.lower().strip())
        if not match:
            return None

        value = int(match.group(1))
        unit = match.group(2)

        if unit == 'm':
            return value * 60
        elif unit == 'h':
            return value * 3600
        elif unit == 'd':
            return value * 86400
        return None

    def activate_snooze(self, duration_seconds: int, queue_mode: bool = False):
        """Activate snooze for a specified duration.

        Args:
            duration_seconds: Duration in seconds
            queue_mode: If True, queue alerts instead of dropping
        """
        self.snooze_active = True
        self.snooze_until = time.time() + duration_seconds
        self.snooze_behavior = "queue" if queue_mode else "drop"
        self.save()
        logger.info(f"Snooze activated for {duration_seconds}s, behavior={self.snooze_behavior}")

    def deactivate_snooze(self) -> List[Dict[str, Any]]:
        """Deactivate snooze and return queued alerts.

        Returns:
            List of queued alerts (empty if drop mode was used)
        """
        queued = self.snooze_queue.copy()
        self.snooze_active = False
        self.snooze_until = None
        self.snooze_queue = []
        self.save()
        logger.info(f"Snooze deactivated, returning {len(queued)} queued alerts")
        return queued

    def check_snooze_expired(self) -> bool:
        """Check if snooze has expired and deactivate if so.

        Returns:
            True if snooze was active but expired
        """
        if self.snooze_active and self.snooze_until:
            if time.time() > self.snooze_until:
                logger.info("Snooze expired")
                self.snooze_active = False
                # Keep queue for delivery
                return True
        return False

    def is_snoozed(self) -> bool:
        """Check if snooze is currently active.

        Returns:
            True if snoozed
        """
        self.check_snooze_expired()
        return self.snooze_active

    def snooze_remaining_seconds(self) -> Optional[float]:
        """Get remaining snooze time in seconds.

        Returns:
            Remaining seconds, or None if not snoozed
        """
        if not self.snooze_active or not self.snooze_until:
            return None
        remaining = self.snooze_until - time.time()
        return max(0, remaining)

    def queue_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Add an alert to the snooze queue.

        Args:
            alert_data: Alert data to queue

        Returns:
            True if queued, False if not in queue mode
        """
        if self.snooze_behavior != "queue":
            return False

        # FIFO eviction if at limit
        if len(self.snooze_queue) >= self.queue_limit:
            self.snooze_queue.pop(0)
            logger.warning(f"Queue at limit ({self.queue_limit}), dropped oldest alert")

        self.snooze_queue.append(alert_data)
        self.save()

        # Warn if approaching limit
        if len(self.snooze_queue) >= self.queue_limit * 0.8:
            logger.warning(f"Queue at {len(self.snooze_queue)}/{self.queue_limit} capacity")

        return True

    def get_queue_size(self) -> int:
        """Get current queue size.

        Returns:
            Number of queued alerts
        """
        return len(self.snooze_queue)

    def clear_queue(self):
        """Clear the alert queue."""
        self.snooze_queue = []
        self.save()

    # -------------------------------------------------------------------------
    # Timezone Methods
    # -------------------------------------------------------------------------

    def get_timezone_offset(self) -> float:
        """Get the user's timezone offset in hours.

        Returns:
            UTC offset in hours (e.g., 7 for UTC+7, -5 for UTC-5)
        """
        return self.timezone_offset

    def set_timezone_offset(self, offset: float):
        """Set the user's timezone offset.

        Args:
            offset: UTC offset in hours (e.g., 7 for UTC+7, -5 for UTC-5)
        """
        self.timezone_offset = offset
        self.save()
        logger.info(f"Timezone set to UTC{'+' if offset >= 0 else ''}{offset:g}")
