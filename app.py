import ssl
from aiohttp import web
from aiogram.dispatcher.webhook import get_new_configured_app
from loader import dp, db, bot
from aiogram.types import Message
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher.webhook import SendMessage
from aiogram.utils.executor import start_webhook
from data.config import WEBHOOK_SSL_CERT, WEBHOOK_SSL_PRIV
from data.config import BOT_TOKEN
import filters
import logging

WEBHOOK_HOST = 'https://marrakesh.space'
WEBHOOK_PATH = '/app.py'
WEBHOOK_URL = f'{WEBHOOK_HOST}{WEBHOOK_PATH}'

WEBAPP_HOST = '199.189.108.70'
WEBAPP_PORT = 3301

filters.setup(dp)
logging.basicConfig(level=logging.INFO)
dp.middleware.setup(LoggingMiddleware())


@dp.message_handler()
async def echo(message: Message):
    return SendMessage(message.chat.id, message.text)


async def on_startup(dp):
    db.create_tables()
    await bot.set_webhook(WEBHOOK_URL, certificate=open(WEBHOOK_SSL_CERT, 'rb'))


async def on_shutdown(dp):
    logging.warning("Shutting down..")
    await bot.delete_webhook()
    await dp.storage.close()
    await dp.storage.wait_closed()
    logging.warning("Bot down")


if __name__ == '__main__':
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )
