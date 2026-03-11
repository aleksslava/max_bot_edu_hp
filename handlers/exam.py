from pprint import pprint

from maxapi import Router, F
from maxapi.context import MemoryContext
from maxapi.enums.upload_type import UploadType
from maxapi.filters.command import Command
from maxapi.types import BotStarted, MessageCreated, CallbackButton, MessageCallback, InputMedia, LinkButton
from maxapi.types.attachments.upload import AttachmentUpload, AttachmentPayload
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from service.questions_lexicon import welcome_message, exam_lesson, exam_questions, edu_compleat_text, \
    urls_to_messanger, edu_not_compleat
from fsm.exam import Exam
from fsm.main_states import Main_menu
from services.utils import build_question_inline_keyboard, proceed_radio_button, build_question_multiply_keyboard, \
    proceed_multiply_button, get_question_text, proceed_result, main_menu_button, build_exam_keyboard, proceed_exam, \
    result_exam
from service.questions_lexicon import questions_7 as lesson
from config.config import BASE_DIR

exam_router = Router()

@exam_router.message_callback(F.callback.payload == 'exam')
async def vebinar_1(event: MessageCallback, context: MemoryContext, video_tokens: dict[str, str]):
    await context.set_state(Exam.vebinar)
    if event.message is None:
        return

    kb = InlineKeyboardBuilder()
    kb.add(
        CallbackButton(
            text='Вперед',
            payload='next'),
        )

    token = video_tokens.get('hp_exam')
    attachment = AttachmentUpload(
        type=UploadType.VIDEO,
        payload=AttachmentPayload(token=token),
    )


    await event.message.edit(
        text='Видеозапись экзамена',
        attachments=[
            attachment,
            kb.as_markup()],
    )


#  Вход в первый вопрос
@exam_router.message_callback(F.callback.payload == 'next', Exam.vebinar)
async def question_1(event: MessageCallback, context: MemoryContext, image_tokens: dict[str, str],
                     video_tokens: dict[str, str]):
    question_number = 1
    await context.set_state(Exam.question_1)
    token = image_tokens.get('q1')
    attachment = AttachmentUpload(
        type=UploadType.IMAGE,
        payload=AttachmentPayload(token=token),
    )

    token = video_tokens.get('hp_exam')
    video_attachment = AttachmentUpload(
        type=UploadType.VIDEO,
        payload=AttachmentPayload(token=token),
    )

    await event.message.edit()

    kb: InlineKeyboardBuilder = build_exam_keyboard(question_data=exam_lesson, question_number='q1')
    await event.message.edit(text=event.message.body.text, attachments=[video_attachment])
    await event.message.answer(text=exam_questions.get('1'),
                               attachments=[kb.as_markup(), attachment])

#  обработка вопроса 1
@exam_router.message_callback(F.callback.payload != 'next', Exam.question_1)
async def question_1_proceed(event: MessageCallback, context: MemoryContext, image_tokens: dict[str, str]):
    question_number = 1
    choose = event.callback.payload
    token = image_tokens.get('q1')
    attachment = AttachmentUpload(
        type=UploadType.IMAGE,
        payload=AttachmentPayload(token=token),
    )


    now_choose = await context.get_data()
    now_choose = now_choose.get('results', {}).get(f'exam_{question_number}', None)
    result_question = proceed_exam(question_data=exam_lesson, question_number='q1', now_choose=choose,
                                   choose_payload=now_choose)

    context_data = await context.get_data()
    results = context_data.setdefault('results', {})
    results[f'exam_{question_number}'] = result_question

    kb: InlineKeyboardBuilder = build_exam_keyboard(question_data=exam_lesson, question_number='q1', choose_payload=result_question)

    await event.message.edit(text=exam_questions.get('1'),
                               attachments=[kb.as_markup(), attachment])


#  Вход во второй вопрос
@exam_router.message_callback(F.callback.payload == 'next', Exam.question_1)
async def question_2(event: MessageCallback, context: MemoryContext, image_tokens: dict[str, str]):
    question_number = 2
    await context.set_state(Exam.question_2)

    token = image_tokens.get('q2')
    attachment = AttachmentUpload(
        type=UploadType.IMAGE,
        payload=AttachmentPayload(token=token),
    )

    kb: InlineKeyboardBuilder = build_exam_keyboard(question_data=exam_lesson, question_number='q2')
    await event.message.edit(text=exam_questions.get('2'),
                               attachments=[kb.as_markup(), attachment])

#  обработка вопроса 2
@exam_router.message_callback(F.callback.payload != 'next', Exam.question_2)
async def question_2_proceed(event: MessageCallback, context: MemoryContext, image_tokens: dict[str, str]):
    question_number = 2
    choose = event.callback.payload
    token = image_tokens.get('q2')
    attachment = AttachmentUpload(
        type=UploadType.IMAGE,
        payload=AttachmentPayload(token=token),
    )


    now_choose = await context.get_data()
    now_choose = now_choose.get('results', {}).get(f'exam_{question_number}', None)
    result_question = proceed_exam(question_data=exam_lesson, question_number='q2', now_choose=choose,
                                   choose_payload=now_choose)

    context_data = await context.get_data()
    results = context_data.setdefault('results', {})
    results[f'exam_{question_number}'] = result_question

    kb: InlineKeyboardBuilder = build_exam_keyboard(question_data=exam_lesson, question_number='q2', choose_payload=result_question)

    await event.message.edit(text=exam_questions.get('2'),
                               attachments=[kb.as_markup(), attachment])

