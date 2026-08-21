"""
Unit tests for Pyrogram userbot client, rate-limiting, verbose logging, and bulletproof error-handling mechanisms.
"""

import asyncio
import logging
import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock
import pytest
from pytest_mock import MockerFixture
from pyrogram.errors import PeerIdInvalid, UserIsBlocked, UserPrivacyRestricted

from config.settings import MAX_DAILY_DMS
from userbot import client as userbot_client


@pytest.fixture(autouse=True)
def reset_rate_limits() -> None:
    """Reset the daily DM quota counter and clear active clients before each test."""
    userbot_client.reset_dm_counter()
    userbot_client.active_userbot_clients.clear()


@pytest.mark.asyncio
async def test_handle_auto_reply_successful_dm(mocker: MockerFixture) -> None:
    """Test that a valid student inquiry triggers DM send_message and increments counter."""
    mocker.patch("userbot.client.evaluate_message", return_value=True)
    mocker.patch("userbot.client.random.uniform", return_value=0.01)
    mock_sleep = mocker.patch("asyncio.sleep", new_callable=AsyncMock)

    mock_client = MagicMock()
    mock_client.name = "alpha_session"
    mock_client.send_message = AsyncMock()

    mock_message = MagicMock()
    mock_message.text = "ابي احد يحل لي واجب ضروري"
    mock_message.from_user.id = 987654321

    await userbot_client.handle_auto_reply(mock_client, mock_message)

    mock_sleep.assert_awaited_once_with(0.01)
    mock_client.send_message.assert_awaited_once()
    call_args = mock_client.send_message.call_args[1]
    assert call_args["chat_id"] == 987654321
    assert "خدمات" in call_args["text"] or "نقدم" in call_args["text"]
    assert userbot_client._daily_dm_count == 1
    assert userbot_client.daily_dms_count["alpha_session"] == 1


@pytest.mark.asyncio
async def test_handle_auto_reply_ab_messaging_toggle(mocker: MockerFixture) -> None:
    """Test that A/B messages toggle sequentially."""
    mocker.patch("userbot.client.evaluate_message", return_value=True)
    mocker.patch("userbot.client.random.uniform", return_value=0.01)
    mocker.patch("asyncio.sleep", new_callable=AsyncMock)

    mock_client = MagicMock()
    mock_client.name = "alpha_session"
    mock_client.send_message = AsyncMock()

    mock_message = MagicMock()
    mock_message.text = "ابي احد يحل لي واجب ضروري"
    mock_message.from_user.id = 987654321

    # First call
    await userbot_client.handle_auto_reply(mock_client, mock_message)
    call_args1 = mock_client.send_message.call_args_list[-1][1]
    msg1 = call_args1["text"]

    # Second call
    await userbot_client.handle_auto_reply(mock_client, mock_message)
    call_args2 = mock_client.send_message.call_args_list[-1][1]
    msg2 = call_args2["text"]

    # Third call
    await userbot_client.handle_auto_reply(mock_client, mock_message)
    call_args3 = mock_client.send_message.call_args_list[-1][1]
    msg3 = call_args3["text"]

    assert msg1 != msg2
    assert msg1 == msg3


@pytest.mark.asyncio
async def test_handle_auto_reply_catches_privacy_restricted_no_counter_increment(mocker: MockerFixture) -> None:
    """Test UserPrivacyRestricted is caught gracefully, does not crash, and does NOT increment counter."""
    mocker.patch("userbot.client.evaluate_message", return_value=True)
    mocker.patch("asyncio.sleep", new_callable=AsyncMock)

    mock_client = MagicMock()
    mock_client.name = "alpha_session"
    # Simulate Pyrogram 403 UserPrivacyRestricted error
    mock_client.send_message = AsyncMock(side_effect=UserPrivacyRestricted())

    mock_message = MagicMock()
    mock_message.text = "احتاج مساعدة في مشروع التخرج"
    mock_message.from_user.id = 11223344

    # Execution should not raise exception
    await userbot_client.handle_auto_reply(mock_client, mock_message)
    mock_client.send_message.assert_awaited_once()
    assert userbot_client._daily_dm_count == 0
    assert userbot_client.daily_dms_count.get("alpha_session", 0) == 0


@pytest.mark.asyncio
async def test_handle_auto_reply_catches_user_is_blocked_no_counter_increment(mocker: MockerFixture) -> None:
    """Test UserIsBlocked is caught silently and does NOT increment daily DM counter."""
    mocker.patch("userbot.client.evaluate_message", return_value=True)
    mocker.patch("asyncio.sleep", new_callable=AsyncMock)

    mock_client = MagicMock()
    mock_client.name = "alpha_session"
    mock_client.send_message = AsyncMock(side_effect=UserIsBlocked())

    mock_message = MagicMock()
    mock_message.text = "احتاج مساعدة في واجب"
    mock_message.from_user.id = 55667788

    await userbot_client.handle_auto_reply(mock_client, mock_message)
    mock_client.send_message.assert_awaited_once()
    assert userbot_client._daily_dm_count == 0
    assert userbot_client.daily_dms_count.get("alpha_session", 0) == 0


