import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import async_session_factory
from db.models import User, HpLessonResult as LessonResult
from service.questions_lexicon import lessons

logger = logging.getLogger(__name__)



# Функция определяет результаты прохождения уроков и выдаёт наименования кнопок в зависимости от результата
async def get_lessons_buttons(user: User, session: AsyncSession) -> dict:
    lessons_access: dict[str, str|bool] = {}

    compleat_icon = '✅ '
    ready_icon = '▶️ '
    close_icon = '🔒 '

    if user is None or user.id is None:
        return {
            "lesson_1": '▶️ Первый урок',
            "lesson_2": "🔒 Второй урок",
            "lesson_3": "🔒 Третий урок",
        }

    result = await session.execute(
        select(LessonResult)
        .where(LessonResult.user_id == user.id)
    )
    lesson_results = result.scalars().all()

    # completed = {"lesson_1": False, "lesson_2": False, "lesson_3": False}
    completed = {lesson['title']: False for lesson in lessons}
    for lesson in lesson_results:
        if lesson.compleat and lesson.lesson_key in completed:
            completed[lesson.lesson_key] = True
            if all(completed.values()):
                break

    for index, lesson in enumerate(lessons):
        if index == 0:
            lessons_access[lesson['title']] = compleat_icon + lesson['descr'] if completed[lesson['title']] else ready_icon + lesson['descr']
        else:
            if completed[lesson['title']]:
                lessons_access[lesson['title']] = compleat_icon + lesson['descr']
            else:
                if completed[lessons[index-1]['title']]:
                    lessons_access[lesson['title']] = ready_icon + lesson['descr']
                else:
                    lessons_access[lesson['title']] = close_icon + lesson['descr']



    return lessons_access