#  Вход в третий вопрос
@exam_router.message_callback(F.callback.payload == 'next', Exam.question_2)
async def question_3(event: MessageCallback, context: MemoryContext, image_tokens: dict[str, str]):
    question_number = 3
    await context.set_state(Exam.question_3)

    token = image_tokens.get('q3')
    attachment = AttachmentUpload(
        type=UploadType.IMAGE,
        payload=AttachmentPayload(token=token),
    )

    kb: InlineKeyboardBuilder = build_exam_keyboard(question_data=exam_lesson, question_number='q3')
    await event.message.edit(text=exam_questions.get('3'),
                               attachments=[kb.as_markup(), attachment])

#  обработка вопроса 3
@exam_router.message_callback(F.callback.payload != 'next', Exam.question_3)
async def question_3_proceed(event: MessageCallback, context: MemoryContext, image_tokens: dict[str, str]):
    question_number = 3
    choose = event.callback.payload

    token = image_tokens.get('q3')
    attachment = AttachmentUpload(
        type=UploadType.IMAGE,
        payload=AttachmentPayload(token=token),
    )

    now_choose = await context.get_data()
    now_choose = now_choose.get('results', {}).get(f'exam_{question_number}', None)
    result_question = proceed_exam(question_data=exam_lesson, question_number='q3', now_choose=choose,
                                   choose_payload=now_choose)

    context_data = await context.get_data()
    results = context_data.setdefault('results', {})
    results[f'exam_{question_number}'] = result_question

    kb: InlineKeyboardBuilder = build_exam_keyboard(question_data=exam_lesson, question_number='q3', choose_payload=result_question)

    await event.message.edit(text=exam_questions.get('3'),
                               attachments=[kb.as_markup(), attachment])

#  Вход в четвертый вопрос
@exam_router.message_callback(F.callback.payload == 'next', Exam.question_3)
async def question_4(event: MessageCallback, context: MemoryContext, image_tokens: dict[str, str]):
    question_number = 4
    await context.set_state(Exam.question_4)

    token = image_tokens.get('q4')
    attachment = AttachmentUpload(
        type=UploadType.IMAGE,
        payload=AttachmentPayload(token=token),
    )

    kb: InlineKeyboardBuilder = build_exam_keyboard(question_data=exam_lesson, question_number='q4')
    await event.message.edit(text=exam_questions.get('4'),
                             attachments=[kb.as_markup(), attachment])

#  обработка вопроса 4
@exam_router.message_callback(F.callback.payload != 'next', Exam.question_4)
async def question_4_proceed(event: MessageCallback, context: MemoryContext, image_tokens: dict[str, str]):
    question_number = 4
    choose = event.callback.payload

    token = image_tokens.get('q4')
    attachment = AttachmentUpload(
        type=UploadType.IMAGE,
        payload=AttachmentPayload(token=token),
    )

    now_choose = await context.get_data()
    now_choose = now_choose.get('results', {}).get(f'exam_{question_number}', None)
    result_question = proceed_exam(question_data=exam_lesson, question_number='q4', now_choose=choose,
                                   choose_payload=now_choose)

    context_data = await context.get_data()
    results = context_data.setdefault('results', {})
    results[f'exam_{question_number}'] = result_question

    kb: InlineKeyboardBuilder = build_exam_keyboard(question_data=exam_lesson, question_number='q4',
                                                    choose_payload=result_question)

    await event.message.edit(text=exam_questions.get('4'),
                             attachments=[kb.as_markup(), attachment])

@exam_router.message_callback(F.callback.payload == 'next', Exam.question_4)
async def exam_result(event: MessageCallback, context: MemoryContext, image_tokens: dict[str, str]):
    await context.set_state(Exam.compleate)
    exam_results = await context.get_data()
    exam_results = exam_results.get('results', {})
    result_check = result_exam(results=exam_results,
                               trouth_results=exam_lesson
                               )
    await event.message.edit(text=result_check.get('title'),
                             attachments=[])
    kb = InlineKeyboardBuilder()
    kb.row(LinkButton(url=urls_to_messanger.get('tg'), text='🔵 Сообщить в телеграмм'))
    kb.row(LinkButton(url=urls_to_messanger.get('whatsapp'), text="🟢 Сообщить в whats'app"))
    kb.row(LinkButton(url=urls_to_messanger.get('max'), text='🟣 Сообщить в MAX'))
    kb.row(CallbackButton(text='В главное меню', payload='main_menu'))

    await context.clear()
    await context.set_state(Main_menu.menu)

    if result_check.get('results'):
        token = image_tokens.get('exam')
        attachment = AttachmentUpload(
            type=UploadType.IMAGE,
            payload=AttachmentPayload(token=token),
        )

        await event.message.answer(text=edu_compleat_text,
                                   attachments=[kb.as_markup(),attachment])
    else:
        await event.message.answer(text=edu_not_compleat,
                                   attachments=[kb.as_markup()])