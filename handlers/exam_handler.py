import datetime
import logging

from maxapi.types import Message
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db import async_session_factory
from db.models import HpLessonResult as LessonResult
from service.questions_lexicon import edu_compleat_text, exam_in_message, exam_lesson, urls_to_messanger
from service.service import check_push_to_new_status
from services.context import amo_api, config
from services.keyboards import build_exam_question_keyboard, build_result_keyboard
from services.message_utils import clean_markup, get_chat_id, get_user_id
from services.messaging import answer_or_edit, send_text
from services.runtime_state import RuntimeSession, evaluate_exam_answers, runtime_sessions
from services.user_flow import get_user, render_menu

logger = logging.getLogger(__name__)


def _get_exam_question_and_keys(index: int) -> tuple[str, list[str]]:
    question_key, expected_map = list(exam_lesson.items())[index]
    return question_key, list(expected_map.keys())


def _exam_text(index: int, total: int, keys: list[str], counts: dict[str, int]) -> str:
    lines = [
        f"Экзамен | Вопрос {index + 1}/{total}",
        "Используйте кнопки + и - для указания количества.",
        "",
    ]
    for idx, key in enumerate(keys, start=1):
        lines.append(f"{idx}. {key}: {counts.get(key, 0)}")
    return "\n".join(lines)


async def start_exam(message: Message, lesson_id: int) -> None:
    chat_id = get_chat_id(message)
    messenger_id = get_user_id(message)

    runtime_sessions[messenger_id] = RuntimeSession(
        mode="exam_question",
        lesson_key="exam",
        lesson_id=lesson_id,
        exam_answers={},
        exam_index=0,
        exam_draft_counts={},
    )

    try:
        user = await get_user(messenger_id)
        if user and user.amo_deal_id:
            amo_api.push_lead_to_status(
                pipeline_id=config.amo_fields.get("pipelines", {}).get("hite_pro_education"),
                status_id=config.amo_fields.get("statuses", {}).get("ready_to_exam"),
                lead_id=str(user.amo_deal_id),
            )
    except Exception:
        logger.exception("Не удалось перевести сделку в статус ready_to_exam")

    send_text(chat_id, clean_markup(exam_in_message))
    await send_current_exam_question(message, edit=False)


async def send_current_exam_question(message: Message, edit: bool) -> None:
    chat_id = get_chat_id(message)
    messenger_id = get_user_id(message)
    session_data = runtime_sessions.get(messenger_id)
    if session_data is None:
        send_text(chat_id, "Экзамен не запущен. Откройте /menu")
        return

    question_key, keys = _get_exam_question_and_keys(session_data.exam_index)
    if not session_data.exam_draft_counts:
        session_data.exam_draft_counts = {key: 0 for key in keys}

    text = _exam_text(
        index=session_data.exam_index,
        total=len(exam_lesson),
        keys=keys,
        counts=session_data.exam_draft_counts,
    )
    keyboard = build_exam_question_keyboard(keys, session_data.exam_draft_counts)

    try:
        await answer_or_edit(message, text=text, attachments=keyboard, edit=edit)
    except Exception:
        await answer_or_edit(message, text=text, attachments=keyboard, edit=False)


async def on_exam_change(message: Message, item_index: int, delta: int) -> None:
    messenger_id = get_user_id(message)
    session_data = runtime_sessions.get(messenger_id)
    if session_data is None:
        return

    _, keys = _get_exam_question_and_keys(session_data.exam_index)
    if item_index < 0 or item_index >= len(keys):
        return

    key = keys[item_index]
    current = session_data.exam_draft_counts.get(key, 0)
    session_data.exam_draft_counts[key] = max(0, min(99, current + delta))
    await send_current_exam_question(message, edit=True)


async def on_exam_clear(message: Message) -> None:
    messenger_id = get_user_id(message)
    session_data = runtime_sessions.get(messenger_id)
    if session_data is None:
        return
    _, keys = _get_exam_question_and_keys(session_data.exam_index)
    session_data.exam_draft_counts = {key: 0 for key in keys}
    await send_current_exam_question(message, edit=True)


async def on_exam_submit(message: Message) -> None:
    messenger_id = get_user_id(message)
    session_data = runtime_sessions.get(messenger_id)
    if session_data is None:
        return

    question_key, keys = _get_exam_question_and_keys(session_data.exam_index)
    if any(key not in session_data.exam_draft_counts for key in keys):
        return

    session_data.exam_answers[question_key] = dict(session_data.exam_draft_counts)
    session_data.exam_index += 1
    session_data.exam_draft_counts = {}

    if session_data.exam_index < len(exam_lesson):
        await send_current_exam_question(message, edit=True)
        return

    await finalize_exam(message)


async def finalize_exam(message: Message) -> None:
    chat_id = get_chat_id(message)
    messenger_id = get_user_id(message)
    session_data = runtime_sessions.get(messenger_id)
    if session_data is None or session_data.lesson_id is None:
        send_text(chat_id, "Экзамен не найден. Запустите заново: /exam")
        return

    result_data = evaluate_exam_answers(session_data.exam_answers)
    score = int(result_data["score"])
    passed = bool(result_data["passed"])
    result_text = str(result_data["result_text"])
    amo_note_text = str(result_data["amo_note_text"])

    async with async_session_factory() as session:
        lesson_result = await session.execute(
            select(LessonResult).options(selectinload(LessonResult.user)).where(LessonResult.id == session_data.lesson_id)
        )
        lesson = lesson_result.scalar_one_or_none()
        if lesson is None:
            send_text(chat_id, "Попытка экзамена не найдена.")
            runtime_sessions.pop(messenger_id, None)
            return

        lesson.score = score
        lesson.compleat = passed
        lesson.completed_at = datetime.datetime.utcnow()
        user = lesson.user
        await session.commit()
        await session.refresh(lesson)
        await session.refresh(user)

    try:
        amo_api.add_new_note_to_lead(lead_id=user.amo_deal_id, text=amo_note_text)
        status_id_in_amo = amo_api.get_lead_by_id(lead_id=user.amo_deal_id).get("status_id")
        can_push = await check_push_to_new_status(lesson_key="compleat_exam", lead_status=status_id_in_amo)
        if passed and can_push:
            amo_api.push_lead_to_status(
                pipeline_id=config.amo_fields.get("pipelines", {}).get("hite_pro_education"),
                status_id=config.amo_fields.get("statuses", {}).get("compleat_exam"),
                lead_id=str(user.amo_deal_id),
            )
    except Exception:
        logger.exception("Ошибка синхронизации результата экзамена с amoCRM")

    runtime_sessions.pop(messenger_id, None)
    if passed:
        send_text(chat_id, "Экзамен пройден!\n\n" + result_text)
        send_text(chat_id, clean_markup(edu_compleat_text))
        send_text(
            chat_id,
            f"Сообщить менеджеру в MAX: {urls_to_messanger.get('max')}",
            attachments=build_result_keyboard(),
        )
    else:
        send_text(chat_id, "Экзамен не пройден.\n\n" + result_text, attachments=build_result_keyboard())
    await render_menu(message)


async def handle_exam_answer(message: Message) -> None:
    # Text fallback, no-op in inline mode.
    return
