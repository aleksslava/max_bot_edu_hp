from maxapi.context import StatesGroup, State

class Main_menu(StatesGroup):
    authorize = State()
    welcome = State()
    menu = State()
    get_phone = State()
