"""
Process management module for asynchronous MTProto Userbot and Link Extraction execution.

Controls non-blocking task creation (asyncio.create_task), active background task
tracking, status inquiries, and graceful task cancellation across multiple user accounts.
"""

import asyncio
from datetime import datetime
from typing import Any, Final, Optional
from core.logger_setup import setup_logger
from userbot.client import run_userbot, stop_userbot_client
from userbot.extractor import run_extraction_task

logger = setup_logger(__name__)

# Registries mapping session names to their active background asyncio.Task instances
active_tasks: dict[str, asyncio.Task[Any]] = {}
active_extractions: dict[str, asyncio.Task[Any]] = {}
active_joiners: dict[str, asyncio.Task[Any]] = {}

# Registry mapping session names to their active sleep state: {"until": float, "conflict": bool}
joiner_sleep_state: dict[str, dict[str, Any]] = {}


def set_joiner_sleep_state(session_name: str, until: float, conflict: bool = False) -> None:
    """Set the sleep state for a session's Auto-Joiner.
    
    Args:
        session_name: Session identifier.
        until: Epoch timestamp when the sleep ends (0 to clear).
        conflict: True if yielding due to conflict.
    """
    if until <= 0:
        joiner_sleep_state.pop(session_name, None)
    else:
        joiner_sleep_state[session_name] = {"until": until, "conflict": conflict}


def get_joiner_sleep_state(session_name: str) -> Optional[dict[str, Any]]:
    """Get the current sleep state for a session's Auto-Joiner.
    
    Args:
        session_name: Session identifier.
        
    Returns:
        dict with 'until' and 'conflict' or None if not sleeping.
    """
    return joiner_sleep_state.get(session_name)



def is_joiner_running(session_name: Optional[str]) -> bool:
    """Check whether a background auto-joiner task is currently active for a session.

    Args:
        session_name: The session identifier to inspect.

    Returns:
        bool: True if the task exists and has not finished/cancelled; False otherwise.
    """
    if not session_name:
        return False
    task = active_joiners.get(session_name)
    return task is not None and not task.done()


def stop_joiner_task(session_name: str) -> bool:
    """Cancel and remove an active auto-joiner background task.

    Args:
        session_name: Target session identifier to stop.

    Returns:
        bool: True if task was found and cancelled; False otherwise.
    """
    task = active_joiners.pop(session_name, None)
    if task is None or task.done():
        logger.warning("Attempted to stop joiner task for '%s', but no active task found.", session_name)
        return False

    logger.info("Cancelling background auto-joiner task for session '%s'...", session_name)
    task.cancel()
    logger.info("Auto-joiner task for session '%s' cancelled and removed from active pool.", session_name)
    return True


def is_userbot_running(session_name: Optional[str]) -> bool:
    """Check whether a background auto-reply userbot task is currently active for a session.

    Args:
        session_name: The session identifier to inspect.

    Returns:
        bool: True if the task exists and has not finished/cancelled or client is connected; False otherwise.
    """
    if not session_name:
        return False
    from userbot.client import active_userbot_clients
    client = active_userbot_clients.get(session_name)
    if client is not None and getattr(client, "is_connected", False):
        return True
    task = active_tasks.get(session_name)
    return task is not None and not task.done()


def is_extraction_running(session_name: Optional[str]) -> bool:
    """Check whether a background link extraction task is currently active for a session.

    Args:
        session_name: The session identifier to inspect.

    Returns:
        bool: True if the task exists and has not finished/cancelled; False otherwise.
    """
    if not session_name:
        return False
    task = active_extractions.get(session_name)
    return task is not None and not task.done()


async def start_userbot_task(session_name: str) -> bool:
    """Launch the Pyrogram auto-reply userbot engine as a non-blocking background task.

    Args:
        session_name: The identifier of the MTProto session to activate.

    Returns:
        bool: True if a new task was successfully spawned; False if already running.
    """
    if is_userbot_running(session_name):
        logger.warning("Userbot task for session '%s' is already running.", session_name)
        return False

    logger.info("Spawning background auto-reply task for session '%s'...", session_name)
    task: asyncio.Task[Any] = asyncio.create_task(
        run_userbot(session_name),
        name=f"userbot_{session_name}",
    )
    active_tasks[session_name] = task
    logger.info("Userbot task for session '%s' successfully registered.", session_name)
    return True


