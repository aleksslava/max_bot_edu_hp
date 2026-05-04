import asyncio
import aiohttp
import logging
from maxapi import Router, F, Bot
from maxapi.context import MemoryContext
from maxapi.enums.attachment import AttachmentType
from maxapi.filters.command import Command
from maxapi.types import BotStarted, MessageCreated, CallbackButton, MessageCallback, RequestContactButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from amo_api.amo_service import processing_contact, processing_lead
from service.questions_lexicon import welcome_message, manager_text, start_message
from fsm.main_states import Main_menu
from services.utils import extract_phone_from_vcf, get_main_menu, get_manager_url
from amo_api.amo_api import AmoCRMWrapper
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db.models import User, HpLessonResult as LessonResult

logger = logging.getLogger(__name__)

main_router = Router()



@main_router.message_callback(F.callback.payload == 'manager')
async def manager(event: MessageCallback):
    builder = await get_manager_url()

    await event.message.edit(
        text=manager_text,
        attachments=[
            builder.as_markup(),
        ]
    )
    return builder.as_markup()

@main_router.bot_started()
async def bot_start(event: BotStarted, context: MemoryContext, session: AsyncSession,
                    webhook_url: str, utm_token:str):
    await context.clear()
    webhook_id = event.payload
    if webhook_id is not None:
        utm_data = {
            "utm_source": "",
            "utm_medium": "",
            "utm_campaign": "",
            "utm_content": "",
            "utm_term": "",
            "yclid": "",
        }
        try:
            async with aiohttp.ClientSession() as client_session:
                async with client_session.get(
                    f"{webhook_url}{webhook_id}",
                    params={"utm_token": utm_token},
                    timeout=10,
                ) as response:
                    response.raise_for_status()
                    payload = await response.json()
                    if isinstance(payload, dict):
                        utm_data.update(payload)
                        logger.info(f'Получены UTM метки клиента: {utm_data["utm_source"]}; {utm_data["utm_medium"]}\n'
                                    f'; {utm_data["utm_campaign"]}; {utm_data["utm_content"]}; {utm_data["utm_term"]}\n'
                                    f'; {utm_data["yclid"]}')

                        context_data = await context.get_data()
                        context_data['utm_data'] = utm_data
                        await context.set_data(context_data)
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            pass

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
        builder = await get_main_menu(user=user, session=session)

        await event.bot.send_message(
            chat_id=event.chat_id,
            text=welcome_message,
            attachments=[
                builder.as_markup(),
            ]
        )




@main_router.message_created(Command('start'))
async def start(event: MessageCreated, context: MemoryContext, session: AsyncSession):
    await context.clear()
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


