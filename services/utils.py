from email.policy import default
from pprint import pprint
from typing import Any
import re

from maxapi.enums.intent import Intent
from maxapi.types import CallbackButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from db import User
from service.service import get_lessons_buttons


def pad_right(s: str, width: int) -> str:
    # обычные пробелы иногда “съедаются”/выглядят странно в кнопках,
    # поэтому лучше NBSP (неразрывный пробел)
    return s + ("\u2800" * 50)

def build_question_inline_keyboard(question_data: dict[str, Any], choose_payload: str = '',
                                   text_on_button: bool = True,
                                   ) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    answers = question_data.get("answers", [])
    choose = '🟢 '
    not_choose = '⚪ '
    max_answer_len = len(max(map(lambda x: '🟢 ' + x[0], answers), key=len))
    for answer in answers:
        if len(answer) < 2:
            continue

        answer_text = pad_right(answer[0], max_answer_len)
        answer_id = answer[1]

        builder.add(
            CallbackButton(
                text=choose + [f'Вариант {answer_id}' ,str(answer_text)][text_on_button] if choose_payload == str(answer_id) else not_choose + [f'Вариант {answer_id}' ,str(answer_text)][text_on_button],
                payload=str(answer_id),
            )
        )

    builder.add(
        CallbackButton(text="Вперед", payload="next"),
    )

    rows_pattern = [1] * len(answers) + [2]
    builder.adjust(*rows_pattern)
    return builder

def build_question_multiply_keyboard(question_data: dict[str, Any], choose_payload: dict=None,
                                     text_on_button: bool = True,
                                     ) -> InlineKeyboardBuilder:
    if choose_payload is None:
        choose_payload = {}
    builder = InlineKeyboardBuilder()
    answers = question_data.get("answers", [])
    choose = '✅ '
    not_choose = '◻️ '
    max_answer_len = len(max(map(lambda x: '🟢 ' + x[0], answers), key=len))

    for answer in answers:
        if len(answer) < 2:
            continue

        answer_text = pad_right(answer[0], max_answer_len)
        answer_id = answer[1]

        builder.add(
            CallbackButton(
                text=choose + [f'Вариант {answer_id}' ,str(answer_text)][text_on_button] if choose_payload.get(str(answer_id), False) else not_choose + [f'Вариант {answer_id}' ,str(answer_text)][text_on_button],
                payload=str(answer_id),
            )
        )


    builder.add(
        CallbackButton(text="Вперед", payload="next"),
    )

    rows_pattern = [1] * len(answers) + [2]
    builder.adjust(*rows_pattern)
    return builder

def proceed_exam(question_data: dict[str, Any], question_number: str, choose_payload: dict=None, now_choose: str|None=None) -> dict:
    if choose_payload is None or  not choose_payload:
        choose_payload = {key: 0 for key in question_data.get(question_number).keys()}

    if now_choose is not None:
        key, method = now_choose.split('_')
        if method == 'increment':
            choose_payload[key] = int(choose_payload.get(key, 0)) + 1
        else:
            choose_payload[key] = int(choose_payload.get(key, 0)) - 1 if int(choose_payload.get(key, 0)) != 0 else 0

    return choose_payload

def build_exam_keyboard(question_data: dict[str, Any], question_number: str, choose_payload: dict=None) -> InlineKeyboardBuilder:
    if choose_payload is None:
        choose_payload = {key: 0 for key in question_data.get(question_number).keys()}

    builder = InlineKeyboardBuilder()

    row_values = {}
    for key, value in choose_payload.items():
        if len(row_values) < 2:
            row_values[key] = value

        if len(row_values) == 2:
            buttons = []
            buttons_floor = []
            for row_key, row_value in row_values.items():
                if len(row_key) > 10:
                    builder.row(
                        CallbackButton(
                            text=f'{row_key}: {row_value}',
                            payload=None
                        )
                    )
                    builder.row(
                        CallbackButton(
                            text='-',
                            payload=f'{row_key}_decrement'
                        ),
                        CallbackButton(
                            text='+',
                            payload=f'{row_key}_increment'
                        )
                    )
                    continue
                buttons.append(CallbackButton(
                    text=f'{row_key}: {row_value}',
                    payload=None
                ))
                buttons_floor.append(CallbackButton(
                    text='-',
                    payload=f'{row_key}_decrement'
                ))
                buttons_floor.append(CallbackButton(
                    text='+',
                    payload=f'{row_key}_increment'
                ))
            builder.row(*buttons)
            builder.row(*buttons_floor)
            row_values.clear()
    if row_values:
        for key, value in row_values.items():
            builder.row(
                CallbackButton(
                    text=f'{key}: {value}',
                    payload=None
                )
            )
            builder.row(
                CallbackButton(
                    text='-',
                    payload=f'{key}_decrement'
                ),
                CallbackButton(
                    text='+',
                    payload=f'{key}_increment'
                )
            )


    builder.row(
        CallbackButton(
            text='Далее',
            payload='next'
        )
    )

    return builder


def main_menu_button() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.add(
        CallbackButton(text="В главное меню", payload="main_menu"),
    )
    return builder

def proceed_radio_button(question_data: dict[str, Any], choose_payload: str = '') -> dict[str, Any]:
    answers = question_data.get("answers", [])
    question_result = {}

    for answer in answers:
        choose = True if choose_payload == str(answer[1]) else False
        question_result[answer[1]] = choose

    return question_result

