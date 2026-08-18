"""
Historical global group message extractor module for Telegram and WhatsApp links.

Connects to Pyrogram MTProto sessions, queries all joined groups and supergroups,
iterates through chat history batches with exact date range filtering, yields live
progress updates to Aiogram, and pipelines discovered links into categorized storage.
Tracks granular extraction metrics per link type for live and final status reports.
"""

import asyncio
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final, Optional
from pyrogram import Client
from pyrogram.enums import ChatType
from pyrogram.errors import (
    ChannelPrivate,
    ChatAdminRequired,
    PeerIdInvalid,
    RPCError,
    UsernameInvalid,
)

from aiogram.types import FSInputFile

from config.settings import API_HASH, API_ID
from core.config import ARCHIVE_CHANNEL_ID
from core.file_manager import save_link
from core.logger_setup import setup_logger
from userbot.session_manager import get_session_string
from validators.whatsapp_validator import extract_whatsapp_links, validate_whatsapp_link

logger = setup_logger(__name__)

# Base directory for saved sessions
SESSIONS_DIR: Final[Path] = Path(__file__).resolve().parent.parent / "sessions"

# Combined regex matching standard Telegram links and shareable folder links
TELEGRAM_COMBINED_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?:https?://)?(?:www\.)?(?:t\.me|telegram\.me)/([a-zA-Z0-9_\-+/?=]+)"
    r"|(?:tg://addlist\?slug=([a-zA-Z0-9_\-]+))",
    re.IGNORECASE,
)


def extract_and_segregate_telegram_links(text: str) -> tuple[list[str], list[str]]:
    """Extract standard Telegram links and folder invite links, segregating them into two lists.

    Scrapes both standard Telegram group/channel/invite links and folder share links
    simultaneously from the given text string, then classifies them based on whether
    they contain 'addlist'.

    Args:
        text: Raw message text or caption.

    Returns:
        tuple[list[str], list[str]]: A tuple containing (group_links, folder_links).
    """
    if not text or not isinstance(text, str):
        logger.debug("Received empty or invalid text input for Telegram dual link extraction.")
        return [], []

    group_links: list[str] = []
    folder_links: list[str] = []
    seen: set[str] = set()

    for match in TELEGRAM_COMBINED_PATTERN.finditer(text):
        raw_match = match.group(0).rstrip(".,!?:;)]}\"'")
        if not raw_match:
            continue

        if "addlist" in raw_match.lower():
            slug = match.group(2) or match.group(1) or ""
            slug = slug.rstrip(".,!?:;)]}\"'")
            if slug.lower().startswith("addlist/"):
                slug = slug[len("addlist/"):]
            if not slug:
                continue
            normalized_url = f"https://t.me/addlist/{slug}"
            if normalized_url not in seen:
                seen.add(normalized_url)
                folder_links.append(normalized_url)
        else:
            identifier = (match.group(1) or "").rstrip(".,!?:;)]}\"'")
            if not identifier:
                continue
            normalized_url = f"https://t.me/{identifier}"
            if normalized_url not in seen:
                seen.add(normalized_url)
                group_links.append(normalized_url)

    logger.debug(
        "Segregated Telegram links: %d group link(s), %d folder link(s)",
        len(group_links),
        len(folder_links),
    )
    return group_links, folder_links


