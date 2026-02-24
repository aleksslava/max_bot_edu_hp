from maxapi import Bot, Dispatcher

from amo_api.amo_api import AmoCRMWrapper
from config.config import load_config

config = load_config()

bot_kwargs = {"token": config.max_bot.token}
if config.max_bot.api_url:
    bot_kwargs["api_url"] = config.max_bot.api_url
bot = Bot(**bot_kwargs)

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
