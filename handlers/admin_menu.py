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
from fsm.admin import Admin
from services.utils import extract_phone_from_vcf, get_main_menu
from amo_api.amo_api import AmoCRMWrapper
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db.models import User, HpLessonResult as LessonResult

logger = logging.getLogger(__name__)

admin_router = Router()

@admin_router.message_callback(F.callback.payload == 'admin_menu', Main_menu.menu)
async def admin_menu(event: MessageCallback, context: MemoryContext, session: AsyncSession):
    kb = InlineKeyboardBuilder()
    kb.add(CallbackButton(text='Удалить пользователя', payload='delete_user'))
    await context.set_state(Admin.menu)

    await event.message.edit(
        text='Выберите нужный пункт меню',
        attachments=[
            kb.as_markup(),
        ]
    )


@admin_router.message_callback(F.callback.payload == 'delete_user', Admin.menu)
async def delete_user(event: MessageCallback, context: MemoryContext, session: AsyncSession):
    await context.set_state(Admin.id_reque)

    await event.message.edit(
        text='Отправьте id пользователя для удаления ',
        attachments=[]
    )

@admin_router.message_created(Admin.id_reque)
async def get_user_id(event: MessageCreated, context: MemoryContext, session: AsyncSession):
    text = ((event.message.body.text if event.message and event.message.body else "") or "").strip()

    if not text.isdigit():
        await event.message.answer(
            text='Отправьте только числовой id пользователя (max_user_id).'
        )
        return

    max_user_id = int(text)
    result = await session.execute(select(User).where(User.max_user_id == max_user_id))
    user = result.scalar_one_or_none()

    if user is None:
        await event.message.answer(
            text=f'Пользователь с id {max_user_id} не найден.'
        )
        return

    await session.delete(user)
    await session.commit()

    await context.set_state(Admin.menu)
    await event.message.answer(
        text=f'Пользователь с id {max_user_id} удалён.'
    )
