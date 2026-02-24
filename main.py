import asyncio
import logging

from db import init_db, shutdown_db
from services.context import bot, dp

# noqa: F401 - регистрация обработчиков по декораторам
import handlers.command_handler  # noqa: F401,E402

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s",
)


async def run() -> None:
    logger.info("Starting hitepro_edu_bot for MAX")
    await init_db()
    try:
        await dp.start_polling(bot)
    finally:
        await shutdown_db()


if __name__ == "__main__":
    asyncio.run(run())
