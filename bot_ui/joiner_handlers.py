"""
Aiogram 3.x handlers for the granular Auto-Joiner FSM workflow.

Provides step-by-step UI for selecting an extraction date, choosing a specific
categorized group link .txt file, and initiating the background MTProto joiner task.
"""

import asyncio
from pathlib import Path
import re
from typing import Optional
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot_ui.handlers import get_user_active_session, safe_callback_answer
from bot_ui.keyboards import (
    get_back_keyboard,
    get_joiner_dates_keyboard,
    get_joiner_files_keyboard,
    get_joiner_progress_keyboard,
    get_joiner_source_keyboard,
    get_main_menu,
)
from bot_ui.states import JoinerState
from core.file_manager import LINKS_DIR
from core.logger_setup import setup_logger
from core.process_manager import (
    active_joiners,
    is_extraction_running,
    is_joiner_running,
    is_userbot_running,
    stop_joiner_task,
)
from userbot.joiner import run_auto_join_task

logger = setup_logger(__name__)

# Aiogram Router instance for Auto-Joiner handlers
router: Router = Router(name="joiner_router")


def get_available_group_dates(session_name: Optional[str] = None) -> list[str]:
    """Scan the data/links/[{session_name}/] directory for date folders containing telegram_groups .txt files.

    Args:
        session_name: Optional session identifier for tenant-isolated date discovery.

    Returns:
        list[str]: Sorted list of date folder names (e.g. ['2026-08-10', '2026-08-11']).
    """
    if not LINKS_DIR.exists():
        return []

    date_folders: set[str] = set()
    date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    if session_name:
        session_dir = LINKS_DIR / session_name
        if not session_dir.exists() or not session_dir.is_dir():
            return []
        for item in session_dir.iterdir():
            if item.is_dir() and date_pattern.match(item.name):
                tg_dir = item / "telegram_groups"
                if tg_dir.exists() and tg_dir.is_dir():
                    txt_files = [f for f in tg_dir.iterdir() if f.is_file() and f.suffix == ".txt"]
                    if txt_files:
                        date_folders.add(item.name)
    else:
        # Scan all sessions and legacy flat date folders
        for sess_or_date in LINKS_DIR.iterdir():
            if not sess_or_date.is_dir():
                continue
            if date_pattern.match(sess_or_date.name):
                tg_dir = sess_or_date / "telegram_groups"
                if tg_dir.exists() and tg_dir.is_dir():
                    txt_files = [f for f in tg_dir.iterdir() if f.is_file() and f.suffix == ".txt"]
                    if txt_files:
                        date_folders.add(sess_or_date.name)
            else:
                for date_item in sess_or_date.iterdir():
                    if date_item.is_dir() and date_pattern.match(date_item.name):
                        tg_dir = date_item / "telegram_groups"
                        if tg_dir.exists() and tg_dir.is_dir():
                            txt_files = [f for f in tg_dir.iterdir() if f.is_file() and f.suffix == ".txt"]
                            if txt_files:
                                date_folders.add(date_item.name)

    return sorted(date_folders, reverse=True)


def get_group_files_for_date(date_str: str, session_name: Optional[str] = None) -> list[str]:
    """Scan data/links/[{session_name}/]{date_str}/telegram_groups/ for available .txt files.

    Args:
        date_str: Date folder name.
        session_name: Optional session identifier for isolated file lookup.

    Returns:
        list[str]: Sorted list of file names (e.g. ['part_1.txt', 'part_2.txt']).
    """
    if session_name:
        tg_dir = LINKS_DIR / session_name / date_str / "telegram_groups"
    else:
        tg_dir = LINKS_DIR / date_str / "telegram_groups"

    if not tg_dir.exists() or not tg_dir.is_dir():
        return []

    part_pattern = re.compile(r"^part_(\d+)\.txt$")
    files: list[tuple[int, str]] = []

    for item in tg_dir.iterdir():
        if item.is_file() and item.suffix == ".txt":
            match = part_pattern.match(item.name)
            part_num = int(match.group(1)) if match else 9999
            files.append((part_num, item.name))

    files.sort(key=lambda item: item[0])
    return [f[1] for f in files]


