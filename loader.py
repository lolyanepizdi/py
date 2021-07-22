from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from utils.db.storage import DatabaseManager
import asyncio

from data import config

loop = asyncio.get_event_loop()
bot = Bot(token=config.BOT_TOKEN, loop=loop, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
db = DatabaseManager('data/database.db')
