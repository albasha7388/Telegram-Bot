"""
Pyrogram MTProto Userbot client module.

Manages userbot lifecycle, group chat monitoring with verbose logging, automated
smart replies with rate limiting, strict daily DM quota enforcement, anti-ban sleep
timers, hourly feedback metrics tracking, robust DM error handling, and link extraction.
"""

import asyncio
from datetime import date
from pathlib import Path
import random
from typing import Final, Optional

from pyrogram import Client, filters
from pyrogram.errors import (
    FloodWait,
    PeerIdInvalid,
    RPCError,
    UserIsBlocked,
    UserPrivacyRestricted,
)
from pyrogram.types import Message

from config.settings import (
    API_HASH,
    API_ID,
    MAX_DAILY_DMS,
    TIME_SLEEP_MAX,
    TIME_SLEEP_MIN,
)
from core.file_manager import save_link
from core.logger_setup import setup_logger
from userbot.auto_reply import evaluate_message
from userbot.session_manager import get_session_string
from validators.folder_validator import extract_folder_links
from validators.telegram_validator import extract_telegram_links
from validators.whatsapp_validator import extract_whatsapp_links, validate_whatsapp_link

logger = setup_logger(__name__)

# Sessions storage directory
SESSIONS_DIR: Final[Path] = Path(__file__).resolve().parent.parent / "sessions"

# Default Arabic response for genuine student inquiries
DEFAULT_AUTO_REPLY_TEXT: Final[str] = (
    "السلام عليكم ورحمة الله، أهلاً بك أخي الكريم.\n"
    "بخصوص استفسارك الأكاديمي، تفضل بتزويدي بالتفاصيل وسأقوم بمساعدتك فوراً بإذن الله."
)

# Registry of active Pyrogram Client instances for graceful shutdown
active_userbot_clients: dict[str, Client] = {}

# Outbound DM tracking dictionary and counter for anti-ban rate limiting
daily_dms_count: dict[str, int] = {}
_daily_dm_count: int = 0
_last_dm_date: date = date.today()

# Hourly metric counters for scheduler feedback reports
hourly_scanned_count: int = 0
hourly_replies_sent: int = 0


def can_send_dm(session_name: str = "default") -> bool:
    """Check if the daily direct message (DM) quota has not been exceeded.

    Automatically resets the counter at the start of a new calendar day.

    Args:
        session_name: The session identifier (default: "default").

    Returns:
        bool: True if an outbound DM is permitted, False if the limit is reached.
    """
    global _daily_dm_count, _last_dm_date
    today = date.today()
    if today > _last_dm_date:
        reset_dm_counter()
        _last_dm_date = today

    session_count = daily_dms_count.get(session_name, _daily_dm_count)
    return session_count < MAX_DAILY_DMS


def increment_dm_counter(session_name: str = "default") -> None:
    """Increment the outbound DM counter by 1 and record hourly reply metric.

    Args:
        session_name: The session identifier to increment.
    """
    global _daily_dm_count, hourly_replies_sent
    _daily_dm_count += 1
    hourly_replies_sent += 1
    daily_dms_count[session_name] = daily_dms_count.get(session_name, 0) + 1
    logger.debug(
        "Daily DM counter incremented: %d/%d for session '%s' (hourly sent: %d)",
        _daily_dm_count,
        MAX_DAILY_DMS,
        session_name,
        hourly_replies_sent,
    )


def reset_dm_counter() -> None:
    """Reset all outbound DM counters (used by midnight scheduler and unit tests)."""
    global _daily_dm_count, _last_dm_date
    _daily_dm_count = 0
    daily_dms_count.clear()
    _last_dm_date = date.today()
    logger.info("All outbound daily DM quota trackers have been reset to 0.")


