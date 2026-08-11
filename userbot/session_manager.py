"""
Session manager module for MTProto userbot accounts.

Discovers and validates saved Pyrogram session files in the sessions/ directory.
"""

import os
from pathlib import Path
from typing import Final, Optional
from core.logger_setup import setup_logger

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


def get_available_sessions() -> list[str]:
    """Scan the sessions directory and retrieve names of all valid Pyrogram sessions.

    Returns:
        list[str]: Sorted list of session identifiers (without the .session file extension).
    """
    if not os.path.exists(SESSIONS_DIR):
        logger.warning("Sessions directory '%s' does not exist.", SESSIONS_DIR)
        return []

    try:
        session_names: list[str] = []
        for filename in os.listdir(SESSIONS_DIR):
            if filename.endswith(".session") and not filename.endswith(".session-journal"):
                session_name = filename[:-8]  # Strip '.session'
                if session_name.strip():
                    session_names.append(session_name.strip())

        session_names.sort()
        logger.info("Found %d available userbot session(s): %s", len(session_names), session_names)
        return session_names
    except OSError as exc:
        logger.error("Error accessing sessions directory '%s': %s", SESSIONS_DIR, exc, exc_info=True)
        return []


def delete_session(session_name: str) -> bool:
    """Safely delete a Pyrogram session file and its SQLite journal from the sessions directory.

    If the deleted session is the currently active session, resets _active_session to None.

    Args:
        session_name: Name of the session to delete (with or without .session extension).

    Returns:
        bool: True if deletion succeeded, False otherwise.
    """
    global _active_session
    clean_name = session_name.strip()
    if clean_name.endswith(".session"):
        clean_name = clean_name[:-8]

    if not clean_name:
        logger.warning("Attempted to delete an empty session name.")
        return False

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
