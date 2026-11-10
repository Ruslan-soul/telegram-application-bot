from aiogram.fsm.state import State, StatesGroup


class ApplicationForm(StatesGroup):
    name = State()
    phone = State()
    service = State()
    comment = State()
    confirmation = State()