@pytest.mark.asyncio
async def test_handle_auto_reply_catches_peer_id_invalid_no_counter_increment(mocker: MockerFixture) -> None:
    """Test PeerIdInvalid is caught cleanly without incrementing daily quota counter."""
    mocker.patch("userbot.client.evaluate_message", return_value=True)
    mocker.patch("asyncio.sleep", new_callable=AsyncMock)

    mock_client = MagicMock()
    mock_client.name = "alpha_session"
    mock_client.send_message = AsyncMock(side_effect=PeerIdInvalid())

    mock_message = MagicMock()
    mock_message.text = "احتاج مساعدة في كويز"
    mock_message.from_user.id = 99887766

    await userbot_client.handle_auto_reply(mock_client, mock_message)
    mock_client.send_message.assert_awaited_once()
    assert userbot_client._daily_dm_count == 0
    assert userbot_client.daily_dms_count.get("alpha_session", 0) == 0


@pytest.mark.asyncio
async def test_handle_auto_reply_catches_generic_exception_fallback(mocker: MockerFixture) -> None:
    """Test unexpected exception fallback ensures listener never crashes and does not increment quota."""
    mocker.patch("userbot.client.evaluate_message", return_value=True)
    mocker.patch("asyncio.sleep", new_callable=AsyncMock)

    mock_client = MagicMock()
    mock_client.name = "alpha_session"
    mock_client.send_message = AsyncMock(side_effect=RuntimeError("Unexpected connection reset"))

    mock_message = MagicMock()
    mock_message.text = "احتاج مساعدة في حل واجب"
    mock_message.from_user.id = 33445566

    await userbot_client.handle_auto_reply(mock_client, mock_message)
    mock_client.send_message.assert_awaited_once()
    assert userbot_client._daily_dm_count == 0
    assert userbot_client.daily_dms_count.get("alpha_session", 0) == 0


@pytest.mark.asyncio
async def test_handle_auto_reply_aborts_early_when_daily_limit_exceeded(mocker: MockerFixture) -> None:
    """Test that outbound DMs are strictly halted early once the daily limit (MAX_DAILY_DMS=20) is reached."""
    mock_eval = mocker.patch("userbot.client.evaluate_message", return_value=True)
    mocker.patch("userbot.client.can_send_dm", return_value=False)

    mock_client = MagicMock()
    mock_client.send_message = AsyncMock()

    mock_message = MagicMock()
    mock_message.text = "ابي مساعدة في حل واجب"
    mock_message.from_user.id = 12345

    await userbot_client.handle_auto_reply(mock_client, mock_message)

    # Early check prevents evaluate_message and send_message from executing
    mock_eval.assert_not_called()
    mock_client.send_message.assert_not_called()
    assert userbot_client._daily_dm_count == 0


@pytest.mark.asyncio
async def test_can_send_dm_enforces_max_daily_limit() -> None:
    """Test can_send_dm returns True under MAX_DAILY_DMS (20) and False once reached."""
    session = "beta_session"
    assert userbot_client.can_send_dm(session) is True

    # Increment up to limit - 1
    for _ in range(MAX_DAILY_DMS - 1):
        userbot_client.increment_dm_counter(session)

    assert userbot_client.can_send_dm(session) is True

    # Hit limit (20)
    userbot_client.increment_dm_counter(session)
    assert userbot_client.can_send_dm(session) is False


@pytest.mark.asyncio
async def test_handle_link_extraction_end_to_end(mocker: MockerFixture) -> None:
    """Test link extraction handler correctly routes valid links to save_link."""
    mock_save = mocker.patch("userbot.client.save_link", return_value="/path/links_part1.txt")
    mocker.patch("userbot.client.validate_whatsapp_link", return_value=True)

    sample_text = (
        "Check Telegram: https://t.me/DevGroup "
        "and folder https://t.me/addlist/StudyPack "
        "and WhatsApp https://chat.whatsapp.com/ValidInvite123"
    )

    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.text = sample_text

    await userbot_client.handle_link_extraction(mock_client, mock_message)

    assert mock_save.call_count == 3
    saved_links = [call[0][0] for call in mock_save.call_args_list]
    assert "https://t.me/DevGroup" in saved_links
    assert "https://t.me/addlist/StudyPack" in saved_links
    assert "https://chat.whatsapp.com/ValidInvite123" in saved_links


