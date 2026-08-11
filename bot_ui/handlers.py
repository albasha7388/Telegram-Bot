"""
Aiogram 3.x control router and callback handlers.

Provides Single Message UI interaction for monitoring userbot status, navigating features,
triggering and stopping background worker tasks, categorized link file delivery,
cancelling FSM workflows safely, granular target link extraction, and soft toast alerts.
Safely handles expired callback queries (TelegramBadRequest) and validates active sessions.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final, Optional
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from bot_ui.keyboards import (
    get_back_keyboard,
    get_cancel_keyboard,
    get_delete_sessions_keyboard,
    get_download_dates_keyboard,
    get_download_files_keyboard,
    get_download_menu,
    get_extraction_target_menu,
    get_main_menu,
    get_rename_sessions_keyboard,
    get_session_mgr_menu,
    get_sessions_keyboard,
)
from bot_ui.states import DownloadState, ExtractionState, SessionState
from config.settings import MAX_DAILY_DMS
from core.file_manager import (
    LINKS_DIR,
    get_all_link_files,
    get_available_dates_for_category,
    get_files_by_category,
    get_files_for_category_and_date,
    get_total_links_count,
    get_total_links_count_async,
)
from core.logger_setup import setup_logger
from core.process_manager import (
    is_extraction_running,
    is_userbot_running,
    start_extraction_task,
    start_userbot_task,
    stop_extraction_task,
    stop_userbot_task,
)
from userbot import client as userbot_client
from userbot.session_manager import (
    delete_session,
    get_available_sessions,
    rename_session,
)

logger = setup_logger(__name__)

# Aiogram Router instance for UI handlers
router: Router = Router(name="bot_ui_router")

# In-memory dictionary tracking the active session per admin user ID
user_states: dict[int, str] = {}

# Category callback-to-slug mapping
CATEGORY_ACTION_MAP: Final[dict[str, tuple[str, str]]] = {
    "dl_whatsapp": ("whatsapp", "📱 WhatsApp"),
    "dl_telegram_groups": ("telegram_groups", "✈️ Telegram Groups"),
    "dl_telegram_folders": ("telegram_folders", "📁 Telegram Folders"),
}

# Human-readable labels for extraction targets
TARGET_LABELS: Final[dict[str, str]] = {
    "whatsapp": "📱 WhatsApp Links",
    "tg_groups": "✈️ Telegram Groups",
    "telegram_groups": "✈️ Telegram Groups",
    "tg_folders": "📁 Telegram Folders",
    "telegram_folders": "📁 Telegram Folders",
    "all": "🌐 All Links",
}


async def safe_callback_answer(callback: CallbackQuery, *args: Any, **kwargs: Any) -> None:
    """Safely answer callback queries ignoring expired query timeouts (TelegramBadRequest).

    Args:
        callback: Target CallbackQuery to acknowledge.
        *args: Positional arguments forwarded to callback.answer.
        **kwargs: Keyword arguments forwarded to callback.answer.
    """
    try:
        await callback.answer(*args, **kwargs)
    except TelegramBadRequest as exc:
        logger.warning("Ignored expired callback query: %s", exc)


def get_user_active_session(user_id: int) -> Optional[str]:
    """Retrieve the currently active session name for a specific user.

    Args:
        user_id: Telegram user ID.

    Returns:
        Optional[str]: Active session name, or None if unassigned.
    """
    return user_states.get(user_id)


def set_user_active_session(user_id: int, session_name: str) -> None:
    """Assign an active session name to a user in state memory.

    Args:
        user_id: Telegram user ID.
        session_name: Chosen session identifier.
    """
    user_states[user_id] = session_name
    logger.info("User %d switched active session to: %s", user_id, session_name)


def build_dashboard_text(active_session: Optional[str]) -> str:
    """Generate detailed dashboard guidance text indicating current session and action guidelines.

    Args:
        active_session: Optional active session identifier.

    Returns:
        str: Formatted HTML dashboard guidance message.
    """
    session_text = active_session if active_session else "None"

    return (
        "<b>🤖 Hybrid Telegram Control Panel</b>\n\n"
        f"Current Session: <code>{session_text}</code>\n\n"
        "<b>📖 Menu Guide:</b>\n"
        "🚀/⏹ <b>Auto-Reply:</b> Start or stop the background engine that listens to groups and replies to target students.\n"
        "🔍/⏹ <b>Extract Links:</b> Scrape joined groups for specific or all links.\n"
        "📊 <b>System Stats:</b> View daily limits, active tasks, and total extracted links.\n"
        "📂 <b>Download Links:</b> Select a category to receive paginated link .txt files.\n"
        "👥 <b>Sessions Manager:</b> Switch active account, add new, rename, or delete sessions.\n\n"
        "<i>Please select an action below carefully:</i>"
    )


def build_session_mgr_text(active_session: Optional[str], total_sessions: int) -> str:
    """Generate detailed guidance text for the Sessions Manager sub-menu.

    Args:
        active_session: Optional active session identifier.
        total_sessions: Total count of saved sessions.

    Returns:
        str: Formatted HTML guidance message.
    """
    session_text = active_session if active_session else "None"
    return (
        "👥 <b>Sessions Manager Dashboard</b>\n\n"
        f"🟢 Active Account: <code>{session_text}</code>\n"
        f"📁 Total Sessions: <b>{total_sessions}</b>\n\n"
        "<b>Actions:</b>\n"
        "🔄 <b>Switch Active:</b> Choose which account is active.\n"
        "➕ <b>Add New:</b> Authorize a new Pyrogram session via OTP / 2FA.\n"
        "✏️ <b>Rename:</b> Safely rename an existing session file.\n"
        "🗑️ <b>Delete:</b> Permanently remove a session file.\n\n"
        "<i>Please select an option below:</i>"
    )


@router.message(CommandStart())
async def start_command_handler(message: Message, state: FSMContext) -> None:
    """Handle the /start command by hard-resetting active FSM states and rendering fresh control panel UI.

    Args:
        message: The incoming Telegram message object.
        state: FSM execution context for state clearing.
    """
    await state.clear()
    user_id = message.from_user.id if message.from_user else 0

    try:
        from bot_ui.login_handlers import cleanup_user_login_client
        await cleanup_user_login_client(user_id)
    except Exception as exc:
        logger.debug("Failed cleaning up login client on /start: %s", exc)

    active_session = get_user_active_session(user_id)
    userbot_on = is_userbot_running(active_session)
    extractor_on = is_extraction_running(active_session)

    welcome_text = build_dashboard_text(active_session)

    await message.answer(
        text=welcome_text,
        parse_mode="HTML",
        reply_markup=get_main_menu(
            active_session,
            is_userbot_on=userbot_on,
            is_extractor_on=extractor_on,
        ),
    )
    logger.info("Admin user %d accessed /start control menu with FSM hard reset.", user_id)


@router.callback_query(F.data == "menu_start_reply")
async def start_reply_callback_handler(callback: CallbackQuery) -> None:
    """Handle request to spawn non-blocking background userbot engine for the active session.

    Args:
        callback: The incoming callback query.
    """
    user_id = callback.from_user.id
    active_session = get_user_active_session(user_id)

    if not active_session:
        await safe_callback_answer(
            callback,
            "⚠️ Please select a Session (Account) first from the menu!",
            show_alert=True,
        )
        return

    if is_userbot_running(active_session):
        await safe_callback_answer(
            callback,
            "⚠️ Auto-Reply is ALREADY running for this session!",
            show_alert=True,
        )
        return

    started = await start_userbot_task(active_session)
    if started:
        if callback.message:
            try:
                await callback.message.edit_reply_markup(
                    reply_markup=get_main_menu(
                        active_session,
                        is_userbot_on=True,
                        is_extractor_on=is_extraction_running(active_session),
                    ),
                )
            except TelegramBadRequest as exc:
                logger.debug("Failed updating reply markup on start reply: %s", exc)
        await safe_callback_answer(callback, f"✅ Auto-Reply engine started for '{active_session}'!")
        logger.info("User %d started Userbot for session '%s'.", user_id, active_session)
    else:
        await safe_callback_answer(callback, "⚠️ Auto-Reply is ALREADY running for this session!", show_alert=True)


@router.callback_query(F.data == "menu_stop_reply")
async def stop_reply_callback_handler(callback: CallbackQuery) -> None:
    """Handle request to gracefully cancel and terminate the running userbot background task.

    Args:
        callback: The incoming callback query.
    """
    user_id = callback.from_user.id
    active_session = get_user_active_session(user_id)

    if not active_session:
        await safe_callback_answer(callback, "⚠️ Process is already stopped.", show_alert=True)
        return

    stopped = await stop_userbot_task(active_session)
    if stopped:
        if callback.message:
            try:
                await callback.message.edit_reply_markup(
                    reply_markup=get_main_menu(
                        active_session,
                        is_userbot_on=False,
                        is_extractor_on=is_extraction_running(active_session),
                    ),
                )
            except TelegramBadRequest as exc:
                logger.debug("Failed updating reply markup on stop reply: %s", exc)
        await safe_callback_answer(callback, f"⏹️ Auto-Reply stopped for '{active_session}'!")
        logger.info("User %d stopped Userbot for session '%s'.", user_id, active_session)
    else:
        await safe_callback_answer(callback, "⚠️ Process is already stopped.", show_alert=True)


@router.callback_query(F.data == "menu_extract_links")
async def extract_links_callback_handler(callback: CallbackQuery) -> None:
    """Render granular extraction target sub-menu to allow selecting link types.

    Args:
        callback: The incoming callback query.
    """
    user_id = callback.from_user.id
    active_session = get_user_active_session(user_id)

    if not active_session:
        await safe_callback_answer(
            callback,
            "⚠️ Please select a Session (Account) first from the menu!",
            show_alert=True,
        )
        return

    if is_userbot_running(active_session):
        await safe_callback_answer(
            callback,
            "⚠️ STOP the Auto-Reply first! You cannot run Extractor and Auto-Reply on the same account simultaneously.",
            show_alert=True,
        )
        return

    prompt_text = (
        "🔍 <b>Select Link Extraction Target</b>\n\n"
        f"🟢 Active Session: <code>{active_session}</code>\n\n"
        "Choose which category of links you want to scan and extract:"
    )

    if callback.message:
        try:
            await callback.message.edit_text(
                text=prompt_text,
                parse_mode="HTML",
                reply_markup=get_extraction_target_menu(),
            )
        except TelegramBadRequest as exc:
            logger.debug("Failed editing text on extract links: %s", exc)
    await safe_callback_answer(callback)
    logger.info("User %d opened extraction target sub-menu.", user_id)


@router.callback_query(F.data.startswith("extract_target:"))
async def extract_target_callback_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle extraction target selection, save to FSM state data, and prompt for date range.

    Args:
        callback: The incoming callback query containing target in data.
        state: FSM execution context.
    """
    if not callback.data:
        await safe_callback_answer(callback)
        return

    target_type = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id
    active_session = get_user_active_session(user_id)

    if not active_session:
        await safe_callback_answer(
            callback,
            "⚠️ Please select a Session (Account) first from the menu!",
            show_alert=True,
        )
        return

    if is_userbot_running(active_session):
        await safe_callback_answer(
            callback,
            "⚠️ STOP the Auto-Reply first! You cannot run Extractor and Auto-Reply on the same account simultaneously.",
            show_alert=True,
        )
        return

    await state.set_state(ExtractionState.waiting_for_date_range)
    if callback.message:
        await state.update_data(
            target=target_type,
            target_type=target_type,
            prompt_message_id=callback.message.message_id,
        )

    target_label = TARGET_LABELS.get(target_type, target_type)
    prompt_text = (
        "📅 <b>Global Group Link Extraction</b>\n\n"
        f"🟢 Active Session: <code>{active_session}</code>\n"
        f"🎯 Target: <b>{target_label}</b>\n\n"
        "Enter the date range to scan across all your joined groups:\n"
        "Format: <b>YYYY-MM-DD to YYYY-MM-DD</b>\n"
        "Example: <code>2026-08-01 to 2026-08-08</code>"
    )

    if callback.message:
        try:
            await callback.message.edit_text(
                text=prompt_text,
                parse_mode="HTML",
                reply_markup=get_cancel_keyboard(),
            )
        except TelegramBadRequest as exc:
            logger.debug("Failed editing text on extract target: %s", exc)
    await safe_callback_answer(callback)
    logger.info("User %d selected extraction target '%s' and transitioned to date prompt.", user_id, target_type)


