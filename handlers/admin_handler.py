import datetime
import tempfile
from pathlib import Path

from maxapi.types import Message
from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db import async_session_factory
from db.models import HpLessonResult as LessonResult
from db.models import User
from services.context import bot
from services.message_utils import get_chat_id, get_user_id
from services.messaging import send_text


async def send_user_stats(message: Message) -> None:
    chat_id = get_chat_id(message)
    messenger_id = get_user_id(message)

    async with async_session_factory() as session:
        result = await session.execute(
            select(User).options(selectinload(User.lesson_results)).where(User.tg_user_id == messenger_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            send_text(chat_id, "Пользователь не найден.")
            return

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

        results_by_key: dict[str, list[LessonResult]] = {}
        for lesson in user.lesson_results or []:
            results_by_key.setdefault(lesson.lesson_key, []).append(lesson)

        lines: list[str] = []
        for lesson_key in lesson_names:
            lesson_title = lesson_names[lesson_key]
            attempts = sorted(results_by_key.get(lesson_key, []), key=lambda item: item.id or 0)
            successful_attempts = sum(1 for item in attempts if item.compleat)
            completed_attempts = [item for item in attempts if item.completed_at is not None]

            if completed_attempts:
                last_completed = max(completed_attempts, key=lambda item: (item.completed_at, item.id or 0))
                last_score = f"{last_completed.score} баллов" if last_completed.score is not None else "нет данных"
            else:
                last_score = "нет данных"

            lines.append(f"{lesson_title}:")
            lines.append(f"Всего попыток: {len(attempts)}")
            lines.append(f"Успешных: {successful_attempts}")
            lines.append(f"Последняя попытка: {last_score}")
            lines.append("")

        lines.append("Успешная попытка урока: 80% и выше.")
        send_text(chat_id, "\n".join(lines))


async def admin_show_help(message: Message) -> None:
    chat_id = get_chat_id(message)
    send_text(
        chat_id,
        "Админ-команды:\n"
        "/admin_stats - результаты по пользователям\n"
        "/admin_export - выгрузка в XLSX\n"
        "/admin_add <max_id> - назначить администратора\n"
        "/admin_del <max_id> - удалить пользователя",
    )


async def admin_add(message: Message, target_id: int) -> None:
    chat_id = get_chat_id(message)
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.tg_user_id == target_id))
        user = result.scalar_one_or_none()
        if user is None:
            send_text(chat_id, f"Пользователь max_id={target_id} не найден.")
            return
        user.is_admin = True
        await session.commit()
        send_text(chat_id, f"Пользователю max_id={target_id} выданы права администратора.")


async def admin_delete_user(message: Message, target_id: int) -> None:
    chat_id = get_chat_id(message)
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.tg_user_id == target_id))
        user = result.scalar_one_or_none()
        if user is None:
            send_text(chat_id, f"Пользователь max_id={target_id} не найден.")
            return
        await session.delete(user)
        await session.commit()
        send_text(chat_id, f"Пользователь max_id={target_id} удален.")


async def admin_stats(message: Message) -> None:
    chat_id = get_chat_id(message)
    async with async_session_factory() as session:
        result = await session.execute(select(User).options(selectinload(User.lesson_results)).order_by(User.id))
        users = result.scalars().all()
        if not users:
            send_text(chat_id, "Пользователи в БД не найдены.")
            return

        lines = ["Результаты уроков по пользователям", ""]
        for user in users:
            lines.append(
                f"user_id={user.id} max_id={user.tg_user_id} "
                f"name={user.first_name or '-'} {user.last_name or '-'}"
            )
            lessons_items = sorted(user.lesson_results or [], key=lambda lesson: lesson.id or 0)
            if not lessons_items:
                lines.append("  результатов нет")
                lines.append("")
                continue

            for lesson in lessons_items:
                lines.append(
                    "  "
                    + " | ".join(
                        [
                            f"lesson_id={lesson.id}",
                            f"key={lesson.lesson_key}",
                            f"score={lesson.score if lesson.score is not None else '-'}",
                            f"compleat={lesson.compleat}",
                            f"started_at={lesson.started_at or '-'}",
                            f"completed_at={lesson.completed_at or '-'}",
                        ]
                    )
                )
            lines.append("")

        send_text(chat_id, "\n".join(lines))


async def admin_export(message: Message) -> None:
    chat_id = get_chat_id(message)
    async with async_session_factory() as session:
        result = await session.execute(select(User).options(selectinload(User.lesson_results)).order_by(User.id))
        users = result.scalars().all()
        if not users:
            send_text(chat_id, "Пользователи в БД не найдены.")
            return

        wb = Workbook()
        ws = wb.active
        ws.title = "users_results"
        ws.append(
            [
                "user_id",
                "max_id",
                "username",
                "first_name",
                "last_name",
                "phone_number",
                "amo_contact_id",
                "amo_deal_id",
                "lesson_id",
                "lesson_key",
                "score",
                "compleat",
                "started_at",
                "completed_at",
            ]
        )

        def fmt_dt(value: datetime.datetime | None) -> str:
            if value is None:
                return ""
            return value.strftime("%Y-%m-%d %H:%M:%S")

        for user in users:
            lessons_items = sorted(user.lesson_results or [], key=lambda lesson: lesson.id or 0)
            if not lessons_items:
                ws.append(
                    [
                        user.id,
                        user.tg_user_id,
                        user.username or "",
                        user.first_name or "",
                        user.last_name or "",
                        user.phone_number or "",
                        user.amo_contact_id or "",
                        user.amo_deal_id or "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                    ]
                )
                continue

            for lesson in lessons_items:
                ws.append(
                    [
                        user.id,
                        user.tg_user_id,
                        user.username or "",
                        user.first_name or "",
                        user.last_name or "",
                        user.phone_number or "",
                        user.amo_contact_id or "",
                        user.amo_deal_id or "",
                        lesson.id,
                        lesson.lesson_key,
                        lesson.score if lesson.score is not None else "",
                        lesson.compleat,
                        fmt_dt(lesson.started_at),
                        fmt_dt(lesson.completed_at),
                    ]
                )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        path = Path(tmp.name)
    wb.save(path)

    try:
        bot.send_file(chat_id=chat_id, file=str(path), file_type="file", caption="Таблица пользователей и результатов")
    finally:
        path.unlink(missing_ok=True)
