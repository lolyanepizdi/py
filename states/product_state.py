from aiogram.dispatcher.filters.state import StatesGroup, State


class ProductState(StatesGroup):
    title = State()
    body = State()
    image = State()
    price = State()
    amount = State()
    confirm = State()


class CategoryState(StatesGroup):
    title = State()