@router.callback_query(F.data == "menu_stop_extraction")
async def stop_extraction_callback_handler(callback: CallbackQuery) -> None:
    """Handle request to terminate active link extraction background worker.

    Args:
        callback: The incoming callback query.
    """
    user_id = callback.from_user.id
    active_session = get_user_active_session(user_id)

    if not active_session:
        await safe_callback_answer(callback, "⚠️ Process is already stopped.", show_alert=True)
        return

    stopped = await stop_extraction_task(active_session)
    if stopped:
        if callback.message:
            try:
                await callback.message.edit_reply_markup(
                    reply_markup=get_main_menu(
                        active_session,
                        is_userbot_on=is_userbot_running(active_session),
                        is_extractor_on=False,
                    ),
                )
            except TelegramBadRequest as exc:
                logger.debug("Failed updating reply markup on stop extraction: %s", exc)
        await safe_callback_answer(callback, f"⏹️ Extraction stopped for '{active_session}'!")
        logger.info("User %d stopped extraction for session '%s'.", user_id, active_session)
    else:
        await safe_callback_answer(callback, "⚠️ Process is already stopped.", show_alert=True)


@router.callback_query(F.data == "cancel_fsm")
async def cancel_fsm_callback_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel any active FSM state and safely return the user to the main menu dashboard.

    Args:
        callback: The incoming callback query.
        state: FSM execution context.
    """
    user_id = callback.from_user.id
    try:
        from bot_ui.login_handlers import cleanup_user_login_client
        await cleanup_user_login_client(user_id)
    except Exception as exc:
        logger.debug("Failed cleaning up login client on cancel: %s", exc)

    await state.clear()
    active_session = get_user_active_session(user_id)
    userbot_on = is_userbot_running(active_session)
    extractor_on = is_extraction_running(active_session)

    dashboard_text = build_dashboard_text(active_session)

    if callback.message:
        try:
            await callback.message.edit_text(
                text=dashboard_text,
                parse_mode="HTML",
                reply_markup=get_main_menu(
                    active_session,
                    is_userbot_on=userbot_on,
                    is_extractor_on=extractor_on,
                ),
            )
        except TelegramBadRequest as exc:
            logger.debug("Failed editing text on cancel FSM: %s", exc)
    await safe_callback_answer(callback, "❌ Operation cancelled.")
    logger.info("User %d cancelled active FSM operation.", user_id)


@router.message(ExtractionState.waiting_for_date_range)
async def process_date_range_extraction_handler(message: Message, state: FSMContext) -> None:
    """Validate date range format, clear user message, and edit prompt to launch extraction.

    Enforces Single Message UI:
    1. Instantly deletes the user's incoming message.
    2. Edits the original prompt message with status/feedback instead of sending new text.

    Args:
        message: The incoming message containing the date range string.
        state: FSM execution context.
    """
    # 1. Instantly delete user's text message to keep chat history clean
    try:
        await message.delete()
    except Exception as exc:
        logger.debug("Failed to delete user input message: %s", exc)

    user_id = message.from_user.id if message.from_user else 0
    active_session = get_user_active_session(user_id)
    raw_date = message.text.strip() if message.text else ""

    # Retrieve stored prompt message ID and extraction target from FSM state data
    state_data = await state.get_data()
    prompt_message_id: Optional[int] = state_data.get("prompt_message_id")
    target_type: str = state_data.get("target") or state_data.get("target_type", "all")

    if not active_session:
        error_lost_text = "⚠️ <b>Active session was lost.</b> Please restart with /start."
        if prompt_message_id and message.bot:
            try:
                await message.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=prompt_message_id,
                    text=error_lost_text,
                    parse_mode="HTML",
                )
            except Exception:
                await message.answer(text=error_lost_text, parse_mode="HTML")
        else:
            await message.answer(text=error_lost_text, parse_mode="HTML")
        await state.clear()
        return

    if is_userbot_running(active_session):
        error_msg = (
            "⚠️ <b>Concurrency Conflict!</b>\n\n"
            "STOP the Auto-Reply first! You cannot run Extractor and Auto-Reply on the same account simultaneously."
        )
        main_markup = get_main_menu(
            active_session,
            is_userbot_on=True,
            is_extractor_on=False,
        )
        if prompt_message_id and message.bot:
            try:
                await message.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=prompt_message_id,
                    text=error_msg,
                    parse_mode="HTML",
                    reply_markup=main_markup,
                )
                await state.clear()
                return
            except Exception:
                pass
        await message.answer(
            text=error_msg,
            parse_mode="HTML",
            reply_markup=main_markup,
        )
        await state.clear()
        return

    # Parse and validate exact YYYY-MM-DD to YYYY-MM-DD format
    try:
        parts = [p.strip() for p in raw_date.split("to")]
        if len(parts) != 2:
            raise ValueError("Must contain 'to' separator.")
        start_date = datetime.strptime(parts[0], "%Y-%m-%d").replace(hour=0, minute=0, second=0, tzinfo=timezone.utc)
        end_date = datetime.strptime(parts[1], "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        if start_date > end_date:
            raise ValueError("Start date cannot be after end date.")
    except Exception:
        error_msg = (
            "⚠️ <b>Invalid date format!</b>\n\n"
            "Please use the exact format:\n"
            "<b>YYYY-MM-DD to YYYY-MM-DD</b>\n"
            "Example: <code>2026-08-01 to 2026-08-08</code>"
        )
        if prompt_message_id and message.bot:
            try:
                await message.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=prompt_message_id,
                    text=error_msg,
                    parse_mode="HTML",
                    reply_markup=get_cancel_keyboard(),
                )
            except Exception:
                await message.answer(
                    text=error_msg,
                    parse_mode="HTML",
                    reply_markup=get_cancel_keyboard(),
                )
        else:
            await message.answer(
                text=error_msg,
                parse_mode="HTML",
                reply_markup=get_cancel_keyboard(),
            )
        return

    await state.clear()

    # Launch background global extraction task tracked in process manager
    await start_extraction_task(
        session_name=active_session,
        start_date=start_date,
        end_date=end_date,
        target_type=target_type,
        bot=message.bot,
        admin_chat_id=user_id,
    )

    target_label = TARGET_LABELS.get(target_type, target_type)
    ack_text = (
        "⏳ <b>Starting global extraction in the background...</b>\n\n"
        f"Session: <code>{active_session}</code>\n"
        f"Target: <b>{target_label}</b>\n"
        f"Date Range: <code>{parts[0]}</code> to <code>{parts[1]}</code>\n\n"
        "All joined groups will be scanned and valid links categorized into <code>data/links/</code>."
    )
    main_markup = get_main_menu(
        active_session,
        is_userbot_on=is_userbot_running(active_session),
        is_extractor_on=True,
    )

    if prompt_message_id and message.bot:
        try:
            await message.bot.edit_message_text(
                chat_id=user_id,
                message_id=prompt_message_id,
                text=ack_text,
                parse_mode="HTML",
                reply_markup=main_markup,
            )
        except Exception:
            await message.answer(
                text=ack_text,
                parse_mode="HTML",
                reply_markup=main_markup,
            )
    else:
        await message.answer(
            text=ack_text,
            parse_mode="HTML",
            reply_markup=main_markup,
        )
    logger.info(
        "Spawned global group link extraction task on session '%s' (target: %s)",
        active_session,
        target_type,
    )


@router.callback_query(F.data == "menu_system_stats")
async def system_stats_callback_handler(callback: CallbackQuery) -> None:
    """Render real-time system metrics, granular link counts by category, and safety limits.

    Args:
        callback: The incoming callback query.
    """
    user_id = callback.from_user.id
    active_session = get_user_active_session(user_id)
    userbot_on = is_userbot_running(active_session)
    extractor_on = is_extraction_running(active_session)

    session_display = f"<code>{active_session}</code>" if active_session else "<i>None</i>"
    userbot_display = "🟢 <b>RUNNING 🚀</b>" if userbot_on else "⚪ <b>STOPPED ⏸️</b>"
    extractor_display = "🟢 <b>EXTRACTING 📥</b>" if extractor_on else "⚪ <b>IDLE ⏸️</b>"

    stats = await get_total_links_count_async()
    total_files = len(get_all_link_files())

    # Daily DMs metric
    session_key = active_session or "default"
    dms_sent_today = userbot_client.daily_dms_count.get(session_key, userbot_client._daily_dm_count)

    wa_count = stats.get("whatsapp", 0)
    tg_group_count = stats.get("telegram_groups", 0)
    tg_folder_count = stats.get("telegram_folders", 0)
    total_count = stats.get("total", 0)

    stats_text = (
        "📊 <b>System Statistics Dashboard</b>\n\n"
        f"👤 <b>Active Session:</b> {session_display}\n"
        f"🤖 <b>Auto-Reply Status:</b> {userbot_display}\n"
        f"🔍 <b>Extractor Status:</b> {extractor_display}\n"
        f"📩 <b>Auto-Replies Sent Today:</b> <code>{dms_sent_today}/{MAX_DAILY_DMS}</code>\n\n"
        "📂 <b>Database Storage Breakdown:</b>\n"
        f"├ 📱 WhatsApp: <b>{wa_count}</b>\n"
        f"├ ✈️ TG Groups: <b>{tg_group_count}</b>\n"
        f"└ 📁 TG Folders: <b>{tg_folder_count}</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"📈 <b>Total Links Saved:</b> <b>{total_count}</b>\n"
        f"📄 <b>Paginated Storage Files:</b> <code>{total_files}</code>\n\n"
        "⏰ <i>Daily limits automatically reset at 00:00 UTC.</i>"
    )

    if callback.message:
        try:
            await callback.message.edit_text(
                text=stats_text,
                parse_mode="HTML",
                reply_markup=get_back_keyboard(),
            )
        except TelegramBadRequest as exc:
            logger.debug("Failed editing text on system stats: %s", exc)
    await safe_callback_answer(callback)
    logger.info("Admin user %d viewed system statistics.", user_id)


@router.callback_query(F.data == "menu_open_downloads")
async def open_downloads_menu_callback_handler(callback: CallbackQuery) -> None:
    """Render the download sub-menu allowing category selection.

    Args:
        callback: The incoming callback query.
    """
    prompt_text = (
        "📥 <b>Select which category of links you want to download:</b>"
    )

    if callback.message:
        try:
            await callback.message.edit_text(
                text=prompt_text,
                parse_mode="HTML",
                reply_markup=get_download_menu(),
            )
        except TelegramBadRequest as exc:
            logger.debug("Failed editing text on open downloads: %s", exc)
    await safe_callback_answer(callback)
    logger.info("Admin user %d opened download category sub-menu.", callback.from_user.id)


@router.callback_query(F.data.in_(CATEGORY_ACTION_MAP.keys()))
async def download_category_callback_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle category selection and render date folders containing that category's files.

    Args:
        callback: The incoming callback query.
        state: FSM execution context.
    """
    user_id = callback.from_user.id
    action = callback.data or ""
    category, display_title = CATEGORY_ACTION_MAP[action]

    dates = get_available_dates_for_category(category)

    if not dates:
        await safe_callback_answer(
            callback,
            "📭 No links found in this category yet. Try extracting some first! 😊",
            show_alert=True,
        )
        return

    await state.set_state(DownloadState.selecting_date)
    await state.update_data(category=category, category_title=display_title)

    prompt_text = (
        f"📂 <b>Download: {display_title} (Step 1/2)</b>\n\n"
        f"Available Dates: <b>{len(dates)}</b>\n\n"
        "Select the date folder you wish to browse files from:"
    )

    if callback.message:
        try:
            await callback.message.edit_text(
                text=prompt_text,
                parse_mode="HTML",
                reply_markup=get_download_dates_keyboard(dates),
            )
        except TelegramBadRequest as exc:
            logger.debug("Failed editing text on download category select: %s", exc)

    await safe_callback_answer(callback)
    logger.info("Admin user %d selected category '%s' for download browsing.", user_id, category)


