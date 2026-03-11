import logging
import datetime

from maxapi import Router, F
from maxapi.context import MemoryContext
from maxapi.enums.upload_type import UploadType
from maxapi.filters.command import Command
from maxapi.types import BotStarted, MessageCreated, CallbackButton, MessageCallback, InputMedia
from maxapi.types.attachments.upload import AttachmentUpload, AttachmentPayload
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from amo_api.amo_api import AmoCRMWrapper
from db.models import User, HpLessonResult as LessonResult
from service.questions_lexicon import welcome_message
from fsm.lesson_1 import Lesson_1
from fsm.main_states import Main_menu
from service.service import check_push_to_new_status
from services.utils import build_question_inline_keyboard, proceed_radio_button, build_question_multiply_keyboard, \
    proceed_multiply_button, get_question_text, proceed_result, main_menu_button
from service.questions_lexicon import questions_1 as lesson
from config.config import BASE_DIR

logger = logging.getLogger(__name__)

lesson_1 = Router()
lesson_number = '1'


@lesson_1.message_callback(F.callback.payload == 'lesson_1')
async def vebinar_1(event: MessageCallback, context: MemoryContext, video_tokens: dict[str, str],
                    session: AsyncSession):
    max_id = event.callback.user.user_id
    result = await session.execute(select(User).where(User.max_user_id == max_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise ValueError(f'Пользователь не найден при переходе в урок 1, tg_id: {max_id}')
    if user.start_edu is None:
        user.start_edu = datetime.datetime.utcnow()
    lesson = LessonResult(
        user_id=user.id,
        lesson_key='lesson_1',
    )
    session.add(lesson)
    await session.commit()
    await session.refresh(lesson)
    logger.info(f'Запущен первый урок пользователем tg_ID:{max_id}. ID урока в БД - {lesson.id}')
    await context.set_state(Lesson_1.vebinar)
    context_data = await context.get_data()
    results = context_data.setdefault('results', {})
    results['lesson_id'] = lesson.id

    if event.message is None:
        return

    kb = InlineKeyboardBuilder()
    kb.add(
        CallbackButton(
            text='Вперед',
            payload='next'),
        )
    token = video_tokens.get('lesson_1')
    attachment = AttachmentUpload(
        type=UploadType.VIDEO,
        payload=AttachmentPayload(token=token),
    )

    await event.message.edit(
        text='Видеозапись урока 1',
        attachments=[
            attachment,
            kb.as_markup()],
    )
#  Вход в первый вопрос
@lesson_1.message_callback(F.callback.payload == 'next', Lesson_1.vebinar)
async def question_1(event: MessageCallback, context: MemoryContext, video_tokens: dict[str, str]):
    question_number = 1
    await context.set_state(Lesson_1.question_1)

    token = video_tokens.get('lesson_1')
    attachment = AttachmentUpload(
        type=UploadType.VIDEO,
        payload=AttachmentPayload(token=token),
    )

    kb: InlineKeyboardBuilder = build_question_inline_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'))
    await event.message.edit(text=event.message.body.text, attachments=[attachment])
    await event.message.answer(text=get_question_text(questions=lesson, lesson_number=lesson_number, question_number=question_number),
                               attachments=[kb.as_markup()])

# Обработка первого вопроса
@lesson_1.message_callback(F.callback.payload != 'next' , Lesson_1.question_1)
async def proceed_question_1(event: MessageCallback, context: MemoryContext):
    question_number = 1
    choose = event.callback.payload
    result_question = proceed_radio_button(question_data=lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
                                           choose_payload=choose)
    context_data = await context.get_data()
    results = context_data.setdefault('results', {})
    results[f'question_{question_number}'] = result_question

    kb: InlineKeyboardBuilder = build_question_inline_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'), choose_payload=choose)
    await event.message.edit(text=get_question_text(questions=lesson, lesson_number=lesson_number, question_number=question_number),
                             attachments=[kb.as_markup()])


#  Вход во второй вопрос
@lesson_1.message_callback(F.callback.payload == 'next', Lesson_1.question_1)
async def question_2(event: MessageCallback, context: MemoryContext):
    question_number = 2
    await context.set_state(Lesson_1.question_2)

    kb: InlineKeyboardBuilder = build_question_inline_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'))
    await event.message.edit(text=get_question_text(questions=lesson, lesson_number=lesson_number, question_number=question_number),
                               attachments=[kb.as_markup()])


# Обработка второго вопроса
@lesson_1.message_callback(F.callback.payload != 'next', Lesson_1.question_2)
async def proceed_question_2(event: MessageCallback, context: MemoryContext):
    question_number = 2
    choose = event.callback.payload
    result_question = proceed_radio_button(question_data=lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
                                           choose_payload=choose)

    context_data = await context.get_data()
    results = context_data.setdefault('results', {})
    results[f'question_{question_number}'] = result_question

    kb: InlineKeyboardBuilder = build_question_inline_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
                                                               choose_payload=choose)
    await event.message.edit(text=get_question_text(questions=lesson, lesson_number=lesson_number, question_number=question_number),
                             attachments=[kb.as_markup()])


#  Вход во третий вопрос
@lesson_1.message_callback(F.callback.payload == 'next', Lesson_1.question_2)
async def question_3(event: MessageCallback, context: MemoryContext):
    question_number = 3
    await context.set_state(Lesson_1.question_3)

    kb: InlineKeyboardBuilder = build_question_inline_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'))
    await event.message.edit(text=get_question_text(questions=lesson, lesson_number=lesson_number, question_number=question_number),
                               attachments=[kb.as_markup()])


# Обработка третьего вопроса
@lesson_1.message_callback(F.callback.payload != 'next', Lesson_1.question_3)
async def proceed_question_3(event: MessageCallback, context: MemoryContext):
    question_number = 3
    choose = event.callback.payload
    result_question = proceed_radio_button(question_data=lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
                                           choose_payload=choose)

    context_data = await context.get_data()
    results = context_data.setdefault('results', {})
    results[f'question_{question_number}'] = result_question

    kb: InlineKeyboardBuilder = build_question_inline_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
                                                               choose_payload=choose)
    await event.message.edit(text=get_question_text(questions=lesson, lesson_number=lesson_number, question_number=question_number),
                             attachments=[kb.as_markup()])


