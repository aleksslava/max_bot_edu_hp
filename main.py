import asyncio
import logging
from pprint import pprint

from maxapi import Bot, Dispatcher
from maxapi.types import BotStarted

from config.config import load_config, Config
from config.config import load_config
from maxapi.enums import parse_mode

from handlers.admin_menu import admin_router
from handlers.error_handler import error_handler
from handlers.exam import exam_router
from handlers.lesson_5 import lesson_5
from handlers.lesson_6 import lesson_6
from handlers.lesson_7 import lesson_7
from handlers.main_handlers import main_router
from handlers.lesson_1 import lesson_1
from handlers.lesson_2 import lesson_2
from handlers.lesson_3 import lesson_3
from handlers.lesson_4 import lesson_4
from middleware.amo_api import AmoApiMiddleware
from middleware.dp import DbSessionMiddleware
from middleware.image_tokens import ImageTokensMiddleware
from middleware.video_tokens import VideoTokensMiddleware
from services.video_tokens_env import ensure_video_tokens_in_env, ensure_image_tokens_in_env
from amo_api.amo_api import AmoCRMWrapper

from config.config import BASE_DIR

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
dp.include_routers(main_router, lesson_1, lesson_2, lesson_3, lesson_4, lesson_5, lesson_6, lesson_7,
                   exam_router,admin_router, error_handler)


async def run() -> None:
    logger.info("Starting hitepro_edu_bot for MAX")
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
    dp.middleware(AmoApiMiddleware(amo_api, amo_fields=config.amo_fields, admin_id=config.admin,
                                      webhook_url=config.webhook_url, utm_token=config.utm_token))
    dp.middleware(DbSessionMiddleware())
    await dp.start_polling(bot, skip_updates=True)



if __name__ == "__main__":
    asyncio.run(run())
