"""Authentication manager for Telegram.

Handles MTProto authentication, session management, and reconnection.
"""

import os
import logging
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

logger = logging.getLogger(__name__)


class AuthManager:
    """Manages Telegram authentication and session persistence."""

    def __init__(self, api_id: int, api_hash: str, phone: str, session_file: str):
        """Initialize authentication manager.

        Args:
            api_id: Telegram API ID
            api_hash: Telegram API Hash
            phone: User phone number
            session_file: Path to session file
        """
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.session_file = session_file
        self.client: TelegramClient = None

    async def connect(self) -> TelegramClient:
        """Connect to Telegram and authenticate.

        Returns:
            Authenticated TelegramClient instance

        Raises:
            Exception: If authentication fails
        """
        logger.info("Initializing Telegram client...")

        # Create client with session file
        self.client = TelegramClient(self.session_file, self.api_id, self.api_hash)

        # Connect to Telegram
        await self.client.connect()

        # Check if already authorized
        if not await self.client.is_user_authorized():
            logger.info("Not authorized, starting authentication flow...")
            await self._authenticate()
        else:
            logger.info("Session loaded successfully, already authorized")

        # Set session file permissions to 0600
        self._set_session_permissions()

        logger.info("Successfully connected to Telegram")
        return self.client

    async def _authenticate(self):
        """Perform interactive authentication flow."""
        try:
            # Request phone code
            await self.client.send_code_request(self.phone)
            logger.info(f"Code sent to {self.phone}")

            # Prompt for code
            code = input("Enter the code you received: ")

            try:
                # Sign in with code
                await self.client.sign_in(self.phone, code)
                logger.info("Authentication successful")

            except SessionPasswordNeededError:
                # 2FA is enabled, prompt for password
                logger.info("2FA is enabled")
                password = input("Enter your 2FA password: ")
                await self.client.sign_in(password=password)
                logger.info("2FA authentication successful")

        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise

    def _set_session_permissions(self):
        """Set session file permissions to 0600 (owner read/write only)."""
        session_files = [
            f"{self.session_file}.session",
            f"{self.session_file}.session-journal"
        ]

        for file_path in session_files:
            if os.path.exists(file_path):
                try:
                    os.chmod(file_path, 0o600)
                    logger.debug(f"Set permissions for {file_path} to 0600")
                except Exception as e:
                    logger.warning(f"Failed to set permissions for {file_path}: {e}")

    async def disconnect(self):
        """Disconnect from Telegram gracefully."""
        if self.client and self.client.is_connected():
            logger.info("Disconnecting from Telegram...")
            await self.client.disconnect()
            logger.info("Disconnected successfully")

    def get_client(self) -> TelegramClient:
        """Get the authenticated Telegram client.

        Returns:
            TelegramClient instance

        Raises:
            RuntimeError: If not connected
        """
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")
        return self.client
