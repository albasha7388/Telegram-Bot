"""
Core Folder Unpacker engine for Telegram.
Fetches contents of folder links (e.g., t.me/addlist/slug) without joining them,
filters for public groups, deduplicates, and saves to chunked .txt files (max 100 links/file).
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

from aiogram import Bot
from aiogram.types import FSInputFile
from pyrogram.errors import FloodWait, RPCError
from pyrogram.raw.functions.chatlists import CheckChatlistInvite
from pyrogram.raw.types.chatlists import ChatlistInvite, ChatlistInviteAlready
from pyrogram.raw.types import Channel, Chat

from core.file_manager import LINKS_DIR
from core.logger_setup import setup_logger
from pyrogram import Client

from config.settings import API_ID, API_HASH
from userbot.session_manager import get_session_string

SESSIONS_DIR = Path(__file__).resolve().parent.parent / "sessions"

logger = setup_logger(__name__)

async def run_folder_unpacker_task(
    session_name: str,
    folder_links: list[str],
    bot: Bot,
    admin_chat_id: int,
    message_id: int,
) -> None:
    """Run the MTProto Folder Unpacking task in the background.

    Args:
        session_name: Valid Pyrogram session identifier.
        folder_links: List of raw `t.me/addlist/...` folder links.
        bot: Aiogram bot instance for reporting.
        admin_chat_id: Telegram User ID of the admin.
        message_id: ID of the status message to edit on completion.
    """
    logger.info("Starting Folder Unpacker for session '%s' with %d links", session_name, len(folder_links))

    # Initialize Pyrogram client
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
    if not client:
        logger.error("Failed to load client for session '%s'. Aborting unpacker task.", session_name)
        await _abort_unpacker(bot, admin_chat_id, message_id, session_name, "Session client could not be loaded.")
        return

    await client.start()
    
    seen_links: set[str] = set()
    output_files: list[Path] = []
    current_file_path: Path | None = None
    current_file_count = 0
    file_index = 1
    
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_dir = LINKS_DIR / session_name / "unpacked"
    target_dir.mkdir(parents=True, exist_ok=True)
    
    def get_new_file_path() -> Path:
        nonlocal file_index
        path = target_dir / f"Unpacked_Folders_Groups_{run_timestamp}_{file_index}.txt"
        file_index += 1
        output_files.append(path)
        return path

    current_file_path = get_new_file_path()
    total_extracted = 0

    try:
        for link in folder_links:
            # Check for cancellation
            from core.process_manager import is_unpacker_running
            if not is_unpacker_running(session_name):
                logger.info("Unpacker task cancelled by admin during execution.")
                break

            slug = link.split("/")[-1]
            if not slug:
                continue

            try:
                logger.debug("Checking chatlist invite for slug: %s", slug)
                result = await client.invoke(CheckChatlistInvite(slug=slug))
                
                chats = []
                if isinstance(result, ChatlistInvite):
                    chats = result.chats
                elif isinstance(result, ChatlistInviteAlready):
                    chats = result.already_peers
                
                for chat in chats:
                    # Look for channels/supergroups with usernames (Public Groups)
                    if isinstance(chat, Channel):
                        if getattr(chat, 'username', None):
                            group_link = f"https://t.me/{chat.username}"
                            if group_link not in seen_links:
                                seen_links.add(group_link)
                                total_extracted += 1
                                
                                # Chunking logic (max 100 per file)
                                if current_file_count >= 100:
                                    current_file_path = get_new_file_path()
                                    current_file_count = 0
                                    
                                with open(current_file_path, "a", encoding="utf-8") as f:
                                    f.write(f"{group_link}\n")
                                current_file_count += 1
                                
            except FloodWait as e:
                logger.warning("FloodWait encountered in Unpacker: sleeping %d seconds", e.value)
                await asyncio.sleep(e.value)
            except RPCError as e:
                logger.error("RPC Error processing folder link '%s': %s", link, e)
            except Exception as e:
                logger.error("Unexpected error processing folder link '%s': %s", link, e, exc_info=True)
                
            await asyncio.sleep(1) # Be nice to API

    finally:
        await client.stop()
        
        # Cleanup state
        from core.process_manager import active_unpackers
        active_unpackers.pop(session_name, None)
        
        # Report results
        if total_extracted == 0:
            msg = "⚠️ <b>Folder Unpacking Finished</b>\n\nNo valid public groups were found in the provided folders."
            await bot.edit_message_text(chat_id=admin_chat_id, message_id=message_id, text=msg, parse_mode="HTML")
        else:
            msg = (
                "✅ <b>Folder Unpacking Completed!</b>\n\n"
                f"📥 Total Public Groups Extracted: <b>{total_extracted}</b>\n"
                f"📁 Files Generated: <b>{len(output_files)}</b> (Max 100/file)\n\n"
                "<i>Sending files now...</i>"
            )
            await bot.edit_message_text(chat_id=admin_chat_id, message_id=message_id, text=msg, parse_mode="HTML")
            
            for file_path in output_files:
                if file_path.exists() and file_path.stat().st_size > 0:
                    await bot.send_document(chat_id=admin_chat_id, document=FSInputFile(str(file_path)))
                    
        # Refresh menu
        try:
            from bot_ui.handlers import send_main_menu
            await send_main_menu(bot=bot, chat_id=admin_chat_id, session_name=session_name)
        except Exception as exc:
            logger.error("Failed auto-refreshing Main Menu after unpacker completion: %s", exc)


async def _abort_unpacker(bot: Bot, admin_chat_id: int, message_id: int, session_name: str, reason: str) -> None:
    from core.process_manager import active_unpackers
    active_unpackers.pop(session_name, None)
    try:
        await bot.edit_message_text(
            chat_id=admin_chat_id,
            message_id=message_id,
            text=f"❌ <b>Folder Unpacking Failed</b>\n\nReason: {reason}",
            parse_mode="HTML"
        )
        from bot_ui.handlers import send_main_menu
        await send_main_menu(bot=bot, chat_id=admin_chat_id, session_name=session_name)
    except Exception as e:
        logger.error("Error aborting unpacker: %s", e)
