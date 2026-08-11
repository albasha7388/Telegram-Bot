"""
Unit tests for background scheduler, midnight daily quota reset, and hourly feedback reports.
"""

from unittest.mock import AsyncMock, MagicMock
import pytest
from pytest_mock import MockerFixture

from core import scheduler
from userbot import client as userbot_client


def test_reset_daily_limits_clears_userbot_tracking() -> None:
    """Test that reset_daily_limits properly clears daily DM counters in userbot client."""
    userbot_client.daily_dms_count["test_session"] = 18
    userbot_client._daily_dm_count = 18

    assert userbot_client.can_send_dm("test_session") is True

    # Manually exhaust the limit
    userbot_client.daily_dms_count["test_session"] = 20
    assert userbot_client.can_send_dm("test_session") is False

    # Trigger scheduler reset
    scheduler.reset_daily_limits()

    assert userbot_client.can_send_dm("test_session") is True
    assert len(userbot_client.daily_dms_count) == 0


@pytest.mark.asyncio
async def test_send_hourly_report_active_userbot(mocker: MockerFixture) -> None:
    """Test send_hourly_report compiles metrics, sends message to admin, and resets hourly metrics."""
    mocker.patch("core.scheduler.get_all_active_sessions", return_value=["session_alpha"])
    mocker.patch("core.scheduler.get_daily_dm_count", return_value=10)

    userbot_client.hourly_scanned_count = 120
    userbot_client.hourly_replies_sent = 4

    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock()

    await scheduler.send_hourly_report(bot=mock_bot, admin_chat_id=987654)

    mock_bot.send_message.assert_awaited_once()
    args, kwargs = mock_bot.send_message.call_args
    assert kwargs["chat_id"] == 987654
    assert "Hourly Auto-Reply Report" in kwargs["text"]
    assert "Scanned: <b>120</b>" in kwargs["text"]
    assert "Replies Sent: <b>4</b>" in kwargs["text"]
    assert "Remaining Daily Quota: <b>10/20</b>" in kwargs["text"]

    # Verify hourly metrics are reset
    assert userbot_client.hourly_scanned_count == 0
    assert userbot_client.hourly_replies_sent == 0


@pytest.mark.asyncio
async def test_send_hourly_report_idle_userbot(mocker: MockerFixture) -> None:
    """Test send_hourly_report skips execution when no userbot tasks are actively running."""
    mocker.patch("core.scheduler.get_all_active_sessions", return_value=[])

    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock()

    await scheduler.send_hourly_report(bot=mock_bot, admin_chat_id=987654)

    mock_bot.send_message.assert_not_called()


def test_start_scheduler_registers_both_cron_jobs(mocker: MockerFixture) -> None:
    """Test scheduler initialization registers midnight reset and hourly report jobs."""
    mock_scheduler_instance = MagicMock()
    mock_scheduler_class = mocker.patch(
        "core.scheduler.AsyncIOScheduler",
        return_value=mock_scheduler_instance,
    )

    mock_bot = MagicMock()
    running_scheduler = scheduler.start_scheduler(bot=mock_bot, admin_chat_id=123456)

    mock_scheduler_class.assert_called_once_with(timezone="UTC")
    assert mock_scheduler_instance.add_job.call_count == 2

    job_ids = [call[1]["id"] for call in mock_scheduler_instance.add_job.call_args_list]
    assert "reset_daily_limits_job" in job_ids
    assert "hourly_report_job" in job_ids

    mock_scheduler_instance.start.assert_called_once()
    assert running_scheduler == mock_scheduler_instance
