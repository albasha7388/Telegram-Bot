"""
Centralized configuration and settings module for the Hybrid Telegram System.

This module securely loads environment variables, validates Telegram API credentials,
and defines global operational constants according to system safety protocols.
"""

import os
from typing import Any, Final, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def _get_required_env(var_name: str) -> str:
    """Retrieve an environment variable or raise an explicit ValueError if not set.

    Args:
        var_name: The name of the environment variable.

    Returns:
        The stripped string value of the environment variable.

    Raises:
        ValueError: If the environment variable is missing, None, or empty.
    """
    value: str | None = os.getenv(var_name)
    if value is None or not value.strip():
        raise ValueError(f"Required environment variable '{var_name}' is missing or empty.")
    return value.strip()


def get_api_id() -> int:
    """Retrieve and validate the Telegram API_ID environment variable.

    Returns:
        The Telegram API ID as an integer.

    Raises:
        ValueError: If API_ID is missing, empty, or not a valid integer.
    """
    raw_id: str = _get_required_env("API_ID")
    try:
        return int(raw_id)
    except ValueError as exc:
        raise ValueError(
            f"Environment variable 'API_ID' must be a valid integer, got '{raw_id}'."
        ) from exc


def get_api_hash() -> str:
    """Retrieve and validate the Telegram API_HASH environment variable.

    Returns:
        The Telegram API Hash string.

    Raises:
        ValueError: If API_HASH is missing or empty.
    """
    return _get_required_env("API_HASH")


def get_bot_token() -> str:
    """Retrieve and validate the Telegram BOT_TOKEN environment variable.

    Returns:
        The Telegram Bot Token string.

    Raises:
        ValueError: If BOT_TOKEN is missing or empty.
    """
    return _get_required_env("BOT_TOKEN")


def get_admin_id() -> Optional[int]:
    """Retrieve optional Telegram ADMIN_ID environment variable.

    Returns:
        Optional[int]: The admin Telegram user ID if configured; None otherwise.
    """
    raw_id = os.getenv("ADMIN_ID")
    if raw_id and raw_id.strip():
        try:
            return int(raw_id.strip())
        except ValueError:
            return None
    return None


def get_archive_channel_id() -> Optional[int]:
    """Retrieve optional Telegram ARCHIVE_CHANNEL_ID environment variable.

    Returns:
        Optional[int]: The archive Telegram channel ID if configured; None otherwise.
    """
    raw_id = os.getenv("ARCHIVE_CHANNEL_ID")
    if raw_id and raw_id.strip():
        try:
            return int(raw_id.strip())
        except ValueError:
            return None
    return None


# System Constants
MAX_DAILY_DMS: Final[int] = 20
LINKS_PER_FILE: Final[int] = 100
TIME_SLEEP_MIN: Final[int] = 5
TIME_SLEEP_MAX: Final[int] = 12


def __getattr__(name: str) -> Any:
    """Dynamically resolve credential attributes and validate on access.

    Args:
        name: The attribute name being accessed on the module.

    Returns:
        The resolved configuration value.

    Raises:
        ValueError: If the requested credential environment variable is missing or invalid.
        AttributeError: If the requested attribute name is not defined on the module.
    """
    if name == "API_ID":
        return get_api_id()
    if name == "API_HASH":
        return get_api_hash()
    if name == "BOT_TOKEN":
        return get_bot_token()
    if name == "ADMIN_ID":
        return get_admin_id()
    if name == "ARCHIVE_CHANNEL_ID":
        return get_archive_channel_id()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
