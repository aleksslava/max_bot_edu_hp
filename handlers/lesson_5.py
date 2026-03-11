from pprint import pprint

from maxapi import Router, F
from maxapi.context import MemoryContext
from maxapi.enums.upload_type import UploadType
from maxapi.filters.command import Command
from maxapi.types import BotStarted, MessageCreated, CallbackButton, MessageCallback, InputMedia
from maxapi.types.attachments.upload import AttachmentUpload, AttachmentPayload
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from service.questions_lexicon import welcome_message
from fsm.lesson_5 import Lesson_5
from fsm.main_states import Main_menu
from services.utils import build_question_inline_keyboard, proceed_radio_button, build_question_multiply_keyboard, \
    proceed_multiply_button, get_question_text, proceed_result, main_menu_button
from service.questions_lexicon import questions_5 as lesson
from config.config import BASE_DIR


lesson_5 = Router()
lesson_number = '5'


@lesson_5.message_callback(F.callback.payload == 'lesson_5')
async def vebinar_1(event: MessageCallback, context: MemoryContext, video_tokens: dict[str, str]):
    await context.set_state(Lesson_5.vebinar)
    if event.message is None:
        return

    kb = InlineKeyboardBuilder()
    kb.add(
        CallbackButton(
            text='Вперед',
            payload='next'),
        )

    token = video_tokens.get('hp_lesson_5')
    attachment = AttachmentUpload(
        type=UploadType.VIDEO,
        payload=AttachmentPayload(token=token),
    )


    await event.message.edit(
        text='Видеозапись урока 5',
        attachments=[
            attachment,
            kb.as_markup()],
    )
#  Вход в первый вопрос
@lesson_5.message_callback(F.callback.payload == 'next', Lesson_5.vebinar)
async def question_1(event: MessageCallback, context: MemoryContext, video_tokens: dict[str, str]):
    question_number = 1
    await context.set_state(Lesson_5.question_1)

    token = video_tokens.get('hp_lesson_5')
    attachment = AttachmentUpload(
        type=UploadType.VIDEO,
        payload=AttachmentPayload(token=token),
    )


    kb: InlineKeyboardBuilder = build_question_inline_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
                                                               text_on_button=False)
    await event.message.edit(text=event.message.body.text, attachments=[attachment])
    await event.message.answer(text=get_question_text(questions=lesson, lesson_number=lesson_number, question_number=question_number,
                                                      with_answers=True),
                               attachments=[kb.as_markup()])

# Обработка первого вопроса
@lesson_5.message_callback(F.callback.payload != 'next' , Lesson_5.question_1)
async def proceed_question_1(event: MessageCallback, context: MemoryContext):
    question_number = 1
    choose = event.callback.payload
    result_question = proceed_radio_button(question_data=lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
                                           choose_payload=choose)
    context_data = await context.get_data()
    results = context_data.setdefault('results', {})
    results[f'question_{question_number}'] = result_question

    kb: InlineKeyboardBuilder = build_question_inline_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
                                                               text_on_button=False, choose_payload=choose)
    await event.message.edit(text=get_question_text(questions=lesson, lesson_number=lesson_number, question_number=question_number,
                                                    with_answers=True),
                             attachments=[kb.as_markup()])


#  Вход во второй вопрос
@lesson_5.message_callback(F.callback.payload == 'next', Lesson_5.question_1)
async def question_2(event: MessageCallback, context: MemoryContext):
    question_number = 2
    await context.set_state(Lesson_5.question_2)

    kb: InlineKeyboardBuilder = build_question_inline_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'))
    await event.message.edit(text=get_question_text(questions=lesson, lesson_number=lesson_number, question_number=question_number),
                               attachments=[kb.as_markup()])


# Обработка второго вопроса
@lesson_5.message_callback(F.callback.payload != 'next', Lesson_5.question_2)
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
@lesson_5.message_callback(F.callback.payload == 'next', Lesson_5.question_2)
async def question_3(event: MessageCallback, context: MemoryContext):
    question_number = 3
    await context.set_state(Lesson_5.question_3)

    kb: InlineKeyboardBuilder = build_question_inline_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
                                                               text_on_button=False)
    await event.message.edit(text=get_question_text(questions=lesson, lesson_number=lesson_number, question_number=question_number,
                                                    with_answers=True),
                               attachments=[kb.as_markup()])


