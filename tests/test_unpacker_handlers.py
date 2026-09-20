"""
Tests for the Folder Unpacking UI handlers.
"""

from unittest.mock import AsyncMock, patch
import pytest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, User, Document

from bot_ui.states import UnpackerState
from bot_ui.unpacker_handlers import start_unpacker_handler, process_unpacker_input

@pytest.fixture
def mock_state() -> FSMContext:
    state = AsyncMock(spec=FSMContext)
    state.get_data.return_value = {"session_name": "test_session"}
    return state

@pytest.fixture
def mock_callback() -> CallbackQuery:
    cb = AsyncMock(spec=CallbackQuery)
    cb.from_user = User(id=123, is_bot=False, first_name="Test")
    cb.message = AsyncMock(spec=Message)
    cb.message.edit_text = AsyncMock()
    cb.answer = AsyncMock()
    return cb

@pytest.fixture
def mock_message() -> Message:
    msg = AsyncMock(spec=Message)
    msg.from_user = User(id=123, is_bot=False, first_name="Test")
    msg.bot = AsyncMock()
    msg.answer = AsyncMock()
    return msg

@pytest.mark.asyncio
async def test_start_unpacker_handler(mock_callback, mock_state) -> None:
    """Test start_unpacker_handler sets state and prompts user."""
    with patch("bot_ui.unpacker_handlers.get_user_active_session", return_value="test_session"), \
         patch("bot_ui.unpacker_handlers.is_userbot_running", return_value=False):
        
        await start_unpacker_handler(mock_callback, mock_state)
        
        mock_state.set_state.assert_called_once_with(UnpackerState.waiting_for_input)
        mock_state.update_data.assert_called_once_with(session_name="test_session")
        mock_callback.message.edit_text.assert_called_once()
        assert "Folder Unpacker: Input Links" in mock_callback.message.edit_text.call_args[1]["text"]

@pytest.mark.asyncio
async def test_process_unpacker_input_text(mock_message, mock_state) -> None:
    """Test process_unpacker_input correctly parses text input."""
    mock_message.text = "Here are some folders:\nhttps://t.me/addlist/slug1\nt.me/group (ignore)\nhttps://t.me/addlist/slug2"
    mock_message.document = None
    
    with patch("bot_ui.unpacker_handlers.get_user_active_session", return_value="test_session"), \
         patch("bot_ui.unpacker_handlers.active_unpackers", {}), \
         patch("bot_ui.unpacker_handlers.run_folder_unpacker_task") as mock_task:
        
        await process_unpacker_input(mock_message, mock_state)
        
        mock_state.clear.assert_called_once()
        mock_message.answer.assert_called_once()
        assert "Detected Folder Links: <b>2</b>" in mock_message.answer.call_args[1]["text"]
        
        # Unpacker task should have been added
        from bot_ui.unpacker_handlers import active_unpackers
        assert "test_session" in active_unpackers
