"""
CLI utility tool for generating MTProto Pyrogram sessions.

Provides interactive terminal authorization for new Telegram user accounts,
saving .session files directly into the sessions/ directory.
"""

from pathlib import Path
import re
from typing import Final, Optional
from pyrogram import Client
from config.settings import API_HASH, API_ID
from core.logger_setup import setup_logger

logger = setup_logger(__name__)

# Base directory where session files must be stored
SESSIONS_DIR: Final[Path] = Path(__file__).resolve().parent.parent / "sessions"


def sanitize_session_name(raw_name: str) -> str:
    """Sanitize the session name by stripping file extensions and non-alphanumeric characters.

    Args:
        raw_name: The user-supplied raw session name string.

    Returns:
        str: Sanitized session identifier string.

    Raises:
        ValueError: If the session name is empty or contains no valid alphanumeric characters.
    """
    cleaned = raw_name.strip()
    if cleaned.endswith(".session"):
        cleaned = cleaned[:-8].strip()

    # Must contain at least one alphanumeric character
    if not cleaned or not re.search(r"[a-zA-Z0-9]", cleaned):
        raise ValueError("Session name must contain alphanumeric characters.")

    # Replace special characters and spaces with underscores
    sanitized = re.sub(r"[^a-zA-Z0-9_\-]", "_", cleaned)
    if not sanitized or not re.search(r"[a-zA-Z0-9]", sanitized):
        raise ValueError("Session name must contain alphanumeric characters.")

    return sanitized


def create_new_session(session_name: Optional[str] = None) -> str:
    """Interactively authenticate a new Pyrogram user account and save the session.

    Prompts the user via terminal for phone number and Telegram OTP, saving
    the resulting credentials to sessions/<session_name>.session.

    Args:
        session_name: Optional pre-defined session identifier string.

    Returns:
        str: Sanitized name of the successfully created session.
    """
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    if not session_name:
        user_input = input("Enter a name for the new session: ")
        session_name = sanitize_session_name(user_input)
    else:
        session_name = sanitize_session_name(session_name)

    print(f"\n[+] Initializing authorization for session: '{session_name}'")
    print(f"[+] Session file destination: {SESSIONS_DIR / f'{session_name}.session'}\n")

    app = Client(
        name=session_name,
        api_id=API_ID,
        api_hash=API_HASH,
        workdir=str(SESSIONS_DIR),
    )

    with app:
        me = app.get_me()
        user_display = f"@{me.username}" if me.username else f"ID:{me.id}"
        print(f"\n[✓] Session successfully authorized as: {me.first_name} ({user_display})")
        logger.info("Created and authorized new session '%s' for user %s", session_name, user_display)

    return session_name


if __name__ == "__main__":
    try:
        create_new_session()
    except Exception as exc:
        print(f"\n[!] Session creation failed: {exc}")
        logger.error("Session creation failed: %s", exc, exc_info=True)
