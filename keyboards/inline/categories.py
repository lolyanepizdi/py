from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData
from loader import db


category_cb = CallbackData('category', 'id', 'action')


def categories_markup():

    global category_cb
    
    cat_markup = InlineKeyboardMarkup()
    for idx, title in db.fetchall('SELECT * FROM categories'):
        cat_markup.add(InlineKeyboardButton(title, callback_data=category_cb.new(id=idx, action='view')))

    return cat_markup
