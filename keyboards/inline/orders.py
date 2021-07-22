from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData
from loader import db

order_cb = CallbackData('order', 'id', 'action')


def orders_markup():
    global order_cb

    markup = InlineKeyboardMarkup()
    for order_id, address, ttn, products in db.fetchall('SELECT * FROM orders'):
        markup.add(InlineKeyboardButton('Подробнее', callback_data=order_cb.new(id=order_id, action='expand')))
        markup.add(InlineKeyboardButton('Обновить ТТН', callback_data=order_cb.new(id=order_id, action='add_ttn')))
        markup.add(InlineKeyboardButton('Удалить заказ', callback_data=order_cb.new(id=order_id, action='delete_order')))
    return markup
