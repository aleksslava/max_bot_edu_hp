import logging

from maxapi import F
from maxapi.types import Message

from handlers.admin_handler import (
    admin_add,
    admin_delete_user,
    admin_export,
    admin_stats,
    send_user_stats,
)
from handlers.exam_handler import on_exam_change, on_exam_clear, on_exam_submit
from handlers.lesson_handler import (
    finalize_lesson,
    on_lesson_clear,
    on_lesson_pick,
    on_lesson_restart,
    on_lesson_submit,
    start_lesson,
)
from services.context import dp
from services.keyboards import build_admin_keyboard
from services.message_utils import (
    get_chat_id,
    get_text,
    get_user_id,
    parse_number_answers,
)
from services.messaging import send_text
from services.runtime_state import RuntimeSession, runtime_sessions
from services.user_flow import (
    authorize_user_by_phone,
    fetch_utm_data,
    get_or_create_user,
    is_admin,
    open_admin_menu,
    render_menu,
)

logger = logging.getLogger(__name__)

ADMIN_ADD_MODE = "await_admin_add_id"
ADMIN_DEL_MODE = "await_admin_del_id"


def _extract_target_id(text: str) -> int | None:
    raw = text.strip()
    if not raw:
        return None

    try:
        target_id = int(raw)
    except ValueError:
        numbers = parse_number_answers(raw)
        if not numbers:
            return None
        target_id = numbers[0]

    if target_id <= 0:
        return None
    return target_id


async def process_command(message: Message, command: str, args: str) -> None:
    chat_id = get_chat_id(message)
    messenger_id = get_user_id(message)

    if command == "/start":
        runtime_sessions.pop(messenger_id, None)
        webhook_id = args.strip()
        utm_data = fetch_utm_data(webhook_id)
        user = await get_or_create_user(message, utm_data=utm_data)
        if user.amo_contact_id is None:
            runtime_sessions[messenger_id] = RuntimeSession(mode="await_phone")
            send_text(chat_id, "Для доступа к обучению отправьте номер телефона в формате +7XXXXXXXXXX")
            return
        await render_menu(message)
        return

    if command == "/menu":
        runtime_sessions.pop(messenger_id, None)
        await render_menu(message)
        return

    if command == "/auth":
        runtime_sessions[messenger_id] = RuntimeSession(mode="await_phone")
        send_text(chat_id, "Отправьте номер телефона в формате +7XXXXXXXXXX")
        return

    # Backward-compatible command fallbacks.
    if command in {"/lesson1", "/lesson2", "/lesson3", "/lesson4", "/lesson5", "/lesson6", "/lesson7"}:
        index = int(command[-1])
        await start_lesson(message, f"lesson_{index}")
        return

    if command == "/exam":
        await start_lesson(message, "exam")
        return

    if command == "/stats":
        await send_user_stats(message)
        return

    if command == "/admin":
        if not await is_admin(messenger_id):
            send_text(chat_id, "Недостаточно прав.")
            return
        await open_admin_menu(message)
        return

    if command == "/admin_stats":
        if not await is_admin(messenger_id):
            send_text(chat_id, "Недостаточно прав.")
            return
        await admin_stats(message)
        return

    if command == "/admin_export":
        if not await is_admin(messenger_id):
            send_text(chat_id, "Недостаточно прав.")
            return
        await admin_export(message)
        return

    send_text(chat_id, "Используйте inline-кнопки под сообщениями. Откройте меню: /menu")


async def process_non_command(message: Message) -> None:
    chat_id = get_chat_id(message)
    messenger_id = get_user_id(message)
    session_data = runtime_sessions.get(messenger_id)
    incoming_text = get_text(message)

    if session_data is None:
        send_text(chat_id, "Используйте /start или /menu")
        return

    if session_data.mode == "await_phone":
        await authorize_user_by_phone(message, incoming_text)
        return

    if session_data.mode == ADMIN_ADD_MODE:
        if not await is_admin(messenger_id):
            runtime_sessions.pop(messenger_id, None)
            send_text(chat_id, "Недостаточно прав.")
            return

        target_id = _extract_target_id(incoming_text)
        if target_id is None:
            send_text(chat_id, "Введите корректный max_id пользователя числом.")
            return

        runtime_sessions.pop(messenger_id, None)
        await admin_add(message, target_id)
        await open_admin_menu(message)
        return

    if session_data.mode == ADMIN_DEL_MODE:
        if not await is_admin(messenger_id):
            runtime_sessions.pop(messenger_id, None)
            send_text(chat_id, "Недостаточно прав.")
            return

        target_id = _extract_target_id(incoming_text)
        if target_id is None:
            send_text(chat_id, "Введите корректный max_id пользователя числом.")
            return

        runtime_sessions.pop(messenger_id, None)
        await admin_delete_user(message, target_id)
        await open_admin_menu(message)
        return

    send_text(chat_id, "Используйте inline-кнопки под сообщениями.")