async def run_extraction_task(
    session_name: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    target_type: str = "all",
    bot: Any = None,
    admin_chat_id: Optional[int] = None,
    limit_per_group: int = 10000,
) -> int:
    """Iterate over all joined groups/supergroups, extract and persist all valid links.

    Fetches user dialogs, filters strictly for group and supergroup chats, evaluates
    messages within [start_date, end_date], selectively applies regex extraction based
    on target_type, updates the admin via Aiogram with granular breakdowns, and persists links.

    Args:
        session_name: Target MTProto session identifier.
        start_date: Earliest message date to include (messages older than this terminate group scan).
        end_date: Latest message date to include (messages newer than this are skipped).
        target_type: Category of links to extract ('all', 'whatsapp', 'tg_groups', 'tg_folders').
        bot: Optional Aiogram Bot instance used for live progress notifications.
        admin_chat_id: Admin Telegram chat ID where live progress updates are sent.
        limit_per_group: Maximum number of recent messages to inspect per group (default 10000).

    Returns:
        int: Total count of valid links saved across all categories.
    """
    logger.info(
        "Starting global group link extraction for session '%s' (target: %s)...",
        session_name,
        target_type,
    )
    run_time = datetime.now()
    run_timestamp = run_time.strftime("%Y%m%d_%H%M%S")
    run_date_str = run_time.strftime("%Y-%m-%d")
    run_time_str = run_time.strftime("%H-%M-%S")
    files_generated_this_run: set[str] = set()

    counters: dict[str, int] = {
        "whatsapp": 0,
        "tg_groups": 0,
        "tg_folders": 0,
    }
    total_messages_checked = 0
    scanned_groups_count = 0
    total_links_found = 0

    progress_msg: Any = None
    if bot and admin_chat_id:
        try:
            progress_msg = await bot.send_message(
                chat_id=admin_chat_id,
                text="🔍 Fetching your group list...",
            )
        except Exception as exc:
            logger.warning("Could not send initial progress notification: %s", exc)

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

    normalized_target = target_type.strip().lower()

    try:
        async with app:
            async for dialog in app.get_dialogs():
                chat = dialog.chat
                # Filter strictly for GROUP and SUPERGROUP chats
                if chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
                    continue

                scanned_groups_count += 1
                group_title = chat.title or str(chat.id)
                logger.info(f"🔍 Scanning Group: {dialog.chat.title} (ID: {dialog.chat.id})")

                try:
                    async for message in app.get_chat_history(chat.id, limit=limit_per_group):
                        total_messages_checked += 1

                        # Date Range Filtering Logic
                        if message.date and start_date and end_date:
                            msg_date = message.date
                            # Normalize timezone awareness
                            if msg_date.tzinfo is None and start_date.tzinfo is not None:
                                msg_date = msg_date.replace(tzinfo=timezone.utc)
                            elif msg_date.tzinfo is not None and start_date.tzinfo is None:
                                start_date = start_date.replace(tzinfo=msg_date.tzinfo)
                                end_date = end_date.replace(tzinfo=msg_date.tzinfo)

                            # Skip messages newer than the upper bound
                            if msg_date > end_date:
                                continue

                            # Stop reading further history once we pass the lower bound for this group
                            if msg_date < start_date:
                                logger.debug(
                                    "Message in '%s' older than start_date (%s). Ending group scan.",
                                    group_title,
                                    start_date,
                                )
                                break

                        text_content = message.text or message.caption
                        if text_content:
                            # 1. Dual-Extraction for Telegram Links (Segregated into Groups vs Folders)
                            if normalized_target in ("all", "tg_groups", "telegram_groups", "tg_folders", "telegram_folders"):
                                group_links, folder_links = extract_and_segregate_telegram_links(text_content)

                                # Flush group_links -> data/links/{session_name}/YYYY-MM-DD/telegram_groups/part_X.txt
                                if normalized_target in ("all", "tg_groups", "telegram_groups"):
                                    for tg_link in group_links:
                                        try:
                                            saved_file = save_link(
                                                tg_link,
                                                category="telegram_groups",
                                                session_name=session_name,
                                                run_timestamp=run_timestamp,
                                            )
                                            files_generated_this_run.add(saved_file)
                                            counters["tg_groups"] += 1
                                            logger.debug("Persisted extracted Telegram group link: %s", tg_link)
                                        except Exception as exc:
                                            logger.error("Failed to persist Telegram group link '%s': %s", tg_link, exc)

                                # Flush folder_links -> data/links/{session_name}/YYYY-MM-DD/telegram_folders/part_X.txt
                                if normalized_target in ("all", "tg_folders", "telegram_folders"):
                                    for folder_link in folder_links:
                                        try:
                                            saved_file = save_link(
                                                folder_link,
                                                category="telegram_folders",
                                                session_name=session_name,
                                                run_timestamp=run_timestamp,
                                            )
                                            files_generated_this_run.add(saved_file)
                                            counters["tg_folders"] += 1
                                            logger.debug("Persisted extracted Telegram folder link: %s", folder_link)
                                        except Exception as exc:
                                            logger.error("Failed to persist Telegram folder link '%s': %s", folder_link, exc)

                            # 2. WhatsApp Group links -> data/links/{session_name}/YYYY-MM-DD/whatsapp/part_X.txt
                            if normalized_target in ("all", "whatsapp"):
                                for wa_link in extract_whatsapp_links(text_content):
                                    try:
                                        if validate_whatsapp_link(wa_link):
                                            saved_file = save_link(
                                                wa_link,
                                                category="whatsapp",
                                                session_name=session_name,
                                                run_timestamp=run_timestamp,
                                            )
                                            files_generated_this_run.add(saved_file)
                                            counters["whatsapp"] += 1
                                            logger.debug("Persisted validated WhatsApp link: %s", wa_link)
                                    except Exception as exc:
                                        logger.error("Failed validating/persisting WhatsApp link '%s': %s", wa_link, exc)

                        # Periodic live progress notification every 500 messages checked globally
                        if total_messages_checked % 500 == 0 and bot and admin_chat_id and progress_msg:
                            total_so_far = sum(counters.values())
                            try:
                                await bot.edit_message_text(
                                    chat_id=admin_chat_id,
                                    message_id=progress_msg.message_id,
                                    text=(
                                        f"⏳ <b>Scanning all groups...</b>\n"
                                        f"Checked Messages: <code>{total_messages_checked}</code>\n\n"
                                        f"📊 <b>Discovered Links Breakdown:</b>\n"
                                        f"├ 📱 WhatsApp: <b>{counters['whatsapp']}</b>\n"
                                        f"├ ✈️ TG Groups: <b>{counters['tg_groups']}</b>\n"
                                        f"└ 📁 TG Folders: <b>{counters['tg_folders']}</b>\n"
                                        f"━━━━━━━━━━━━━━━━━━\n"
                                        f"📈 Total Found: <b>{total_so_far}</b>"
                                    ),
                                    parse_mode="HTML",
                                )
                            except Exception as exc:
                                logger.debug("Failed updating live progress message: %s", exc)

                except (ChatAdminRequired, UsernameInvalid, ChannelPrivate, PeerIdInvalid) as exc:
                    logger.warning("Access restricted for group '%s' (%s): %s", group_title, chat.id, exc)
                except RPCError as exc:
                    logger.error("RPC error processing group '%s' (%s): %s", group_title, chat.id, exc)
                except Exception as exc:
                    logger.error("Unexpected error in group '%s' (%s): %s", group_title, chat.id, exc, exc_info=True)

        total_links_found = sum(counters.values())

        logger.info(
            "Global extraction completed for session '%s'. Scanned %d groups, %d messages. Found %d links (WA: %d, TG: %d, Folders: %d).",
            session_name,
            scanned_groups_count,
            total_messages_checked,
            total_links_found,
            counters["whatsapp"],
            counters["tg_groups"],
            counters["tg_folders"],
        )

        # Final completion notification
        if bot and admin_chat_id:
            if progress_msg:
                try:
                    await bot.edit_message_text(
                        chat_id=admin_chat_id,
                        message_id=progress_msg.message_id,
                        text=(
                            f"✅ <b>Global Extraction Complete!</b>\n\n"
                            f"Scanned Groups: <b>{scanned_groups_count}</b>\n"
                            f"Checked Messages: <b>{total_messages_checked}</b>\n\n"
                            f"📂 <b>Extracted Links Breakdown:</b>\n"
                            f"├ 📱 WhatsApp: <b>{counters['whatsapp']}</b>\n"
                            f"├ ✈️ TG Groups: <b>{counters['tg_groups']}</b>\n"
                            f"└ 📁 TG Folders: <b>{counters['tg_folders']}</b>\n"
                            f"━━━━━━━━━━━━━━━━━━\n"
                            f"📈 <b>Total Links Saved:</b> <b>{total_links_found}</b>"
                        ),
                        parse_mode="HTML",
                    )
                except Exception as exc:
                    logger.debug("Failed sending final extraction complete update: %s", exc)

            # Automated persistent channel archive upload
            if ARCHIVE_CHANNEL_ID and bot and files_generated_this_run:
                try:
                    for file_path_str in sorted(files_generated_this_run):
                        file_path = Path(file_path_str)
                        if file_path.exists() and file_path.is_file():
                            category_name = file_path.parent.name
                            custom_name = f"{session_name}_{category_name}_{run_date_str}_{run_time_str}.txt"
                            try:
                                doc = FSInputFile(path=str(file_path), filename=custom_name)
                                caption = (
                                    f"📄 <b>New Links Archive</b>\n"
                                    f"👤 <b>Session:</b> <code>{session_name}</code>\n"
                                    f"📅 <b>Date:</b> <code>{run_date_str}</code>\n"
                                    f"📂 <b>Category:</b> {category_name}\n"
                                    f"📝 <b>File:</b> <code>{custom_name}</code>"
                                )
                                await bot.send_document(
                                    chat_id=ARCHIVE_CHANNEL_ID,
                                    document=doc,
                                    caption=caption,
                                    parse_mode="HTML",
                                )
                                logger.info(
                                    "Archived file '%s' as '%s' (%s) to channel %s for session '%s'",
                                    file_path.name,
                                    custom_name,
                                    category_name,
                                    ARCHIVE_CHANNEL_ID,
                                    session_name,
                                )
                            except Exception as doc_exc:
                                logger.error(
                                    "Failed to upload '%s' to archive channel %s: %s",
                                    file_path.name,
                                    ARCHIVE_CHANNEL_ID,
                                    doc_exc,
                                )
                except Exception as archive_exc:
                    logger.error("Error during automated link archiving: %s", archive_exc, exc_info=True)

            # Guaranteed UI auto-refresh with fresh Main Menu
            from core.process_manager import active_extractions
            active_extractions.pop(session_name, None)
            try:
                from bot_ui.handlers import send_main_menu
                await send_main_menu(bot=bot, chat_id=admin_chat_id, session_name=session_name)
            except Exception as menu_exc:
                logger.error("Failed to auto-refresh Main Menu after extraction completion: %s", menu_exc)

    except asyncio.CancelledError:
        logger.info("Global extraction task for session '%s' cancelled by admin.", session_name)
        from core.process_manager import active_extractions
        active_extractions.pop(session_name, None)
        if bot and admin_chat_id:
            if progress_msg:
                try:
                    await bot.edit_message_text(
                        chat_id=admin_chat_id,
                        message_id=progress_msg.message_id,
                        text=(
                            f"🛑 <b>Link Extraction Aborted by Admin</b>\n\n"
                            f"Session: <code>{session_name}</code>\n"
                            f"Scanned Groups: <b>{scanned_groups_count}</b>\n"
                            f"Checked Messages: <b>{total_messages_checked}</b>\n"
                            f"Discovered Links: <b>{sum(counters.values())}</b>\n\n"
                            "🛑 <b>ABORTED BY ADMIN</b>"
                        ),
                        parse_mode="HTML",
                    )
                except Exception as ui_exc:
                    logger.debug("Failed updating progress message on extraction abort: %s", ui_exc)
            else:
                try:
                    await bot.send_message(
                        chat_id=admin_chat_id,
                        text=(
                            f"🛑 <b>Link Extraction Aborted by Admin</b>\n\n"
                            f"Session: <code>{session_name}</code>\n"
                            "🛑 <b>ABORTED BY ADMIN</b>"
                        ),
                        parse_mode="HTML",
                    )
                except Exception as ui_exc:
                    logger.debug("Failed sending abort notification: %s", ui_exc)
            try:
                from bot_ui.handlers import send_main_menu
                await send_main_menu(bot=bot, chat_id=admin_chat_id, session_name=session_name)
            except Exception as menu_exc:
                logger.error("Failed to auto-refresh Main Menu after extraction abort: %s", menu_exc)

    except (RPCError, Exception) as exc:
        logger.error("Failure during global extraction for session '%s': %s", session_name, exc, exc_info=True)
        from core.process_manager import active_extractions
        active_extractions.pop(session_name, None)
        if bot and admin_chat_id:
            if progress_msg:
                try:
                    await bot.edit_message_text(
                        chat_id=admin_chat_id,
                        message_id=progress_msg.message_id,
                        text=(
                            f"❌ <b>Link Extraction Failed</b>\n\n"
                            f"Session: <code>{session_name}</code>\n"
                            f"Error occurred: <code>{type(exc).__name__}</code>\n"
                            "Please check system logs."
                        ),
                        parse_mode="HTML",
                    )
                except Exception as ui_exc:
                    logger.debug("Failed updating progress message on extraction failure: %s", ui_exc)
            else:
                try:
                    await bot.send_message(
                        chat_id=admin_chat_id,
                        text=(
                            f"❌ <b>Link Extraction Failed</b>\n\n"
                            f"Session: <code>{session_name}</code>\n"
                            f"Error occurred: <code>{type(exc).__name__}</code>\n"
                            "Please check system logs."
                        ),
                        parse_mode="HTML",
                    )
                except Exception as ui_exc:
                    logger.debug("Failed sending extraction failure notice: %s", ui_exc)
            try:
                from bot_ui.handlers import send_main_menu
                await send_main_menu(bot=bot, chat_id=admin_chat_id, session_name=session_name)
            except Exception as menu_exc:
                logger.error("Failed to auto-refresh Main Menu after extraction failure: %s", menu_exc)
    finally:
        from core.process_manager import active_extractions
        active_extractions.pop(session_name, None)

    return total_links_found
