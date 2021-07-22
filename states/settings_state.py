from aiogram.dispatcher.filters.state import StatesGroup, State

# НАСТРОЙКА СПИСКА АДМИНОВ


class AdminState(StatesGroup):
    info = State()
    role = State()
    submit = State()

# НАСТРОЙКА БОНУСОВ


class BonusState(StatesGroup):
    bonus_amount = State()
    confirm = State()


class SetBonusState(StatesGroup):
    cid = State()
    bonus_amount = State()
    confirm = State()

# НАСТРОЙКА ПЛАТЕЖЕК


class BTCConfigState(StatesGroup):
    admin_address = State()
    submit = State()


class KunaConfigState(StatesGroup):
    api_key = State()
    api_secret = State()
    submit = State()

# НАСТРОЙКА КАНАЛОВ


class ChannelState(StatesGroup):
    channel_id = State()
    role = State()
    submit = State()

# НАСТРОЙКА РАССЫЛОК


class MailState(StatesGroup):
    text = State()
    submit = State()

# НАСТРОЙКА МОДЕРАЦИИ ОТЗЫВОВ


class ModerateReviewState(StatesGroup):
    channel_id = State()
    submit = State()

# НАСТРОЙКА ОТВЕТОВ НА ВОПРОСЫ


class AnswerState(StatesGroup):
    answer = State()
    submit = State()

# НАСТРОЙКА КОНТАКТОВ


class ContactState(StatesGroup):
    info = State()
    role = State()
    submit = State()
