from aiogram.dispatcher.filters.state import StatesGroup, State


class BTCState(StatesGroup):
    wallet_id = State()
    address_num = State()
    balance = State()
    submit = State()


class KunaState(StatesGroup):
    code = State()
    status = State()
    submit = State()


class SpentBonusState(StatesGroup):
    total_cost = State()
    bonus = State()
    submit = State()