async def stop_userbot_task(session_name: str) -> bool:
    """Safely stop Pyrogram client and cancel the active userbot background task.

    Args:
        session_name: The identifier of the session to terminate.

    Returns:
        bool: True if the task was found and cancellation was signaled; False if not running.
    """
    task = active_tasks.pop(session_name, None)
    from userbot.client import active_userbot_clients
    client = active_userbot_clients.get(session_name)

    if task is None and client is None:
        logger.warning("Attempted to stop userbot task for '%s', but no active task found.", session_name)
        return False

    # 1. Gracefully stop Pyrogram Client first to prevent PeerIdInvalid / update loop errors
    await stop_userbot_client(session_name)

    # 2. Cancel and pop asyncio background task
    if task is not None and not task.done():
        logger.info("Cancelling background userbot task for session '%s'...", session_name)
        task.cancel()

    logger.info("Session '%s' removed from active background tasks.", session_name)
    return True


async def start_extraction_task(
    session_name: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    target_type: str = "all",
    bot: Any = None,
    admin_chat_id: Optional[int] = None,
) -> bool:
    """Launch the Pyrogram global group link extractor as a non-blocking background task.

    Args:
        session_name: The identifier of the MTProto session to use.
        start_date: Earliest date bound for message scraping.
        end_date: Latest date bound for message scraping.
        target_type: Type of links to extract ('all', 'whatsapp', 'tg_groups', 'tg_folders').
        bot: Optional Aiogram Bot instance for live progress feedback.
        admin_chat_id: Telegram chat ID to receive live status updates.

    Returns:
        bool: True if a new extraction task was spawned; False if already running.
    """
    if is_extraction_running(session_name):
        logger.warning("Link extraction task for session '%s' is already running.", session_name)
        return False

    logger.info("Spawning background global link extraction task for session '%s' (target: %s)...", session_name, target_type)
    task: asyncio.Task[Any] = asyncio.create_task(
        run_extraction_task(
            session_name=session_name,
            start_date=start_date,
            end_date=end_date,
            target_type=target_type,
            bot=bot,
            admin_chat_id=admin_chat_id,
        ),
        name=f"extraction_{session_name}",
    )
    active_extractions[session_name] = task
    logger.info("Extraction task for session '%s' successfully registered in pool.", session_name)
    return True


async def stop_extraction_task(session_name: str) -> bool:
    """Cancel and remove an active link extraction task from the process pool.

    Args:
        session_name: The identifier of the session whose extraction task should stop.

    Returns:
        bool: True if task was found and cancelled; False if not running.
    """
    task = active_extractions.get(session_name)
    if task is None or task.done():
        logger.warning("Attempted to stop extraction task for '%s', but no active task found.", session_name)
        return False

    logger.info("Cancelling background link extraction task for session '%s'...", session_name)
    task.cancel()
    active_extractions.pop(session_name, None)
    logger.info("Extraction task for session '%s' removed from active pool.", session_name)
    return True


def get_all_active_sessions() -> list[str]:
    """Retrieve a list of all currently active auto-reply session names.

    Returns:
        list[str]: Sorted list of running session identifiers.
    """
    from userbot.client import active_userbot_clients
    running_set = {name for name, task in active_tasks.items() if not task.done()}
    for name, client in active_userbot_clients.items():
        if getattr(client, "is_connected", False):
            running_set.add(name)
    running = list(running_set)
    running.sort()
    return running


def get_all_active_extractions() -> list[str]:
    """Retrieve a list of all currently active link extraction session names.

    Returns:
        list[str]: Sorted list of session identifiers currently running extractions.
    """
    running = [name for name, task in active_extractions.items() if not task.done()]
    running.sort()
    return running
