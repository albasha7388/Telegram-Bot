"""
Core Auto-Joiner engine for Telegram Groups and Channels.

Reads categorized Telegram group link files and sequentially joins groups via MTProto
with rate limit compliance, anti-spam spacing (7s), FloodWait auto-retry, and live progress reporting.
"""

import asyncio
from pathlib import Path
import re
from typing import Any, Final, Optional, Union
from pyrogram import Client
from pyrogram.errors import (
    FloodWait,
    InviteHashExpired,
    InviteHashInvalid,
    InviteRequestSent,
    PeerIdInvalid,
    RPCError,
    UserAlreadyParticipant,
    UserDeactivated,
    UsernameInvalid,
    UsernameNotOccupied,
)

from bot_ui.keyboards import get_back_keyboard, get_joiner_progress_keyboard
from config.settings import API_HASH, API_ID
from core.logger_setup import setup_logger
from userbot.session_manager import SESSIONS_DIR, get_session_string

logger = setup_logger(__name__)

# Standard delay in seconds between successful group joins to prevent account restrictions
JOIN_ANTI_SPAM_SLEEP_SECONDS: Final[int] = 7

# Regex pattern to match Telegram group/channel invite links or usernames
TG_LINK_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?:https?://)?(?:www\.)?(?:t\.me|telegram\.me)/(?:joinchat/|\+)?([a-zA-Z0-9_]+)",
    re.IGNORECASE,
)


def extract_links_from_file(file_path: Union[str, Path]) -> list[str]:
    """Read a link file and extract unique Telegram group/channel invite links or handles.

    Args:
        file_path: Absolute or relative Path or string path to the link text file.

    Returns:
        list[str]: Deduplicated ordered list of raw joinable link strings.
    """
    path_obj = Path(file_path)
    if not path_obj.exists() or not path_obj.is_file():
        logger.warning("Target link file '%s' does not exist or is not a file.", file_path)
        return []

    links: list[str] = []
    seen: set[str] = set()

    try:
        with open(path_obj, "r", encoding="utf-8") as f:
            for line in f:
                cleaned = line.strip()
                if not cleaned:
                    continue
                # Match against Telegram link pattern or @ username
                if "t.me" in cleaned or "telegram.me" in cleaned or cleaned.startswith("@"):
                    if cleaned not in seen:
                        seen.add(cleaned)
                        links.append(cleaned)
        logger.info("Extracted %d unique Telegram link(s) from '%s'", len(links), path_obj.name)
        return links
    except OSError as exc:
        logger.error("Failed reading link file '%s': %s", file_path, exc, exc_info=True)
        return []


parse_group_links_from_file = extract_links_from_file


def sanitize_chat_target(link: str) -> str:
    """Sanitize Telegram link/handle into a valid target format for Pyrogram client.join_chat.

    For private invite links (+hash or joinchat/hash), the full link/hash is preserved.
    For public links (t.me/username), the raw username without URL prefixes or @ is extracted.

    Args:
        link: Raw Telegram link or username handle.

    Returns:
        str: Sanitized chat target suitable for Pyrogram join_chat.
    """
    target_chat = link.strip()
    if target_chat.startswith("https://t.me/+"):
        pass  # Private invite hash with +, keep as is
    elif target_chat.startswith("https://t.me/joinchat/"):
        pass  # Private invite hash with joinchat/, keep as is
    elif target_chat.startswith("https://telegram.me/+"):
        pass
    elif target_chat.startswith("https://telegram.me/joinchat/"):
        pass
    elif target_chat.startswith("https://t.me/"):
        # Public link: extract raw username
        target_chat = target_chat.replace("https://t.me/", "")
        target_chat = target_chat.split("/")[0].split("?")[0]
    elif target_chat.startswith("https://telegram.me/"):
        target_chat = target_chat.replace("https://telegram.me/", "")
        target_chat = target_chat.split("/")[0].split("?")[0]
    elif target_chat.startswith("http://t.me/"):
        if target_chat.startswith("http://t.me/+"):
            pass
        elif target_chat.startswith("http://t.me/joinchat/"):
            pass
        else:
            target_chat = target_chat.replace("http://t.me/", "")
            target_chat = target_chat.split("/")[0].split("?")[0]
    elif target_chat.startswith("@"):
        target_chat = target_chat[1:]

    return target_chat


