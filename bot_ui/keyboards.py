"""
Inline keyboard generators for the Aiogram 3.x Control UI.

Constructs navigation menus, action triggers, dynamic toggle buttons for background
workers, cancel buttons for FSM workflows, category download sub-menus, extraction target sub-menus,
and dynamic session selector keyboards.
"""

from typing import Optional
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_menu(
    active_session: Optional[str] = None,
    is_userbot_on: bool = False,
    is_extractor_on: bool = False,
) -> InlineKeyboardMarkup:
    """Generate the primary control panel inline keyboard with a structured grid layout.

    Layout grid dimensions:
        Row 1 (1 btn): Auto-Reply toggle (Start / Stop).
        Row 2 (1 btn): Link Extractor toggle (Extract / Stop).
        Row 3 (1 btn): Auto-Join Groups.
        Row 4 (2 btns): System Statistics & Download Links.
        Row 5 (1 btn): Sessions Manager.

    Args:
        active_session: Optional name of the currently active Pyrogram session.
        is_userbot_on: Whether the auto-reply engine is actively running in background.
        is_extractor_on: Whether the link extraction task is actively running in background.

    Returns:
        InlineKeyboardMarkup: 5-row structured grid control panel.
    """
    builder = InlineKeyboardBuilder()

    # Row 1: Dynamic Auto-Reply Toggle Button
    if is_userbot_on:
        builder.button(
            text="[ ⏹️ Stop Auto-Reply ]",
            callback_data="menu_stop_reply",
        )
    else:
        builder.button(
            text="[ 🚀 Start Auto-Reply ]",
            callback_data="menu_start_reply",
        )

    # Row 2: Dynamic Link Extraction Toggle Button
    if is_extractor_on:
        builder.button(
            text="[ ⏹️ Stop Extraction ]",
            callback_data="menu_stop_extraction",
        )
    else:
        builder.button(
            text="[ 🔍 Extract Links ]",
            callback_data="menu_extract_links",
        )

    # Row 3: Auto-Join Groups Button
    builder.button(
        text="[ 🚪 Auto-Join Groups ]",
        callback_data="menu_auto_join",
    )

    # Row 4: System Statistics & Download Links Sub-menu Trigger (Side-by-Side)
    builder.button(
        text="[ 📊 System Stats ]",
        callback_data="menu_system_stats",
    )
    builder.button(
        text="[ 📂 Download Links ]",
        callback_data="menu_open_downloads",
    )

    # Row 5: Sessions Manager
    builder.button(
        text="[ 👥 Sessions Manager ]",
        callback_data="menu_session_mgr",
    )

    # Enforce exact row dimensions: 1, 1, 1, 2, 1
    builder.adjust(1, 1, 1, 2, 1)
    return builder.as_markup()


def get_session_mgr_menu() -> InlineKeyboardMarkup:
    """Generate inline keyboard sub-menu for the Sessions Manager.

    Buttons:
        - [ 🔄 Switch Active ]
        - [ ➕ Add New ]
        - [ ✏️ Rename Session ]
        - [ 🗑️ Delete Session ]
        - [ 🔙 Back ]

    Returns:
        InlineKeyboardMarkup: Sessions Manager sub-menu.
    """
    builder = InlineKeyboardBuilder()

    builder.button(
        text="[ 🔄 Switch Active ]",
        callback_data="menu_switch_session",
    )
    builder.button(
        text="[ ➕ Add New ]",
        callback_data="menu_add_session",
    )
    builder.button(
        text="[ ✏️ Rename Session ]",
        callback_data="menu_rename_session_list",
    )
    builder.button(
        text="[ 🗑️ Delete Session ]",
        callback_data="menu_delete_session_list",
    )
    builder.button(
        text="[ 🔙 Back ]",
        callback_data="menu_back",
    )

    builder.adjust(2, 2, 1)
    return builder.as_markup()


def get_extraction_target_menu() -> InlineKeyboardMarkup:
    """Generate inline keyboard sub-menu for choosing link extraction target types.

    Buttons:
        - [📱 WhatsApp]
        - [✈️ TG Groups]
        - [📁 TG Folders]
        - [🌐 All Links]
        - [🔙 Back]

    Returns:
        InlineKeyboardMarkup: Extraction target selection keyboard.
    """
    builder = InlineKeyboardBuilder()

    builder.button(
        text="[📱 WhatsApp]",
        callback_data="extract_target:whatsapp",
    )
    builder.button(
        text="[✈️ TG Groups]",
        callback_data="extract_target:tg_groups",
    )
    builder.button(
        text="[📁 TG Folders]",
        callback_data="extract_target:tg_folders",
    )
    builder.button(
        text="[🌐 All Links]",
        callback_data="extract_target:all",
    )
    builder.button(
        text="[🔙 Back]",
        callback_data="menu_back",
    )

    builder.adjust(1)
    return builder.as_markup()


