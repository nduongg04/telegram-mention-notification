"""Notification sink for alert delivery.

Sends formatted alerts via Telegram Bot API with retry logic and rate limiting.
"""

import logging
import asyncio
import aiohttp
from typing import Optional

logger = logging.getLogger(__name__)


class NotificationSink:
    """Handles alert delivery via Telegram Bot API."""

    def __init__(self, bot_token: str, chat_id: int):
        """Initialize notification sink.

        Args:
            bot_token: Telegram Bot API token
            chat_id: Chat ID to send notifications to
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        self.last_alert_time = 0
        self.min_alert_interval = 1.0  # Minimum 1 second between alerts

    async def send_alert(self, formatted_message: str, max_retries: int = 3) -> bool:
        """Send alert via Bot API with retry logic.

        Args:
            formatted_message: Formatted alert message
            max_retries: Maximum number of retry attempts (default: 3)

        Returns:
            True if alert was sent successfully, False otherwise
        """
        # Rate limiting: ensure minimum interval between alerts
        await self._rate_limit()

        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    payload = {
                        "chat_id": self.chat_id,
                        "text": formatted_message,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True
                    }

                    async with session.post(self.api_url, json=payload) as response:
                        if response.status == 200:
                            logger.info("Alert sent successfully via Bot API")
                            self.last_alert_time = asyncio.get_event_loop().time()
                            return True

                        result = await response.json()

                        # Rate limit hit (error code 429)
                        if response.status == 429:
                            retry_after = result.get("parameters", {}).get("retry_after", 5)
                            logger.warning(f"Rate limit hit, waiting {retry_after} seconds (attempt {attempt + 1}/{max_retries})")

                            if attempt < max_retries - 1:
                                await asyncio.sleep(retry_after)
                            else:
                                logger.error(f"Failed to send alert after {max_retries} attempts due to rate limiting")
                                return False
                        else:
                            logger.error(f"Bot API error: {result.get('description', 'Unknown error')} (attempt {attempt + 1}/{max_retries})")

                            if attempt < max_retries - 1:
                                wait_time = 2 ** attempt
                                logger.info(f"Retrying in {wait_time} seconds...")
                                await asyncio.sleep(wait_time)
                            else:
                                logger.error(f"Failed to send alert after {max_retries} attempts")
                                return False

            except aiohttp.ClientError as e:
                logger.error(f"Network error: {e} (attempt {attempt + 1}/{max_retries})")

                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed to send alert after {max_retries} attempts")
                    return False

            except Exception as e:
                logger.error(f"Unexpected error sending alert: {e} (attempt {attempt + 1}/{max_retries})")

                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed to send alert after {max_retries} attempts")
                    return False

        return False

    async def _rate_limit(self):
        """Ensure minimum interval between alerts (anti-spam)."""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self.last_alert_time

        if time_since_last < self.min_alert_interval:
            wait_time = self.min_alert_interval - time_since_last
            logger.debug(f"Rate limiting: waiting {wait_time:.2f} seconds")
            await asyncio.sleep(wait_time)
