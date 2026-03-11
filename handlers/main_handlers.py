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

main_router = Router()

@main_router.bot_started()
async def bot_start(event: BotStarted, context: MemoryContext, session: AsyncSession):
    # Получаем id пользователя в мах
    max_id = event.user.user_id
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
        await event.bot.send_message(
            chat_id=event.chat_id,
            text='👇Для прохождения обучения, поделитесь номером телефона через кнопку👇',
            attachments=[
                kb.as_markup(),
            ]
        )
    else:
        await context.set_state(Main_menu.menu)
        builder = get_main_menu()

        await event.bot.send_message(
            chat_id=event.chat_id,
            text=welcome_message,
            attachments=[
                builder.as_markup(),
            ]
        )




@main_router.message_created(Command('start'))
async def start(event: MessageCreated, context: MemoryContext, session: AsyncSession):
    # Получаем id пользователя в мах
    max_id = event.user.user_id
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
        builder = get_main_menu()


        await event.message.answer(
            text=welcome_message,
            attachments=[
                builder.as_markup(),
            ]
        )


@main_router.message_callback(F.callback.payload == 'main_menu', Main_menu.menu)
async def main_menu(event: MessageCallback, context: MemoryContext, session: AsyncSession):
    # Получаем id пользователя в мах
    max_id = event.user.user_id
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
        await event.message.edit(
            text='👇Для прохождения обучения, поделитесь номером телефона через кнопку👇',
            attachments=[
                kb.as_markup(),
            ]
        )

    else:
        await context.set_state(Main_menu.menu)
        builder = get_main_menu()



        await event.message.edit(
            text=welcome_message,
            attachments=[
                builder.as_markup(),
            ]
        )


