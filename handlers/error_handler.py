from logging.handlers import RotatingFileHandler
from pprint import pprint
import logging
from maxapi import Router, F, Bot
from maxapi.context import MemoryContext
from maxapi.enums.attachment import AttachmentType
from maxapi.filters.command import Command
from maxapi.types import BotStarted, MessageCreated, CallbackButton, MessageCallback, RequestContactButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from amo_api.amo_service import processing_contact, processing_lead
from service.questions_lexicon import welcome_message
from fsm.main_states import Main_menu
from services.utils import extract_phone_from_vcf, get_main_menu
from amo_api.amo_api import AmoCRMWrapper
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db.models import User, HpLessonResult as LessonResult

logger = logging.getLogger(__name__)

error_handler = Router()


@error_handler.message_created
async def error_handler(event: MessageCreated, context: MemoryContext, session: AsyncSession):
    # Получаем id пользователя в мах
    max_id = event.message.sender.user_id
    logger.info(f'Запущен бот пользователем max_id:{max_id}')

    # Запрос в БД на наличие пользователя
    result = await session.execute(select(User).where(User.max_user_id == max_id))
    user = result.scalar_one_or_none()

    if user is None:
        await context.set_state(Main_menu.authorize)
        logger.info(f'Для пользователя max_id:{max_id} не найдена запись в БД!\n'
                    f'Отправляю запрос контакта!')

        kb = InlineKeyboardBuilder()
        kb.add(
            RequestContactButton(text='Авторизоваться')
        )
        await event.message.answer(
            text='👇Для прохождения обучения, поделитесь номером телефона через кнопку👇',
            attachments=[
                kb.as_markup(),
            ]
        )

    else:
        await context.set_state(Main_menu.menu)
        builder = await get_main_menu(user=user, session=session)

        await event.message.answer(
            text=welcome_message,
            attachments=[
                builder.as_markup(),
            ]
        )