def get_download_menu() -> InlineKeyboardMarkup:
    """Generate inline keyboard sub-menu for categorized link file downloads.

    Provides category selection buttons for WhatsApp, Telegram Groups, and Telegram Folders,
    along with a Back navigation button.

    Returns:
        InlineKeyboardMarkup: Category download sub-menu.
    """
    builder = InlineKeyboardBuilder()

    builder.button(
        text="[📱 WhatsApp]",
        callback_data="dl_whatsapp",
    )
    builder.button(
        text="[✈️ TG Groups]",
        callback_data="dl_telegram_groups",
    )
    builder.button(
        text="[📁 TG Folders]",
        callback_data="dl_telegram_folders",
    )
    builder.button(
        text="[🔙 Back]",
        callback_data="menu_back",
    )

    builder.adjust(1)
    return builder.as_markup()


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Generate inline keyboard with a single Back to Menu navigation button.

    Returns:
        InlineKeyboardMarkup: Keyboard containing [ 🔙 Back to Menu ].
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔙 Back to Menu",
        callback_data="menu_back",
    )
    builder.adjust(1)
    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Generate inline keyboard with a single Cancel button for active FSM states.

    Returns:
        InlineKeyboardMarkup: Keyboard containing [ ❌ Cancel ].
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text="[ ❌ Cancel ]",
        callback_data="cancel_fsm",
    )
    builder.adjust(1)
    return builder.as_markup()


def get_sessions_keyboard(
    sessions: list[str], current: Optional[str] = None
) -> InlineKeyboardMarkup:
    """Generate an inline keyboard listing all available MTProto sessions for switching.

    Appends a visual checkmark (✅) to the button corresponding to the currently
    active session and appends a navigation Back button at the bottom.

    Args:
        sessions: List of available session identifiers.
        current: Identifier of the currently active session, if any.

    Returns:
        InlineKeyboardMarkup: Dynamic session selection keyboard.
    """
    builder = InlineKeyboardBuilder()

    for session_name in sessions:
        display_text = f"{session_name} ✅" if session_name == current else session_name
        builder.button(
            text=display_text,
            callback_data=f"select_session:{session_name}",
        )

    # Navigation back button to Sessions Manager
    builder.button(
        text="🔙 Back",
        callback_data="menu_session_mgr",
    )

    # 1 button per row for clean readability
    builder.adjust(1)
    return builder.as_markup()


def get_rename_sessions_keyboard(sessions: list[str]) -> InlineKeyboardMarkup:
    """Generate an inline keyboard listing available sessions for renaming.

    Args:
        sessions: List of available session identifiers.

    Returns:
        InlineKeyboardMarkup: Session rename selection keyboard.
    """
    builder = InlineKeyboardBuilder()

    for session_name in sessions:
        builder.button(
            text=f"✏️ {session_name}",
            callback_data=f"rename_sess_{session_name}",
        )

    builder.button(
        text="🔙 Back",
        callback_data="menu_session_mgr",
    )

    builder.adjust(1)
    return builder.as_markup()


def get_delete_sessions_keyboard(sessions: list[str]) -> InlineKeyboardMarkup:
    """Generate an inline keyboard listing available sessions for deletion.

    Args:
        sessions: List of available session identifiers.

    Returns:
        InlineKeyboardMarkup: Session deletion selection keyboard.
    """
    builder = InlineKeyboardBuilder()

    for session_name in sessions:
        builder.button(
            text=f"🗑️ {session_name}",
            callback_data=f"del_sess_{session_name}",
        )

    builder.button(
        text="🔙 Back",
        callback_data="menu_session_mgr",
    )

    builder.adjust(1)
    return builder.as_markup()


