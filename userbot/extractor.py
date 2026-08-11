"""
Historical global group message extractor module for Telegram and WhatsApp links.

Connects to Pyrogram MTProto sessions, queries all joined groups and supergroups,
iterates through chat history batches with exact date range filtering, yields live
progress updates to Aiogram, and pipelines discovered links into categorized storage.
Tracks granular extraction metrics per link type for live and final status reports.
"""

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

from config.settings import API_HASH, API_ID
from core.file_manager import (
    save_folder_link,
    save_link,
    save_telegram_link,
    save_whatsapp_link,
)
from core.logger_setup import setup_logger
from validators.folder_validator import extract_folder_links
from validators.telegram_validator import extract_telegram_links
from validators.whatsapp_validator import extract_whatsapp_links, validate_whatsapp_link

logger = setup_logger(__name__)

# Base directory for saved sessions
SESSIONS_DIR: Final[Path] = Path(__file__).resolve().parent.parent / "sessions"


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
    counters: dict[str, int] = {
        "whatsapp": 0,
        "tg_groups": 0,
        "tg_folders": 0,
    }
    total_messages_checked = 0
    scanned_groups_count = 0

    progress_msg: Any = None
    if bot and admin_chat_id:
        try:
            progress_msg = await bot.send_message(
                chat_id=admin_chat_id,
                text="🔍 Fetching your group list...",
            )
        except Exception as exc:
            logger.warning("Could not send initial progress notification: %s", exc)

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
                            # 1. Telegram Channel/Group links -> data/links/YYYY-MM-DD/telegram_groups/part_X.txt
                            if normalized_target in ("all", "tg_groups", "telegram_groups"):
                                for tg_link in extract_telegram_links(text_content):
                                    try:
                                        save_link(tg_link, category="telegram_groups")
                                        counters["tg_groups"] += 1
                                        logger.debug("Persisted extracted Telegram link: %s", tg_link)
                                    except Exception as exc:
                                        logger.error("Failed to persist Telegram link '%s': %s", tg_link, exc)

                            # 2. Telegram Shareable Folder links -> data/links/YYYY-MM-DD/telegram_folders/part_X.txt
                            if normalized_target in ("all", "tg_folders", "telegram_folders"):
                                for folder_link in extract_folder_links(text_content):
                                    try:
                                        save_link(folder_link, category="telegram_folders")
                                        counters["tg_folders"] += 1
                                        logger.debug("Persisted extracted Folder link: %s", folder_link)
                                    except Exception as exc:
                                        logger.error("Failed to persist Folder link '%s': %s", folder_link, exc)

                            # 3. WhatsApp Group links -> data/links/YYYY-MM-DD/whatsapp/part_X.txt
                            if normalized_target in ("all", "whatsapp"):
                                for wa_link in extract_whatsapp_links(text_content):
                                    try:
                                        if validate_whatsapp_link(wa_link):
                                            save_link(wa_link, category="whatsapp")
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
        if bot and admin_chat_id and progress_msg:
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

    except RPCError as exc:
        logger.error("Telegram RPC error during global extraction for session '%s': %s", session_name, exc)
    except Exception as exc:
        logger.error("Unexpected failure in global extraction for session '%s': %s", session_name, exc, exc_info=True)

    return total_links_found