# --- Step 1: Source Selection ---

@router.callback_query(F.data == "menu_auto_join")
async def start_auto_join_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Validate active session and prompt user to select the source of links.

    Args:
        callback: Incoming callback query.
        state: FSM execution context.
    """
    user_id = callback.from_user.id
    active_session = get_user_active_session(user_id)

    if not active_session:
        logger.warning("User %d attempted auto-join without an active session.", user_id)
        await safe_callback_answer(
            callback,
            "⚠️ No active session! Please select or add an account in Sessions Manager first.",
            show_alert=True,
        )
        return

    if is_userbot_running(active_session):
        await safe_callback_answer(
            callback,
            "⚠️ STOP the Auto-Reply first! You cannot run Joiner and Auto-Reply on the same account simultaneously.",
            show_alert=True,
        )
        return

    prompt_text = (
        "🚪 <b>Auto-Joiner: Source Selection</b>\n\n"
        f"🟢 Active Account: <code>{active_session}</code>\n\n"
        "How would you like to provide the list of links?"
    )

    if callback.message:
        try:
            await callback.message.edit_text(
                text=prompt_text,
                parse_mode="HTML",
                reply_markup=get_joiner_source_keyboard(),
            )
        except TelegramBadRequest as exc:
            logger.debug("Failed editing message on start auto-join: %s", exc)

    await safe_callback_answer(callback)
    logger.info("User %d opened Auto-Joiner source selection for session '%s'.", user_id, active_session)


@router.callback_query(F.data == "joiner_upload")
async def joiner_upload_file_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt user to upload a new .txt file.

    Args:
        callback: Incoming callback query.
        state: FSM execution context.
    """
    user_id = callback.from_user.id
    active_session = get_user_active_session(user_id)
    await state.set_state(JoinerState.waiting_for_upload)
    await state.update_data(session_name=active_session)

    prompt_text = (
        "📁 <b>Auto-Joiner: Upload File</b>\n\n"
        f"🟢 Active Account: <code>{active_session}</code>\n\n"
        "Please send the <code>.txt</code> file containing the Telegram links (one link per line)."
    )

    if callback.message:
        try:
            await callback.message.edit_text(
                text=prompt_text,
                parse_mode="HTML",
                reply_markup=get_back_keyboard(),
            )
        except TelegramBadRequest as exc:
            logger.debug("Failed editing message on upload prompt: %s", exc)

    await safe_callback_answer(callback)


@router.message(JoinerState.waiting_for_upload, F.document)
async def process_file_upload_handler(message: Message, state: FSMContext) -> None:
    """Handle the uploaded .txt file and launch the Auto-Joiner.

    Args:
        message: The incoming message with the document.
        state: FSM execution context.
    """
    if not message.document.file_name.endswith(".txt"):
        await message.answer("⚠️ Please upload a valid `.txt` file.")
        return

    user_id = message.from_user.id if message.from_user else 0
    state_data = await state.get_data()
    session_name = state_data.get("session_name") or get_user_active_session(user_id)

    if not session_name:
        await message.answer("⚠️ Active session lost. Please restart.")
        await state.clear()
        return

    target_dir = LINKS_DIR / session_name / "uploaded"
    target_dir.mkdir(parents=True, exist_ok=True)
    file_path = target_dir / message.document.file_name

    await message.bot.download(message.document, destination=file_path)
    await state.clear()

    start_text = (
        "⏳ <b>Starting Auto-Joiner Engine...</b>\n\n"
        f"📁 Uploaded File: <code>{message.document.file_name}</code>\n"
        f"🟢 Account: <code>{session_name}</code>\n\n"
        "<i>Connecting MTProto client and starting joining process...</i>"
    )

    status_msg = await message.answer(
        text=start_text,
        parse_mode="HTML",
        reply_markup=get_joiner_progress_keyboard(session_name),
    )

    logger.info("User %d launched Auto-Joiner on session '%s' with uploaded file '%s'.", user_id, session_name, file_path)

    task = asyncio.create_task(
        run_auto_join_task(
            session_name=session_name,
            file_path=str(file_path),
            bot=message.bot,
            admin_chat_id=user_id,
            message_id=status_msg.message_id,
        ),
        name=f"joiner_{session_name}",
    )
    active_joiners[session_name] = task


