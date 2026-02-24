from maxapi.types.attachments.buttons import CallbackButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from services.runtime_state import RuntimeSession


def _truncate(text: str, size: int = 56) -> str:
    if len(text) <= size:
        return text
    return text[: size - 1].rstrip() + "…"


def build_main_menu_keyboard(
    authorized: bool,
    lessons_text: dict[str, str] | None = None,
    is_admin: bool = False,
) -> list:
    builder = InlineKeyboardBuilder()
    if not authorized:
        builder.row(CallbackButton(text="Авторизация", payload="menu:auth"))
    else:
        lessons_text = lessons_text or {}
        builder.row(CallbackButton(text=lessons_text.get("lesson_1", "Урок 1"), payload="menu:lesson:1"))
        builder.row(CallbackButton(text=lessons_text.get("lesson_2", "Урок 2"), payload="menu:lesson:2"))
        builder.row(CallbackButton(text=lessons_text.get("lesson_3", "Урок 3"), payload="menu:lesson:3"))
        builder.row(CallbackButton(text=lessons_text.get("lesson_4", "Урок 4"), payload="menu:lesson:4"))
        builder.row(CallbackButton(text=lessons_text.get("lesson_5", "Урок 5"), payload="menu:lesson:5"))
        builder.row(CallbackButton(text=lessons_text.get("lesson_6", "Урок 6"), payload="menu:lesson:6"))
        builder.row(CallbackButton(text=lessons_text.get("lesson_7", "Урок 7"), payload="menu:lesson:7"))
        builder.row(CallbackButton(text=lessons_text.get("exam", "Экзамен"), payload="menu:exam"))
        builder.row(CallbackButton(text="Статистика обучения", payload="menu:stats"))
        builder.row(CallbackButton(text="Повторная авторизация", payload="menu:auth"))

    if is_admin:
        builder.row(CallbackButton(text="Админ-меню", payload="menu:admin"))

    return [builder.as_markup()]


def build_admin_keyboard() -> list:
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="Результаты пользователей", payload="admin:stats"))
    builder.row(CallbackButton(text="Экспорт XLSX", payload="admin:export"))
    builder.row(CallbackButton(text="Как выдать/удалить админа", payload="admin:help"))
    builder.row(CallbackButton(text="В главное меню", payload="menu:open"))
    return [builder.as_markup()]


def build_lesson_question_keyboard(
    session_data: RuntimeSession,
    question_answers: list[tuple[str, str, bool]],
) -> list:
    builder = InlineKeyboardBuilder()
    selected = session_data.draft_selection
    for idx, answer in enumerate(question_answers, start=1):
        label = f"{'✅ ' if idx in selected else ''}{idx}. {_truncate(answer[0])}"
        builder.row(CallbackButton(text=label, payload=f"lesson:pick:{idx}"))

    builder.row(CallbackButton(text="Ответить", payload="lesson:submit"))
    builder.row(
        CallbackButton(text="Сбросить выбор", payload="lesson:clear"),
        CallbackButton(text="В меню", payload="menu:open"),
    )
    return [builder.as_markup()]


def build_lesson_confirm_keyboard() -> list:
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="Отправить результат", payload="lesson:finish"))
    builder.row(CallbackButton(text="Пройти заново", payload="lesson:restart"))
    builder.row(CallbackButton(text="В меню", payload="menu:open"))
    return [builder.as_markup()]


def build_exam_question_keyboard(
    keys: list[str],
    counts: dict[str, int],
) -> list:
    builder = InlineKeyboardBuilder()
    for index, key in enumerate(keys):
        value = counts.get(key, 0)
        builder.row(
            CallbackButton(text=f"-{index + 1}", payload=f"exam:dec:{index}"),
            CallbackButton(text=_truncate(f"{key}: {value}", 38), payload="exam:noop"),
            CallbackButton(text=f"+{index + 1}", payload=f"exam:inc:{index}"),
        )

    builder.row(CallbackButton(text="Ответить", payload="exam:submit"))
    builder.row(
        CallbackButton(text="Сбросить", payload="exam:clear"),
        CallbackButton(text="В меню", payload="menu:open"),
    )
    return [builder.as_markup()]


def build_result_keyboard() -> list:
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="В главное меню", payload="menu:open"))
    return [builder.as_markup()]
