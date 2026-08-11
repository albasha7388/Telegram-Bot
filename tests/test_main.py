"""
Unit tests for the main application entry point, dispatcher wiring, and CLI tools.
"""

from unittest.mock import AsyncMock, MagicMock
import pytest
from pytest_mock import MockerFixture

import main as main_app
from bot_ui.handlers import router as ui_router
from bot_ui.joiner_handlers import router as joiner_router
from bot_ui.login_handlers import router as login_router
from tools.create_session import create_new_session, sanitize_session_name


# --- 1. Main Entry Point & Dispatcher Tests ---

def test_create_dispatcher_includes_ui_and_login_routers() -> None:
    """Test that create_dispatcher properly attaches the bot_ui, login, and joiner routers."""
    dp = main_app.create_dispatcher()
    assert dp is not None
    assert ui_router in dp.sub_routers
    assert login_router in dp.sub_routers
    assert joiner_router in dp.sub_routers


def test_create_bot_custom_token() -> None:
    """Test Bot instance creation with explicit token."""
    bot = main_app.create_bot("123456789:ABCDefGhiJklMnoPqrStuVwxYz")
    assert bot.token == "123456789:ABCDefGhiJklMnoPqrStuVwxYz"


@pytest.mark.asyncio
async def test_main_polling_loop_invocation(mocker: MockerFixture) -> None:
    """Test that main() properly initializes components, starts scheduler, and executes start_polling."""
    mock_bot = MagicMock()
    mock_bot.session.close = AsyncMock()

    mock_dp = MagicMock()
    mock_dp.start_polling = AsyncMock()

    mock_scheduler = MagicMock()
    mock_start_scheduler = mocker.patch("main.start_scheduler", return_value=mock_scheduler)

    mocker.patch("main.create_bot", return_value=mock_bot)
    mocker.patch("main.create_dispatcher", return_value=mock_dp)

    await main_app.main()

    mock_start_scheduler.assert_called_once()
    mock_dp.start_polling.assert_awaited_once_with(mock_bot)
    mock_scheduler.shutdown.assert_called_once_with(wait=False)
    mock_bot.session.close.assert_awaited_once()


# --- 2. Session Creation CLI Tool Tests ---

def test_sanitize_session_name_rules() -> None:
    """Test input sanitization and stripping of .session file extensions."""
    assert sanitize_session_name("student_helper.session") == "student_helper"
    assert sanitize_session_name("secondary account #1") == "secondary_account__1"

    with pytest.raises(ValueError, match="must contain alphanumeric characters"):
        sanitize_session_name("   ")

    with pytest.raises(ValueError, match="must contain alphanumeric characters"):
        sanitize_session_name("!@#$%^&*()")


def test_create_new_session_flow(mocker: MockerFixture) -> None:
    """Test interactive session creation context flow using a mocked Pyrogram client."""
    mock_me = MagicMock()
    mock_me.id = 123456789
    mock_me.username = "test_student_bot"
    mock_me.first_name = "StudentBot"

    mock_client_instance = MagicMock()
    mock_client_instance.get_me.return_value = mock_me
    mock_client_instance.__enter__.return_value = mock_client_instance
    mock_client_instance.__exit__.return_value = None

    mocker.patch("tools.create_session.Client", return_value=mock_client_instance)

    session_name = create_new_session("test_account")
    assert session_name == "test_account"
    mock_client_instance.get_me.assert_called_once()
