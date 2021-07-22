
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardRemove
from loader import dp, db, bot
from .menu import delivery_status
from filters import IsUser
from aiogram.utils.callback_data import CallbackData
from aiogram.dispatcher import FSMContext
from keyboards.default.markups import *
from states import CheckoutState
order_cb = CallbackData('order', 'id', 'action')

postkind = {'ukrpost': '🇺🇦 Укрпочта', 'justin': '🌀 Justin', 'newpost': '📮 Новая Почта'}


@dp.message_handler(IsUser(), text=delivery_status)
async def process_delivery_status(message: Message):

    orders = db.fetchall('SELECT * FROM orders WHERE cid=?', (message.chat.id,))

    if len(orders) == 0:
        await message.answer('У вас нет активных заказов.')
    else:
        await delivery_status_answer(message, orders)


async def delivery_status_answer(message, orders):

    cid = message.chat.id

    for order in orders:
        ttn = order[4]
        order_id = order[2]

        res = f'Заказ <b>№{order_id}</b>'
        answer = [
            ' лежит на складе.',
            f' уже в пути! Ожидайте смс-сообщения от почты. Ваш ТТН для отслеживания: {ttn}',
        ]
        if ttn == 0:
            res += answer[0]
        else:
            res += answer[1]
        res += '\n\n'
        answer_markup = InlineKeyboardMarkup()
        answer_markup.add(InlineKeyboardButton(
            'Подробнее', callback_data=order_cb.new(id=order_id, action='expand')))

        await message.answer(res, reply_markup=answer_markup)


@dp.callback_query_handler(IsUser(), order_cb.filter(action='expand'))
async def process_expand(query: CallbackQuery, callback_data: dict, state: FSMContext):
    async with state.proxy() as data:
        data['order_id'] = callback_data['id']
        orders = db.fetchall('SELECT * FROM orders where order_id=?', (data['order_id'],))

        await query.message.answer('Ваш заказ:\n', reply_markup=back_markup())
        for cid, username, order_id, address, ttn, products, post_kind in orders:
            post_kind = postkind[post_kind]
            address = address.split('\n')
            products = products.split('\n')
            if len(products) > 1:
                product = ' шт.\n'.join(products)
            else:
                product = f'{"".join(products)} шт.'

            text = f'''<b>Телефон:</b> {address[0]}
<b>ФИО:</b> {address[1]}
<b>Город/почта:</b> {address[2]}
<b>Способ доставки:</b> {post_kind}
<b>ТТН:</b> {ttn}
<b>Заказ:</b>
{product}'''
        await query.message.answer(text, reply_markup=back_markup())

