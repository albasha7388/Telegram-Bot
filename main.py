"""
Main entry point for the Hybrid Telegram System Control UI.

Initializes the Aiogram Bot instance, configures the dispatcher with UI routers,
starts the background midnight scheduler and hourly feedback reporter, and runs the event polling loop.
"""

import asyncio
import os
from aiohttp import web
from aiogram import Bot, Dispatcher
from bot_ui.handlers import router as ui_router
from bot_ui.joiner_handlers import router as joiner_router
from bot_ui.login_handlers import router as login_router
from config.settings import ADMIN_ID, BOT_TOKEN
from core.logger_setup import setup_logger
from core.scheduler import start_scheduler

# Initialize root application logger
logger = setup_logger("main")


async def health_check(request: web.Request) -> web.Response:
    """Handle incoming HTTP GET health check requests for cloud hosting platforms.

    Args:
        request: The incoming aiohttp web Request object.

    Returns:
        web.Response: Plain text response confirming the bot is active.
    """
    return web.Response(text="Bot is alive!")


async def start_dummy_server() -> None:
    """Start a lightweight background aiohttp web server to satisfy Render/cloud health checks."""
    port = int(os.environ.get("PORT", 10000))
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Dummy web server started on port {port} for Render health checks.")


def create_bot(token: str | None = None) -> Bot:
    """Instantiate and configure the Aiogram Bot instance.

    Args:
        token: Optional Telegram Bot API token (defaults to settings.BOT_TOKEN).

    Returns:
        Bot: Configured Aiogram Bot instance.
    """
    bot_token = token or BOT_TOKEN
    return Bot(token=bot_token)


def create_dispatcher() -> Dispatcher:
    """Create and configure the central Aiogram Dispatcher with registered UI routers.

    Returns:
        Dispatcher: Configured dispatcher instance with attached sub-routers.
    """
    dp = Dispatcher()
    dp.include_router(ui_router)
    dp.include_router(login_router)
    dp.include_router(joiner_router)
    logger.debug("Registered bot_ui, login, and joiner routers into main dispatcher.")
    return dp


async def main() -> None:
    """Set up the system logger, instantiate bot, dispatcher, and scheduler, and run polling."""
    logger.info("Initializing Hybrid Telegram System Control UI...")

    bot = create_bot()
    dp = create_dispatcher()
    scheduler = start_scheduler(bot=bot, admin_chat_id=ADMIN_ID)

    # Startup Notification Hook
    admin_id_str = os.getenv("ADMIN_ID")
    if not admin_id_str:
        logger.error("ADMIN_ID is missing from environment variables.")
    else:
        try:
            admin_id_int = int(admin_id_str)
        except ValueError:
            logger.error("Failed to cast ADMIN_ID to integer.")
            admin_id_int = None

        if admin_id_int is not None:
            try:
                await bot.send_message(
                    chat_id=admin_id_int,
                    text="🔄 <b>System Update Complete</b>\n\nThe bot has been successfully restarted, updated, and is ready for new tasks.",
                    parse_mode="HTML",
                )
                from bot_ui.handlers import send_main_menu
                await send_main_menu(bot=bot, chat_id=admin_id_int)
                logger.info("Startup notification and main menu successfully delivered to Admin.")
            except Exception as e:
                logger.error(f"Failed to send startup sequence to admin: {e}")

    logger.info("Starting Aiogram polling loop for Control UI...")
    try:
        asyncio.create_task(start_dummy_server())
        await dp.start_polling(bot, drop_pending_updates=True)
    finally:
        logger.info("Shutting down background scheduler and bot session...")
        scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("System gracefully stopped by administrator.")
