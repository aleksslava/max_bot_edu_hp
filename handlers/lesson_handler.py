import datetime
import logging

from maxapi.types import Message
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db import async_session_factory
from db.models import HpLessonResult as LessonResult
from db.models import User
from service.service import check_push_to_new_status, checking_result, format_progress, format_results, lesson_access
from services.context import amo_api, config
from services.keyboards import build_lesson_confirm_keyboard, build_lesson_question_keyboard, build_result_keyboard
from services.message_utils import get_chat_id, get_text, get_user_id, parse_number_answers
from services.messaging import answer_or_edit, send_text
from services.runtime_state import LESSON_META, RuntimeSession, ordered_questions, runtime_sessions
from services.user_flow import render_menu

logger = logging.getLogger(__name__)


def _question_text(metadata: dict, question: dict, index: int, total: int, is_multi: bool) -> str:
    lines = [
        f"{metadata['title']} | Вопрос {index + 1}/{total}",
        "",
        str(question["title"]),
        "",
        "Выберите вариант кнопкой ниже." if not is_multi else "Выберите один или несколько вариантов кнопками ниже.",
    ]
    return "\n".join(lines)


async def start_lesson(message: Message, lesson_key: str) -> None:
    chat_id = get_chat_id(message)
    messenger_id = get_user_id(message)

    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.tg_user_id == messenger_id))
        user = result.scalar_one_or_none()
        if user is None:
            send_text(chat_id, "Пользователь не найден. Отправьте /start")
            return
        if user.amo_contact_id is None:
            send_text(chat_id, "Сначала авторизуйтесь по телефону: /auth")
            return

        if lesson_key != "lesson_1":
            has_access = await lesson_access(user=user, session=session, lesson_key=lesson_key)
            if not has_access:
                send_text(chat_id, "Доступ к этому уроку закрыт. Сначала завершите предыдущий урок.")
                return

        if lesson_key == "lesson_1" and user.start_edu is None:
            user.start_edu = datetime.datetime.utcnow()

        lesson = LessonResult(user_id=user.id, lesson_key=lesson_key)
        session.add(lesson)
        await session.commit()
        await session.refresh(lesson)

    if lesson_key == "exam":
        from handlers.exam_handler import start_exam

        await start_exam(message, lesson.id)
        return

    metadata = LESSON_META[lesson_key]
    runtime_sessions[messenger_id] = RuntimeSession(
        mode="lesson_question",
        lesson_key=lesson_key,
        lesson_id=lesson.id,
        question_index=0,
        answers={},
    )
    send_text(
        chat_id,
        f"{metadata['title']}\nВидео урока: {metadata['video_url']}",
    )
    await send_current_lesson_question(message, edit=False)


async def send_current_lesson_question(message: Message, edit: bool) -> None:
    chat_id = get_chat_id(message)
    messenger_id = get_user_id(message)
    session_data = runtime_sessions.get(messenger_id)
    if session_data is None or session_data.lesson_key is None:
        send_text(chat_id, "Активный урок не найден. Выберите урок в меню: /menu")
        return

    metadata = LESSON_META[session_data.lesson_key]
    question_list = ordered_questions(metadata["questions"])
    question = question_list[session_data.question_index]
    answers = question["answers"]
    is_multi = sum(1 for item in answers if item[2]) > 1
    text = _question_text(metadata, question, session_data.question_index, len(question_list), is_multi)
    keyboard = build_lesson_question_keyboard(session_data, answers)

    try:
        await answer_or_edit(message, text=text, attachments=keyboard, edit=edit)
    except Exception:
        await answer_or_edit(message, text=text, attachments=keyboard, edit=False)


def _save_current_question_result(session_data: RuntimeSession) -> tuple[bool, int]:
    metadata = LESSON_META[session_data.lesson_key]
    question_list = ordered_questions(metadata["questions"])
    question = question_list[session_data.question_index]
    answers = question["answers"]

    if not session_data.draft_selection:
        return False, len(question_list)

    selected_set = set(session_data.draft_selection)
    per_option_result: dict[str, bool] = {}
    for idx, (answer_text, _, should_be_selected) in enumerate(answers, start=1):
        user_selected = idx in selected_set
        per_option_result[answer_text] = user_selected == should_be_selected

    session_data.answers[str(question["key"])] = per_option_result
    session_data.question_index += 1
    session_data.draft_selection.clear()
    return True, len(question_list)


