"""Configuration loader for Telegram Priority Notifier.

Loads and validates environment variables for the application.
"""

import os
import sys
from typing import Optional
from dotenv import load_dotenv


class Config:
    """Application configuration loaded from environment variables."""

    def __init__(self):
        """Load and validate configuration from environment."""
        load_dotenv()

        # Required variables
        self.api_id: Optional[int] = self._get_int_env('TELEGRAM_API_ID', required=True)
        self.api_hash: Optional[str] = self._get_env('TELEGRAM_API_HASH', required=True)
        self.phone: Optional[str] = self._get_env('TELEGRAM_PHONE', required=True)

        # Bot configuration (required for notifications)
        self.bot_token: Optional[str] = self._get_env('TELEGRAM_BOT_TOKEN', required=True)
        self.chat_id: Optional[int] = self._get_int_env('TELEGRAM_CHAT_ID', required=True)

        # Optional variables with defaults
        self.session_file: str = self._get_env('SESSION_FILE', default='telegram_session.json')
        self.state_file: str = self._get_env('STATE_FILE', default='state.json')
        self.log_level: str = self._get_env('LOG_LEVEL', default='INFO').upper()

        # Validate log level
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.log_level not in valid_levels:
            print(f"Warning: Invalid LOG_LEVEL '{self.log_level}', defaulting to INFO")
            self.log_level = 'INFO'

    def _get_env(self, key: str, required: bool = False, default: Optional[str] = None) -> Optional[str]:
        """Get environment variable with validation."""
        value = os.getenv(key, default)

        if required and not value:
            print(f"Error: Required environment variable '{key}' is not set.", file=sys.stderr)
            print(f"Please set {key} in your .env file or environment.", file=sys.stderr)
            sys.exit(1)

        return value

    def _get_int_env(self, key: str, required: bool = False, default: Optional[int] = None) -> Optional[int]:
        """Get integer environment variable with validation."""
        value_str = self._get_env(key, required=False)

        if not value_str:
            if required:
                print(f"Error: Required environment variable '{key}' is not set.", file=sys.stderr)
                print(f"Please set {key} in your .env file or environment.", file=sys.stderr)
                sys.exit(1)
            return default

        try:
            return int(value_str)
        except ValueError:
            print(f"Error: Environment variable '{key}' must be an integer, got '{value_str}'", file=sys.stderr)
            sys.exit(1)

    def summary(self) -> str:
        """Return a summary of configuration (without sensitive data)."""
        return f"""Configuration Summary:
  API ID: {self.api_id} (set)
  API Hash: {'*' * 8} (set)
  Phone: {self.phone[:3]}...{self.phone[-2:]} (set)
  Bot Token: {'*' * 8} (set)
  Chat ID: {self.chat_id}
  Session File: {self.session_file}
  State File: {self.state_file}
  Log Level: {self.log_level}
"""


def load_config() -> Config:
    """Load and return application configuration."""
    return Config()
