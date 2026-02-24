import logging

import requests
from maxapi.types import Message
from sqlalchemy import select

from amo_api.amo_service import processing_contact, processing_lead
from db import async_session_factory
from db.models import User
from services.context import amo_api, config
from services.keyboards import build_admin_keyboard, build_main_menu_keyboard
from services.message_utils import (
    clean_markup,
    get_chat_id,
    get_user_id,
    get_user_name,
    normalize_phone,
)
from services.messaging import send_text
from services.runtime_state import RuntimeSession, runtime_sessions

from service.questions_lexicon import welcome_message
from service.service import get_lessons_buttons

logger = logging.getLogger(__name__)


def fetch_utm_data(webhook_id: str) -> dict:
    utm_data = {
        "utm_source": "",
        "utm_medium": "",
        "utm_campaign": "",
        "utm_content": "",
        "utm_term": "",
        "yclid": "",
    }
    if not webhook_id:
        return utm_data
    try:
        response = requests.get(
            f"{config.webhook_url}{webhook_id}",
            params={"utm_token": config.utm_token},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict):
            utm_data.update(payload)
    except requests.RequestException:
        logger.exception("Не удалось получить UTM-метки для webhook_id=%s", webhook_id)
    return utm_data


async def get_or_create_user(message: Message, utm_data: dict | None = None) -> User:
    if utm_data is None:
        utm_data = {}
    messenger_id = get_user_id(message)
    user_name = get_user_name(message)

    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.tg_user_id == messenger_id))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                tg_user_id=messenger_id,
                username=user_name,
                first_name=user_name,
                last_name="",
                utm_campaign=utm_data.get("utm_campaign", ""),
                utm_medium=utm_data.get("utm_medium", ""),
                utm_content=utm_data.get("utm_content", ""),
                utm_term=utm_data.get("utm_term", ""),
                utm_source=utm_data.get("utm_source", ""),
                yclid=utm_data.get("yclid", ""),
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            logger.info("Создан пользователь max_id=%s", messenger_id)
        else:
            if user_name and user.username != user_name:
                user.username = user_name
                user.first_name = user_name
                await session.commit()
        return user


async def get_user(messenger_id: int) -> User | None:
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.tg_user_id == messenger_id))
        return result.scalar_one_or_none()


async def is_admin(messenger_id: int) -> bool:
    if str(messenger_id) == str(config.admin):
        return True
    user = await get_user(messenger_id)
    return bool(user and user.is_admin)


async def render_menu(message: Message) -> None:
    chat_id = get_chat_id(message)
    messenger_id = get_user_id(message)

    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.tg_user_id == messenger_id))
        user = result.scalar_one_or_none()
        if user is None:
            send_text(chat_id, "Пользователь не найден. Отправьте /start")
            return

        lines: list[str] = [clean_markup(welcome_message)]
        if user.amo_contact_id is None:
            lines.append("Для доступа к обучению нужна авторизация по телефону.")
            keyboard = build_main_menu_keyboard(authorized=False, is_admin=await is_admin(messenger_id))
        else:
            lessons_text = await get_lessons_buttons(user, session)
            lines.append("Доступные разделы:")
            lines.append("Выберите раздел кнопками ниже.")
            keyboard = build_main_menu_keyboard(
                authorized=True,
                lessons_text=lessons_text,
                is_admin=await is_admin(messenger_id),
            )

        send_text(chat_id, "\n".join(lines), attachments=keyboard)


async def open_admin_menu(message: Message) -> None:
    chat_id = get_chat_id(message)
    text = (
        "Админ-панель.\n\n"
        "Для назначения/удаления админов используйте команды:\n"
        "/admin_add <max_id>\n"
        "/admin_del <max_id>"
    )
    send_text(chat_id, text, attachments=build_admin_keyboard())


async def authorize_user_by_phone(message: Message, phone_input: str) -> None:
    chat_id = get_chat_id(message)
    messenger_id = get_user_id(message)
    normalized_phone = normalize_phone(phone_input)
    if normalized_phone is None:
        send_text(chat_id, "Не удалось распознать номер. Введите телефон в формате +7XXXXXXXXXX")
        return

    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.tg_user_id == messenger_id))
        user = result.scalar_one_or_none()
        if user is None:
            send_text(chat_id, "Пользователь не найден. Отправьте /start")
            return

        status_fields: dict = config.amo_fields.get("statuses", {})
        pipelines: dict = config.amo_fields.get("pipelines", {})
        fields_id: dict = config.amo_fields.get("fields_id", {})
        utm_metriks = fields_id.get("utm_metriks", {})
        messenger_id_field = fields_id.get("max_id") or fields_id.get("tg_id")
        messenger_username_field = fields_id.get("max_username") or fields_id.get("tg_username")
        username = user.username or f"user_{messenger_id}"

        user.phone_number = normalized_phone
        contact_data = processing_contact(amo_api=amo_api, contact_phone_number=normalized_phone)

        if contact_data:
            if not contact_data["tg_id"]:
                amo_api.add_tg_to_contact(
                    contact_id=contact_data["amo_contact_id"],
                    tg_id=messenger_id,
                    tg_id_field=messenger_id_field,
                    username_id=messenger_username_field,
                    username=username,
                )

            user.first_name = contact_data["first_name"] or user.first_name
            user.last_name = contact_data["last_name"] or user.last_name
            user.amo_contact_id = contact_data["amo_contact_id"]

            lead_data = processing_lead(
                amo_api=amo_api,
                contact_id=contact_data["amo_contact_id"],
                pipeline_id=pipelines["hite_pro_education"],
                status_id=status_fields["admitted_to_training"],
            )
            if lead_data:
                user.amo_deal_id = lead_data["amo_deal_id"]
            else:
                new_lead_id = amo_api.send_lead_to_amo(
                    pipeline_id=pipelines.get("hite_pro_education"),
                    status_id=status_fields.get("admitted_to_training"),
                    contact_id=contact_data.get("amo_contact_id"),
                    utm_metriks_fields=utm_metriks,
                    user=user,
                )
                user.amo_deal_id = new_lead_id
        else:
            user_name = user.username or f"user_{messenger_id}"
            new_contact_id = amo_api.create_new_contact(
                first_name=user_name,
                last_name="",
                phone=normalized_phone,
                tg_id_field=messenger_id_field,
                tg_id=messenger_id,
                username_id=messenger_username_field,
                username=username,
            )
            new_lead_id = amo_api.send_lead_to_amo(
                pipeline_id=pipelines.get("hite_pro_education"),
                status_id=status_fields.get("admitted_to_training"),
                contact_id=new_contact_id,
                utm_metriks_fields=utm_metriks,
                user=user,
            )
            user.amo_contact_id = new_contact_id
            user.amo_deal_id = new_lead_id

        await session.commit()
        await session.refresh(user)

        if user.amo_deal_id:
            amo_api.push_lead_to_status(
                pipeline_id=pipelines.get("hite_pro_education"),
                status_id=status_fields.get("authorized_in_bot"),
                lead_id=str(user.amo_deal_id),
            )

    runtime_sessions.pop(messenger_id, None)
    send_text(chat_id, "Спасибо! Номер получен, доступ открыт.")
    await render_menu(message)
