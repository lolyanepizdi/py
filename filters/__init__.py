from aiogram import Dispatcher
from .is_admin import IsAdmin
from .is_user import IsUser
from .is_cura import IsCura
from .is_oper import IsOper


def setup(dp: Dispatcher):
    dp.filters_factory.bind(IsAdmin, event_handlers=[dp.message_handlers])
    dp.filters_factory.bind(IsUser, event_handlers=[dp.message_handlers])
    dp.filters_factory.bind(IsOper, event_handlers=[dp.message_handlers])
    dp.filters_factory.bind(IsCura, event_handlers=[dp.message_handlers])