def get_daily_dm_count(session_name: Optional[str] = None) -> int:
    """Retrieve the current daily DM count for a specific session or total across active sessions.

    Args:
        session_name: Optional session identifier. If None, returns sum of session counts or global count.

    Returns:
        int: Number of direct messages sent today.
    """
    if session_name:
        return daily_dms_count.get(session_name, _daily_dm_count)
    if daily_dms_count:
        return sum(daily_dms_count.values())
    return _daily_dm_count


def get_hourly_metrics() -> tuple[int, int]:
    """Retrieve the current hourly scanned message and sent reply counts.

    Returns:
        tuple[int, int]: (hourly_scanned_count, hourly_replies_sent)
    """
    return (hourly_scanned_count, hourly_replies_sent)


def reset_hourly_metrics() -> None:
    """Reset the hourly scanned message and sent reply counters back to 0."""
    global hourly_scanned_count, hourly_replies_sent
    hourly_scanned_count = 0
    hourly_replies_sent = 0
    logger.debug("Hourly feedback report metrics reset to 0.")


async def handle_auto_reply(client: Client, message: Message) -> None:
    """Process incoming group messages for genuine student inquiries and send private replies.

    Enforces early daily DM limit checks prior to intent processing, 4-step intent evaluation
    with verbose audit logging, randomized anti-ban delay, and robust error handling for
    privacy/blocked users without terminating execution or incorrectly incrementing counters.

    Args:
        client: The active Pyrogram Client instance.
        message: The incoming group message object.
    """
    if not message.text:
        return

    session_id = client.name if hasattr(client, "name") and client.name else "default"

    # 1. Early Daily DM Limit Check: Skip processing if daily quota reached
    if not can_send_dm(session_id):
        logger.info(
            "Daily limit reached (%d/%d). Skipping auto-reply.",
            MAX_DAILY_DMS,
            MAX_DAILY_DMS,
        )
        return

    # 2. Evaluate incoming message against 4-step intent classification
    if not evaluate_message(message.text):
        logger.info("Message ignored by filters: does not match student inquiry intent.")
        return

    logger.info("✅ Message matched! Attempting to send DM...")

    sender = message.from_user
    if not sender or not sender.id:
        logger.debug("Message has no valid sender object, skipping DM.")
        return

    user_id = sender.id

    # Re-verify daily DM quota before entering sleep delay
    if not can_send_dm(session_id):
        logger.info(
            "Daily limit reached (%d/%d). Skipping auto-reply to user %d.",
            MAX_DAILY_DMS,
            MAX_DAILY_DMS,
            user_id,
        )
        return

    # 3. Anti-ban protocol: Global Sleep Rule with randomized human-like delay
    delay = random.uniform(TIME_SLEEP_MIN, TIME_SLEEP_MAX)
    logger.info(
        "Approved student inquiry from user %d. Sleeping %.2fs before sending DM...",
        user_id,
        delay,
    )
    await asyncio.sleep(delay)

    # 4. Dispatch private message wrapped in error handling for privacy/block/peer errors
    try:
        await client.send_message(chat_id=user_id, text=DEFAULT_AUTO_REPLY_TEXT)
        increment_dm_counter(session_id)
        logger.info("Successfully sent private auto-reply to user %d.", user_id)
    except (UserPrivacyRestricted, UserIsBlocked, PeerIdInvalid) as exc:
        logger.warning(
            "Failed to DM user %d: Privacy restricted or blocked (%s).",
            user_id,
            exc,
        )
    except FloodWait as exc:
        logger.warning(
            "FloodWait encountered while sending DM to user %d: wait %ds.",
            user_id,
            exc.value,
        )
    except RPCError as exc:
        logger.warning(
            "Telegram RPC error while sending DM to user %d: %s.",
            user_id,
            exc,
        )
    except Exception as exc:
        logger.error(
            "Unexpected error sending DM to user %d: %s",
            user_id,
            exc,
            exc_info=True,
        )


