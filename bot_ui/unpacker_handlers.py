"""
Aiogram 3.x handlers for the Folder Unpacking workflow.
"""

import asyncio
import re
from typing import Optional
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot_ui.handlers import get_user_active_session, safe_callback_answer
from bot_ui.keyboards import get_back_keyboard, get_main_menu
from bot_ui.states import UnpackerState
from core.file_manager import LINKS_DIR
from core.logger_setup import setup_logger
from core.process_manager import is_userbot_running, active_unpackers
from userbot.unpacker import run_folder_unpacker_task

logger = setup_logger(__name__)

# Aiogram Router instance for Folder Unpacking handlers
router: Router = Router(name="unpacker_router")

@router.callback_query(F.data == "menu_unpack_folders")
async def start_unpacker_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt user to upload a file or send a text message containing folder links.

    Args:
        callback: Incoming callback query.
        state: FSM execution context.
    """
    user_id = callback.from_user.id
    active_session = get_user_active_session(user_id)

    if not active_session:
        logger.warning("User %d attempted folder unpacking without an active session.", user_id)
        await safe_callback_answer(
            callback,
            "⚠️ No active session! Please select or add an account in Sessions Manager first.",
            show_alert=True,
        )
        return

    if is_userbot_running(active_session):
        await safe_callback_answer(
            callback,
            "⚠️ STOP the Auto-Reply first! You cannot run Unpacker and Auto-Reply simultaneously.",
            show_alert=True,
        )
        return

    await state.set_state(UnpackerState.waiting_for_input)
    await state.update_data(session_name=active_session)

    prompt_text = (
        "📂 <b>Folder Unpacker: Input Links</b>\n\n"
        f"🟢 Active Account: <code>{active_session}</code>\n\n"
        "Please send a <code>.txt</code> file containing Telegram folder links (e.g. <code>t.me/addlist/...</code>) "
        "OR simply paste the links as a text message directly here."
    )

    if callback.message:
        try:
            await callback.message.edit_text(
                text=prompt_text,
                parse_mode="HTML",
                reply_markup=get_back_keyboard(),
            )
        except TelegramBadRequest as exc:
            logger.debug("Failed editing message on unpacker prompt: %s", exc)

    await safe_callback_answer(callback)
    logger.info("User %d opened Folder Unpacker input prompt for session '%s'.", user_id, active_session)


@router.message(UnpackerState.waiting_for_input, F.document | F.text)
async def process_unpacker_input(message: Message, state: FSMContext) -> None:
    """Handle text or file upload containing folder links and start unpacking task.

    Args:
        message: The incoming message (text or document).
        state: FSM execution context.
    """
    user_id = message.from_user.id if message.from_user else 0
    state_data = await state.get_data()
    session_name = state_data.get("session_name") or get_user_active_session(user_id)

    if not session_name:
        await message.answer("⚠️ Active session lost. Please restart.")
        await state.clear()
        return

    links = []

    if message.document:
        if not message.document.file_name.endswith(".txt"):
            await message.answer("⚠️ Please upload a valid `.txt` file.")
            return

        target_dir = LINKS_DIR / session_name / "uploaded"
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / message.document.file_name
        
        await message.bot.download(message.document, destination=file_path)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                links = re.findall(r"(https?://t\.me/addlist/\S+)", content)
        except OSError as exc:
            logger.error("Failed to read uploaded file for unpacking: %s", exc)
            await message.answer("⚠️ Failed to read the uploaded file.")
            return
    elif message.text:
        links = re.findall(r"(https?://t\.me/addlist/\S+)", message.text)
    
    if not links:
        await message.answer("⚠️ No valid folder links (`t.me/addlist/...`) found. Please try again.")
        return

    await state.clear()

    # Create stop button for unpacker task
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="⏹️ Stop Unpacker", callback_data=f"stop_unpacker_{session_name}")
    builder.adjust(1)
    keyboard = builder.as_markup()

    start_text = (
        "⏳ <b>Starting Folder Unpacking Engine...</b>\n\n"
        f"📂 Detected Folder Links: <b>{len(links)}</b>\n"
        f"🟢 Account: <code>{session_name}</code>\n\n"
        "<i>Fetching folder contents and filtering public groups...</i>"
    )

    status_msg = await message.answer(
        text=start_text,
        parse_mode="HTML",
        reply_markup=keyboard,
    )

    logger.info("User %d launched Folder Unpacker on session '%s' with %d folder links.", user_id, session_name, len(links))

    # Lazy import to avoid circular dependency
    from userbot.unpacker import run_folder_unpacker_task

    task = asyncio.create_task(
        run_folder_unpacker_task(
            session_name=session_name,
            folder_links=links,
            bot=message.bot,
            admin_chat_id=user_id,
            message_id=status_msg.message_id,
        ),
        name=f"unpacker_{session_name}",
    )
    active_unpackers[session_name] = task

    try:
        from bot_ui.handlers import send_main_menu
        await send_main_menu(bot=message.bot, chat_id=user_id, session_name=session_name)
    except Exception as exc:
        logger.error("Failed to dispatch main menu on unpacker start: %s", exc)


@router.callback_query(F.data.startswith("stop_unpacker_"))
async def stop_unpacker_callback_handler(callback: CallbackQuery) -> None:
    """Handle request to gracefully cancel the running Folder Unpacker task.

    Args:
        callback: Incoming callback query containing target session.
    """
    if not callback.data:
        await safe_callback_answer(callback)
        return

    session_name = callback.data[len("stop_unpacker_"):]
    from core.process_manager import stop_unpacker_task
    stopped = stop_unpacker_task(session_name)

    await safe_callback_answer(callback, "🛑 Sending abort signal to Unpacker...", show_alert=True)
    logger.info(
        "Admin %d requested abort for Folder Unpacker on session '%s' (stopped=%s).",
        callback.from_user.id if callback.from_user else 0,
        session_name,
        stopped,
    )