async def process_callback(message: Message, payload: str) -> None:
    chat_id = get_chat_id(message)
    messenger_id = get_user_id(message)

    if payload == "menu:open":
        runtime_sessions.pop(messenger_id, None)
        await render_menu(message)
        return

    if payload == "menu:auth":
        runtime_sessions[messenger_id] = RuntimeSession(mode="await_phone")
        send_text(chat_id, "Отправьте номер телефона в формате +7XXXXXXXXXX")
        return

    if payload == "menu:stats":
        await send_user_stats(message)
        return

    if payload == "menu:exam":
        await start_lesson(message, "exam")
        return

    if payload == "menu:admin":
        if not await is_admin(messenger_id):
            send_text(chat_id, "Недостаточно прав.")
            return
        await open_admin_menu(message)
        return

    if payload.startswith("menu:lesson:"):
        try:
            lesson_index = int(payload.rsplit(":", 1)[1])
        except ValueError:
            return
        await start_lesson(message, f"lesson_{lesson_index}")
        return

    if payload.startswith("admin:"):
        if not await is_admin(messenger_id):
            send_text(chat_id, "Недостаточно прав.")
            return

        if payload == "admin:stats":
            await admin_stats(message)
            return

        if payload == "admin:export":
            await admin_export(message)
            return

        if payload == "admin:add":
            runtime_sessions[messenger_id] = RuntimeSession(mode=ADMIN_ADD_MODE)
            send_text(chat_id, "Введите max_id пользователя для назначения администратором.")
            return

        if payload == "admin:del":
            runtime_sessions[messenger_id] = RuntimeSession(mode=ADMIN_DEL_MODE)
            send_text(chat_id, "Введите max_id пользователя для удаления.")
            return

        if payload == "admin:help":
            send_text(
                chat_id,
                "Как работать с админ-правами:\n"
                "1. Нажмите «Назначить админа» или «Удалить пользователя».\n"
                "2. Отправьте max_id пользователя числом.\n"
                "3. После выполнения бот вернет вас в админ-меню.",
                attachments=build_admin_keyboard(),
            )
            return

    if payload.startswith("lesson:pick:"):
        try:
            option_index = int(payload.rsplit(":", 1)[1])
        except ValueError:
            return
        await on_lesson_pick(message, option_index)
        return

    if payload == "lesson:submit":
        await on_lesson_submit(message)
        return

    if payload == "lesson:clear":
        await on_lesson_clear(message)
        return

    if payload == "lesson:finish":
        await finalize_lesson(message)
        return

    if payload == "lesson:restart":
        await on_lesson_restart(message)
        return

    if payload.startswith("exam:inc:"):
        try:
            item_index = int(payload.rsplit(":", 1)[1])
        except ValueError:
            return
        await on_exam_change(message, item_index=item_index, delta=1)
        return

    if payload.startswith("exam:dec:"):
        try:
            item_index = int(payload.rsplit(":", 1)[1])
        except ValueError:
            return
        await on_exam_change(message, item_index=item_index, delta=-1)
        return

    if payload == "exam:clear":
        await on_exam_clear(message)
        return

    if payload == "exam:submit":
        await on_exam_submit(message)
        return

    if payload == "exam:noop":
        return


@dp.message_created(F.message.body.text)
async def on_text_message(event):
    try:
        message = event.message
        user_id = get_user_id(message)
        if user_id == 0:
            return

        text = get_text(message)
        if not text:
            return

        if text.startswith("/"):
            first, *tail = text.split(maxsplit=1)
            command = first.split("@")[0].lower()
            args = tail[0] if tail else ""
            await process_command(message, command, args)
            return

        await process_non_command(message)
    except Exception:
        logger.exception("Ошибка обработки входящего сообщения")
        send_text(get_chat_id(event.message), "Произошла ошибка. Попробуйте снова или отправьте /menu")


@dp.message_callback()
async def on_message_callback(event):
    try:
        message = event.message
        payload = getattr(event.callback, "payload", "") or ""
        if message is None or not payload:
            return

        await process_callback(message, payload)

        try:
            await event.answer()
        except Exception:
            pass
    except Exception:
        logger.exception("Ошибка обработки callback")
        if getattr(event, "message", None) is not None:
            send_text(get_chat_id(event.message), "Произошла ошибка при обработке кнопки. Откройте /menu")
