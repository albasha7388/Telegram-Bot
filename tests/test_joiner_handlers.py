"""
Unit tests for the Auto-Joiner FSM and Aiogram handler workflows.

Verifies active session verification, date folder scanning, file listing,
FSM state transitions, and background joiner task spawning.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest
from pytest_mock import MockerFixture
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Chat, User

from bot_ui import joiner_handlers
from bot_ui.states import JoinerState


@pytest.fixture
def mock_user() -> User:
    """Provide a mock Telegram User object."""
    return User(id=12345, is_bot=False, first_name="Admin")


@pytest.fixture
def mock_chat() -> Chat:
    """Provide a mock Telegram Chat object."""
    return Chat(id=12345, type="private")


# --- 1. Helper Function Tests ---

def test_get_available_group_dates_scanning(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test get_available_group_dates correctly discovers date folders containing telegram_groups .txt files."""
    mocker.patch.object(joiner_handlers, "LINKS_DIR", tmp_path)

    d1 = tmp_path / "acc1" / "2026-08-10" / "telegram_groups"
    d1.mkdir(parents=True, exist_ok=True)
    (d1 / "part_1.txt").write_text("https://t.me/g1")

    d2 = tmp_path / "acc1" / "2026-08-11" / "telegram_groups"
    d2.mkdir(parents=True, exist_ok=True)
    (d2 / "part_1.txt").write_text("https://t.me/g2")

    # Empty date folder (no txt files)
    d3 = tmp_path / "acc1" / "2026-08-12" / "telegram_groups"
    d3.mkdir(parents=True, exist_ok=True)

    # Another session
    d_other = tmp_path / "acc2" / "2026-08-15" / "telegram_groups"
    d_other.mkdir(parents=True, exist_ok=True)
    (d_other / "part_1.txt").write_text("https://t.me/g3")

    dates = joiner_handlers.get_available_group_dates(session_name="acc1")
    assert dates == ["2026-08-11", "2026-08-10"]


