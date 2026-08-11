"""
Unit tests for Aiogram Control UI keyboards, granular extraction sub-menu, and router handlers under Single Message UI.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest
from pytest_mock import MockerFixture
from aiogram.exceptions import TelegramBadRequest

from bot_ui import handlers
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


# --- 1. Keyboard Structure & Dynamic Toggle Tests ---

def test_get_main_menu_all_idle() -> None:
    """Test main menu renders 5 rows (1, 1, 1, 2, 1 layout) when both workers are idle."""
    markup = get_main_menu(is_userbot_on=False, is_extractor_on=False)
    assert markup.inline_keyboard is not None
    assert len(markup.inline_keyboard) == 5

    # Row 1: Auto-Reply (1 button)
    row1 = markup.inline_keyboard[0]
    assert len(row1) == 1
    assert row1[0].text == "[ 🚀 Start Auto-Reply ]"
    assert row1[0].callback_data == "menu_start_reply"

    # Row 2: Link Extractor (1 button)
    row2 = markup.inline_keyboard[1]
    assert len(row2) == 1
    assert row2[0].text == "[ 🔍 Extract Links ]"
    assert row2[0].callback_data == "menu_extract_links"

    # Row 3: Auto-Join Groups (1 button)
    row3 = markup.inline_keyboard[2]
    assert len(row3) == 1
    assert row3[0].text == "[ 🚪 Auto-Join Groups ]"
    assert row3[0].callback_data == "menu_auto_join"

    # Row 4: Stats and Download (2 buttons)
    row4 = markup.inline_keyboard[3]
    assert len(row4) == 2
    assert row4[0].text == "[ 📊 System Stats ]"
    assert row4[0].callback_data == "menu_system_stats"
    assert row4[1].text == "[ 📂 Download Links ]"
    assert row4[1].callback_data == "menu_open_downloads"

    # Row 5: Sessions Manager (1 button)
    row5 = markup.inline_keyboard[4]
    assert len(row5) == 1
    assert row5[0].text == "[ 👥 Sessions Manager ]"
    assert row5[0].callback_data == "menu_session_mgr"


def test_get_main_menu_userbot_running() -> None:
    """Test main menu toggles Auto-Reply button to Stop on Row 1 when active."""
    markup = get_main_menu(is_userbot_on=True, is_extractor_on=False)
    assert markup.inline_keyboard is not None
    assert len(markup.inline_keyboard) == 5

    row1 = markup.inline_keyboard[0]
    row2 = markup.inline_keyboard[1]

    assert row1[0].text == "[ ⏹️ Stop Auto-Reply ]"
    assert row1[0].callback_data == "menu_stop_reply"

    assert row2[0].text == "[ 🔍 Extract Links ]"
    assert row2[0].callback_data == "menu_extract_links"


def test_get_main_menu_extractor_running() -> None:
    """Test main menu toggles Link Extractor button to Stop on Row 2 when active."""
    markup = get_main_menu(is_userbot_on=False, is_extractor_on=True)
    assert markup.inline_keyboard is not None
    assert len(markup.inline_keyboard) == 5

    row1 = markup.inline_keyboard[0]
    row2 = markup.inline_keyboard[1]

    assert row1[0].text == "[ 🚀 Start Auto-Reply ]"
    assert row1[0].callback_data == "menu_start_reply"

    assert row2[0].text == "[ ⏹️ Stop Extraction ]"
    assert row2[0].callback_data == "menu_stop_extraction"


def test_get_main_menu_both_running() -> None:
    """Test main menu displays Stop buttons for both concurrent background tasks."""
    markup = get_main_menu(is_userbot_on=True, is_extractor_on=True)
    assert markup.inline_keyboard is not None
    assert len(markup.inline_keyboard) == 5

    row1 = markup.inline_keyboard[0]
    row2 = markup.inline_keyboard[1]

    assert row1[0].text == "[ ⏹️ Stop Auto-Reply ]"
    assert row1[0].callback_data == "menu_stop_reply"

    assert row2[0].text == "[ ⏹️ Stop Extraction ]"
    assert row2[0].callback_data == "menu_stop_extraction"


def test_get_extraction_target_menu_structure() -> None:
    """Test extraction target sub-menu renders 5 buttons with granular options and back navigation."""
    markup = get_extraction_target_menu()
    assert markup.inline_keyboard is not None
    assert len(markup.inline_keyboard) == 5

    assert markup.inline_keyboard[0][0].text == "[📱 WhatsApp]"
    assert markup.inline_keyboard[0][0].callback_data == "extract_target:whatsapp"

    assert markup.inline_keyboard[1][0].text == "[✈️ TG Groups]"
    assert markup.inline_keyboard[1][0].callback_data == "extract_target:tg_groups"

    assert markup.inline_keyboard[2][0].text == "[📁 TG Folders]"
    assert markup.inline_keyboard[2][0].callback_data == "extract_target:tg_folders"

    assert markup.inline_keyboard[3][0].text == "[🌐 All Links]"
    assert markup.inline_keyboard[3][0].callback_data == "extract_target:all"

    assert markup.inline_keyboard[4][0].text == "[🔙 Back]"
    assert markup.inline_keyboard[4][0].callback_data == "menu_back"


def test_get_download_menu_structure() -> None:
    """Test download sub-menu renders 4 category options and back navigation."""
    markup = get_download_menu()
    assert markup.inline_keyboard is not None
    assert len(markup.inline_keyboard) == 4

    assert markup.inline_keyboard[0][0].text == "[📱 WhatsApp]"
    assert markup.inline_keyboard[0][0].callback_data == "dl_whatsapp"

    assert markup.inline_keyboard[1][0].text == "[✈️ TG Groups]"
    assert markup.inline_keyboard[1][0].callback_data == "dl_telegram_groups"

    assert markup.inline_keyboard[2][0].text == "[📁 TG Folders]"
    assert markup.inline_keyboard[2][0].callback_data == "dl_telegram_folders"

    assert markup.inline_keyboard[3][0].text == "[🔙 Back]"
    assert markup.inline_keyboard[3][0].callback_data == "menu_back"


def test_get_download_dates_keyboard_structure() -> None:
    """Test download dates keyboard formats buttons with dl_date_ prefix and back button."""
    markup = get_download_dates_keyboard(["2026-08-11", "2026-08-10"])
    assert markup.inline_keyboard is not None
    assert len(markup.inline_keyboard) == 3
    assert markup.inline_keyboard[0][0].text == "📅 2026-08-11"
    assert markup.inline_keyboard[0][0].callback_data == "dl_date_2026-08-11"
    assert markup.inline_keyboard[1][0].text == "📅 2026-08-10"
    assert markup.inline_keyboard[1][0].callback_data == "dl_date_2026-08-10"
    assert markup.inline_keyboard[2][0].callback_data == "menu_open_downloads"


def test_get_download_files_keyboard_structure() -> None:
    """Test download files keyboard formats buttons with dl_file_ prefix and back button."""
    markup = get_download_files_keyboard(["part_1.txt", "part_2.txt"])
    assert markup.inline_keyboard is not None
    assert len(markup.inline_keyboard) == 3
    assert markup.inline_keyboard[0][0].text == "📄 part_1.txt"
    assert markup.inline_keyboard[0][0].callback_data == "dl_file_part_1.txt"
    assert markup.inline_keyboard[1][0].text == "📄 part_2.txt"
    assert markup.inline_keyboard[1][0].callback_data == "dl_file_part_2.txt"
    assert markup.inline_keyboard[2][0].callback_data == "dl_back_dates"


def test_get_back_keyboard() -> None:
    """Test back keyboard structure contains single back button."""
    markup = get_back_keyboard()
    assert markup.inline_keyboard is not None
    assert len(markup.inline_keyboard) == 1
    assert markup.inline_keyboard[0][0].callback_data == "menu_back"


def test_get_cancel_keyboard() -> None:
    """Test cancel keyboard structure contains single Cancel button with cancel_fsm callback."""
    markup = get_cancel_keyboard()
    assert markup.inline_keyboard is not None
    assert len(markup.inline_keyboard) == 1
    assert markup.inline_keyboard[0][0].text == "[ ❌ Cancel ]"
    assert markup.inline_keyboard[0][0].callback_data == "cancel_fsm"


def test_get_sessions_keyboard_with_active_indicator() -> None:
    """Test session listing, active checkmark indicator, and back button."""
    sessions = ["account_alpha", "account_beta"]
    markup = get_sessions_keyboard(sessions, current="account_alpha")

    assert markup.inline_keyboard is not None
    assert len(markup.inline_keyboard) == 3

    btn1 = markup.inline_keyboard[0][0]
    btn2 = markup.inline_keyboard[1][0]
    btn_back = markup.inline_keyboard[2][0]

    assert btn1.text == "account_alpha ✅"
    assert btn1.callback_data == "select_session:account_alpha"

    assert btn2.text == "account_beta"
    assert btn2.callback_data == "select_session:account_beta"

    assert "Back" in btn_back.text
    assert btn_back.callback_data == "menu_session_mgr"


def test_get_sessions_keyboard_empty_list() -> None:
    """Test session keyboard with empty sessions list still contains Back button."""
    markup = get_sessions_keyboard([])
    assert markup.inline_keyboard is not None
    assert len(markup.inline_keyboard) == 1
    assert markup.inline_keyboard[0][0].callback_data == "menu_session_mgr"


def test_get_session_mgr_menu_structure() -> None:
    """Test Session Manager sub-menu structure renders 5 action buttons."""
    markup = get_session_mgr_menu()
    assert markup.inline_keyboard is not None
    assert len(markup.inline_keyboard) == 3

    # Row 1: Switch Active (btn 1) & Add New (btn 2)
    assert len(markup.inline_keyboard[0]) == 2
    assert markup.inline_keyboard[0][0].callback_data == "menu_switch_session"
    assert markup.inline_keyboard[0][1].callback_data == "menu_add_session"

    # Row 2: Rename (btn 1) & Delete (btn 2)
    assert len(markup.inline_keyboard[1]) == 2
    assert markup.inline_keyboard[1][0].callback_data == "menu_rename_session_list"
    assert markup.inline_keyboard[1][1].callback_data == "menu_delete_session_list"

    # Row 3: Back (btn 1)
    assert len(markup.inline_keyboard[2]) == 1
    assert markup.inline_keyboard[2][0].callback_data == "menu_back"


def test_get_rename_sessions_keyboard_structure() -> None:
    """Test rename session list keyboard formats buttons with rename_sess_ prefix and back button."""
    markup = get_rename_sessions_keyboard(["sess1", "sess2"])
    assert markup.inline_keyboard is not None
    assert len(markup.inline_keyboard) == 3
    assert markup.inline_keyboard[0][0].text == "✏️ sess1"
    assert markup.inline_keyboard[0][0].callback_data == "rename_sess_sess1"
    assert markup.inline_keyboard[1][0].text == "✏️ sess2"
    assert markup.inline_keyboard[1][0].callback_data == "rename_sess_sess2"
    assert markup.inline_keyboard[2][0].callback_data == "menu_session_mgr"


def test_get_delete_sessions_keyboard_structure() -> None:
    """Test delete session list keyboard formats buttons with del_sess_ prefix and back button."""
    markup = get_delete_sessions_keyboard(["sessA"])
    assert markup.inline_keyboard is not None
    assert len(markup.inline_keyboard) == 2
    assert markup.inline_keyboard[0][0].text == "🗑️ sessA"
    assert markup.inline_keyboard[0][0].callback_data == "del_sess_sessA"
    assert markup.inline_keyboard[1][0].callback_data == "menu_session_mgr"


# --- 2. Safe Callback Answer & Timeout Tests ---

@pytest.mark.asyncio
async def test_safe_callback_answer_handles_telegram_bad_request() -> None:
    """Test safe_callback_answer catches TelegramBadRequest without propagating exception."""
    mock_callback = MagicMock()
    # Simulate expired query error from Telegram
    method = MagicMock()
    mock_callback.answer = AsyncMock(
        side_effect=TelegramBadRequest(method=method, message="query is too old and response timeout expired")
    )

    # Should not raise exception
    await handlers.safe_callback_answer(mock_callback, "Test Text", show_alert=False)
    mock_callback.answer.assert_awaited_once_with("Test Text", show_alert=False)


# --- 3. Handler Workflow Tests ---

@pytest.mark.asyncio
async def test_start_command_handler(mocker: MockerFixture) -> None:
    """Test /start command clears FSM state, cleans up any login client, and answers with fresh main menu."""
    mock_cleanup = mocker.patch("bot_ui.login_handlers.cleanup_user_login_client", new_callable=AsyncMock)

    mock_state = MagicMock()
    mock_state.clear = AsyncMock()

    mock_message = MagicMock()
    mock_message.from_user.id = 12345
    mock_message.answer = AsyncMock()

    await handlers.start_command_handler(mock_message, mock_state)

    mock_state.clear.assert_awaited_once()
    mock_cleanup.assert_awaited_once_with(12345)
    mock_message.answer.assert_awaited_once()
    args, kwargs = mock_message.answer.call_args
    assert "Hybrid Telegram Control Panel" in kwargs["text"]
    assert "Menu Guide:" in kwargs["text"]
    assert kwargs["reply_markup"] is not None


@pytest.mark.asyncio
async def test_start_reply_callback_handler_triggers_process_manager(mocker: MockerFixture) -> None:
    """Test start reply button triggers start_userbot_task and updates reply markup to Stop button."""
    mocker.patch("bot_ui.handlers.get_user_active_session", return_value="acc1")
    mock_start_task = mocker.patch("bot_ui.handlers.start_userbot_task", new_callable=AsyncMock, return_value=True)

    mock_callback = MagicMock()
    mock_callback.from_user.id = 12345
    mock_callback.message.edit_reply_markup = AsyncMock()
    mock_callback.answer = AsyncMock()

    await handlers.start_reply_callback_handler(mock_callback)

    mock_start_task.assert_awaited_once_with("acc1")
    mock_callback.message.edit_reply_markup.assert_awaited_once()
    mock_callback.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_reply_callback_handler_no_session_validation(mocker: MockerFixture) -> None:
    """Test start reply with no session rejects launch, does NOT call start_userbot_task, and warns user."""
    mocker.patch("bot_ui.handlers.get_user_active_session", return_value=None)
    mock_start_task = mocker.patch("bot_ui.handlers.start_userbot_task", new_callable=AsyncMock)

    mock_callback = MagicMock()
    mock_callback.from_user.id = 12345
    mock_callback.answer = AsyncMock()

    await handlers.start_reply_callback_handler(mock_callback)

    mock_start_task.assert_not_called()
    mock_callback.answer.assert_awaited_once_with(
        "⚠️ Please select a Session (Account) first from the menu!",
        show_alert=True,
    )


@pytest.mark.asyncio
async def test_start_reply_callback_handler_already_running_concurrency(mocker: MockerFixture) -> None:
    """Test start reply when userbot is already running aborts launch and shows modal alert."""
    mocker.patch("bot_ui.handlers.get_user_active_session", return_value="acc1")
    mocker.patch("bot_ui.handlers.is_userbot_running", return_value=True)
    mock_start_task = mocker.patch("bot_ui.handlers.start_userbot_task", new_callable=AsyncMock)

    mock_callback = MagicMock()
    mock_callback.from_user.id = 12345
    mock_callback.answer = AsyncMock()

    await handlers.start_reply_callback_handler(mock_callback)

    mock_start_task.assert_not_called()
    mock_callback.answer.assert_awaited_once_with(
        "⚠️ Auto-Reply is ALREADY running for this session!",
        show_alert=True,
    )


@pytest.mark.asyncio
async def test_stop_reply_callback_handler_triggers_process_manager(mocker: MockerFixture) -> None:
    """Test stop reply button triggers stop_userbot_task and refreshes reply markup."""
    mocker.patch("bot_ui.handlers.get_user_active_session", return_value="acc1")
    mock_stop_task = mocker.patch("bot_ui.handlers.stop_userbot_task", new_callable=AsyncMock, return_value=True)

    mock_callback = MagicMock()
    mock_callback.from_user.id = 12345
    mock_callback.message.edit_reply_markup = AsyncMock()
    mock_callback.answer = AsyncMock()

    await handlers.stop_reply_callback_handler(mock_callback)

    mock_stop_task.assert_awaited_once_with("acc1")
    mock_callback.message.edit_reply_markup.assert_awaited_once()
    mock_callback.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_stop_reply_callback_handler_already_stopped(mocker: MockerFixture) -> None:
    """Test stop reply when task is already stopped warns user via soft toast."""
    mocker.patch("bot_ui.handlers.get_user_active_session", return_value="acc1")
    mocker.patch("bot_ui.handlers.stop_userbot_task", new_callable=AsyncMock, return_value=False)

    mock_callback = MagicMock()
    mock_callback.from_user.id = 12345
    mock_callback.answer = AsyncMock()

    await handlers.stop_reply_callback_handler(mock_callback)

    mock_callback.answer.assert_awaited_once_with(
        "⚠️ Process is already stopped.",
        show_alert=True,
    )


@pytest.mark.asyncio
async def test_extract_links_callback_handler_shows_target_menu(mocker: MockerFixture) -> None:
    """Test extract links callback renders the granular target selection sub-menu."""
    mocker.patch("bot_ui.handlers.get_user_active_session", return_value="acc1")

    mock_callback = MagicMock()
    mock_callback.from_user.id = 12345
    mock_callback.message.edit_text = AsyncMock()
    mock_callback.answer = AsyncMock()

    await handlers.extract_links_callback_handler(mock_callback)

    mock_callback.message.edit_text.assert_awaited_once()
    args, kwargs = mock_callback.message.edit_text.call_args
    assert "Select Link Extraction Target" in kwargs["text"]
    assert kwargs["reply_markup"] is not None
    mock_callback.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_extract_links_callback_handler_no_session_validation(mocker: MockerFixture) -> None:
    """Test extract links callback with no session warns user and does not open target menu."""
    mocker.patch("bot_ui.handlers.get_user_active_session", return_value=None)

    mock_callback = MagicMock()
    mock_callback.from_user.id = 12345
    mock_callback.message = MagicMock()
    mock_callback.message.edit_text = AsyncMock()
    mock_callback.answer = AsyncMock()

    await handlers.extract_links_callback_handler(mock_callback)

    mock_callback.message.edit_text.assert_not_called()
    mock_callback.answer.assert_awaited_once_with(
        "⚠️ Please select a Session (Account) first from the menu!",
        show_alert=True,
    )


@pytest.mark.asyncio
async def test_extract_target_callback_handler_transitions_to_date_prompt(mocker: MockerFixture) -> None:
    """Test selecting extraction target saves target in FSM state and prompts for date range."""
    mocker.patch("bot_ui.handlers.get_user_active_session", return_value="acc1")

    mock_state = MagicMock()
    mock_state.set_state = AsyncMock()
    mock_state.update_data = AsyncMock()

    mock_callback = MagicMock()
    mock_callback.from_user.id = 12345
    mock_callback.data = "extract_target:whatsapp"
    mock_callback.message.message_id = 456
    mock_callback.message.edit_text = AsyncMock()
    mock_callback.answer = AsyncMock()

    await handlers.extract_target_callback_handler(mock_callback, mock_state)

    mock_state.set_state.assert_awaited_once_with(ExtractionState.waiting_for_date_range)
    mock_state.update_data.assert_awaited_once_with(
        target="whatsapp",
        target_type="whatsapp",
        prompt_message_id=456,
    )
    mock_callback.message.edit_text.assert_awaited_once()
    args, kwargs = mock_callback.message.edit_text.call_args
    assert "WhatsApp Links" in kwargs["text"]
    assert kwargs["reply_markup"] is not None
    mock_callback.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_extract_target_callback_handler_no_session_validation(mocker: MockerFixture) -> None:
    """Test selecting extraction target with no session warns user and rejects FSM transition."""
    mocker.patch("bot_ui.handlers.get_user_active_session", return_value=None)

    mock_state = MagicMock()
    mock_state.set_state = AsyncMock()

    mock_callback = MagicMock()
    mock_callback.from_user.id = 12345
    mock_callback.data = "extract_target:whatsapp"
    mock_callback.answer = AsyncMock()

    await handlers.extract_target_callback_handler(mock_callback, mock_state)

    mock_state.set_state.assert_not_called()
    mock_callback.answer.assert_awaited_once_with(
        "⚠️ Please select a Session (Account) first from the menu!",
        show_alert=True,
    )


@pytest.mark.asyncio
async def test_extract_links_callback_handler_userbot_running_blocks_extraction(mocker: MockerFixture) -> None:
    """Test extract links callback is blocked if userbot is currently running on the session."""
    mocker.patch("bot_ui.handlers.get_user_active_session", return_value="acc1")
    mocker.patch("bot_ui.handlers.is_userbot_running", return_value=True)

    mock_callback = MagicMock()
    mock_callback.from_user.id = 12345
    mock_callback.message = MagicMock()
    mock_callback.message.edit_text = AsyncMock()
    mock_callback.answer = AsyncMock()

    await handlers.extract_links_callback_handler(mock_callback)

    mock_callback.message.edit_text.assert_not_called()
    mock_callback.answer.assert_awaited_once_with(
        "⚠️ STOP the Auto-Reply first! You cannot run Extractor and Auto-Reply on the same account simultaneously.",
        show_alert=True,
    )


@pytest.mark.asyncio
async def test_process_date_range_extraction_handler_userbot_running_blocks_extraction(mocker: MockerFixture) -> None:
    """Test process date range blocks extraction launch if userbot is currently running."""
    mocker.patch("bot_ui.handlers.get_user_active_session", return_value="acc1")
    mocker.patch("bot_ui.handlers.is_userbot_running", return_value=True)
    mock_start_ext = mocker.patch("bot_ui.handlers.start_extraction_task", new_callable=AsyncMock)

    mock_state = MagicMock()
    mock_state.clear = AsyncMock()
    mock_state.get_data = AsyncMock(return_value={"prompt_message_id": 456, "target": "whatsapp"})

    mock_message = MagicMock()
    mock_message.from_user.id = 12345
    mock_message.text = "2026-08-01 to 2026-08-08"
    mock_message.delete = AsyncMock()
    mock_message.bot = MagicMock()
    mock_message.bot.edit_message_text = AsyncMock()

    await handlers.process_date_range_extraction_handler(mock_message, mock_state)

    mock_start_ext.assert_not_called()
    mock_message.bot.edit_message_text.assert_awaited_once()
    args, kwargs = mock_message.bot.edit_message_text.call_args
    assert "Concurrency Conflict" in kwargs["text"]


@pytest.mark.asyncio
async def test_stop_extraction_callback_handler(mocker: MockerFixture) -> None:
    """Test stop extraction button cancels background extraction task and updates reply markup."""
    mocker.patch("bot_ui.handlers.get_user_active_session", return_value="acc1")
    mock_stop_ext = mocker.patch("bot_ui.handlers.stop_extraction_task", new_callable=AsyncMock, return_value=True)

    mock_callback = MagicMock()
    mock_callback.from_user.id = 12345
    mock_callback.message.edit_reply_markup = AsyncMock()
    mock_callback.answer = AsyncMock()

    await handlers.stop_extraction_callback_handler(mock_callback)

    mock_stop_ext.assert_awaited_once_with("acc1")
    mock_callback.message.edit_reply_markup.assert_awaited_once()
    mock_callback.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_stop_extraction_callback_handler_already_stopped(mocker: MockerFixture) -> None:
    """Test stop extraction when task is already stopped warns user via soft toast."""
    mocker.patch("bot_ui.handlers.get_user_active_session", return_value="acc1")
    mocker.patch("bot_ui.handlers.stop_extraction_task", new_callable=AsyncMock, return_value=False)

    mock_callback = MagicMock()
    mock_callback.from_user.id = 12345
    mock_callback.answer = AsyncMock()

    await handlers.stop_extraction_callback_handler(mock_callback)

    mock_callback.answer.assert_awaited_once_with(
        "⚠️ Process is already stopped.",
        show_alert=True,
    )


@pytest.mark.asyncio
async def test_cancel_fsm_callback_handler(mocker: MockerFixture) -> None:
    """Test cancel button clears FSM state and restores main dashboard with full keyboard."""
    mocker.patch("bot_ui.handlers.get_user_active_session", return_value="acc1")
    mocker.patch("bot_ui.handlers.is_userbot_running", return_value=False)
    mocker.patch("bot_ui.handlers.is_extraction_running", return_value=False)

    mock_state = MagicMock()
    mock_state.clear = AsyncMock()

    mock_callback = MagicMock()
    mock_callback.from_user.id = 12345
    mock_callback.message.edit_text = AsyncMock()
    mock_callback.answer = AsyncMock()

    await handlers.cancel_fsm_callback_handler(mock_callback, mock_state)

    mock_state.clear.assert_awaited_once()
    mock_callback.message.edit_text.assert_awaited_once()
    mock_callback.answer.assert_awaited_once_with("❌ Operation cancelled.")


@pytest.mark.asyncio
async def test_process_date_range_extraction_handler_invalid_format(mocker: MockerFixture) -> None:
    """Test invalid date format deletes user message, edits prompt to show error, and preserves FSM state."""
    mocker.patch("bot_ui.handlers.get_user_active_session", return_value="acc1")

    mock_state = MagicMock()
    mock_state.clear = AsyncMock()
    mock_state.get_data = AsyncMock(return_value={"prompt_message_id": 456, "target": "whatsapp"})

    mock_message = MagicMock()
    mock_message.from_user.id = 12345
    mock_message.text = "invalid-date-format"
    mock_message.delete = AsyncMock()
    mock_message.bot.edit_message_text = AsyncMock()

    await handlers.process_date_range_extraction_handler(mock_message, mock_state)

    # Asserts that incoming user message is deleted immediately
    mock_message.delete.assert_awaited_once()
    mock_state.clear.assert_not_called()
    mock_message.bot.edit_message_text.assert_awaited_once()
    args, kwargs = mock_message.bot.edit_message_text.call_args
    assert kwargs["message_id"] == 456
    assert "Invalid date format!" in kwargs["text"]
    assert kwargs["reply_markup"] is not None


@pytest.mark.asyncio
async def test_process_date_range_extraction_handler_success(mocker: MockerFixture) -> None:
    """Test valid date range input deletes user message, passes target_type, and launches task."""
    mocker.patch("bot_ui.handlers.get_user_active_session", return_value="acc1")
    mock_start_ext = mocker.patch("bot_ui.handlers.start_extraction_task", new_callable=AsyncMock, return_value=True)

    mock_state = MagicMock()
    mock_state.clear = AsyncMock()
    mock_state.get_data = AsyncMock(return_value={"prompt_message_id": 456, "target": "whatsapp"})

    mock_message = MagicMock()
    mock_message.from_user.id = 12345
    mock_message.text = "2026-08-01 to 2026-08-08"
    mock_message.delete = AsyncMock()
    mock_message.bot = MagicMock()
    mock_message.bot.edit_message_text = AsyncMock()

    await handlers.process_date_range_extraction_handler(mock_message, mock_state)

    # Single Message UI: user message deleted, prompt edited
    mock_message.delete.assert_awaited_once()
    mock_state.clear.assert_awaited_once()
    mock_start_ext.assert_awaited_once()
    start_kwargs = mock_start_ext.call_args[1]
    assert start_kwargs["target_type"] == "whatsapp"

    mock_message.bot.edit_message_text.assert_awaited_once()
    args, kwargs = mock_message.bot.edit_message_text.call_args
    assert kwargs["message_id"] == 456
    assert "Starting global extraction" in kwargs["text"]
    assert "WhatsApp Links" in kwargs["text"]


@pytest.mark.asyncio
async def test_system_stats_callback_handler(mocker: MockerFixture) -> None:
    """Test system statistics view compiles metrics, async granular link counts, and renders back button."""
    mocker.patch("bot_ui.handlers.get_user_active_session", return_value="acc1")
    mocker.patch("bot_ui.handlers.is_userbot_running", return_value=True)
    mocker.patch("bot_ui.handlers.is_extraction_running", return_value=False)
    mocker.patch(
        "bot_ui.handlers.get_total_links_count_async",
        new_callable=AsyncMock,
        return_value={"whatsapp": 100, "telegram_groups": 40, "telegram_folders": 10, "total": 150},
    )
    mocker.patch("bot_ui.handlers.get_all_link_files", return_value=["file1.txt", "file2.txt"])

    mock_callback = MagicMock()
    mock_callback.from_user.id = 12345
    mock_callback.message.edit_text = AsyncMock()
    mock_callback.answer = AsyncMock()

    await handlers.system_stats_callback_handler(mock_callback)

    mock_callback.answer.assert_awaited_once()
    mock_callback.message.edit_text.assert_awaited_once()
    args, kwargs = mock_callback.message.edit_text.call_args
    assert "System Statistics Dashboard" in kwargs["text"]
    assert "WhatsApp: <b>100</b>" in kwargs["text"]
    assert "TG Groups: <b>40</b>" in kwargs["text"]
    assert "TG Folders: <b>10</b>" in kwargs["text"]
    assert "Total Links Saved:</b> <b>150</b>" in kwargs["text"]
    assert kwargs["reply_markup"] is not None


@pytest.mark.asyncio
async def test_open_downloads_menu_callback_handler() -> None:
    """Test opening the downloads sub-menu renders the category selection keyboard."""
    mock_callback = MagicMock()
    mock_callback.from_user.id = 12345
    mock_callback.message.edit_text = AsyncMock()
    mock_callback.answer = AsyncMock()

    await handlers.open_downloads_menu_callback_handler(mock_callback)

    mock_callback.message.edit_text.assert_awaited_once()
    args, kwargs = mock_callback.message.edit_text.call_args
    assert "Select which category of links you want to download:" in kwargs["text"]
    assert kwargs["reply_markup"] is not None
    mock_callback.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_download_category_callback_handler_empty_soft_alert(mocker: MockerFixture) -> None:
    """Test category download alerts user with friendly soft toast when no dates exist."""
    mocker.patch("bot_ui.handlers.get_available_dates_for_category", return_value=[])

    mock_state = MagicMock()
    mock_callback = MagicMock()
    mock_callback.from_user.id = 12345
    mock_callback.data = "dl_whatsapp"
    mock_callback.answer = AsyncMock()

    await handlers.download_category_callback_handler(mock_callback, mock_state)

    mock_callback.answer.assert_awaited_once_with(
        "📭 No links found in this category yet. Try extracting some first! 😊",
        show_alert=True,
    )


@pytest.mark.asyncio
async def test_download_category_callback_handler_renders_dates(mocker: MockerFixture) -> None:
    """Test category selection transitions to selecting_date and renders dates keyboard."""
    mocker.patch("bot_ui.handlers.get_available_dates_for_category", return_value=["2026-08-11"])

    mock_state = MagicMock()
    mock_state.set_state = AsyncMock()
    mock_state.update_data = AsyncMock()

    mock_callback = MagicMock()
    mock_callback.from_user.id = 12345
    mock_callback.data = "dl_whatsapp"
    mock_callback.message.edit_text = AsyncMock()
    mock_callback.answer = AsyncMock()

    await handlers.download_category_callback_handler(mock_callback, mock_state)

    mock_state.set_state.assert_awaited_once_with(DownloadState.selecting_date)
    mock_state.update_data.assert_awaited_once_with(category="whatsapp", category_title="📱 WhatsApp")
    mock_callback.message.edit_text.assert_awaited_once()
    args, kwargs = mock_callback.message.edit_text.call_args
    assert "Download: 📱 WhatsApp" in kwargs["text"]
    assert kwargs["reply_markup"] is not None


@pytest.mark.asyncio
async def test_download_date_callback_handler_renders_files(mocker: MockerFixture) -> None:
    """Test selecting a download date transitions to selecting_file and renders files keyboard."""
    mocker.patch(
        "bot_ui.handlers.get_files_for_category_and_date",
        return_value=["part_1.txt", "part_2.txt"],
    )

    mock_state = MagicMock()
    mock_state.get_data = AsyncMock(return_value={"category": "whatsapp", "category_title": "📱 WhatsApp"})
    mock_state.set_state = AsyncMock()
    mock_state.update_data = AsyncMock()

    mock_callback = MagicMock()
    mock_callback.from_user.id = 12345
    mock_callback.data = "dl_date_2026-08-11"
    mock_callback.message.edit_text = AsyncMock()
    mock_callback.answer = AsyncMock()

    await handlers.download_date_callback_handler(mock_callback, mock_state)

    mock_state.set_state.assert_awaited_once_with(DownloadState.selecting_file)
    mock_state.update_data.assert_awaited_once_with(selected_date="2026-08-11")
    mock_callback.message.edit_text.assert_awaited_once()
    args, kwargs = mock_callback.message.edit_text.call_args
    assert "Download: 📱 WhatsApp" in kwargs["text"]
    assert "2026-08-11" in kwargs["text"]
    assert kwargs["reply_markup"] is not None


@pytest.mark.asyncio
async def test_download_back_to_dates_callback_handler(mocker: MockerFixture) -> None:
    """Test back to dates navigation renders date list again."""
    mocker.patch("bot_ui.handlers.get_available_dates_for_category", return_value=["2026-08-11"])

    mock_state = MagicMock()
    mock_state.get_data = AsyncMock(return_value={"category": "whatsapp", "category_title": "📱 WhatsApp"})
    mock_state.set_state = AsyncMock()

    mock_callback = MagicMock()
    mock_callback.from_user.id = 12345
    mock_callback.data = "dl_back_dates"
    mock_callback.message.edit_text = AsyncMock()
    mock_callback.answer = AsyncMock()

    await handlers.download_back_to_dates_callback_handler(mock_callback, mock_state)

    mock_state.set_state.assert_awaited_once_with(DownloadState.selecting_date)
    mock_callback.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_download_file_callback_handler_delivers_single_file(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    """Test selecting a specific file sends document attachment, deletes old menu, and resends menu at bottom."""
    mocker.patch.object(handlers, "LINKS_DIR", tmp_path)
    target_dir = tmp_path / "2026-08-11" / "whatsapp"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / "part_1.txt"
    target_file.write_text("https://chat.whatsapp.com/TestLink1\n", encoding="utf-8")

    mock_state = MagicMock()
    mock_state.get_data = AsyncMock(
        return_value={
            "category": "whatsapp",
            "selected_date": "2026-08-11",
            "category_title": "📱 WhatsApp",
        }
    )

    mock_callback = MagicMock()
    mock_callback.from_user.id = 12345
    mock_callback.data = "dl_file_part_1.txt"
    mock_callback.answer = AsyncMock()
    mock_callback.message.html_text = "<b>Download: 📱 WhatsApp</b>"
    mock_callback.message.reply_markup = MagicMock()
    mock_callback.message.answer_document = AsyncMock()
    mock_callback.message.delete = AsyncMock()
    mock_callback.message.answer = AsyncMock()

    await handlers.download_file_callback_handler(mock_callback, mock_state)

    mock_callback.message.answer_document.assert_awaited_once()
    mock_callback.message.delete.assert_awaited_once()
    mock_callback.message.answer.assert_awaited_once_with(
        text="<b>Download: 📱 WhatsApp</b>",
        reply_markup=mock_callback.message.reply_markup,
        parse_mode="HTML",
    )
    mock_callback.answer.assert_awaited_once_with("✅ File sent!", show_alert=False)



@pytest.mark.asyncio
async def test_switch_session_callback_handler(mocker: MockerFixture) -> None:
    """Test switch session callback queries available sessions and edits message."""
    mocker.patch("bot_ui.handlers.get_available_sessions", return_value=["acc1", "acc2"])

    mock_callback = MagicMock()
    mock_callback.from_user.id = 12345
    mock_callback.message.edit_text = AsyncMock()
    mock_callback.answer = AsyncMock()

    await handlers.switch_session_callback_handler(mock_callback)

    mock_callback.message.edit_text.assert_awaited_once()
    mock_callback.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_select_session_callback_handler(mocker: MockerFixture) -> None:
    """Test selecting a session updates in-memory state and updates view."""
    mocker.patch("bot_ui.handlers.get_available_sessions", return_value=["acc1", "acc2"])

    mock_callback = MagicMock()
    mock_callback.from_user.id = 12345
    mock_callback.data = "select_session:acc2"
    mock_callback.message.edit_text = AsyncMock()
    mock_callback.answer = AsyncMock()

    await handlers.select_session_callback_handler(mock_callback)

    assert handlers.get_user_active_session(12345) == "acc2"
    mock_callback.message.edit_text.assert_awaited_once()
    mock_callback.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_back_to_main_menu_callback_handler() -> None:
    """Test back button callback renders dashboard back to user."""
    mock_callback = MagicMock()
    mock_callback.from_user.id = 12345
    mock_callback.message.edit_text = AsyncMock()
    mock_callback.answer = AsyncMock()

    await handlers.back_to_main_menu_callback_handler(mock_callback)

    mock_callback.message.edit_text.assert_awaited_once()
    mock_callback.answer.assert_awaited_once()


# --- 4. Sessions Manager Handler Tests ---

@pytest.mark.asyncio
async def test_session_mgr_callback_handler(mocker: MockerFixture) -> None:
    """Test session manager button opens Session Manager sub-menu with session stats."""
    mocker.patch("bot_ui.handlers.get_available_sessions", return_value=["acc1", "acc2"])
    mocker.patch("bot_ui.handlers.get_user_active_session", return_value="acc1")

    mock_callback = MagicMock()
    mock_callback.from_user.id = 12345
    mock_callback.message.edit_text = AsyncMock()
    mock_callback.answer = AsyncMock()

    await handlers.session_mgr_callback_handler(mock_callback)

    mock_callback.message.edit_text.assert_awaited_once()
    args, kwargs = mock_callback.message.edit_text.call_args
    assert "Sessions Manager Dashboard" in kwargs["text"]
    assert "Total Sessions: <b>2</b>" in kwargs["text"]
    mock_callback.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_rename_session_list_callback_handler_empty(mocker: MockerFixture) -> None:
    """Test rename session list shows soft alert when no sessions are available."""
    mocker.patch("bot_ui.handlers.get_available_sessions", return_value=[])

    mock_callback = MagicMock()
    mock_callback.from_user.id = 12345
    mock_callback.answer = AsyncMock()

    await handlers.rename_session_list_callback_handler(mock_callback)

    mock_callback.answer.assert_awaited_once_with(
        "📭 No sessions found to rename. Add one first!",
        show_alert=True,
    )


@pytest.mark.asyncio
async def test_rename_session_list_callback_handler_has_sessions(mocker: MockerFixture) -> None:
    """Test rename session list renders rename buttons for available sessions."""
    mocker.patch("bot_ui.handlers.get_available_sessions", return_value=["acc1", "acc2"])

    mock_callback = MagicMock()
    mock_callback.from_user.id = 12345
    mock_callback.message.edit_text = AsyncMock()
    mock_callback.answer = AsyncMock()

    await handlers.rename_session_list_callback_handler(mock_callback)

    mock_callback.message.edit_text.assert_awaited_once()
    args, kwargs = mock_callback.message.edit_text.call_args
    assert "Rename Session" in kwargs["text"]
    assert kwargs["reply_markup"] is not None


@pytest.mark.asyncio
async def test_rename_sess_select_callback_handler(mocker: MockerFixture) -> None:
    """Test selecting a session for rename sets FSM state and prompts for new name."""
    mock_state = MagicMock()
    mock_state.set_state = AsyncMock()
    mock_state.update_data = AsyncMock()

    mock_callback = MagicMock()
    mock_callback.from_user.id = 12345
    mock_callback.data = "rename_sess_acc1"
    mock_callback.message.message_id = 99
    mock_callback.message.edit_text = AsyncMock()
    mock_callback.answer = AsyncMock()

    await handlers.rename_sess_select_callback_handler(mock_callback, mock_state)

    mock_state.set_state.assert_awaited_once_with(SessionState.waiting_for_new_session_name)
    mock_state.update_data.assert_awaited_once_with(
        old_session_name="acc1",
        prompt_message_id=99,
    )
    mock_callback.message.edit_text.assert_awaited_once()
    args, kwargs = mock_callback.message.edit_text.call_args
    assert "Target Session: <code>acc1</code>" in kwargs["text"]


@pytest.mark.asyncio
async def test_process_new_session_name_handler_invalid_format(mocker: MockerFixture) -> None:
    """Test invalid session name format rejects and keeps cancel keyboard."""
    mock_state = MagicMock()
    mock_state.get_data = AsyncMock(return_value={"old_session_name": "acc1", "prompt_message_id": 99})

    mock_bot = MagicMock()
    mock_bot.edit_message_text = AsyncMock()

    mock_msg = MagicMock()
    mock_msg.from_user.id = 12345
    mock_msg.text = "!invalid name with spaces!"
    mock_msg.bot = mock_bot
    mock_msg.delete = AsyncMock()

    await handlers.process_new_session_name_handler(mock_msg, mock_state)

    mock_msg.delete.assert_awaited_once()
    mock_bot.edit_message_text.assert_awaited_once()
    args, kwargs = mock_bot.edit_message_text.call_args
    assert "Invalid Session Name" in kwargs["text"]


@pytest.mark.asyncio
async def test_process_new_session_name_handler_duplicate(mocker: MockerFixture) -> None:
    """Test duplicate session name rejects and informs user."""
    mocker.patch("bot_ui.handlers.get_available_sessions", return_value=["acc1", "acc_duplicate"])

    mock_state = MagicMock()
    mock_state.get_data = AsyncMock(return_value={"old_session_name": "acc1", "prompt_message_id": 99})

    mock_bot = MagicMock()
    mock_bot.edit_message_text = AsyncMock()

    mock_msg = MagicMock()
    mock_msg.from_user.id = 12345
    mock_msg.text = "acc_duplicate"
    mock_msg.bot = mock_bot
    mock_msg.delete = AsyncMock()

    await handlers.process_new_session_name_handler(mock_msg, mock_state)

    mock_msg.delete.assert_awaited_once()
    mock_bot.edit_message_text.assert_awaited_once()
    args, kwargs = mock_bot.edit_message_text.call_args
    assert "Session Name Already Exists" in kwargs["text"]


@pytest.mark.asyncio
async def test_process_new_session_name_handler_success(mocker: MockerFixture) -> None:
    """Test valid new session name renames session file, updates active session, and returns to menu."""
    mocker.patch("bot_ui.handlers.get_available_sessions", return_value=["acc1"])
    mock_rename = mocker.patch("bot_ui.handlers.rename_session", return_value=True)
    mocker.patch("bot_ui.handlers.get_user_active_session", return_value="acc1")
    mock_set_active = mocker.patch("bot_ui.handlers.set_user_active_session")

    mock_state = MagicMock()
    mock_state.get_data = AsyncMock(return_value={"old_session_name": "acc1", "prompt_message_id": 99})
    mock_state.clear = AsyncMock()

    mock_bot = MagicMock()
    mock_bot.edit_message_text = AsyncMock()

    mock_msg = MagicMock()
    mock_msg.from_user.id = 12345
    mock_msg.text = "acc_renamed"
    mock_msg.bot = mock_bot
    mock_msg.delete = AsyncMock()

    await handlers.process_new_session_name_handler(mock_msg, mock_state)

    mock_msg.delete.assert_awaited_once()
    mock_rename.assert_called_once_with("acc1", "acc_renamed")
    mock_set_active.assert_called_once_with(12345, "acc_renamed")
    mock_state.clear.assert_awaited_once()
    mock_bot.edit_message_text.assert_awaited_once()
    args, kwargs = mock_bot.edit_message_text.call_args
    assert "Session Renamed Successfully" in kwargs["text"]


@pytest.mark.asyncio
async def test_delete_session_list_callback_handler_empty(mocker: MockerFixture) -> None:
    """Test delete session list shows soft alert when no sessions are available."""
    mocker.patch("bot_ui.handlers.get_available_sessions", return_value=[])

    mock_callback = MagicMock()
    mock_callback.from_user.id = 12345
    mock_callback.answer = AsyncMock()

    await handlers.delete_session_list_callback_handler(mock_callback)

    mock_callback.answer.assert_awaited_once_with(
        "📭 No sessions found to delete.",
        show_alert=True,
    )


@pytest.mark.asyncio
async def test_delete_session_list_callback_handler_has_sessions(mocker: MockerFixture) -> None:
    """Test delete session list renders delete buttons for available sessions."""
    mocker.patch("bot_ui.handlers.get_available_sessions", return_value=["acc1", "acc2"])

    mock_callback = MagicMock()
    mock_callback.from_user.id = 12345
    mock_callback.message.edit_text = AsyncMock()
    mock_callback.answer = AsyncMock()

    await handlers.delete_session_list_callback_handler(mock_callback)

    mock_callback.message.edit_text.assert_awaited_once()
    args, kwargs = mock_callback.message.edit_text.call_args
    assert "Delete Session" in kwargs["text"]
    assert kwargs["reply_markup"] is not None


@pytest.mark.asyncio
async def test_del_sess_select_callback_handler_success(mocker: MockerFixture) -> None:
    """Test deleting a session stops workers, deletes file, clears active state, and alerts user."""
    mocker.patch("bot_ui.handlers.is_userbot_running", return_value=True)
    mocker.patch("bot_ui.handlers.is_extraction_running", return_value=False)
    mock_stop_userbot = mocker.patch("bot_ui.handlers.stop_userbot_task", new_callable=AsyncMock)
    mock_delete = mocker.patch("bot_ui.handlers.delete_session", return_value=True)
    mocker.patch("bot_ui.handlers.get_available_sessions", return_value=["acc_remaining"])
    handlers.user_states[12345] = "acc_to_delete"

    mock_callback = MagicMock()
    mock_callback.from_user.id = 12345
    mock_callback.data = "del_sess_acc_to_delete"
    mock_callback.message.edit_text = AsyncMock()
    mock_callback.answer = AsyncMock()

    await handlers.del_sess_select_callback_handler(mock_callback)

    mock_stop_userbot.assert_awaited_once_with("acc_to_delete")
    mock_delete.assert_called_once_with("acc_to_delete")
    assert handlers.get_user_active_session(12345) is None
    mock_callback.answer.assert_awaited_once_with("🗑️ Session 'acc_to_delete' deleted!", show_alert=True)
    mock_callback.message.edit_text.assert_awaited_once()