async def run_auto_join_task(
    session_name: str,
    file_path: str,
    bot: Optional[Any] = None,
    admin_chat_id: Optional[int] = None,
    message_id: Optional[int] = None,
) -> dict[str, int]:
    """Execute sequential joining of Telegram groups with rate limiting and progress updates.

    Args:
        session_name: Identifier of the MTProto session to use.
        file_path: Full path to the `.txt` links file.
        bot: Optional Aiogram Bot instance for editing progress UI messages.
        admin_chat_id: Telegram chat ID of the admin.
        message_id: ID of the progress message to edit.

    Returns:
        dict[str, int]: Execution statistics (total, joined, skipped_already_in, failed).
    """
    path_obj = Path(file_path)
    links = extract_links_from_file(path_obj)

    stats: dict[str, int] = {
        "total": len(links),
        "joined": 0,
        "sent_request": 0,
        "skipped_already_in": 0,
        "failed": 0,
    }

    if not links:
        logger.warning("No valid Telegram links found in '%s'. Aborting joiner task.", file_path)
        if bot and admin_chat_id and message_id:
            try:
                await bot.edit_message_text(
                    chat_id=admin_chat_id,
                    message_id=message_id,
                    text=(
                        "⚠️ <b>Auto-Joiner Aborted</b>\n\n"
                        f"No valid Telegram group links found in <code>{path_obj.name}</code>."
                    ),
                    parse_mode="HTML",
                    reply_markup=get_back_keyboard(),
                )
            except Exception as exc:
                logger.debug("Failed updating UI for empty link file: %s", exc)

        from core.process_manager import active_joiners
        active_joiners.pop(session_name, None)

        if bot and admin_chat_id:
            try:
                from bot_ui.handlers import send_main_menu
                await send_main_menu(bot=bot, chat_id=admin_chat_id, session_name=session_name)
            except Exception as menu_exc:
                logger.error("Failed auto-refreshing Main Menu after joiner empty target abort: %s", menu_exc)

        return stats

    session_str = get_session_string(session_name)
    if session_str:
        client = Client(
            name=session_name,
            session_string=session_str,
            api_id=API_ID,
            api_hash=API_HASH,
            in_memory=True,
            no_updates=True,
        )
    else:
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        client = Client(
            name=session_name,
            api_id=API_ID,
            api_hash=API_HASH,
            workdir=str(SESSIONS_DIR),
            no_updates=True,
        )

    try:
        await client.start()
        logger.info("Auto-Joiner started Pyrogram client '%s' for '%s'", session_name, path_obj.name)

        for index, link in enumerate(links, 1):
            target_chat = sanitize_chat_target(link)
            while True:
                try:
                    logger.debug("Joining '%s' (as '%s') via session '%s' (%d/%d)...", link, target_chat, session_name, index, stats["total"])
                    await client.join_chat(target_chat)
                    stats["joined"] += 1
                    logger.info("Successfully joined '%s' on session '%s' (%d/%d)", link, session_name, index, stats["total"])
                    await asyncio.sleep(JOIN_ANTI_SPAM_SLEEP_SECONDS)
                    break
                except UserAlreadyParticipant:
                    stats["skipped_already_in"] += 1
                    logger.info("Skipped '%s': already a participant on session '%s'", link, session_name)
                    break
                except InviteRequestSent:
                    stats["sent_request"] += 1
                    logger.info("Join request sent for '%s' on session '%s' (%d/%d)", link, session_name, index, stats["total"])
                    await asyncio.sleep(JOIN_ANTI_SPAM_SLEEP_SECONDS)
                    break
                except FloodWait as exc:
                    wait_seconds = exc.value + 5
                    logger.warning("FloodWait of %d seconds triggered when joining '%s'. Sleeping %ds before retry.", exc.value, link, wait_seconds)
                    flood_text = (
                        "⚠️ <b>Telegram Rate Limit (FloodWait)</b>\n\n"
                        f"Telegram requested waiting for <b>{exc.value}</b> seconds.\n"
                        f"Sleeping for <b>{wait_seconds}</b>s before retrying <code>{link}</code>..."
                    )
                    if bot and admin_chat_id and message_id:
                        try:
                            await bot.edit_message_text(
                                chat_id=admin_chat_id,
                                message_id=message_id,
                                text=flood_text,
                                parse_mode="HTML",
                                reply_markup=get_joiner_progress_keyboard(session_name),
                            )
                        except Exception as ui_exc:
                            logger.debug("Failed editing UI on FloodWait: %s", ui_exc)
                    await asyncio.sleep(wait_seconds)
                    # Loop continues without break to retry this exact same link!
                except Exception as exc:
                    stats["failed"] += 1
                    logger.warning(f"Failed to join '{link}': Telegram API says -> {exc}")
                    break

            # Send live progress update every 3 processed links or on completion
            processed = stats["joined"] + stats["sent_request"] + stats["skipped_already_in"] + stats["failed"]
            if processed % 3 == 0 or processed == stats["total"]:
                progress_text = (
                    "🚀 <b>Auto-Joiner Progress</b>\n"
                    f"├ Target: <code>{path_obj.name}</code>\n"
                    f"├ Joined: <b>{stats['joined']}</b>\n"
                    f"├ Requests Sent: <b>{stats['sent_request']}</b>\n"
                    f"├ Skipped (Already in): <b>{stats['skipped_already_in']}</b>\n"
                    f"└ Failed/Expired: <b>{stats['failed']}</b>\n"
                    "━━━━━━━━━━━━\n"
                    f"⏳ Progress: <b>{processed}/{stats['total']}</b>"
                )
                if bot and admin_chat_id and message_id:
                    try:
                        await bot.edit_message_text(
                            chat_id=admin_chat_id,
                            message_id=message_id,
                            text=progress_text,
                            parse_mode="HTML",
                            reply_markup=get_joiner_progress_keyboard(session_name),
                        )
                    except Exception as ui_exc:
                        logger.debug("Failed updating progress UI: %s", ui_exc)

        # Final completion UI update
        completion_text = (
            "✅ <b>Auto-Joiner Task Completed!</b>\n\n"
            f"📁 Target File: <code>{path_obj.name}</code>\n"
            f"🟢 Successfully Joined: <b>{stats['joined']}</b>\n"
            f"📩 Requests Sent: <b>{stats['sent_request']}</b>\n"
            f"⏭️ Skipped (Already in): <b>{stats['skipped_already_in']}</b>\n"
            f"❌ Failed / Expired: <b>{stats['failed']}</b>\n"
            f"📊 Total Processed: <b>{stats['total']}</b>\n\n"
            "All targets in the selected file have been processed."
        )
        if bot and admin_chat_id and message_id:
            try:
                await bot.edit_message_text(
                    chat_id=admin_chat_id,
                    message_id=message_id,
                    text=completion_text,
                    parse_mode="HTML",
                    reply_markup=get_back_keyboard(),
                )
            except Exception as ui_exc:
                logger.debug("Failed updating completion UI: %s", ui_exc)

        logger.info("Auto-Joiner completed task for '%s': %s", path_obj.name, stats)

        from core.process_manager import active_joiners
        active_joiners.pop(session_name, None)

        if bot and admin_chat_id:
            try:
                from bot_ui.handlers import send_main_menu
                await send_main_menu(bot=bot, chat_id=admin_chat_id, session_name=session_name)
            except Exception as menu_exc:
                logger.error("Failed auto-refreshing Main Menu after joiner completion: %s", menu_exc)

        return stats

    except asyncio.CancelledError:
        logger.info("Auto-Joiner task for session '%s' cancelled by admin.", session_name)
        processed = stats["joined"] + stats["sent_request"] + stats["skipped_already_in"] + stats["failed"]
        abort_text = (
            "🛑 <b>Auto-Joiner Aborted by Admin</b>\n\n"
            f"📁 Target File: <code>{path_obj.name}</code>\n"
            f"🟢 Successfully Joined: <b>{stats['joined']}</b>\n"
            f"📩 Requests Sent: <b>{stats['sent_request']}</b>\n"
            f"⏭️ Skipped (Already in): <b>{stats['skipped_already_in']}</b>\n"
            f"❌ Failed / Expired: <b>{stats['failed']}</b>\n"
            f"⏳ Progress: <b>{processed}/{stats['total']}</b>\n\n"
            "🛑 <b>ABORTED BY ADMIN</b>"
        )
        if bot and admin_chat_id and message_id:
            try:
                await bot.edit_message_text(
                    chat_id=admin_chat_id,
                    message_id=message_id,
                    text=abort_text,
                    parse_mode="HTML",
                    reply_markup=get_back_keyboard(),
                )
            except Exception as ui_exc:
                logger.debug("Failed updating UI on Auto-Joiner cancellation: %s", ui_exc)

        from core.process_manager import active_joiners
        active_joiners.pop(session_name, None)

        if bot and admin_chat_id:
            try:
                from bot_ui.handlers import send_main_menu
                await send_main_menu(bot=bot, chat_id=admin_chat_id, session_name=session_name)
            except Exception as menu_exc:
                logger.error("Failed auto-refreshing Main Menu after joiner cancellation: %s", menu_exc)

        return stats

    except Exception as exc:
        logger.error("Unexpected error in Auto-Joiner execution for '%s': %s", file_path, exc, exc_info=True)
        error_text = (
            "❌ <b>Auto-Joiner Execution Failed</b>\n\n"
            f"Error occurred: <code>{type(exc).__name__}</code>\n"
            "Please check system logs."
        )
        if bot and admin_chat_id and message_id:
            try:
                await bot.edit_message_text(
                    chat_id=admin_chat_id,
                    message_id=message_id,
                    text=error_text,
                    parse_mode="HTML",
                    reply_markup=get_back_keyboard(),
                )
            except Exception:
                pass

        from core.process_manager import active_joiners
        active_joiners.pop(session_name, None)

        if bot and admin_chat_id:
            try:
                from bot_ui.handlers import send_main_menu
                await send_main_menu(bot=bot, chat_id=admin_chat_id, session_name=session_name)
            except Exception as menu_exc:
                logger.error("Failed auto-refreshing Main Menu after joiner error: %s", menu_exc)

        return stats
    finally:
        from core.process_manager import active_joiners
        active_joiners.pop(session_name, None)
        try:
            if client.is_connected:
                await client.stop()
                logger.info("Stopped Auto-Joiner Pyrogram client '%s'", session_name)
        except Exception as stop_exc:
            logger.debug("Error while stopping Pyrogram client '%s': %s", session_name, stop_exc)
