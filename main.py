import asyncio
import logging
import os
import signal

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from database.database import init_db
from handlers import buyer, common, seller, subscription

logger = logging.getLogger(__name__)


async def main() -> None:
    """Entry point for the Telegram bot."""

    load_dotenv()
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not set")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    await init_db()

    bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.include_router(common.router)
    dp.include_router(seller.router)
    dp.include_router(buyer.router)
    dp.include_router(subscription.router)

    shutdown_event = asyncio.Event()

    def _signal_handler(*_: int) -> None:
        shutdown_event.set()

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    await bot.delete_webhook(drop_pending_updates=True)

    polling_task = asyncio.create_task(dp.start_polling(bot))
    await shutdown_event.wait()
    polling_task.cancel()
    await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

