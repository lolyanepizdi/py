from aiogram.dispatcher.filters.state import StatesGroup, State


class ReviewState(StatesGroup):
    category = State()
    product_name = State()
    text = State()
    photo = State()
    submit = State()