@pytest.mark.asyncio
async def test_stop_userbot_client_graceful_shutdown() -> None:
    """Test that stop_userbot_client gracefully disconnects active Pyrogram app."""
    mock_app = MagicMock()
    mock_app.is_connected = True
    mock_app.stop = AsyncMock()

    userbot_client.active_userbot_clients["test_session"] = mock_app

    await userbot_client.stop_userbot_client("test_session")

    mock_app.stop.assert_awaited_once()
    assert "test_session" not in userbot_client.active_userbot_clients


def test_create_userbot_client_default_has_no_updates_true(mocker: MockerFixture) -> None:
    """Test create_userbot_client defaults to enable_listening=False with no_updates=True."""
    mocker.patch("userbot.client.get_session_string", return_value="test_session_str")
    mock_pyrogram_client = mocker.patch("userbot.client.Client")

    userbot_client.create_userbot_client("session_deaf")

    mock_pyrogram_client.assert_called_once()
    call_kwargs = mock_pyrogram_client.call_args[1]
    assert call_kwargs.get("no_updates") is True
    assert call_kwargs["name"] == "session_deaf"


def test_create_userbot_client_enable_listening_true_removes_no_updates(mocker: MockerFixture) -> None:
    """Test create_userbot_client with enable_listening=True instantiates without no_updates=True."""
    mocker.patch("userbot.client.get_session_string", return_value="test_session_str")
    mock_pyrogram_client = mocker.patch("userbot.client.Client")

    userbot_client.create_userbot_client("session_monitoring", enable_listening=True)

    mock_pyrogram_client.assert_called_once()
    call_kwargs = mock_pyrogram_client.call_args[1]
    assert "no_updates" not in call_kwargs or call_kwargs["no_updates"] is not True


@pytest.mark.asyncio
async def test_run_userbot_initializes_with_enable_listening_true(mocker: MockerFixture) -> None:
    """Test run_userbot initiates client with enable_listening=True for the monitoring task."""
    mock_create = mocker.patch("userbot.client.create_userbot_client")
    mock_app = MagicMock()
    mock_app.start = AsyncMock()
    mock_create.return_value = mock_app
    mocker.patch("asyncio.sleep", side_effect=asyncio.CancelledError)

    with pytest.raises(asyncio.CancelledError):
        await userbot_client.run_userbot("monitor_session")

    mock_create.assert_called_once_with("monitor_session", enable_listening=True)
    mock_app.start.assert_awaited_once()


def test_suppress_peer_id_invalid_filter_blocks_record() -> None:
    """Test SuppressPeerIdInvalidFilter filters out records containing 'Peer id invalid'."""
    log_filter = userbot_client.SuppressPeerIdInvalidFilter()

    # Record with message containing Peer id invalid
    record1 = logging.LogRecord(
        name="pyrogram.session",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="ValueError: Peer id invalid",
        args=(),
        exc_info=None,
    )
    assert log_filter.filter(record1) is False

    # Record with exc_info containing Peer id invalid
    try:
        raise ValueError("Peer id invalid: [-100123456789]")
    except ValueError:
        record2 = logging.LogRecord(
            name="pyrogram.client",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="Unhandled exception",
            args=(),
            exc_info=sys.exc_info(),
        )
    assert log_filter.filter(record2) is False

    # Regular log record should pass
    record_pass = logging.LogRecord(
        name="userbot.client",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Successfully processed student inquiry.",
        args=(),
        exc_info=None,
    )
    assert log_filter.filter(record_pass) is True


@pytest.mark.asyncio
async def test_handle_auto_reply_catches_value_error_peer_id_invalid(mocker: MockerFixture) -> None:
    """Test ValueError with 'Peer id invalid' is caught safely in handle_auto_reply without crashing."""
    mocker.patch("userbot.client.evaluate_message", return_value=True)
    mocker.patch("asyncio.sleep", new_callable=AsyncMock)

    mock_client = MagicMock()
    mock_client.name = "alpha_session"
    mock_client.send_message = AsyncMock(side_effect=ValueError("Peer id invalid: 123456789"))

    mock_message = MagicMock()
    mock_message.text = "احتاج مساعدة في حل واجب"
    mock_message.from_user.id = 123456789

    # Should not raise exception
    await userbot_client.handle_auto_reply(mock_client, mock_message)
    mock_client.send_message.assert_awaited_once()
    assert userbot_client._daily_dm_count == 0
    assert userbot_client.daily_dms_count.get("alpha_session", 0) == 0


def test_ab_promotional_messages_validity() -> None:
    """Test A/B promotional messages contain the official WhatsApp contact link."""
    assert "https://wa.me/966502762144" in userbot_client.MESSAGE_A
    assert "https://wa.me/966502762144" in userbot_client.MESSAGE_B
    assert userbot_client.MESSAGE_A != userbot_client.MESSAGE_B

