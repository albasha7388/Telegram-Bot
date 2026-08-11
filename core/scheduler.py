"""
Background task scheduler module using APScheduler.

Automates scheduled system maintenance, including midnight UTC resets of outbound
direct message (DM) rate limit quotas for all active MTProto userbot sessions,
and hourly feedback reporting to the administrator when userbots are actively running.
"""

from typing import Any, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config.settings import MAX_DAILY_DMS
from core.logger_setup import setup_logger
from core.process_manager import get_all_active_sessions
from userbot.client import (
    get_daily_dm_count,
    get_hourly_metrics,
    reset_dm_counter,
    reset_hourly_metrics,
)

logger = setup_logger(__name__)


def reset_daily_limits() -> None:
    """Reset the daily direct message (DM) safety quota for all userbot sessions.

    Triggered automatically at 00:00 UTC by the scheduler to ensure compliance
    with Telegram anti-ban rate limiting protocols.
    """
    logger.info("Executing scheduled midnight reset of daily DM counters...")
    reset_dm_counter()
    logger.info("Scheduled midnight reset of daily DM counters completed.")


async def send_hourly_report(bot: Any = None, admin_chat_id: Optional[int] = None) -> None:
    """Send an hourly feedback report to the admin if the userbot engine is actively running.

    Checks process manager status. If no userbot background tasks are active, exits silently.
    Otherwise, accurately computes daily quota consumption across active sessions, compiles
    hourly message metrics, and delivers an Aiogram HTML summary.

    Args:
        bot: Optional Aiogram Bot instance for report delivery.
        admin_chat_id: Optional Telegram Admin user/chat ID.
    """
    active_sessions = get_all_active_sessions()
    if not active_sessions:
        logger.debug("No active userbot sessions running. Skipping hourly report.")
        return

    if not bot or not admin_chat_id:
        logger.debug("Bot instance or admin_chat_id missing for hourly feedback report.")
        return

    scanned, sent = get_hourly_metrics()

    # Calculate current daily DM count dynamically across active sessions or global count
    current_count = 0
    if active_sessions:
        session_counts = [get_daily_dm_count(s) for s in active_sessions]
        if any(session_counts):
            current_count = sum(session_counts)
        else:
            current_count = get_daily_dm_count()
    else:
        current_count = get_daily_dm_count()

    remaining = max(0, min(MAX_DAILY_DMS, MAX_DAILY_DMS - current_count))

    report_text = (
        "⏱️ <b>Hourly Auto-Reply Report</b>\n"
        f"├ Scanned: <b>{scanned}</b>\n"
        f"├ Replies Sent: <b>{sent}</b>\n"
        f"└ Remaining Daily Quota: <b>{remaining}/{MAX_DAILY_DMS}</b>"
    )

    try:
        await bot.send_message(
            chat_id=admin_chat_id,
            text=report_text,
            parse_mode="HTML",
        )
        logger.info(
            "Delivered hourly feedback report to admin %d (scanned: %d, sent: %d, remaining: %d).",
            admin_chat_id,
            scanned,
            sent,
            remaining,
        )
    except Exception as exc:
        logger.error("Failed sending hourly feedback report to admin %d: %s", admin_chat_id, exc)
    finally:
        reset_hourly_metrics()


def start_scheduler(bot: Any = None, admin_chat_id: Optional[int] = None) -> AsyncIOScheduler:
    """Initialize, configure, and start the AsyncIOScheduler instance.

    Registers:
    1. Midnight daily DM limit reset job configured for 00:00 UTC.
    2. Hourly feedback reporting job configured for minute=0 of every hour.

    Args:
        bot: Optional Aiogram Bot instance for report delivery.
        admin_chat_id: Optional Telegram Admin user/chat ID.

    Returns:
        AsyncIOScheduler: The active running scheduler instance.
    """
    logger.info("Initializing background AsyncIOScheduler...")
    scheduler = AsyncIOScheduler(timezone="UTC")

    # 1. Midnight Daily DM Limit Reset Job (00:00 UTC)
    scheduler.add_job(
        reset_daily_limits,
        trigger=CronTrigger(hour=0, minute=0, timezone="UTC"),
        id="reset_daily_limits_job",
        name="Reset Userbot Daily DM Limits",
        replace_existing=True,
    )

    # 2. Hourly Feedback Report Job (Every hour at minute 0)
    if bot and admin_chat_id:
        scheduler.add_job(
            send_hourly_report,
            trigger=CronTrigger(minute=0, timezone="UTC"),
            args=[bot, admin_chat_id],
            id="hourly_report_job",
            name="Hourly Auto-Reply Feedback Report",
            replace_existing=True,
        )

    scheduler.start()
    logger.info("AsyncIOScheduler started successfully with active midnight and hourly triggers.")
    return scheduler