# Обработка третьего вопроса
@lesson_5.message_callback(F.callback.payload != 'next', Lesson_5.question_3)
async def proceed_question_3(event: MessageCallback, context: MemoryContext):
    question_number = 3
    choose = event.callback.payload
    result_question = proceed_radio_button(question_data=lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
                                           choose_payload=choose)

    context_data = await context.get_data()
    results = context_data.setdefault('results', {})
    results[f'question_{question_number}'] = result_question

    kb: InlineKeyboardBuilder = build_question_inline_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
                                                               choose_payload=choose, text_on_button=False)
    await event.message.edit(text=get_question_text(questions=lesson, lesson_number=lesson_number, question_number=question_number,
                                                    with_answers=True),
                             attachments=[kb.as_markup()])


#  Вход во четвертый вопрос
@lesson_5.message_callback(F.callback.payload == 'next', Lesson_5.question_3)
async def question_4(event: MessageCallback, context: MemoryContext):
    question_number = 4
    await context.set_state(Lesson_5.question_4)

    kb: InlineKeyboardBuilder = build_question_inline_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
                                                               text_on_button=False)
    await event.message.edit(text=get_question_text(questions=lesson, lesson_number=lesson_number, question_number=question_number,
                                                    with_answers=True),
                               attachments=[kb.as_markup()])


# Обработка четвертого вопроса
@lesson_5.message_callback(F.callback.payload != 'next', Lesson_5.question_4)
async def proceed_question_4(event: MessageCallback, context: MemoryContext):
    question_number = 4
    choose = event.callback.payload
    result_question = proceed_radio_button(question_data=lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
                                           choose_payload=choose)

    context_data = await context.get_data()
    results = context_data.setdefault('results', {})
    results[f'question_{question_number}'] = result_question

    kb: InlineKeyboardBuilder = build_question_inline_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
                                                               choose_payload=choose, text_on_button=False)
    await event.message.edit(text=get_question_text(questions=lesson, lesson_number=lesson_number, question_number=question_number,
                                                    with_answers=True),
                             attachments=[kb.as_markup()])


#  Вход во пятый вопрос
@lesson_5.message_callback(F.callback.payload == 'next', Lesson_5.question_4)
async def question_5(event: MessageCallback, context: MemoryContext):
    question_number = 5
    await context.set_state(Lesson_5.question_5)

    kb: InlineKeyboardBuilder = build_question_inline_keyboard(
        lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
        text_on_button=False)
    await event.message.edit(
        text=get_question_text(questions=lesson, lesson_number=lesson_number, question_number=question_number,
                               with_answers=True),
        attachments=[kb.as_markup()])


# Обработка пятого вопроса
@lesson_5.message_callback(F.callback.payload != 'next', Lesson_5.question_5)
async def proceed_question_5(event: MessageCallback, context: MemoryContext):
    question_number = 5
    choose = event.callback.payload
    result_question = proceed_radio_button(
        question_data=lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
        choose_payload=choose)

    context_data = await context.get_data()
    results = context_data.setdefault('results', {})
    results[f'question_{question_number}'] = result_question

    kb: InlineKeyboardBuilder = build_question_inline_keyboard(
        lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
        choose_payload=choose, text_on_button=False)
    await event.message.edit(
        text=get_question_text(questions=lesson, lesson_number=lesson_number, question_number=question_number,
                               with_answers=True),
        attachments=[kb.as_markup()])

#  Вход в шестой вопрос
@lesson_5.message_callback(F.callback.payload == 'next', Lesson_5.question_5)
async def question_6(event: MessageCallback, context: MemoryContext):
    question_number = 6
    await context.set_state(Lesson_5.question_6)

    kb: InlineKeyboardBuilder = build_question_inline_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'), text_on_button=False)
    await event.message.edit(text=get_question_text(questions=lesson, with_answers=True, lesson_number=lesson_number, question_number=question_number),
                               attachments=[kb.as_markup()])