@main_router.message_callback(F.callback.payload == 'main_menu', Main_menu.menu)
async def main_menu(event: MessageCallback, context: MemoryContext, session: AsyncSession):
    await context.clear()
    # Получаем id пользователя в мах
    max_id = event.callback.user.user_id
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
        builder = await get_main_menu(user=user, session=session)



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
    utm_metriks = amo_fields.get('fields_id').get('utm_metriks')
    context_data = await context.get_data()
    utm_data = context_data.get('utm_data', {})
    attachments = (event.message.body.attachments if event.message and event.message.body else []) or []
    max_id = event.message.sender.user_id
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
                utm_campaign=utm_data.get("utm_campaign", ''),
                utm_medium=utm_data.get("utm_medium", ''),
                utm_content=utm_data.get("utm_content", ''),
                utm_term=utm_data.get("utm_term", ''),
                utm_source=utm_data.get("utm_source", ''),
                yclid=utm_data.get("yclid", ''),
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            lead_data = processing_lead(amo_api=amo_api, contact_id=contact_data["amo_contact_id"],
                                        pipeline_id=pipelines["hite_pro_education"],
                                        status_id=status_fields['admitted_to_training'], )

            if lead_data:  # Данные сделки найдены в амосрм
                user.amo_deal_id = lead_data["amo_deal_id"]
                await session.commit()
                await session.refresh(user)
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

    else:
        """Если контакт в АМО не найден, то создаём новый контакт, сделку, запись USER в таблице"""
        logger.info(f'В амо не найден контакт для пользователя max_id: {max_id}, телефон: {phone}')
        user = User(
            max_user_id= max_id,
            phone_number=phone,
            utm_campaign=utm_data.get("utm_campaign", ''),
            utm_medium=utm_data.get("utm_medium", ''),
            utm_content=utm_data.get("utm_content", ''),
            utm_term=utm_data.get("utm_term", ''),
            utm_source=utm_data.get("utm_source", ''),
            yclid=utm_data.get("yclid", ''),
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
        user.amo_deal_id = new_lead_id
        user.amo_contact_id = new_contact_id
        response = amo_api.push_lead_to_status(pipeline_id=pipelines.get('hite_pro_education'),
                                               status_id=status_fields.get('authorized_in_bot'),
                                               lead_id=str(user.amo_deal_id))

        logger.info(f'Для пользователя max_id: {max_id}, телефон: {phone} создан новый контакт {new_contact_id} и '
                    f'новая сделка {new_lead_id}')

    await session.commit()
    await session.refresh(user)

    await context.set_state(Main_menu.menu)
    builder = await get_main_menu(user=user, session=session)
    await  event.message.answer(
        text=start_message,
    )
    await event.message.answer(
        text=welcome_message,
        attachments=[
            builder.as_markup(),
        ]
    )


@main_router.message_callback(F.callback.payload == 'stat', Main_menu.menu)
async def stat(event: MessageCallback, context: MemoryContext, session: AsyncSession):
    max_id = event.callback.user.user_id


    result = await session.execute(
        select(User)
        .options(selectinload(User.lesson_results))
        .where(User.max_user_id == max_id)
    )
    user = result.scalar_one_or_none()

    lesson_names = {
        "lesson_1": "Урок №1",
        "lesson_2": "Урок №2",
        "lesson_3": "Урок №3",
        "lesson_4": "Урок №4",
        "lesson_5": "Урок №5",
        "lesson_6": "Урок №6",
        "lesson_7": "Урок №7",
        "exam": "Экзамен",
    }

    if user is None:
        return {"message": "Пользователь не найден."}

    results_by_key: dict[str, list[LessonResult]] = {}
    for lesson in user.lesson_results or []:
        results_by_key.setdefault(lesson.lesson_key, []).append(lesson)

    lines: list[str] = []
    for lesson_key in lesson_names.keys():
        lesson_title = lesson_names.get(lesson_key, lesson_key)
        lines.append(f"{lesson_title}:")

        attempts = results_by_key.get(lesson_key, [])
        attempts_sorted = sorted(attempts, key=lambda l: l.id or 0)
        total_attempts = len(attempts_sorted)
        successful_attempts = sum(1 for attempt in attempts_sorted if attempt.compleat)

        completed_attempts = [attempt for attempt in attempts_sorted if attempt.completed_at is not None]
        if completed_attempts:
            last_completed_attempt = max(
                completed_attempts,
                key=lambda attempt: (attempt.completed_at, attempt.id or 0),
            )
            if last_completed_attempt.score is not None:
                last_result_text = f"{last_completed_attempt.score} баллов."
            else:
                last_result_text = "нет данных."
        else:
            last_result_text = "нет данных."

        lines.append(f"📖 Всего попыток - {total_attempts}")
        lines.append(f"✅ Успешных - {successful_attempts}")
        lines.append(f"⏩ Результат последней попытки - {last_result_text}")

        lines.append("")
    lines.append("Успешной попыткой считается результат: более 80% правильных ответов.")
    message = "\n".join(lines).strip()
    # return {"message": message}
    builder = InlineKeyboardBuilder()
    builder.add(CallbackButton(text='Назад', payload='main_menu'))
    await event.message.edit(
        text=message,
        attachments=[
            builder.as_markup(),
        ]
    )