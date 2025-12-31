#!/usr/bin/env python3
"""Telegram Priority Notifier - Main Application.

Monitors Telegram messages and sends priority alerts to Saved Messages
for direct messages, mentions, and replies.
"""

import asyncio
import logging
import signal
import sys
import time
from datetime import datetime

from telethon import events

from src.config import load_config
from src.auth import AuthManager
from src.triggers import TriggerEngine
from src.formatter import AlertFormatter
from src.notifier import NotificationSink
from src.state import StateManager


# Metrics tracking
class Metrics:
    """Tracks operational metrics."""

    def __init__(self):
        self.start_time = time.time()
        self.messages_received = 0
        self.alerts_sent = {"DM": 0, "Mention": 0, "Reply": 0}
        self.dedup_hits = 0
        self.last_heartbeat = time.time()

    def record_message(self):
        """Record a message received."""
        self.messages_received += 1

    def record_alert(self, trigger_type: str):
        """Record an alert sent."""
        if trigger_type in self.alerts_sent:
            self.alerts_sent[trigger_type] += 1

    def record_dedup_hit(self):
        """Record a deduplication hit."""
        self.dedup_hits += 1

    def uptime(self) -> str:
        """Get uptime string."""
        uptime_seconds = int(time.time() - self.start_time)
        hours = uptime_seconds // 3600
        minutes = (uptime_seconds % 3600) // 60
        return f"{hours}h {minutes}m"

    def should_log_heartbeat(self) -> bool:
        """Check if hourly heartbeat should be logged."""
        return (time.time() - self.last_heartbeat) >= 3600

    def log_heartbeat(self, logger):
        """Log heartbeat with metrics."""
        total_alerts = sum(self.alerts_sent.values())
        logger.info(f"=== Heartbeat ===")
        logger.info(f"Uptime: {self.uptime()}")
        logger.info(f"Messages received: {self.messages_received}")
        logger.info(f"Alerts sent: {total_alerts} (DM: {self.alerts_sent['DM']}, Mention: {self.alerts_sent['Mention']}, Reply: {self.alerts_sent['Reply']})")
        logger.info(f"Deduplication hits: {self.dedup_hits}")
        self.last_heartbeat = time.time()


class TelegramPriorityNotifier:
    """Main application class."""

    def __init__(self):
        """Initialize the application."""
        self.config = None
        self.auth_manager = None
        self.client = None
        self.trigger_engine = None
        self.formatter = None
        self.notifier = None
        self.state = None
        self.metrics = Metrics()
        self.logger = None
        self.running = True

    def setup_logging(self, log_level: str):
        """Setup logging configuration."""
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)

    async def startup(self):
        """Initialize all components and start the application."""
        # Load configuration
        self.config = load_config()
        self.setup_logging(self.config.log_level)

        self.logger.info("=" * 60)
        self.logger.info("Telegram Priority Notifier Starting...")
        self.logger.info("=" * 60)
        self.logger.info(self.config.summary())

        # Initialize state manager
        self.state = StateManager(self.config.state_file)

        # Initialize and connect auth manager
        self.auth_manager = AuthManager(
            self.config.api_id,
            self.config.api_hash,
            self.config.phone,
            self.config.session_file
        )
        self.client = await self.auth_manager.connect()

        # Get user info
        me = await self.client.get_me()
        user_id = me.id
        username = me.username

        self.logger.info(f"Authenticated as: {me.first_name} (@{username}) [ID: {user_id}]")

        # Initialize components
        self.trigger_engine = TriggerEngine(user_id, username, self.config.chat_id)
        self.formatter = AlertFormatter()
        self.notifier = NotificationSink(self.config.bot_token, self.config.chat_id)

        # Register message handler
        @self.client.on(events.NewMessage(incoming=True))
        async def message_handler(event):
            await self.handle_message(event)

        self.logger.info("✓ All components initialized successfully")
        self.logger.info("✓ Message listener registered")
        self.logger.info("=" * 60)
        self.logger.info("System is now running. Press Ctrl+C to stop.")
        self.logger.info("=" * 60)

    async def handle_message(self, event):
        """Handle incoming message event.

        Args:
            event: Telethon NewMessage event
        """
        try:
            self.metrics.record_message()
            message = event.message

            # Check trigger conditions
            should_alert, trigger_type = await self.trigger_engine.should_alert(event)

            if not should_alert:
                return

            # Check deduplication
            if self.state.is_processed(message.chat_id, message.id):
                self.logger.debug(f"Message {message.chat_id}:{message.id} already processed, skipping")
                self.metrics.record_dedup_hit()
                return

            # Format alert
            alert_message = await self.formatter.format_alert(event, trigger_type)

            # Send alert
            success = await self.notifier.send_alert(alert_message)

            if success:
                # Mark as processed
                self.state.mark_processed(message.chat_id, message.id, trigger_type)
                self.metrics.record_alert(trigger_type)
                self.logger.info(f"Alert sent for {trigger_type} from chat {message.chat_id}")
            else:
                self.logger.error(f"Failed to send alert for {trigger_type} from chat {message.chat_id}")

        except Exception as e:
            self.logger.error(f"Error processing message {message.chat_id}:{message.id}: {e}", exc_info=True)

    async def run(self):
        """Run the main event loop."""
        await self.startup()

        # Main loop
        while self.running:
            try:
                # Periodic heartbeat logging
                if self.metrics.should_log_heartbeat():
                    self.metrics.log_heartbeat(self.logger)

                # Periodic state cleanup
                if self.state.should_cleanup():
                    self.logger.info("Running periodic state cleanup...")
                    self.state.cleanup_old_entries()

                await asyncio.sleep(60)  # Check every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def shutdown(self):
        """Graceful shutdown."""
        self.logger.info("=" * 60)
        self.logger.info("Shutting down...")
        self.logger.info("=" * 60)

        self.running = False

        # Log final metrics
        self.metrics.log_heartbeat(self.logger)

        # Save state
        if self.state:
            self.state.save()
            self.logger.info("✓ State saved")

        # Disconnect from Telegram
        if self.auth_manager:
            await self.auth_manager.disconnect()
            self.logger.info("✓ Disconnected from Telegram")

        self.logger.info("=" * 60)
        self.logger.info("Shutdown complete")
        self.logger.info("=" * 60)


async def main():
    """Main entry point."""
    app = TelegramPriorityNotifier()

    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        asyncio.create_task(app.shutdown())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await app.run()
    except KeyboardInterrupt:
        await app.shutdown()
    except Exception as e:
        if app.logger:
            app.logger.critical(f"Fatal error: {e}", exc_info=True)
        else:
            print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
