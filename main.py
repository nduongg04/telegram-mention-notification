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

from telethon import events, TelegramClient

from src.config import load_config
from src.auth import AuthManager
from src.triggers import TriggerEngine
from src.formatter import AlertFormatter
from src.notifier import NotificationSink
from src.state import StateManager
from src.commands import CommandHandler


# Metrics tracking
class Metrics:
    """Tracks operational metrics."""

    def __init__(self):
        self.start_time = time.time()
        self.messages_received = 0
        self.alerts_sent = {"DM": 0, "Mention": 0, "Reply": 0}
        self.dedup_hits = 0
        self.priority_filtered = 0
        self.snooze_dropped = 0
        self.snooze_queued = 0
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

    def record_priority_filtered(self):
        """Record a message filtered by priority contacts."""
        self.priority_filtered += 1

    def record_snooze_dropped(self):
        """Record a message dropped due to snooze."""
        self.snooze_dropped += 1

    def record_snooze_queued(self):
        """Record a message queued due to snooze."""
        self.snooze_queued += 1

    def uptime(self) -> str:
        """Get uptime string."""
        uptime_seconds = int(time.time() - self.start_time)
        hours = uptime_seconds // 3600
        minutes = (uptime_seconds % 3600) // 60
        return f"{hours}h {minutes}m"

    def should_log_heartbeat(self) -> bool:
        """Check if hourly heartbeat should be logged."""
        return (time.time() - self.last_heartbeat) >= 3600

    def log_heartbeat(self, logger, state=None):
        """Log heartbeat with metrics."""
        total_alerts = sum(self.alerts_sent.values())
        logger.info(f"=== Heartbeat ===")
        logger.info(f"Uptime: {self.uptime()}")
        logger.info(f"Messages received: {self.messages_received}")
        logger.info(f"Alerts sent: {total_alerts} (DM: {self.alerts_sent['DM']}, Mention: {self.alerts_sent['Mention']}, Reply: {self.alerts_sent['Reply']})")
        logger.info(f"Deduplication hits: {self.dedup_hits}")

        # Priority and snooze stats
        if self.priority_filtered > 0:
            logger.info(f"Priority filtered: {self.priority_filtered}")
        if self.snooze_dropped > 0 or self.snooze_queued > 0:
            logger.info(f"Snooze: dropped={self.snooze_dropped}, queued={self.snooze_queued}")

        # Current state
        if state:
            if state.priority_mode != 'disabled':
                logger.info(f"Priority mode: {state.priority_mode}")
            if state.snooze_active:
                remaining = state.snooze_remaining_seconds()
                if remaining:
                    logger.info(f"Snooze active: {remaining/60:.1f}m remaining, queue={state.get_queue_size()}")

        self.last_heartbeat = time.time()