def proceed_multiply_button(question_data: dict[str, Any], choose_payload: str = '', now_choose=None) -> dict[str, Any]:
    if now_choose is None:
        now_choose = {}
    answers = question_data.get("answers", [])
    question_result = {}

    for answer in answers:
        if choose_payload == str(answer[1]):
            if now_choose.get(str(answer[1]), False):
                question_result[answer[1]] = False
            else:
                question_result[answer[1]] = True
        else:
            question_result[answer[1]] = now_choose.get(str(answer[1]), False)
        # choose = True if choose_payload == str(answer[1]) or now_choose.get(str(answer[1]), False) else False
        # question_result[answer[1]] = choose

    return question_result

def get_question_text(questions: dict[str, Any],
                      with_answers: bool = False,
                      lesson_number: str = '1',
                      question_number: int = 1,
                      is_radio=True) -> str:
    questions_len = len(questions)
    header = f'<b>Вопрос {question_number} из {questions_len}</b>\n\n'
    title = questions.get(f'Lesson_{lesson_number}:question_{question_number}').get("title")
    result = header + title

    if is_radio:
        result += '\n(Только один правильный ответ)'
    else:
        result += '\n(Один или несколько правильных ответов)'

    if with_answers:
        result += '\n\n<b>Варианты ответов:</b>'
        answers = questions.get(f'Lesson_{lesson_number}:question_{question_number}').get("answers", [])
        for answer in answers:
            result += f'\n\n{str(answer[1])})  {str(answer[0])}'


    return result


def proceed_result(questions: dict[dict, Any],
                   results: dict[str, Any],
                   ):

    good_answers = 0
    questions_len = len(questions)
    prepared_questions = {}
    for value in questions.values():
        question_number = value.get('key')[1:]
        answers: list[tuple] = value.get("answers", [])
        prepared_questions[f'question_{question_number}'] = {answer[1]: answer[2] for answer in answers}

    results = results.get('results', {})

    result_text = '<b>Результаты проверки:</b>\n\n'

    for key in prepared_questions.keys():
        answer = results.get(key, {})
        if answer:
            if answer == prepared_questions.get(key):
                good_answers += 1
                key: str = key.replace('question_', 'Вопрос #')
                result_text += f'✅ {key} - Верно\n'
                continue
            else:
                key: str = key.replace('question_', 'Вопрос #')
                result_text += f'❌ {key} - Не верно\n'
        else:
            key: str = key.replace('question_', 'Вопрос #')
            result_text += f'❓ {key} - Пропущен\n'

    score = int(good_answers / questions_len * 100)
    result_text += f'Вы  набрали {score} баллов из 100.\n\n'
    compleat_lesson = True if score >= 80 else False
    result_text += 'Поздравляем с успешным прохождением урока!' if compleat_lesson else 'К сожалению, урок не пройден'
    return {
        'good_answers_count': good_answers,
        'score': score,
        'title': result_text,
        'compleat_lesson': compleat_lesson,
    }


def result_exam(results: dict[str, Any],
                 trouth_results: dict[str, Any],) -> dict[str, Any]:
    res = []
    title = 'Результаты экзамена\n\n'
    for question_number in range(1, 5):
        result = results.get(f'exam_{question_number}')
        trough_result = trouth_results.get(f'q{question_number}')
        res.append(result == trough_result)
        if result == trough_result:
            title += f'✅ Вопрос №{question_number}\n'
        else:
            title += f'❌ Вопрос №{question_number}\n'

    if all(res):
        title += '<b>Экзамен пройден!</b>🎉'
    else:
        title += '<b>Экзамен не пройден</b>🥹'

    return {
        'title': title,
        'results': all(res),
    }



def extract_phone_from_vcf(vcf: str) -> str | None:
    m = re.search(r"^TEL(?:;[^:]*)?:(.+)$", vcf, flags=re.MULTILINE | re.IGNORECASE)
    if not m:
        return None
    raw = m.group(1).strip()  # например: 79878217816 или tel:+7...
    return re.sub(r"[^\d+]", "", raw)



async def get_main_menu(user: User, session: AsyncSession) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()

    lesson_access = await get_lessons_buttons(user, session)

    builder.add(
        CallbackButton(
            text=lesson_access['lesson_1'],
            payload='lesson_1'
        ),
        CallbackButton(
            text=lesson_access['lesson_2'],
            payload='lesson_2',
        ),
        CallbackButton(
            text=lesson_access['lesson_3'],
            payload='lesson_3',
        ),
        CallbackButton(
            text=lesson_access['lesson_4'],
            payload='lesson_4',
        ),
        CallbackButton(
            text=lesson_access['lesson_5'],
            payload='lesson_5',
        ),
        CallbackButton(
            text=lesson_access['lesson_6'],
            payload='lesson_6',
        ),
        CallbackButton(
            text=lesson_access['lesson_7'],
            payload='lesson_7',
        ),
        CallbackButton(
            text=lesson_access['exam'],
            payload='exam',
        ),
        CallbackButton(
            text='📖 Статистика обучения',
            payload='stat',
        )
    )
    if lesson_access['is_admin']:
        builder.add(CallbackButton(text='Кабинет администратора', payload='admin_menu'))
    builder.adjust(1)

    return builder