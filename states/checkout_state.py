from aiogram.dispatcher.filters.state import StatesGroup, State


class CheckoutState(StatesGroup):
    payment_status = State()
    post_kind = State()
    check_cart = State()
    address = State()
    ttn = State()
    confirm = State()


class NewPostState(StatesGroup):
    submit = State()