#  Вход во четвертый вопрос
@lesson_1.message_callback(F.callback.payload == 'next', Lesson_1.question_3)
async def question_4(event: MessageCallback, context: MemoryContext):
    question_number = 4
    await context.set_state(Lesson_1.question_4)

    kb: InlineKeyboardBuilder = build_question_inline_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'))
    await event.message.edit(text=get_question_text(questions=lesson, lesson_number=lesson_number, question_number=question_number),
                               attachments=[kb.as_markup()])


# Обработка четвертого вопроса
@lesson_1.message_callback(F.callback.payload != 'next', Lesson_1.question_4)
async def proceed_question_4(event: MessageCallback, context: MemoryContext):
    question_number = 4
    choose = event.callback.payload
    result_question = proceed_radio_button(question_data=lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
                                           choose_payload=choose)

    context_data = await context.get_data()
    results = context_data.setdefault('results', {})
    results[f'question_{question_number}'] = result_question

    kb: InlineKeyboardBuilder = build_question_inline_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
                                                               choose_payload=choose)
    await event.message.edit(text=get_question_text(questions=lesson, lesson_number=lesson_number, question_number=question_number),
                             attachments=[kb.as_markup()])


#  Вход во пятый вопрос
@lesson_1.message_callback(F.callback.payload == 'next', Lesson_1.question_4)
async def question_5(event: MessageCallback, context: MemoryContext):
    question_number = 5
    await context.set_state(Lesson_1.question_5)

    kb: InlineKeyboardBuilder = build_question_multiply_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'))
    await event.message.edit(text=get_question_text(questions=lesson, lesson_number=lesson_number, question_number=question_number,
                                                    is_radio=False),
                               attachments=[kb.as_markup()])


# Обработка пятого вопроса
@lesson_1.message_callback(F.callback.payload != 'next', Lesson_1.question_5)
async def proceed_question_5(event: MessageCallback, context: MemoryContext):
    question_number = 5
    choose = event.callback.payload
    now_choose = await context.get_data()
    now_choose = now_choose.get('results', {}).get(f'question_{question_number}', None)
    result_question = proceed_multiply_button(question_data=lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
                                              choose_payload=choose,
                                              now_choose=now_choose)

    context_data = await context.get_data()
    results = context_data.setdefault('results', {})
    results[f'question_{question_number}'] = result_question

    kb: InlineKeyboardBuilder = build_question_multiply_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
                                                               choose_payload=result_question)
    await event.message.edit(text=get_question_text(questions=lesson, lesson_number=lesson_number, question_number=question_number,
                                                    is_radio=False),
                             attachments=[kb.as_markup()])

