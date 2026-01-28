"""Notification sink for alert delivery.

Sends formatted alerts via Telegram Bot API with retry logic and rate limiting.
"""

import logging
import asyncio
import aiohttp
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from telethon import TelegramClient
    from telethon.tl.types import Document

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
        self.api_base = f"https://api.telegram.org/bot{bot_token}"
        self.api_url = f"{self.api_base}/sendMessage"
        self.sticker_url = f"{self.api_base}/sendSticker"
        self.animation_url = f"{self.api_base}/sendAnimation"
        self.photo_url = f"{self.api_base}/sendPhoto"
        self.video_url = f"{self.api_base}/sendVideo"
        self.document_url = f"{self.api_base}/sendDocument"
        self.last_alert_time = 0
        self.min_alert_interval = 1.0  # Minimum 1 second between alerts
        self.user_client: Optional["TelegramClient"] = None

    def set_user_client(self, client: "TelegramClient"):
        """Set user client for forwarding media messages.

        Args:
            client: Telethon user client
        """
        self.user_client = client

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

    async def send_media_alert(
        self,
        event,
        caption: str,
        max_retries: int = 3
    ) -> bool:
        """Send alert with media embedded in the notification.

        Downloads media via user client and uploads via Bot API.

        Args:
            event: Telethon NewMessage event containing media
            caption: Formatted caption text (HTML)
            max_retries: Maximum number of retry attempts

        Returns:
            True if alert was sent successfully, False otherwise
        """
        if not self.user_client:
            logger.warning("User client not set, falling back to text-only alert")
            return await self.send_alert(caption, max_retries)

        await self._rate_limit()

        message = event.message
        media = message.media

        from telethon.tl.types import (
            MessageMediaPhoto,
            MessageMediaDocument,
        )

        # Determine media type
        if isinstance(media, MessageMediaDocument):
            doc = media.document
            media_type = self._get_document_type(doc)

            if media_type == 'sticker':
                return await self._send_sticker_alert(message, caption, max_retries)
            elif media_type == 'gif':
                return await self._send_animation_alert(message, caption, max_retries)
            elif media_type == 'video':
                return await self._send_video_alert(message, caption, max_retries)
            else:
                return await self._send_document_alert(message, caption, max_retries)

        elif isinstance(media, MessageMediaPhoto):
            return await self._send_photo_alert(message, caption, max_retries)

        # Fallback to text-only
        logger.warning("Unknown media type, sending text-only alert")
        return await self.send_alert(caption + "\n\n<i>[Media type not supported]</i>", max_retries)

    def _get_document_type(self, doc) -> str:
        """Determine the type of document.

        Args:
            doc: Telethon Document object

        Returns:
            Type string: 'sticker', 'gif', 'video', or 'document'
        """
        for attr in doc.attributes:
            attr_name = type(attr).__name__
            if attr_name == 'DocumentAttributeSticker':
                return 'sticker'
            elif attr_name == 'DocumentAttributeAnimated':
                return 'gif'
            elif attr_name == 'DocumentAttributeVideo':
                # Check if it's a GIF (animated video)
                for a in doc.attributes:
                    if type(a).__name__ == 'DocumentAttributeAnimated':
                        return 'gif'
                return 'video'

        # Check mime type as fallback
        if doc.mime_type == 'image/gif':
            return 'gif'

        return 'document'

    async def _send_sticker_alert(
        self,
        message,
        caption: str,
        max_retries: int = 3
    ) -> bool:
        """Send sticker via Bot API by downloading and re-uploading.

        Stickers don't support captions, so we send caption first, then sticker.

        Args:
            message: Telethon Message object
            caption: Formatted caption text (HTML)
            max_retries: Maximum retry attempts

        Returns:
            True if sent successfully
        """
        # Send caption first (stickers don't support captions)
        caption_sent = await self.send_alert(caption, max_retries)
        if not caption_sent:
            return False

        for attempt in range(max_retries):
            try:
                # Download sticker to bytes
                sticker_bytes = await self.user_client.download_media(message.media, bytes)
                if not sticker_bytes:
                    logger.warning("Failed to download sticker")
                    return True  # Caption was sent

                # Get file extension from document
                doc = message.media.document
                ext = '.webp'  # Default sticker format
                for attr in doc.attributes:
                    if type(attr).__name__ == 'DocumentAttributeFilename':
                        ext = '.' + attr.file_name.split('.')[-1] if '.' in attr.file_name else ext
                        break

                async with aiohttp.ClientSession() as session:
                    form = aiohttp.FormData()
                    form.add_field('chat_id', str(self.chat_id))
                    form.add_field('sticker', sticker_bytes,
                                   filename=f'sticker{ext}',
                                   content_type='image/webp')

                    async with session.post(self.sticker_url, data=form) as response:
                        if response.status == 200:
                            logger.info("Sticker alert sent successfully via Bot API")
                            self.last_alert_time = asyncio.get_event_loop().time()
                            return True

                        result = await response.json()
                        logger.error(f"Bot API error sending sticker: {result.get('description', 'Unknown error')}")

                        if response.status == 429:
                            retry_after = result.get("parameters", {}).get("retry_after", 5)
                            if attempt < max_retries - 1:
                                await asyncio.sleep(retry_after)
                            continue

                        if attempt < max_retries - 1:
                            await asyncio.sleep(2 ** attempt)

            except Exception as e:
                logger.error(f"Error sending sticker: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        return True  # Caption was sent successfully

    async def _send_animation_alert(
        self,
        message,
        caption: str,
        max_retries: int = 3
    ) -> bool:
        """Send animation/GIF via Bot API by downloading and re-uploading.

        Args:
            message: Telethon Message object
            caption: Formatted caption text (HTML)
            max_retries: Maximum retry attempts

        Returns:
            True if sent successfully
        """
        for attempt in range(max_retries):
            try:
                # Download animation to bytes
                anim_bytes = await self.user_client.download_media(message.media, bytes)
                if not anim_bytes:
                    logger.warning("Failed to download animation")
                    return await self.send_alert(caption + "\n\n<i>[GIF]</i>", max_retries)

                # Get filename/extension
                doc = message.media.document
                filename = 'animation.mp4'
                content_type = doc.mime_type or 'video/mp4'
                for attr in doc.attributes:
                    if type(attr).__name__ == 'DocumentAttributeFilename':
                        filename = attr.file_name
                        break

                async with aiohttp.ClientSession() as session:
                    form = aiohttp.FormData()
                    form.add_field('chat_id', str(self.chat_id))
                    form.add_field('animation', anim_bytes,
                                   filename=filename,
                                   content_type=content_type)
                    form.add_field('caption', caption)
                    form.add_field('parse_mode', 'HTML')

                    async with session.post(self.animation_url, data=form) as response:
                        if response.status == 200:
                            logger.info("Animation alert sent successfully via Bot API")
                            self.last_alert_time = asyncio.get_event_loop().time()
                            return True

                        result = await response.json()
                        logger.error(f"Bot API error sending animation: {result.get('description', 'Unknown error')}")

                        if response.status == 429:
                            retry_after = result.get("parameters", {}).get("retry_after", 5)
                            if attempt < max_retries - 1:
                                await asyncio.sleep(retry_after)
                            continue

                        if attempt < max_retries - 1:
                            await asyncio.sleep(2 ** attempt)

            except Exception as e:
                logger.error(f"Error sending animation: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        return await self.send_alert(caption + "\n\n<i>[GIF could not be sent]</i>", max_retries)

    async def _send_photo_alert(
        self,
        message,
        caption: str,
        max_retries: int = 3
    ) -> bool:
        """Send photo via Bot API by downloading and re-uploading.

        Args:
            message: Telethon Message object
            caption: Formatted caption text (HTML)
            max_retries: Maximum retry attempts

        Returns:
            True if sent successfully
        """
        for attempt in range(max_retries):
            try:
                # Download photo to bytes
                photo_bytes = await self.user_client.download_media(message.media, bytes)
                if not photo_bytes:
                    logger.warning("Failed to download photo")
                    return await self.send_alert(caption + "\n\n<i>[Photo]</i>", max_retries)

                async with aiohttp.ClientSession() as session:
                    form = aiohttp.FormData()
                    form.add_field('chat_id', str(self.chat_id))
                    form.add_field('photo', photo_bytes,
                                   filename='photo.jpg',
                                   content_type='image/jpeg')
                    form.add_field('caption', caption)
                    form.add_field('parse_mode', 'HTML')

                    async with session.post(self.photo_url, data=form) as response:
                        if response.status == 200:
                            logger.info("Photo alert sent successfully via Bot API")
                            self.last_alert_time = asyncio.get_event_loop().time()
                            return True

                        result = await response.json()
                        logger.error(f"Bot API error sending photo: {result.get('description', 'Unknown error')}")

                        if attempt < max_retries - 1:
                            await asyncio.sleep(2 ** attempt)

            except Exception as e:
                logger.error(f"Error sending photo: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        return await self.send_alert(caption + "\n\n<i>[Photo could not be sent]</i>", max_retries)

    async def _send_video_alert(
        self,
        message,
        caption: str,
        max_retries: int = 3
    ) -> bool:
        """Send video via Bot API by downloading and re-uploading.

        Args:
            message: Telethon Message object
            caption: Formatted caption text (HTML)
            max_retries: Maximum retry attempts

        Returns:
            True if sent successfully
        """
        for attempt in range(max_retries):
            try:
                # Download video to bytes
                video_bytes = await self.user_client.download_media(message.media, bytes)
                if not video_bytes:
                    logger.warning("Failed to download video")
                    return await self.send_alert(caption + "\n\n<i>[Video]</i>", max_retries)

                # Get filename/extension
                doc = message.media.document
                filename = 'video.mp4'
                content_type = doc.mime_type or 'video/mp4'
                for attr in doc.attributes:
                    if type(attr).__name__ == 'DocumentAttributeFilename':
                        filename = attr.file_name
                        break

                async with aiohttp.ClientSession() as session:
                    form = aiohttp.FormData()
                    form.add_field('chat_id', str(self.chat_id))
                    form.add_field('video', video_bytes,
                                   filename=filename,
                                   content_type=content_type)
                    form.add_field('caption', caption)
                    form.add_field('parse_mode', 'HTML')

                    async with session.post(self.video_url, data=form) as response:
                        if response.status == 200:
                            logger.info("Video alert sent successfully via Bot API")
                            self.last_alert_time = asyncio.get_event_loop().time()
                            return True

                        result = await response.json()
                        logger.error(f"Bot API error sending video: {result.get('description', 'Unknown error')}")

                        if attempt < max_retries - 1:
                            await asyncio.sleep(2 ** attempt)

            except Exception as e:
                logger.error(f"Error sending video: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        return await self.send_alert(caption + "\n\n<i>[Video could not be sent]</i>", max_retries)

    async def _send_document_alert(
        self,
        message,
        caption: str,
        max_retries: int = 3
    ) -> bool:
        """Send document via Bot API by downloading and re-uploading.

        Args:
            message: Telethon Message object
            caption: Formatted caption text (HTML)
            max_retries: Maximum retry attempts

        Returns:
            True if sent successfully
        """
        for attempt in range(max_retries):
            try:
                # Download document to bytes
                doc_bytes = await self.user_client.download_media(message.media, bytes)
                if not doc_bytes:
                    logger.warning("Failed to download document")
                    return await self.send_alert(caption + "\n\n<i>[Document]</i>", max_retries)

                # Get filename
                doc = message.media.document
                filename = 'document'
                content_type = doc.mime_type or 'application/octet-stream'
                for attr in doc.attributes:
                    if type(attr).__name__ == 'DocumentAttributeFilename':
                        filename = attr.file_name
                        break

                async with aiohttp.ClientSession() as session:
                    form = aiohttp.FormData()
                    form.add_field('chat_id', str(self.chat_id))
                    form.add_field('document', doc_bytes,
                                   filename=filename,
                                   content_type=content_type)
                    form.add_field('caption', caption)
                    form.add_field('parse_mode', 'HTML')

                    async with session.post(self.document_url, data=form) as response:
                        if response.status == 200:
                            logger.info("Document alert sent successfully via Bot API")
                            self.last_alert_time = asyncio.get_event_loop().time()
                            return True

                        result = await response.json()
                        logger.error(f"Bot API error sending document: {result.get('description', 'Unknown error')}")

                        if attempt < max_retries - 1:
                            await asyncio.sleep(2 ** attempt)

            except Exception as e:
                logger.error(f"Error sending document: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        return await self.send_alert(caption + "\n\n<i>[Document could not be sent]</i>", max_retries)