@router.callback_query(F.data == "joiner_extracted")
async def joiner_select_extracted_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """List available dates for extracted files.

    Args:
        callback: Incoming callback query.
        state: FSM execution context.
    """
    user_id = callback.from_user.id
    active_session = get_user_active_session(user_id)

    dates = get_available_group_dates(session_name=active_session)
    if not dates:
        logger.info("No telegram_groups link files found for session '%s' auto-join.", active_session)
        await safe_callback_answer(
            callback,
            f"📭 No Telegram group links found for session '{active_session}' in storage yet. Extract some links first!",
            show_alert=True,
        )
        return

    await state.set_state(JoinerState.selecting_date)
    await state.update_data(session_name=active_session)

    prompt_text = (
        "🚪 <b>Auto-Joiner: Select Date (Step 1/2)</b>\n\n"
        f"🟢 Active Account: <code>{active_session}</code>\n"
        f"📁 Available Dates: <b>{len(dates)}</b>\n\n"
        "Please select the extraction date folder to view its group link files:"
    )

    if callback.message:
        try:
            await callback.message.edit_text(
                text=prompt_text,
                parse_mode="HTML",
                reply_markup=get_joiner_dates_keyboard(dates),
            )
        except TelegramBadRequest as exc:
            logger.debug("Failed editing message on start auto-join: %s", exc)

    await safe_callback_answer(callback)
    logger.info("User %d opened Auto-Joiner date selection for session '%s'.", user_id, active_session)

# --- Step 2: Browse Files for Selected Date ---