class TelegramPriorityNotifier:
    """Main application class."""

    def __init__(self):
        """Initialize the application."""
        self.config = None
        self.auth_manager = None
        self.client = None  # User client for monitoring
        self.bot_client = None  # Bot client for commands
        self.trigger_engine = None
        self.formatter = None
        self.notifier = None
        self.state = None
        self.command_handler = None
        self.user_id = None
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
        self.user_id = me.id
        username = me.username

        self.logger.info(f"Authenticated as: {me.first_name} (@{username}) [ID: {self.user_id}]")

        # Initialize components
        self.trigger_engine = TriggerEngine(self.user_id, username, self.config.chat_id)
        self.formatter = AlertFormatter()
        self.notifier = NotificationSink(self.config.bot_token, self.config.chat_id)

        # Initialize command handler
        self.command_handler = CommandHandler(
            self.state,
            self.notifier,
            self.client,
            self.user_id
        )

        # Check for expired snooze and deliver queued alerts
        await self._check_startup_snooze()

        # Register message handler for incoming messages (alerts)
        @self.client.on(events.NewMessage(incoming=True))
        async def message_handler(event):
            await self.handle_message(event)

        # Initialize and start bot client for receiving commands
        self.bot_client = TelegramClient(
            'bot_session',
            self.config.api_id,
            self.config.api_hash
        )
        await self.bot_client.start(bot_token=self.config.bot_token)
        self.logger.info("✓ Bot client connected for commands")

        # Register bot command handler
        @self.bot_client.on(events.NewMessage(chats=self.config.chat_id))
        async def bot_command_handler(event):
            await self.handle_bot_command(event)

        self.logger.info("✓ All components initialized successfully")
        self.logger.info(f"✓ Message listener registered (bot chat ID: {self.config.chat_id})")
        if self.state.priority_mode != 'disabled':
            self.logger.info(f"✓ Priority mode: {self.state.priority_mode}")
        self.logger.info("=" * 60)
        self.logger.info("System is now running. Press Ctrl+C to stop.")
        self.logger.info("=" * 60)

    async def _check_startup_snooze(self):
        """Check for expired snooze on startup and deliver queued alerts."""
        if self.state.snooze_queue:
            self.logger.info(f"Found {len(self.state.snooze_queue)} queued alerts from previous run")

            if not self.state.snooze_active:
                # Snooze expired, deliver queued alerts
                queued = self.state.snooze_queue.copy()
                self.state.snooze_queue = []
                self.state.save()

                delivered = 0
                for alert in queued:
                    try:
                        message = alert.get('message', '')
                        if message:
                            await self.notifier.send_alert(message)
                            delivered += 1
                    except Exception as e:
                        self.logger.error(f"Failed to deliver queued alert: {e}")

                self.logger.info(f"Delivered {delivered}/{len(queued)} queued alerts from previous session")

    async def handle_bot_command(self, event):
        """Handle commands sent to the bot.

        Args:
            event: Telethon NewMessage event from bot client
        """
        try:
            message = event.message
            # Only process commands (messages starting with /)
            if message.text and message.text.startswith('/'):
                self.logger.info(f"Bot command received: {message.text}")
                response = await self.command_handler.handle_command(
                    message.text,
                    self.user_id  # Commands are authorized for the owner
                )
                if response:
                    self.logger.info(f"Sending command response")
                    await self.notifier.send_alert(response)
        except Exception as e:
            self.logger.error(f"Error processing bot command: {e}", exc_info=True)

    async def handle_message(self, event):
        """Handle incoming message event.

        Args:
            event: Telethon NewMessage event
        """
        try:
            self.metrics.record_message()
            message = event.message

            # Step 1: Check snooze (before everything else)
            if self.state.is_snoozed():
                # Check trigger first to see if this is an alert-worthy message
                should_alert, trigger_type = await self.trigger_engine.should_alert(event)
                if should_alert:
                    if self.state.snooze_behavior == 'queue':
                        # Queue the alert
                        alert_message = await self.formatter.format_alert(event, trigger_type)
                        self.state.queue_alert({
                            'message': alert_message,
                            'trigger_type': trigger_type,
                            'chat_id': message.chat_id,
                            'message_id': message.id,
                        })
                        self.metrics.record_snooze_queued()
                        self.logger.debug(f"Queued alert for {trigger_type} (snooze active)")
                    else:
                        self.metrics.record_snooze_dropped()
                        self.logger.debug(f"Dropped alert for {trigger_type} (snooze active)")
                return

            # Step 2: Check priority contacts filter
            sender_id = message.sender_id or 0
            if not self.state.should_process_message(sender_id, message.chat_id):
                self.metrics.record_priority_filtered()
                self.logger.debug(f"Message from {sender_id} filtered by priority contacts")
                return

            # Step 3: Check trigger conditions
            should_alert, trigger_type = await self.trigger_engine.should_alert(event)

            if not should_alert:
                return

            # Step 4: Check deduplication
            if self.state.is_processed(message.chat_id, message.id):
                self.logger.debug(f"Message {message.chat_id}:{message.id} already processed, skipping")
                self.metrics.record_dedup_hit()
                return

            # Step 5: Format alert
            alert_message = await self.formatter.format_alert(event, trigger_type)

            # Step 6: Send alert
            success = await self.notifier.send_alert(alert_message)

            if success:
                # Mark as processed
                self.state.mark_processed(message.chat_id, message.id, trigger_type)
                self.metrics.record_alert(trigger_type)
                self.logger.info(f"Alert sent for {trigger_type} from chat {message.chat_id}")
            else:
                self.logger.error(f"Failed to send alert for {trigger_type} from chat {message.chat_id}")

        except Exception as e:
            self.logger.error(f"Error processing message: {e}", exc_info=True)

    async def run(self):
        """Run the main event loop."""
        await self.startup()

        # Main loop
        while self.running:
            try:
                # Periodic heartbeat logging
                if self.metrics.should_log_heartbeat():
                    self.metrics.log_heartbeat(self.logger, self.state)

                # Periodic state cleanup
                if self.state.should_cleanup():
                    self.logger.info("Running periodic state cleanup...")
                    self.state.cleanup_old_entries()

                # Check snooze expiration and deliver queued alerts
                if self.state.check_snooze_expired():
                    await self._deliver_snooze_queue()

                await asyncio.sleep(60)  # Check every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def _deliver_snooze_queue(self):
        """Deliver queued alerts when snooze expires."""
        if self.state.snooze_queue:
            queued = self.state.snooze_queue.copy()
            self.state.snooze_queue = []
            self.state.save()

            self.logger.info(f"Snooze expired, delivering {len(queued)} queued alerts")
            delivered = 0
            for alert in queued:
                try:
                    message = alert.get('message', '')
                    if message:
                        await self.notifier.send_alert(message)
                        delivered += 1
                except Exception as e:
                    self.logger.error(f"Failed to deliver queued alert: {e}")

            self.logger.info(f"Delivered {delivered}/{len(queued)} queued alerts")

    async def shutdown(self):
        """Graceful shutdown."""
        self.logger.info("=" * 60)
        self.logger.info("Shutting down...")
        self.logger.info("=" * 60)

        self.running = False

        # Log final metrics
        self.metrics.log_heartbeat(self.logger, self.state)

        # Save state
        if self.state:
            self.state.save()
            self.logger.info("✓ State saved")

        # Disconnect from Telegram
        if self.bot_client:
            await self.bot_client.disconnect()
            self.logger.info("✓ Bot client disconnected")

        if self.auth_manager:
            await self.auth_manager.disconnect()
            self.logger.info("✓ User client disconnected")

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