async def handle_link_extraction(client: Client, message: Message) -> None:
    """Extract and persist valid Telegram, shareable folder, and WhatsApp links from messages.

    Args:
        client: The active Pyrogram Client instance.
        message: The incoming message containing raw text.
    """
    if not message.text:
        return

    raw_text = message.text

    # 1. Telegram Standard Links -> data/links/YYYY-MM-DD/telegram_groups/part_X.txt
    for tg_link in extract_telegram_links(raw_text):
        try:
            saved_file = save_link(tg_link, category="telegram_groups")
            logger.info("Extracted and saved Telegram link: %s -> %s", tg_link, saved_file)
        except Exception as exc:
            logger.error("Failed to save Telegram link '%s': %s", tg_link, exc)

    # 2. Telegram Shareable Folder Links -> data/links/YYYY-MM-DD/telegram_folders/part_X.txt
    for folder_link in extract_folder_links(raw_text):
        try:
            saved_file = save_link(folder_link, category="telegram_folders")
            logger.info("Extracted and saved Folder link: %s -> %s", folder_link, saved_file)
        except Exception as exc:
            logger.error("Failed to save Folder link '%s': %s", folder_link, exc)

    # 3. WhatsApp Group Links -> data/links/YYYY-MM-DD/whatsapp/part_X.txt
    for wa_link in extract_whatsapp_links(raw_text):
        try:
            if validate_whatsapp_link(wa_link):
                saved_file = save_link(wa_link, category="whatsapp")
                logger.info("Validated and saved WhatsApp link: %s -> %s", wa_link, saved_file)
            else:
                logger.debug("WhatsApp link '%s' failed validation; discarded.", wa_link)
        except Exception as exc:
            logger.error("Failed validating/saving WhatsApp link '%s': %s", wa_link, exc)


def create_userbot_client(session_name: str) -> Client:
    """Instantiate and configure a Pyrogram userbot client with all event handlers registered.

    Args:
        session_name: The session file name (without .session extension).

    Returns:
        Client: Configured Pyrogram client.
    """
    session_str = get_session_string(session_name)
    if session_str:
        app = Client(
            name=session_name,
            session_string=session_str,
            api_id=API_ID,
            api_hash=API_HASH,
            in_memory=True,
        )
    else:
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        app = Client(
            name=session_name,
            api_id=API_ID,
            api_hash=API_HASH,
            workdir=str(SESSIONS_DIR),
        )

    # Register handlers with Pyrogram filters and verbose logging
    @app.on_message(filters.group & filters.text)
    async def _group_message_listener(client: Client, message: Message) -> None:
        global hourly_scanned_count
        hourly_scanned_count += 1
        chat_title = message.chat.title or "Unknown Group"
        chat_id = message.chat.id
        logger.info(f"📩 New message detected in group: {chat_title} (ID: {chat_id})")
        await handle_auto_reply(client, message)
        await handle_link_extraction(client, message)

    return app


async def run_userbot(session_name: str) -> None:
    """Initialize and start the MTProto userbot client for a designated session.

    Keeps the background task alive until explicitly stopped or cancelled.

    Args:
        session_name: Target session identifier.
    """
    logger.info("Starting Pyrogram Userbot with session '%s'...", session_name)
    app = create_userbot_client(session_name)
    active_userbot_clients[session_name] = app
    await app.start()
    logger.info("Userbot session '%s' started successfully.", session_name)
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        logger.info("Userbot task loop cancelled for session '%s'.", session_name)
        raise


async def stop_userbot_client(session_name: str) -> None:
    """Gracefully stop and disconnect the active Pyrogram client for a session.

    Args:
        session_name: Target session identifier to disconnect.
    """
    app = active_userbot_clients.pop(session_name, None)
    if app and getattr(app, "is_connected", False):
        try:
            logger.info("Gracefully stopping Pyrogram Client for session '%s'...", session_name)
            await app.stop()
            logger.info("Pyrogram Client for session '%s' stopped cleanly.", session_name)
        except Exception as exc:
            logger.warning("Exception during Pyrogram app.stop() for '%s': %s", session_name, exc)