# Обработка шестого вопроса
@lesson_5.message_callback(F.callback.payload != 'next', Lesson_5.question_6)
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
@lesson_5.message_callback(F.callback.payload == 'next', Lesson_5.question_6)
async def question_7(event: MessageCallback, context: MemoryContext):
    question_number = 7
    await context.set_state(Lesson_5.question_7)

    kb: InlineKeyboardBuilder = build_question_inline_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'), text_on_button=False)
    await event.message.edit(text=get_question_text(questions=lesson, with_answers=True, lesson_number=lesson_number, question_number=question_number),
                               attachments=[kb.as_markup()])


# Обработка седьмого вопроса
@lesson_5.message_callback(F.callback.payload != 'next', Lesson_5.question_7)
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
@lesson_5.message_callback(F.callback.payload == 'next', Lesson_5.question_7)
async def question_8(event: MessageCallback, context: MemoryContext):
    question_number = 8
    await context.set_state(Lesson_5.question_8)

    kb: InlineKeyboardBuilder = build_question_inline_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'), text_on_button=False)
    await event.message.edit(text=get_question_text(questions=lesson, with_answers=True, lesson_number=lesson_number, question_number=question_number),
                               attachments=[kb.as_markup()])


# Обработка восьмого вопроса
@lesson_5.message_callback(F.callback.payload != 'next', Lesson_5.question_8)
async def proceed_question_8(event: MessageCallback, context: MemoryContext):
    question_number = 8
    choose = event.callback.payload
    result_question = proceed_radio_button(question_data=lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
                                           choose_payload=choose)

    context_data = await context.get_data()
    results = context_data.setdefault('results', {})
    results[f'question_{question_number}'] = result_question


    kb: InlineKeyboardBuilder = build_question_inline_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'), text_on_button=False,
                                                               choose_payload=choose)
    await event.message.edit(text=get_question_text(questions=lesson, with_answers=True, lesson_number=lesson_number, question_number=question_number),
                             attachments=[kb.as_markup()])

#  Вход в девятый вопрос
@lesson_5.message_callback(F.callback.payload == 'next', Lesson_5.question_8)
async def question_9(event: MessageCallback, context: MemoryContext):
    question_number = 9
    await context.set_state(Lesson_5.question_9)

    kb: InlineKeyboardBuilder = build_question_inline_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
                                                               text_on_button=False)
    await event.message.edit(text=get_question_text(questions=lesson, lesson_number=lesson_number, question_number=question_number,
                                                    with_answers=True),
                               attachments=[kb.as_markup()])


# Обработка девятого вопроса
@lesson_5.message_callback(F.callback.payload != 'next', Lesson_5.question_9)
async def proceed_question_9(event: MessageCallback, context: MemoryContext):
    question_number = 9
    choose = event.callback.payload
    result_question = proceed_radio_button(question_data=lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
                                           choose_payload=choose)

    context_data = await context.get_data()
    results = context_data.setdefault('results', {})
    results[f'question_{question_number}'] = result_question

    kb: InlineKeyboardBuilder = build_question_inline_keyboard(lesson.get(f'Lesson_{lesson_number}:question_{question_number}'),
                                                               choose_payload=choose, text_on_button=False)
    await event.message.edit(text=get_question_text(questions=lesson, lesson_number=lesson_number, question_number=question_number,
                                                    with_answers=True),
                             attachments=[kb.as_markup()])


@lesson_5.message_callback(F.callback.payload == 'next', Lesson_5.question_9)
async def result(event: MessageCallback, context: MemoryContext):
    result = await context.get_data()

    checking_result = proceed_result(questions=lesson, results=result)
    score = checking_result.get('score', 0)
    title = checking_result.get('title', '')
    compleat_lesson = checking_result.get('compleat_lesson', False)
    kb: InlineKeyboardBuilder = main_menu_button()
    await context.clear()
    await context.set_state(Main_menu.menu)
    await event.message.edit(text=str(title),
                             attachments=[kb.as_markup()])