@router.callback_query(F.data.startswith("jdate_"))
async def select_joiner_date_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle date selection and render the list of part_X.txt files for that date.

    Args:
        callback: Incoming callback query containing selected date.
        state: FSM execution context.
    """
    if not callback.data:
        await safe_callback_answer(callback)
        return

    selected_date = callback.data[len("jdate_"):]
    user_id = callback.from_user.id
    active_session = get_user_active_session(user_id)
    state_data = await state.get_data()
    session_name = active_session or state_data.get("session_name", "default")

    files = get_group_files_for_date(selected_date, session_name=session_name)
    if not files:
        await safe_callback_answer(
            callback,
            f"📭 No group link files found for date {selected_date} in session '{session_name}'.",
            show_alert=True,
        )
        return

    await state.set_state(JoinerState.selecting_file)
    await state.update_data(selected_date=selected_date, session_name=session_name)

    prompt_text = (
        "🚪 <b>Auto-Joiner: Select File (Step 2/2)</b>\n\n"
        f"📅 Date: <code>{selected_date}</code>\n"
        f"🟢 Active Account: <code>{session_name}</code>\n"
        f"📄 Available Files: <b>{len(files)}</b>\n\n"
        "Select the specific <code>.txt</code> file you want to execute Auto-Join on:"
    )

    if callback.message:
        try:
            await callback.message.edit_text(
                text=prompt_text,
                parse_mode="HTML",
                reply_markup=get_joiner_files_keyboard(files),
            )
        except TelegramBadRequest as exc:
            logger.debug("Failed editing message on select joiner date: %s", exc)

    await safe_callback_answer(callback)
    logger.info("User %d selected date '%s' for Auto-Joiner on session '%s'.", user_id, selected_date, session_name)


# --- Step 3: Execute Auto-Join on Selected File ---

@router.callback_query(F.data.startswith("jfile_"))
async def select_joiner_file_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle file selection, clear FSM state, and launch the background Auto-Join task.

    Args:
        callback: Incoming callback query containing chosen filename.
        state: FSM execution context.
    """
    if not callback.data:
        await safe_callback_answer(callback)
        return

    selected_file = callback.data[len("jfile_"):]
    user_id = callback.from_user.id
    active_session = get_user_active_session(user_id)
    state_data = await state.get_data()
    session_name = active_session or state_data.get("session_name", "default")

    if not active_session:
        await safe_callback_answer(
            callback,
            "⚠️ Active session lost! Please restart from main menu.",
            show_alert=True,
        )
        await state.clear()
        return

    if is_userbot_running(active_session):
        await safe_callback_answer(
            callback,
            "⚠️ STOP the Auto-Reply first! You cannot run Joiner and Auto-Reply on the same account simultaneously.",
            show_alert=True,
        )
        return

    selected_date = state_data.get("selected_date")

    # Fallback search if date was lost from FSM
    if not selected_date:
        for d in get_available_group_dates(session_name=session_name):
            if (LINKS_DIR / session_name / d / "telegram_groups" / selected_file).exists() or (LINKS_DIR / d / "telegram_groups" / selected_file).exists():
                selected_date = d
                break

    if not selected_date:
        await safe_callback_answer(
            callback,
            "⚠️ Could not locate selected file path. Please restart.",
            show_alert=True,
        )
        await state.clear()
        return

    full_path = LINKS_DIR / session_name / selected_date / "telegram_groups" / selected_file
    if not full_path.exists():
        full_path = LINKS_DIR / selected_date / "telegram_groups" / selected_file

    if not full_path.exists():
        await safe_callback_answer(
            callback,
            f"❌ File '{selected_file}' not found on disk.",
            show_alert=True,
        )
        await state.clear()
        return

    await state.clear()

    start_text = (
        "⏳ <b>Starting Auto-Joiner Engine...</b>\n\n"
        f"📁 Target File: <code>{selected_file}</code>\n"
        f"📅 Date: <code>{selected_date}</code>\n"
        f"🟢 Account: <code>{active_session}</code>\n\n"
        "<i>Connecting MTProto client and starting joining process...</i>"
    )

    if callback.message:
        try:
            await callback.message.edit_text(
                text=start_text,
                parse_mode="HTML",
                reply_markup=get_joiner_progress_keyboard(active_session),
            )
        except TelegramBadRequest as exc:
            logger.debug("Failed editing message on select joiner file: %s", exc)

    await safe_callback_answer(callback, "🚀 Auto-Joiner started!")
    logger.info(
        "User %d launched Auto-Joiner on session '%s' with file '%s'.",
        user_id,
        active_session,
        full_path,
    )

    # Spawn background task and register in process manager
    if callback.message:
        task = asyncio.create_task(
            run_auto_join_task(
                session_name=active_session,
                file_path=str(full_path),
                bot=callback.bot,
                admin_chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
            ),
            name=f"joiner_{active_session}",
        )
        active_joiners[active_session] = task


@router.callback_query(F.data.startswith("stop_joiner_"))
async def stop_joiner_callback_handler(callback: CallbackQuery) -> None:
    """Handle request to gracefully cancel and terminate the running Auto-Joiner task.

    Args:
        callback: Incoming callback query containing target session in callback data.
    """
    if not callback.data:
        await safe_callback_answer(callback)
        return

    session_name = callback.data[len("stop_joiner_"):]
    stopped = stop_joiner_task(session_name)

    await safe_callback_answer(callback, "🛑 Sending abort signal...", show_alert=True)
    logger.info(
        "Admin %d requested abort for Auto-Joiner on session '%s' (stopped=%s).",
        callback.from_user.id if callback.from_user else 0,
        session_name,
        stopped,
    )