#  Вход в шестой вопрос
@lesson_1.message_callback(F.callback.payload == 'next', Lesson_1.question_5)
async def question_6(event: MessageCallback, context: MemoryContext):
    question_number = 6
    await context.set_state(Lesson_1.question_6)

    kb: InlineKeyboardBuilder = build_question_inline_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'), text_on_button=False)
    await event.message.edit(text=get_question_text(questions=lesson, with_answers=True, lesson_number=lesson_number, question_number=question_number),
                               attachments=[kb.as_markup()])


# Обработка шестого вопроса
@lesson_1.message_callback(F.callback.payload != 'next', Lesson_1.question_6)
async def proceed_question_6(event: MessageCallback, context: MemoryContext):
    question_number = 6
    choose = event.callback.payload
    result_question = proceed_radio_button(question_data=lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
                                           choose_payload=choose)

    context_data = await context.get_data()
    results = context_data.setdefault('results', {})
    results[f'question_{question_number}'] = result_question

    kb: InlineKeyboardBuilder = build_question_inline_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
                                                               choose_payload=choose,
                                                               text_on_button=False)
    await event.message.edit(text=get_question_text(questions=lesson, with_answers=True, lesson_number=lesson_number, question_number=question_number),
                             attachments=[kb.as_markup()])


#  Вход в седьмой вопрос
@lesson_1.message_callback(F.callback.payload == 'next', Lesson_1.question_6)
async def question_7(event: MessageCallback, context: MemoryContext):
    question_number = 7
    await context.set_state(Lesson_1.question_7)

    kb: InlineKeyboardBuilder = build_question_inline_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'), text_on_button=False)
    await event.message.edit(text=get_question_text(questions=lesson, with_answers=True, lesson_number=lesson_number, question_number=question_number),
                               attachments=[kb.as_markup()])


# Обработка седьмого вопроса
@lesson_1.message_callback(F.callback.payload != 'next', Lesson_1.question_7)
async def proceed_question_7(event: MessageCallback, context: MemoryContext):
    question_number = 7
    choose = event.callback.payload
    result_question = proceed_radio_button(question_data=lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
                                           choose_payload=choose)

    context_data = await context.get_data()
    results = context_data.setdefault('results', {})
    results[f'question_{question_number}'] = result_question

    kb: InlineKeyboardBuilder = build_question_inline_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),text_on_button=False,
                                                               choose_payload=choose)
    await event.message.edit(text=get_question_text(questions=lesson, with_answers=True, lesson_number=lesson_number, question_number=question_number),
                             attachments=[kb.as_markup()])


#  Вход в восьмой вопрос
@lesson_1.message_callback(F.callback.payload == 'next', Lesson_1.question_7)
async def question_8(event: MessageCallback, context: MemoryContext):
    question_number = 8
    await context.set_state(Lesson_1.question_8)

    kb: InlineKeyboardBuilder = build_question_inline_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'), text_on_button=False)
    await event.message.edit(text=get_question_text(questions=lesson, with_answers=True, lesson_number=lesson_number, question_number=question_number),
                               attachments=[kb.as_markup()])


# Обработка восьмого вопроса
@lesson_1.message_callback(F.callback.payload != 'next', Lesson_1.question_8)
async def proceed_question_8(event: MessageCallback, context: MemoryContext):
    question_number = 8
    choose = event.callback.payload
    result_question = proceed_radio_button(question_data=lesson.get('Lesson_1:question_8'),
                                           choose_payload=choose)

    context_data = await context.get_data()
    results = context_data.setdefault('results', {})
    results[f'question_{question_number}'] = result_question


    kb: InlineKeyboardBuilder = build_question_inline_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'), text_on_button=False,
                                                               choose_payload=choose)
    await event.message.edit(text=get_question_text(questions=lesson, with_answers=True, lesson_number=lesson_number, question_number=question_number),
                             attachments=[kb.as_markup()])

#  Вход в девятый вопрос
@lesson_1.message_callback(F.callback.payload == 'next', Lesson_1.question_8)
async def question_9(event: MessageCallback, context: MemoryContext):
    question_number = 9
    await context.set_state(Lesson_1.question_9)

    kb: InlineKeyboardBuilder = build_question_inline_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'))
    await event.message.edit(text=get_question_text(questions=lesson, lesson_number=lesson_number, question_number=question_number),
                               attachments=[kb.as_markup()])