@router.callback_query(F.data.startswith("dl_date_"))
async def download_date_callback_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle date selection and render the list of link files for that date.

    Args:
        callback: Incoming callback query containing selected date.
        state: FSM execution context.
    """
    if not callback.data:
        await safe_callback_answer(callback)
        return

    selected_date = callback.data[len("dl_date_"):]
    state_data = await state.get_data()
    category = state_data.get("category", "telegram_groups")
    display_title = state_data.get("category_title", "Links")

    files = get_files_for_category_and_date(category, selected_date)
    if not files:
        await safe_callback_answer(
            callback,
            f"📭 No link files found for {selected_date}.",
            show_alert=True,
        )
        return

    await state.set_state(DownloadState.selecting_file)
    await state.update_data(selected_date=selected_date)

    prompt_text = (
        f"📂 <b>Download: {display_title} (Step 2/2)</b>\n\n"
        f"📅 Date: <code>{selected_date}</code>\n"
        f"📄 Available Files: <b>{len(files)}</b>\n\n"
        "Click on a file below to download it directly:"
    )

    if callback.message:
        try:
            await callback.message.edit_text(
                text=prompt_text,
                parse_mode="HTML",
                reply_markup=get_download_files_keyboard(files),
            )
        except TelegramBadRequest as exc:
            logger.debug("Failed editing text on download date selection: %s", exc)

    await safe_callback_answer(callback)
    logger.info(
        "Admin user %d selected date '%s' for category '%s' download.",
        callback.from_user.id,
        selected_date,
        category,
    )


@router.callback_query(F.data == "dl_back_dates")
async def download_back_to_dates_callback_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Navigate back to the date selection keyboard from file selection.

    Args:
        callback: Incoming callback query.
        state: FSM execution context.
    """
    state_data = await state.get_data()
    category = state_data.get("category", "telegram_groups")
    display_title = state_data.get("category_title", "Links")

    dates = get_available_dates_for_category(category)
    await state.set_state(DownloadState.selecting_date)

    prompt_text = (
        f"📂 <b>Download: {display_title} (Step 1/2)</b>\n\n"
        f"Available Dates: <b>{len(dates)}</b>\n\n"
        "Select the date folder you wish to browse files from:"
    )

    if callback.message:
        try:
            await callback.message.edit_text(
                text=prompt_text,
                parse_mode="HTML",
                reply_markup=get_download_dates_keyboard(dates),
            )
        except TelegramBadRequest as exc:
            logger.debug("Failed editing text on download back to dates: %s", exc)

    await safe_callback_answer(callback)


