"""
Unit tests for the Auto-Joiner core engine module.

Verifies link extraction from categorized .txt files, MTProto join execution,
UserAlreadyParticipant skipping, FloodWait sleep and retry mechanism, failed link handling,
and live progress UI reporting.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest
from pytest_mock import MockerFixture
from pyrogram.errors import (
    FloodWait,
    InviteHashExpired,
    InviteHashInvalid,
    InviteRequestSent,
    PeerIdInvalid,
    RPCError,
    UserAlreadyParticipant,
    UserDeactivated,
    UsernameInvalid,
    UsernameNotOccupied,
)

from userbot import joiner


# --- 1. Link Extraction Tests ---

def test_extract_links_from_file_valid(tmp_path: Path) -> None:
    """Test extracting and deduplicating Telegram group links from a text file."""
    sample_file = tmp_path / "part_1.txt"
    sample_file.write_text(
        "https://t.me/joinchat/AbCdEf12345\n"
        "https://t.me/+AbCdEf12345\n"
        "https://t.me/group_alpha\n"
        "https://t.me/group_alpha\n"  # Duplicate
        "@group_beta\n"
        "https://chat.whatsapp.com/12345\n"  # Non-Telegram
        "\n",
        encoding="utf-8",
    )

    links = joiner.extract_links_from_file(sample_file)
    assert len(links) == 4
    assert "https://t.me/joinchat/AbCdEf12345" in links
    assert "https://t.me/+AbCdEf12345" in links
    assert "https://t.me/group_alpha" in links
    assert "@group_beta" in links


def test_extract_links_from_file_non_existent(tmp_path: Path) -> None:
    """Test extract_links_from_file returns empty list for non-existent file."""
    missing_file = tmp_path / "does_not_exist.txt"
    assert joiner.extract_links_from_file(missing_file) == []


# --- 2. Link Sanitization Tests ---

def test_sanitize_chat_target_private_invite_links() -> None:
    """Test private invite links (+ or joinchat/) are preserved as full URLs."""
    assert joiner.sanitize_chat_target("https://t.me/+AbCdEf12345") == "https://t.me/+AbCdEf12345"
    assert joiner.sanitize_chat_target("https://t.me/joinchat/AbCdEf12345") == "https://t.me/joinchat/AbCdEf12345"
    assert joiner.sanitize_chat_target("https://telegram.me/+AbCdEf12345") == "https://telegram.me/+AbCdEf12345"
    assert joiner.sanitize_chat_target("https://telegram.me/joinchat/AbCdEf12345") == "https://telegram.me/joinchat/AbCdEf12345"


def test_sanitize_chat_target_public_links_and_handles() -> None:
    """Test public group links and @ handles have URL prefix and @ stripped to raw username."""
    assert joiner.sanitize_chat_target("https://t.me/PublicGroup") == "PublicGroup"
    assert joiner.sanitize_chat_target("https://t.me/PublicGroup/") == "PublicGroup"
    assert joiner.sanitize_chat_target("https://t.me/PublicGroup?start=ref") == "PublicGroup"
    assert joiner.sanitize_chat_target("https://telegram.me/PublicGroup") == "PublicGroup"
    assert joiner.sanitize_chat_target("@PublicGroup") == "PublicGroup"
    assert joiner.sanitize_chat_target("PublicGroup") == "PublicGroup"


# --- 3. Auto-Join Task Execution Tests ---

@pytest.mark.asyncio
async def test_run_auto_join_task_empty_links(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test run_auto_join_task handles empty link file and informs UI without connecting client."""
    empty_file = tmp_path / "part_empty.txt"
    empty_file.write_text("", encoding="utf-8")

    mock_bot = MagicMock()
    mock_bot.edit_message_text = AsyncMock()

    stats = await joiner.run_auto_join_task(
        session_name="test_session",
        file_path=str(empty_file),
        bot=mock_bot,
        admin_chat_id=12345,
        message_id=99,
    )

    assert stats["total"] == 0
    assert stats["joined"] == 0
    mock_bot.edit_message_text.assert_awaited_once()
    args, kwargs = mock_bot.edit_message_text.call_args
    assert "No valid Telegram group links found" in kwargs["text"]


