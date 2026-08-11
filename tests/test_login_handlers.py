"""
Unit tests for the In-Bot Session Creation (Login FSM) router and handlers.

Verifies session name validation, phone number formatting, MTProto Client lifecycle,
OTP sign-in flow, 2FA password verification, Single Message UI updates, message deletions,
and comprehensive exception handling with clean resource cleanup.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from pytest_mock import MockerFixture
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Chat, Message, User
from pyrogram.errors import (
    FloodWait,
    PasswordHashInvalid,
    PhoneCodeExpired,
    PhoneCodeInvalid,
    PhoneNumberBanned,
    PhoneNumberInvalid,
    PhoneNumberUnoccupied,
    RPCError,
    SessionPasswordNeeded,
)

from bot_ui import login_handlers
from bot_ui.handlers import cancel_fsm_callback_handler, get_user_active_session, set_user_active_session
from bot_ui.states import LoginState


@pytest.fixture
def fsm_storage() -> MemoryStorage:
    """Create an isolated in-memory FSM storage instance."""
    return MemoryStorage()


@pytest.fixture
def fsm_context(fsm_storage: MemoryStorage) -> FSMContext:
    """Instantiate a real FSMContext bound to a test user and chat."""
    key = StorageKey(bot_id=123456, chat_id=987654321, user_id=987654321)
    return FSMContext(storage=fsm_storage, key=key)


@pytest.fixture
def mock_user() -> User:
    """Provide a standard Telegram User mock."""
    return User(id=987654321, is_bot=False, first_name="Admin", username="admin_user")


@pytest.fixture
def mock_chat() -> Chat:
    """Provide a standard Telegram Chat mock."""
    return Chat(id=987654321, type="private", title="Admin Chat")


# --- 1. Client Cleanup & Resource Management Tests ---

@pytest.mark.asyncio
async def test_cleanup_user_login_client_connected() -> None:
    """Test that cleanup_user_login_client safely disconnects a connected client."""
    mock_client = MagicMock()
    mock_client.is_connected = True
    mock_client.disconnect = AsyncMock()

    login_handlers._active_login_clients[987654321] = mock_client
    await login_handlers.cleanup_user_login_client(987654321)

    mock_client.disconnect.assert_awaited_once()
    assert 987654321 not in login_handlers._active_login_clients


@pytest.mark.asyncio
async def test_cleanup_user_login_client_disconnected() -> None:
    """Test that cleanup_user_login_client does not error on an already disconnected client."""
    mock_client = MagicMock()
    mock_client.is_connected = False
    mock_client.disconnect = AsyncMock()

    login_handlers._active_login_clients[987654321] = mock_client
    await login_handlers.cleanup_user_login_client(987654321)

    mock_client.disconnect.assert_not_awaited()
    assert 987654321 not in login_handlers._active_login_clients


@pytest.mark.asyncio
async def test_cleanup_user_login_client_handles_exception() -> None:
    """Test that cleanup_user_login_client catches disconnect exceptions gracefully."""
    mock_client = MagicMock()
    mock_client.is_connected = True
    mock_client.disconnect = AsyncMock(side_effect=RuntimeError("Socket failed"))

    login_handlers._active_login_clients[987654321] = mock_client
    await login_handlers.cleanup_user_login_client(987654321)

    assert 987654321 not in login_handlers._active_login_clients


# --- 2. Step 1: Trigger Add Session ---

@pytest.mark.asyncio
async def test_start_add_session_handler(
    mock_user: User, mock_chat: Chat, fsm_context: FSMContext, mocker: MockerFixture
) -> None:
    """Test clicking menu_add_session initiates FSM and renders Step 1 prompt."""
    mock_msg = MagicMock(spec=Message)
    mock_msg.message_id = 42
    mock_msg.edit_text = AsyncMock()

    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.from_user = mock_user
    mock_cb.message = mock_msg
    mock_cb.answer = AsyncMock()

    cleanup_mock = mocker.patch("bot_ui.login_handlers.cleanup_user_login_client", new_callable=AsyncMock)

    await login_handlers.start_add_session_handler(mock_cb, fsm_context)

    cleanup_mock.assert_awaited_once_with(mock_user.id)
    current_state = await fsm_context.get_state()
    assert current_state == LoginState.waiting_for_session_name.state

    state_data = await fsm_context.get_data()
    assert state_data.get("prompt_message_id") == 42
    mock_msg.edit_text.assert_awaited_once()
    assert "Add New Session (Step 1/3)" in mock_msg.edit_text.call_args.kwargs["text"]


# --- 3. Step 2: Session Name Validation ---

@pytest.mark.asyncio
async def test_process_session_name_valid(
    mock_user: User, mock_chat: Chat, fsm_context: FSMContext, mocker: MockerFixture
) -> None:
    """Test submitting a valid session name transitions to waiting_for_phone."""
    await fsm_context.set_state(LoginState.waiting_for_session_name)
    await fsm_context.update_data(prompt_message_id=42)

    mocker.patch("bot_ui.login_handlers.get_available_sessions", return_value=["account_old"])

    mock_bot = MagicMock()
    mock_bot.edit_message_text = AsyncMock()

    mock_msg = MagicMock(spec=Message)
    mock_msg.from_user = mock_user
    mock_msg.chat = mock_chat
    mock_msg.text = "account_marketing_2"
    mock_msg.bot = mock_bot
    mock_msg.delete = AsyncMock()

    await login_handlers.process_session_name_handler(mock_msg, fsm_context)

    mock_msg.delete.assert_awaited_once()
    current_state = await fsm_context.get_state()
    assert current_state == LoginState.waiting_for_phone.state

    state_data = await fsm_context.get_data()
    assert state_data.get("session_name") == "account_marketing_2"

    mock_bot.edit_message_text.assert_awaited_once()
    assert "Step 2/3" in mock_bot.edit_message_text.call_args.kwargs["text"]


@pytest.mark.asyncio
async def test_process_session_name_invalid_characters(
    mock_user: User, mock_chat: Chat, fsm_context: FSMContext
) -> None:
    """Test submitting an invalid session name rejects with error and keeps state."""
    await fsm_context.set_state(LoginState.waiting_for_session_name)
    await fsm_context.update_data(prompt_message_id=42)

    mock_bot = MagicMock()
    mock_bot.edit_message_text = AsyncMock()

    mock_msg = MagicMock(spec=Message)
    mock_msg.from_user = mock_user
    mock_msg.chat = mock_chat
    mock_msg.text = "invalid name with spaces!"
    mock_msg.bot = mock_bot
    mock_msg.delete = AsyncMock()

    await login_handlers.process_session_name_handler(mock_msg, fsm_context)

    mock_msg.delete.assert_awaited_once()
    current_state = await fsm_context.get_state()
    assert current_state == LoginState.waiting_for_session_name.state

    mock_bot.edit_message_text.assert_awaited_once()
    assert "Invalid Session Name" in mock_bot.edit_message_text.call_args.kwargs["text"]


@pytest.mark.asyncio
async def test_process_session_name_duplicate_rejected(
    mock_user: User, mock_chat: Chat, fsm_context: FSMContext, mocker: MockerFixture
) -> None:
    """Test submitting a duplicate existing session name is rejected."""
    await fsm_context.set_state(LoginState.waiting_for_session_name)
    await fsm_context.update_data(prompt_message_id=42)

    mocker.patch("bot_ui.login_handlers.get_available_sessions", return_value=["account_existing"])

    mock_bot = MagicMock()
    mock_bot.edit_message_text = AsyncMock()

    mock_msg = MagicMock(spec=Message)
    mock_msg.from_user = mock_user
    mock_msg.chat = mock_chat
    mock_msg.text = "account_existing"
    mock_msg.bot = mock_bot
    mock_msg.delete = AsyncMock()

    await login_handlers.process_session_name_handler(mock_msg, fsm_context)

    mock_msg.delete.assert_awaited_once()
    current_state = await fsm_context.get_state()
    assert current_state == LoginState.waiting_for_session_name.state

    mock_bot.edit_message_text.assert_awaited_once()
    assert "Session Already Exists" in mock_bot.edit_message_text.call_args.kwargs["text"]


# --- 4. Step 3: Phone Number, Client Initialization & Code Sending ---

@pytest.mark.asyncio
async def test_process_phone_number_success(
    mock_user: User, mock_chat: Chat, fsm_context: FSMContext, mocker: MockerFixture
) -> None:
    """Test valid phone number initializes Client, connects, and sends OTP code."""
    await fsm_context.set_state(LoginState.waiting_for_phone)
    await fsm_context.update_data(prompt_message_id=42, session_name="test_session")

    mock_sent_code = MagicMock()
    mock_sent_code.phone_code_hash = "hash_xyz_123"

    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    mock_client.send_code = AsyncMock(return_value=mock_sent_code)

    mock_client_cls = mocker.patch("bot_ui.login_handlers.Client", return_value=mock_client)

    mock_bot = MagicMock()
    mock_bot.edit_message_text = AsyncMock()

    mock_msg = MagicMock(spec=Message)
    mock_msg.from_user = mock_user
    mock_msg.chat = mock_chat
    mock_msg.text = "+1 (555) 123-4567"
    mock_msg.bot = mock_bot
    mock_msg.delete = AsyncMock()

    await login_handlers.process_phone_number_handler(mock_msg, fsm_context)

    mock_msg.delete.assert_awaited_once()
    mock_client_cls.assert_called_once()
    mock_client.connect.assert_awaited_once()
    mock_client.send_code.assert_awaited_once_with("+15551234567")

    current_state = await fsm_context.get_state()
    assert current_state == LoginState.waiting_for_code.state

    state_data = await fsm_context.get_data()
    assert state_data.get("phone") == "+15551234567"
    assert state_data.get("phone_code_hash") == "hash_xyz_123"


@pytest.mark.asyncio
async def test_process_phone_number_invalid_format(
    mock_user: User, mock_chat: Chat, fsm_context: FSMContext
) -> None:
    """Test invalid phone string is rejected without initializing Client."""
    await fsm_context.set_state(LoginState.waiting_for_phone)
    await fsm_context.update_data(prompt_message_id=42, session_name="test_session")

    mock_bot = MagicMock()
    mock_bot.edit_message_text = AsyncMock()

    mock_msg = MagicMock(spec=Message)
    mock_msg.from_user = mock_user
    mock_msg.chat = mock_chat
    mock_msg.text = "abc123"
    mock_msg.bot = mock_bot
    mock_msg.delete = AsyncMock()

    await login_handlers.process_phone_number_handler(mock_msg, fsm_context)

    mock_msg.delete.assert_awaited_once()
    current_state = await fsm_context.get_state()
    assert current_state == LoginState.waiting_for_phone.state

    mock_bot.edit_message_text.assert_awaited_once()
    assert "Invalid Phone Number Format" in mock_bot.edit_message_text.call_args.kwargs["text"]


@pytest.mark.asyncio
async def test_process_phone_number_flood_wait_handled(
    mock_user: User, mock_chat: Chat, fsm_context: FSMContext, mocker: MockerFixture
) -> None:
    """Test FloodWait during send_code cleans up client and notifies user."""
    await fsm_context.set_state(LoginState.waiting_for_phone)
    await fsm_context.update_data(prompt_message_id=42, session_name="test_session")

    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    flood_exc = FloodWait(value=45)
    mock_client.send_code = AsyncMock(side_effect=flood_exc)

    mocker.patch("bot_ui.login_handlers.Client", return_value=mock_client)
    cleanup_mock = mocker.patch("bot_ui.login_handlers.cleanup_user_login_client", new_callable=AsyncMock)

    mock_bot = MagicMock()
    mock_bot.edit_message_text = AsyncMock()

    mock_msg = MagicMock(spec=Message)
    mock_msg.from_user = mock_user
    mock_msg.chat = mock_chat
    mock_msg.text = "+15551234567"
    mock_msg.bot = mock_bot
    mock_msg.delete = AsyncMock()

    await login_handlers.process_phone_number_handler(mock_msg, fsm_context)

    cleanup_mock.assert_awaited_once_with(mock_user.id)
    current_state = await fsm_context.get_state()
    assert current_state is None

    assert any("FloodWait" in str(call) for call in mock_bot.edit_message_text.call_args_list)


@pytest.mark.asyncio
async def test_process_phone_number_unoccupied_phone(
    mock_user: User, mock_chat: Chat, fsm_context: FSMContext, mocker: MockerFixture
) -> None:
    """Test PhoneNumberUnoccupied cleans up client and displays clear feedback."""
    await fsm_context.set_state(LoginState.waiting_for_phone)
    await fsm_context.update_data(prompt_message_id=42, session_name="test_session")

    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    mock_client.send_code = AsyncMock(side_effect=PhoneNumberUnoccupied())

    mocker.patch("bot_ui.login_handlers.Client", return_value=mock_client)
    cleanup_mock = mocker.patch("bot_ui.login_handlers.cleanup_user_login_client", new_callable=AsyncMock)

    mock_bot = MagicMock()
    mock_bot.edit_message_text = AsyncMock()

    mock_msg = MagicMock(spec=Message)
    mock_msg.from_user = mock_user
    mock_msg.chat = mock_chat
    mock_msg.text = "+15551234567"
    mock_msg.bot = mock_bot
    mock_msg.delete = AsyncMock()

    await login_handlers.process_phone_number_handler(mock_msg, fsm_context)

    cleanup_mock.assert_awaited_once_with(mock_user.id)
    current_state = await fsm_context.get_state()
    assert current_state is None

    assert any("Unoccupied" in str(call) or "Invalid" in str(call) for call in mock_bot.edit_message_text.call_args_list)


# --- 5. Step 4: OTP Code Sign In & 2FA Detection ---

@pytest.mark.asyncio
async def test_process_otp_code_success_no_2fa(
    mock_user: User, mock_chat: Chat, fsm_context: FSMContext, mocker: MockerFixture
) -> None:
    """Test valid OTP sign in completes successfully when no 2FA is needed."""
    await fsm_context.set_state(LoginState.waiting_for_code)
    await fsm_context.update_data(
        prompt_message_id=42,
        session_name="account_success",
        phone="+15551234567",
        phone_code_hash="hash123",
    )

    mock_client = MagicMock()
    mock_client.sign_in = AsyncMock()
    login_handlers._active_login_clients[mock_user.id] = mock_client

    cleanup_mock = mocker.patch("bot_ui.login_handlers.cleanup_user_login_client", new_callable=AsyncMock)
    set_session_mock = mocker.patch("bot_ui.login_handlers.set_user_active_session")

    mock_bot = MagicMock()
    mock_bot.edit_message_text = AsyncMock()

    mock_msg = MagicMock(spec=Message)
    mock_msg.from_user = mock_user
    mock_msg.chat = mock_chat
    mock_msg.text = "1 2 3 4 5"
    mock_msg.bot = mock_bot
    mock_msg.delete = AsyncMock()

    await login_handlers.process_otp_code_handler(mock_msg, fsm_context)

    mock_msg.delete.assert_awaited_once()
    mock_client.sign_in.assert_awaited_once_with(
        phone_number="+15551234567",
        phone_code_hash="hash123",
        phone_code="12345",
    )
    cleanup_mock.assert_awaited_once_with(mock_user.id)
    set_session_mock.assert_called_once_with(mock_user.id, "account_success")

    current_state = await fsm_context.get_state()
    assert current_state is None
    assert "Session Created Successfully" in mock_bot.edit_message_text.call_args.kwargs["text"]


@pytest.mark.asyncio
async def test_process_otp_code_requires_2fa(
    mock_user: User, mock_chat: Chat, fsm_context: FSMContext
) -> None:
    """Test SessionPasswordNeeded error transitions state to waiting_for_password."""
    await fsm_context.set_state(LoginState.waiting_for_code)
    await fsm_context.update_data(
        prompt_message_id=42,
        session_name="account_2fa",
        phone="+15551234567",
        phone_code_hash="hash123",
    )

    mock_client = MagicMock()
    mock_client.sign_in = AsyncMock(side_effect=SessionPasswordNeeded())
    login_handlers._active_login_clients[mock_user.id] = mock_client

    mock_bot = MagicMock()
    mock_bot.edit_message_text = AsyncMock()

    mock_msg = MagicMock(spec=Message)
    mock_msg.from_user = mock_user
    mock_msg.chat = mock_chat
    mock_msg.text = "12345"
    mock_msg.bot = mock_bot
    mock_msg.delete = AsyncMock()

    await login_handlers.process_otp_code_handler(mock_msg, fsm_context)

    mock_msg.delete.assert_awaited_once()
    current_state = await fsm_context.get_state()
    assert current_state == LoginState.waiting_for_password.state

    assert "Two-Step Verification (2FA) Required" in mock_bot.edit_message_text.call_args.kwargs["text"]


@pytest.mark.asyncio
async def test_process_otp_code_invalid_code_error(
    mock_user: User, mock_chat: Chat, fsm_context: FSMContext, mocker: MockerFixture
) -> None:
    """Test PhoneCodeInvalid error cleans up client and notifies user."""
    await fsm_context.set_state(LoginState.waiting_for_code)
    await fsm_context.update_data(
        prompt_message_id=42,
        session_name="account_fail",
        phone="+15551234567",
        phone_code_hash="hash123",
    )

    mock_client = MagicMock()
    mock_client.sign_in = AsyncMock(side_effect=PhoneCodeInvalid())
    login_handlers._active_login_clients[mock_user.id] = mock_client

    cleanup_mock = mocker.patch("bot_ui.login_handlers.cleanup_user_login_client", new_callable=AsyncMock)

    mock_bot = MagicMock()
    mock_bot.edit_message_text = AsyncMock()

    mock_msg = MagicMock(spec=Message)
    mock_msg.from_user = mock_user
    mock_msg.chat = mock_chat
    mock_msg.text = "99999"
    mock_msg.bot = mock_bot
    mock_msg.delete = AsyncMock()

    await login_handlers.process_otp_code_handler(mock_msg, fsm_context)

    cleanup_mock.assert_awaited_once_with(mock_user.id)
    current_state = await fsm_context.get_state()
    assert current_state is None

    assert "Invalid or Expired Code" in mock_bot.edit_message_text.call_args.kwargs["text"]


# --- 6. Step 5: 2FA Password Verification ---

@pytest.mark.asyncio
async def test_process_2fa_password_success(
    mock_user: User, mock_chat: Chat, fsm_context: FSMContext, mocker: MockerFixture
) -> None:
    """Test valid 2FA password completes login successfully."""
    await fsm_context.set_state(LoginState.waiting_for_password)
    await fsm_context.update_data(
        prompt_message_id=42,
        session_name="account_2fa_success",
    )

    mock_client = MagicMock()
    mock_client.check_password = AsyncMock()
    login_handlers._active_login_clients[mock_user.id] = mock_client

    cleanup_mock = mocker.patch("bot_ui.login_handlers.cleanup_user_login_client", new_callable=AsyncMock)
    set_session_mock = mocker.patch("bot_ui.login_handlers.set_user_active_session")

    mock_bot = MagicMock()
    mock_bot.edit_message_text = AsyncMock()

    mock_msg = MagicMock(spec=Message)
    mock_msg.from_user = mock_user
    mock_msg.chat = mock_chat
    mock_msg.text = "super_secret_2fa_password"
    mock_msg.bot = mock_bot
    mock_msg.delete = AsyncMock()

    await login_handlers.process_2fa_password_handler(mock_msg, fsm_context)

    mock_msg.delete.assert_awaited_once()
    mock_client.check_password.assert_awaited_once_with(password="super_secret_2fa_password")
    cleanup_mock.assert_awaited_once_with(mock_user.id)
    set_session_mock.assert_called_once_with(mock_user.id, "account_2fa_success")

    current_state = await fsm_context.get_state()
    assert current_state is None
    assert "2FA Verified" in mock_bot.edit_message_text.call_args.kwargs["text"]


@pytest.mark.asyncio
async def test_process_2fa_password_invalid(
    mock_user: User, mock_chat: Chat, fsm_context: FSMContext, mocker: MockerFixture
) -> None:
    """Test PasswordHashInvalid cleans up client and notifies user."""
    await fsm_context.set_state(LoginState.waiting_for_password)
    await fsm_context.update_data(
        prompt_message_id=42,
        session_name="account_2fa_fail",
    )

    mock_client = MagicMock()
    mock_client.check_password = AsyncMock(side_effect=PasswordHashInvalid())
    login_handlers._active_login_clients[mock_user.id] = mock_client

    cleanup_mock = mocker.patch("bot_ui.login_handlers.cleanup_user_login_client", new_callable=AsyncMock)

    mock_bot = MagicMock()
    mock_bot.edit_message_text = AsyncMock()

    mock_msg = MagicMock(spec=Message)
    mock_msg.from_user = mock_user
    mock_msg.chat = mock_chat
    mock_msg.text = "wrong_password"
    mock_msg.bot = mock_bot
    mock_msg.delete = AsyncMock()

    await login_handlers.process_2fa_password_handler(mock_msg, fsm_context)

    mock_msg.delete.assert_awaited_once()
    cleanup_mock.assert_awaited_once_with(mock_user.id)
    current_state = await fsm_context.get_state()
    assert current_state is None
    assert "Invalid 2FA Password" in mock_bot.edit_message_text.call_args.kwargs["text"]


# --- 7. FSM Cancellation & Cleanup Tests ---

@pytest.mark.asyncio
async def test_cancel_fsm_cleans_up_login_client(
    mock_user: User, fsm_context: FSMContext, mocker: MockerFixture
) -> None:
    """Test cancelling FSM during login flow disconnects temporary client and restores main menu."""
    await fsm_context.set_state(LoginState.waiting_for_code)
    await fsm_context.update_data(session_name="temp_acc")

    mock_client = MagicMock()
    mock_client.is_connected = True
    mock_client.disconnect = AsyncMock()
    login_handlers._active_login_clients[mock_user.id] = mock_client

    mock_msg = MagicMock(spec=Message)
    mock_msg.edit_text = AsyncMock()

    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.from_user = mock_user
    mock_cb.message = mock_msg
    mock_cb.answer = AsyncMock()

    await cancel_fsm_callback_handler(mock_cb, fsm_context)

    mock_client.disconnect.assert_awaited_once()
    assert mock_user.id not in login_handlers._active_login_clients

    current_state = await fsm_context.get_state()
    assert current_state is None
    mock_msg.edit_text.assert_awaited_once()