@router.callback_query(F.data.startswith("dl_file_"))
async def download_file_callback_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Deliver the chosen link file as a document attachment and keep the file list open.

    Args:
        callback: Incoming callback query containing selected file name.
        state: FSM execution context.
    """
    if not callback.data:
        await safe_callback_answer(callback)
        return

    selected_file = callback.data[len("dl_file_"):]
    state_data = await state.get_data()
    category = state_data.get("category", "telegram_groups")
    selected_date = state_data.get("selected_date")
    display_title = state_data.get("category_title", "Links")

    if not selected_date:
        for d in get_available_dates_for_category(category):
            if (LINKS_DIR / d / category / selected_file).exists():
                selected_date = d
                break

    if not selected_date:
        await safe_callback_answer(callback, "⚠️ Download session expired. Please restart.", show_alert=True)
        return

    file_path = LINKS_DIR / selected_date / category / selected_file
    if not file_path.exists():
        await safe_callback_answer(callback, f"❌ File '{selected_file}' not found.", show_alert=True)
        return

    caption = f"📄 <b>{display_title}:</b> <code>{selected_date}/{selected_file}</code>"
    input_file = FSInputFile(path=str(file_path), filename=f"{selected_date}_{category}_{selected_file}")

    if callback.message:
        # a. Save current menu state
        current_text = getattr(callback.message, "html_text", None) or callback.message.text or ""
        current_markup = callback.message.reply_markup

        # b. Send requested document
        await callback.message.answer_document(
            document=input_file,
            caption=caption,
            parse_mode="HTML",
        )

        # c. Delete old misplaced menu message
        try:
            await callback.message.delete()
        except Exception as exc:
            logger.debug("Failed deleting old menu message during download push-down: %s", exc)

        # d. Resend menu as a brand new message at the bottom of the chat
        await callback.message.answer(
            text=current_text,
            reply_markup=current_markup,
            parse_mode="HTML",
        )

    await safe_callback_answer(callback, "✅ File sent!", show_alert=False)
    logger.info("Delivered single link file '%s' with push-down menu to admin %d.", file_path.name, callback.from_user.id)


@router.callback_query(F.data == "menu_session_mgr")
async def session_mgr_callback_handler(callback: CallbackQuery) -> None:
    """Render the Sessions Manager sub-menu dashboard.

    Args:
        callback: The incoming callback query.
    """
    user_id = callback.from_user.id
    active_session = get_user_active_session(user_id)
    available_sessions = get_available_sessions()
    text = build_session_mgr_text(active_session, len(available_sessions))

    if callback.message:
        try:
            await callback.message.edit_text(
                text=text,
                parse_mode="HTML",
                reply_markup=get_session_mgr_menu(),
            )
        except TelegramBadRequest as exc:
            logger.debug("Failed editing text on session mgr: %s", exc)
    await safe_callback_answer(callback)
    logger.info("User %d opened Sessions Manager menu.", user_id)


@router.callback_query(F.data == "menu_switch_session")
async def switch_session_callback_handler(callback: CallbackQuery) -> None:
    """Render the session selection keyboard with all discovered session files.

    Args:
        callback: The incoming callback query.
    """
    user_id = callback.from_user.id
    available_sessions = get_available_sessions()
    current_session = get_user_active_session(user_id)

    prompt_text = (
        "🔄 <b>Session Switcher</b>\n\n"
        f"Available Sessions Found: <b>{len(available_sessions)}</b>\n"
        "Click on a session below to activate it for the Userbot engine:"
    )

    if callback.message:
        try:
            await callback.message.edit_text(
                text=prompt_text,
                parse_mode="HTML",
                reply_markup=get_sessions_keyboard(available_sessions, current=current_session),
            )
        except TelegramBadRequest as exc:
            logger.debug("Failed editing text on switch session: %s", exc)
    await safe_callback_answer(callback)
    logger.info("User %d opened session switcher list.", user_id)


@router.callback_query(F.data.startswith("select_session:"))
async def select_session_callback_handler(callback: CallbackQuery) -> None:
    """Handle user selection of a specific session account and update state.

    Args:
        callback: The incoming callback query containing session name in data.
    """
    if not callback.data:
        await safe_callback_answer(callback)
        return

    session_name = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id
    set_user_active_session(user_id, session_name)

    available_sessions = get_available_sessions()
    updated_text = (
        "🔄 <b>Session Switcher</b>\n\n"
        f"Active session updated to: 🟢 <b>{session_name}</b>\n\n"
        "You may select another session or return to the Sessions Manager."
    )

    if callback.message:
        try:
            await callback.message.edit_text(
                text=updated_text,
                parse_mode="HTML",
                reply_markup=get_sessions_keyboard(available_sessions, current=session_name),
            )
        except TelegramBadRequest as exc:
            logger.debug("Failed editing text on select session: %s", exc)
    await safe_callback_answer(callback, f"Activated: {session_name}")


@router.callback_query(F.data == "menu_rename_session_list")
async def rename_session_list_callback_handler(callback: CallbackQuery) -> None:
    """Render a list of available sessions to select for renaming.

    Args:
        callback: The incoming callback query.
    """
    available_sessions = get_available_sessions()
    if not available_sessions:
        await safe_callback_answer(
            callback,
            "📭 No sessions found to rename. Add one first!",
            show_alert=True,
        )
        return

    prompt_text = (
        "✏️ <b>Rename Session</b>\n\n"
        "Select the session you would like to rename:"
    )
    if callback.message:
        try:
            await callback.message.edit_text(
                text=prompt_text,
                parse_mode="HTML",
                reply_markup=get_rename_sessions_keyboard(available_sessions),
            )
        except TelegramBadRequest as exc:
            logger.debug("Failed editing text on rename session list: %s", exc)
    await safe_callback_answer(callback)
    logger.info("User %d opened rename session list.", callback.from_user.id)


@router.callback_query(F.data.startswith("rename_sess_"))
async def rename_sess_select_callback_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle session selection for renaming and prompt for the new name.

    Args:
        callback: The incoming callback query.
        state: FSM execution context.
    """
    if not callback.data:
        await safe_callback_answer(callback)
        return

    old_name = callback.data[len("rename_sess_"):]
    await state.set_state(SessionState.waiting_for_new_session_name)
    if callback.message:
        await state.update_data(
            old_session_name=old_name,
            prompt_message_id=callback.message.message_id,
        )

    prompt_text = (
        "✏️ <b>Rename Session</b>\n\n"
        f"Target Session: <code>{old_name}</code>\n\n"
        "Please enter the <b>new name</b> for this session:\n"
        "<i>(Only alphanumeric characters, dashes, and underscores are allowed)</i>"
    )
    if callback.message:
        try:
            await callback.message.edit_text(
                text=prompt_text,
                parse_mode="HTML",
                reply_markup=get_cancel_keyboard(),
            )
        except TelegramBadRequest as exc:
            logger.debug("Failed editing text on rename sess select: %s", exc)
    await safe_callback_answer(callback)
    logger.info("User %d selected session '%s' for renaming.", callback.from_user.id, old_name)


