from maxapi.context import StatesGroup, State


class Exam(StatesGroup):
    vebinar = State()
    question_1 = State()
    question_2 = State()
    question_3 = State()
    question_4 = State()
    compleate = State()