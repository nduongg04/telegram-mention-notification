"""State management for deduplication.

Maintains persistent state to track processed messages and prevent duplicates.
"""

import json
import logging
import os
import time
from typing import Dict, Set
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


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
            logger.info(f"Loaded state with {len(self.processed_messages)} processed messages")

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
            self.processed_messages = {}
            self.last_cleanup = time.time()

        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            self.processed_messages = {}
            self.last_cleanup = time.time()

    def save(self):
        """Save state to file atomically."""
        try:
            # Write to temporary file
            temp_file = f"{self.state_file}.tmp"
            data = {
                'processed_messages': self.processed_messages,
                'last_cleanup': self.last_cleanup
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
