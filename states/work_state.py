from aiogram.dispatcher.filters.state import StatesGroup, State


class WorkState(StatesGroup):
    form = State()
    submit = State()