@router.message(SessionState.waiting_for_new_session_name)
async def process_new_session_name_handler(message: Message, state: FSMContext) -> None:
    """Validate new session name, rename the file, update active states, and return to manager menu.

    Args:
        message: The incoming message containing the new session name.
        state: FSM execution context.
    """
    try:
        await message.delete()
    except Exception as exc:
        logger.debug("Failed deleting user message in rename flow: %s", exc)

    user_id = message.from_user.id if message.from_user else 0
    state_data = await state.get_data()
    old_name: Optional[str] = state_data.get("old_session_name")
    prompt_message_id: Optional[int] = state_data.get("prompt_message_id")

    raw_new_name = message.text.strip() if message.text else ""
    if raw_new_name.endswith(".session"):
        raw_new_name = raw_new_name[:-8]

    # Validate format: alphanumeric, underscores, hyphens (2-32 chars)
    import re
    if not re.match(r"^[a-zA-Z0-9_-]{2,32}$", raw_new_name):
        error_text = (
            "⚠️ <b>Invalid Session Name!</b>\n\n"
            "Name must be 2-32 characters (letters, numbers, <code>_</code>, <code>-</code>).\n\n"
            "Please enter a valid new name:"
        )
        if prompt_message_id and message.bot:
            try:
                await message.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=prompt_message_id,
                    text=error_text,
                    parse_mode="HTML",
                    reply_markup=get_cancel_keyboard(),
                )
                return
            except Exception:
                pass
        await message.answer(text=error_text, parse_mode="HTML", reply_markup=get_cancel_keyboard())
        return

    # Check for duplicate
    existing = get_available_sessions()
    if raw_new_name in existing and raw_new_name != old_name:
        error_text = (
            "⚠️ <b>Session Name Already Exists!</b>\n\n"
            f"A session named <code>{raw_new_name}</code> already exists.\n\n"
            "Please choose a different unique name:"
        )
        if prompt_message_id and message.bot:
            try:
                await message.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=prompt_message_id,
                    text=error_text,
                    parse_mode="HTML",
                    reply_markup=get_cancel_keyboard(),
                )
                return
            except Exception:
                pass
        await message.answer(text=error_text, parse_mode="HTML", reply_markup=get_cancel_keyboard())
        return

    if not old_name:
        await state.clear()
        return

    success = rename_session(old_name, raw_new_name)
    await state.clear()

    if success:
        # If active session was old_name, update active session
        if get_user_active_session(user_id) == old_name:
            set_user_active_session(user_id, raw_new_name)

        available_now = get_available_sessions()
        active_now = get_user_active_session(user_id)
        ack_text = (
            "✅ <b>Session Renamed Successfully!</b>\n\n"
            f"<code>{old_name}</code> ➔ <code>{raw_new_name}</code>\n\n"
            + build_session_mgr_text(active_now, len(available_now))
        )
    else:
        available_now = get_available_sessions()
        active_now = get_user_active_session(user_id)
        ack_text = (
            "❌ <b>Rename Failed!</b>\n\n"
            f"Could not rename <code>{old_name}</code>. File may no longer exist.\n\n"
            + build_session_mgr_text(active_now, len(available_now))
        )

    if prompt_message_id and message.bot:
        try:
            await message.bot.edit_message_text(
                chat_id=user_id,
                message_id=prompt_message_id,
                text=ack_text,
                parse_mode="HTML",
                reply_markup=get_session_mgr_menu(),
            )
            return
        except Exception:
            pass
    await message.answer(text=ack_text, parse_mode="HTML", reply_markup=get_session_mgr_menu())
    logger.info("User %d renamed session '%s' to '%s'.", user_id, old_name, raw_new_name)