@main_router.message_created(Main_menu.authorize)
async def authorize(event: MessageCreated, context: MemoryContext, session: AsyncSession, amo_api: AmoCRMWrapper,
                    amo_fields: dict):
    pipelines = amo_fields.get('pipelines')
    status_fields = amo_fields.get('statuses')
    utm_metriks = {}
    attachments = (event.message.body.attachments if event.message and event.message.body else []) or []
    max_id = event.user.user_id
    phone = None
    for att in attachments:
        if att.type == AttachmentType.CONTACT and att.payload:
            phone = extract_phone_from_vcf(att.payload.vcf_info or "")
            logger.info(f'Пользователь max_id: {max_id} поделился номером телефона: {phone}')
            break
    # Ищем контакт в Амосрм
    contact_data = processing_contact(amo_api=amo_api, contact_phone_number=str(phone))
    if contact_data is not None:
        """Если контакт в АМО найден, то ищем в БД запись USER по полю amo_deal_id"""
        amo_contact_id = contact_data.get("amo_contact_id")
        result = await session.execute(select(User).where(User.amo_contact_id == amo_contact_id))
        user = result.scalar_one_or_none()

        if user is not None:
            user.max_user_id = max_id
            await session.commit()
            await session.refresh(user)
            """Если запись в БД найдена, то проверяем есть ли в user id сделки в обучении, если нет создаём новую"""
            if not user.amo_deal_id:
                lead_data = processing_lead(amo_api=amo_api, contact_id=contact_data["amo_contact_id"],
                                            pipeline_id=pipelines["hite_pro_education"],
                                            status_id=status_fields['admitted_to_training'], )

                if lead_data:  # Данные сделки найдены в амосрм
                    user.amo_deal_id = lead_data["amo_deal_id"]
                    logger.info(
                        f'Для пользователя телефон: {phone}, max_id: {max_id} найдена сделка в амосрм')

                else:  # Сделка не найдена, создаём новую
                    logger.info(
                        f'Для пользователя телефон: {phone}, max_id: {max_id} не найдена сделка в амосрм')
                    new_lead_id = amo_api.send_lead_to_amo(pipeline_id=pipelines.get('hite_pro_education'),
                                                           status_id=status_fields.get('admitted_to_training'),
                                                           contact_id=contact_data.get("amo_contact_id"),
                                                           utm_metriks_fields=utm_metriks,
                                                           user=user
                                                           )
                    user.amo_deal_id = new_lead_id
                await session.commit()
                await session.refresh(user)
                response = amo_api.push_lead_to_status(pipeline_id=pipelines.get('hite_pro_education'),
                                                       status_id=status_fields.get('authorized_in_bot'),
                                                       lead_id=str(user.amo_deal_id))
                if response:
                    logger.info(f'Сделка {user.amo_deal_id} перемещена в следующий этап - Авторизовался в боте')
                else:
                    logger.info(f'Не получилось переместить сделку id: {user.amo_deal_id} дальше по воронке')

            else:
                logger.info(f'У контакта {user.amo_contact_id} найдена сделка в БД {user.amo_deal_id}')


        else:
            logger.info(f'В БД не найден контакт с номером {phone}, создаём новую запись в БД')

            user = User(
                max_user_id= max_id,
                phone_number = phone,
                first_name = contact_data.get("first_name"),
                last_name = contact_data.get("last_name"),
                amo_contact_id = contact_data.get("amo_contact_id"),
            )
            lead_data = processing_lead(amo_api=amo_api, contact_id=contact_data["amo_contact_id"],
                                        pipeline_id=pipelines["hite_pro_education"],
                                        status_id=status_fields['admitted_to_training'], )

            if lead_data:  # Данные сделки найдены в амосрм
                user.amo_deal_id = lead_data["amo_deal_id"]
                logger.info(
                    f'Для пользователя телефон: {phone}, max_id: {max_id} найдена сделка в амосрм')

            else:  # Сделка не найдена, создаём новую
                logger.info(
                    f'Для пользователя телефон: {phone}, max_id: {max_id} не найдена сделка в амосрм')
                new_lead_id = amo_api.send_lead_to_amo(pipeline_id=pipelines.get('hite_pro_education'),
                                                       status_id=status_fields.get('admitted_to_training'),
                                                       contact_id=contact_data.get("amo_contact_id"),
                                                       utm_metriks_fields=utm_metriks,
                                                       user=user
                                                       )
                response = amo_api.push_lead_to_status(pipeline_id=pipelines.get('hite_pro_education'),
                                                       status_id=status_fields.get('authorized_in_bot'),
                                                       lead_id=str(user.amo_deal_id))
                user.amo_deal_id = new_lead_id
            session.add(user)
            await session.commit()
            await session.refresh(user)

    else:
        """Если контакт в АМО не найден, то создаём новый контакт, сделку, запись USER в таблице"""
        logger.info(f'В амо не найден контакт для пользователя max_id: {max_id}, телефон: {phone}')
        user = User(
            max_user_id= max_id,
        )
        session.add(user)
        new_contact_id = amo_api.create_new_contact(first_name='Новый контакт из бота MAX',
                                                    last_name=str(phone),
                                                    phone=phone,
                                                    )
        new_lead_id = amo_api.send_lead_to_amo(pipeline_id=pipelines.get('hite_pro_education'),
                                               status_id=status_fields.get('admitted_to_training'),
                                               contact_id=new_contact_id,
                                               utm_metriks_fields=utm_metriks,
                                               user=user
                                               )
        response = amo_api.push_lead_to_status(pipeline_id=pipelines.get('hite_pro_education'),
                                               status_id=status_fields.get('authorized_in_bot'),
                                               lead_id=str(user.amo_deal_id))
        user.amo_deal_id = new_lead_id
        user.amo_contact_id = new_contact_id
        logger.info(f'Для пользователя max_id: {max_id}, телефон: {phone} создан новый контакт {new_contact_id} и '
                    f'новая сделка {new_lead_id}')

    await session.commit()
    await session.refresh(user)

    await context.set_state(Main_menu.menu)
    builder = get_main_menu()

    await event.message.edit(
        text=welcome_message,
        attachments=[
            builder.as_markup(),
        ]
    )


