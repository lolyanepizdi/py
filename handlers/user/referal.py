import json
from aiogram.types import ReplyKeyboardMarkup
from keyboards.default.markups import back_message
from aiogram.types import Message
from filters import IsUser
from loader import dp, db, bot
from handlers.user import menu
from handlers.user.menu import referal

markup = ReplyKeyboardMarkup()
markup.add(menu.catalog)
markup.add(menu.cart, menu.delivery_status, menu.reviews)
markup.add(referal, menu.recrute, menu.contacts)

ref_back_markup = ReplyKeyboardMarkup()
ref_back_markup.add(back_message)


@dp.message_handler(IsUser(), text=referal)
async def process_referral(message: Message):
    cid = message.from_user.id
    username = message.from_user.username
    ref = db.fetchone('SELECT * FROM referral WHERE cid=?', (cid,))
    if ref is None:
        ref_user = []
        ref_buyer = []
        bonus = 0
        db.query('INSERT INTO referral VALUES (?, ?, ?, ?, ?)', (cid, username, json.dumps(ref_user), json.dumps(ref_buyer), bonus))
    else:
        ref_user = json.loads(ref[2])
        ref_buyer = json.loads(ref[3])
        bonus = ref[4]
    me = await bot.get_me()
    ref_link = f'https://t.me/{me.username}?start={username}'
    await message.answer(f'''Привет! Это твоя рефералка. Приглашай друзей и получай 3% бонусов от их покупок.
Бонусами можно оплатить часть заказа, выше минимальной суммы, при условии, что накоплено 10$ и больше.

Твоя реферальная ссылка: {ref_link}

Кол-во перешедших по ссылке: <b>{len(ref_user)}</b>
Кол-во активных рефералов: <b>{len(ref_buyer)}</b>
Количество бонусов: <b>{round(bonus, 2)}</b>''', reply_markup=ref_back_markup)


@dp.message_handler(text=back_message)
async def process_review_cancel(message: Message):
    await message.answer('Отменено!', reply_markup=markup)