# Обработка девятого вопроса
@lesson_1.message_callback(F.callback.payload != 'next', Lesson_1.question_9)
async def proceed_question_9(event: MessageCallback, context: MemoryContext):
    question_number = 9
    choose = event.callback.payload
    result_question = proceed_radio_button(question_data=lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
                                           choose_payload=choose)

    context_data = await context.get_data()
    results = context_data.setdefault('results', {})
    results[f'question_{question_number}'] = result_question

    kb: InlineKeyboardBuilder = build_question_inline_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
                                                               choose_payload=choose)
    await event.message.edit(text=get_question_text(questions=lesson, lesson_number=lesson_number, question_number=question_number),
                             attachments=[kb.as_markup()])

#  Вход в десятый вопрос
@lesson_1.message_callback(F.callback.payload == 'next', Lesson_1.question_9)
async def question_10(event: MessageCallback, context: MemoryContext):
    question_number = 10
    await context.set_state(Lesson_1.question_10)

    kb: InlineKeyboardBuilder = build_question_inline_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'))
    await event.message.edit(text=get_question_text(questions=lesson, lesson_number=lesson_number, question_number=question_number),
                               attachments=[kb.as_markup()])


# Обработка десятого вопроса
@lesson_1.message_callback(F.callback.payload != 'next', Lesson_1.question_10)
async def proceed_question_10(event: MessageCallback, context: MemoryContext):
    question_number = 10
    choose = event.callback.payload
    result_question = proceed_radio_button(question_data=lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
                                           choose_payload=choose)

    context_data = await context.get_data()
    results = context_data.setdefault('results', {})
    results[f'question_{question_number}'] = result_question


    kb: InlineKeyboardBuilder = build_question_inline_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
                                                               choose_payload=choose)
    await event.message.edit(text=get_question_text(questions=lesson, lesson_number=lesson_number, question_number=question_number),
                             attachments=[kb.as_markup()])

@lesson_1.message_callback(F.callback.payload == 'next', Lesson_1.question_10)
async def result(event: MessageCallback, context: MemoryContext, session: AsyncSession,
                 amo_api: AmoCRMWrapper, amo_fields: dict):
    max_id = event.callback.user.user_id
    result = await context.get_data()
    lesson_id = result.get('lesson_id')
    pipelines = amo_fields.get('pipelines')
    status_fields = amo_fields.get('statuses')
    checking_result = proceed_result(questions=lesson, results=result)
    score = checking_result.get('score', 0)
    title = checking_result.get('title', '')
    compleat_lesson = checking_result.get('compleat_lesson', False)
    if compleat_lesson:
        lesson_obj = None
        user = None
        if lesson_id is not None:
            lesson_result = await session.execute(
                select(LessonResult)
                .options(selectinload(LessonResult.user))
                .where(LessonResult.id == lesson_id)
            )
            lesson_obj = lesson_result.scalar_one_or_none()
            lesson_obj.score = score
            lesson_obj.compleat = compleat_lesson
            lesson_obj.completed_at = datetime.datetime.utcnow()
            if lesson is not None:
                user = lesson.user

            await session.commit()
            await session.refresh(lesson)
            await session.refresh(user)

            # Отправляем примечание в сделку с обучением
            amo_api.add_new_note_to_lead(lead_id=user.amo_deal_id, text=f'Результаты урока №1: {result}')

            user_lead_id = user.amo_deal_id
            status_id_in_amo = amo_api.get_lead_by_id(lead_id=user_lead_id).get('status_id')
            push_to_new_status = await check_push_to_new_status(lesson_key='compleat_lesson_1',
                                                                lead_status=status_id_in_amo)

            # Перемещаем сделку далее по воронке обучения, если успешно. В сделку записываем примечание с результатами
            if compleat_lesson and push_to_new_status:
                amo_api.push_lead_to_status(pipeline_id=pipelines.get('hite_pro_education'),
                                            status_id=status_fields.get('compleat_lesson_1'),
                                            lead_id=str(user.amo_deal_id))
    kb: InlineKeyboardBuilder = main_menu_button()
    await context.clear()
    await context.set_state(Main_menu.menu)
    await event.message.edit(text=str(title),
                             attachments=[kb.as_markup()])