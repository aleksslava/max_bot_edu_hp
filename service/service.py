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


async def check_push_to_new_status(lesson_key: str, lead_status: int) -> bool:
    lead_status = int(lead_status)
    logger.info(f'Входящие lesson_key: {lesson_key}, lead_status: {lead_status}')
    statuses_list = [
        {'key':'admitted_to_training',
         'id': 47244117},
        {'key': 'authorized_in_bot',
         'id': 65758021},
        {'key': 'compleat_lesson_1',
         'id': 35444481},
        {'key': 'compleat_lesson_2',
         'id': 35444484},
        {'key': 'compleat_lesson_3',
         'id': 41608782},
        {'key': 'compleat_lesson_4',
         'id': 41608785},
        {'key': 'compleat_lesson_5',
         'id': 41608788},
        {'key': 'compleat_lesson_6',
         'id': 41608791},
        {'key': 'compleat_lesson_7',
         'id': 58699973},
        {'key': 'ready_to_exam',
         'id': 41608797},
        {'key': 'compleat_exam',
         'id': 41608800},
        {'key': 'compleat_training',
         'id': 35440800}
        ]
    lesson_index = 0
    lead_index = 0

    for index, lesson in enumerate(statuses_list):
        if lesson['key'] == lesson_key:
            lesson_index = index

        if lesson['id'] == lead_status:
            lead_index = index
    logger.info(f'Индекс lesson_key: {lesson_key}, lead_status: {lead_status}')

    if lead_index >= lesson_index:
        logger.info('Функция возвратила False')
        return False
    else:
        logger.info('Функция возвратила True')
        return True


async def lesson_access(user: User, session: AsyncSession, lesson_key: str) -> bool:
    if user is None or user.id is None:
        return False
    required_key = ''
    for index, lesson in enumerate(lessons):
        if lesson['title'] == lesson_key:
            required_key = lessons[index - 1].get('title')

    result = await session.execute(
        select(LessonResult.id)
        .where(
            LessonResult.user_id == user.id,
            LessonResult.lesson_key == required_key,
            LessonResult.compleat.is_(True),
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None