def test_get_group_files_for_date_scanning(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test get_group_files_for_date correctly returns sorted part files."""
    mocker.patch.object(joiner_handlers, "LINKS_DIR", tmp_path)

    tg_dir = tmp_path / "acc1" / "2026-08-11" / "telegram_groups"
    tg_dir.mkdir(parents=True, exist_ok=True)
    (tg_dir / "part_2.txt").write_text("link2")
    (tg_dir / "part_1.txt").write_text("link1")
    (tg_dir / "notes.txt").write_text("notes")

    files = joiner_handlers.get_group_files_for_date("2026-08-11", session_name="acc1")
    assert files == ["part_1.txt", "part_2.txt", "notes.txt"]


# --- 2. Handler Step 1: Browse Dates Tests ---

@pytest.mark.asyncio
async def test_start_auto_join_handler_no_active_session(
    mock_user: User, mock_chat: Chat, mocker: MockerFixture
) -> None:
    """Test start auto-join alerts user when no session is active."""
    mocker.patch("bot_ui.joiner_handlers.get_user_active_session", return_value=None)

    mock_state = MagicMock(spec=FSMContext)
    mock_callback = MagicMock(spec=CallbackQuery)
    mock_callback.from_user = mock_user
    mock_callback.answer = AsyncMock()

    await joiner_handlers.start_auto_join_handler(mock_callback, mock_state)

    mock_callback.answer.assert_awaited_once_with(
        "⚠️ No active session! Please select or add an account in Sessions Manager first.",
        show_alert=True,
    )


@pytest.mark.asyncio
async def test_start_auto_join_handler_no_dates_found(
    mock_user: User, mock_chat: Chat, mocker: MockerFixture
) -> None:
    """Test start auto-join alerts user when no date folders contain link files."""
    mocker.patch("bot_ui.joiner_handlers.get_user_active_session", return_value="acc1")
    mocker.patch("bot_ui.joiner_handlers.get_available_group_dates", return_value=[])

    mock_state = MagicMock(spec=FSMContext)
    mock_callback = MagicMock(spec=CallbackQuery)
    mock_callback.from_user = mock_user
    mock_callback.answer = AsyncMock()

    await joiner_handlers.start_auto_join_handler(mock_callback, mock_state)

    mock_callback.answer.assert_awaited_once_with(
        "📭 No Telegram group links found for session 'acc1' in storage yet. Extract some links first!",
        show_alert=True,
    )


@pytest.mark.asyncio
async def test_start_auto_join_handler_success_renders_dates(
    mock_user: User, mock_chat: Chat, mocker: MockerFixture
) -> None:
    """Test start auto-join sets selecting_date state and renders dates keyboard."""
    mocker.patch("bot_ui.joiner_handlers.get_user_active_session", return_value="acc1")
    mocker.patch("bot_ui.joiner_handlers.get_available_group_dates", return_value=["2026-08-11"])

    mock_state = MagicMock(spec=FSMContext)
    mock_state.set_state = AsyncMock()
    mock_state.update_data = AsyncMock()

    mock_callback = MagicMock(spec=CallbackQuery)
    mock_callback.from_user = mock_user
    mock_callback.message = MagicMock()
    mock_callback.message.edit_text = AsyncMock()
    mock_callback.answer = AsyncMock()

    await joiner_handlers.start_auto_join_handler(mock_callback, mock_state)

    mock_state.set_state.assert_awaited_once_with(JoinerState.selecting_date)
    mock_state.update_data.assert_awaited_once_with(session_name="acc1")
    mock_callback.message.edit_text.assert_awaited_once()
    args, kwargs = mock_callback.message.edit_text.call_args
    assert "Auto-Joiner: Select Date" in kwargs["text"]
    assert kwargs["reply_markup"] is not None


# --- 3. Handler Step 2: Browse Files Tests ---

@pytest.mark.asyncio
async def test_select_joiner_date_handler_no_files(
    mock_user: User, mock_chat: Chat, mocker: MockerFixture
) -> None:
    """Test selecting a date with no files alerts the user."""
    mocker.patch("bot_ui.joiner_handlers.get_user_active_session", return_value="acc1")
    mocker.patch("bot_ui.joiner_handlers.get_group_files_for_date", return_value=[])

    mock_state = MagicMock(spec=FSMContext)
    mock_state.get_data = AsyncMock(return_value={"session_name": "acc1"})
    mock_callback = MagicMock(spec=CallbackQuery)
    mock_callback.from_user = mock_user
    mock_callback.data = "jdate_2026-08-11"
    mock_callback.answer = AsyncMock()

    await joiner_handlers.select_joiner_date_handler(mock_callback, mock_state)

    mock_callback.answer.assert_awaited_once_with(
        "📭 No group link files found for date 2026-08-11 in session 'acc1'.",
        show_alert=True,
    )


@pytest.mark.asyncio
async def test_select_joiner_date_handler_success_renders_files(
    mock_user: User, mock_chat: Chat, mocker: MockerFixture
) -> None:
    """Test selecting a date transitions to selecting_file and renders files keyboard."""
    mocker.patch("bot_ui.joiner_handlers.get_user_active_session", return_value="acc1")
    mocker.patch("bot_ui.joiner_handlers.get_group_files_for_date", return_value=["part_1.txt", "part_2.txt"])

    mock_state = MagicMock(spec=FSMContext)
    mock_state.get_data = AsyncMock(return_value={"session_name": "acc1"})
    mock_state.set_state = AsyncMock()
    mock_state.update_data = AsyncMock()

    mock_callback = MagicMock(spec=CallbackQuery)
    mock_callback.from_user = mock_user
    mock_callback.data = "jdate_2026-08-11"
    mock_callback.message = MagicMock()
    mock_callback.message.edit_text = AsyncMock()
    mock_callback.answer = AsyncMock()

    await joiner_handlers.select_joiner_date_handler(mock_callback, mock_state)

    mock_state.set_state.assert_awaited_once_with(JoinerState.selecting_file)
    mock_state.update_data.assert_awaited_once_with(selected_date="2026-08-11", session_name="acc1")
    mock_callback.message.edit_text.assert_awaited_once()
    args, kwargs = mock_callback.message.edit_text.call_args
    assert "Auto-Joiner: Select File" in kwargs["text"]
    assert kwargs["reply_markup"] is not None


# --- 4. Handler Step 3: Execute Auto-Join Tests ---

@pytest.mark.asyncio
async def test_select_joiner_file_handler_file_not_found(
    mock_user: User, mock_chat: Chat, tmp_path: Path, mocker: MockerFixture
) -> None:
    """Test choosing a missing file alerts user and clears state."""
    mocker.patch.object(joiner_handlers, "LINKS_DIR", tmp_path)
    mocker.patch("bot_ui.joiner_handlers.get_user_active_session", return_value="acc1")

    mock_state = MagicMock(spec=FSMContext)
    mock_state.get_data = AsyncMock(return_value={"selected_date": "2026-08-11", "session_name": "acc1"})
    mock_state.clear = AsyncMock()

    mock_callback = MagicMock(spec=CallbackQuery)
    mock_callback.from_user = mock_user
    mock_callback.data = "jfile_part_missing.txt"
    mock_callback.answer = AsyncMock()

    await joiner_handlers.select_joiner_file_handler(mock_callback, mock_state)

    mock_state.clear.assert_awaited_once()
    mock_callback.answer.assert_awaited_once()
    assert "not found" in str(mock_callback.answer.call_args)


@pytest.mark.asyncio
async def test_select_joiner_file_handler_success_spawns_task(
    mock_user: User, mock_chat: Chat, tmp_path: Path, mocker: MockerFixture
) -> None:
    """Test selecting a valid file clears state, updates UI, and launches background joiner task."""
    mocker.patch.object(joiner_handlers, "LINKS_DIR", tmp_path)
    mocker.patch("bot_ui.joiner_handlers.get_user_active_session", return_value="acc1")
    mock_run_task = mocker.patch("bot_ui.joiner_handlers.run_auto_join_task", new_callable=AsyncMock)

    tg_dir = tmp_path / "acc1" / "2026-08-11" / "telegram_groups"
    tg_dir.mkdir(parents=True, exist_ok=True)
    target_file = tg_dir / "part_1.txt"
    target_file.write_text("https://t.me/g1")

    mock_state = MagicMock(spec=FSMContext)
    mock_state.get_data = AsyncMock(return_value={"selected_date": "2026-08-11", "session_name": "acc1"})
    mock_state.clear = AsyncMock()

    mock_callback = MagicMock(spec=CallbackQuery)
    mock_callback.from_user = mock_user
    mock_callback.data = "jfile_part_1.txt"
    mock_callback.bot = MagicMock()
    mock_callback.message = MagicMock()
    mock_callback.message.chat.id = 12345
    mock_callback.message.message_id = 99
    mock_callback.message.edit_text = AsyncMock()
    mock_callback.answer = AsyncMock()

    await joiner_handlers.select_joiner_file_handler(mock_callback, mock_state)

    mock_state.clear.assert_awaited_once()
    mock_callback.message.edit_text.assert_awaited_once()
    args, kwargs = mock_callback.message.edit_text.call_args
    assert "Starting Auto-Joiner Engine" in kwargs["text"]
    mock_callback.answer.assert_awaited_once_with("🚀 Auto-Joiner started!")


@pytest.mark.asyncio
async def test_select_joiner_file_handler_userbot_running_blocks_joiner(
    mock_user: User, mock_chat: Chat, mocker: MockerFixture
) -> None:
    """Test select joiner file prevents starting Auto-Joiner if Auto-Reply is running on the same session."""
    mocker.patch("bot_ui.joiner_handlers.get_user_active_session", return_value="acc1")
    mocker.patch("bot_ui.joiner_handlers.is_userbot_running", return_value=True)
    mock_run_task = mocker.patch("bot_ui.joiner_handlers.run_auto_join_task", new_callable=AsyncMock)

    mock_state = MagicMock(spec=FSMContext)
    mock_state.clear = AsyncMock()

    mock_callback = MagicMock(spec=CallbackQuery)
    mock_callback.from_user = mock_user
    mock_callback.data = "jfile_part_1.txt"
    mock_callback.answer = AsyncMock()

    await joiner_handlers.select_joiner_file_handler(mock_callback, mock_state)

    mock_run_task.assert_not_called()
    mock_callback.answer.assert_awaited_once_with(
        "⚠️ STOP the Auto-Reply first! You cannot run Joiner and Auto-Reply on the same account simultaneously.",
        show_alert=True,
    )


@pytest.mark.asyncio
async def test_start_auto_join_handler_userbot_running_blocks_joiner(
    mock_user: User, mock_chat: Chat, mocker: MockerFixture
) -> None:
    """Test start auto-join prevents opening date selection if Auto-Reply is running on the same session."""
    mocker.patch("bot_ui.joiner_handlers.get_user_active_session", return_value="acc1")
    mocker.patch("bot_ui.joiner_handlers.is_userbot_running", return_value=True)

    mock_state = MagicMock(spec=FSMContext)
    mock_callback = MagicMock(spec=CallbackQuery)
    mock_callback.from_user = mock_user
    mock_callback.answer = AsyncMock()

    await joiner_handlers.start_auto_join_handler(mock_callback, mock_state)

    mock_callback.answer.assert_awaited_once_with(
        "⚠️ STOP the Auto-Reply first! You cannot run Joiner and Auto-Reply on the same account simultaneously.",
        show_alert=True,
    )


@pytest.mark.asyncio
async def test_stop_joiner_callback_handler_triggers_stop_joiner_task(
    mock_user: User, mocker: MockerFixture
) -> None:
    """Test stop joiner callback calls stop_joiner_task and alerts user with modal toast."""
    mock_stop = mocker.patch("bot_ui.joiner_handlers.stop_joiner_task", return_value=True)

    mock_callback = MagicMock(spec=CallbackQuery)
    mock_callback.from_user = mock_user
    mock_callback.data = "stop_joiner_test_session"
    mock_callback.answer = AsyncMock()

    await joiner_handlers.stop_joiner_callback_handler(mock_callback)

    mock_stop.assert_called_once_with("test_session")
    mock_callback.answer.assert_awaited_once_with("🛑 Sending abort signal...", show_alert=True)


def test_get_joiner_progress_keyboard_structure() -> None:
    """Test get_joiner_progress_keyboard generates single Stop Auto-Joiner button."""
    from bot_ui.keyboards import get_joiner_progress_keyboard
    markup = get_joiner_progress_keyboard("sess_gamma")
    assert markup.inline_keyboard is not None
    assert len(markup.inline_keyboard) == 1
    button = markup.inline_keyboard[0][0]
    assert button.text == "⏹️ Stop Auto-Joiner"
    assert button.callback_data == "stop_joiner_sess_gamma"