@pytest.mark.asyncio
async def test_run_auto_join_task_successful_joins(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test successful joining of all links with 7-second sleep and completion UI."""
    sample_file = tmp_path / "part_1.txt"
    sample_file.write_text("https://t.me/group_1\nhttps://t.me/+private_hash\n", encoding="utf-8")

    mock_client = MagicMock()
    mock_client.start = AsyncMock()
    mock_client.join_chat = AsyncMock()
    mock_client.is_connected = True
    mock_client.stop = AsyncMock()

    mocker.patch("userbot.joiner.Client", return_value=mock_client)
    mock_sleep = mocker.patch("asyncio.sleep", new_callable=AsyncMock)

    mock_bot = MagicMock()
    mock_bot.edit_message_text = AsyncMock()

    stats = await joiner.run_auto_join_task(
        session_name="test_session",
        file_path=str(sample_file),
        bot=mock_bot,
        admin_chat_id=12345,
        message_id=99,
    )

    assert stats["total"] == 2
    assert stats["joined"] == 2
    assert stats["skipped_already_in"] == 0
    assert stats["failed"] == 0

    assert mock_client.join_chat.await_count == 2
    # Verify public link was stripped to raw username and private link was preserved
    mock_client.join_chat.assert_any_await("group_1")
    mock_client.join_chat.assert_any_await("https://t.me/+private_hash")
    mock_client.stop.assert_awaited_once()
    # Anti-spam sleep asserted
    mock_sleep.assert_any_await(7)


@pytest.mark.asyncio
async def test_run_auto_join_task_user_already_participant(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test UserAlreadyParticipant increments skipped counter and proceeds instantly."""
    sample_file = tmp_path / "part_1.txt"
    sample_file.write_text("https://t.me/already_in\n", encoding="utf-8")

    mock_client = MagicMock()
    mock_client.start = AsyncMock()
    mock_client.join_chat = AsyncMock(side_effect=UserAlreadyParticipant())
    mock_client.is_connected = True
    mock_client.stop = AsyncMock()

    mocker.patch("userbot.joiner.Client", return_value=mock_client)
    mocker.patch("asyncio.sleep", new_callable=AsyncMock)

    mock_bot = MagicMock()
    mock_bot.edit_message_text = AsyncMock()

    stats = await joiner.run_auto_join_task(
        session_name="test_session",
        file_path=str(sample_file),
        bot=mock_bot,
        admin_chat_id=12345,
        message_id=99,
    )

    assert stats["total"] == 1
    assert stats["joined"] == 0
    assert stats["skipped_already_in"] == 1
    assert stats["failed"] == 0


@pytest.mark.asyncio
async def test_run_auto_join_task_flood_wait_retries_and_succeeds(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test FloodWait sleeps for requested duration + 5s and retries the exact same link successfully."""
    sample_file = tmp_path / "part_1.txt"
    sample_file.write_text("https://t.me/rate_limited_group\n", encoding="utf-8")

    flood_exc = FloodWait(value=10)
    mock_client = MagicMock()
    mock_client.start = AsyncMock()
    # First attempt raises FloodWait(10), second attempt succeeds
    mock_client.join_chat = AsyncMock(side_effect=[flood_exc, None])
    mock_client.is_connected = True
    mock_client.stop = AsyncMock()

    mocker.patch("userbot.joiner.Client", return_value=mock_client)
    mock_sleep = mocker.patch("asyncio.sleep", new_callable=AsyncMock)

    mock_bot = MagicMock()
    mock_bot.edit_message_text = AsyncMock()

    stats = await joiner.run_auto_join_task(
        session_name="test_session",
        file_path=str(sample_file),
        bot=mock_bot,
        admin_chat_id=12345,
        message_id=99,
    )

    assert stats["total"] == 1
    assert stats["joined"] == 1
    assert mock_client.join_chat.await_count == 2
    mock_sleep.assert_any_await(15)  # 10 + 5


@pytest.mark.asyncio
async def test_run_auto_join_task_expired_and_invalid_links(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test InviteHashExpired and InviteHashInvalid exceptions increment failed counter."""
    sample_file = tmp_path / "part_1.txt"
    sample_file.write_text("https://t.me/+expired\nhttps://t.me/+invalid\n", encoding="utf-8")

    mock_client = MagicMock()
    mock_client.start = AsyncMock()
    mock_client.join_chat = AsyncMock(side_effect=[InviteHashExpired(), InviteHashInvalid()])
    mock_client.is_connected = True
    mock_client.stop = AsyncMock()

    mocker.patch("userbot.joiner.Client", return_value=mock_client)
    mocker.patch("asyncio.sleep", new_callable=AsyncMock)

    mock_bot = MagicMock()
    mock_bot.edit_message_text = AsyncMock()

    stats = await joiner.run_auto_join_task(
        session_name="test_session",
        file_path=str(sample_file),
        bot=mock_bot,
        admin_chat_id=12345,
        message_id=99,
    )

    assert stats["total"] == 2
    assert stats["joined"] == 0
    assert stats["failed"] == 2


@pytest.mark.asyncio
async def test_run_auto_join_task_failure_logs_verbose_warning(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test Telegram API exceptions increment failed counter and log verbose warning with API message."""
    sample_file = tmp_path / "part_failures.txt"
    sample_file.write_text(
        "https://t.me/invalid_user\n"
        "https://t.me/unoccupied_user\n"
        "https://t.me/+expired\n"
        "https://t.me/+invalid_hash\n"
        "https://t.me/peer_invalid\n",
        encoding="utf-8",
    )

    mock_client = MagicMock()
    mock_client.start = AsyncMock()
    mock_client.join_chat = AsyncMock(side_effect=[
        UsernameInvalid(),
        UsernameNotOccupied(),
        InviteHashExpired(),
        InviteHashInvalid(),
        PeerIdInvalid(),
    ])
    mock_client.is_connected = True
    mock_client.stop = AsyncMock()

    mocker.patch("userbot.joiner.Client", return_value=mock_client)
    mocker.patch("asyncio.sleep", new_callable=AsyncMock)
    mock_logger_warning = mocker.patch.object(joiner.logger, "warning")

    mock_bot = MagicMock()
    mock_bot.edit_message_text = AsyncMock()

    stats = await joiner.run_auto_join_task(
        session_name="test_session",
        file_path=str(sample_file),
        bot=mock_bot,
        admin_chat_id=12345,
        message_id=99,
    )

    assert stats["total"] == 5
    assert stats["joined"] == 0
    assert stats["failed"] == 5
    # Ensure logger.warning was called for every failure with verbose format
    assert mock_logger_warning.call_count == 5
    for call_item in mock_logger_warning.call_args_list:
        assert "Telegram API says ->" in call_item[0][0]


@pytest.mark.asyncio
async def test_run_auto_join_task_unexpected_error_logs_warning(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test unexpected exception increments failed counter and logs verbose warning."""
    sample_file = tmp_path / "part_err.txt"
    sample_file.write_text("https://t.me/problem_group\n", encoding="utf-8")

    mock_client = MagicMock()
    mock_client.start = AsyncMock()
    mock_client.join_chat = AsyncMock(side_effect=RuntimeError("Unexpected network failure"))
    mock_client.is_connected = True
    mock_client.stop = AsyncMock()

    mocker.patch("userbot.joiner.Client", return_value=mock_client)
    mocker.patch("asyncio.sleep", new_callable=AsyncMock)
    mock_logger_warning = mocker.patch.object(joiner.logger, "warning")

    mock_bot = MagicMock()
    mock_bot.edit_message_text = AsyncMock()

    stats = await joiner.run_auto_join_task(
        session_name="test_session",
        file_path=str(sample_file),
        bot=mock_bot,
        admin_chat_id=12345,
        message_id=99,
    )

    assert stats["total"] == 1
    assert stats["joined"] == 0
    assert stats["failed"] == 1
    mock_logger_warning.assert_called_once()
    assert "Telegram API says -> Unexpected network failure" in mock_logger_warning.call_args[0][0]


@pytest.mark.asyncio
async def test_run_auto_join_task_invite_request_sent(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test InviteRequestSent increments sent_request counter, sleeps, and updates progress UI."""
    sample_file = tmp_path / "part_req.txt"
    sample_file.write_text("https://t.me/+approval_group\n", encoding="utf-8")

    mock_client = MagicMock()
    mock_client.start = AsyncMock()
    mock_client.join_chat = AsyncMock(side_effect=InviteRequestSent())
    mock_client.is_connected = True
    mock_client.stop = AsyncMock()

    mocker.patch("userbot.joiner.Client", return_value=mock_client)
    mock_sleep = mocker.patch("asyncio.sleep", new_callable=AsyncMock)

    mock_bot = MagicMock()
    mock_bot.edit_message_text = AsyncMock()

    stats = await joiner.run_auto_join_task(
        session_name="test_session",
        file_path=str(sample_file),
        bot=mock_bot,
        admin_chat_id=12345,
        message_id=99,
    )

    assert stats["total"] == 1
    assert stats["joined"] == 0
    assert stats["sent_request"] == 1
    assert stats["skipped_already_in"] == 0
    assert stats["failed"] == 0
    mock_sleep.assert_awaited_once_with(joiner.JOIN_ANTI_SPAM_SLEEP_SECONDS)
    mock_bot.edit_message_text.assert_awaited()
    last_call = mock_bot.edit_message_text.call_args
    assert "Requests Sent" in last_call.kwargs["text"]


@pytest.mark.asyncio
async def test_run_auto_join_task_admin_cancellation(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test cancelling the auto joiner task catches CancelledError and updates UI with abort message."""
    sample_file = tmp_path / "part_cancel.txt"
    sample_file.write_text("https://t.me/cancel_group_1\nhttps://t.me/cancel_group_2\n", encoding="utf-8")

    mock_client = MagicMock()
    mock_client.start = AsyncMock()
    mock_client.join_chat = AsyncMock(side_effect=asyncio.CancelledError())
    mock_client.is_connected = True
    mock_client.stop = AsyncMock()

    mocker.patch("userbot.joiner.Client", return_value=mock_client)
    mocker.patch("asyncio.sleep", new_callable=AsyncMock)

    mock_bot = MagicMock()
    mock_bot.edit_message_text = AsyncMock()

    stats = await joiner.run_auto_join_task(
        session_name="test_session",
        file_path=str(sample_file),
        bot=mock_bot,
        admin_chat_id=12345,
        message_id=99,
    )

    mock_client.stop.assert_awaited_once()
    mock_bot.edit_message_text.assert_awaited_once()
    args, kwargs = mock_bot.edit_message_text.call_args
    assert "ABORTED BY ADMIN" in kwargs["text"]
    assert kwargs["reply_markup"] is not None