async def on_lesson_pick(message: Message, option_index: int) -> None:
    messenger_id = get_user_id(message)
    session_data = runtime_sessions.get(messenger_id)
    if session_data is None or session_data.mode != "lesson_question" or session_data.lesson_key is None:
        return

    metadata = LESSON_META[session_data.lesson_key]
    question_list = ordered_questions(metadata["questions"])
    question = question_list[session_data.question_index]
    answers = question["answers"]
    if option_index < 1 or option_index > len(answers):
        return

    is_multi = sum(1 for item in answers if item[2]) > 1
    if is_multi:
        if option_index in session_data.draft_selection:
            session_data.draft_selection.remove(option_index)
        else:
            session_data.draft_selection.add(option_index)
    else:
        session_data.draft_selection = {option_index}

    await send_current_lesson_question(message, edit=True)


async def on_lesson_clear(message: Message) -> None:
    messenger_id = get_user_id(message)
    session_data = runtime_sessions.get(messenger_id)
    if session_data is None:
        return
    session_data.draft_selection.clear()
    await send_current_lesson_question(message, edit=True)


async def on_lesson_submit(message: Message) -> None:
    chat_id = get_chat_id(message)
    messenger_id = get_user_id(message)
    session_data = runtime_sessions.get(messenger_id)
    if session_data is None or session_data.lesson_key is None:
        return

    accepted, total_questions = _save_current_question_result(session_data)
    if not accepted:
        send_text(chat_id, "Выберите хотя бы один вариант перед отправкой ответа.")
        return

    if session_data.question_index < total_questions:
        await send_current_lesson_question(message, edit=True)
        return

    session_data.mode = "lesson_confirm"
    progress = format_progress(session_data.answers, total_questions=total_questions)
    text = f"{progress}\n\nПроверьте ответы и отправьте результат."
    keyboard = build_lesson_confirm_keyboard()
    try:
        await answer_or_edit(message, text=text, attachments=keyboard, edit=True)
    except Exception:
        send_text(chat_id, text, attachments=keyboard)


async def finalize_lesson(message: Message) -> None:
    chat_id = get_chat_id(message)
    messenger_id = get_user_id(message)
    session_data = runtime_sessions.get(messenger_id)
    if session_data is None or session_data.lesson_key is None or session_data.lesson_id is None:
        send_text(chat_id, "Активный урок не найден. Откройте меню: /menu")
        return

    metadata = LESSON_META[session_data.lesson_key]
    question_list = ordered_questions(metadata["questions"])
    check_data = checking_result(session_data.answers, total_questions=len(question_list))
    score = check_data["score"]
    passed = check_data["passed"]
    result_text = format_results(session_data.answers, total_questions=len(question_list))

    async with async_session_factory() as session:
        lesson_result = await session.execute(
            select(LessonResult).options(selectinload(LessonResult.user)).where(LessonResult.id == session_data.lesson_id)
        )
        lesson = lesson_result.scalar_one_or_none()
        if lesson is None:
            send_text(chat_id, "Попытка урока не найдена. Начните урок заново.")
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
        amo_api.add_new_note_to_lead(lead_id=user.amo_deal_id, text=f"{metadata['amo_note_title']}: {result_text}")
        status_id_in_amo = amo_api.get_lead_by_id(lead_id=user.amo_deal_id).get("status_id")
        can_push = await check_push_to_new_status(
            lesson_key=metadata["status_key"],
            lead_status=status_id_in_amo,
        )
        if passed and can_push:
            amo_api.push_lead_to_status(
                pipeline_id=config.amo_fields.get("pipelines", {}).get("hite_pro_education"),
                status_id=config.amo_fields.get("statuses", {}).get(metadata["status_key"]),
                lead_id=str(user.amo_deal_id),
            )
    except Exception:
        logger.exception("Ошибка синхронизации результата урока с amoCRM")

    runtime_sessions.pop(messenger_id, None)
    send_text(chat_id, f"Ваши результаты:\n\n{result_text}", attachments=build_result_keyboard())
    await render_menu(message)


async def on_lesson_restart(message: Message) -> None:
    messenger_id = get_user_id(message)
    session_data = runtime_sessions.get(messenger_id)
    if session_data is None:
        return
    session_data.mode = "lesson_question"
    session_data.question_index = 0
    session_data.answers = {}
    session_data.draft_selection = set()
    await send_current_lesson_question(message, edit=True)


# Text fallback for compatibility if user types instead of callbacks.
async def handle_lesson_answer(message: Message) -> None:
    messenger_id = get_user_id(message)
    session_data = runtime_sessions.get(messenger_id)
    if session_data is None:
        return
    selected_numbers = parse_number_answers(get_text(message))
    if not selected_numbers:
        return
    session_data.draft_selection = set(selected_numbers)
    await on_lesson_submit(message)


async def handle_lesson_confirm(message: Message) -> None:
    text = get_text(message).strip().lower()
    if text in {"отправить", "да", "готово"}:
        await finalize_lesson(message)
    elif text in {"повтор", "заново"}:
        await on_lesson_restart(message)
