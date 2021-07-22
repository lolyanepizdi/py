from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, CallbackQuery
from aiogram.utils.callback_data import CallbackData
from aiogram.dispatcher import FSMContext
from loader import dp, db, bot
from handlers.user.menu import orders
from filters import IsCura
from states import CheckoutState
from handlers.user import menu
from keyboards.default.markups import back_message, back_markup

postkind = {'ukrpost': '🇺🇦 Укрпочта', 'justin': '🌀 Justin', 'newpost': '📮 Новая Почта'}

cura_markup = ReplyKeyboardMarkup(selective=True)
cura_markup.add(menu.orders, back_message)

order_cb = CallbackData('order', 'id', 'action')


@dp.message_handler(IsCura(), text=orders)
async def process_orders(message: Message):
    if db.fetchone('SELECT * FROM orders') is None or db.fetchone('SELECT * FROM orders WHERE ttn=?', (0,)) is None:
        order_markup = ReplyKeyboardMarkup()
        order_markup.add('Выполненные заказы', back_message)
        await message.answer('У вас нет новых заказов.', reply_markup=order_markup)
    else:
        order_list = db.fetchall('SELECT * FROM orders WHERE ttn=?', (0,))
        for _, username, order_id, address, ttn, products, post_kind in order_list:
            post_kind = postkind[post_kind]
            address = address.split('\n')
            products = products.split('\n')
            answer = ''
            if len(products) > 1:
                product = ' шт.\n'.join(products)
            else:
                product = f'{"".join(products)} шт.'

            text = f'''<b>Телефон:</b> {address[0]}            
<b>ФИО:</b> {address[1]}
<b>Юзернэйм:</b> @{username}
<b>Город/почта:</b> {address[2]}
<b>Способ доставки:</b> {post_kind}
<b>ТТН:</b> {ttn}
<b>Заказ:</b>
{product}'''
            answer_markup = InlineKeyboardMarkup()
            answer_markup.add(InlineKeyboardButton(
                'Обновить ТТН', callback_data=order_cb.new(id=order_id, action='add_ttn')))
            answer_markup.add(InlineKeyboardButton(
                'Удалить заказ', callback_data=order_cb.new(id=order_id, action='delete_order')))

            await message.answer(text=text, reply_markup=answer_markup)


@dp.message_handler(IsCura(), text=back_message)
async def process_orders_back(message: Message):
    await menu.cura_menu(message)


@dp.message_handler(IsCura(), text='Выполненные заказы')
async def order_history_process(message: Message, state: FSMContext):
    if db.fetchone('SELECT * FROM orders WHERE NOT ttn=?', (0,)) is None:
        await message.answer('Выполненных заказов нет!', reply_markup=back_markup())
    else:
        order_history = db.fetchall('SELECT * FROM orders WHERE NOT ttn=?', (0,))
        for _, username, order_id, address, ttn, products, post_kind in order_history:
            post_kind = postkind[post_kind]
            address = address.split('\n')
            products = products.split('\n')

            if len(products) > 1:
                product = ' шт.\n'.join(products)
            else:
                product = f'{"".join(products)} шт.'

            text = f'''<b>Телефон:</b> {address[0]}            
<b>ФИО:</b> {address[1]}
<b>Юзернэйм:</b> @{username}
<b>Город/почта:</b> {address[2]}
<b>Способ доставки:</b> {post_kind}
<b>ТТН:</b> {ttn}
<b>Заказ:</b>
{product}'''

            answer_markup = InlineKeyboardMarkup()
            answer_markup.add(InlineKeyboardButton(
                'Обновить ТТН', callback_data=order_cb.new(id=order_id, action='add_ttn')))
            answer_markup.add(InlineKeyboardButton(
                'Удалить заказ', callback_data=order_cb.new(id=order_id, action='delete_order')))

            await message.answer(text=text, reply_markup=answer_markup)


@dp.callback_query_handler(IsCura(), order_cb.filter(action='add_ttn'))
async def process_answer(query: CallbackQuery, callback_data: dict, state: FSMContext):
    async with state.proxy() as data:
        data['order_id'] = callback_data['id']

    await query.message.answer('Напиши номер ТТН.', reply_markup=back_markup())
    await CheckoutState.ttn.set()


@dp.message_handler(IsCura(), text=back_message, state=CheckoutState.ttn)
async def process_send_answer(message: Message, state: FSMContext):
    await state.finish()
    await process_orders(message)


@dp.message_handler(IsCura(), lambda message: message.text.isdigit(), state=CheckoutState.ttn)
async def process_send_answer(message: Message, state: FSMContext):
    async with state.proxy() as data:
        ttn = message.text
        order_id = data['order_id']
        order = db.fetchall('SELECT * FROM orders WHERE order_id=?', (order_id,))
        for cid, username, order_id, address, _, products, _ in order:
            db.query('UPDATE orders SET ttn=? WHERE order_id=?', (ttn, order_id))
            address = address.split('\n')
            products = products.split('\n')
            answer = ''
            for product in products:
                if len(product) > 0:
                    answer += f'{product} шт.\n'

            text = f'''Заказ №<b>{order_id}</b> был обновлен!
<b>Телефон:</b> {address[0]}
<b>ФИО:</b> {address[1]}
<b>Юзернэйм:</b> @{username}
<b>Город/почта:</b> {address[2]}
<b>ТТН:</b> {ttn}
<b>Заказ:</b>
{answer}'''

            await message.answer(f'''Обновлено!
{text}''')
            await bot.send_message(cid, text)
        await state.finish()
        await menu.cura_menu(message)


@dp.message_handler(IsCura(), lambda message: not message.text.isdigit(), state=CheckoutState.ttn)
async def process_send_answer_invalid(message: Message, state: FSMContext):
    if message.text == back_message:
        await message.answer('Отменено!')
        await state.finish()
        await process_orders(message)
    else:
        await message.answer('Укажите ТТН в виде числа!')


@dp.callback_query_handler(IsCura(), order_cb.filter(action='delete_order'))
async def process_delete(query: CallbackQuery, callback_data: dict):
    order_id = callback_data['id']
    db.query('DELETE FROM orders WHERE order_id=?', (order_id,))
    await query.answer('Удалено!')
    await query.message.delete()
