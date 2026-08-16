"""
Session manager module for MTProto userbot accounts.

Discovers and validates saved Pyrogram session files in the sessions/ directory.
"""

import os
from pathlib import Path
from typing import Final, Optional
from dotenv import load_dotenv
from core.logger_setup import setup_logger

# Ensure environment variables are loaded
load_dotenv()

logger = setup_logger(__name__)

# Base directory where Pyrogram .session files are stored
SESSIONS_DIR: Final[Path] = Path(__file__).resolve().parent.parent / "sessions"

# Global tracking of active userbot session
_active_session: Optional[str] = None


def get_active_session() -> Optional[str]:
    """Retrieve the global active session identifier.

    Returns:
        Optional[str]: Name of the currently active session, or None if unassigned.
    """
    return _active_session


def set_active_session(session_name: Optional[str]) -> None:
    """Set the global active session identifier.

    Args:
        session_name: Chosen session identifier or None to clear.
    """
    global _active_session
    _active_session = session_name
    logger.info("Global active userbot session updated to: %s", session_name)


def get_session_string(session_name: str) -> Optional[str]:
    """Retrieve Pyrogram StringSession from environment variables if present.

    Checks os.environ for matching keys such as SESSION_{NAME}, SESSION_{NAME.upper()},
    or case-insensitive matches.

    Args:
        session_name: The session identifier to search for.

    Returns:
        Optional[str]: The session string if found in environment variables; None otherwise.
    """
    clean_name = session_name.strip()
    if clean_name.endswith(".session"):
        clean_name = clean_name[:-8]

    if not clean_name:
        return None

    # 1. Direct candidate lookups
    target_key = clean_name if clean_name.upper().startswith("SESSION_") else f"SESSION_{clean_name}"
    val = os.getenv(target_key) or os.getenv(target_key.upper()) or os.getenv(target_key.lower())
    if val and val.strip():
        return val.strip()

    # 2. Case-insensitive scan over os.environ
    target_upper = target_key.upper()
    direct_upper = clean_name.upper()
    for k, v in os.environ.items():
        if k.upper() in (target_upper, direct_upper) and v and str(v).strip():
            return str(v).strip()

    return None


def is_env_session(session_name: str) -> bool:
    """Check whether a session is defined via environment variables.

    Args:
        session_name: The session identifier.

    Returns:
        bool: True if the session is backed by an environment variable, False otherwise.
    """
    return get_session_string(session_name) is not None


def get_available_sessions() -> list[str]:
    """Scan environment variables and the sessions directory for valid Pyrogram sessions.

    Discovers sessions loaded from environment variables (keys starting with 'SESSION_')
    and merges them with local .session files stored in SESSIONS_DIR, ensuring deduplication.

    Returns:
        list[str]: Sorted list of unique session identifiers.
    """
    session_names_set: set[str] = set()
    env_sessions: list[str] = []

    # 1. Discover sessions from environment variables (e.g., SESSION_ACCOUNT_1 -> ACCOUNT_1)
    for key, val in os.environ.items():
        if key.upper().startswith("SESSION_") and len(key) > len("SESSION_") and val and str(val).strip():
            derived_name = key[len("SESSION_"):].strip()
            if derived_name:
                env_sessions.append(derived_name)
                session_names_set.add(derived_name)

    logger.info(f"Loaded env sessions: {env_sessions}")

    # 2. Discover sessions from local filesystem
    local_sessions: list[str] = []
    if os.path.exists(SESSIONS_DIR):
        try:
            for filename in os.listdir(SESSIONS_DIR):
                if filename.endswith(".session") and not filename.endswith(".session-journal"):
                    session_name = filename[:-8].strip()  # Strip '.session'
                    if session_name:
                        local_sessions.append(session_name)
                        session_names_set.add(session_name)
        except OSError as exc:
            logger.error("Error accessing sessions directory '%s': %s", SESSIONS_DIR, exc, exc_info=True)

    session_names = sorted(session_names_set)
    logger.info("Found %d available userbot session(s): %s", len(session_names), session_names)
    return session_names