def get_joiner_dates_keyboard(dates: list[str]) -> InlineKeyboardMarkup:
    """Generate an inline keyboard listing available date folders containing Telegram group link files.

    Args:
        dates: List of date folder names (e.g. '2026-08-11').

    Returns:
        InlineKeyboardMarkup: Date selection keyboard.
    """
    builder = InlineKeyboardBuilder()

    for date_str in dates:
        builder.button(
            text=f"📅 {date_str}",
            callback_data=f"jdate_{date_str}",
        )

    builder.button(
        text="🔙 Back to Menu",
        callback_data="menu_back",
    )

    builder.adjust(1)
    return builder.as_markup()


def get_joiner_files_keyboard(files: list[str]) -> InlineKeyboardMarkup:
    """Generate an inline keyboard listing available group link .txt files for a selected date.

    Args:
        files: List of file names (e.g. 'part_1.txt').

    Returns:
        InlineKeyboardMarkup: File selection keyboard.
    """
    builder = InlineKeyboardBuilder()

    for file_name in files:
        builder.button(
            text=f"📄 {file_name}",
            callback_data=f"jfile_{file_name}",
        )

    builder.button(
        text="🔙 Back to Dates",
        callback_data="menu_auto_join",
    )

    builder.adjust(1)
    return builder.as_markup()


def get_download_dates_keyboard(dates: list[str]) -> InlineKeyboardMarkup:
    """Generate an inline keyboard listing available date folders for link downloads.

    Args:
        dates: List of date folder names (e.g. '2026-08-11').

    Returns:
        InlineKeyboardMarkup: Date selection keyboard.
    """
    builder = InlineKeyboardBuilder()

    for date_str in dates:
        builder.button(
            text=f"📅 {date_str}",
            callback_data=f"dl_date_{date_str}",
        )

    builder.button(
        text="🔙 Back to Categories",
        callback_data="menu_open_downloads",
    )

    builder.adjust(1)
    return builder.as_markup()


def get_download_files_keyboard(
    files: list[str],
    category: str = "telegram_groups",
    date_str: str = "",
    page: int = 1,
    page_size: int = 10,
) -> InlineKeyboardMarkup:
    """Generate an inline keyboard listing available link part files for a selected date and category with pagination.

    Limits displayed file buttons to a maximum of 10 items per page and renders
    navigation buttons ([ ⬅️ Prev ] and [ Next ➡️ ]) when multi-page navigation is needed.

    Args:
        files: List of file names (e.g. ['part_1.txt', 'part_2.txt']).
        category: Category identifier for callback routing (default 'telegram_groups').
        date_str: Date folder name for callback routing (e.g. '2026-08-14').
        page: Target page number (1-indexed, default 1).
        page_size: Maximum number of file buttons per page (default 10).

    Returns:
        InlineKeyboardMarkup: Paginated file selection keyboard.
    """
    builder = InlineKeyboardBuilder()

    total_files = len(files)
    total_pages = max(1, (total_files + page_size - 1) // page_size)
    clamped_page = max(1, min(page, total_pages))

    start_idx = (clamped_page - 1) * page_size
    end_idx = start_idx + page_size
    page_files = files[start_idx:end_idx]

    # File buttons (1 per row)
    for file_name in page_files:
        builder.button(
            text=f"📄 {file_name}",
            callback_data=f"dl_file_{file_name}",
        )

    # Navigation buttons row
    nav_buttons_count = 0
    if clamped_page > 1:
        builder.button(
            text="[ ⬅️ Prev ]",
            callback_data=f"dl_page_{category}_{date_str}_{clamped_page - 1}",
        )
        nav_buttons_count += 1

    if clamped_page < total_pages:
        builder.button(
            text="[ Next ➡️ ]",
            callback_data=f"dl_page_{category}_{date_str}_{clamped_page + 1}",
        )
        nav_buttons_count += 1

    # Back navigation button
    builder.button(
        text="🔙 Back to Dates",
        callback_data="dl_back_dates",
    )

    layout: list[int] = [1] * len(page_files)
    if nav_buttons_count > 0:
        layout.append(nav_buttons_count)
    layout.append(1)

    builder.adjust(*layout)
    return builder.as_markup()


def get_joiner_progress_keyboard(session_name: str) -> InlineKeyboardMarkup:
    """Generate an inline keyboard with a Stop button during active Auto-Joiner execution.

    Args:
        session_name: Identifier of the running userbot session.

    Returns:
        InlineKeyboardMarkup: Keyboard containing [ ⏹️ Stop Auto-Joiner ].
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text="⏹️ Stop Auto-Joiner",
        callback_data=f"stop_joiner_{session_name}",
    )
    builder.adjust(1)
    return builder.as_markup()


