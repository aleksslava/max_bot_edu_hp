from dataclasses import dataclass, field

from service.questions_lexicon import (
    exam_lesson,
    questions_1,
    questions_2,
    questions_3,
    questions_4,
    questions_5,
    questions_6,
    questions_7,
)


@dataclass
class RuntimeSession:
    mode: str = "menu"
    lesson_key: str | None = None
    lesson_id: int | None = None
    question_index: int = 0
    answers: dict[str, dict[str, bool]] = field(default_factory=dict)
    draft_selection: set[int] = field(default_factory=set)
    exam_answers: dict[str, dict[str, int]] = field(default_factory=dict)
    exam_index: int = 0
    exam_draft_counts: dict[str, int] = field(default_factory=dict)


runtime_sessions: dict[int, RuntimeSession] = {}

LESSON_META: dict[str, dict] = {
    "lesson_1": {
        "title": "Урок 1",
        "questions": questions_1,
        "status_key": "compleat_lesson_1",
        "amo_note_title": "Результаты урока №1",
        "video_url": "https://drive.google.com/file/d/1Pwg4YnD1fK5RJAvLxyzrcccPUPG_2nmy/view?usp=sharing",
    },
    "lesson_2": {
        "title": "Урок 2",
        "questions": questions_2,
        "status_key": "compleat_lesson_2",
        "amo_note_title": "Результаты урока №2",
        "video_url": "https://drive.google.com/file/d/1YlOt7Te4dcwXGp65H3IBLajs4rj_DtYL/view?usp=sharing",
    },
    "lesson_3": {
        "title": "Урок 3",
        "questions": questions_3,
        "status_key": "compleat_lesson_3",
        "amo_note_title": "Результаты урока №3",
        "video_url": "https://drive.google.com/file/d/1GL9EtnYC3FGEyTW4CHspot7MEO_EHWbG/view?usp=sharing",
    },
    "lesson_4": {
        "title": "Урок 4",
        "questions": questions_4,
        "status_key": "compleat_lesson_4",
        "amo_note_title": "Результаты урока №4",
        "video_url": "https://drive.google.com/file/d/1tglQ2ZJcZ4viWPttQ8dFPmWnM3W4r-KY/view?usp=drive_link",
    },
    "lesson_5": {
        "title": "Урок 5",
        "questions": questions_5,
        "status_key": "compleat_lesson_5",
        "amo_note_title": "Результаты урока №5",
        "video_url": "https://drive.google.com/file/d/13JPZHbnWCdSj7axmD5jya6f9XszVuRCB/view?usp=drive_link",
    },
    "lesson_6": {
        "title": "Урок 6",
        "questions": questions_6,
        "status_key": "compleat_lesson_6",
        "amo_note_title": "Результаты урока №6",
        "video_url": "https://drive.google.com/file/d/1EvB4Pqb0Z4vsrCLHekGaHygnNwk9-rT6/view?usp=drive_link",
    },
    "lesson_7": {
        "title": "Урок 7",
        "questions": questions_7,
        "status_key": "compleat_lesson_7",
        "amo_note_title": "Результаты урока №7",
        "video_url": "https://drive.google.com/file/d/1UikSd4lu5ec7rnTblwr0qCXg7IgYwJlN/view?usp=drive_link",
    },
}


def ordered_questions(question_dict: dict) -> list[dict]:
    return sorted(question_dict.values(), key=lambda q: int(str(q["key"])[1:]))


def evaluate_exam_answers(user_answers: dict[str, dict[str, int]]) -> dict:
    user_result_lines: list[str] = []
    amo_note_lines: list[str] = []
    correct_questions = 0

    for question_number, (q_key, expected_map) in enumerate(exam_lesson.items(), start=1):
        incoming_map = user_answers.get(q_key, {})
        if not isinstance(incoming_map, dict):
            incoming_map = {}

        question_is_correct = True
        amo_note_lines.append(f"Вопрос {question_number}:")

        for expected_key, expected_value in expected_map.items():
            actual_value = incoming_map.get(expected_key)
            is_correct = actual_value == expected_value
            if not is_correct:
                question_is_correct = False
            amo_note_lines.append(
                f"{expected_key} - {actual_value if actual_value is not None else 'не указан'} {'✅' if is_correct else '❌'}"
            )

        for extra_key in [key for key in incoming_map if key not in expected_map]:
            question_is_correct = False
            amo_note_lines.append(f"{extra_key} - {incoming_map.get(extra_key)} ❌")

        if question_is_correct:
            correct_questions += 1
        user_result_lines.append(f"Вопрос {question_number} {'✅' if question_is_correct else '❌'}")

    return {
        "score": correct_questions,
        "passed": correct_questions == len(exam_lesson),
        "result_text": "\n".join(user_result_lines),
        "amo_note_text": "\n".join(amo_note_lines),
    }