@router.callback_query(F.data == "menu_delete_session_list")
async def delete_session_list_callback_handler(callback: CallbackQuery) -> None:
    """Render a list of available sessions to select for deletion.

    Args:
        callback: The incoming callback query.
    """
    available_sessions = get_available_sessions()
    if not available_sessions:
        await safe_callback_answer(
            callback,
            "📭 No sessions found to delete.",
            show_alert=True,
        )
        return

    prompt_text = (
        "🗑️ <b>Delete Session</b>\n\n"
        "Click on a session below to permanently delete its file:"
    )
    if callback.message:
        try:
            await callback.message.edit_text(
                text=prompt_text,
                parse_mode="HTML",
                reply_markup=get_delete_sessions_keyboard(available_sessions),
            )
        except TelegramBadRequest as exc:
            logger.debug("Failed editing text on delete session list: %s", exc)
    await safe_callback_answer(callback)
    logger.info("User %d opened delete session list.", callback.from_user.id)


@router.callback_query(F.data.startswith("del_sess_"))
async def del_sess_select_callback_handler(callback: CallbackQuery) -> None:
    """Delete the selected session file, update active states, and refresh list or return to menu.

    Args:
        callback: The incoming callback query.
    """
    if not callback.data:
        await safe_callback_answer(callback)
        return

    session_name = callback.data[len("del_sess_"):]
    user_id = callback.from_user.id

    # Stop any running background workers on this session
    if is_userbot_running(session_name):
        await stop_userbot_task(session_name)
    if is_extraction_running(session_name):
        await stop_extraction_task(session_name)

    deleted = delete_session(session_name)
    if deleted:
        if get_user_active_session(user_id) == session_name:
            user_states[user_id] = None
        await safe_callback_answer(callback, f"🗑️ Session '{session_name}' deleted!", show_alert=True)
    else:
        await safe_callback_answer(callback, f"⚠️ Failed to delete '{session_name}'.", show_alert=True)

    available_remaining = get_available_sessions()
    active_now = get_user_active_session(user_id)

    if available_remaining:
        prompt_text = (
            "🗑️ <b>Delete Session</b>\n\n"
            f"Deleted: <code>{session_name}</code>\n\n"
            "Select another session to delete or return to the menu:"
        )
        markup = get_delete_sessions_keyboard(available_remaining)
    else:
        prompt_text = (
            "🗑️ <b>Delete Session</b>\n\n"
            f"Deleted: <code>{session_name}</code>\n\n"
            + build_session_mgr_text(active_now, 0)
        )
        markup = get_session_mgr_menu()

    if callback.message:
        try:
            await callback.message.edit_text(
                text=prompt_text,
                parse_mode="HTML",
                reply_markup=markup,
            )
        except TelegramBadRequest as exc:
            logger.debug("Failed updating text after delete: %s", exc)
    logger.info("User %d deleted session '%s'.", user_id, session_name)


@router.callback_query(F.data == "menu_back")
async def back_to_main_menu_callback_handler(callback: CallbackQuery) -> None:
    """Navigate back from sub-menus to the main dashboard.

    Args:
        callback: The incoming callback query.
    """
    user_id = callback.from_user.id
    active_session = get_user_active_session(user_id)
    userbot_on = is_userbot_running(active_session)
    extractor_on = is_extraction_running(active_session)

    dashboard_text = build_dashboard_text(active_session)

    if callback.message:
        try:
            await callback.message.edit_text(
                text=dashboard_text,
                parse_mode="HTML",
                reply_markup=get_main_menu(
                    active_session,
                    is_userbot_on=userbot_on,
                    is_extractor_on=extractor_on,
                ),
            )
        except TelegramBadRequest as exc:
            logger.debug("Failed editing text on back to main menu: %s", exc)
    await safe_callback_answer(callback)
    logger.info("User %d navigated back to main menu.", user_id)
