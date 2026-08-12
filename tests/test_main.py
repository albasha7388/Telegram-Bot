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
async def test_health_check_endpoint() -> None:
    """Test health check HTTP endpoint returns expected 200 response and text."""
    mock_request = MagicMock()
    response = await main_app.health_check(mock_request)
    assert response.status == 200
    assert response.text == "Bot is alive!"


@pytest.mark.asyncio
async def test_start_dummy_server_binding(mocker: MockerFixture) -> None:
    """Test start_dummy_server sets up aiohttp Application, AppRunner, and TCPSite."""
    mock_app = MagicMock()
    mocker.patch("aiohttp.web.Application", return_value=mock_app)

    mock_runner = MagicMock()
    mock_runner.setup = AsyncMock()
    mocker.patch("aiohttp.web.AppRunner", return_value=mock_runner)

    mock_site = MagicMock()
    mock_site.start = AsyncMock()
    mock_tcp_site = mocker.patch("aiohttp.web.TCPSite", return_value=mock_site)

    mocker.patch.dict("os.environ", {"PORT": "8080"})

    await main_app.start_dummy_server()

    mock_app.router.add_get.assert_called_once_with('/', main_app.health_check)
    mock_runner.setup.assert_awaited_once()
    mock_tcp_site.assert_called_once_with(mock_runner, '0.0.0.0', 8080)
    mock_site.start.assert_awaited_once()


@pytest.mark.asyncio
async def test_main_polling_loop_invocation(mocker: MockerFixture) -> None:
    """Test that main() properly initializes components, starts dummy server, starts scheduler, and executes start_polling."""
    mock_bot = MagicMock()
    mock_bot.session.close = AsyncMock()

    mock_dp = MagicMock()
    mock_dp.start_polling = AsyncMock()

    mock_scheduler = MagicMock()
    mock_start_scheduler = mocker.patch("main.start_scheduler", return_value=mock_scheduler)

    mocker.patch("main.create_bot", return_value=mock_bot)
    mocker.patch("main.create_dispatcher", return_value=mock_dp)
    mock_start_dummy = mocker.patch("main.start_dummy_server", return_value=None)

    await main_app.main()

    mock_start_scheduler.assert_called_once()
    mock_start_dummy.assert_called_once()
    mock_dp.start_polling.assert_awaited_once_with(mock_bot, drop_pending_updates=True)
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