def delete_session(session_name: str) -> bool:
    """Safely delete a Pyrogram session file and its SQLite journal from the sessions directory.

    If the deleted session is the currently active session, resets _active_session to None.
    If the session is defined via environment variables, safely prevents filesystem deletion.

    Args:
        session_name: Name of the session to delete (with or without .session extension).

    Returns:
        bool: True if deletion succeeded or was gracefully handled, False otherwise.
    """
    global _active_session
    clean_name = session_name.strip()
    if clean_name.endswith(".session"):
        clean_name = clean_name[:-8]

    if not clean_name:
        logger.warning("Attempted to delete an empty session name.")
        return False

    if is_env_session(clean_name):
        logger.info("Session '%s' is an environment-based session; skipping file deletion.", clean_name)
        if _active_session == clean_name:
            _active_session = None
            logger.info("Reset global active session to None after removing active env session '%s'.", clean_name)
        return True

    session_path = SESSIONS_DIR / f"{clean_name}.session"
    journal_path = SESSIONS_DIR / f"{clean_name}.session-journal"

    if not session_path.exists():
        logger.warning("Attempted to delete non-existent session file '%s'.", session_path)
        return False

    try:
        os.remove(session_path)
        if journal_path.exists():
            try:
                os.remove(journal_path)
            except OSError as j_exc:
                logger.debug("Failed removing session journal '%s': %s", journal_path, j_exc)

        if _active_session == clean_name:
            _active_session = None
            logger.info("Reset global active session to None after deleting '%s'.", clean_name)

        logger.info("Successfully deleted session file for '%s'.", clean_name)
        return True
    except OSError as exc:
        logger.error("Error deleting session file '%s': %s", session_path, exc, exc_info=True)
        return False


def rename_session(old_name: str, new_name: str) -> bool:
    """Safely rename a Pyrogram session file and its SQLite journal.

    If the renamed session is currently active, updates _active_session to new_name.
    If the session is defined via environment variables, returns False as env sessions cannot be renamed on disk.

    Args:
        old_name: Existing session identifier.
        new_name: Desired new session identifier.

    Returns:
        bool: True if rename succeeded, False otherwise.
    """
    global _active_session
    clean_old = old_name.strip()
    if clean_old.endswith(".session"):
        clean_old = clean_old[:-8]

    clean_new = new_name.strip()
    if clean_new.endswith(".session"):
        clean_new = clean_new[:-8]

    if not clean_old or not clean_new:
        logger.warning("Invalid session names for rename: '%s' -> '%s'.", old_name, new_name)
        return False

    if is_env_session(clean_old):
        logger.warning("Session '%s' is an environment-based session and cannot be renamed.", clean_old)
        return False

    old_session_path = SESSIONS_DIR / f"{clean_old}.session"
    new_session_path = SESSIONS_DIR / f"{clean_new}.session"
    old_journal_path = SESSIONS_DIR / f"{clean_old}.session-journal"
    new_journal_path = SESSIONS_DIR / f"{clean_new}.session-journal"

    if not old_session_path.exists():
        logger.warning("Attempted to rename non-existent session file '%s'.", old_session_path)
        return False

    if new_session_path.exists() and clean_old != clean_new:
        logger.warning("Cannot rename '%s' to '%s': destination file already exists.", clean_old, clean_new)
        return False

    try:
        os.rename(old_session_path, new_session_path)
        if old_journal_path.exists():
            try:
                os.rename(old_journal_path, new_journal_path)
            except OSError as j_exc:
                logger.debug("Failed renaming session journal '%s': %s", old_journal_path, j_exc)

        if _active_session == clean_old:
            _active_session = clean_new
            logger.info("Updated global active session to '%s' after rename.", clean_new)

        logger.info("Successfully renamed session from '%s' to '%s'.", clean_old, clean_new)
        return True
    except OSError as exc:
        logger.error(
            "Error renaming session file '%s' -> '%s': %s",
            old_session_path,
            new_session_path,
            exc,
            exc_info=True,
        )
        return False
