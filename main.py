import asyncio
import logging

from maxapi import Bot, Dispatcher
from maxapi.enums import parse_mode

from amo_api.amo_api import AmoCRMWrapper
from config.config import BASE_DIR, Config, load_config
from db import init_db, shutdown_db
from handlers.admin_menu import admin_router
from handlers.error_handler import error_handler
from handlers.exam import exam_router
from handlers.lesson_1 import lesson_1
from handlers.lesson_2 import lesson_2
from handlers.lesson_3 import lesson_3
from handlers.lesson_4 import lesson_4
from handlers.lesson_5 import lesson_5
from handlers.lesson_6 import lesson_6
from handlers.lesson_7 import lesson_7
from handlers.main_handlers import main_router
from middleware.amo_api import AmoApiMiddleware
from middleware.dp import DbSessionMiddleware
from middleware.image_tokens import ImageTokensMiddleware
from middleware.video_tokens import VideoTokensMiddleware
from service.background_notifications import (
    start_inactivity_scheduler,
    stop_inactivity_scheduler,
)
from services.video_tokens_env import ensure_image_tokens_in_env, ensure_video_tokens_in_env

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s",
)

config: Config = load_config()

bot = Bot(token=config.max_bot.token, parse_mode=parse_mode.ParseMode.HTML)
amo_api = AmoCRMWrapper(
    path=config.amo_config.path_to_env,
    amocrm_subdomain=config.amo_config.amocrm_subdomain,
    amocrm_client_id=config.amo_config.amocrm_client_id,
    amocrm_redirect_url=config.amo_config.amocrm_redirect_url,
    amocrm_client_secret=config.amo_config.amocrm_client_secret,
    amocrm_secret_code=config.amo_config.amocrm_secret_code,
    amocrm_access_token=config.amo_config.amocrm_access_token,
    amocrm_refresh_token=config.amo_config.amocrm_refresh_token,
)

dp = Dispatcher()
dp.include_routers(
    main_router,
    lesson_1,
    lesson_2,
    lesson_3,
    lesson_4,
    lesson_5,
    lesson_6,
    lesson_7,
    exam_router,
    admin_router,
    error_handler,
)

inactivity_scheduler_task: asyncio.Task | None = None


async def run() -> None:
    global inactivity_scheduler_task

    logger.info("Starting hitepro_edu_bot for MAX")

    try:
        await init_db()
    except Exception as exc:
        # Do not crash startup if DB is temporarily unavailable.
        logger.exception("DB init failed: %s", exc)

    tokens = await ensure_video_tokens_in_env(
        bot=bot,
        folder=BASE_DIR / "media" / "video",
        env_path=BASE_DIR / ".env",
    )

    tokens_image = await ensure_image_tokens_in_env(
        bot=bot,
        folder=BASE_DIR / "media" / "photo",
        env_path=BASE_DIR / ".env",
    )

    dp.middleware(VideoTokensMiddleware(tokens))
    dp.middleware(ImageTokensMiddleware(tokens_image))
    dp.middleware(
        AmoApiMiddleware(
            amo_api,
            amo_fields=config.amo_fields,
            admin_id=config.admin,
            webhook_url=config.webhook_url,
            utm_token=config.utm_token,
        )
    )
    dp.middleware(DbSessionMiddleware())

    inactivity_scheduler_task = start_inactivity_scheduler(bot)

    try:
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await stop_inactivity_scheduler(inactivity_scheduler_task)
        inactivity_scheduler_task = None
        await shutdown_db()


if __name__ == "__main__":
    asyncio.run(run())
